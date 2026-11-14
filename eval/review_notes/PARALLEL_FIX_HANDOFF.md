# Parallel implementation handoff

The user authorized parallel implementation after the N4 review. Work is integrated
on `finish/parallel-hardening`, originally based on `a0b4fce` and now also including
C0's non-overlapping checkpoint `82beb24`. The separate checkout is
`/private/tmp/chain-of-proof-n4-smoke`. The original `main` checkout remains owned
by C0. This terminal did not update `main`, push, launch a live model trial, or run Mulder.

## Completed changes

- **N4-1/N4-4:** scorer and submission CLI preserve existing files, input aliases,
  symlink targets, and competing writers. Bad inputs and output failures produce
  short CLI errors. Scoring rules and reference values are unchanged.
- **N4-2/N4-3:** failed subprocess results and nonzero exits produce a failed
  wrapper exit. Startup/provider errors retain run/report/summary/status artifacts
  and existing certificates. Diagnostics retain the exception class, not payloads.
  Unexpected programmer errors remain visible after finalization.
- **Optional gate failure:** the initial run/report is written before gate work.
  Gate failures stay unmeasured and fail the command; independent certificate
  verification still controls whether answers and scores can be produced.
- **N1 setup:** explicit setuptools package discovery fixes the documented
  editable-install command. Previously it stopped at “Multiple top-level packages
  discovered in a flat-layout.” Generated package metadata is ignored by Git.
- **N1 threaded tools:** one Workbench instance safely shares its SQLite connection
  with API worker threads. Query budgets/cursors, evidence access, proposal IDs,
  and conclusion writes are serialized without copying the full evidence store.
- **N1 tool access:** the API graph advertises and dispatches only `forms`, `sql`,
  `fact`, `check`, and `conclude`. A model attempting a hidden filesystem or
  delegation tool receives an error. Large evidence responses and public messages
  are not evicted into files that the restricted investigator cannot retrieve.
- **N1 timeout classification:** a provider's `TimeoutError` is distinguished
  from the overall investigation deadline. A deliberate budget stop retains the
  existing partial-run policy; provider errors remain failed executions.
  Queued tool calls check cancellation after acquiring the API lock, and claim
  batches check the monotonic deadline between proofs. Expired batches do not
  keep starting new proof work while the async runner shuts down.
- **N3:** all 14 unresolved source contracts have source-grounded proposals in
  [n3_reference_contracts.md](n3_reference_contracts.md), with a hashed source
  index. These are evaluator-only review notes, not independent human approval.
  The private reference and public questions were not changed.

The old [N4 report](N4_RELEASE_SMOKE.md) and its original JSON snapshot describe
the pre-fix checkpoint. The reproduction script now also records handled backend
failures so it remains useful after the fixes.

## Validation environment

The API dependencies were installed only in
`/private/tmp/cop-n1-readiness-venv`. The original shared `.venv` was not modified.
The tested environment contains Python 3.12.14, DeepAgents 0.7.38,
LangChain 1.5.0, LangChain Anthropic 1.7.10, DuckDB 2.0.0, and Dissect 3.22.
`pip check` passed. The editable package imports correctly outside the checkout.

The clean environment initially lacked Dissect, so three extractor test modules
could not import. Installing the already declared Dissect dependency resolved
that environment issue. README setup instructions now state this test dependency.

Validation before incorporating C0's new demo checkpoint: **326 tests passed with no skips**
in 35.924 seconds, including
all eight optional API integration/deadline tests. `lake build` passed (11 jobs).
In the original environment without API packages, all 14 case-profile/deadline
tests also passed; the eight optional API tests skip cleanly there.

After incorporating `82beb24`, its five new demo tests passed in 0.829 seconds via
`python -m unittest tests.test_demo_proof_gate`. This is 331 distinct passing tests
across the full regression run and the added demo check, not a claim that one
331-test discovery command was rerun after the merge. The merge changed no files
owned by the hardening lanes.

Post-fix smoke assertions confirm that all three scorer overwrite probes preserve
their original bytes and exit 2; backend error probes exit 1 and retain their
artifacts; the successful control exits 0. All ten CLI help commands work, the
four public package hashes and nine original-source hashes/sizes match, and the
30 checked local Markdown targets resolve.

The real API graph tests replace model resolution with a scripted local model,
clear provider/tracing environment variables, and reject network connections.
They exercise actual graph middleware and worker-thread dispatch, rather than
mocking the graph itself. They cover SQL/fact access, SQL write refusal, hidden
tool refusal, explicit model selection, and preservation of large tool results.
Additional tests cover queued-tool cancellation and stopping between claims,
including expiration while the event loop itself is blocked.
No provider response or authentication is claimed to have been validated.

The optional tests skip cleanly in the original environment without API packages.
The existing deadline tests still run there. Lean builds successfully.

Commands in the integration checkout:

```sh
/private/tmp/cop-n1-readiness-venv/bin/python -m unittest discover -s tests -t .
/Users/paul/Documents/hackpton/.venv/bin/python -m eval.review_notes.n4_release_smoke
```

From `lean/`, run `lake build`. All fixture/run writes in the test suite and smoke
probes are temporary. The canonical facts and saved run artifacts are unchanged.

## Remaining limits

The API's asynchronous cancellation cannot forcibly stop a synchronous proof
already running in a worker. Treat its budget as cooperative at those boundaries;
the Claude subprocess backend retains its process-group watchdog. Workbench
locking is per instance, not a cross-process lock for agents sharing one run
directory. Every actual trial still needs its own run name.

A live provider smoke test and any AI/Mulder trial remain unrun. Credentials and
comparison authorization remain with the coordinating terminal and user. The N3
notes propose decisions; none of the 14 questions was marked scorable by this work.
No full re-verification of the saved 473 certificates was needed for these changes;
regressions independently verify their newly generated fixture certificates.

## Integration

C0 can inspect `git diff 82beb24..finish/parallel-hardening` and integrate the
branch after reconciling any newer work. The commits are limited to runner/tool
hardening, CLI preservation, packaging setup, related tests, and review notes.
The preserved N3 notes contain private answer-source material and must not be
copied into an investigator package.

The branch incorporates C0's `82beb24` cleanly. If `main` remains at that checkpoint,
C0 can fast-forward it to this tested integration branch:

```sh
git merge --ff-only finish/parallel-hardening
```

If `main` advances again, reconcile that new work in the integration branch first.
This terminal did not run the integration command against `main`.

Framework references used during the API audit:
[DeepAgents customization](https://docs.langchain.com/oss/python/deepagents/customization),
[framework tool behavior](https://docs.langchain.com/oss/python/deepagents/overview#virtual-filesystem-access).
Implementation was additionally checked against the installed 0.7.38 source.
