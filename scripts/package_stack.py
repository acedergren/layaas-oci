"""Create a Resource Manager zip containing only the deployable stack files."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
STACK_FILES = (
    "main.tf", "variables.tf", "outputs.tf", "schema.yaml", ".terraform.lock.hcl",
    "cloud-init.yaml.tftpl", "LICENSE", "NOTICE",
    "server.py", "release.py", "release.json", "requirements-linux.lock",
    "model_bundle.py", "model-manifest.json",
    "deploy/bootstrap.sh", "deploy/preload.py", "deploy/fetch_secret.py",
    "deploy/layaas-api.service", "deploy/layaas-secrets.service",
)


def package_stack(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in STACK_FILES:
            source = ROOT / relative
            if not source.is_file():
                raise FileNotFoundError(f"Required stack file is missing: {relative}")
            archive.write(source, arcname=relative)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default="dist/layaas-oci-stack.zip")
    args = parser.parse_args()
    output = package_stack(args.output)
    print(f"Wrote {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
