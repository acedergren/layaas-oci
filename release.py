"""The single runtime source for release identity and resource limits."""
import json
from pathlib import Path
import re

RELEASE = json.loads(Path(__file__).with_name("release.json").read_text())
for field in ("upstream_commit", "model_revision"):
    if not re.fullmatch(r"[0-9a-f]{40}", RELEASE[field]):
        raise RuntimeError("release requires immutable source/model commits")
LIMITS = RELEASE["limits"]


def verify_health(health):
    """Raise on preference-only reporting, wrong device or checkpoint identity."""
    if not (health.get("status") == "ok" and health.get("device") == "cpu"
            and health.get("device_is_preference") is False
            and health.get("loaded") == [RELEASE["checkpoint"]]
            and health.get("revisions") == {RELEASE["checkpoint"]: RELEASE["model_revision"]}):
        raise ValueError("unexpected model readiness or identity")
