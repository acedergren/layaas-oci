# Secure CPU dependency upgrade implementation plan

Accepted 2026-09-29. Owner: Alex. Goal: verified public patch release and a reviewable private adoption package; no production changes.

## Constraints

Retain upstream 9d955671415fc19f069b9cc998928075c1f255ec and multilingual model revision 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851. Pin Torch 2.13.0+cpu, Transformers 5.10.4 and huggingface-hub 1.33.0 on Python 3.12 / Ubuntu 24.04 amd64. Retain API/auth/limits and one CPU worker. No model weights, credentials, live evidence or production identifiers in this public repository. No VM/cloud/credential access. Use existing checkout and focused commits.

## Deliverables and progress

- [ ] 1. Clean pinned model retrieval, raw/final SHA-256 manifest and updated dependency lock/release identity; advisory disposition.
- [ ] 2. Staged, verified, root-owned read-only model preparation; local Agent plus Router.attach loader; packaging/bootstrap/service updates and negative security tests.
- [ ] 3. Ubuntu installation, root ownership/write-denial, offline startup/restart, API regression and real baseline/candidate acceptance in CI.
- [ ] 4. Independent final review, immutable public patch release/runtime/stack/evidence SHA-256; private reviewed extraction/adoption/rollback package committed and pushed.

## Acceptance

The manifest is reviewed release input, never generated as a trust decision on an operator machine. Exactly five model files are copied (weights, agent config, encoder config, tokenizer JSON/config); raw and known normalized tokenizer variants are bound to the release. Preparation normalizes only through pinned upstream code, verifies output, removes links and publishes atomically under /opt/laya/models. Root owns immutable files/directories; the inference user cannot write or change parent entries. Runtime verifies complete contents and permissions before Agent load and reports revision only afterward. No network fallback or global monkeypatch. Original cache remains available for rollback.

Run existing contract/stack tests plus malformed/tampered/missing/link/cache-migration/interrupted-preparation and credential/admission/cancellation tests. Test actual startup and a second fresh process with networking blocked, using both old-format and fresh cache. Verify no model writes and bounded admission.

Compare 24 synthetic cases: en/sv x choice/score/noul x ordinary/negated/ambiguous/long; unchanged schema, answer and rank; probability absolute delta <=1e-6; ten identical repetitions per case. Measure 50 warmed requests at concurrency 1 and 2 for old/new on the same Linux runner; zero errors, all <30 seconds, candidate p95 <=1.2 baseline, process memory <6 GiB. Report CPU, throughput, startup/preparation, memory and disk. Synchronized four-client burst: two 200, two 503, subsequent inference healthy. Never relax gates automatically.

Pin CI actions by commit. Model tests have no production secrets. Release only allowlisted runtime/stack files and sanitized evidence, bound to commit and digests; no weights in artifacts. Verify installed dependencies are CPU-only. Review final dependency advisories. Retain precise failures as evidence.

Private package pins public runtime commit/digest, verifies before safe extraction, separates runtime/model versions and documents preflight, atomic activation, readiness, rollback and later live acceptance. No live checks or deployment in this goal. Completion requires published green release and pushed private package, explicitly leaving production on its previous version.

## Execution ledger

- Start: both repositories clean; public base 0f7767f, private base 025430d. Earlier Mac diagnostic proves potential parity only; unchanged Hub 1.33/1.32 startup fails offline with old cache.
- Ruling: work in existing single Git trees as explicitly approved, overriding the execution skill worktree default. Public publishing and private package push are explicitly within the accepted plan.
