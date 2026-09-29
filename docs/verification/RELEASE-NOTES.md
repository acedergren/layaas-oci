CPU dependency and immutable-model security release. Upstream Laya and the multilingual checkpoint revisions are unchanged; API routes, authentication, response schemas and request limits are preserved.

- Torch 2.13.0+cpu, Transformers 5.10.4 and Hugging Face Hub 1.33.0.
- OCI SDK 2.187.1, cryptography 50.0.1 and pyOpenSSL 26.4.0 remove additional matched advisories found while auditing the final dependency set.
- Release-bound original/final SHA-256 manifest; root-owned read-only model bundle; verified local Agent loading, offline startup, no dynamic Hub fallback.
- Baseline/candidate Linux evidence includes 24 synthetic cases, ten repetitions per case, concurrent performance, startup/restart without networking, write-denial and overload recovery. These are compatibility measurements, not task-quality or live-deployment validation.

Assets bind this commit, runtime, OCI stack, model manifest and synthetic evidence through SHA256SUMS and release-manifest.json. Model weights and credentials are excluded. Deployments must review and explicitly adopt this release; publishing it does not upgrade existing installations.

Trust assumptions: approved release process and root administrator. This protection cannot defend against compromised root or a malicious approved source release. Read-only model copies use extra disk and hashing adds startup cost; see preparation.json and candidate.json. Preserve previous runtime/model pairs for rollback.
