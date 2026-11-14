# A/B/C/D runtime review

Read-only implementation review. No model was run, no private key was read, and no
runtime, reference, scorer, or saved evaluation was changed. Implementation is pending.

The minimal sound first experiment is a **paired claim-level gate evaluation**:
A records unchecked proposals; B checks exactly those proposals after A has stopped.
It is not yet a four-way answer-accuracy experiment.

| Arm | Generation and output | What the comparison isolates |
| --- | --- | --- |
| A | Same public case, facts, forms and model; proposal receipt only; unverified output | Proposals without proof feedback |
| B | Offline check of the sealed A log; preserve order and accept/reject entire original proposals | Gate retention on the exact A population; no second investigator |
| C | Same inputs/budget; online Lean check and failure feedback | Generation with proof feedback; a separate model trajectory |
| D | Mulder on the same public questions/evidence package | External system performance, not an isolated Lean ablation |

## Current boundaries that matter

- `agent/tools.py::Workbench.check` checks immediately, deduplicates earlier claims,
  and returns verdicts, rendered sentences and failing values. None may run or leak
  through A's receipt path. Duplicate submissions must remain separate logged events.
- `agent/tools.py::Workbench.conclude` is another feedback/gating path. Keep judgments
  outside this experiment, or store them without validation for both arms; they are
  not part of the certified or primary scored output.
- `agent/brief.py` currently requires checker-certified findings and correction after
  refusals. A needs an honest receipt-only variant; case context, record descriptions,
  public questions, static forms and other investigation advice should stay identical.
- `agent/mcp_server.py` hard-codes `Workbench`, its tool description promises proof
  results, and `agent/run.py` has separate Claude/DeepAgents implementations. A mode
  must propagate through both or be explicitly restricted to the one tested backend.
- `checker/export.py` correctly exports only verified certificates. Do not weaken it
  or create fake verified findings to make A fit the existing bundle format.
- `eval/nist_answers.py::Evidence` admits cited rows from verified findings, then its
  mappings answer questions from actual row kinds and metadata. It does not preserve
  the meaning of an unchecked proposal. Relabeling A as verified could turn a wrong
  `searched(usb_record)` proposal into a correct device answer, or treat an invalid
  device-link proposal as a checked relation. Row hashes bind bytes, not claim truth.
- `eval/pipeline.py` independently verifies before this adapter; keep that boundary.
  `eval/benchmark.py` already scores literal typed submissions without a model judge.
  `eval/submission.py` can extract a model's JSON unchanged, but proves no support.

## Minimal implementation touchpoints

| File/function | Small required change when implementation is authorized |
| --- | --- |
| `agent/tools.py::Workbench` | Receipt-only collection path; separate unverified event log, no checker call or semantic validation |
| `agent/mcp_server.py::main/tools_for` | Explicit mode selection and accurate tool descriptions; same read-only evidence tools |
| `agent/brief.py::investigator_brief` | Shared instructions plus a small mode-specific submission/feedback block |
| `agent/run.py::main/run_claude_code/run_deepagents` | Bind mode and input hashes; preserve raw transcript and record outputs; do not invoke verified-bundle export for A |
| New offline replay module | Read sealed A log, call existing `checker.check` in order, write B into a new directory, independently verify accepted certificates |
| New focused tests | Receipt path never calls checker; exact replay including duplicates/invalid claims; input mismatch refusal; A unchanged after B |

Keep the existing checker, verified export, verifier, answer adapter and benchmark
unchanged for this first milestone. No new orchestration framework is needed.

Seal A only after its process exits. Record the facts/public profile/prompt/model/tool
versions and hashes, ordered tool-call and batch positions, raw proposal payloads,
stable event IDs, and final log hash. B must require the same facts hash and preserve
that A log byte-for-byte. It must not repair IDs, split a failed conjunction, replace
values, infer missing evidence, or rerun A. B's logs and feedback are never visible to A.
Report malformed syntax, unsupported forms, unresolved IDs, kernel refusal and verified
claims separately. A refused proposal is not automatically a ground-truth false claim.
Record model tokens, calls and time plus proof overhead; B has no generation budget.

## What is still needed for four answer-accuracy cells

A/B/C need one frozen, claim-faithful answer projection. A possible small contract is
literal submitted values plus question/field pointers and supporting proposal IDs.
B may remove values but must not replace them with the cited records' correct values.
Checking those claims alone does **not** prove their entailment of the submitted values;
value-to-claim binding and metadata interpretation must be checked or clearly marked
unverified. An arbitrary wrong value cannot become certified merely by citing a valid
but unrelated claim. Missing/unsupported values stay absent; they are not repaired.

Until that contract and adversarial tests exist, do not publish four comparable answer
accuracy cells. Existing certified-evidence coverage and direct model-JSON accuracy
are different measurements. Freeze the common projection and protocol before new runs;
freeze the private evaluation separately, outside all investigation tool environments.

Safe first step: a small synthetic sealed A log with valid, invalid, duplicated and
wrongly linked proposals, followed by deterministic B replay and non-mutation tests.
It needs no model invocation or answer key. The defensible pitch is measuring filtering
separately from feedback-driven investigation, with machine-checkable evidence links.
This review establishes neither a novelty priority claim nor correctness of extraction,
natural-language interpretation, intent, or complete answers.
