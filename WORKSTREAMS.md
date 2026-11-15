# Workstreams and terminal handoff

Updated: 2026-11-15 UTC. Read this before assigning more agents.
The project is CONAN-F. The desktop app is Conan; `conan` opens it. The `cop` command and `ChainOfProof` Lean library retain their names for compatibility.

## Current ownership

| Owner | State |
|---|---|
| Root Codex | Integrates tested changes and pushes main. Owns readers, checker/Lean source semantics, docs/UI and final integration. Active fixes: `/private/tmp/cop-evidence-meaning`, branch `fix/evidence-meaning`. |
| Other Codex terminal (`01a1dc3d`) | Strict field policy and durable checkpoints are complete. Owns answer-row relationships and the separate strict 60-question public contract in `/private/tmp/cop-strict60-public`, branch `fix/strict60-public`. |
| UI integration terminal (`01a1dd77`) | Desktop merge is complete and pushed as b7d254e: replay, case time display, report layout and graph colors. Its focused suite passed 46 tests; the full UI checkpoint ran 854 tests (843 passed, 11 dependency skips). Root now owns main integration. Claude supplied the desktop branch. |
| Root helpers | Binary metadata and journal fixes are complete. `optical_timestamps` now owns execution-attribute reader emission; `lean_gap_types` owns its fixed roles, Lean predicates and source sentences. `journal_gaps` is idle. |

See [FINAL_EVAL_HANDOFF.md](FINAL_EVAL_HANDOFF.md) for the five priorities and [TASKS.md](TASKS.md) for remaining work.
The six backend interfaces remain in [BACKEND_HANDOFF.md](BACKEND_HANDOFF.md).
App and feature interfaces remain in [APP_HANDOFF.md](APP_HANDOFF.md) and [FEATURE_HANDOFF.md](FEATURE_HANDOFF.md).

## Latest implementation

The completed source/answer/checkpoint batch passed 913 tests (912 passed, one platform skip). See [the retained validation and remaining gaps](docs/CORRECTNESS_FIXES.md). New model experiments are held while the row-relationship and execution-source follow-ups are checked.
The Hacking C-only pilot was prepared but never dispatched. Its frozen runtime and
manifest are preparation artifacts, not a completed or running test.

Ownership above is final; it supersedes earlier crossed terminal proposals. Root
does not edit `agent/answer_*`, the other terminal's public contract, or the ablation
protocol. The other terminal does not edit readers, checker roles/sentences or Lean.
Helpers use their owner's isolated worktree and do not modify frozen evidence or runs.

The three incorrect answers were traced to narrow verified observations used as stronger answers. The product now requires explicit public field meanings. The new v3 comparison protocol adds the same public preview for A/C and durable investigator-authored checkpoints. The original 60-question contract and all frozen results stay unchanged; v3 refuses that unannotated contract before a model starts. The derivative contract is still under public-only review. Per-field compatibility does not establish that several fields describe the same event, subject or source scope; the other terminal owns that follow-up. Root owns the source-sensitive distinction between an application sighting and an execution-artifact attribute. See [the diagnosis](docs/INCORRECT_ANSWER_DEBUG.md).

## Latest measured state

The [latest Data Leakage repeat](comparison/ablation/RESULTS_SOL61_POSTFIX_20261115.md)
is frozen at clean `96cd518` with requested Sol 6.1,
A then C, each capped at 900 seconds. B replays A exactly without another model call.

- A/B: 7 complete, 22 partial, 16 unanswered and 1 incorrect question.
- The reference still has 46 scorable and 14 unresolved questions out of 60.
- A/B matched 544 of 1,627 scorable atoms, with 2,644 extra and 99 unequal assertions.
- B verified 84 candidates and refused three malformed candidates; its answers are unchanged.
- C stopped at its deadline without a final binding document. Accuracy is unavailable.
- All 84 B and 1,017 C certificates passed independent replay. Claim count is not accuracy.
- The separate 240-second, three-question meaning diagnostic passed its operational audit.
  All 21 certificates reverified. It retained narrow observations and left stronger fields empty.
  The agent made no incompatible bindings; no actual guard intervention was observed.

The [earlier completed comparison](comparison/ablation/RESULTS_SOL61_20261115.md)
remains frozen at `c2b9753`. It showed no overall answer-accuracy advantage from Lean
feedback. The latest repeat cannot supply an A/C accuracy comparison because C has
no final submission. Never hand-write retrospective bindings.

Hacking integration passed 834 regression tests (833 passed, one platform skip).
The final real-image mechanical workflow has 11,939 records and 58 certificates;
all passed independent replay, con-leche and portable-package verification.
This is workflow validation, not model answer accuracy. The model/scorer runtime is
frozen at `08c7ce1`; the later `3da5c93` only adds a package toolchain fingerprint.

## Inputs and retained outputs

Latest NIST facts: `/private/tmp/cop-nist-final-20261115T020159Z/evidence/facts.json`.
SHA-256: `a79fcce1015bf73a66779557a6d5235b4ee4d4b1bc9683803cff5f1abc0f5c8d`.
There are 335,509 records, including 11 email records and 32 system settings. All 12 reader/exhibit attempts completed. Nine unsupported shell targets and the dirty Search database remain limitations. Extraction took 55.96 seconds; its clean `8a625fc` launch and input/source hashes are retained beside the facts.

- Public case: `comparison/mulder/case-profile.json`.
- Public prompts and schema: `eval/QUESTIONS.md`, `eval/benchmark_nist_questions.json`.
- Private reference: `eval/benchmark_nist.json`, scorer only after investigation stops.
- Latest repeat archive: `runs/dev/sol61-nist-postfix-20261115T0316Z/`.
- Separate diagnostic archive: `runs/dev/sol61-meaning-diagnostic-20261115T0316Z/`.
- Frozen repeat runtime: `/private/tmp/cop-sol61-96cd518-runtime` at `96cd518`.
- Earlier completed comparison archive: `runs/dev/sol61-nist-v2-20261115T0217Z/`;
  its runtime remains `/private/tmp/cop-sol61-smoke-runtime` at `c2b9753`.

Separate DFIR Madness facts: `/private/tmp/cop-case2-final-20261115T015403Z/evidence/facts.json`.
SHA-256: `0a4d2243adbe10b33eaff335fdc7bbd8be901e55cb3a1bd20f01089437361e61`.
This is a desktop-only, 1,800-record snapshot with `windows,system` readers and four documented intake issues. It excludes server, memory and network captures.

The mechanical workflow retained 12 independently verified certificates, reports and a portable package in `runs/dev/case2-workflow-20261115T015403Z/`. The live Sol smoke passed all 11 operational checks and retained 34/34 C and 10/10 B verified certificates in `runs/dev/sol61-smoke-20261115T0209Z/`. There is no second-case accuracy key.

## Measurement and integration rules

New workstream: official NIST CFReDS Hacking Case, isolated at `/private/tmp/cop-nist-hacking` on `feature/nist-hacking-case`. Root owns integration, image/scan readers, host attributes and generic subset scoring. `optical_timestamps` delivered the legacy app/browser/traffic/recycle readers and EVT reader. `lean_gap_types` delivered fixed-role typed attributes, joins, digest comparison and kernel tests. `journal_gaps` authored the separate 31-question reference and source audit. Only that reference author read the published answer key.

The Data Leakage repeat and its separate role diagnostic have stopped and their results are retained. The Hacking C-only pilot was prepared but never dispatched. Its old frozen runtime is not the new v3 protocol. A future trial needs a new freeze after the current correctness work and public-contract review pass; no model experiment is running.

The Hacking intake has been exercised on the official E01 image. All 31 questions have deterministic contracts. Three stronger meanings lack a proof rule; current DBX subscription state lacks a reader. All remain visible. Supporting a dataset does not establish complete answers or zero false positives.

Do not use an LLM judge. Do not give investigators the private reference, review notes, scored reports or another arm's outputs. Preserve failures and unknowns. Freeze new code and inputs for any new experiment; do not overwrite saved evidence or repair a measured submission.

Lean proves the declared formal statement relative to extracted records and rules. It does not prove parser correctness, relevance, complete lists, source authenticity or universal zero false positives. The shared exporter preserves claim values and reports unsupported fields. Question placement remains the investigator's responsibility.

The original 60-question reference remains unchanged. The separate Q53 metadata derivative is not a silent replacement. Both Mulder packages are prepared and unrun. The full A/B/C/D experiment remains incomplete.

The local Claude login works. Automatic approval review blocked the proposed native Claude test under the user's Sol-only instruction before execution. Do not send selected evidence to Claude.ai without destination approval. The external Sol bridge is not validation of the native product backend. Never copy credentials into chat or Git.

Use isolated worktrees and agree on ownership before editing shared files. Inspect main before merging because another terminal may advance it. Preserve completed work; resolve routine conflicts without resetting another agent's branch.
