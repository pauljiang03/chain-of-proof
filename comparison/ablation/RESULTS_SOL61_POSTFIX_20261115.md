# Sol 6.1 Data Leakage repeat after the export fix

The repeat did not produce a measured A/C accuracy comparison. A completed; C reached its 900-second cap without a final binding document. C's 1,017 saved claims all independently reverified, but there is no C answer score. The missing submission is an operational failure, retained without repair or an extra-budget rerun.

A is a fresh investigation without checker feedback. B is exact offline whole-candidate verification/filtering of A, with zero model calls. C is a separate fresh investigation with online checker feedback. All use the original 60-question public contract; it remains unannotated. This run does not test the opt-in field-role guard.

| Question outcome | A | B | C |
|---|---:|---:|---|
| Complete | 7 | 7 | unavailable |
| Partial | 22 | 22 | unavailable |
| Unanswered | 16 | 16 | unavailable |
| Incorrect | 1 | 1 | unavailable |
| Unresolved reference | 14 | 14 | no score; contract still contains 14 |

The original draft key has 46 provisionally scorable questions and 14 unresolved questions, including Q53. All 60 remain reported. The Q53 derivative was not substituted. No LLM judge was used.

| Reference atoms | A | B |
|---|---:|---:|
| Matched | 544 | 544 |
| Missing | 1,083 | 1,083 |
| Extra/unexpected | 2,644 | 2,644 |
| Unequal-value/type | 99 | 99 |
| Scorable reference atoms | 1,627 | 1,627 |

Partial questions can contain substantial mismatches. Q15 contributes 2,019 extra atoms and Q12 contributes 484: together 94.667% of extras. These are disagreements with the versioned reference list, not an independently established count of forensic false claims. Browser-record multiplicity, resource/redirect scope, observation-time meaning and service/session scope need review. More matched atoms alone does not establish better answer quality.

B accepted 84 of A's 87 candidates; all 84 certificates independently reverified. Three singleton `both` claims were malformed, not demonstrated false forensic propositions. Their three bindings were already unsupported in A (`claim_part_unavailable`), so they contributed no A fields. B removed no retained answer field, and A/B answer JSON and scores are equal. Serialized files retain their own exact hashes.

Q18 is the sole wholly incorrect question: the retained `programRan` field is `OUTLOOK.EXE`, while the reference expects `Microsoft Outlook 2013`. The program-run observation does not itself establish product/version identity or use for email communication. This is not evidence of a Lean soundness failure or a fabricated executable.

## Export and runtime findings

A retained 3,698 fields, with three unsupported bindings, zero dropped supported bindings and zero conflicts. No `unsupported_schema_reference_or_union` remains in this A projection. Of the five earlier schema-loss questions, Q11 retained 4 fields, Q22 retained 4, and Q45 retained 66; each scored partial. Q55 and Q56 had no submitted bound fields and remain unanswered. Their current blanks cannot be attributed to the former export loss. C has no projection to inspect.

A completed in 810.773 controller-observed seconds. C was interrupted at the recorded 03:48:04 UTC deadline, after a 03:33:04.285524 UTC dispatch. Its raw finalizer elapsed field is 959.653 seconds because finalization observation includes 59.653 seconds of post-interruption administrative cleanup. That is not extra investigator time. The controller retains both timestamps and the explanation. No model output existed when checked immediately after interruption.

A made 349 bridge calls; C made 204. Each had one recorded non-check error from supplying an unsupported `question_id` argument to `plan`. C recorded 1,017 unique online-verified proposals, and all 1,017 independently reverified after it stopped. Certificate counts are not question counts or accuracy counts.

The important reliability follow-up is to save valid, model-authored binding checkpoints during an investigation, with a predeclared final-output reserve. This run's late-only final artifact could not be reconstructed from saved claims without inventing bindings, so it was left unavailable. The separate Hacking pilot declares its own checkpoint policy before launch; it does not repair this result.

## Scope and retained evidence

This is one development attempt per live arm, requested `gpt-6.1-sol`, fresh contexts, identical 900-second caps and procedural isolation. Actual model revision, token use and cost are not independently observed. Other authorized work ran on the same machine. The absent C submission prevents a numerical A/C accuracy conclusion; the earlier completed pair remains historical evidence, not replaced by this failure.

Frozen source: `96cd518d0edae0e5d9999025c1bb5dda72a0274c`.
Facts SHA-256: `a79fcce1015bf73a66779557a6d5235b4ee4d4b1bc9683803cff5f1abc0f5c8d` (335,509 extracted records).
Frozen manifest: `0ffef516312a0e0fbd21c760c016ffb1a0dbe0a4820aa18513b5a90220fb3a39`.
Controller: `86bb7a02f0ec32d8b920cf01acad5a00b0dcd2f3997a8b7c6947330ee4e31f52`.
Retained A: `7f1059e5ad225a7f0d4a1956f3d0c48979265d5264156ac770f08a5bf64e0d83`.
Retained C: `7b1d65d18e601af48d85403a698c2f8aa4ae3c520bee064b169e9883bbd29f2f`.
B replay checkpoint: `c97e89ee0f95f87de23fe5fed846d4ad189164ae205f86948efe361867003f94`.

Local durable archive: `runs/dev/sol61-nist-postfix-20261115T0316Z/`. It retains raw outputs, missing-output marker, candidates, certificates, projection artifacts, exact scoring submissions, full per-question results, controller events, frozen source and input copies. Key reports are `comparison.json`, `audits/answer-and-replay-trace.md` and `audits/operational-and-projection-reviewed.json`. The initial accounting audit is also preserved; its measured-to-unmeasured transition list must not be read as 60 measured regressions.

Machine comparison SHA-256: `2c7ec5f213847818a69522cf7a264740dcc0ce102276d8b5f95e491e0a43b01b`.
