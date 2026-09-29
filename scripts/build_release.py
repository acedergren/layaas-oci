"""Build allowlisted, deterministic archives and commit-bound release metadata."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.package_stack import STACK_FILES
from release import RELEASE

RUNTIME_FILES = ('server.py', 'release.py', 'release.json', 'model_bundle.py',
                 'model-manifest.json', 'requirements-linux.lock', 'deploy/preload.py',
                 'LICENSE', 'NOTICE')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive(path, files):
    with ZipFile(path, 'w', ZIP_DEFLATED, compresslevel=9) as package:
        for relative in sorted(files):
            source = ROOT / relative
            if source.is_symlink() or not source.is_file():
                raise ValueError('release input must be a regular file')
            info = ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            package.writestr(info, source.read_bytes())


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, text=True).strip():
        raise SystemExit('release requires clean tracked files')
    comparison = json.loads((output / 'comparison.json').read_text())
    if comparison.get('candidate_commit') != commit or comparison.get('passed') is not True:
        raise SystemExit('passing comparison must match release commit')
    archive(output / 'layaas-runtime.zip', RUNTIME_FILES)
    archive(output / 'layaas-oci-stack.zip', STACK_FILES)
    metadata = {'schema_version': 1, 'version': RELEASE['version'], 'commit': commit,
                'packages': RELEASE['packages'], 'model_manifest_sha256': RELEASE['model_manifest_sha256'],
                'runtime_sha256': digest(output / 'layaas-runtime.zip'),
                'runtime_files': {n: digest(ROOT / n) for n in RUNTIME_FILES},
                'artifacts': {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file() and p.suffix in ('.zip', '.json')}}
    (output / 'release-manifest.json').write_text(json.dumps(metadata, indent=2, sort_keys=True) + '\n')
    (output / 'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in sorted(output.iterdir()) if p.name != 'SHA256SUMS' and p.is_file()))
    print('Built release for ' + commit)


if __name__ == '__main__':
    main()
