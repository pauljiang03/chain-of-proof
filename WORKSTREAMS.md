# Workstreams and terminal handoff

Updated: 2026-11-15 UTC. Read this before assigning more agents.
The project is CONAN-F. The `cop` command and `ChainOfProof` Lean library retain their names for compatibility.

## Current ownership

| Owner | State |
|---|---|
| Root Codex | Integrates tested changes and pushes main. Latest worktree: `/private/tmp/cop-answer-meaning`, branch `fix/answer-meaning`. |
| Other Codex terminal | Completed coverage, reader and comparison work. Frozen A/B/C results and audits are retained; no production-file ownership. |
| Claude | Independent checker, rename, desktop, proof graph and report builder are integrated. Check for new work before assigning UI tasks. |
| Root helpers | Shared projection, census, reference review, UI correctness review and common-field schema fix are complete. No active implementation ownership. |

See [FINAL_EVAL_HANDOFF.md](FINAL_EVAL_HANDOFF.md) for the five priorities and [TASKS.md](TASKS.md) for remaining work.
The six backend interfaces remain in [BACKEND_HANDOFF.md](BACKEND_HANDOFF.md).
App and feature interfaces remain in [APP_HANDOFF.md](APP_HANDOFF.md) and [FEATURE_HANDOFF.md](FEATURE_HANDOFF.md).

## Latest implementation

The three incorrect answers were traced to narrow verified observations used as stronger answers. Optional public claim-role requirements, early evidence-need diagnostics and a separate unscored diagnostic profile are integrated. See [the diagnosis](docs/INCORRECT_ANSWER_DEBUG.md). Original benchmark inputs, frozen results and unannotated contract behavior are unchanged. This is declared-role compatibility, not Lean proof of question entailment.

## Latest measured state

[The latest comparison](comparison/ablation/RESULTS_SOL61_20261115.md) is frozen at clean `c2b9753` with requested Sol 6.1, one A run then one C run, each capped at 900 seconds. B replays A exactly without another model call.

- A/B: 8 complete, 20 partial, 16 unanswered and 2 incorrect questions.
- C: 7 complete, 21 partial, 15 unanswered and 3 incorrect questions.
- Each has 14 unresolved reference questions, retained in the 60-question result.
- B reverified 63/63 certificates; C reverified 96/96. There was no demonstrated semantic-predicate refusal.
- The frozen exporter dropped A120/C96 fields at public `anyOf` schemas. A67/C43 concern scorable questions. A later common-field fix has no new accuracy score.
- Code after the trial also contains Claude's UI and reviewed fixes for citation identities and stale previews.
- Final combined regression suite: 775 tests run, 774 passed and one platform test skipped.

This pair showed no overall answer-accuracy advantage from Lean feedback. The older literal-answer pilot uses a different answer channel and is not a direct improvement comparison. Keep both frozen; never hand-write retrospective bindings.

## Inputs and retained outputs

Latest NIST facts: `/private/tmp/cop-nist-final-20261115T020159Z/evidence/facts.json`.
SHA-256: `a79fcce1015bf73a66779557a6d5235b4ee4d4b1bc9683803cff5f1abc0f5c8d`.
There are 335,509 records, including 11 email records and 32 system settings. All 12 reader/exhibit attempts completed. Nine unsupported shell targets and the dirty Search database remain limitations. Extraction took 55.96 seconds; its clean `8a625fc` launch and input/source hashes are retained beside the facts.

- Public case: `comparison/mulder/case-profile.json`.
- Public prompts and schema: `eval/QUESTIONS.md`, `eval/benchmark_nist_questions.json`.
- Private reference: `eval/benchmark_nist.json`, scorer only after investigation stops.
- Scored archive: `runs/dev/sol61-nist-v2-20261115T0217Z/`.
- Frozen comparison runtime: `/private/tmp/cop-sol61-smoke-runtime` at `c2b9753`.

Second-case facts: `/private/tmp/cop-case2-final-20261115T015403Z/evidence/facts.json`.
SHA-256: `0a4d2243adbe10b33eaff335fdc7bbd8be901e55cb3a1bd20f01089437361e61`.
This is a desktop-only, 1,800-record snapshot with `windows,system` readers and four documented intake issues. It excludes server, memory and network captures.

The mechanical workflow retained 12 independently verified certificates, reports and a portable package in `runs/dev/case2-workflow-20261115T015403Z/`. The live Sol smoke passed all 11 operational checks and retained 34/34 C and 10/10 B verified certificates in `runs/dev/sol61-smoke-20261115T0209Z/`. There is no second-case accuracy key.

## Measurement and integration rules

New workstream: official NIST CFReDS Hacking Case, isolated at `/private/tmp/cop-nist-hacking` on `feature/nist-hacking-case`. Root owns integration, image/scan readers, host attributes and generic subset scoring. `optical_timestamps` delivered the legacy app/browser/traffic/recycle readers and EVT reader. `lean_gap_types` delivered fixed-role typed attributes, joins, digest comparison and kernel tests. `journal_gaps` authored the separate 31-question reference and source audit. Only that reference author read the published answer key.

The first Data Leakage repeat continues in the other terminal on frozen `96cd518`: A then C, 900 seconds each, followed by exact B and the separate 240-second role diagnostic. The new Hacking code must not enter that runtime or mutate its environment. Root integrates public documentation after the coordinator retains the results.

The Hacking intake has been exercised on the official E01 image. All 31 questions have deterministic contracts. Three stronger meanings lack a proof rule; current DBX subscription state lacks a reader. All remain visible. Supporting a dataset does not establish complete answers or zero false positives.

Do not use an LLM judge. Do not give investigators the private reference, review notes, scored reports or another arm's outputs. Preserve failures and unknowns. Freeze new code and inputs for any new experiment; do not overwrite saved evidence or repair a measured submission.

Lean proves the declared formal statement relative to extracted records and rules. It does not prove parser correctness, relevance, complete lists, source authenticity or universal zero false positives. The shared exporter preserves claim values and reports unsupported fields. Question placement remains the investigator's responsibility.

The original 60-question reference remains unchanged. The separate Q53 metadata derivative is not a silent replacement. Both Mulder packages are prepared and unrun. The full A/B/C/D experiment remains incomplete.

The local Claude login works. Automatic approval review blocked the proposed native Claude test under the user's Sol-only instruction before execution. Do not send selected evidence to Claude.ai without destination approval. The external Sol bridge is not validation of the native product backend. Never copy credentials into chat or Git.

Use isolated worktrees and agree on ownership before editing shared files. Inspect main before merging because another terminal may advance it. Preserve completed work; resolve routine conflicts without resetting another agent's branch.
