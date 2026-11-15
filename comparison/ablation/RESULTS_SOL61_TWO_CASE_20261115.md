# Sol 6.1 comparison on Data Leakage and Hacking

The latest comparison has a saved answer score for every arm on both cases.
With Lean feedback, Data Leakage has five complete answers among 46 scorable
questions. Hacking has eight complete answers among 31 questions, with three
incorrect answers. Most questions remain unanswered. Certificate checks passed,
but answer coverage remains low.

This is a **legacy-reference-agreement development** result. It uses the frozen
reference and its original matching rules. It does not establish semantic
equivalence with every prose answer. No LLM judged the answers. The stricter
semantic reference drafts remain held.

## Question results

A is a fresh investigator without Lean feedback. B checks A's exact saved
candidate prefix after investigation, with no model calls. C is a separate fresh
investigator with Lean feedback. Each live arm has a 900-second limit and requests
`gpt-6.1-sol`. The two cases ran in parallel on one host; A preceded C within each
case. Scoring began after all live investigators stopped and both B replays ended.

| Case | Arm | Complete | Partial | Unanswered | Incorrect | Unevaluable |
|---|---|---:|---:|---:|---:|---:|
| Data Leakage | A | 4/46 (8.7%) | 6 | 36 | 0 | 14 |
| Data Leakage | B | 4/46 (8.7%) | 6 | 36 | 0 | 14 |
| Data Leakage | C | 5/46 (10.9%) | 7 | 34 | 0 | 14 |
| Hacking | A | 8/31 (25.8%) | 0 | 20 | 3 | 0 |
| Hacking | B | 8/31 (25.8%) | 0 | 20 | 3 | 0 |
| Hacking | C | 8/31 (25.8%) | 0 | 20 | 3 | 0 |

All 60 Data Leakage questions remain visible. Fourteen have unresolved reference
status; they are not scored as failures. Over all 60 questions, the confirmed
complete counts are 4/60 for A/B and 5/60 for C. Hacking retains all 31 questions.
An incorrect question has no matched field. A partial question can contain both
matched and incorrect fields. Thus zero wholly incorrect Data Leakage questions
does **not** mean zero incorrect assertions.

| Case | Arms | Matched fields | Missing | Extra | Unequal |
|---|---|---:|---:|---:|---:|
| Data Leakage | A, B each | 18/1,627 (1.1%) | 1,609 | 14 | 13 |
| Data Leakage | C | 75/1,627 (4.6%) | 1,552 | 14 | 13 |
| Hacking | A, B, C each | 10/52 (19.2%) | 42 | 0 | 3 |

The Data Leakage reference also contains 462 known fields in unevaluable
questions. These are excluded from the 1,627 scorable-field denominator.
Extra and unequal fields are disagreements with the answer contract, not an
independent count of false forensic claims.

Data Leakage C adds partial Q11 and complete Q51. Its other question statuses
match A/B. Hacking Q2, Q4 and Q8 are incorrect in every arm: the fixed scorer
records two value/type mismatches and one timestamp mismatch. These remain
errors under the frozen contract. The reference was not changed to accept them.
The [machine-readable results](RESULTS_SOL61_TWO_CASE_20261115.json) include all
question statuses and field counts without private expected answers.

## Proof checks and retained answers

B verified all 45 Data Leakage candidates. For Hacking, it verified 11 candidates
and rejected one malformed candidate. That malformed candidate was unbound in A,
so removing it changed no answer. A/B scores are equal on both cases.

All 113 Data Leakage C certificates and all 11 Hacking C certificates passed
independent replay. Replay regenerated Lean from the frozen facts and ran the
kernel. This is separate from online acceptance. It does not prove that a claim
answers the requested question or agrees with the reference. These experiment
counts do not claim a separate con-leche pass.

All six projections report zero unsupported bindings, zero dropped bindings and
zero conflicts. Data Leakage retained 113 projected leaves in A/B and 370 in C;
Hacking retained 13 in each arm. Some leaves belong to unevaluable questions.
These counts cannot replace scored fields. The low scores are not explained by
dropped bindings in these submissions. Missing investigation work, unsupported
source meanings and answer scope still require review.

## Execution issues

The first Data Leakage launch failed because its interactive bridge lost stdin.
It produced no evidence calls or answer checkpoint. Its failed attempt remains
retained. A successful transport smoke preceded the separately labeled second
A/C pair. Hacking continued unchanged.

Data Leakage attempt 2 A made 79 bridge calls, saved a checkpoint and later hit
the time limit without a final response. Its checkpoint was scored unchanged.
The last logged tool returned normally at 09:33:19.592 UTC. No later tool request
appears before interruption. The deadline was 09:43:12.948 UTC. The cause of this
post-tool wait remains unknown. An unchanged reported usage counter does not
prove that no generation was in progress.

All four checkpoints were saved within budget. The audit found zero tool calls
started or completed after any deadline. Data Leakage A's bridge cleanup ended
39.190 seconds after its deadline; its recorded elapsed time is 939.190 seconds.
This delay remains an execution limitation, not additional scored investigation.
The other three arms returned final responses within budget. Data Leakage C also
made one invalid question-status update; the tool rejected it and later
checkpoints were valid.

Three earlier retained summary copies contain one extra trailing newline compared
with the original response payload. Exact payload copies are now retained
separately. The sealed originals were not edited. Answer content and bindings are
unchanged; Data Leakage C's sealed response is already byte-exact.

This is one development comparison. Shared-host timing, the transport retry and
the A timeout limit causal conclusions about Lean feedback. Actual provider
revision, model token use and cost were not independently established. The result
does not show universal zero false positives or a gain over Mulder. Mulder and
the planned D arm remain unrun. Historical runs remain linked; their inputs and
constraints differ, so they are not a controlled before/after test of this batch.

## Frozen inputs and audit

Runtime: `cf97b96bfe8598aebf4a940cc939f6a2f192f89b`.
Data Leakage: 409,971 records, facts SHA-256
`c81482c116d55bd3f9d76f15aaf37490dca7f0d2a09b19cb29870bcda0bf8251`.
Hacking: 14,468 records, facts SHA-256
`b0cfceb95ab9e69704daed83b64a00894a6cf7d06a5bc7e4c0d975c21bc31109`.
Extraction reported no failed readers, with 17 and 18 explicit limitations.

The fixed scorer validated 69 bound files and ran the frozen-manifest validator
before and after scoring. All checks passed. Source, saved answers, matching,
question statuses and denominators stayed unchanged. Normalization stayed off.
Full private scores stay separate from the public aggregate report.

Public scoring receipt SHA-256:
`30f6f8165d0205c963950dec92ad675425a4e815e71c58396f5069affe41c1ba`.
Final operational audit SHA-256:
`7907793666576cd768be963eb4ed14e2a099f516465d09690f90114de818e92d`.
Scorer source SHA-256:
`73885427d73b82a89538b41e0086248a99c3b298ce118e35a22498b8937e6333`.

The run source directory is
`/private/tmp/cop-matched-ablation-20261115T0918Z/`.
The durable archive is `runs/dev/matched-ablation-20261115T1019Z/`, with sealed
manifest SHA-256
`36849d2cd24bfaf3a7540c53bfab81f15b5cb959338388eee26a67d6ba60d8dc`.
All 564 files and recorded bindings passed readback checks. The archive excludes
private reference payloads, full private scores and raw internal model traces.
It retains public operational metadata, exact final responses and source hashes.
Previous sealed archives remain intact.
