"""Prepare a release-bound model. Run only during installation, as root."""
import argparse
import fcntl
import os
from pathlib import Path

from model_bundle import MODEL_ROOT, load_manifest, prepare
from release import RELEASE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='existing checkpoint directory; never trusted without hashes')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('model publication requires root')
    MODEL_ROOT.mkdir(parents=True, exist_ok=True, mode=0o755)
    with (MODEL_ROOT / '.prepare.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        manifest, digest = load_manifest()
        source = args.source
        if source is None:
            from huggingface_hub import snapshot_download
            snapshot = snapshot_download(RELEASE['model_repo'], revision=RELEASE['model_revision'],
                                         allow_patterns=[RELEASE['checkpoint'] + '/' + name for name in manifest['files']],
                                         token=False)
            source = Path(snapshot) / RELEASE['checkpoint']
        from laya.agent import _fix_tokenizer_config
        result = prepare(source, MODEL_ROOT, manifest, digest, _fix_tokenizer_config)
        print('Verified model prepared: ' + result.name)


if __name__ == '__main__':
    main()
