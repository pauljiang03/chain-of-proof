# N4 release smoke review

Reviewed 2026-11-14 at checkpoint `a0b4fce7b530581b170dc4a7a5d68cdd57260f63`.
Lane: N4. Branch: `finish/n4-release-smoke`.

This lane owns only these new review notes and the offline reproduction script.
No production files, expected answers, saved results, or comparison settings were changed.
Per `WORKSTREAMS.md`, production fixes need ownership coordination with C0.
No AI investigation, provider request, Mulder trial, or new grading was performed.

## Findings for C0

### N4-1 — High: standalone scorer silently overwrites prior results or its inputs

Location: `eval/benchmark.py:504-520`, especially the `write_text` call at line 518.

The documented `python -m eval.benchmark --reference ... --answers ... --out ...`
command does not require a new output path. The offline probe observed all three:

| Temporary output target | CLI exit | Original bytes preserved |
| --- | ---: | --- |
| An existing results file | 0 | No |
| The supplied reference file itself | 0 | No |
| The supplied answers file itself | 0 | No |

Scoring and input hashing happen before the overwrite, so the command can print a
valid-looking score while replacing the reference or submission with that score.
This affects the standalone external-submission path documented in
`eval/EVALUATION.md` and `comparison/mulder/README.md`. The separate
`eval.pipeline` output guards worked in this review.

Smallest proposed fix: reject existing files and symlinks with a clear parser
error, then create the output exclusively (`open("x")`) so concurrent runs cannot
replace one another. Catch write-time `OSError` as a CLI error too. Cover an old
result, either input used as output, a symlink to an input, and a new output.
No scorer rules or reference values need to change.

### N4-2 — High: some failed CLI investigations return success to their caller

Locations: `agent/run.py:108-112` and `agent/run.py:266-267` (C0 ownership).

The probe replaces the Claude subprocess with a local Python process that emits
a synthetic stream event and exits. It then runs the real `agent.run.main`,
including its artifact generation and exit-code decision:

| Simulated outcome | Child exit | Saved `ended` | Runner exit |
| --- | ---: | --- | ---: |
| Success event | 0 | `success` | 0 |
| No result event | 3 | `process_error` | 1 |
| Error result (`is_error: true`) | 1 | `error_during_execution` | **0** |
| Success event followed by process failure | 3 | `success` | **0** |

The final event subtype takes precedence over the child exit, and `main` only
treats two exact status strings as failures. A caller using the shell exit code
can advance past a failed investigation. The numeric child exit remains in
`run.json`, but the wrapper does not enforce it.

Smallest proposed fix: carry the result's error indicator into metadata and make
nonzero child exits / error results fail the wrapper, while keeping any deliberate
time-limit policy explicit. Preserve partial certificates and reports. Add tests
through `main`, since the current subprocess tests alone do not catch this.

### N4-3 — Medium: backend exceptions bypass failed-run finalization

Location: `agent/run.py:240-255` (C0 ownership).

With `run_claude_code` patched to raise `FileNotFoundError`, or `run_deepagents`
patched to raise a provider-like `RuntimeError`, the exception escapes `main`.
The reserved run directory contains only `case-profile.json` and `prompt.md`.
There is no `run.json`, `summary.md`, `report.md`, or evaluation status.

These are injected exception probes, not claims that a live provider was tested.
They demonstrate that backend exceptions skip the common finalization path.
A real CLI startup failure can additionally leave an empty transcript because
`run_claude_code` opens it before starting the process. Certificates already on
disk are not deleted, but this path does not bundle them into a failed run.

Smallest proposed fix: represent expected startup/provider exceptions as failed
execution metadata, finalize whatever artifacts were produced, return nonzero,
and preserve the reserved directory. Keep exception details appropriate for logs;
do not dump credentials or entire request payloads. Test both startup failure and
failure after a saved proposal.

### N4-4 — Low: submission overwrite refusal prints a traceback

Location: `eval/submission.py:49-61`.

The submission extractor preserves an existing output using exclusive creation,
but `FileExistsError` escapes and produces a traceback (exit 1). The verifier,
baseline, and pipeline reject the same condition with a short CLI error (exit 2).
This is error-message consistency, not a data-loss finding. Catch input/validation/
output exceptions at the CLI boundary without weakening exclusive creation.

## Reproduction and observations

From this worktree:

```sh
cd /private/tmp/chain-of-proof-n4-smoke
/Users/paul/Documents/hackpton/.venv/bin/python -m eval.review_notes.n4_release_smoke
```

From a normal checkout with its own environment:

```sh
.venv/bin/python -m eval.review_notes.n4_release_smoke
```

The script creates synthetic reference/answer/fact files only inside temporary
directories. It never passes actual reference files to the overwrite probes.
Backend execution is replaced with local Python or injected exceptions.
It prints observations; a zero script exit is not a declaration that the
observed release behavior is correct. The captured checkpoint output is
[`n4_release_smoke_observations.json`](n4_release_smoke_observations.json).

## Passing checks

- All ten CLI help commands exit 0: investigator, evidence tools, baseline,
  pipeline, scorer, submission extractor, package builder, key audit, gate,
  and certificate verifier.
- Existing-output checks preserve their sentinel for `eval.submission`,
  `verifier.verify`, `eval.baseline`, and `eval.pipeline`.
- All four declared public-package file hashes match. The packaged public
  questions equal `eval/benchmark_nist_questions.json`.
- All nine archived original-20 source/license hashes and byte sizes match.
  The original-20 and expanded-60 packages remain separate and unrun.
- All 30 relative Markdown targets in the seven listed project documents exist.
  This excludes external URLs, fragment anchors, and archived upstream links.
- The ready full-facts file hashes to
  `c22bc84acca90791961494d2411938efec8153965cb6f27696011090dc9673b5`,
  exactly the hash in the handoff. No facts were rewritten.
- Installed Claude Code `2.1.325` advertises the runner's `--permission-prompts`,
  `--allowedTools`, and `--strict-mcp-config` flags in local `--help`.
- 38 existing focused tests passed. The pipeline/tool tests built Lean in this
  separate worktree and exercised certificate acceptance, refusal, and independent
  verification before scoring.

Commands for the 38 tests (run with the shared environment's absolute Python path):

```sh
python -m unittest tests.test_agent_deadline tests.test_baseline_cases tests.test_package tests.test_case_profile
python -m unittest tests.test_evaluation_pipeline tests.test_agent
```

The groups passed 25 and 13 tests respectively. These are targeted rechecks, not
a new claim of a full 281-test run or a recheck of all 473 saved certificates.

## Environment and limits

Python: 3.12.14. DuckDB: 2.0.0. The shared `.venv` has neither `deepagents` nor
`langchain-anthropic` installed, so it cannot yet execute the API backend as-is.
This review did not install dependencies or inspect authentication credentials.
Model login remains a coordinator/user setup step. The optional backend's live
integration and full tool restrictions remain N1 work.

Seven evidence segments are declared in the public manifest. Their raw image
bytes were not rehashed in this smoke test. The 424 MB facts hash check does not
establish reader correctness. No claim is made about unresolved reference
contracts, general forensic precision, or controlled comparison readiness.

## Integration handoff

Only `eval/review_notes/N4_RELEASE_SMOKE.md`,
`eval/review_notes/n4_release_smoke.py`, and its JSON observation snapshot belong
to this branch. C0 can cherry-pick the branch's review commit without touching
its owned implementation files. Prioritize N4-1 and N4-2 before unattended trials;
N4-3 concerns preserving useful failure records. Production fixes were intentionally
left to the agreed owner, as required by the handoff board.
