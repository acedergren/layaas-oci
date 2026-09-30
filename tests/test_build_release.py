"""Release metadata must depend only on the intended release artifacts."""

import hashlib
import json
import subprocess
import sys

from scripts import build_release


def test_rebuild_ignores_existing_manifest_and_unrelated_files(tmp_path, monkeypatch):
    commit = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=build_release.ROOT, text=True
    ).strip()
    (tmp_path / 'comparison.json').write_text(
        json.dumps({'candidate_commit': commit, 'passed': True})
    )
    for name in (
        'model-manifest.json', 'baseline.json', 'candidate.json', 'restart.json',
        'preparation.json', 'dependency-audit.json',
    ):
        (tmp_path / name).write_text('{}')
    for name in ('stale.zip', 'stale.json', 'notes.txt'):
        (tmp_path / name).write_text('not a release artifact')

    # The test's tracked file changes must not block a local metadata test.
    monkeypatch.setattr(
        build_release.subprocess, 'check_output',
        lambda args, **kwargs: commit if args[1] == 'rev-parse' else '',
    )
    monkeypatch.setattr(sys, 'argv', ['build_release.py', str(tmp_path)])

    build_release.main()
    first_manifest = (tmp_path / 'release-manifest.json').read_bytes()
    first_sums = (tmp_path / 'SHA256SUMS').read_bytes()
    build_release.main()

    assert (tmp_path / 'release-manifest.json').read_bytes() == first_manifest
    assert (tmp_path / 'SHA256SUMS').read_bytes() == first_sums

    manifest = json.loads(first_manifest)
    assert set(manifest['artifacts']) == {
        'comparison.json', 'layaas-runtime.zip', 'layaas-oci-stack.zip',
        'model-manifest.json', 'baseline.json', 'candidate.json', 'restart.json',
        'preparation.json', 'dependency-audit.json',
    }
    for name, expected in manifest['artifacts'].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == expected

    sums = [line.split('  ', 1) for line in first_sums.decode().splitlines()]
    assert len(sums) == 10
    assert {name for _, name in sums} == {
        'comparison.json', 'layaas-runtime.zip', 'layaas-oci-stack.zip',
        'release-manifest.json', 'model-manifest.json', 'baseline.json',
        'candidate.json', 'restart.json', 'preparation.json',
        'dependency-audit.json',
    }
    for expected, name in sums:
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == expected
