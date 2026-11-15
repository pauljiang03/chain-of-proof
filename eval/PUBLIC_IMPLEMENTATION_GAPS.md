# Remaining public implementation gaps

Review base: `e1b4f70`. These proposals use public prompts, schemas and reader
source code only. They contain no case answers, private reference or score.
Proposed role names need approval by the reader/checker owner. Adding a role does
not establish that the required evidence exists in a particular source snapshot.
The requested matched Sol 6.1 experiment is conditional on resolved launch gaps,
reviewed contracts and a new frozen setup; it is not currently launched.

## Ownership and completed batch

- Root terminal: readers, fixed roles, Lean, source checks and main integration.
  Initial targets: Hacking Q4 timezone, Q27 Yahoo message-cache classification,
  Q29 deletion state of the exact referenced executable set.
- Answer terminal: public mappings, projection/conditions, readiness and bounded
  native answer-tool output. `durable_ablation` owns neutral completion feedback,
  checkpoint diagnostics and coverage annotation handling in its isolated lane.
- Third terminal: implemented Q27 Yahoo message-cache classification, Q47 VSS
  catalog tuples and Q41 literal Sticky Notes/container timestamps.

The source and public mapping batch now implements Data Leakage Q16, Q41, Q47
(except size) and Q51, plus Hacking Q4, Q27 and Q28/Q29. The exact declared-set
count and deletion Boolean share a reviewed extraction definition; Q29 requires
the unique Q28 binding from the same atomic claim. Every aggregate supporting
record is source checked. Q51 requires all three typed index attributes even for
partial bindings and one common origin across the reviewed origin alternatives.
The rows below retain the source requirements and boundaries for review; other
proposed capability additions are not represented as completed by this batch.

## Concrete source and relation proposals

| Public target | Source basis and implementation requirement | Boundaries that remain |
|---|---|---|
| Data Leakage Q1 image MD5/SHA1 | One atomic image-specific pair must establish logical-image subject and both exact digest roles. | Generic tuple subject is not an image-identity selector; partial rows cannot bypass that condition. |
| Q2 partition number, bootable flag, start and total sectors, filesystem | MBR parsing already has the first four values. Join the actual filesystem by disk identity **and** byte offset, then emit one partition tuple. | Offset alone can join different disks. Computed size is not a source-printed size; MBR enumeration is not a complete partition census. Review an exact whole-image source origin. |
| Q4 timezone display/bias | Selected timezone definition has Display; SYSTEM has Bias, StandardBias and DaylightBias. Define the exact sign/display convention and active vs standard offset. | Signed values require a reviewed native type. Generic fallback timezone is insufficient. |
| Q6 account/name/RID/count/enabled | SAM F/V parsing supplies these values. Add RID and a predicate for exclusion of exactly the five names stated in the public question; condition every leaf on it. | Names-key time may mean creation or rename. NT-hash decryption is absent. Source-local display and absent-value semantics need separate rules. |
| Q9 DHCP interface fields | Join exact interface GUID between Tcpip Interfaces and NetworkCards.ServiceName. Retain DHCP-specific fields without static fallbacks. | EnableDHCP plus an IP is configuration; assignment requires reviewed server/lease evidence. All eight fields need the same eligible-interface subject. |
| Q12 event records in the requested local-time interval | Emit provider/channel/EventRecordID, exact source timestamp and reviewed startup/shutdown/logon/logoff description on one event occurrence. | Local-window eligibility needs source-confirmed timezone, explicit interval boundaries and correct event-time meaning. No EventID may be invented for SAM/registry rows. |
| Q16 search URL/query/browser/time | `_searches` has the full URL but currently retains a truncated URL only in provenance. Emit four typed fields on one occurrence and map the complete row through a tuple. | Use full URL and exact browser-history time meaning; not a claim about who typed it. |
| Q29 cloud artifact service/type/path | Classify actual Google Drive log/SQLite containers and preserve exact container path on one subject. | Filename alone is not classification. A deleted flag requires the same artifact filesystem identity. |
| Q30 cloud filename/modified/deleted time | Relate CLOUD_ENTRY and CLOUD_DELETE by canonical log-container plus document ID; retain distinct server modification/deletion fields. | Reject unresolved document-ID display fallbacks and unrelated local-entry RawEvent times. |
| Q31 cloud account | Emit a dedicated account role from the exact credential-use log occurrence. | Credential use does not establish a successful logon time. |
| Q41 Sticky Notes content/container file time | Parse note content on a per-container/note subject; retain the actual container file mtime separately from note-storage mtime, with validated format membership. | Storage-entry time is not file mtime; neither is a user action time. |
| Q42 Search configuration fields | Exact registry key/value-name/value tuples from Search configuration and the current WSearch service key. | Service Start does not prove actual running/indexing. Database location needs an explicit configuration-to-database relation. |
| Q44/Q46 Search indexed fields | Native per-ESE-container/table/DocID URL/path and DateModified/DateCreated, with reviewed category/path/date-window predicates. | Different timestamp columns stay distinct. Indexed times are not actor browsing or file-creation events. |
| Q47 VSS catalog copy/set/path/time | `_shadow_copies` already retains these catalog fields. Emit one catalog-entry tuple under the **base-volume** source origin. | Not a VSS-content origin. No size from file length or changed-file sums. |
| Q50 OST snapshot exclusion setting | Exact current-control-set FilesNotToSnapshot key/value-name/pattern tuple, conditioned on the OutlookOST value name. | Configuration is not proof that bytes were omitted from a particular snapshot or why they are absent. |
| Q51 recycle index/path/deletion time | Validated `$I` v1/v2 source supplies the index filename, full drive-qualified original path and deletion timestamp. Emit one index-entry tuple. | Do not strip the drive or assert unrecoverability. |
| Hacking Q4 | Reviewed effective timezone label/offset using the selected current control set and appropriate active-bias/DST evidence. | Stored standard bias alone is not the effective current offset. |
| Hacking Q27 | Content-based Yahoo Mail **message** classification joined to the exact browser-cache filename. | A Yahoo host, generic cache filename or mailbox-looking text is insufficient. |
| Hacking Q29 | A source-bound deleted-state aggregate over exactly the executable population referenced by Q28, with checked set identity. | A single flag or equality of unrelated counts does not identify the referenced set. |

## Source selections requiring actual evidence review

- Q48/Q49 name no VSS copy ID, unique creation instant, or oldest/latest selector.
  Do not invent a selection. A future all-copy policy needs a frozen inventory of
  parser-validated origins and explicit per-copy identities/relationships.
- Q56/Q57 name the optical exhibit but no recovered entry or descriptor identity.
  A union of arbitrary recovery origins would weaken the current row meaning.
- Q55/Q58/Q59/Q60 need directional copy, event, diagram-edge or component rules.
  Those relations must determine the source of each component; choosing a broad
  case-wide origin union cannot establish them.

## Evidence and interpretation gaps that generic tuples cannot close

- Latest successful logon needs eligible events, ordering and population coverage;
  configured usernames and largest SAM counters are insufficient.
- Predominant use needs a defined usage metric, interval, population and maximum.
- Suspect installation, browser use, email communication, victim identity and
  referenced-document/capture attribution need actual identity/use relations.
- mIRC configuration fields do not establish settings during an online session.
  An application-name condition establishes configuration family only.
- A DBX mailbox name does not establish current subscription. A configured mail
  address does not establish who used it.
- Mail body/subject and OOXML properties retain literal content. They do not by
  themselves establish actor identity, Word/Desktop/resignation classification,
  filesystem dates, or a particular print event.
- Older WordWheelQuery rows lack exact per-query input times. A key last-write
  timestamp cannot be copied onto every query.
- Census completeness and global absence remain separate from source observations.

## Answer preservation and readiness

The completion lane now exposes saved checkpoint coverage, surviving bindings,
pending inventory pages and removed authored bindings in bounded neutral
diagnostics shared by A/C. These are work-progress counts, not proof feedback or
question completeness. Native output is paged with explicit size bounds while
full answers stay durable and inspectable. No coordinator may fabricate missing bindings.

The readiness review must distinguish implemented capability, absent source
evidence, unsupported interpretation, source-selection gaps and experimental
setup. None is silently marked complete to launch the conditional experiment.
