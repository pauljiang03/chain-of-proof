# Public meaning review for the 60 Data Leakage questions

This is a separate, unrun draft. **It is not ready for a model comparison.** The
original public contract, private reference, prior scores and frozen runs are
unchanged. No private reference or case answers were used to author this review.

`questions.json` preserves all 60 prompts, answer shapes and matching rules. It
adds exact leaf requirements and uses a distinct case ID. `review.json` records
the public input hashes, per-field decisions, separate narrow observations,
independent peer reviews and launch blockers. The `parts` files are the authoring
and peer-review records; peer reports describe the draft before their findings
were resolved in the authoring files.

The reviewed draft has 358 leaf occurrences, including repeated `anyOf` branches:
21 have compatible catalog roles and 337 explicitly require missing support.
There are no missing or invalid annotations. Nine questions have at least one
compatible leaf. **These are catalog counts, not accuracy, evidence availability
or complete-answer counts.** The supported mappings still require selected-PC or
exhibit scope to be enforced before a run.

The main remaining issues are concrete:

- Independently valid fields could previously be assembled into a row about
  different records or images. The new row guard requires the same candidate and
  atomic claim part for related fields. Image comparison, search-history and
  shadow-copy rows retain coherent fields; unsupported cross-claim joins remain
  withheld. The draft has 83 same-part policies and 10 independent section policies.
- `programRan` includes observations from sources such as MuiCache. A generic
  path from that form cannot alone establish membership in an execution log.
  Q11 now accepts the exact reviewed `app.execution.path` role as a partial
  execution-artifact path. It supplies no inferred execution time or count.
- Generic paths, text, record kinds and timestamps lack many requested artifact,
  actor, date-range, action, copy, recovery and intent meanings. Such leaves use
  `needs_*` requirements absent from the catalog; those names do not create rules.
- List completeness remains unproved. This alone does not disqualify a supported
  individual observation; field-specific scope and relationship gaps are separate.

`validate_examples.py` uses only synthetic records. Three exact claims pass the
Lean kernel and independent replay. A reconstructed superseded per-field policy
accepts a shadow-copy ID with another copy's timestamp. The reviewed draft refuses
the mixed row and a nonexecution path while retaining an independent coherent row.
The guard also rejects using unrelated parts of one `both` certificate. This
validates explicit row consistency; it does not establish question relevance,
selected-exhibit scope or case accuracy.

From the repository root, using an environment with the project's dependencies:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python eval/data_leakage_strict_draft/assemble.py --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python eval/data_leakage_strict_draft/validate_examples.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m unittest tests.test_strict60_public_draft
```

Omit `--check` only to regenerate the two derived review files from reviewed parts.
The assembler reads only named public contracts, code and review files. No new
reference, score, investigator session or model run is created here. Before any
experiment, enforce the remaining exhibit checks and required cross-claim joins, review the exact
remaining unsupported meanings, and freeze a separately declared comparison.
