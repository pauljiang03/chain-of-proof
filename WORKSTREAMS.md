# Workstreams and terminal handoff

Updated: 2026-11-14. Read this before assigning more agents.

Current implementation split: [FEATURE_HANDOFF.md](FEATURE_HANDOFF.md). Original terminal owns F1 audit, F2 citations,
and F3 proof-gap diagnostics. Other terminal owns F4 portable verification, F5 coverage, and F6 revision history.
The hardening branch at `c411fe6` is now integrated; use the feature handoff for current file ownership.

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

The original three implementation lanes are complete. The root agent owns final integration and the push.
The `a0b4fce` checkpoint is pushed. The second terminal is working in separate worktrees.

| ID | Owner | State | Work and owned files |
|---|---|---|---|
| C0 | Root | Final integration / push | `agent/run.py`, deadline tests, `README.md`, `TASKS.md`, `WORKSTREAMS.md`, `runs/current/`. Integrate completed lanes; preserve current results and provenance. |
| C1 | `journal_gaps` | Complete; frozen | JumpList sections of `extractor/windows.py`, `extractor/inventory.py`, `tests/test_jumplists.py`, inventory tests. Windows 10 v4 parsing, valid empty CFB handling, concrete container inventory. Fresh evidence build is ready. |
| C2 | `optical_timestamps` | Complete; frozen | `eval/nist_answers.py`, `extractor/webcloud.py`, mailbox sections of `extractor/windows.py`, related tests. Correct source/time vocabulary, extensionless browser paths, unavailable senders, inventory answers. Original-20 package and final validation. |
| C3 | `lean_gap_types` | Complete; frozen | Acquisition identity, explicit public policy, bounded journal path observations, existing Lean rules, `eval/package.py`, `comparison/mulder/`, package tests. New metadata schema was stopped before any repository edits. |

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

- 281 regression tests pass. Lean builds successfully.
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
No fresh AI or Mulder trial has started.

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

## Available assignments for a new terminal

Take one label per agent. Work in a separate worktree. Announce the label and files before editing.

| ID | Assignment | Allowed work | Completion evidence |
|---|---|---|---|
| N1 | API integration readiness | Existing API backend and isolated integration tests. Verify restricted evidence tools, explicit model selection, time limits, error reporting, and dependency setup. Coordinate `agent/run.py` ownership with C0. Do not launch paid trials or Mulder on your own. | Reproducible setup and a mocked test or authorized live smoke test. No new agent framework. |
| N2 | Public subject scope | Investigate Q15's all-profile export. Propose the smallest explicit public account selector shared by both systems; never infer it from the key. Own a proposal/test file first, coordinate adapter edits with C0. | Tests with two users, an unknown user, and another case. No hidden NIST username fallback. |
| N3 | Reference contract review | Read the original PDF/text and the 14 unresolved question notes. Write source-grounded findings under `eval/review_notes/`. Do not edit the reference, assign new model grades, or mark independent human review complete. | Exact source pages/lines, the ambiguity, and the smallest proposed contract decision. |
| N4 | Release smoke test | Read-only checks of CLI commands, package inputs, local links, output preservation, and failure messages. Put findings in a new file under `eval/review_notes/`. | Reproducible command and observed failure. Fix only after file ownership is agreed. |

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
