# Mulder's original 20-item evaluation

This package preserves Mulder's published 20-item NIST Data Leakage Case rubric. It contains the original baseline and three Opus 4.6 assessment reports, unchanged. It does not contain a new score for either system. No investigation, grading trial, or LLM judge has run as part of this preparation.

The package is **prepared; rubric review is required**. The original test uses prose judgments about a complete investigation report. Its authors did not publish a complete executable matching contract in the inspected sources. A Lean certificate can support a claim in a report. It does not determine whether that report satisfies one of these prose criteria.

## Files and access

| File | Purpose | Give to an investigator? |
| --- | --- | --- |
| [public/questions.json](public/questions.json) | New question-only projection of the 20 topics | Only for the explicit question-driven variant |
| [public/answers.template.json](public/answers.template.json) | Optional answer format, with no expected answers | Yes, for that variant |
| [public/INSTRUCTIONS.md](public/INSTRUCTIONS.md) | Response and evidence instructions | Yes, for that variant |
| [private/items.json](private/items.json) | Exact original item text, source lines, wording variants, and published judgments | No |
| [private/rubric.json](private/rubric.json) | Published prose rules, formulas, unresolved boundaries, and historical results | No |
| [private/review.template.json](private/review.template.json) | Empty review record; it does not assign judgments | No |
| `private/upstream/` | Unchanged upstream accuracy reports and READMEs | No |
| [SOURCES.json](SOURCES.json) | Immutable source revision and SHA-256 for each copied file | Evaluation coordinator only |

`private/` means evaluator-only input. A directory name is not an access control. An investigator must receive only its approved public files and evidence, without the private directory, NIST answer key, assessment reports, or repository-wide search access. The upstream READMEs also contain answers.

## What is exact, and what is new

The original 20 item texts, published judgments, assessment prose, and source files are preserved. The original baseline and later Opus reports differ in capitalization for item 7 and dash punctuation for item 15. The machine-readable manifest retains those variants rather than normalizing them silently.

No standalone original 20-question input was found in the pinned example directories or source tree inventory. The Opus README publishes an autonomous `mulder investigate` command. The 20 items appear in the later assessment report. Generic investigator prompts exist in Mulder's source, but these are not a standalone 20-question test. The published materials do not identify the grading actor or method. An investigating model's name is not evidence that the same model graded the report. A source commit's Claude coauthor trailer does not establish that either.

There are two distinct future protocols:

1. **Original task and rubric:** investigate the evidence, then assess the entire resulting report against the preserved 20-item rubric. Do not supply the new question projection. The evidence, software/model settings, report, and reviewer decisions must be recorded. The pinned release commit is available; an immutable container digest and the complete original grader environment are not established here.
2. **Question-driven variant:** give both systems the same `public/` files and evidence. Assess their answers and full reports against a reviewed contract. This adds questions to the historical input and must be reported as a variant, even if the 20 topics are unchanged.

The neutral [60-question package](../mulder/README.md) is separate. Neither package replaces the other. Do not compare the 60-question deterministic metric with the original 20-item prose metric as if they were the same denominator or matching rule.

## Original accounting

The original grid has 20 items. Each receives FOUND, PARTIAL, MISSED, or FALSE POSITIVE. Full match is `FOUND / 20`. Detection is `(FOUND + PARTIAL) / 20`.

The published false-positive rate is `(within-grid false-positive claims + additional false-positive claims outside the grid) / 20`. Its denominator is **not the number of assertions**. It is not semantic precision. Correct extra findings do not automatically count as errors. Review also covers unhedged claims in narrative, IOC tables, and containment actions. Claim grouping and exclusions require the original assessment prose.

These are the upstream author's published results, transcribed without rescoring:

| Opus 4.6 run | FOUND | PARTIAL | MISSED | FP in grid | Additional FP | Full match | Detection | Published FP rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 9 | 10 | 0 | 1 | 1 | 45% | 95% | 10% |
| 2 | 10 | 8 | 1 | 1 | 1 | 50% | 90% | 10% |
| 3 | 9 | 10 | 0 | 1 | 0 | 45% | 95% | 5% |

Each row's four grid counts sums to 20. Additional false positives are outside that grid. The three reports use the same 20 item titles, but their explanations expose judgment boundaries: run 2 calls item 4 a close decision; run 1 accepts item 11 with less timestamp detail; run 2 retains FOUND for item 13 despite an interval arithmetic error. The source also explicitly exempts an RM1 destination interpretation adopted by the rubric. These choices are recorded in [private/rubric.json](private/rubric.json).

## Review before a future comparison

A named reviewer must resolve and record the open boundaries before applying this rubric to new reports. The review template records the report hash, source citations, rationale, exclusions, and additional false-positive claims. It contains no filled judgments. No agent is assigned to grade it.

A deterministic adaptation would need a new version with explicit required facts, accepted evidence, list scope, time tolerances, contradiction rules, and supported inference rules. Both systems would use that same frozen contract. Such a scorer could compute arithmetic deterministically after decisions are fixed. It could not reproduce the original semantic judgments merely by counting matching words or Lean record kinds. No such adaptation is implemented or executed in this package.

## Source preservation

Report-source commit: `f3f1952ba610bb2b7e6bd6548c903546f8ec5f63`.

Reported Mulder release: `v1.5.2`, commit `77eee1d47a49caece7c2f2f345c70df2e61b7498`. The report-source commit is later than the executable release commit.

The six Opus files match the existing local baseline copies byte for byte. Every copied source has a SHA-256 in [SOURCES.json](SOURCES.json). The archived source subset does not include investigation logs or reports; original relative links to those files can be resolved at the pinned upstream URL listed in the manifest. Source files were not rewritten to change those links.

The upstream files are distributed under [Apache License 2.0](LICENSE). See [ATTRIBUTION.md](ATTRIBUTION.md). Preserving an original assertion does not certify its forensic interpretation or endorse its historical score.
