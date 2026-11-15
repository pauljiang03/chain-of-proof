# Q53 metadata recovery, revised contract v1

This is a separately identified, one-question operational task derived from
NIST Q53. It preserves all **17 metadata recovery rows and all five attributes**
in the published table. It does not resolve or replace the frozen 60-question
benchmark. Its case ID is `nist-cfreds-data-leakage-q53-metadata-v1`.

The source explicitly says metadata recovery may suffice for RM#2 and makes
signature carving optional (PDF pages 51–52; text lines 4301–4342). Optional
carving remains preserved in the private reference's supplemental source context.
It belongs in a **top-level submission `appendices` object or the report**, outside
the scored `answer`. The existing generic scorer ignores that metadata, so no
scoring-engine change or case-specific exception is required. Extra fields inside
`answer` continue to count as extra assertions.

`viewable` means reported successful display of recovered content in a compatible
viewer. Extension, signature, header recognition or successful file extraction
alone is insufficient. For each claimed display, the report or evidence appendix
must identify the recovered artifact, viewer/tool, outcome and evidence locator
or digest. Partial, failed and unattempted displays must remain distinct. Omit an
unsupported Boolean; it remains missing rather than becoming a guessed `false`.

The deterministic matcher compares the submitted Boolean to the recorded source
Boolean. It does **not** verify that the display occurred or that its supporting
observation is authentic or adequate. Answer agreement, display evidence support
and Lean verification are separate statements. This is a provisional,
source-derived operational convention; no independent approval or proof of key
truth is claimed or required to run this explicitly labelled revised task.

Give systems only [questions.json](questions.json), the case brief and supplied
evidence. Keep [reference.json](reference.json) and this evaluator documentation
outside their access. The public profile contains the task, schemas and complete
matching policy; it contains no answer filenames, sizes, row count, recovery-method
answer or private-source locator. Different systems must receive the same public
profile. The existing full-case NIST answer adapter must not silently relabel its
output to this new case ID; a submission must explicitly follow this contract.

A submission can have this shape (the empty list is a schema example, not an answer):

```json
{
  "schema_version": 2,
  "case_id": "nist-cfreds-data-leakage-q53-metadata-v1",
  "answers": [{"question_id": "Q53", "status": "answered", "answer": {"files": []}}],
  "appendices": {"display_observations": [], "optional_carving": []}
}
```

Validate without running a model, extraction or an application evaluation:

```sh
python -m eval.contracts.nist_q53_metadata_v1.validate --source-root /path/to/repo-with-source
```

The validator checks reference/public schemas, matching-rule symmetry, unchanged
frozen inputs, all 17 preserved rows, source bindings, no expected-value leakage,
appendix score invariance, and missing/wrong/extra-field penalties. Its copied-key
self-tests are deliberately synthetic. [validation.json](validation.json) records
those checks, **not an investigator performance score**. All 14 original questions
remain unresolved in the frozen key; the other 13 decisions remain documented in
[the reference review](../../review_notes/final_reference_decisions.md). Q33's
representation patch remains unapplied.
