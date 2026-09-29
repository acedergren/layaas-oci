import base64
import gzip
import json
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_stack_cloud_init_is_valid_and_embeds_only_pinned_files_and_secret_reference():
    sources = {
        "server": "server.py",
        "release_py": "release.py",
        "release_json": "release.json",
        "requirements": "requirements-linux.lock",
        "preload": "deploy/preload.py",
        "fetch_secret": "deploy/fetch_secret.py",
        "bootstrap": "deploy/bootstrap.sh",
        "api_service": "deploy/layaas-api.service",
        "secrets_service": "deploy/layaas-secrets.service",
    }
    values = {
        key: base64.b64encode(gzip.compress((ROOT / path).read_bytes())).decode()
        for key, path in sources.items()
    }
    values["api_secret_ocid"] = "ocid1.vaultsecret.oc1..fixture"
    template = (ROOT / "cloud-init.yaml.tftpl").read_text()
    rendered = re.sub(r"\$\{([a-z_]+)\}", lambda match: values[match.group(1)], template)
    config = yaml.safe_load(rendered)

    written = {entry["path"]: entry for entry in config["write_files"]}
    assert config["runcmd"] == [["bash", "/opt/laya/bootstrap.sh"]]
    for key, relative in sources.items():
        entry = written[next(path for path, name in {
            "/opt/laya/server.py": "server.py",
            "/opt/laya/release.py": "release.py",
            "/opt/laya/release.json": "release.json",
            "/opt/laya/requirements-linux.lock": "requirements-linux.lock",
            "/opt/laya/preload.py": "deploy/preload.py",
            "/opt/laya/fetch_secret.py": "deploy/fetch_secret.py",
            "/opt/laya/bootstrap.sh": "deploy/bootstrap.sh",
            "/etc/systemd/system/layaas-api.service": "deploy/layaas-api.service",
            "/etc/systemd/system/layaas-secrets.service": "deploy/layaas-secrets.service",
        }.items() if name == relative)]
        assert gzip.decompress(base64.b64decode(entry["content"])) == (ROOT / relative).read_bytes()
        assert entry["encoding"] == "gz+b64"

    refs = json.loads(written["/etc/laya/api-secret.json"]["content"])
    assert refs == {"secret_ocid": values["api_secret_ocid"]}
