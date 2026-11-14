# Audit, citations, proof gaps: two-terminal implementation

Updated 2026-11-14. The user authorized all six features and parallel work across both terminals.
This is implementation work. No live AI or Mulder benchmark is authorized by this handoff.
Keep the existing Lean gate and private-reference isolation. Do not build a new framework or UI.

## Integrated result

All six lanes and both coordinator integrations are complete. The table below records ownership; it is not an open assignment list.
Future runs include tool audits, linked citations, proof-gap diagnostics, coverage, and explicit claim history.
The package CLI exports a complete fact store and independently checks its certificates and file hashes.
An offline fixture exercises refusal, explicit revision, report export, portable verification, and tamper rejection.
The optional API graph is tested without a provider call. Saved benchmark results are unchanged.

Final review added checks for modified package files during verification, non-finite audit JSON,
and SQL results that cannot be serialized. Those SQL failures now leave sanitized error events.
See `TASKS.md` for the final test count and `WORKSTREAMS.md` for the remaining comparison work.

## Shared base and ownership

C0 integrated the other terminal's tested hardening branch at `c411fe6` into `main`.
The original terminal owns integration and pushes to `main`. The other terminal uses its existing worktree and its own branch.
Read this document before editing. Each terminal has a coordinator and up to three subagents.

| Lane | Terminal / owner | Files owned | Deliverable |
|---|---|---|---|
| F1 | Original / journal_gaps | `agent/tools.py`, new `agent/audit.py`, `tests/test_audit.py` | All five Workbench tools emit a common audit log, with integrity verification. |
| F2 | Original / optical_timestamps | `checker/report.py`, optional `checker/citations.py`, `tests/test_report_citations.py` | Full linked evidence and proof appendix, plus a separate proof-gap section. |
| F3 | Original / lean_gap_types | `checker/check.py`, new `checker/needs.py`, `tests/test_proof_needs.py` | Deterministic explanation of why a claim cannot be proved and what is still required. |
| F4 | Other terminal / assign one agent | New `verifier/package.py`, `tests/test_verification_package.py` | Portable verification directory and a command to verify its contents. |
| F5 | Other terminal / assign one agent | New `agent/coverage.py`, `tests/test_coverage.py` | Honest extraction, inspection, certification, and unknown/failure summary. |
| F6 | Other terminal / assign one agent | New `agent/history.py`, `tests/test_claim_history.py` | Chronological claim attempts and explicit revision links, kept apart from proof validity. |
| F0 | Original coordinator | `agent/run.py`, `agent/mcp_server.py`, `agent/brief.py`, README/TASKS/WORKSTREAMS, integration tests | Wire run metadata, optional explicit revision IDs, coverage, and reports after modules arrive. |
| F7 | Other coordinator | `checker/export.py`, own handoff notes, integration tests | Integrate optional audit/coverage/history metadata into bundles; preserve old saved-run compatibility. |

Do not edit another lane's files. Send required hooks to its owner. Do not touch the key, current saved reports, or extractor output.
The original terminal owns the `agent/tools.py` integration of optional revision IDs; F6 supplies a helper rather than editing that file.
The other terminal must not edit `agent/run.py`, `agent/mcp_server.py`, `agent/brief.py`, or `checker/report.py`.

## F1: audit interface

Write `audit.jsonl` in the run directory. Include tool name, arguments, result or result hash, stable call ID/sequence,
UTC timestamp, duration, status, and returned finding IDs. Record duplicate submissions and failures too.
Preserve existing tool behavior and thread safety. Never log credentials, environment dumps, or exception payloads.
`verify_audit(path, expected_head=None)` returns a dictionary with `passed`, `count`, `head`, and `problems`.
F1 publishes the event schema before F5/F6 depend on it. Missing logs mean unavailable, not zero activity.
Hash chaining checks integrity against a retained checkpoint; it does not authenticate an author or defeat a complete rewrite without an external anchor.

## F2/F3: explain proof gaps

Rejected checker results carry:

```json
{"proof_gap":{"status":"diagnostic","summary":"...","requirements":[
  {"category":"...","reason":"...","action":"...","fact_ids":[],"observed":{},"required":{}}
],"disclaimer":"..."}}
```

`observed` and `required` are optional. Keep accepted certificate semantics unchanged.
Distinguish a missing record, conflicting identities or values, insufficient timestamp precision,
reversed time order, wrong record type, unsupported claim form, malformed input, and execution failure.
Use actual rule conditions and source records. Do not invent evidence, promise that it exists, or imply that an unsupported allegation becomes true after adding a document.
An existing contradiction must not be described as merely missing evidence.
Show this as diagnostic guidance, never as a certified finding or proof of a counterfactual.

F2 uses finding-scoped evidence anchors, all cited records, available provenance, and embedded Lean source.
Escape metadata and do not invent byte offsets. Preserve the certificate's sentence. Optional judgments remain separate.
F2 may render optional `coverage` and `history` blocks once their schemas are agreed.

## F4: portable verification

Suggested CLI: `python -m verifier.package build --run RUN --facts FACTS --out NEW_DIRECTORY`,
and `python -m verifier.package verify --bundle DIRECTORY`.
Use a directory, not a new archive framework. Never overwrite an output or follow manifest paths outside it.
Reverify before export. Copy the complete fact store: census proofs need the entire relevant population, not only selected rows.
Include the run, report, available audit/claim logs, toolchain identity, and a manifest of file hashes and explicit source bindings.
Export no answer keys, environment dumps, API credentials, or arbitrary sibling files.
Missing model/version/audit information must be marked unknown. Do not invent run provenance for an old snapshot.
Verify file hashes and regenerate proofs from bundled facts. An optional externally retained manifest hash can anchor integrity.
Explain that this verifies supplied records and artifacts, not the authenticity or completeness of an original disk image.
Coordinate report rendering through F2's existing `render` API; audit verification through F1's function when available.

## F5: coverage and failures

Separate records extracted, records explicitly inspected, records cited, accepted findings, and unanswered public questions.
Do not equate an aggregate SQL query with reading all records or equate a tool call with a complete investigation.
Reuse existing extraction metadata/health. Distinguish reader failures, unsupported sources, and missing information.
No answer key is needed. If public answers or inspection logs are absent, say unmeasured/unknown.
Return a JSON-serializable summary; provide a pure helper and standalone CLI if useful.
F7 integrates available summaries in export; F0 wires optional health/question inputs into future runs.

## F6: history and explicit revisions

Read actual proposal/audit events in order. Show accepted, refused, duplicate, and failed attempts with IDs and times when available.
Do not infer that similar claims are corrections or that success followed a refusal causally.
Support an explicit `revises` reference to a prior proposal in the same run; reject unknown, self, or forward references.
Provide a pure helper to validate/link this metadata. F1/F0 will wire it into tools and prompts.
Keep revision metadata outside the certified claim. A corrected proposal requires a new proof.
Handle legacy logs without timestamps or revision IDs as incomplete history, not fabricated activity.

## Tests and integration

Use focused synthetic tests: true/false claim conditions, audit tampering, concurrent calls, broken citation metadata,
bundle tampering/path escape, missing coverage data, and invalid revision links. No model calls.
Each agent reports its schema, changed files, tests, and limitations to its coordinator.
The other terminal commits its branch and sends the commit ID. Only C0 integrates and pushes `main`.
After integration, run the combined regression suite with the prepared optional-API environment and Lean build.
Preserve the planned A–D comparison; A receipt-only mode must not receive proof-gap feedback.
