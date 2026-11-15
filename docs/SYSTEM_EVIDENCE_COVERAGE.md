# Source support and answer limits

This batch adds source fields for both NIST cases. It is an implementation batch,
not a new accuracy result. The complete batch is still under integration review.

## Source readers

| Source | Support | Meaning limit |
|---|---|---|
| SAM | Account name and validated relative identifier from the same account | The RID must agree with the account key. No benchmark-specific name filter is added to the reader. |
| Current network registry | DHCP fields joined through one exact interface GUID | These are configuration fields. They do not prove a DHCP lease or actual assignment. |
| Current timezone registry | Signed bias values and a retained resource-backed display name | Resource resolution uses bytes from the image and an explicit language. No host locale or code execution is used. Current bias is not proof of historical daylight-saving state. |
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

The fixed catalog adds reviewed signed integer values. Native signed values remain
separate from nonnegative count values. Existing kind identifiers retain their
order. Lean checks the role, value kind and shared source subject. This change
does not add a theorem for unit conversion or historical timezone inference.

Public answer conditions can now exclude explicit text values with an explicit
comparison policy. A missing or ambiguous field does not satisfy a condition.
An answer cannot substitute registry minutes for requested hours, configuration
for an actual assignment, or a bounded extracted set for an unproved population.

The optional [representation matcher](../eval/MATCH_NORMALIZATION.md) is disabled
in existing contracts. A future contract must declare its version and reviewed
rules before an investigation starts. Original references, submissions and scores
are not rewritten. A formatting rule cannot supply missing evidence.

## Validation and release gate

Focused tests and selected source checks are in progress. The host reader has
passed checks on both cases. Selected Leakage account, signed timezone and DHCP
configuration tuples passed Lean, independent replay and ConLeche. These checks
are not counts of correct test answers.

The full combined suite, final source receipts and release archive are still
pending. The accuracy experiment remains held. The independent reference review
must define the comparison, then the full inputs and code must be frozen before
the authorized investigator runs begin.

Lean proves statements relative to the extracted facts and declared rules.
Source parsing, authenticity, completeness and the meaning of a question remain
separate trust boundaries. This batch does not establish zero false positives.
