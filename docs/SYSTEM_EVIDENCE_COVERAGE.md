# Source support and answer limits

This batch adds source fields for both NIST cases. It is an implementation batch,
not a new accuracy result. The source-support suite passed. Later soundness fixes
and fresh experiment inputs remain under review.

## Source readers

| Source | Support | Meaning limit |
|---|---|---|
| SAM | Account name and validated relative identifier from the same account | The RID must agree with the account key. No benchmark-specific name filter is added to the reader. |
| Current network registry | DHCP fields joined through one exact interface GUID | These are configuration fields. They do not prove a DHCP lease or actual assignment. |
| Current timezone registry | Signed bias values and a retained resource-backed display name | Resource resolution uses bytes from the image and an explicit language. No host locale or code execution is used. Current bias is not proof of historical daylight-saving state. |
| USB registry and SetupAPI | Full literal device and instance identifiers, source type and recorded time meaning | A generated instance identifier is not a hardware serial number. SetupAPI local times remain literal; an ambiguous clock time does not become one UTC instant. |
| FAT and exFAT file times | Creation and modification records tied to one native directory entry and partition | A time comparison requires the same source and file occurrence. It proves a timestamp pattern, not that a person copied a file. |
| Primary MBR | Entry number, sector bounds, boot indicator and an exact filesystem join | The filesystem join needs the same disk and byte bounds. This is not a GPT or complete partition census. |
| Current Search configuration | Registry values and the service start configuration | Service configuration does not prove that the service ran. A directory value does not prove a relation to a particular database. |
| Windows Search ESE | Source row identity, literal paths, URLs, categories and stored times | The fields do not prove browsing, attribution or a filesystem action. No URL is substituted for a missing item path. |
| Snapshot exclusions | Exact retained exclusion patterns | A configured pattern is not proof that a file was omitted from a snapshot. |
| Reviewed EVTX events | Provider, channel, event ID, record ID, parser timestamp and literal account fields | The timestamp has the parser's microsecond precision. It is not a crash time or an embedded performance time. Legacy EVT records do not gain invented EVTX fields. |
| Google Drive | Literal client log fields and unambiguous record relations | A client label does not prove transfer success or a remote deletion time. |
| OLE Office and PDF | Bounded metadata fields and document source identity | Raw FILETIME values and literal PDF date strings remain distinct from filesystem and user-action times. |
| Mail | Retained Unicode, explicitly decoded STRING8 and literal HTML | HTML is not rendered. Message text is not proof that a person sent or read it. |
| Optional PFF recovery | Bounded parser-recovered Unicode properties with a distinct source variant | Parser recovery is not proof of purge, deletion or an unallocated source. The real-source check returned zero recovered items; positive protocol proof checks used synthetic inputs. |
| SQLite WAL | A checksum-validated view through a complete committed transaction | The source includes both the database and its adjacent WAL. No claim is made from an incomplete transaction. |
| Historical files | Explicit VSS selection and bounded comparison of exact paths | Comparison gives observations from each version. It does not infer a transfer direction or a complete history. |

`structured_system` and `cloud_attributes` are part of the default PC reader
selection. Historical comparison requires an explicit CLI command and source
selection. Expensive image hashing and antivirus scanning remain explicit choices.

## Formal and answer support

The fixed catalog adds 94 reviewed roles and signed integer values. It now has
199 roles and 243 fact kinds. Native signed values remain
separate from nonnegative count values. Existing kind identifiers retain their
order. Lean checks the role, value kind and shared source subject. This change
does not add a theorem for unit conversion or historical timezone inference.

Public answer conditions can now exclude explicit text values with an explicit
comparison policy. A missing or ambiguous field does not satisfy a condition.
An answer cannot substitute registry minutes for requested hours, configuration
for an actual assignment, or a bounded extracted set for an unproved population.

Identity checks apply to the claims that need identity. A matching recorded
serial or label remains an observation; it does not establish one physical
device. Notes retain the kind of source timestamp. Hash comparisons retain
recovery and read-method limits. Answer references must still address the same
claim at the declared output path after array assembly and filtering.

The standalone second checker binds each finding to the supplied facts and its
regenerated proof text. It checks an immutable copy of those facts. A missing
proof or a proof of an unrelated statement fails the check.

The optional [representation matcher](../eval/MATCH_NORMALIZATION.md) is disabled
in existing contracts. A future contract must declare its version and reviewed
rules before an investigation starts. Original references, submissions and scores
are not rewritten. A formatting rule cannot supply missing evidence.

## Validation and release gate

At `2f9a3b0`, the combined suite ran 1,528 tests: 1,526 passed and two were
skipped. One skip applies only to other operating systems. The other needs the
reviewed native PFF library; that test passed separately in the source-reader
environment. The public assembler check also passed.

Selected source tuples passed Lean and independent replay. The host, event,
cloud and mail checks also include ConLeche validation. Document and recovered
mail positive checks include explicitly synthetic inputs. These checks are not
counts of correct test answers.

Full extraction found a Dissect filename subtype that the strict value emitter
refused. The reader now converts that validated string subtype to plain text at
three filename boundaries. The emitter remains strict. First attempts and their
diagnostics are retained. Complete snapshots at `1ae4082` contain 409,971 Data
Leakage records and 14,468 Hacking records. No reader failed. They retain 17 and
18 explicit limitations, respectively. These record counts are not test scores.

The first eight reported soundness counterexamples now pass independent
regression checks on the combined source and answer fixes. Positive controls
include actual timestamp proofs from both removable drives and a valid array
reference. Two later optical-reader reports, about virtual-block mapping and
version-specific caching, remain under repair. The snapshots above predate those
repairs and are not approved experiment inputs. The final combined suite and
current demo refresh are still pending.

The local validation archive is `runs/dev/system-evidence-20261115T0805Z/`.
It remains unsealed while final snapshot checks are pending. The comparison is
held. Its prepared compatibility bundle preserves all original answers, matching
rules, statuses and 91 questions. The endpoint is a development comparison under
original matching rules, not semantic equivalence. Normalization remains disabled.

Lean proves statements relative to the extracted facts and declared rules.
Source parsing, authenticity, completeness and the meaning of a question remain
separate trust boundaries. This batch does not establish zero false positives.
