# X1: A/B/C/D evaluation protocol

**Preparation only. No investigation is authorized by this document.** The manifest is
a template, not an executable configuration. Freeze the inputs, missing runtime support,
budgets, and analysis rules before requesting permission to run. Synthetic integration
smokes do not count as trials.

NIST is a development case. Keep all 60 questions visible. The current draft reference
has 46 provisionally scorable questions and 14 unresolved questions: Q1, Q2, Q6, Q10,
Q16, Q19, Q29, Q30, Q33, Q39, Q48, Q53, Q58, Q60. Review and freeze their treatment
before execution; do not resolve them by inspecting an arm's output. An independent
second case is optional and needs its own public context and reviewed reference.

## Arms and repetitions

| Arm | Live behavior | Output used for evaluation |
|---|---|---|
| A: no gate | Same AI, extracted records, query tools, claim schema, and public task as C. Claim submission returns only an ID/receipt. No semantic checks, acceptance labels, explanations, or repair hints reach the AI. | Immutable submitted candidates and their asserted meanings, labeled unverified. Structural JSON/schema errors remain a separate category. |
| B: offline filter | No AI run. Apply the frozen checker to **exactly A's saved candidates**, preserving candidate IDs and order. No repair, new query, extra reasoning, or replacement claim. | Accepted subset, refusal/error ledger, and precisely recorded losses. A compound `both` proposal is one candidate; reject the whole proposal if any part fails. |
| C: online gate | Same inputs and tools as A; submission invokes the checker and returns its verdict and repair feedback. Repairs create new candidate IDs. | Accepted final claims plus the entire attempt/repair history. Independently replay every published certificate. |
| D: Mulder | Same source images, public case context, questions, exact model/provider, and resource caps; Mulder keeps its native investigation tools. | Its original report and structured answers, with no certification implied. |

Plan three replicate blocks: **9 live investigations (A, C, D) and 3 offline B passes**.
B is paired with its exact A run, never independently sampled. Use separate sessions and
output directories; no prior reports, private reference, or another arm's transcript is
available to an investigator. Counterbalance live order: A/C/D, C/D/A, D/A/C. Insufficient
credentials or time blocks this plan; a smaller pilot must be declared before running
and must not be presented as the three-repetition result. Keep failed and timed-out runs.

The A/C prompt and tool interface differ only in the declared gate behavior and receipt
versus semantic feedback. Neither arm gets silent assistance or extra tools. Treat
uncertified conclusions identically and exclude them from certified-claim metrics.

## Shared answer projection

The shared projector is implemented in `agent/answer_projection.py`, with A/B/C
entry points in `comparison/ablation/projection.py`. New trials must freeze explicit
model-authored field bindings before scoring. The legacy `eval.nist_answers` adapter accepts verified findings and derives answers from
the actual kinds and fields of their cited facts. Flipping A's status to `verified`,
bypassing replay, or substituting those actual facts for A's asserted meaning would
repair A offline and invalidate the experiment. Do none of these.

Freeze the deterministic projection for A, B, and C before their answer comparison:
same schema, normalization, duplicate/list policy, and candidate-to-answer-leaf mapping;
no expected-value lookup. It must preserve what a candidate asserts, including a wrong
relation or time meaning, and must not silently correct it using the cited record.
Every projected leaf retains its candidate dependencies. B removes leaves whose required
candidates were refused, using a predefined structural rule; it cannot refill gaps from
raw facts. Unprojectable claims remain visible in a separate denominator. C uses the
same projection over its accepted claims. No mode fabricates proof status.
Conflicting paths are omitted before filtering. B cannot reveal a value that A's
conflict policy hid. Each output retains its candidate hash, field selector and source links.
Question placement and relevance remain investigator choices, not Lean theorems.

Paired **claim-level A/B** retention and error-removal analysis is useful independently
of that projector. If answer projection does not express a rejected relationship, an
unchanged question score says nothing about whether the gate removed that error.
Existing C and D exports may receive neutral question scores, but do not display four
comparable answer-accuracy percentages until shared A/B/C projection is ready. Current
C adapter scores are answer-export metrics; they do not prove every answer value or
complete list is entailed by Lean.

## Freeze and budgets

Use the same [public case profile](../mulder/case-profile.json) and
[question contract](../mulder/questions.json) in every arm. Freeze image segment hashes,
the A/C record snapshot, extractor and system commits, Lean/Python dependencies, prompts,
tool/schema versions, projector, scorer, private reference, and output serialization.
Record exact provider endpoint and immutable model revision: aliases such as `opus` or
`latest` are not acceptable. Pin Mulder's planner, executor, analyst, and every utility
or repair model call too. An unmatchable role is a declared mismatch and blocks D from
the exact-model comparison.

Set numeric per-trial token and end-to-end wall-time caps in advance, with identical
caps within each replicate block. Count reasoning, feedback, retries, and utility calls;
record input, cached input, output, reasoning, and cost using the frozen accounting rule.
Record sampling parameters and seeds, or explicit provider non-support. B consumes zero
model calls; measure its checking cost separately. Never grant a failed run extra budget.

Include our extraction cost: measure preparation per replicate, disclose shared A/C
preprocessing, and charge that cost to each arm's end-to-end time/budget. B inherits A's
cost plus offline filtering. Mulder's native extraction stays in D's total. Report
preparation, investigation, checker/replay, and total times separately. Record hardware,
cache treatment, and run order; do not compare a warm prepared A/C snapshot with cold D
and claim an end-to-end speed advantage. D is an external system baseline with different
tools; A/B/C provide the narrower gate comparison.

## Measurements and current implementation

Report each replicate and paired changes, not only the best run. Separate:

- Question correctness/misses and atomic contract mismatches, including extra assertions,
  unequal values, abstentions, and the unresolved reference denominator.
- A-to-B retention, supported claims lost, independently established errors removed,
  errors retained, and valid answer leaves lost through filtering; C repair attempts,
  successes, abandonment, latency, and budget use.
- Semantic refusal, malformed input, timeout/tool failure, certificate replay failure,
  and actual forensic error. Refusal or schema mismatch alone does not establish an error.

Use the same deterministic scorer. Actual error labels need independent artifact-grounded
evidence under a frozen rubric, with human review blinded to arm where deterministic
labels are unavailable. Publish the reviewed denominator and unresolved judgments. No
LLM judge, self-grading, or universal false-positive guarantee. A Python implementation
of the exact same rules is a useful matched rules/checking-cost baseline; agreement does
not show that Lean makes the forensic assumptions more accurate.

The neutral A recorder, exact B replay, and shared claim-field projector are implemented.
The original pilot predates this projector and must not receive retrospective bindings.
Aggregate budget accounting, D's complete model routing, and full execution-manifest
validation remain pending. Existing checker/replay, public packaging, and deterministic scoring can
be reused. `manifest.template.json` is an unfinished preparation artifact; changing its flags alone
does not implement them. At execution, no active required field may be unset, a model
alias, or a placeholder. Hash and retain the frozen manifest with every trial.
