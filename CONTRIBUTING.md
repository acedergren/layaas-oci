# Contributing

Keep the public/private repository boundary intact. Do not submit production
configuration, evidence, real customer data, credentials, private IPs or OCI
resource IDs. Use synthetic examples only. Report vulnerabilities privately via
GitHub's Security tab.

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
