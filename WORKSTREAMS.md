# Workstreams and terminal handoff

Updated: 2026-11-14. Read this before assigning more agents.

The two-terminal feature split is integrated. See [FEATURE_HANDOFF.md](FEATURE_HANDOFF.md) for interfaces and ownership.
The original terminal supplied audits, citations, and proof-gap diagnostics.
The other terminal supplied portable verification, coverage, and claim history.
Both coordinators connected the modules to the runner and report.
The CLI and optional local browser interface are also integrated; see [APP_HANDOFF.md](APP_HANDOFF.md).
The CLI is the primary interface. Both interfaces use the same investigation runner and report outputs.
The user then authorized six backend workflow additions. See [BACKEND_HANDOFF.md](BACKEND_HANDOFF.md) for the completed split and scope.

## Objective and constraints

Finish a usable AI-led investigation workflow quickly. Keep the existing Lean verification gate. The deterministic miner is an optional baseline.

- Do not add a new framework, rewrite the fact schema, or build a new UI for this finish pass.
- Keep findings, unverified judgments, answer accuracy, and certificate validity distinct.
- Do not use an LLM judge. Do not give the investigator expected answers or old scored reports.
- Preserve the original answer source. Do not change expected values to fit our output.
- Keep Mulder's original 20-item prose rubric separate from the expanded 60-question typed test.
- Prepare Mulder only. Do not execute it until finalization and the user's instruction to run.
- Do not claim universal zero false positives. Lean proves formal statements relative to extracted facts and declared rules.
- Credentials belong in the local environment, not chat, Git, or logs.

## Current terminal: ownership and state

All six feature lanes are complete. The root agent owns the final checkpoint and push.
The other terminal worked on `finish/evidence-features` in separate worktrees.
No agent may change saved benchmark results as part of this feature work.
Use a separate worktree for new work and agree on file ownership before integration.

## A–D preparation and demonstration

The user selected all four configurations: unchecked AI proposals (A), offline checking of those exact proposals (B), online proof feedback (C), and Mulder (D).
Preparation is authorized. The full comparison remains unrun and must be finalized before execution.

| ID | Owner | Scope |
|---|---|---|
| X0 | Root | `comparison/HACKPRINCETON.md`: sourced event guidance, pitch, limits, and two-minute demonstration plan. |
| X1 | `lean_gap_types` | `comparison/abcd/`: experiment protocol and unfinished freeze manifest. No model calls. |
| X2 | `optical_timestamps` | `scripts/demo_proof_gate.py`, `tests/test_demo_proof_gate.py`: synthetic acceptance, wrong-device refusal, independent verification, and certificate tampering. Five tests and the CLI demo pass. |
| X3 | `journal_gaps` | `eval/review_notes/abcd_runtime_review.md`: implementation and scoring boundaries. Read-only review; existing runtime unchanged. |

A/B runtime support and a shared claim-faithful answer projection remain to be implemented.
Do not relabel unchecked proposals as verified to use the current answer adapter.
The adapter derives values from cited records and could otherwise repair an invalid proposal during scoring.
Paired claim filtering and full question accuracy must remain distinct until the common projection is ready.

The other terminal's `finish/parallel-hardening` branch contains API/CLI fixes and private reference-review notes.
It was integrated at `c411fe6`. Its `eval/review_notes/PARALLEL_FIX_HANDOFF.md` records validation and remaining limits.
Do not copy evaluator review notes into public investigator inputs.

## Completed and tested

- 577 regression tests pass with the optional API dependencies installed. Lean sources are unchanged from the passing build.
- The synthetic workflow verifies refusal, explicit revision, linked reports, portable packages, and tamper rejection without a model call.
- Offline end-to-end tests exercise the CLI and HTTP API through the existing runner and real Lean checks, including cancellation and partial reports.
- The installed CLI, static assets, and HTML/Markdown/JSON downloads pass a local smoke check. Sample report and workspace inspection passed native Chrome checks.
- All 473 certificates in the current saved report independently verify.
- All 24 known false-claim regression probes are refused.
- No LLM grader remains in the current evaluation path.
- The original 20-item package preserves source files, exact item wording, license, hashes, and published decisions.
- Its grading actor and method are not disclosed by the inspected sources. No new judgment was assigned.
- The full 60-question package gives both systems the same public case context and comparison rules.
- CLI timeout enforcement works when the process is silent. The API graph also has an asynchronous deadline.
- API deadline behavior has a synthetic test; a live API investigation still requires credentials and validation.

## Current measured state

`runs/current/` is the saved AI/miner claim union, replayed with current templates and the latest adapter against `evidence/case_facts.json`.
It is not a new AI run with the rebuilt evidence.

| Measure | Current saved report |
|---|---:|
| Fully correct questions | 9 |
| Partial questions | 17 |
| Unanswered questions | 20 |
| Unevaluable questions | 14 |
| Provisionally scorable questions | 46 of 60 |
| Independently verified certificates | 473 of 473 |

Some partial answers contain unequal values. Zero `INCORRECT` whole-question labels does not mean zero false assertions.
The 14 unevaluable questions are unresolved reference contracts, not failed system answers.

A separate fresh deterministic miner run certified and reverified 381 claims, with the same question-status counts.
Its output is under `/private/tmp/cop-latest-nist-miner/`. It used the earlier fresh snapshot, before the final browser/mailbox export corrections.
Do not present it as the new AI result or mix its atomic counts with the saved union.

## Ready inputs for the next AI run

Latest full evidence:

- Facts: `/private/tmp/cop-nist-ready-20261114T224105Z/facts.json`
- SHA-256: `c22bc84acca90791961494d2411938efec8153965cb6f27696011090dc9673b5`
- Health: `/private/tmp/cop-nist-ready-20261114T224105Z/health.json`
- Build log: `/private/tmp/cop-nist-ready-20261114T224105Z/build.log`
- Public case context: `comparison/mulder/case-profile.json`
- Public questions: `eval/benchmark_nist_questions.json`
- Private reference, used only after the run: `eval/benchmark_nist.json`

The facts contain 335,498 records. Logged limitations are nine unsupported Control Panel namespace targets and an unclean Windows Search database. There were no reader crashes.
The 424 MB derived facts remain outside Git. Do not replace the small canonical fact store without also regenerating its bound certificates.

Last authentication check: installed Claude CLI was signed out. No model API key was configured. The user has been asked to authenticate locally.
A separate terminal has frozen and started a bounded Sol with/without-Lean pilot from its own checkout.
Those results and comparison-only commits are separate from this backend change. No fresh native Mulder trial has started.

After credentials are available, the root coordinator can use a new run name:

```sh
.venv/bin/python -m agent.run \
  --backend claude-code --model opus --minutes 15 \
  --name dev/ai-finish-1 \
  --facts /private/tmp/cop-nist-ready-20261114T224105Z/facts.json \
  --case-profile comparison/mulder/case-profile.json \
  --questions eval/benchmark_nist_questions.json \
  --reference eval/benchmark_nist.json --adapter nist
```

For a controlled comparison, replace `opus` with the same exact model ID and provider used by Mulder. The alias command above is a development run, not that comparison.
The optional API backend is `--backend deepagents`; install `.[agent]` and configure credentials locally first. It has not yet had a live integration run here.

## Next parallel assignments

Take one label per agent. Work in a separate worktree. Announce the label and files before editing.
The other terminal has taken the next with/without-Lean experiment preparation in its own branch, following the user's request there. Coordinate B1/B2 with that coordinator; root has no active ablation edits.

| ID | Assignment | Allowed work | Completion evidence |
|---|---|---|---|
| B1 | Unchecked proposal capture | Implement A's receipt-only mode and replay its exact claims through B. Coordinate runner and tool ownership with root. A must receive no proof feedback. | Frozen claim IDs and hashes; no altered or silently discarded proposals. |
| B2 | Shared answer projection | Define one claim-faithful answer path for A, B, and C. Do not mark unchecked claims verified to reuse the current adapter. | Invalid proposed values remain invalid in A; B filters exact claims; source links are retained. |
| B3 | Reference decisions | Review the existing source-grounded notes for the 14 unresolved questions. Keep human review and mechanical source checks distinct. | Explicit approved contract decisions, fixed before model execution. |

Do not start thumbnail interpretation, ESE recovery engines, exhaustive journal proof sweeps, or new Lean metadata schemas in this finish pass.
They remain useful later work, not hidden completion requirements for this checkpoint.

## Safe branch workflow

Start from the latest pushed checkpoint, not an older checkout. The root terminal pushes `main`.
Other terminals should commit their own branch and report the commit; do not push or merge `main` concurrently.

Example after the root push is confirmed:

```sh
git fetch origin
git worktree add /private/tmp/chain-of-proof-next -b finish-next origin/main
```

Raw images and temporary fact builds are not copied into a worktree. Use their explicit read-only paths.
Keep each new run directory separate. Existing output directories must not be overwritten.
