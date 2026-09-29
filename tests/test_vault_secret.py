import base64
from pathlib import Path
from types import SimpleNamespace

import pytest

from deploy.fetch_secret import fetch


class Vault:
    def __init__(self, value):
        self.value = value
    def get_secret_bundle(self, identifier, stage):
        assert identifier == "ocid1.vaultsecret.fixture"
        assert stage == "CURRENT"
        return SimpleNamespace(data=SimpleNamespace(secret_bundle_content=SimpleNamespace(
            content=base64.b64encode(self.value).decode())))


def test_fetch_secret_writes_only_valid_value_with_restrictive_permissions(tmp_path):
    fetch(Vault(b"fixture-only-api-key-with-more-than-32-bytes"),
          "ocid1.vaultsecret.fixture", tmp_path)

    assert tmp_path.stat().st_mode & 0o777 == 0o700
    secret_file = tmp_path / "api-key"
    assert secret_file.read_bytes() == b"fixture-only-api-key-with-more-than-32-bytes"
    assert secret_file.stat().st_mode & 0o777 == 0o600


def test_fetch_secret_rejects_short_secret_without_writing(tmp_path):
    with pytest.raises(ValueError):
        fetch(Vault(b"short"), "ocid1.vaultsecret.fixture", tmp_path)

    assert not list(tmp_path.iterdir())
