"""Security properties with tiny synthetic files; real weights are tested in Linux CI."""
import hashlib
import os
from pathlib import Path
import pytest

from model_bundle import prepare, verify_bundle, load_manifest, bundle_name


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def fixture(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    data = b'{"fixture": true}'
    (source / 'config.json').write_bytes(data)
    manifest = {'model_revision': 'a' * 40, 'files': {'config.json': {
        'source_sha256': digest(data), 'source_size': len(data),
        'sha256': digest(data), 'size': len(data)}}}
    target = tmp_path / 'models'
    target.mkdir()
    yield source, target, manifest
    # Restore fixture directory modes so pytest can remove them, without following links.
    for current, dirs, files in os.walk(target):
        Path(current).chmod(0o700)
        for name in dirs:
            child = Path(current) / name
            if not child.is_symlink(): child.chmod(0o700)


def call(fixture, normalize=lambda p: None):
    source, target, manifest = fixture
    return prepare(source, target, manifest, 'b' * 64, normalize, owner=os.getuid())


def verify(path, manifest):
    # The runtime always checks all root-owned ancestors; tests isolate file checks.
    return verify_bundle(path, manifest, owner=os.getuid(), ancestors=False)


def test_manifest_release_binding():
    manifest, sha = load_manifest()
    assert len(manifest['files']) == 5
    assert bundle_name(manifest, sha) == manifest['model_revision'] + '-' + sha


def test_prepare_immutable_copy_and_resume(fixture):
    path = call(fixture)
    verify(path, fixture[2])
    assert (path / 'config.json').stat().st_ino != (fixture[0] / 'config.json').stat().st_ino
    assert not path.stat().st_mode & 0o222
    assert call(fixture) == path


@pytest.mark.parametrize('variant', ['tamper', 'missing', 'symlink', 'hardlink', 'writable', 'extra'])
def test_reject_bad_final_bundle(fixture, variant):
    path = call(fixture)
    path.chmod(0o755)
    f = path / 'config.json'
    f.chmod(0o644)
    if variant == 'tamper': f.write_text('changed')
    if variant == 'missing': f.unlink()
    if variant == 'symlink':
        f.unlink(); f.symlink_to(fixture[0] / 'config.json')
    if variant == 'hardlink': os.link(f, fixture[0] / 'linked')
    if variant == 'extra': (path / 'surprise').write_text('x')
    if variant != 'writable' and f.exists() and not f.is_symlink(): f.chmod(0o444)
    path.chmod(0o555)
    with pytest.raises((ValueError, FileNotFoundError)):
        verify(path, fixture[2])


def test_changed_source_and_failed_normalization_never_publish(fixture):
    fixture[0].joinpath('config.json').write_text('changed')
    with pytest.raises(ValueError): call(fixture)
    assert list(fixture[1].iterdir()) == []


def test_interrupted_prepare_never_publishes(fixture):
    def fail(path): raise RuntimeError('normalization interrupted')
    with pytest.raises(RuntimeError): call(fixture, fail)
    assert list(fixture[1].iterdir()) == []
    call(fixture)


def test_normalizer_must_produce_reviewed_bytes(fixture):
    def corrupt(path): Path(path, 'config.json').write_text('unknown normalization')
    with pytest.raises(ValueError): call(fixture, corrupt)
    assert list(fixture[1].iterdir()) == []


def test_old_source_variant_and_normalized_cache(fixture):
    old = b'{"old": true}'
    record = fixture[2]['files']['config.json']
    record.update(source_sha256=digest(old), source_size=len(old))
    fixture[0].joinpath('config.json').write_bytes(old)
    def normalize(path): Path(path, 'config.json').write_bytes(b'{"fixture": true}')
    path = call(fixture, normalize)
    verify(path, fixture[2])


def test_unexpected_source_link_is_rejected(fixture):
    f = fixture[0] / 'config.json'
    f.unlink(); f.symlink_to('/etc/passwd')
    with pytest.raises(ValueError): call(fixture)


def test_manifest_digest_and_identity_fail_closed(monkeypatch, tmp_path):
    import json
    import model_bundle
    from release import RELEASE
    real, _ = load_manifest()
    monkeypatch.setitem(RELEASE, 'model_manifest_sha256', '0' * 64)
    with pytest.raises(ValueError, match='digest'): load_manifest()
    real['model_revision'] = 'f' * 40
    data = json.dumps(real).encode()
    (tmp_path / 'model-manifest.json').write_bytes(data)
    monkeypatch.setattr(model_bundle, '__file__', str(tmp_path / 'model_bundle.py'))
    monkeypatch.setitem(RELEASE, 'model_manifest_sha256', digest(data))
    with pytest.raises(ValueError, match='identity'): load_manifest()


def test_unexpected_owner_is_rejected(fixture):
    path = call(fixture)
    with pytest.raises(ValueError, match='owner'):
        verify_bundle(path, fixture[2], owner=os.getuid() + 1, ancestors=False)
