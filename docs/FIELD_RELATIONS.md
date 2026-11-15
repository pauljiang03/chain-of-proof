# Exact source fields and file-set checks

This batch extends the readers for both NIST cases. It adds 14 fixed attribute
roles and one Lean census form. These are implementation and source checks.
They are not new benchmark scores.

## What changed

| Source | New support | Limit |
|---|---|---|
| Current Windows registry | Effective recorded time-zone name and UTC offset from matching bias fields | No clock or calendar guess. An indirect resource label stays unresolved. |
| Legacy IE cache | Yahoo message-cache filename bound to an allocated URL entry, exact cache file and matching message HTML | The supported legacy layout does not establish ownership, sending or reading. |
| Recycle Bin namespace | Exact executable file set and actual NTFS allocation flags | Only the declared, bounded namespace procedure is complete. This is not all files on disk. |
| Browser history | Full URL, one-pass decoded search term, browser and source timestamp on one occurrence | Only reviewed hosts and routes. Redirect URLs are excluded. No actor attribution. |
| Modern Recycle Bin index | Index filename, full original path and recorded deletion time on one entry | Recovered indexes have an explicit recovery origin. No inference that the bin was emptied or data erased. |
| VSS catalog | Copy ID, set ID, creation time and verified store path on one entry | Catalog metadata is a base-volume source. Store size and snapshot-content claims are not inferred. |
| Sticky Notes | Literal note text, container path and actual container file modification time on one note subject | File time is distinct from the note's own storage timestamp or a user's editing time. |

Typed field timestamps use the declared examination time. Source event times
remain separate values. Missing examination time does not cause a new clock value
to be silently inserted.

## The file-set proof

`filesystemSetDeleted` takes a declaration record, a proposed count and a proposed
Boolean. Lean checks the full declared member list. It checks unique file
identities and known flags. A true result needs a deleted flag for every member.
A false result needs an allocated member. The set must contain 1 to 256 members.
Unknown flags, duplicate members and partial enumeration cannot certify this claim.

The reader does not supply a summary Boolean. Independent replay reads the whole
membership again and rejects a certificate if a member was added, removed or changed.
Both new soundness theorems use no axioms. Python, Lean and SQL retain the same
append-only kind order.

An answer about whether "these files" are deleted also needs the same atomic claim
as the preceding file-count answer. The public contract must require the exact
reviewed Recycle Bin procedure. A generic set count cannot answer that question.

## Real-source checks

- Hacking: the effective timezone observation certifies. The Recycle Bin collector
  supplies a complete four-member set. The supported Yahoo message-cache layout
  supplies a filename observation.
- Data Leakage: the narrow search/index check supplies 55 search occurrences and
  14 index records, with 855 fact rows and no reader issues. The VSS catalog supplies
  all four new fields. The Sticky Notes source supplies a note tuple.
- Data Leakage's effective timezone label remains unavailable. The selected label
  is an indirect `tzres.dll` reference. The reader preserves that limitation.

The source counts above are not counts of correct test answers. The original
question contracts, references and measured submissions are unchanged.

## Validation

The integrated source and answer-runtime code at `5cf4d43` passed the full suite:
1,261 tests ran, 1,260 passed and one platform test was skipped. The earlier
source-only integration run had one missing agent-form declaration. The answer
runtime commit supplied it, and the full combined run passed. Both logs remain.

Seven selected real-source certificates independently replayed. Five also passed
ConLeche. The public projection checks retained 17 supported fields across
Hacking Q4/Q27/Q28/Q29 and Data Leakage Q16/Q41/Q47/Q51. Four invalid bindings
were refused. Separate proof controls refused a wrong role, a wrong aggregate
result and mixed source subjects. VSS size remains unsupported.

The current public drafts have 48 compatible and 310 unsupported Data Leakage
leaf occurrences, and 16 compatible and 22 unsupported Hacking leaves. These
count schema requirements, including repeated alternatives; they are not question
accuracy or extracted-data coverage. Both drafts remain held for readiness review.

The independent [reference audit](../eval/REFERENCE_COMPATIBILITY.json) confirms
that all original question prompts, schemas, expected values and match rules are
unchanged. It does not approve a scoring derivative. Display formats, identifier
and path conventions, the Hacking executable population and the unresolved
Data Leakage references still need explicit decisions. No model experiment ran.

The local archive is `runs/dev/field-relations-20261115T0730Z/`. It preserves
initial parser and validation-script failures as well as successful checks.
The archive is local and is not pushed with the source code.

## Remaining limits

Python still parses source bytes. Lean proves claims about the resulting records
and rules; it does not prove parser correctness or source authenticity. Source
selection, complete-list coverage and actor attribution need their own evidence.
Unsupported source formats and unresolved reference questions remain explicit.

Format references: [Windows time-zone bias](https://learn.microsoft.com/en-us/windows/win32/api/timezoneapi/ns-timezoneapi-time_zone_information),
[URL form decoding](https://docs.python.org/3/library/urllib.parse.html),
[Recycle Bin index layout](https://github.com/libyal/dtformats/blob/main/documentation/Windows%20Recycle.Bin%20file%20formats.asciidoc).
The Yahoo and VSS readers retain their primary format references in their modules.
