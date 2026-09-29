import sys

from examples import client


def test_malformed_credential_is_rejected_without_echoing_value(monkeypatch, capsys):
    bad_key = "fixture secret with spaces"
    monkeypatch.setenv("LAYA_API_KEY", bad_key)
    monkeypatch.setattr(sys, "argv", ["client.py", "http://127.0.0.1:1"])

    result = client.main()

    assert result == 2
    output = capsys.readouterr()
    assert bad_key not in output.out + output.err
