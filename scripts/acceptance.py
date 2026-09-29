"""Synthetic, local ASGI acceptance. Run baseline and candidate on ONE Linux runner.

Run inside an isolated network namespace, as a non-root user. Never use a live
API or real credentials. Failure is fatal; this script cannot change tolerances.
"""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import resource
import socket
import statistics
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def cases():
    result = {}
    states = {
        'en': {
            'normal': 'I was charged twice for one purchase. Please refund the duplicate charge.',
            'negated': 'I was not charged twice. I do not want a refund. The application crashes on login.',
            'ambiguous': 'The payment looks odd and the application sometimes stops. I am unsure what happened.',
            'long': ('This is a synthetic routine support note about a closed historical case. ' * 85) + ' The application now crashes; no refund is requested.',
        },
        'sv': {
            'normal': 'Jag debiterades två gånger för ett köp. Återbetala den dubbla debiteringen.',
            'negated': 'Jag debiterades inte två gånger och vill inte ha återbetalning. Appen kraschar vid inloggning.',
            'ambiguous': 'Betalningen ser konstig ut och appen stannar ibland. Jag vet inte vad som hände.',
            'long': ('Detta är en syntetisk rutinanteckning om ett gammalt avslutat supportärende. ' * 85) + ' Appen kraschar nu; ingen återbetalning begärs.',
        },
    }
    for language, styles in states.items():
        sample = json.loads((ROOT / 'samples' / f'typed-{language}.json').read_text())
        for question, definition in sample['questions'].items():
            for style, state in styles.items():
                result[f'{language}-{definition["type"]}-{style}'] = sample | {'state': state, 'questions': {question: definition}}
    assert len(result) == 24
    return result


def run(args):
    started = time.perf_counter()
    assert platform.system() == 'Linux' and platform.machine() == 'x86_64'
    assert os.geteuid() != 0, 'inference must run as unprivileged user'
    # Namespace must have only loopback (down). An offline env flag alone is not proof.
    interfaces = sorted(name for _, name in socket.if_nameindex())
    assert interfaces == ['lo'], interfaces
    sys.path.insert(0, str(args.runtime))
    os.environ['LAYA_API_KEY'] = 'synthetic-ci-only-not-a-production-credential'
    from fastapi.testclient import TestClient
    from server import create_app
    from release import RELEASE, verify_health
    import torch
    app = create_app()
    result = {'schema_version': 1, 'commit': args.commit, 'role': args.role,
              'timestamp': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
              'proof': 'Ubuntu 24.04 amd64 local ASGI; isolated network namespace; synthetic inputs; no OCI',
              'cpu_count': os.cpu_count(), 'cpu_model': next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')), 'unknown'),
              'network_interfaces': interfaces, 'startup_seconds': time.perf_counter() - started,
              'versions': {n: importlib.metadata.version(n) for n in ['torch', 'transformers', 'huggingface-hub', 'laya']},
              'model_revision': RELEASE['model_revision'], 'cases': {}, 'performance': {}}
    assert torch.get_num_threads() == 1 and torch.version.cuda is None
    assert torch.are_deterministic_algorithms_enabled()
    assert not any(d.metadata['Name'].lower().startswith(('nvidia-', 'triton')) for d in importlib.metadata.distributions())
    auth = {'Authorization': 'Bearer ' + os.environ['LAYA_API_KEY']}
    fixtures = cases()
    with TestClient(app) as client:
        def infer(payload):
            start = time.perf_counter()
            response = client.post('/v1/systemone', json=payload, headers=auth)
            elapsed = time.perf_counter() - start
            assert response.status_code == 200, (response.status_code, response.text)
            assert elapsed < 30
            return response.json(), elapsed
        for path in ['/health', '/docs', '/openapi.json']:
            for headers in [{}, {'Authorization': 'Bearer invalid'}]:
                assert client.get(path, headers=headers).status_code == 401
        health = client.get('/health', headers=auth).json()
        verify_health(health)
        result['health'] = health
        for name, payload in fixtures.items():
            first, _ = infer(payload)
            repetitions = 0 if args.role == "restart" else 10
            for _ in range(repetitions):
                body, _ = infer(payload)
                assert body == first, 'non-determinism: ' + name
            result['cases'][name] = {'body': first, 'identical_repetitions': repetitions}
        payload = json.loads((ROOT / 'samples/typed-en.json').read_text())
        for concurrency in ([] if args.role == "restart" else [1, 2]):
            for _ in range(5): infer(payload)
            cpu_before = time.process_time()
            start = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                responses = list(pool.map(lambda _: infer(payload), range(50)))
            elapsed = time.perf_counter() - start
            latencies = sorted(r[1] for r in responses)
            result['performance'][str(concurrency)] = {
                'count': 50, 'errors': 0, 'p50_seconds': statistics.median(latencies),
                'p95_seconds': latencies[math.ceil(.95 * len(latencies)) - 1],
                'max_seconds': max(latencies), 'requests_per_second': 50 / elapsed,
                'cpu_seconds': time.process_time() - cpu_before, 'wall_seconds': elapsed}
        barrier = threading.Barrier(4)
        def burst(_):
            barrier.wait(timeout=10)
            return client.post('/v1/systemone', json=payload, headers=auth).status_code
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            statuses = sorted(pool.map(burst, range(4)))
        assert statuses == [200, 200, 503, 503], statuses
        result['burst_statuses'] = statuses
        infer(payload)
        result['post_burst_inference'] = True
    result['max_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    assert result['max_rss_bytes'] < 6 * 1024**3
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(args.role, 'passed 24 cases, repeatability, auth, offline startup, performance and burst')


def compare(baseline, candidate):
    old, new = (json.loads(p.read_text()) for p in (baseline, candidate))
    restart = json.loads(candidate.with_name('restart.json').read_text())
    assert restart['commit'] == new['commit']
    assert restart['cases'].keys() == new['cases'].keys()
    for name in new['cases']:
        assert restart['cases'][name]['body'] == new['cases'][name]['body'], 'restart changed inference'
    assert restart['health'] == new['health'], 'restart changed identity'
    maximum = 0.0
    def walk(a, b, path=''):
        nonlocal maximum
        assert type(a) is type(b), path
        if isinstance(a, dict):
            assert a.keys() == b.keys(), path
            if path.endswith('probabilities'):
                assert sorted(a, key=a.get) == sorted(b, key=b.get), path + ': rank'
            for key in a: walk(a[key], b[key], path + '/' + key)
        elif isinstance(a, list):
            assert len(a) == len(b), path
            for i, (x, y) in enumerate(zip(a, b)): walk(x, y, path + '/' + str(i))
        elif isinstance(a, float):
            delta = abs(a-b)
            maximum = max(maximum, delta)
            assert delta <= .000001, (path, a, b, delta)
        else: assert a == b, (path, a, b)
    walk(old['cases'], new['cases'])
    ratios = {}
    for concurrency in ['1', '2']:
        ratios[concurrency] = new['performance'][concurrency]['p95_seconds'] / old['performance'][concurrency]['p95_seconds']
        assert ratios[concurrency] <= 1.2, ('p95 regression', concurrency, ratios)
    report = {'passed': True, 'baseline_commit': old['commit'], 'candidate_commit': new['commit'],
              'max_absolute_numeric_delta': maximum, 'p95_ratios': ratios,
              'limits': {'absolute_delta': .000001, 'p95_ratio': 1.2, 'timeout_seconds': 30, 'rss_bytes': 6 * 1024**3}}
    candidate.with_name('comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run')
    r.add_argument('--runtime', type=Path, required=True)
    r.add_argument('--role', choices=['baseline', 'candidate', 'restart'], required=True)
    r.add_argument('--commit', required=True)
    r.add_argument('--output', type=Path, required=True)
    c = sub.add_parser('compare')
    c.add_argument('baseline', type=Path); c.add_argument('candidate', type=Path)
    args = p.parse_args()
    if args.command == 'run': run(args)
    else: compare(args.baseline, args.candidate)
