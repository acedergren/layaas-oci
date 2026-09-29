import server


def test_main_uses_configured_private_listener(monkeypatch):
    calls = []
    class Uvicorn:
        @staticmethod
        def run(app, **kwargs):
            calls.append((app, kwargs))
    monkeypatch.setattr(server, "create_app", lambda: "app")
    monkeypatch.setitem(__import__("sys").modules, "uvicorn", Uvicorn)
    monkeypatch.setenv("LAYA_BIND_HOST", "0.0.0.0")
    monkeypatch.setenv("LAYA_PORT", "8123")

    server.main()

    assert calls == [("app", {
        "host": "0.0.0.0", "port": 8123, "workers": 1,
        "access_log": False, "proxy_headers": False,
        "limit_concurrency": 16, "timeout_keep_alive": 5,
    })]


def test_main_defaults_to_loopback(monkeypatch):
    calls = []
    class Uvicorn:
        @staticmethod
        def run(app, **kwargs):
            calls.append(kwargs)
    monkeypatch.setattr(server, "create_app", lambda: "app")
    monkeypatch.setitem(__import__("sys").modules, "uvicorn", Uvicorn)
    monkeypatch.delenv("LAYA_BIND_HOST", raising=False)
    monkeypatch.delenv("LAYA_PORT", raising=False)

    server.main()

    assert calls[0]["host"] == "127.0.0.1"
    assert calls[0]["port"] == 8000
