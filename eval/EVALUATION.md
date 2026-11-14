# Evaluation procedure

Use one public question contract and one private reference for every system.
The scorer is deterministic. It does not interpret prose with an LLM.

## Inputs and outputs

- `benchmark_nist_questions.json`: all 60 public questions and answer structures.
- `benchmark_nist.json`: expected answers, source bindings, and comparison rules.
- `runs/current/run.json`: the current saved certificate bundle.
- `runs/current/verification.json`: independent verification of that bundle.
- `runs/current/answers.json`: structured answers with field-level support.
- `runs/current/results.json`: every question's result and comparison details.
- `runs/current/key-audit.json`: source hashes and exact literal checks.

The saved bundle combines prior AI and miner claims without using the answer key to select them.
It was reissued with corrected templates. It uses the saved fact store.
It is a development snapshot, not a new blind investigation or a controlled comparison.
New extraction features require a fresh fact build and investigation before their effect can be measured.

## Scores

The primary measure is fully correct questions divided by the complete question count.
Questions awaiting reference review remain visible as `UNEVALUABLE`.
Report the complete count and the scorable count together.
The complete-denominator rate is a confirmed-correct lower bound while reference review remains incomplete.

The current reference has 60 questions: 46 provisionally scorable and 14 unevaluable.
A question is fully correct only when all required fields and list entries match.
Partial answers remain partial. Missing support produces `unknown` or `unanswered`.
Literal false and null values are distinct from unknown responses.

String, path, timestamp, and list rules belong to the versioned contract.
Apply the same rules to all submissions.
Do not alter the reference to make a system's output match.
A contract mismatch or an additional row is not automatically a forensic false positive.
Forensic false positives require a separate evidence review of the assertion and its meaning.

## Evidence and proof

`eval.pipeline` verifies every certificate against the supplied fact store before it invokes our answer adapter.
A verification failure prevents adaptation and scoring.
The adapter reads the verified run and public profile only. It does not read expected answers.
Each answer field identifies its finding, fact, field, hash, and transformation.

Support marked `certified_core` uses the cited record fields.
Support marked `bound_provenance` uses metadata bound by the certificate verifier.
The latter is not an additional Lean theorem about that metadata's forensic meaning.
The full adapter and its transformations remain reviewed code outside Lean.

An external system can submit the same answer format without a Lean certificate.
Its accuracy score does not imply proof certification.
Matching the key also does not prove that the answer came from evidence.

## Reference audit

Run the source audit with the local source text and PDF available:

```sh
.venv/bin/python -m eval.key_audit eval/benchmark_nist.json \
  --out runs/dev/key-audit.json
```

This checks file hashes, source spans, exact literals, and declared conversions.
It does not prove complete transcription, correct field association, or the truth of prose.
See [BENCHMARK_REFERENCE.md](BENCHMARK_REFERENCE.md) for unresolved questions.
An author reviewing their own transcription is not independent review.

## External submissions

A system can emit the requested typed answer block within its report.
Extract that block without changing its values:

```sh
.venv/bin/python -m eval.submission \
  --report /path/report.md --questions eval/benchmark_nist_questions.json \
  --out runs/dev/external-answers.json
.venv/bin/python -m eval.benchmark \
  --reference eval/benchmark_nist.json --answers runs/dev/external-answers.json \
  --out runs/dev/external-results.json
```

If no typed block exists, extraction fails. It does not guess answers from prose.
Any manual transcription needs a published mapping and independent review.
Do not silently add a separate model that answers missing questions for one system.

## Controlled comparison

1. Complete reference review and resolve list scope, time semantics, and narrative criteria.
2. Freeze the public contract, private reference, scorer, code versions, and evidence hashes.
3. Give both systems identical public acquisition context. Do not supply key-derived identity mappings to one system alone.
4. Select the same exact model and provider, and declare equal budgets and tool differences.
5. Run three trials per system with no access to expected answers or previous results.
6. Retain every trial, including incomplete or failed runs, with logs and resource use.
7. Score every submission with the same frozen scorer. Publish each score and the range.

The [Mulder package](../comparison/mulder/README.md) is prepared only.
Execution waits for finalization and the user's instruction.

## False-claim regression

The independent fixture contains 24 known false claims.
It tests wrong identity joins, kinds, order, and unsupported relations.
It does not measure general precision or establish zero false positives.

```sh
.venv/bin/python -m eval.gate --facts evidence/case_facts.json \
  --labeled-claims fixtures/nist_false_claims.json \
  --case-id nist-cfreds-data-leakage --out runs/dev/gate.json
```

For another dataset, declare its case, timezone, questions, expected answers, and support adapter.
No old NIST answer rows or fallback timezones are used to score an unfamiliar case.
