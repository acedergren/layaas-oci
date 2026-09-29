"""Query OSV for the exact runtime lock; store only public dependency metadata."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import urllib.request

root = Path(__file__).resolve().parents[1]
lock = (root / 'requirements-linux.lock').read_text()
packages = [(name, version) for name, version in re.findall(r'^([\w-]+)==([^\s]+)$', lock, re.M)]
# Local +cpu wheel uses the same security version as the base Torch release.
queries = [{'package': {'name': name, 'ecosystem': 'PyPI'}, 'version': version.split('+')[0]} for name, version in packages]
queries.append({'package': {'name': 'laya', 'ecosystem': 'PyPI'}, 'version': '0.3.21'})
request = urllib.request.Request('https://api.osv.dev/v1/querybatch', data=json.dumps({'queries': queries}).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=60) as response:
    results = json.load(response)['results']
report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'source': 'https://api.osv.dev/v1/querybatch',
          'scope': 'Published OSV advisories matching exact PyPI versions; not proof of absence of vulnerabilities',
          'packages': [{'package': q['package']['name'], 'version': q['version'], 'vulnerabilities': r.get('vulns', [])} for q, r in zip(queries, results)]}
Path(sys.argv[1]).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
findings = [(p['package'], v['id']) for p in report['packages'] for v in p['vulnerabilities']]
print(json.dumps({'packages_checked': len(queries), 'findings': findings}))
if findings:
    raise SystemExit('Release blocked: review unresolved advisories before publication')
