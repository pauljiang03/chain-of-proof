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
| UDF optical content | Each virtual block is mapped through the selected allocation state. Cached content uses resolved byte ranges. | Known-byte controls cover separated physical blocks and different historical mappings. The NIST disc check found no content-hash change from these two repairs. This is not an independent filesystem implementation. |
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

At `445ef58`, the combined suite ran 1,638 tests: 1,636 passed and two were
skipped. One skip applies only to other operating systems. The other needs the
reviewed native PFF library; that test passed separately in the source-reader
environment. The later UI merge at `8bf03a0` passed all 128 app tests: 127 passed
and the platform test was skipped. No core source changed in that merge. The
public assembler check also passed.

Later literal-value changes passed 142 app-related tests with one platform skip.
Browser checks covered the overview, full report and short report. Quoted spaces,
tabs and line breaks remain intact. Excerpts have a label. Distinct source strings
are not merged because they differ only by case or spaces.

The unchanged independent invariant harness passes 17 of 18 checks. Its remaining
test expects a copy-pattern certificate from a fixture with no native file
identity. The current checker correctly refuses that fixture. A separate version
with valid identity metadata and the current rule wording passes all 18 checks.
Both original and adapted results remain in the archive. These are bounded tests;
they do not establish the three invariants for every reader and claim form.

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

All ten reported soundness counterexamples now pass checks on the integrated
fixes. Positive controls include actual timestamp proofs from both removable
drives and valid array references. Generated tests compare 810 answer-reference
cases against an independent position calculation. UDF tests compare generated
block layouts and historical mappings against known bytes.

Both complete snapshots were rebuilt at `57c1c5f` after the UDF repair, with the
same record counts and explicit limitations. The current demos were regenerated
and independently replayed. Report summaries no longer infer physical identity
or actions from matching labels, account names or file basenames. Exact finding
statements and citations remain available. Selected full-snapshot checks passed:
five actual Hacking certificates, plus three Leakage certificates for two distinct
cloud observations and an atomic-row control. All passed Lean, replay and the
claim-bound second checker. These are selected proof checks, not complete answers.

The local validation archive is `runs/dev/system-evidence-20261115T0805Z/`.
Its sealed manifest hash is
`9682fb97bf82bfd3d58fb2d54655c56866979c3040beeef553d89472b8babc68`.
A separate supplement at
`runs/dev/system-evidence-literal-supplement-20261115T0913Z/` retains the later
invariant audit and literal-value fixes. Its manifest hash is
`f2f1aa760d56c4bcf0b875f5f8e065df0358dd66143090e8c1d0d9ed1edddac1`.
The first seal remains unchanged. The manifests record source hashes, checks and
retained limitations. The
comparison requires a separate readiness receipt. The prepared compatibility
bundle preserves all original answers, matching
rules, statuses and 91 questions. The endpoint is a development comparison under
original matching rules, not semantic equivalence. Normalization remains disabled.

Lean proves statements relative to the extracted facts and declared rules.
Source parsing, authenticity, completeness and the meaning of a question remain
separate trust boundaries. This batch does not establish zero false positives.
