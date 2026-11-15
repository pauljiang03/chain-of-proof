# NIST CFReDS Hacking Case evaluation

This package retains **all 31 official questions** from the
[NIST Hacking Case](https://cfreds-archive.nist.gov/Hacking_Case.html). It defines
typed, deterministic comparison against the
[published answer document](https://cfreds-archive.nist.gov/images/TestAnswers.pdf).
It is a development reference authored from those sources, not an LLM judge, a
historical Mulder grade, or a Lean proof that the English answer key is true.

Give investigators only `questions.json`, the public scenario and supplied
evidence. Its case ID is `nist-cfreds-hacking`; its timezone is deliberately null.
Keep `reference.json`, `sources/TestAnswers.*`, validation outputs and evaluator
tests outside the investigator's workspace. The public profile contains no answer
values or private-key locators. The initial prompt-derived profile is retained in
`sources/questions-public-initial.json`; subsequent refinements specify field
roles and matching conventions without supplying expected values.

The reference is complete at the published answer precision. All 31 questions are
scorable under the explicit conventions below. That does not mean the application
can answer them, that a reported examination occurred, or that every semantic
interpretation has independent review. No application facts, model output or saved
scores were consulted when choosing expected values. Future genuinely unresolved
questions must retain their IDs with `evaluation.status: "unevaluable"` and a
reason; they must never disappear or become silently incorrect.

## Public conventions

- Q16, Q20 and Q22 request a fixed number of examples. The private key retains the
  full source pools. Public `match.list_rules` requires exactly the requested
  number of distinct members; omitted *unrequested* alternatives are not misses.
  Duplicate, unknown or excess submissions do not receive full credit.
- Q3 and Q8 preserve the printed second precision. The declared convention uses
  the contemporaneous display timezone addressed by Q4 and accepts equivalent
  explicit-offset timestamps with **zero added tolerance**. The actual offset is
  private, not disclosed by the public profile. Raw times and conversions are
  retained and checked separately.
- Q1 distinguishes a logical-media digest from compressed-container or segment
  hashes. The [public acquisition notes](https://cfreds-archive.nist.gov/images/hacking-dd/SCHARDT.LOG)
  establish the hash algorithm; the answer document supplies the unchanged
  whole-image digest and comparison result.
- Public display obfuscation is removed only where the source expressly says it
  is absent from the evidence. A two-line file path is joined without its adjacent
  software column, and a MAC address receives conventional colon separators.
- Q15 uses the reference's vendor precision; a more specific model belongs in the
  evidence appendix. The claim that this interface was used during setup still
  needs the stronger setup association, not just vendor text.
- Q16 requests product names. Versions and capability descriptions are retained
  in source context. One differently styled product label is associated with the
  same product explicitly named elsewhere in the official source; this convention
  is recorded, not silently repaired using extracted artifacts.
- Q18 has `nntp_server`. Q21 has `real_name`, `email_address`, `nickname` and
  `alternate_nickname`, bound to the corresponding literal configuration keys.
  No unreported connection parameters are invented.
- Q22 uses the published channel-log basenames as identifiers, including their
  network and suffix. It does not invent a channel sigil or infer chat contents.
- Q25 accepts the published host/service representation. It does not invent a DNS
  hostname for a named service. Supporting URLs and provider context stay outside
  the scored answer.
- Q31 compares the **reported result Boolean**. The report must separately state
  scanner/version/signature date, scope, detections and failures. Boolean agreement
  neither verifies that scanning occurred nor proves historical infection or
  complete absence. The source supplies no reproducible scanner/signature set.

Other strings use case folding and whitespace collapse only. Lists preserve
multiplicity unless the explicitly declared subset policy applies. Explanations,
evidence references, qualifications and optional details belong in top-level
submission appendices or the report; extra fields inside `answer` are additional
assertions under the generic scorer.

## Proof-role requirements and limits

All **38 exact answer leaves** carry `x-claim-requirement`. These public annotations
restrict which reviewed claim roles may supply the application's projected fields.
They do not alter the neutral scorer or require another system to produce Lean
proofs. Catalog compatibility is neither evidence availability nor proof of full
question entailment.

At package preparation, three required stronger roles had no catalog support:
predominant account identity (Q10), interface used during setup (Q15), and
interpreted captured-device type (Q24). Their questions remain scorable. The
application must abstain on unsupported fields instead of substituting an account
name, vendor prefix or raw User-Agent string. Installation-only program fields
likewise cannot be supplied by a mere program mention or execution observation.

## Validation and scoring

```sh
python -m eval.hacking_case.validate --out /new/path/source-audit.json
python -m unittest tests.test_hacking_reference -q
python -m eval.benchmark \
  --reference eval/hacking_case/reference.json \
  --answers /path/to/structured-answers.json \
  --out /new/path/results.json
```

The answer submission uses schema version 2 and this package's exact case ID.
There is no automatic fallthrough to the Data Leakage adapter or reference.
The application can use its generic explicit claim-field projection; other
systems can submit the same public JSON shape. Follow the same frozen public
contract and matching policy for every system.

`sources/manifest.json` binds the exact downloaded HTML, PDF and acquisition note,
the extracted text and the initial public profile. Every question has a source
line span, SHA-256 and PDF pages. Each expected leaf has literal containment or an
explicit reproducible transformation. All four PDF pages were visually checked
by the author; this was not independent review.

`source-audit.json` records validation, not investigator performance. Tests use
synthetic copied-key submissions solely to check contracts, alternate subsets,
missing/false/extra answers, timestamp equivalence, source tampering, key leakage
and proof-role restrictions. Hashes and those tests do not prove source
authenticity, faithful English interpretation, reader correctness or key truth.
