# HackPrinceton pitch and demonstration

Prepared on 2026-11-14. The A–D experiment is approved for preparation. It has not run.
Use [the experiment protocol](abcd/README.md) for execution requirements.

## Main message

**Chain of Proof: AI investigates. Lean checks the claim. You can verify the result.**

An investigator needs to distinguish a supported finding from a plausible explanation.
Our AI searches extracted records and proposes a formal claim.
The checker creates a Lean proof from the claim and the cited records.
Only an accepted claim enters the certified report.
Another person can check its certificate without another model call.

The practical objective is to make evidence review easier and make unsupported links visible.
We have not measured analyst time savings or proved that the complete system has no false positives.

## Position relative to Mulder

Mulder already supplies forensic tools, evidence-reference checks, audit trails, and investigation quality gates.
Its architecture also describes a phase that challenges findings.
Do not describe it as an unchecked chatbot.
See [Mulder's architecture](https://github.com/calebevans/mulder/blob/main/docs/architecture.md).

Our distinct mechanism is a typed claim language, Lean verification of the stated conditions,
fixed report sentences, and certificates that a separate verifier can check again.
The inspected Mulder architecture describes citation and workflow checks; it does not describe this Lean certificate mechanism.
This is a specific distinction from that system, not a claim that we invented formal verification or proof-carrying outputs.

A citation identifies supporting material. A formal proof checks the declared relationship between supplied records.
Both still depend on source interpretation and extraction quality.
Use a device-identity example to make this distinction visible.

Mulder may recover more answers. We must measure that.
A lower error rate at useful answer coverage would still be a useful result.
Rejecting every claim would not be a useful result.
The A–D experiment must show retained correct answers as well as rejected claims.

## A two-minute demonstration

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Two records with different device identities | "An AI can cite real records and still connect the wrong device to an event. A reviewer needs to check the connection." |
| 0:20–0:45 | A supported claim and its certificate | "Our AI proposes a claim in a defined language. Lean checks its conditions against these records. This supported claim receives a certificate." |
| 0:45–1:10 | A claim with a mismatched identity, and the refusal | "Here the device identities differ. The checker refuses the claim and shows the failed condition. This is a controlled example, not a measured AI error." |
| 1:10–1:30 | Independent verification, then rejection of an altered certificate | "The verifier checks the certificate again. If I alter a copied field, verification fails. No second language model decides whether to trust it." |
| 1:30–1:50 | The latest frozen result table, or the labelled preparation status | "We measure complete answers, misses, and supported error categories. We compare unchecked proposals, offline verification, online feedback, and Mulder." |
| 1:50–2:00 | The report and its source links | "The proof covers these formal claims and supplied records. Uncertain conclusions stay separate. This gives an analyst a result they can inspect and verify." |

Use `scripts/demo_proof_gate.py` for the controlled example once validated.
Its evidence is synthetic and must remain labelled synthetic on screen.
Show a real saved finding separately if time permits.
Do not present the scripted demo as a live AI investigation or as an A–D result.

If the A–D runs are unfinished, display "Not run" for those cells.
The saved checkpoint at `a0b4fce` has 473 independently verified certificates,
24 of 24 known false probes refused, and 9 complete answers among 46 provisionally scorable questions.
Another 14 of the 60 questions need reference review.
These are three different measurements. Certificate validity is not answer accuracy.

## Fit to the event

The published rubric names creativity, utility, charity, and avidity.
The in-person presentation limit is two minutes.
See the [official event rules](https://hackprinceton-fall-26.devpost.com/rules).

| Criterion | What our demonstration should establish |
|---|---|
| Creativity | A plausible claim can cite real evidence and still fail a precise relationship check. |
| Utility | A user can inspect records, obtain a supported finding, and independently check the result. |
| Charity | Careful evidence handling can reduce unsupported accusations and help incident responders review their work. This is the intended benefit, not an established outcome. |
| Avidity | The team can explain one proof, its limits, a real failure it fixed, and the next useful improvement. |

My recommended main track is Business & Enterprise, which explicitly includes cybersecurity.
Science & Discovery is an alternative if the presentation centers on the evaluation method.
Choose one main track. See the [official event page](https://hackprinceton-fall-26.devpost.com/).

The rules specify an 8:00 AM Eastern submission stop on November 15, while the page banner lists 8:30 AM.
Plan to submit before 8:00 AM.
The rules also require at least 85% of code to be written during the event and attribution of reused work.
Describe actual team contributions and AI assistance accurately; do not claim unverified eligibility or authorship.

## What to finish first

1. Integrate the other terminal's API, scope, and reference-review fixes.
2. Complete the minimum A/B experiment recording and answer projection. Keep C's production gate intact.
3. Freeze and validate the experiment inputs. Run only after finalization and the user's instruction.
4. Rehearse the controlled demonstration. Keep a clearly labelled recording as a fallback.
5. Fill the result table with observed results. Keep unfinished cells blank or marked "Not run".

The ablation is the main evidence for the mechanism.
Mulder supplies external context; it does not determine whether the demonstration is useful.
An unchanged second-case test supplies evidence about generalization when its reference is ready.

## Highest-value improvements before judging

- Show one useful finding from real evidence, with its source and certificate. Keep the synthetic failure example separate.
- Put the claim, relevant records, and verification result together on screen. A terminal demonstration is sufficient if judges can read it.
- Borrow Mulder's clear investigation stages, readable report, and explicit coverage gaps. Do not rebuild its tool catalog for this deadline.
- Explain who uses the tool: an incident responder who must review an alleged device/file connection. Avoid broad claims about every investigative task.
- Show correct answers retained as well as incorrect claims refused. Abstention alone is not success.
- Rehearse the two-minute sequence with someone who has not seen the code. Remove explanations that they cannot follow on the first pass.

The idea has a clear technical distinction. Winning depends on execution and the competing projects; no numerical win probability is justified.
The present risk is limited demonstrated utility and an unclear presentation, not a shortage of advanced features.

## Questions to rehearse

**Why Lean instead of Python checks?** A correct Python checker can enforce the same rules and obtain the same verdicts.
Lean adds kernel-checked proof artifacts for the formal statements. The generator, parsers, language templates, and source interpretation still need review.

**Does this prove that a person stole a file?** No. It can establish specified relationships between supplied records.
Attribution, intent, completeness, and broader causal conclusions can remain unverified.

**Could you achieve no errors by saying nothing?** Yes. That is why we report useful answer coverage together with supported error measurements.

**Are you better than Mulder?** We have a different verification mechanism. We have not completed a fair performance comparison.
The A–D protocol is designed to measure the contribution and tradeoffs.

**What did you build?** Explain the actual claim representation, proof generation, independent verifier, evidence readers, and integration work completed by the team.
Identify reused software and AI assistance. Do not use code volume or agent count as a substitute for understanding the implementation.
