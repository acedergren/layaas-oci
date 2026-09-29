"""Private CPU deployment adapter; upstream Laya remains unmodified."""
import asyncio
import hmac
import logging
import os
import time
from pathlib import Path

from release import RELEASE, LIMITS

UPSTREAM_COMMIT = RELEASE["upstream_commit"]
MODEL_REPO = RELEASE["model_repo"]
MODEL_REVISION = RELEASE["model_revision"]
CHECKPOINT = RELEASE["checkpoint"]
MAX_TOKENS = LIMITS["max_tokens"]
log = logging.getLogger("laya.deployment")


class FixedRouter:
    def __init__(self, router):
        self.router = router

    def __getattr__(self, name):
        return getattr(self.router, name)

    def predict(self, state, questions, model=None, **kwargs):
        if model not in (None, CHECKPOINT):
            raise ValueError("this deployment serves only the multilingual checkpoint")
        return self.router.predict(
            state, questions, model=CHECKPOINT,
            max_len=kwargs.get("max_len", MAX_TOKENS),
            head_max_len=kwargs.get("head_max_len", LIMITS["head_tokens"]),
        )


class ProtectAllRoutes:
    """Pure ASGI auth before body reads; logs no paths, bodies or credentials."""
    def __init__(self, app, key):
        self.app = app
        self.expected = ("Bearer " + key).encode()
        self.running = set()

    def finished(self, task):
        self.running.discard(task)
        if not task.cancelled() and task.exception() is not None:
            log.error("request transport failed; details suppressed")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        from starlette.responses import JSONResponse
        headers = [v for k, v in scope["headers"] if k == b"authorization"]
        if len(headers) != 1 or not hmac.compare_digest(headers[0], self.expected):
            return await JSONResponse({"detail": "unauthorized"}, status_code=401)(scope, receive, send)
        started = time.monotonic()
        status = 500

        async def record(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        async def dispatch():
            try:
                await self.app(scope, receive, record)
            finally:
                log.info("request status=%d duration_ms=%.1f", status, (time.monotonic()-started)*1000)

        if scope["path"] == "/v1/systemone":
            # Cancelling a client cannot cancel a running torch thread. Keep
            # upstream admission/inference locks until the work actually ends.
            task = asyncio.create_task(dispatch())
            self.running.add(task)
            task.add_done_callback(self.finished)
            await asyncio.shield(task)
        else:
            await dispatch()


def create_app(router=None):
    key = os.environ.get("LAYA_API_KEY", "")
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    if credential_dir:
        key = (Path(credential_dir) / "api-key").read_text().strip()
    if len(key) < 32 or not key.isascii() or any(c.isspace() for c in key):
        raise RuntimeError("a non-whitespace ASCII API secret of at least 32 characters is required")
    os.environ["LAYA_API_KEY"] = key
    os.environ["LAYA_DEVICE"] = "cpu"
    os.environ["LAYA_MAX_CONCURRENT"] = str(LIMITS["admitted_requests"])
    os.environ["LAYA_MAX_TOKEN_BUDGET"] = str(MAX_TOKENS)
    from laya import serve
    serve.MAX_BODY_BYTES = LIMITS["body_bytes"]
    serve.MAX_STATE_CHARS = LIMITS["state_chars"]
    serve.MAX_QUESTIONS = LIMITS["questions"]
    serve.MAX_CHOICE_OPTIONS = LIMITS["choice_options"]
    serve.MAX_SCORE_LEVELS = LIMITS["score_levels"]
    serve.MAX_TOTAL_OPTIONS = LIMITS["total_options"]
    if router is None:
        import torch
        from laya import Router
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        router = Router(device="cpu", revision=MODEL_REVISION, max_loaded=1,
                        auto_task_detection=False)
        router.preload([CHECKPOINT])
    app = serve.create_app(router=FixedRouter(router))
    app.add_middleware(ProtectAllRoutes, key=key)
    return app


def main():
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    host = os.environ.get("LAYA_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("LAYA_PORT", "8000"))
    uvicorn.run(create_app(), host=host, port=port, workers=1,
                access_log=False, proxy_headers=False, limit_concurrency=16,
                timeout_keep_alive=5)


if __name__ == "__main__":
    main()
