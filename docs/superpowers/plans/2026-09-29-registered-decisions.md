# Registered Decisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task by task in the existing Git tree. Steps use
> checkbox (`- [ ]`) syntax for tracking. This is a plan-only handoff;
> implementation has not been requested for this turn.

**Goal:** Add one independently evaluated, authenticated, shadow-only choice
decision to the shared Layaas CPU runtime, with explicit abstention and evidence
required for any later automation.

**Architecture:** Reusable code lives in this public project. Immutable decision
definitions select a pinned inference adapter; application permissions, exact
token integrity and a versioned review policy surround it. Real definitions,
labels, feedback and deployment approvals stay private. Definition, calibration,
policy and deployment-binding hashes form a directed acyclic graph, as specified
in the design; calibration artifacts never approve themselves.

**Tech Stack:** Existing Python 3.12, FastAPI/Starlette, Pydantic, NumPy and pinned
Laya/PyTorch; JSON registry/artifacts and JSONL evaluation data; OCI Vault/systemd
credentials; existing Terraform and GitHub Actions. No registry database.

**Spec:** [Registered decisions design](../specs/2026-09-29-registered-decisions-design.md).

## Global constraints

- Base public commit: `2be952be024a2e46d7ba2b2b83a9d1ebc85baa49` (`v0.1.0`).
- Preserve upstream `9d955671415fc19f069b9cc998928075c1f255ec` and multilingual
  checkpoint/tokenizer `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`; no vendoring.
- CPU only, 32,768 body bytes, 8,000 state characters, 8 questions, 16 choice
  options, 10 score levels, 64 total options, 512 total tokens, 128 head tokens,
  2 admitted requests **across both routes**, 1 simultaneous model inference.
- Preserve experimental `/v1/systemone` compatibility and authenticated health/docs.
  Registered calls never accept model/question/policy overrides.
- First milestone is `choice` and shadow only; every successful registered
  response says `action: review`. No service-executed external actions.
- Real records, credentials and production-specific configuration never enter
  this public repository, CI output or release ZIPs. Synthetic fixtures are not
  evidence for production promotion.
- Current public stack defaults remain private E5 Flex, 1 OCPU, 8 GB RAM, 50 GB
  boot; no resize, model download at request time, upstream upgrade or live apply.

## Review focus

1. A disconnect while either route is inferring must not free shared capacity
   early; test the mixed-route four-client burst and health responsiveness (Task 3).
2. A short character string can exceed the token budget, while a question can
   lose instructions/options even with intact state; test all three losses and
   tokenizer mask-token replacement (Task 2).
3. A plausible artifact can be bound to the wrong labels, model, preprocessing or
   split; mutate each binding and prove validation/promotion fails (Tasks 1, 5, 6).
4. A translated duplicate or empty language slice can inflate reported certainty;
   test group leakage, no accepted cases and missing outcomes explicitly (Tasks 5, 7).
5. Shared origin credentials and spoofed app headers must not bypass application
   isolation, diagnostics permissions, quota or key revocation (Tasks 4, 8).

## Deliverables and dependency order

Tasks 1–4 establish the registered runtime. Task 5 establishes independent
evaluation; Task 6 adds calibration/policy evidence; Task 7 joins shadow outcomes;
Task 8 packages the complete public release. The private adoption plan runs only
after that release and the relevant data/deployment gates are approved.

| Path | Responsibility |
|---|---|
| `decisions/contracts.py`, `registry.py` | Strict types, canonical hashes, immutable definitions and artifact binding |
| `decisions/laya_adapter.py` | Pinned tokenizer/inference integration and full-precision logits |
| `decisions/runtime.py`, `admission.py` | Shared worker, lifecycle and combined request bound |
| `decisions/api.py`, `policy.py`, `calibration.py` | Registered route, review-only policy and artifact application |
| `decisions/auth.py`, `quotas.py` | Authenticated application identity, permissions, quotas |
| `evaluation/datasets.py`, `baselines.py`, `report.py` | Private dataset loading, baselines, reproducible metrics |
| `evaluation/fit.py`, `gate.py`, `feedback.py` | Calibration fitting, promotion checks, outcome joins |
| `examples/decisions/ticket-routing.json`, `tests/fixtures/decisions/` | Explicitly synthetic examples; never enabled by default |
| `scripts/evaluate_decision.py`, `fit_calibration.py`, `report_shadow.py` | Offline commands; no implicit API calls or credential loading |
| `server.py`, deployment/package files | Runtime integration and optional secure configuration |

New package directories include `__init__.py`. Generated real datasets and reports
are stored outside the checkout or in ignored private storage, never ordinary
Git-tracked paths. Artifact hashes cover canonical UTF-8 JSON (sorted object keys,
compact separators, no NaN/Infinity); ordered labels remain arrays and retain order.

### Task 1: Freeze definitions, ownership gates and the wire contract

**Files:** Create `decisions/{__init__,contracts,registry}.py`,
`examples/decisions/ticket-routing.json`, `docs/decision-owner-checklist.md`,
`tests/test_decision_registry.py`.

**Interfaces:** `load_registry(path: Path, release: Mapping) -> DecisionRegistry`;
`registry.resolve(decision_id: str, version: str) -> DecisionDefinition`;
`definition_hash(definition: DecisionDefinition) -> str`.
Define `TextDecisionInput(text: str, language: str)`, `DecisionRequest`,
`DecisionResponse`, `InputIntegrity`, `RawPrediction`, `CalibrationArtifact`,
`PolicyArtifact`, `PolicyDecision`, `DecisionBinding` and `ApplicationPrincipal`
in `contracts.py`. `DecisionBinding` references definition/calibration/policy and
acceptance-attestation hashes; the definition contains no backward artifact links.

- [ ] Write tests `test_exact_version_required`, `test_unknown_decision_rejected`,
  `test_model_and_extra_fields_rejected`, `test_label_order_changes_hash`,
  `test_definition_mismatch_fails_startup`, `test_example_is_shadow_only` and
  `test_unset_business_gates_block_promotion`. Assert request `model="multilingual"`
  is still 422; no implicit latest/model aliases; `act` policies fail startup.
- [ ] Run `python -m pytest tests/test_decision_registry.py -q`; expect failures
  for the unimplemented contract before adding implementation.
- [ ] Implement strict Pydantic models (`extra="forbid"`), deterministic hashes
  and a read-only startup registry. Initially support the named input schema
  `text-language.v1`: text 1–8,000 characters and language 2–35 characters;
  trim/case normalization of language is versioned, text is preserved exactly.
  Its JSON Schema is generated from the same model and bound into the definition.
  Arbitrary new schemas require an explicit supported schema implementation.
  Tests reject cyclic bindings and attestations whose report or artifact digest
  differs. A new binding is a new immutable release, never a mutation of old bytes.
- [ ] Freeze the synthetic example's ordered labels and one English question
  instruction for both language slices. It is a development aid only. Capture
  the owner's real workflow, labels, loss matrix, review capacity, retention and
  required slices before private data work; keep unset values promotion-blocking.
- [ ] Re-run the registry tests; expect all pass. Review the JSON request/response
  examples against the spec, including null calibration and server request IDs.
- [ ] Commit only Task 1 files: `feat: define versioned shadow decision contracts`.

### Task 2: Audit tokens and obtain unrounded model scores

**Files:** Create `decisions/laya_adapter.py`, `tests/test_decision_tokens.py`,
`tests/test_decision_logits.py`, `tests/integration/test_pinned_decision_adapter.py`.

**Interfaces:** `PinnedLayaAdapter.inspect(definition, input) -> InputIntegrity`;
`PinnedLayaAdapter.predict(definition, input) -> RawPrediction`.
`RawPrediction` contains ordered labels, unrounded logits, model/tokenizer
identities and optional diagnostic output; it grants no action permission.

- [ ] Write tests for full assembled lengths 511/512/513, shorter state budgets
  under long heads, Swedish text, decisive final sentences, negation, partial
  instruction/option loss, the 48-token option cap, collided options and literal
  tokenizer mask tokens. Assert truncated or normalized-away evidence never
  reaches the model; `input_integrity.complete` cannot be inferred from character
  length or the legacy response's `usage.input_tokens`.
- [ ] Run `python -m pytest tests/test_decision_tokens.py tests/test_decision_logits.py -q`;
  expect failures for missing adapter behavior.
- [ ] Implement read-only compatibility code against pinned `Agent._to_internal`,
  `_encode_state`, `_forward`, `laya.common.build_sequence` and `collate_items`.
  Use the loaded tokenizer, exact rendering and `torch.inference_mode()`. Verify
  full instruction/option encodings against the actually retained spans before
  state admission; literal mask-token removal yields review, not silent rewriting.
  Isolate all private upstream calls here. No global temperature/config mutation.
- [ ] Prove raw-to-legacy decoding parity using the checkpoint's effective default
  temperature and matching option order. Test that HTTP-rounded 0/1 probabilities
  cannot be substituted for raw logits and all logits must be finite.
- [ ] Run unit tests and the integration test with the **exact cached pinned CPU
  checkpoint** and `HF_HUB_OFFLINE=1`. Exact input IDs/labels must match and decoded
  rounded distributions must equal the legacy path. A missing cache or changed
  upstream interface fails this integration job; do not skip a release gate.
- [ ] Commit: `feat: audit decision input integrity and expose pinned logits`.

### Task 3: Add the review-only route with shared runtime capacity

**Files:** Create `decisions/{runtime,admission,api,policy}.py`,
`tests/test_decision_api.py`, `tests/test_shared_admission.py`; modify `server.py`.

**Interfaces:** `InferenceRuntime.submit(work: Callable) -> Future` and
`InferenceRuntime.close() -> None`; `evaluate_registered(request, definition,
principal, runtime) -> DecisionResponse`; `review_policy(raw: RawPrediction | None,
integrity: InputIntegrity, validated_calibration: CalibrationArtifact | None,
policy: PolicyArtifact) -> PolicyDecision`.
Register the exact route defined in the spec. Middleware owns combined admission
and protected task lifetime, including pre-body-read acquisition.

- [ ] Write tests for 200 review-only responses, 400 malformed JSON, 404 unknown
  decision/version, 413 streamed-body cap, 422 overrides/schema errors, null answer
  on truncation/unsupported language, null calibration and a generated request ID.
  An internal/authenticated principal stub is allowed in tests only. Production
  registered calls stay disabled/denied until Task 4 authenticates an application.
- [ ] Write a synchronized mixed legacy/registered four-client test: two admitted,
  two 503, no more than one model forward at any time; cancelling either admitted
  client retains its slot until work finishes. Health must remain responsive and
  shutdown must drain safely. Test oversized/slow body behavior under the same cap.
- [ ] Run the two new test modules; verify the expected failures, then implement
  one model executor shared by both paths. Have legacy `FixedRouter.predict`
  dispatch through it; preserve upstream route validation/response behavior.
  Wrap the existing lifespan rather than losing upstream executor cleanup.
- [ ] Enforce review-only policy and sanitize errors. Registry/model/invalid
  artifact failures fail startup, not fallback to the sample. Keep raw output
  separate from calibrated probability and never copy upstream action signals.
- [ ] Run new modules plus `tests/test_server.py tests/test_runtime.py`; expect
  passes and no regression in existing limits, cancellation, auth or health.
- [ ] Commit: `feat: serve registered decisions in shadow mode`.

### Task 4: Authenticate applications and bound their use

**Files:** Create `decisions/{auth,quotas}.py`, `tests/test_application_auth.py`,
`tests/test_application_quotas.py`; modify `server.py`, `decisions/api.py`.

**Interfaces:** `authenticate_application(headers, credentials) -> ApplicationPrincipal`;
`authorize(principal, decision_id, version, diagnostics: bool) -> None`;
`ApplicationQuota.acquire(principal, now: float) -> Lease`.
Principals carry application ID, explicit version permissions and quota settings.

- [ ] Write tests for origin-only/unknown/revoked/duplicate credentials, spoofed
  application IDs and forwarded identity headers, unauthorized decision versions
  and diagnostic access. Assert 401/403, no body reads before authentication,
  and no identity-bearing secret in errors or captured logs.
- [ ] Write monotonic fake-clock tests for token-bucket refill, burst, per-app
  in-flight limits, isolation between two apps, 429/`Retry-After`, completion and
  disconnect release. Combined global admission remains two. Document reset on
  restart; quota rejection must not leak an admission lease.
- [ ] Run these tests to show failure; implement the header/credential mapping
  from the spec with constant-time digest matching and startup validation.
  No credential literals in public example definitions; no default application
  derived from the origin key. Keep legacy-only operation when registry disabled.
- [ ] Re-run Task 3/4 tests together; verify 401, 403, 429 and 503 remain distinct.
- [ ] Commit: `feat: isolate registered decisions by application`.

### Task 5: Build the labelled-data and baseline evaluation pipeline

**Files:** Create `evaluation/{__init__,datasets,baselines,report}.py`,
`scripts/evaluate_decision.py`, `tests/test_decision_evaluation.py`,
`tests/fixtures/decisions/definition.json`, `tests/fixtures/decisions/dataset.jsonl`,
`tests/fixtures/decisions/split-manifest.json`;
add the dataset/label guide to `docs/decision-owner-checklist.md`.

**Interfaces:** `load_dataset(path, split_manifest, definition) -> DecisionDataset`;
`evaluate_decision(runner, dataset, definition) -> EvaluationReport`;
`RulesBaseline.predict(input) -> BaselinePrediction`.
Rows include `case_id`, `group_id`, split, language, input, adjudicated label or
`must_review`, challenge tags and provenance class. Sources/records stay private.

- [ ] Write tests for overlapping group/translation IDs, duplicate records,
  unknown labels, mixed definition hashes, missing language/split/provenance,
  nonfinite outputs, ambiguous cases, empty slices and inference failures. A
  skipped/error case remains in attempted counts; it cannot improve coverage.
- [ ] Run evaluation tests, verify failures, then implement dataset binding to
  Task 1 definitions and the four fixed partitions in the spec. Naturalistic
  samples and challenge cases have separate denominators. Hash input/split files;
  do not log examples when validation fails.
- [ ] Wrap `laya.evals` for its existing metrics using the same adapter and exact
  512/128 preprocessing as serving; never trust an unpinned/default CLI runner.
  Add deterministic rules plus majority reference. Develop rules only on the
  development split; ties/no match review. Compare identical cases/definitions.
- [ ] Report confusion, slice counts, errors, review rate, risk/coverage and
  per-case cost including review, alongside upstream metrics. Include runtime,
  model, definition and dataset/split digests, failure counts and timing context.
- [ ] Run synthetic fixture pipeline; assert deterministic metrics and
  `evidence_class: synthetic`, `promotion_eligible: false`. Provide offline CLI
  exit codes 0 success, 1 unmet gate, 2 invalid input/configuration.
  Contract: `python scripts/evaluate_decision.py --registry <directory>
  --decision-id <id> --decision-version <version> --dataset <jsonl>
  --splits <manifest> --split <development|calibration|policy|test>
  --output <report-directory>`. Definition and binding select model/budgets;
  add no model override or implicit remote service call.
- [ ] Commit: `feat: evaluate registered decisions against rule baselines`.

### Task 6: Fit calibration and enforce evidence-bound policies

**Files:** Create `decisions/calibration.py`, `evaluation/{fit,gate}.py`,
`scripts/fit_calibration.py`, `tests/test_decision_calibration.py`,
`tests/test_decision_quality_gate.py`; modify `decisions/policy.py`.

**Interfaces:** `fit_temperature(logits, labels, bindings) -> CalibrationArtifact`;
`calibrate(logits, artifact) -> ndarray`; `select_policy(report, owner_limits) -> PolicyArtifact`;
`check_quality(report, baseline, artifacts, owner_limits) -> GateResult`.
The core gate is offline. The initial online policy still cannot emit `act`.

- [ ] Write deterministic raw-logit fixtures proving positive-temperature
  softmax, finite normalization, label-order preservation, fitting only the
  calibration split, and failure on rounded-probability substitutes. Include
  miscalibrated synthetic scores that demonstrate a measured calibration change.
- [ ] Write gates for every bound-hash mismatch, missing cost/coverage/reviewer
  limits, synthetic-only data, reused final test, missing slice, zero accepted
  cases, error costs worse than baseline, failed confidence bounds and pending
  labels. Test `probability=0.99` never authorizes action in shadow mode.
- [ ] Run tests to fail; fit one positive scalar temperature by minimizing NLL
  in log-temperature space with deterministic optimizer settings recorded in
  the artifact. Keep fitting tools out of the serving image where practical.
  A provisional fit remains unvalidated online. Do not select thresholds on
  calibration or final-test partitions.
- [ ] Implement threshold selection on policy data, the spec's final independent
  slice/error/cost checks, explicit insufficient-evidence outcomes and complete
  provenance. Freeze gate definitions before looking at final-test labels.
  Distinguish an accepted quality artifact from permission to leave shadow mode.
- [ ] Re-run calibration/gate/evaluation tests; validate report math against
  independently calculated small fixtures, including zero denominators and
  simultaneous slice gates. Record deterministic seeds for cost resampling.
- [ ] Commit: `feat: bind calibration and review policy to quality evidence`.

### Task 7: Join outcomes and report shadow quality

**Files:** Create `evaluation/feedback.py`, `scripts/report_shadow.py`,
`tests/test_shadow_feedback.py`, `docs/shadow-integration.md`;
modify `decisions/api.py` for safe response/log metadata and `examples/client.py`
for the new opt-in request contract.

**Interfaces:** `join_outcomes(predictions, outcomes) -> ShadowDataset`;
`summarize_shadow(dataset, owner_limits) -> ShadowReport`.
Outcomes join by server-generated request ID and immutable artifact identities.

- [ ] Write tests for duplicate/corrected outcomes, unknown request IDs, mismatched
  versions, delayed/missing labels and biased reviewed-only samples. Missing
  labels are not successes; all shadow traffic is accounted for in report counts.
- [ ] Run tests to fail; implement an offline JSONL join and report with per-app
  and decision/version slices, review load, error/cost, unsupported/truncated
  rates, overload and missing-outcome rate. No feedback endpoint/database.
- [ ] Add an application walkthrough that runs beside existing routing, stores
  records only in its approved private store, and takes no actions from the API.
  Include data retention and owner review steps; no automatic notification task.
- [ ] Capture logs for success, schema rejection and injected inference errors;
  assert no input, raw output or key values appear. Check diagnostic permission
  and that returned raw model output is explicitly not an explanation.
- [ ] Re-run Task 7 and auth tests; commit: `feat: report shadow decision outcomes`.

### Task 8: Package and verify a deployable public runtime

**Files:** Modify `main.tf`, `variables.tf`, `schema.yaml`, `outputs.tf` as needed,
`cloud-init.yaml.tftpl`, `deploy/{fetch_secret.py,bootstrap.sh,layaas-api.service}`,
`scripts/package_stack.py`, `.github/workflows/verify.yml`, `API.md`, `README.md`,
`DEPLOYMENT.md`, `SECURITY.md`, `ARCHITECTURE.md`; extend
`tests/{test_vault_secret,test_stack_package,test_stack_safety,test_cloud_init}.py`.

**Interfaces:** Existing stack stays valid with registry disabled. New optional
`application_credentials_secret_ocid` is a reference only, requiring an equally
narrow secret-specific IAM rule when set. Installed registry files and artifact
digests must be explicitly configured; no public demo enabled automatically.
`enable_registered_decisions` defaults to false. For opt-in deployments, accept
an operator-supplied non-secret bundle through
`scripts/package_stack.py <private-output.zip> --decision-bundle <bundle.json>`;
include it at `config/decision-bundle.json` and install it read-only. It contains
definitions/bindings/artifacts, never credentials, datasets or predictions.
The default public release ZIP omits this bundle. An enabled stack without it
fails validation. Owners upload customized bundles only to their private stack;
configuration and Terraform state may reveal their decision rules.

- [ ] Add failing tests that package every new runtime module; no customer
  definition, dataset, reports, secret values or evaluator-only dependencies
  enter the public release stack. Validate disabled-registry backward compatibility and failure
  when enabled without a complete credential/definition/artifact set.
  Test opt-in bundle schema/digests, safe fixed archive paths and cloud-init payload
  limits; never weaken those limits to fit a large definition bundle.
- [ ] Extend the secret adapter to atomically validate/write the optional JSON
  credential mapping with root-only permissions, then use systemd credentials.
  Test malformed JSON, IAM propagation failures, wrong secret content, restart
  rotation and denial of the old app key. Never add a credential value variable.
- [ ] Run all Python tests, compilation, shell syntax, Terraform fmt/init/validate
  and stack ZIP/cloud-init checks from `AGENTS.md`. Add an Ubuntu pinned-model
  integration job for Task 2, with no tenancy credentials and no production data.
- [ ] Assess open dependency advisories against the exact lock and loaded paths;
  record remediation or reviewed exceptions before release. At planning time,
  seven Torch/Transformers alerts were open, three high. No applicability review
  was performed here. If a fix requires changing the pinned baseline, do that in
  a separate prerequisite change and rerun adapter parity and affected evaluation.
- [ ] Confirm both route families under one cached model, exact model/device
  health, mixed overload and restart recovery in a clean Linux environment.
  Label Linux smoke evidence separately from any subsequent OCI measurements.
- [ ] Update API/deployment docs to distinguish shipped behavior, accepted
  calibration, synthetic examples and future automatic action. Publish only
  after checks pass; choose the next unused version at execution time and pin
  its commit/artifact in the private deployment plan. No Terraform apply in CI.
- [ ] Commit: `feat: package the registered shadow runtime for OCI`.

## Gates and completion checklist

| Gate | Required evidence | What it allows |
|---|---|---|
| G0: product/data contract | Named owner, actual taxonomy, labels/data approval, costs, review capacity, retention and slices | Representative dataset work and private application integration |
| G1: engineering | Tasks 1–4 and 8 pass; pinned Linux adapter, shared admission and dependency-advisory disposition recorded | A deployable shadow runtime, with synthetic-only claims until G0/G2 |
| G2: independent quality | Tasks 5–6 frozen final report, baseline, calibration, risk/coverage and slice gates | Accept/reject the candidate for a controlled shadow trial |
| G3: shadow rollout | G0/G1/G2 disposition recorded, owner-approved exact rollout and recovery checks; Task 7 outcomes | Learn from real workflow behavior while the current process retains decisions |
| G4: automatic action | Sufficient shadow outcomes, pre-agreed quality/cost/capacity gates, exact owner approval and a separately reviewed act-mode implementation | Future constrained automation; explicitly outside this milestone |

A failed G2 may justify an owner-approved research shadow trial, but it stays
labelled unvalidated and has no automatic-action path. Local contracts and a
synthetic round trip never count as passing G0, G2 or G3.

- [ ] Each task has a focused commit and its stated tests pass.
- [ ] Public release contains reusable code and synthetic examples only.
- [ ] Exact public release is recorded in the separate private rollout package.
- [ ] Model utility and engineering completion have separate reported statuses.
- [ ] No infrastructure mutation, real-data processing or action-mode promotion
  is implied by completion of this plan.

## Plan preparation evidence

Prepared 2026-09-29 from the public base above and the exact pinned upstream
source. The current upstream default branch resolved to the same pinned source
commit when checked; no dependency refresh is needed for `laya.evals`.
The existing 42 public tests passed locally and its latest release CI was green.
No model-quality experiment, cloud inference call or deployment was performed
while preparing this plan. All implementation checkboxes intentionally remain open.
