# What support the misses need

This plan uses the frozen [results](results_full.json) and [reference](reference_full.json).
Counts below describe that saved evaluation, not a new extraction or a new score.
The reference and historical result stay unchanged; later fixes need separate run artifacts.

## Denominators and layers

The current reference covers **57 questions and 613 answer rows**. The closed-book subset is
**47 questions and 517 rows**; the other 10 questions, with 96 rows, were open book.
The original key has 60 questions. Questions 58–60, which request a summary, timeline
and diagram, are outside this reference. Some attributes within Q1–Q57 are not matched;
see [the evaluation contract](EVALUATION.md). Full reference coverage is not full
correctness on every part of the original question.
A row is a declared answer item, not necessarily a unique event; some items overlap.

| Frozen diagnostic | Closed book | Open book | Full test |
|---|---:|---:|---:|
| Matching extracted rows | 367 | 95 | 462 |
| Missing extracted rows | 73 | 1 | 74 |
| Entity found, time differs | 9 | 0 | 9 |
| Unsupported by the reference contract | 68 | 0 | 68 |
| Rows stated by the saved miner's certified findings | 340 | 90 | 430 |

Extraction coverage asks whether a matching record is available. Report coverage asks
whether a certified sentence actually states the answer. Neither alone measures precision.
The old miner left **27 available closed-book rows** unstated: all 24 Q23 renames and
three Q52 rename steps. It also left five available Q16 search rows unstated.
These **32 reporting gaps** need claim selection and complete reporting, not new readers.

The primary end-to-end result should score the application's final certified report
on the fixed test, with both row coverage and complete/partial/unanswered questions.
Show extraction, miner-only, AI-only, certificate verification and false-claim rejection
as separate diagnostics. A complete question requires every declared answer item.
Keep the closed-book split visible; do not call the full 57-question test wholly blind.
Use deterministic matchers, not an LLM judge. Findings outside the reference are not
automatically false positives. Lean acceptance still depends on accurate extraction
and on the declared meaning of each rule.

The combined report builder can unite existing miner and investigator claims, deduplicate
them and issue fresh Lean certificates. Such a union is not another AI trial or new evidence.
Selection must remain independent of the answer key; preserve input hashes and provenance.
Free-form conclusions remain outside the primary certified report and its coverage score.

## Prioritized extraction work

The following groups partition the **73 closed-book missing rows**. They identify where
support is needed, not promised recoveries. Raw records must establish each proposed fact.

| Priority and questions | Missing | Support needed |
|---|---:|---|
| 1. Q34 burn staging | 20 | Journal observations plus file/parent identity and historical rename joins. |
| 1. Q52 anti-forensics trail | 21 | Removal observations, complete raw rename names, cloud logs and download evidence. |
| 2. Q29, Q47, Q48, Q50 cloud and snapshots | 15 | Live/VSS file metadata and deletion sources, snapshot storage paths and exclusion registry values. |
| 2. Q19, Q38, Q40, Q42 containers/settings | 8 | Mail/cache/note/index file locations and search-service configuration. |
| 3. Q11, Q13, Q15 application/browser traces | 3 | Exact executable evidence, browser version registry data and individual visit records. |
| 3. Q45 indexed mail | 2 | Search-index mail parsing with message identity and source field provenance. |
| 3. Q1 image hashes | 4 | Hash the declared image representation and retain its exhibit/container identity. |

The 15 cloud/snapshot misses split as Q29=5, Q47=1, Q48=8 and Q50=1.
The eight container/settings misses split as Q19=1, Q38=4, Q40=1 and Q42=2.
Q1's four reference items include repeated digests across image representations; they
are four answer rows, not evidence of four independently missing hash computations.
The **one open-book extraction miss** is Q21 mail; its message also appears in Q45.
Parse each source independently, then link messages by recorded identifiers and content.

## What the journal and Lean additions enable

The reader now emits `fileCreationRecorded` and `fileRemoved`, with approved claim sets
`fileCreationRecordedAt` and `fileRemovedAt`. They state that a journal record carries
a creation/removal flag at its recorded time. Flags can accumulate before close: the
observation timestamp is not automatically the action's onset or filesystem creation time.
Repeated flags retain their USNs and reason flags; the reader groups them within a close
cycle rather than counting each cumulative observation as a separate creation/removal.

Provenance retains volume serial, file-reference record and sequence, parent identity,
raw names, journal offsets and live/VSS source. Missing parents remain unresolved;
reused MFT record numbers must not attach an old event to a later file incarnation.
`fileRemoved` does not mean Recycle Bin deletion, secure erasure or successful wiping.
`fileCreationRecorded` cannot feed `copiedHere`, which requires filesystem timestamps.

Q34 still needs joins through folder history: creation observations use the original
folder names while the test names later renamed folders. A creation flag under an old
path must not be relabeled as though the final path existed at that time.
Certify the identity/rename chain, then state which later path refers to that same file.
A staging-directory observation alone does not establish a completed optical write.

Q52 removal observations can use randomized terminal names. Connect each to its earlier
name using volume, record number, sequence and ordered rename evidence, retaining all
intermediate names. Raw filename characters must survive parsing unchanged.
Of Q52's 21 misses, 11 concern wiped file/directory rows, four rename steps, five other
removal rows and one download row. Removal and renaming do not alone prove overwriting,
the tool responsible, the user's intent or a completed wipe.

The frozen matcher uses `fileCreated` for Q34 and `fileDeleted` for many Q52 answers.
The new observation kinds therefore do **not** automatically close those frozen misses.
Any richer answer contract needs an explicit, versioned mapping with the weaker event
semantics preserved; keep its results separate from the frozen test.

The miner's bounded mode explicitly lists high-volume kinds it omits; `--complete`
includes them in batches. Coverage claims must disclose the mode and omitted counts.
Complete reporting addresses available records without selecting them from the reference.

## Optical evidence and time discrepancies

`volumeRecorded` / `volumeRecordedAt` now expose the UDF file-set recording timestamp
with its raw bytes, descriptor sector, conversion and physical-disc/volume identity.
`createdAfterVolumeRecord` can prove strict timestamp order on that identified volume;
it does not prove formatting, copying or write completion. An examination timestamp
or a host burn event without a recorded target cannot supply a disc attribution.
These additions improve the inference boundary; they do not establish recovery of the
Q1 hash rows, Q34 staging rows or Q56 carved content.

The **nine time mismatches** are Q11=1, Q15=2, Q30=2, Q44=1 and Q45=3.
Inspect the exact source field before changing conversion or choosing another occurrence:
execution versus cached file modification; individual browser visits versus URL summaries;
cloud event time versus file mtime; and indexed-mail time versus sent/received time.
Preserve raw timestamps, timezone/offset, resolution, source record and conversion steps.
For conflicting observations, keep both and identify their semantics. Do not assume a
reference error, widen tolerance to get a match, or shift times to fit expected answers.

## The 68 unsupported rows need different kinds of support

`not_expressible` means the frozen reference has no supported matcher for that item.
It does not mean Lean can never express it, nor that all 68 items are pictures or opinions.

| Questions | Rows | Missing contract or reader support |
|---|---:|---|
| Q3, Q4, Q6, Q7, Q9 | 11 | System/network properties, failed logons and latest-user scope. |
| Q13, Q14 | 12 | Browser version history and artifact-path roles, beyond mere path existence. |
| Q29, Q32 | 3 | Registry traces and a bounded claim about the burning method. |
| Q39 | 6 | Thumbnail decoding and independently checkable content/identity observations. |
| Q43, Q48 | 6 | Index categories, scoped exclusions, last-record selection and event ordering. |
| Q52 | 8 | Account sign-out and deleted-mail records with explicit event semantics. |
| Q53, Q54, Q57 | 5 | Relevance/formatting/hiding claims requiring additional evidence and scoped rules. |
| Q56 | 17 | Carving, document decoding, content identity and partial-recovery status. |

Ordinary properties and paths can gain typed fields and templates. Content recovery needs
readers, byte ranges, hashes and format validation; Lean cannot manufacture missing bytes.
Visual identification needs a separately justified observation layer, not an LLM's verdict
silently promoted into a fact. Negative claims need an explicit searched scope and reader
completeness; “no record in this parsed source” does not mean an action never occurred.

## Validation across datasets

Implement readers and rules against artifact schemas, not case-specific names or dates.
Use synthetic fixtures for renamed parents, reused identities, truncated journals, DST,
duplicate events, incomplete snapshots and partial content. Recheck every new certificate.
For each dataset publish input/reference hashes, extraction failures, unsupported items,
report mode and deterministic scores. Keep tuning cases separate from held-out cases.
Only report an improved score after a fresh, saved run under its declared contract.
