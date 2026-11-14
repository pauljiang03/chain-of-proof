# Evaluation contract and comparison limits

We reuse the NIST images and published answer key. We do not need a new forensic
dataset to compare systems. We do need a reviewed, versioned encoding of the answers
and a common scoring contract that is independent of either system's implementation.
The current scorer is deterministic; LLM grading has been retired.

## Current report results

The saved combined report states **456 of 613 encoded answer items (74.4%)**.
It matches every encoded item for **24 of 57 questions (42.1%)**, some items for
20 questions, and none for 13. These are reference coverage measures, not precision
or an assertion that every part of 24 original NIST questions has been answered.

| Saved output | Encoded answer items stated | Questions with every encoded item matched |
|---|---:|---:|
| Original AI investigator alone | 164/613 (26.8%) | 6/57 |
| Original deterministic miner alone | 430/613 (70.1%) | 24/57 |
| Combined, corrected certified report | 456/613 (74.4%) | 24/57 |

The combined output uses the union of the original miner and investigator's claims,
without looking at the key to choose claims. It adds no new AI trial or extracted facts.
All 473 unique claims received new certificates and independently reverified.
The 24 deliberately false probes from the original miner are not part of that union;
zero rejections in its statistics does not mean zero false positives.

Artifacts: [combined report](../runs/optical-review/combined-report.md),
[score](../runs/optical-review/combined-results.json),
[certificate verification and source hashes](../runs/optical-review/combined-verification.json).
The combined report states 362/517 items in the formerly closed-book portion and
94/96 in the original open-book portion. It is a development result produced after
reviewing misses, not a new blind evaluation. The original closed-book extraction
result remains 367/517 in [the frozen results](results_full.json).

## What the current reference covers

[reference_full.json](reference_full.json) encodes 613 answer items across Q1–Q57.
The source key has 60 questions; Q58–Q60 request a summary, timeline and diagram and
are excluded from this reference. The 613 items are our transcription, not 613
independent NIST questions. Some rows overlap or repeat the same underlying evidence.

The reference has material limits:

- 68 items have no supported matcher. They remain in the denominator and cannot
  count as matched; this does not mean Lean can never express them.
- Positive matchers use the project's record vocabulary. They do not yet constitute
  an implementation-neutral answer schema.
- Some attributes appear in the transcribed prose but are not tested: for example
  some execution counts, sizes, sender/recipient fields and content details.
- A question is marked complete only under the encoded contract. This does not
  establish that all attributes requested by the original question were checked.
- A correct assertion can match even when another submitted assertion contradicts
  it. Extra assertions are listed as unassessed, not treated as true or false.
- Internally extracted timestamps can use their recorded uncertainty. The external
  answer adapter currently uses only the reference tolerance. A fair comparison
  needs the same predeclared temporal contract for both systems.

Consequently, do not describe current item coverage as unrestricted answer accuracy,
precision, or a fair head-to-head win over Mulder. Reference transcription and matcher
design are trusted evaluation work; Lean does not certify their faithfulness to NIST.

## Extending Mulder's approach

Mulder publishes a [20-item checklist and reports](https://github.com/calebevans/mulder/tree/main/examples/ndlc-v1.5.2).
Those items bundle facts and investigative conclusions. They are not simply the
first 20 NIST questions. Its published full-match and detection rates use that
checklist, not our 613 items. Our historical LLM regrades are exploratory annotations,
not benchmark results, and `eval.mulder` now only displays their archive.

A common benchmark should extend the checklist method while removing ambiguous
grading decisions:

1. Freeze a source-linked answer contract with question IDs, all required fields,
   accepted alternatives, timestamps and tolerances. Audit it against the key before
   running either system. Preserve the original key and version any corrections.
2. Use neutral answer types: scalar values, lists/sets, booleans, temporal relations,
   and explicit conclusions. Distinguish false, unknown and unanswered. Include
   content identification and exclusions explicitly rather than dropping them.
3. Define cardinality and contradiction rules. A scalar answer cannot give every
   possible value and receive full credit. Score missing and incorrect list members
   separately. Treat evidence support as a separate check from answer equality.
4. Give both systems identical images, public questions and resource limits. Keep
   expected values hidden. Require the same output schema; our adapter translates
   Lean-backed findings, and Mulder's adapter translates its own structured output.
5. For existing prose-only reports, use audited transcription with source quotations
   and spans. Do not infer an answer the report did not state. This introduces a
   human annotation boundary, not an LLM judge.
6. Report complete-question accuracy and atomic correctness under that contract,
   unanswered questions, incorrect answers and separately assessed extra claims.
   Show the original 20-item subset separately for historical comparison.
7. Publish per-item verdicts, run/model/tool versions, hashes, costs, failures and
   repeated runs. Use held-out cases to measure generalization after development.

The neutral schema and typed contradiction/extra-answer scoring are now implemented
in [benchmark.py](benchmark.py). A [draft 60-question reference](benchmark_nist.json)
retains many attributes the 613-item version omitted; its
[public questions and answer shapes](benchmark_nist_questions.json) contain no expected
values. Source bindings are audited by [key_audit.py](key_audit.py).
This is a new explicit rubric inspired by Mulder's approach, not a reproduction of
its historical prose judgments. `INCORRECT` means an answer-contract mismatch, not
Mulder's causal-support false-positive category. Extra list members prevent a full
match under the declared contract; that does not prove those facts are false.

The new reference is AI-transcribed development work requiring independent review.
The [source audit](../runs/key-review/reference-source-audit.json) passes all 60
question-span bindings and 1,001 literal-value bindings; it explicitly does not
claim semantic correctness. See [reference review notes](BENCHMARK_REFERENCE.md).
Ambiguous or qualitative questions remain explicitly unevaluable in the full
question denominator. Source hashes establish traceability, not semantic truth.
No result on this draft is a final benchmark claim. Mulder has not been run on the
complete common test in this repository.

```sh
python -m eval.key_audit eval/benchmark_nist.json --out runs/dev/key-audit.json
python -m eval.benchmark --reference eval/benchmark_nist.json \
  --answers path/to/typed-answers.json --out runs/dev/benchmark-result.json
```

The typed submission is `{"schema_version":2,"case_id":"...","answers":[
{"question_id":"Q1","status":"answered","answer":{...}}]}`. The same schema and
matching rules apply to both systems; `false`, `null`, `unknown` and unanswered are
distinct. Certificates remain a separate evidence-support measurement.

## Using the implemented scorer

For an existing trusted checker-produced run:

```sh
python -m eval.score --facts evidence/case_facts.json \
  --reference eval/reference_full.json --run runs/dev/combined-reviewed/run.json \
  --no-gate --out runs/dev/combined-score.json
```

For positive structured assertions from any system:

```json
{"answers": [{"kind": "webSearch", "obj": "example search", "aux": "", "utc": "2020-01-02T12:00:00Z", "exhibit": "HOST-1"}]}
```

```sh
python -m eval.score --reference path/to/reference.json \
  --answers path/to/answers.json --no-gate --out runs/dev/answer-score.json
```

That adapter cannot score arbitrary prose, negation, images or unsupported conclusions.
It records incompatible submissions and unassessed extras. It does not grant external
answers Lean certification. Conversely, `score_run` assumes a trusted checker output;
merely setting a field to `verified` in JSON is not certificate verification.

Generic cases require an explicit reference. Declare an IANA `time_zone` if matchers
use local dates. The legacy NIST fallback is scoped to its known reference/evidence;
other cases do not inherit its questions or false-claim probes. Supply case-specific
`--labeled-claims`, or `--no-gate`. No probes selected means **not measured**.
Investigator `--case-profile` contains only public questions/context, not expected answers.

## What zero false positives would require

The fixed gate refused 24/24 known-false claims. This is useful regression evidence,
not a measured precision of 100% over all possible reports. The retired LLM marker's
11–13 flags were on Mulder's reports, not ours, and are not a trusted FP count.

Lean proves that a formal claim follows from the cited extracted records under its
rules. Correct parsers, correctly interpreted artifact semantics and faithful English
templates remain trust boundaries. A certificate does not prove a heuristic is a
universal law or certify an unverified narrative. Default reports now exclude the
AI's free-form conclusions; an explicit optional appendix remains outside Lean.

See [the optical correction](OPTICAL_REVIEW.md) for an actual semantic failure, and
[misses and required support](MISS_SUPPORT.md) for the remaining extraction/IR gaps.
