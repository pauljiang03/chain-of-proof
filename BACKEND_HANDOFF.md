# Backend investigation workflow

The user authorized all six additions on 2026-11-14. Work is isolated in
`/private/tmp/cop-backend-next`, branch `finish/backend-workflow` from `80a8cea`.
The comparison terminal owns its frozen pilot. Do not change its inputs or results.

| Owner | Scope | Files |
| --- | --- | --- |
| Root | Continuation, tools, runtime, CLI, integration | agent/continuation.py, agent/run.py, agent/tools.py, agent/mcp_server.py, agent/cli.py, agent/brief.py, app/cli.py, app/jobs.py, docs |
| journal_gaps | Supported-image intake and approved follow-up extraction | extractor/build.py, extractor/intake.py, agent/evidence_requests.py, new tests |
| lean_gap_types | Persistent questions and general certificate-linked answers | agent/investigation.py, agent/answers.py, checker/export.py, new tests |
| optical_timestamps | Conservative conflict review and report sections | agent/review.py, app/report.py, checker/report.py, focused tests |

Keep extracted snapshots immutable. A continuation gets a new run directory and binds
its parent. New evidence must not inherit certification from old record IDs. Task
progress, diagnostic conflicts and unresolved needs are not certified conclusions.
No new framework or benchmark-answer access. Use synthetic/local verification for
implementation; do not start additional paid investigations.

## Completed behavior

All six lanes are integrated. `cop investigate --images DIR --exhibits FILE` runs
supported intake and the existing investigator. `cop ingest` extracts without a
model. `cop plan` reads persisted question work. `cop resume` creates a new run and
can add public questions or use new facts. It resumes tasks, not hidden provider state.
The model has plan/update_question/evidence_needs/collect/review in both backends.
Collection permits one successful approved pair per stage. Use `--follow-up-stages`
for up to three automatic additional stages, each with its own time budget.

New snapshots retain prior source observations and recompute deterministic tags.
They bind source-image bytes and parent facts before and after extraction. A changed
input prevents publication. File hashes do not authenticate the original acquisition.
Reports keep work notes, pending evidence, diagnostics and exact certificate statements
separate. The general answer view is `case-answers.json`; benchmark `answers.json`
and private reference handling remain separate.

## Validation and limits

The synthetic vertical test runs CLI intake, real tool dispatch, Lean verification,
collection, automatic continuation, report export, and a follow-up question. Only the
image parser and model are simulated. A synthetic verification package independently
passes with an external manifest digest. The standalone report was rendered in a
separate headless Chrome profile and visually inspected.
No paid model or benchmark investigation was started for this implementation.
The browser start form still accepts extracted facts; the new intake/resume commands
are in the primary CLI. Optional image readers and model credentials remain local
installation requirements. Reader coverage and review patterns are bounded. No claim
of better benchmark accuracy or universal zero false positives follows from these tests.

The full integrated suite passed 577 tests. The Lean build passed all 11 jobs.
Task-level recovery also uses a process-lifetime file lock so a stale running label
after a crash does not block a new continuation, while a live run stays protected.
