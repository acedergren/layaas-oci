"""Read one OCI Vault secret into root-only runtime storage."""
import base64
import os
from pathlib import Path
import tempfile


def fetch(client, secret_id, directory):
    bundle = client.get_secret_bundle(secret_id, stage="CURRENT").data
    value = base64.b64decode(bundle.secret_bundle_content.content, validate=True).strip()
    if len(value) < 32 or not value.isascii() or any(chr(byte).isspace() for byte in value):
        raise ValueError("invalid API credential")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    fd, temporary = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, directory / "api-key")
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    import json
    import time
    import oci

    config = json.loads(Path("/etc/laya/api-secret.json").read_text())
    for attempt in range(30):
        try:
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner(timeout=(5, 10))
            client = oci.secrets.SecretsClient({}, signer=signer, timeout=(5, 10))
            fetch(client, config["secret_ocid"], Path("/run/laya-secrets"))
            print("Runtime API credential loaded")
            return
        except Exception:
            if attempt == 29:
                raise SystemExit("Runtime Vault retrieval failed; check IAM and secret metadata") from None
            time.sleep(20)


if __name__ == "__main__":
    main()
