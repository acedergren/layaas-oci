"""Release-bound model preparation and fail-closed local loading.

Trust boundary: approved release/code and root are trusted. Writable download
caches are not. Runtime callers cannot disable ownership/ancestor checks.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from release import RELEASE

MODEL_ROOT = Path('/opt/laya/models')
FILES = {'model.safetensors', 'rl_agent_config.json', 'encoder/config.json',
         'tokenizer/tokenizer.json', 'tokenizer/tokenizer_config.json'}


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_manifest():
    path = Path(__file__).with_name('model-manifest.json')
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != RELEASE['model_manifest_sha256']:
        raise ValueError('model manifest digest does not match approved release')
    manifest = json.loads(raw)
    if manifest['schema_version'] != 1 or set(manifest['files']) != FILES:
        raise ValueError('unexpected model manifest schema or files')
    for field in ('model_repo', 'model_revision', 'checkpoint', 'upstream_commit'):
        if manifest[field] != RELEASE[field]:
            raise ValueError('model manifest identity mismatch: ' + field)
    return manifest, digest


def bundle_name(manifest, digest):
    return manifest['model_revision'] + '-' + digest


def _protected(path, owner, immutable=False):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or info.st_uid != owner:
        raise ValueError('model path has unexpected owner or link: ' + str(path))
    forbidden = 0o222 if immutable else 0o022
    if info.st_mode & forbidden:
        raise ValueError('model path is writable: ' + str(path))
    return info


def verify_bundle(path, manifest, *, owner=0, ancestors=True):
    """Validate the complete tree, including root-controlled directory entries."""
    path = Path(os.path.abspath(path))  # Do not resolve away a symlink.
    if ancestors:
        for parent in reversed(path.parents):
            _protected(parent, owner)
    _protected(path, owner, immutable=True)
    expected = set(manifest['files'])
    directories = {str(p) for name in expected for p in Path(name).parents if str(p) != '.'}
    actual = set()
    for item in path.rglob('*'):
        relative = item.relative_to(path).as_posix()
        info = _protected(item, owner, immutable=True)
        if stat.S_ISDIR(info.st_mode) and relative in directories:
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or relative not in expected:
            raise ValueError('unexpected model entry or link: ' + relative)
        record = manifest['files'][relative]
        if info.st_size != record['size'] or sha256(item) != record['sha256']:
            raise ValueError('model content mismatch: ' + relative)
        actual.add(relative)
    if actual != expected:
        raise ValueError('model files are missing')
    return path


def prepare(source, root, manifest, digest, normalize, *, owner=0):
    """Copy verified bytes, normalize, verify again, and atomically publish.

    Caller serializes preparation and protects root. Existing final copies must
    already match; preparation never overwrites them. Stale staging directories
    from a killed installer are never selected as runtime models.
    """
    source, root = Path(source), Path(root)
    _protected(root, owner)
    target = root / bundle_name(manifest, digest)
    if target.exists() or target.is_symlink():
        return verify_bundle(target, manifest, owner=owner, ancestors=False)
    stage = Path(tempfile.mkdtemp(prefix='.prepare-', dir=root))
    try:
        for relative, record in manifest['files'].items():
            src, dst = source / relative, stage / relative
            # HF cache links may point at blobs; only copied bytes enter the bundle.
            # Hash the copied bytes, not a racy separate read of writable source.
            if not src.is_file():
                raise ValueError('missing source file: ' + relative)
            dst.parent.mkdir(parents=True, exist_ok=True)
            with src.open('rb') as inp, dst.open('xb') as out:
                remaining = max(record['source_size'], record['size'])
                while chunk := inp.read(min(1024 * 1024, remaining + 1)):
                    if len(chunk) > remaining:
                        raise ValueError('source exceeds approved file size: ' + relative)
                    out.write(chunk)
                    remaining -= len(chunk)
            observed = (sha256(dst), dst.stat().st_size)
            if observed not in {(record['source_sha256'], record['source_size']),
                                (record['sha256'], record['size'])}:
                raise ValueError('unapproved source content: ' + relative)
        normalize(str(stage))
        for item in stage.rglob('*'):
            # Never chmod a link introduced during a failed/incorrect normalizer.
            if item.is_symlink():
                raise ValueError('normalizer introduced a link')
            item.chmod(0o555 if item.is_dir() else 0o444)
        stage.chmod(0o555)
        verify_bundle(stage, manifest, owner=owner, ancestors=False)
        os.rename(stage, target)
        return target
    finally:
        if stage.exists():
            for item in stage.rglob('*'):
                if item.is_dir() and not item.is_symlink(): item.chmod(0o700)
            stage.chmod(0o700)
            shutil.rmtree(stage)


def load_router():
    """No Hub resolution, network fallback, dynamic model selection or monkeypatch."""
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
    manifest, digest = load_manifest()
    path = verify_bundle(MODEL_ROOT / bundle_name(manifest, digest), manifest)
    from importlib.metadata import version, distributions
    for package, expected in RELEASE['packages'].items():
        if version(package) != expected:
            raise RuntimeError('unexpected installed package version: ' + package)
    if any(d.metadata['Name'].lower().startswith(('nvidia-', 'triton')) for d in distributions()):
        raise RuntimeError('GPU dependency is not permitted')
    import torch
    from laya import Agent, Router
    if torch.version.cuda is not None:
        raise RuntimeError('CPU-only Torch is required')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    agent = Agent(str(path), device='cpu', fast=False, compile=False,
                  expected_sha256={name: record['sha256'] for name, record in manifest['files'].items()})
    # A protected local load must not alter the prepared tokenizer or any file.
    verify_bundle(path, manifest)
    agent.revision = manifest['model_revision']
    router = Router(device='cpu', revision=agent.revision, max_loaded=1, auto_task_detection=False)
    router.attach(RELEASE['checkpoint'], agent)
    return router
