# N3: decisions proposed for the 14 unresolved reference contracts

Review date: 2026-11-14. Base checkpoint: `a0b4fce7b530581b170dc4a7a5d68cdd57260f63`.
This is an AI-assisted source review, not independent human approval. All 14
questions remain unevaluable in the unchanged reference. No scores, expected
values, public prompts, or investigator inputs were changed.

This file is evaluator-only: it contains answer-source details and must not enter
an investigator's evidence package or prompt.

## Source identity and reading method

The source is NIST CFReDS *Data Leakage Case*, revision 1.32, saved 2018-07-23.
The preserved files were read from
`/Users/paul/Documents/hackpton/data/reference/`:

| File | SHA-256 |
| --- | --- |
| `leakage-answers.pdf` | `218165427fcb2f490b44eccf7fbc9bf3700b938ea976004051a067e79e0da62b` |
| `leakage-answers.txt` | `149266965308d5d7d343e924566a36c9d8963a156d7d0c1dc1f73d6fd90d1bd1` |

Both match `eval/benchmark_nist.json`. Page numbers below are **one-based PDF
pages**, not the printed footer (which is four lower on these pages). Text ranges
are inclusive, one-based lines in the preserved text with its `===== PAGE =====`
markers. The companion [source index](n3_source_index.json) binds every unresolved
question span and the cross-references used below.

PDFium from the already installed `/private/tmp/cop-pdf-review` was used because
Poppler was unavailable. Complete relevant pages were rendered and inspected,
including tables, merged cells, images, the detailed scenario, and its diagram.
The inspected PDF pages were 7-14, 16-18, 24-27, 34-37, 40, 47-48, and 50-55.
Temporary page images remain outside Git at `/private/tmp/cop-n3-pages/`.
No application reports, extracted fact values, new model grades, or internet
sources were used to choose these proposals.

## Smallest decisions worth taking first

1. **Q53:** make the 17 metadata recovery rows required and carving an optional
   appendix, as the source itself says. A complete carving inventory is unnecessary
   for this narrowly defined mandatory part. Publish that scope before trials.
2. **Q16:** approve a single, explicit singular/plural alternative for the first
   keyword, with its unchanged URL, timestamp, and browser. The plural is also
   present in the source's scenario. Define the list-exclusion rule separately.
3. **Q30:** approve an erratum for the two swapped modification-time associations.
   Both the quoted log and Q49 support the same correction. Keep the original
   table and erratum together; do not silently replace the published source.
4. **Q1, Q29, Q48:** use the additional source sections identified below to reduce
   the missing information, while keeping acquisition verification and path
   identity checks as explicit remaining work.

These are proposed decisions, not newly approved scoring rules. Q53's scope
decision and Q16's alternative still need consistent public/private contracts.
The remaining questions should not be made scorable merely to shrink the
unevaluable count.

## Findings and proposed decisions

### Q1 — image hashes and acquisition verification

**Source:** PDF p16, lines 1014-1034; Section 4, pp12-14, lines 801-916;
revision history p55, lines 4474-4485.

The Q1 table omits RM#1, but Section 4.3 explicitly supplies its MD5
`8BFA4230BF4E35DB966B8C1A9321A0B1` and SHA-1
`F6BB840E98DD7C325AF45539313FC3978FFF812C` (p13, lines 836-847).
The history records addition of that subsection in revision 1.31. Thus RM#1 is
missing from the answer table, not from the entire source. Section 4 distinguishes
RM#3 types: types 1/2 have 52,514 sectors, while type 3 has 52,513 and listed read
errors. The question table does not establish acquisition/verification equality.

**Decision proposed:** bind required images to the actual frozen input manifest;
retain acquisition representation and hash scope per image. Add the Section 4.3
candidate through a documented source addendum. Obtain acquisition/verification
records before setting a match Boolean. Do not compare archive/E01-container
digests to decompressed-media digests, assume all RM#3 variants are identical,
or mark an unavailable variant as a missing answer. Full Q1 remains blocked on
the verification evidence and declared input scope.

### Q2 — the meaning of bootable

**Source:** PDF p16, lines 1035-1042.

The asterisk is visibly on partition 2; the first row is blank. The source gives
no definition of that column. This review confirms the transcription, not whether
the asterisk means the MBR active flag, a boot-code capability, or the OS volume.
The existing reference note mentions a raw-image disagreement; no raw-image check
was performed in this lane.

**Decision proposed:** define the requested property before adjudicating its
value. If the contract means an on-disk active flag, bind a separate raw partition
audit and publish an erratum if needed. If it means OS volume, name that field
explicitly. Preserve the original marker as source metadata. Do not treat these
different meanings as interchangeable accepted Boolean alternatives.

### Q6 — local account timestamps

**Source:** PDF p17, lines 1068-1104; timezone context p16, lines 1053-1056.

The caption says a timezone was applied but supplies no offset. Q4 gives Eastern
Time plus a daylight bias. The printed account timestamps therefore do not, on
their own, identify an absolute instant. The table's SID column holds the four
printed numeric identifiers; blank last-login/failure cells must remain distinct
from an unknown submitted answer.

**Decision proposed:** preserve local printed values, and audit the raw account
timestamp fields and their semantics against a declared display-zone policy
before introducing UTC expected values. Do not infer the offset by aligning a
nearby event from another table; similarly timed login and logoff records need
not denote the same event. No case-wide one-hour tolerance or silent fixed UTC-5
conversion should substitute for that decision.

### Q10 — installation timestamps and operation identity

**Source:** PDF pp17-18, lines 1124-1195; scenario p10, lines 652-662;
Q52 p50, lines 4197-4208.

The installation table also has an unspecified timezone-applied caption. Its
Eraser entry is 09:57:31, while the scenario places installation around 10:50 and
Q52 gives 10:50:14 for starting the Eraser installer. Those observations do not
prove the same timestamp field or operation phase. Installation start, completion,
registry date, and subsequent execution must not be collapsed.

**Decision proposed:** identify each required timestamp's source/meaning and its
offset, retaining the nine printed application rows and all other columns. Freeze
source-specific conversions only after that audit. Do not repair an apparent
one-hour discrepancy by shifting every timestamp or selecting whichever time
matches a system's answer.

### Q16 — singular keyword and an incompletely specified list scope

**Source:** PDF pp24-26, lines 1901-2152; first row lines 1915-1920;
scenario p7, lines 208-242.

The first keyword is singular, while the same row's URL contains the plural query.
The scenario also prints the plural (line 221). The table explicitly says some
duplicates and meaningless items were excluded (lines 1906-1910), without a
reproducible general definition of those exclusions.

**Decision proposed:** permit exactly `data leakage method` and
`data leakage methods` for that one row, preserving its other required fields.
Do not use general stemming. Publish how duplicates and other evidence-backed
searches are handled; either freeze a documented deduplication/exclusion rule or
report extra rows separately until scope is decided. A singular/plural change
alone does not make the entire list contract complete.

### Q19 — conflicting mailbox directories

**Source:** PDF p27, lines 2172-2182.

The answer uses `Microsoft\Office`; the quoted Outlook Search registry value
uses `Microsoft\Outlook` for the same OST basename (lines 2173 and 2178).
This is a visible source conflict, not a line-wrap normalization issue.

**Decision proposed:** adjudicate the actual file location with a file-system
entry and the quoted registry reference, retaining both printed paths in the
audit. Publish the selected expected path and reason in an erratum. Do not create
a global Office/Outlook path equivalence or accept basename-only answers. Until
that identity check is signed off, keep Q19 unresolved.

### Q29 — abbreviated cloud paths and trace-list scope

**Source:** PDF p34, lines 2923-2938; Q52 pp50-51, lines 4248-4270.

Q29 prints `\User\informant\AppData\Google\Drive\user_default` and
`\User\informant\Downloads`. Q52's quoted deletion records instead use
`C:\Users\INFORM~1\AppData\Local\Google\Drive\user_default` for the two
SQLite files. This supplies source-internal evidence for `Users` and `Local`,
but not a proof that every short-name path resolves to a particular long name.
Q29 also includes an ellipsis and a registry wildcard rather than a closed
enumeration of every cloud artifact.

**Decision proposed:** approve finite corrections for the specifically reviewed
rows, after verifying short/long account-path identity. Declare the listed traces
as required evidence categories and how additional valid traces are retained.
Preserve deletion annotations and the registry wildcard's intended category.
Do not globally drop `Local`, ignore arbitrary path prefixes, or demand an exact
closed list where the source itself leaves it open.

### Q30 — two modification times are transposed

**Source:** PDF pp34-35, lines 2939-2995; Q49 p48, lines 4003-4062.

The table assigns January 30 to `happy_holiday.jpg` and January 29 to
`do_u_wanna_build_a_snow_man.mp3`. The quoted CREATE records associate the opposite
epochs with those filenames. Q49 independently prints the same associations as
the log, including decimal epochs and UTC-05 conversions:

| Filename | Quoted log `mtime` | UTC by epoch arithmetic | Q49 corroboration |
| --- | --- | --- | --- |
| `happy_holiday.jpg` | `1422563714.5256062` | `2015-01-29T20:35:14.525606Z` | Lines 4050-4052 |
| `do_u_wanna_build_a_snow_man.mp3` | `1422636560.5520115` | `2015-01-30T16:49:20.552011Z` | Lines 4025-4027 |

**Decision proposed:** document a table-transposition erratum based on these two
source locations, retaining the original table unchanged. Adopt the corrected
associations only after reviewer approval. The DELETE records have an explicit
`-0400` log prefix (lines 2974-2987); keep deletion and modification time separate.
Do not broaden timestamp tolerance to cover the transposition.

### Q33 — several timestamp meanings are mixed

**Source:** PDF pp36-37, lines 3039-3163.

The table has eight mastered-disc rows, a registry selection, an RM#3 descriptor
labelled formatting, and a minute-precision interval: eleven rows total. Both
16:41:21 rows really are labelled System event log, including the row listing
temporary files. Lines 3114-3121 give only 16:54-16:58, not exact endpoint seconds.
The source's causal wording and descriptor explanation do not independently
establish a completed physical write from every host observation.

**Decision proposed:** retain all source rows and duplicate timestamps, and declare
their distinct observation/event meanings. Treat the final endpoints as printed
minute bins or bounds, not fabricated `:00` instants with a two-second tolerance.
Audit the descriptor offset and event definitions before approving stronger
claims about formatting/completion. Any source-label correction needs its own
erratum; do not relabel the seventh row solely because it resembles the journal
rows. Keep host trace time separate from proven media-write time.

### Q39 — six thumbnails require an identity contract

**Source:** PDF p40, lines 3312-3319 and the six images on that page.

The answer is a two-by-three set of first-slide thumbnails from
`thumbcache_256.db`. The PDF shows six document titles, but title strings alone
cannot establish that the submitted artifacts came from that cache. The text
span does not contain the image pixels.

**Decision proposed:** require a cache identifier, recovered-entry locator and
artifact digest for each submitted thumbnail, plus an explicit mapping to a
frozen set of six reviewed reference images. Establish reference images from
evidence before choosing any deterministic image comparator; PDF-rendered pixels
need not equal recovered-image bytes. A named reviewer can adjudicate content
identity if no reliable comparator is frozen. Do not grant complete credit for
titles alone or introduce an LLM judge.

### Q48 — paths and the meaning of logoff

**Source:** PDF pp47-48, lines 3960-4002; Q52 pp50-51, lines 4248-4270;
scenario p10, lines 692-696.

Q48 repeats the Q29 path spelling, then attributes deletion of two SQLite files
to logoff. Q52 identifies a **Google Drive account disconnect** and quotes
`Signing Out` followed by deletion of `sync_config.db` and `snapshot.db` at
11:22:48.878 `-0400`. The scenario identifies Google Drive logout too. The source
therefore supports a more specific meaning than an unspecified Windows logoff.

**Decision proposed:** use the same reviewed finite path corrections as Q29.
Define the comparison's logoff as Google Drive sign-out; bind the inference to
the quoted application sequence and compare its time to VSC creation. Preserve
the source's causal statement with that attribution rather than silently reducing
the requested comparison to presence/absence only. The sequence is source
corroboration, not a general theorem that every sign-out deletes those files.

### Q53 — mandatory recovery versus optional carving

**Source:** PDF pp51-52, lines 4301-4342.

The 17 FAT-directory recovery rows are explicit. The carving section makes a
broad relevance assertion and lists formats with an ellipsis (lines 4329-4332).
But the considerations explicitly call signature-based carving optional and say
metadata recovery may suffice (lines 4337-4341).

**Decision proposed:** require the 17 metadata rows with path, true format,
displayed size, recovery method, and viewability; preserve optional carving as a
separate unscored appendix unless a complete carving inventory/relevance rule is
later frozen. Omission of the optional appendix should not block the mandatory
answer. A blanket claim that every other carved file is unrelated should not be
required for full credit. Define viewability evidence rather than equating a
recognized signature with a successfully opened document.

### Q58 — detailed timeline, not four daily labels

**Source:** PDF p53, lines 4423-4431; detailed scenario pp7-10,
lines 175-713; visual summary p11, lines 722-795.

The answer delegates to Section 3, whose rows include minute times, intervals,
files, actions, and context. It explicitly acknowledges that some traces cannot
be exactly identified from the images. The four daily bullets omit these
requirements. Scenario actions such as attempting to leave with media also
include context not necessarily recoverable from a disk image alone.

**Decision proposed:** freeze an event-level checklist from Section 3, with time
precision, required entities, allowed ordering, evidence support, and a declared
distinction between recoverable observations and scenario-only context. Keep
both visible; do not silently score unavailable intent as a missing disk artifact.
Retain all four days and the data-transfer/anti-forensic stages. No full-credit
shortcut based on the daily bullets is justified. Event eligibility and required
detail need review before implementing a deterministic timeline score.

### Q60 — visual-summary adequacy

**Source:** PDF p54, lines 4457-4469 and its diagram; source example p11,
lines 722-795.

The key explicitly permits the analyst's own visual diagram and calls its own
diagram an example. There is no canonical layout, exact graph, or aesthetic
threshold to match. The current candidate strings identify a requested artifact,
not a completed answer.

**Decision proposed:** accept a renderable diagram or portable specification,
then check a publicly declared content checklist derived from the reviewed Q58
events: identifiable actors/media, supported transfer relations, time/order, and
evidence references. Define handling of unsupported relations. Keep stylistic
quality as a separate named-reviewer criterion if wanted; do not exact-match the
example's nodes/pixels or replace the task with two matching strings. Q60 remains
unresolved until that neutral adequacy contract is frozen.

## Validation and handoff

The source index covers exactly the 14 `evaluation.status == "unevaluable"`
questions at this checkpoint. Validation checked both source file hashes, all
14 existing source-span SHA-256 values, and 12 added cross-reference spans.
Q30 epoch conversions were checked with Python's UTC
datetime conversion. All source files were available locally; nothing was
downloaded or installed. Only `eval/review_notes/n3_*` files belong to this lane.

The source hashes establish byte identity, not correctness of the original key.
Reference changes require an explicit versioned decision and matching public
contract updates. This review does not mark independent human review complete,
execute Mulder, or measure system performance.
