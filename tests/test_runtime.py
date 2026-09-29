import asyncio
import json
from pathlib import Path
import subprocess
import sys
import threading

import httpx
import pytest
from fastapi.testclient import TestClient
from release import RELEASE, verify_health
from server import create_app
from test_server import FakeRouter, KEY, REQUEST

ROOT = Path(__file__).resolve().parents[1]
AUTH = {"Authorization": "Bearer " + KEY}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setenv("LAYA_API_KEY", KEY)
    with TestClient(create_app(FakeRouter())) as c:
        yield c


@pytest.mark.parametrize("raw", [b"", b"{", b"[]", b"null", b'{}', b'\xff'])
def test_malformed_payload(client, raw):
    assert client.post("/v1/systemone", content=raw, headers=AUTH).status_code == 400


@pytest.mark.parametrize("field,value", [
    ("questions", {str(i): REQUEST["questions"]["team"] for i in range(9)}),
    ("questions", {"q": {"type": "choice", "criteria": {str(i): None for i in range(17)}}}),
    ("questions", {"q": {"type": "score", "criteria": [str(i) for i in range(11)]}}),
    ("questions", {str(i): {"type": "choice", "criteria": {str(j): None for j in range(16)}} for i in range(5)}),
])
def test_amplification_limits(client, field, value):
    assert client.post("/v1/systemone", json=REQUEST | {field: value}, headers=AUTH).status_code in (413, 422)


@pytest.mark.parametrize("value", [0, -1, True, "512", 513])
def test_invalid_budget(client, value):
    assert client.post("/v1/systemone", json=REQUEST | {"max_len": value}, headers=AUTH).status_code == 422


def test_credential_file_and_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        create_app(FakeRouter())
    (tmp_path / "api-key").write_text(KEY)
    with TestClient(create_app(FakeRouter())) as c:
        assert c.get("/health", headers=AUTH).status_code == 200


def test_missing_cache_fails_before_serving(monkeypatch):
    import model_bundle
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setenv("LAYA_API_KEY", KEY)
    monkeypatch.setattr(model_bundle, "MODEL_ROOT", Path('/nonexistent-layaas-model-test'))
    with pytest.raises((OSError, ValueError)):
        create_app()


def test_cancelled_client_retains_admission_until_inference_finishes(monkeypatch):
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setenv("LAYA_API_KEY", KEY)
    entered, release = threading.Event(), threading.Event()

    class BlockingRouter(FakeRouter):
        def predict(self, *args, **kwargs):
            entered.set()
            assert release.wait(5), "test failed to release inference"
            return super().predict(*args, **kwargs)

    async def run():
        app = create_app(BlockingRouter())
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as c:
                first = asyncio.create_task(c.post('/v1/systemone', json=REQUEST, headers=AUTH))
                try:
                    assert await asyncio.to_thread(entered.wait, 2)
                    second = asyncio.create_task(c.post('/v1/systemone', json=REQUEST, headers=AUTH))
                    # Let the second request acquire the remaining slot.
                    for _ in range(10):
                        await asyncio.sleep(0)
                    first.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await first
                    denied = await c.post('/v1/systemone', json=REQUEST, headers=AUTH)
                    assert denied.status_code == 503
                    assert (await c.get('/health', headers=AUTH)).status_code == 200
                finally:
                    release.set()
                assert (await second).status_code == 200
                assert (await c.post('/v1/systemone', json=REQUEST, headers=AUTH)).status_code == 200

    asyncio.run(run())


def test_model_identity_and_lock_consistency():
    lock = (ROOT / 'requirements-linux.lock').read_text()
    assert RELEASE['upstream_commit'] + '.tar.gz' in lock
    assert 'torch==' + RELEASE['torch_version'] + '+cpu' in lock
    for wrong in ({}, {"status": "ok", "device": "cpu", "device_is_preference": True}):
        with pytest.raises(ValueError):
            verify_health(wrong)
