# Final reference decisions: proposed, not applied

This evaluator-only review covers exactly the 14 unresolved NIST questions. The
frozen reference, public profile, source answers and saved scores are unchanged.
The companion [review JSON](final_reference_decisions.json) contains source bindings,
per-question decisions and two separate, unapplied JSON Patch proposals.
Nothing here was selected from an investigator's answer or an extraction result.
A source disagreement is not labelled an answer-key error, and no expected value
is replaced to match our application.

Both preserved source-file hashes and all 14 question-span hashes match the
reference. The source is the [NIST v1.32 answer document](https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf),
also available locally under `/Users/paul/Documents/hackpton/data/reference/`.
This pass read the source text and visually checked PDF pages 37, 40 and 52.
The wider prior visual review and its cross-references are documented in
[n3_reference_contracts.md](n3_reference_contracts.md). Page numbers are one-based
PDF pages, not printed footers. This is source review, not proof that an English
interpretation is correct or independent human review.

## Two concrete changes ready for contract review

**Q53: optional carving must not be mandatory.** The private draft currently places
`optional_carving` inside the expected answer, while the public schema requires
only `files`. The source explicitly makes signature carving optional on PDF p52,
text lines 4337-4341. The proposal retains all 17 recovery rows and all five fields
(path, true format, displayed size, viewable, recovery method), moving the carving
statement into source-supplemental material. This fixes our contract's mandatory
scope without changing a source answer.

Before activation, specify `viewable`: recovered content successfully opens or
renders in a compatible viewer; an extension or signature is insufficient. Partial
or failed rendering must remain distinguishable. This criterion does not make a
system's Boolean assertion self-verifying; its evidence support remains separately
reviewable. The current deterministic matcher treats extra fields as wrong, so an
optional appendix must either live outside the scored `answer` or use a tested,
generic unscored-field rule shared by all systems. Merely deleting the private
optional field would incorrectly penalize systems that supply that optional work.
The proposed patch therefore does not yet change `evaluation.status`.

A separately identified [Q53 metadata v1 contract](../contracts/nist_q53_metadata_v1/README.md)
now makes that decision explicit for a new trial: mandatory metadata inventory,
defined reported viewability, and optional appendices outside the scored answer.
Its public/private validators and synthetic matcher checks pass. This does not
apply the patch to the original reference or claim the original 60 questions are
all resolved. The frozen original Q53 remains unevaluable.

**Q33: preserve printed minute precision.** The source prints 16:54-16:58 on PDF
p37, lines 3114-3121. The draft invents seconds and compares UTC `:00` endpoints
with a two-second tolerance. The proposal replaces those two fields with
`start_local_minute_as_printed` and `end_local_minute_as_printed` and removes their
instant matching rules. It retains the printed date and minutes; it does not guess
an offset, inclusive endpoint, or exact action time. Public and private patches
are paired. Q33 remains unresolved because this representation repair does not
settle the other observations' relationship to completed physical disc writing.

These proposals do not require new source facts or an LLM judge. The user has
authorized contract work; the coordinator can adopt explicit decisions and freeze
versions before submissions. Other unresolved semantic choices must be stated,
not hidden inside permissive matching or timestamp tolerance.

## Decisions for all 14 questions

| Question | Source-grounded action | Remaining decision; no automatic full-credit shortcut |
|---|---|---|
| Q1 | Add Section 4.3's RM#1 hash pair as a source addendum; bind required image variants to frozen supplied inputs. | Acquisition versus verification evidence and hash scope are missing from the Q1 table; container digests do not substitute for media digests. |
| Q2 | Preserve the visible partition-2 asterisk. | Define MBR active flag, OS volume or boot capability before choosing a Boolean. Do not equate them. |
| Q6 | Preserve four account rows, printed local times and genuine blank cells. | Declare the display offset and timestamp-field semantics; no inferred one-hour allowance. |
| Q10 | Preserve nine application rows and their printed install times. | Distinguish installer execution, recorded installation and completion; declare time display policy. |
| Q16 | A finite alias for the one singular/plural keyword is supported by the printed row and URL. | Freeze duplicate/exclusion scope; the source omits some items without a general rule. Alias acceptance alone is insufficient. |
| Q19 | Keep the two printed directory references with their source contexts. | Resolve physical container versus registry locator identity; no Office/Outlook global equivalence. |
| Q29 | Preserve trace categories, deletion annotations, wildcard and open-ended scope. | Specify finite path identities and handling of additional valid traces; no basename-only or arbitrary-prefix matching. |
| Q30 | Keep table and quoted-log file/time associations distinct; epoch arithmetic is mechanically checkable. | Choosing an association requires an explicit versioned decision; this patch does not swap expected values. |
| Q33 | Apply the separate minute-precision representation proposal if adopted; retain all11 source rows. | Host observation, method selection, descriptor time and completed write are different claims. |
| Q39 | Require recovered thumbnail identity, cache entry locator and artifact evidence. | Six title strings are not six recovered images; freeze a content comparator/reference set or named review criterion. |
| Q48 | Source context identifies Google Drive sign-out, not generic Windows logoff. | Resolve paths and declare causal comparison semantics while preserving source attribution. |
| Q53 | Apply optional-carving scope clarification if adopted. | Declare viewability and symmetric optional-output handling; retain all17 mandatory rows. |
| Q58 | Build an event-level checklist from Section3 with precision, entities, order and support. | Decide eligibility of scenario-only context versus disk-recoverable observations; four daily labels are incomplete. |
| Q60 | Require an actual renderable diagram or portable specification. | Freeze content adequacy against reviewed events; no exact-layout, image-pixel or title-string substitute for the task. |

Q39 image identity, Q58 event eligibility and Q60 adequacy cannot honestly become
fully scorable by changing status flags. A narrower derivative task is possible,
but it must have a new contract identity and retain the original question as
unresolved. No revised-task score should silently be called the original60 score.

## Second-case readiness

The [DFIR Madness case page](https://dfirmadness.com/the-stolen-szechuan-sauce/) supplies
13 top-level investigation questions plus bonus questions and several evidence
families. Only the desktop disk is local here. Its
[published answers](https://dfirmadness.com/answers-to-szechuan-case-001/) are available,
but describe their own state as provisional and include approximate times.
The author's [timing explanation](https://dfirmadness.com/case-001-the-timing-of-it-all/)
distinguishes host clock data from network time. That requires an explicit clock
policy in any later accuracy contract, not a case-wide undocumented adjustment.

Local inputs, checked by filename/size rather than a fresh image rehash in this review:

- `/Users/paul/Documents/hackpton/data/case2/img/` contains E01-E04, with sizes
  2,147,291,154; 2,147,330,394; 2,147,392,052; and 422,953,421 bytes.
- The accompanying FTK acquisition note names all four segments and records
  matching acquisition/verification MD5 and SHA-1. That is a historical source
  statement; it is not a fresh verification of today's bytes.
- `eval/case2/case_facts.json` is the older8,289-record snapshot. Its errors include
  old JumpList failures and a pre-fix compatibility-cache timestamp failure.
- `/private/tmp/cop-latest-case2-desktop-facts.json` has a recorded64,114-row build,
  also predating the final JumpList fix. Neither snapshot should be relabelled a
  fresh all-reader result.
- The separate prior JumpList validation checked14 containers/47 entries, including
  four empty containers, against an independent byte walk. That validates that
  parser repair, not the completeness of the case or any answer score.
- No local server image, memory image or PCAP was found in the case2 directory.
  No frozen typed case2 reference, scoring profile or answer adapter is present.

The old `eval/case2/exhibits.json` has an unsupported `_note` metadata field for the
new intake validator. New public files fix only the intake configuration and smoke
scope: [smoke-exhibits.json](../case2/smoke-exhibits.json) and
[smoke-profile.json](../case2/smoke-profile.json). They contain no expected answers,
malicious indicators, private reference paths, or clock corrections. The profile
has six generic operational questions and explicitly identifies this as a revised,
desktop-only workflow smoke without an accuracy denominator.

## Exact smoke that is possible now

1. Run new versioned intake against those four desktop segments, initially with
   `windows,system`. This exercises Windows10 artifact dispatch and the repaired
   JumpList reader. Intake hashes inputs and retains reader-health limitations.
2. In a distinct run, query source records, produce a small set of supported formal
   claims, and independently verify them. Check that the report/coverage identify
   this desktop scope and keep unavailable server/memory/network evidence unknown.
3. Optionally exercise one approved `webcloud` collection and staged continuation;
   confirm a new full snapshot, a stable parent hash and freshly checked findings.
4. Record failed readers and known omissions such as unclean Search databases.
   Do not call a record count, successful verification or finished report an answer
   accuracy score. Do not run the NIST adapter on this case.

Example extraction command, prepared but **not executed by this review**:

```sh
python -m app.cli ingest \
  --images /Users/paul/Documents/hackpton/data/case2/img \
  --exhibits eval/case2/smoke-exhibits.json \
  --out /private/tmp/cop-case2-smoke-fresh \
  --title 'DFIR Madness Case001 desktop-only smoke' \
  --readers windows,system
```

Use a new output directory if that path already exists. A live investigator run is
a separate action; this review performed no model calls, extraction, score updates
or source edits. Public-profile and manifest validators passed. The two proposed
patches were checked on in-memory copies only; the frozen source/profile hashes
remain unchanged.
