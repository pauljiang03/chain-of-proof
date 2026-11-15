# Typed source fields and coherent answers

This batch adds working reader, proof and answer-export paths. It contains no new
model experiment or accuracy score. The original test contracts, private
references and measured runs remain unchanged.

## Implemented paths

| Area | Implemented behavior |
|---|---|
| Coherent fields | `attributeTuple` proves 2–8 distinct typed attributes for one scoped source subject. Every member must pass the role, value-kind and identity checks. |
| OS configuration | Exact `CurrentVersion`, `CurrentBuildNumber` and `SystemRoot` fields join the existing product, owner and installation-time attributes. Build numbers use a checked unsigned decimal conversion. |
| Execution artifacts | Reviewed Prefetch, UserAssist and Security records retain source time, source type and time meaning. Prefetch and UserAssist also retain raw and interpreted counters. |
| Artifact locations | The new `artifact_containers` reader validates browser-history, PFF mail-store, Thumbcache and Sticky Notes formats before it emits their paths. |
| Mail content | The same PFF reader emits bounded, literal Unicode subject and body properties. Missing, empty and malformed properties stay distinct. |
| Document metadata | The new `document_metadata` reader emits bounded OOXML core properties after it checks package relationships, content types and XML roots. |
| Answer admission | Strict projection checks allowed values, constant values and declared conditions on attributes in the same atomic claim. Omitting an output column does not remove its source-family requirement. |

There are 25 new fixed roles. Role names are part of the reviewed compiler catalog.
The agent cannot create a new role by supplying a label. The tuple is one atomic
claim, so related answer fields can use it without borrowing values from unrelated
parts of a conjunction. The tuple soundness theorem and generated certificates
have no axioms.

All tuple fields cite every supporting record. Field roles, row relationships and
source selections still apply. The source-family condition uses the typed value
inside the same claim. It does not trust candidate provenance or another claim.
For example, each supported Q11 field requires a Prefetch or UserAssist source in
that tuple, even if the investigator omits the source column. Security records keep
their own label and cannot supply that field by omitting or changing the label.

## Source meaning and limits

Execution timestamps describe retained artifact fields. Attribute timestamps remain
examination time. A counter is not an independent count of actual human actions.
For XP UserAssist, the reader retains the raw counter and the explicit subtraction
of five. A raw value below five produces no interpreted count. Security records
receive no invented counter. Generic cache and task observations do not become
typed execution records.

Artifact paths bind a concrete source locator, the full container SHA-256 and all
four source-origin fields. A virtual filesystem alias becomes a Windows drive path
only when exactly one drive mount refers to the same filesystem object. Familiar
names or equal volume serials are insufficient.

Container validation has finite file, byte, record and parser-operation limits.
SQLite checks use the base database only; they do not replay a WAL. Empty legacy IE
files without an allocated history record do not receive the history subtype.
PFF content support covers retained Unicode `PR_SUBJECT` and `PR_BODY` values.
It does not convert HTML, decode unknown ANSI text or recover purged messages.

OOXML metadata support covers selected document types in bounded Windows user
folders. It checks relationships and declared part types using the
[Open XML package model](https://learn.microsoft.com/en-us/office/open-xml/general/how-to-create-a-package)
and [package relationship types](https://learn.microsoft.com/en-us/dotnet/api/system.io.packaging.package.getrelationshipsbytype).
It preserves literal XML property text. Creator names do not prove authorship;
document dates do not become filesystem or event times. Legacy binary Office
documents, PDF metadata, unsupported package variants and oversized files are not
silently interpreted. This is structural validation, not full schema validation
or an authenticity check.

## Real-source checks

Fresh snapshots used only five readers: `system`, `host_attributes`,
`application_identity`, `artifact_containers` and `document_metadata`.
They do not replace the full benchmark snapshots.

| Retained source observation | Data Leakage PC | Hacking Case PC |
|---|---:|---:|
| Total records in this limited snapshot | 3,711 | 2,761 |
| Reviewed execution occurrences with typed metadata | 98 | 109 |
| Validated browser-history containers | 5 | 7 |
| Validated Thumbcache containers | 18 | 0 |
| Validated Sticky Notes containers | 1 | 0 |
| Validated PFF stores | 1 | 0 |
| Literal Unicode mail subjects / bodies | 14 / 1 | 0 / 0 |
| OOXML documents with core properties | 1 | 0 |

Zero is output from these readers, not proof of source absence. Data Leakage keeps
two empty-history classification diagnostics. Hacking keeps two such diagnostics
and the unavailable registered binary `cmmgr32.exe`.

The first check found one overly strict Thumbcache validation. A bounded slot had
an empty-record marker but retained residual bytes. The reader now accepts only
the constrained empty-slot form; it records residual-byte hashes and does not
interpret those bytes as content. Nonempty length mismatches still fail. The fix
follows the format distinction used by
[Thumbcache Viewer](https://github.com/thumbcacheviewer/thumbcacheviewer/blob/master/thumbcache_viewer_cmd/thumbcache_viewer_cmd.cpp).
The earlier failing snapshot remains in the archive. Exact mount resolution also
removed duplicate Hacking history observations reached through virtual aliases.

The final facts SHA-256 values are
`41010ae7e99dfe15126cb1ff51d2c19333d1f3447a9ff3a05273b74512910b08`
(Data Leakage) and
`033de65ca6758492524780529521f92550ecd19bedc77bb89532c333b51d59fc`
(Hacking).

Nine selected Data Leakage certificates and four Hacking certificates passed the
Lean kernel and independent replay. Both deliberate mixed-subject tuples were
refused. Public-contract projection retained 20 Data Leakage bindings and two
Hacking bindings. One additional, valid narrow execution certificate was refused
as a Q11 answer because it lacked the required source-family attribute. These are
mechanical controls, not scored answers.

The full combined suite at `6c1031f` ran 1,100 tests in 138.544 seconds: 1,099
passed and one platform test was skipped. No model was called. The first projection
script expected a generic refusal reason; the implementation correctly returned
the more specific missing-condition reason. The corrected script passed, and the
earlier log remains retained.

Two small follow-ups have separate focused checks. The source-inspector update
passed 24 UI checks. The compact agent-facing catalog passed 43 catalog, answer
and checkpoint checks. It shares repeated role definitions and reduces the
serialized catalog from 118,198 to 59,533 bytes (49.6%). The full internal catalog,
available fields and verification rules are unchanged. Eight public-draft tests
and the assembler check also passed after refreshing the draft's code-hash receipt.
An initial focused command used the wrong test-module name; its failure log is
retained with the corrected run.

## Remaining work

The reviewed Data Leakage derivative now has 41 catalog-compatible leaf
occurrences and 317 explicitly unsupported ones. This adds 20 compatible
occurrences across 12 field shapes; 13 questions have at least one compatible
leaf. Repeated schema branches count separately. These numbers are not answered
questions, evidence availability or accuracy. Hacking remains at 13 compatible
and 25 unsupported leaf requirements.

Both derivatives remain held. Exact source selections, unsupported joins and
stronger meanings still need work. A configuration value cannot establish the
settings during an earlier session, a named person, predominant use or current
subscription. A scanner observation cannot establish global malware absence.
Complete inventories and historical path gaps remain separate problems.

The public-only Hacking review identified three possible later additions: a
reviewed effective time-zone label and offset, content-based Yahoo mail-cache
filename classification, and a deleted-state aggregate for the exact referenced
Recycle Bin executable set. Each needs its own source and relationship checks.
An application-name filter alone does not supply these meanings.

The 14 unresolved Data Leakage reference contracts, native-provider validation and
the full matched comparison also remain unfinished. No LLM judge is used.

## Implementation pins

- `14eaa97`: tuple proofs and the fixed role catalog.
- `faa219a`: readers and their focused tests.
- `e0d6b37`: answer projection, same-part conditions and public derivatives.
- `6d4ddc1`: real-source Thumbcache and filesystem-alias corrections.
- `6c1031f`: combined implementation, including the replay fix and new logo.
- `571ce42`: readable source-inspector properties with full provenance retained.
- `db83036`: compact tool catalog; internal validation catalog unchanged.
- `e1b4f70`: refreshed code receipt for the unrun public derivative.

See [WORKSTREAMS.md](../WORKSTREAMS.md) for ownership and the unchanged measured
results. The local validation archive is
`runs/dev/supported-answer-fields-20261115T0655Z/`.
Its manifest inventories 164 files (32,409,992 bytes). All copied artifacts and
manifest entries were rechecked. The manifest SHA-256 is
`42b850d6e515fd7443c76428d15a660ca7abca0f22549c6eb73880d4995ab324`.
Large local evidence and validation outputs are not stored in Git.
