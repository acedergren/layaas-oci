# Dependency disposition

The final exact-version OSV batch report is `dependency-audit.json`. It contains
65 runtime package queries (including pinned upstream Laya 0.3.21), with zero
matching published advisories at its timestamp. CI repeats the query and blocks
on any match or lookup failure. Absence from OSV is not proof of vulnerability
absence, and this is not a full application penetration test.

The initially requested inference versions resolve the seven previously reported
Torch/Transformers advisories: GHSA-xrqw-3rrv-vx5w, GHSA-rrmf-rvhw-rf47,
GHSA-fgcw-684q-jj6r, GHSA-29pf-2h5f-8g72, GHSA-qfhq-4f3w-5fph,
GHSA-vgrw-7cvw-pwgx and GHSA-69w3-r845-3855. Transformers 5.10.0 is yanked and is
not used. Upstream and model SHA revisions remain unchanged.

Auditing the complete candidate additionally matched cryptography 44.0.3 and
pyOpenSSL 24.3.0, constrained by OCI SDK 2.160.0. No risk exception was accepted.
OCI SDK 2.187.1 permits cryptography 50.0.1 / pyOpenSSL 26.4.0; these pins remove
all matched findings, including GHSA-537c-gmf6-5ccf, GHSA-g6cj-pr64-35w5,
GHSA-jwv3-5hgf-82ww, GHSA-m959-cc7f-wv43, GHSA-r6ph-v2qm-q3c2,
GHSA-5pwr-322w-8jr4 and GHSA-vp96-hxj8-p424 (and OSV PYSEC aliases).

Sources: [OSV API](https://google.github.io/osv.dev/api/),
[OCI SDK package metadata](https://pypi.org/pypi/oci/2.187.1/json),
[cryptography metadata](https://pypi.org/pypi/cryptography/50.0.1/json),
[pyOpenSSL metadata](https://pypi.org/pypi/pyopenssl/26.4.0/json).
The resolver command is recorded in `requirements-linux.lock`; compatible
previous constraints are preserved in `requirements-constraints.txt`. Linux CI
checks pip consistency and exact runtime versions and rejects GPU packages.
