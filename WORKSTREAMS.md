# Workstreams and terminal handoff

Updated: 2026-11-15 UTC. Read this before assigning more agents.
The project is now CONAN-F. The `cop` command and `ChainOfProof` Lean library keep
their existing names for compatibility.

## Current ownership

See [FINAL_EVAL_HANDOFF.md](FINAL_EVAL_HANDOFF.md) for the five authorized priorities.

| Owner | State and files |
| --- | --- |
| Root Codex | Integration worktree `/private/tmp/cop-final-eval`, branch `finish/final-eval`. Owns product tools, report/evaluation integration, verification, documentation and final push. |
| Other Codex terminal | Coverage, paging and reader commits are integrated. Preparing the new explicit-binding comparison runtime in `/private/tmp/cop-projection-smoke`, branch `finish/projection-smoke-runtime`. Owns comparison runtime/prompt/pilot/bindings files and their tests. No model run until the integrated checkpoint is frozen. |
| Claude | Independent con-leche checker, install fix and CONAN-F rename are integrated. Last observed branch: `finish/desktop-ui`. Avoid concurrent UI changes. |
| Root helpers | Shared projection, census scaling, reference review and second-case mechanical smoke are complete. No active implementation ownership. |

The six backend workflow features are integrated. Their interfaces remain in
[BACKEND_HANDOFF.md](BACKEND_HANDOFF.md). The original app and feature interfaces
remain in [APP_HANDOFF.md](APP_HANDOFF.md) and [FEATURE_HANDOFF.md](FEATURE_HANDOFF.md).

## Implementation delivered in this pass

- Shared claim-field answer projection for A/B/C and product reports. B removes
  whole candidates and preserves A's frozen conflict omissions. It cannot repair
  values or reveal previously hidden values.
- The `answer` tool records explicit field bindings. HTML, Markdown and JSON
  outputs retain each field's claim and source links. `--adapter claims` rechecks
  certificates before deterministic scoring for any case with a public contract.
- Snapshot-bound inventory pages, separate finding/note limits, and neutral
  missing-field and unfinished-page diagnostics. The prompt asks the investigator
  to review those diagnostics within its existing time budget.
- Census proofs up to 2,048 rows, with unchanged Lean semantics and independent
  full-source checks. The 518/747 total and distinct-count proofs also passed con-leche.
- General registry reads for omitted system, timezone, Search and snapshot settings.
- A separate source-grounded Q53 metadata contract. The frozen full-case key and
  original pilot remain unchanged.

## Measurement boundaries

Do not use an LLM judge. Do not give investigators the answer key, private review
notes, old scored reports or another arm's output. Retain failures and unknowns.

Lean proves the declared formal statement relative to the extracted records and
rules. It does not prove parser correctness, question relevance, list completeness,
source authenticity or universal zero false positives.

The original Sol pilot is frozen at `617dc29`. Its [summary](comparison/ablation/PILOT_SOL61_20261115.md)
reports 11/46 fully correct literal answers for A and 12/46 for C. Those answer
blocks are unverified. B reverified 169 claims; C reverified 29 unique claims.
The new projector must not receive retrospective, hand-written bindings to change
those scores. A new explicit-binding protocol and fresh runs are required.

The historical `runs/current` union has 9 complete, 17 partial and 20 unanswered
questions, with 14 unresolved reference questions. Its 473 certificates reverify.
It is not a new investigation with the latest readers or product workflow.

The full A/B/C/D experiment remains unfinished. Mulder is prepared but unrun.
Do not describe a development smoke as the full experiment or as a final comparison.

## Fresh second-case operational smoke

- Output: `/private/tmp/cop-case2-final-20261115T015403Z/`.
- Facts: `evidence/facts.json`, SHA-256
  `0a4d2243adbe10b33eaff335fdc7bbd8be901e55cb3a1bd20f01089437361e61`.
- Scope: desktop image only, `windows,system` readers, 1,800 records.
- Public contract: `eval/case2/smoke-profile.json`, six generic questions; no accuracy key.
- Four documented extraction limitations remain in `evidence/health.json`.
- Mechanical smoke: 46 audited calls, 12 independently verified certificates,
  36 supported answer fields, HTML/Markdown/JSON report and verified portable package.
- The runtime manifest records `791df84` with `dirty=true` and individual source
  hashes. Do not call it a clean-commit trial or an AI accuracy result.

## Inputs for the next full NIST development run

- Facts: `/private/tmp/cop-nist-final-20261115T020159Z/evidence/facts.json`.
- SHA-256: `a79fcce1015bf73a66779557a6d5235b4ee4d4b1bc9683803cff5f1abc0f5c8d`.
- Records: 335,509, including 11 email records and 32 system settings.
- All 12 reader/exhibit attempts completed without reader-level crashes. Nine
  unsupported shell targets and the dirty Search database remain explicit limitations.
- Extraction took 55.96 seconds using the existing complete repository `.venv`.
  The clean `8a625fc` launch and individual source hashes are recorded beside the facts.
- Public case: `comparison/mulder/case-profile.json`.
- Public questions: `eval/benchmark_nist_questions.json`.
- Private reference: `eval/benchmark_nist.json`, post-investigation only.

Do not replace a fact store that saved certificates already bind. Keep the new
extraction cost and reader limitations visible. An earlier attempt used a separate
environment without the mailbox library; retain its failure record but do not use
that incomplete snapshot as the final comparison input.

The local Claude login works outside the sandbox; the first sandboxed status check
could not access it. No API key is present in this process. Live work is restricted
to the user's Sol 6.1 choice unless another destination is approved. The proposed
native Claude test was blocked by automatic approval review and did not start.
Credentials must never be copied into chat, logs or Git. A Codex subagent bridge
trial is not validation of the native Claude/API product backend.

## Integration rules

Start from the latest checkpoint in an isolated worktree. Agree on ownership
before editing shared files. Report completed commits for root integration.
Inspect `main` again before merging; Claude may advance it in parallel.
Preserve completed work and saved results. Resolve routine merge conflicts rather
than resetting or overwriting another terminal's files.
