# Contributing

Keep the public/private repository boundary intact. Do not submit production
configuration, evidence, real customer data, credentials, private IPs or OCI
resource IDs. Use synthetic examples only. Report vulnerabilities privately via
GitHub's Security tab.

## What belongs in Git

Track source, Terraform and cloud-init templates, both dependency lockfiles,
`release.json`, documentation/plans, brand assets and synthetic samples/fixtures.
Keep `.terraform.lock.hcl`: it pins the provider used to reproduce the stack.

Ignore local environments/caches, build/coverage output, editor recovery files,
`.env` variants, Terraform state/plans/real variable files and runtime credentials.
Sanitized `.env.example` and `*.tfvars.example` files remain eligible for review.
Do not add blanket `*.json`, `*.jsonl`, `*.csv`, `*.md` or `*.lock` exclusions.

Store real labels, predictions and feedback in approved storage outside the
checkout. If local staging is authorized, use ignored `work/private/`. The root
`data/`, `datasets/`, `reports/`, `predictions/`, `feedback/`, `decision-bundles/`
and `config/private/` directories are also ignored. Keep downloaded model files
in a cache or ignored `models/`/`checkpoints/`. The operator-specific
`config/decision-bundle.json` is ignored; synthetic examples belong in `examples/`
or `tests/fixtures/`. All live `evidence/` stays outside this public repository.

`.gitignore` filters untracked paths, not file contents, and does not remove
already tracked files. Inspect `git diff --cached` and retain secret scanning;
do not use `git add -f` to work around a private-data rule. Ignored files still
need appropriate storage permissions and retention.

The pinned Linux runtime lock targets Ubuntu 24.04 amd64 and Python 3.12. In that
environment:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-linux.lock
python -m pip install -r requirements-test.txt
python -m pytest -q
python -m compileall -q server.py release.py deploy examples scripts tests
bash -n deploy/bootstrap.sh
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
python scripts/package_stack.py /tmp/layaas-oci-stack.zip
git diff --check
```

Terraform validation and CI never authenticate to OCI or apply infrastructure.
Explain behavior changes, tests, IAM/network impact, and recovery considerations
in pull requests.
