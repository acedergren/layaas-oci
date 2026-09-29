import pytest
from fastapi.testclient import TestClient
from server import create_app, MODEL_REVISION

KEY = "test-only-not-a-real-secret-123456789"
REQUEST = {"model": "multilingual", "state": "Please refund the duplicate charge.",
           "questions": {"team": {"type": "choice", "instructions": "Which team?",
                                  "criteria": {"billing": None, "technical": None}}}}


class FakeRouter:
    loaded = ["multilingual"]
    loaded_revisions = {"multilingual": MODEL_REVISION}
    calls = []

    def predict(self, state, questions, **kwargs):
        self.calls.append(kwargs)
        return {"model": "test-fixture", "answers": {}, "usage": {"output_tokens": 0}}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setenv("LAYA_API_KEY", KEY)
    with TestClient(create_app(FakeRouter())) as c:
        yield c


def test_missing_secret_fails_before_loading(monkeypatch):
    monkeypatch.delenv("LAYA_API_KEY", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    with pytest.raises(RuntimeError):
        create_app()


@pytest.mark.parametrize("path", ["/health", "/docs", "/openapi.json", "/missing"])
def test_all_routes_protected(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_inference_auth_and_forced_model(client):
    assert client.post("/v1/systemone", json=REQUEST).status_code == 401
    result = client.post("/v1/systemone", json=REQUEST, headers={"Authorization": "Bearer " + KEY})
    assert result.status_code == 200
    assert FakeRouter.calls[-1] == {"model": "multilingual", "max_len": 512, "head_max_len": 128}


@pytest.mark.parametrize("change,code", [({"model": "english"}, 422),
    ({"max_len": 513}, 422), ({"head_max_len": 100000}, 422),
    ({"state": "x" * 8001}, 413), ({"state": "x" * 33000}, 413)])
def test_limits(client, change, code):
    assert client.post("/v1/systemone", json=REQUEST | change,
                       headers={"Authorization": "Bearer " + KEY}).status_code == code


def test_duplicate_auth_denied(client):
    assert client.get("/health", headers=[("Authorization", "Bearer " + KEY),
                                          ("Authorization", "Bearer " + KEY)]).status_code == 401


def test_health_identity(client):
    response = client.get("/health", headers={"Authorization": "Bearer " + KEY})
    assert response.status_code == 200
    assert response.json()["revisions"] == {"multilingual": MODEL_REVISION}
