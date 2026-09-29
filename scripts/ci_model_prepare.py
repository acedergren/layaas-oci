"""Root-only CI fixture preparation and recorded immutable model checks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model_bundle import MODEL_ROOT, load_manifest, prepare, verify_bundle, sha256
from laya.agent import _fix_tokenizer_config
from huggingface_hub import snapshot_download
from release import RELEASE

assert os.geteuid() == 0
# Hosted runners make /opt group-writable for tool installers. Model ancestors
# must meet the real runtime contract; harden this disposable CI fixture.
Path("/opt").chmod(0o755)
manifest, digest = load_manifest()
MODEL_ROOT.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
MODEL_ROOT.parent.chmod(0o755)
MODEL_ROOT.mkdir(exist_ok=True, mode=0o755)
start = time.perf_counter()
snapshot = snapshot_download(RELEASE['model_repo'], revision=RELEASE['model_revision'],
                             allow_patterns=[RELEASE['checkpoint'] + '/' + name for name in manifest['files']], token=False)
source = Path(snapshot) / RELEASE['checkpoint']
bundle = prepare(source, MODEL_ROOT, manifest, digest, _fix_tokenizer_config)
verify_bundle(bundle, manifest)
# Actual denied file write and denied replacement of the entire bundle as runtime UID.
for target in [bundle / 'model.safetensors', bundle / 'tokenizer/tokenizer_config.json', MODEL_ROOT / 'unexpected']:
    cmd = ['runuser', '-u', os.environ['CI_RUNTIME_USER'], '--', sys.executable, '-c',
           'import sys; open(sys.argv[1], "ab").write(b"denied")', str(target)]
    check = subprocess.run(cmd, capture_output=True)
    assert check.returncode != 0 and b'PermissionError' in check.stderr
before = {n: sha256(bundle / n) for n in manifest['files']}
_fix_tokenizer_config(str(bundle))
assert before == {n: sha256(bundle / n) for n in manifest['files']}
result = {'model_manifest_sha256': digest, 'prepare_seconds': time.perf_counter() - start,
          'model_bytes': sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file()),
          'files': len(manifest['files']), 'write_denial': True, 'normalization_noop': True}
Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n')
