# Rules

Each rule is a stated assumption about what an artifact means. Lean checks that a claim
follows from the cited facts; it does not check that a rule is true of Windows. Every
certificate lists the rules it used, so a reader can see exactly what was assumed.

| Rule | Assumption | Strength | What it does not establish |
|---|---|---|---|
| R1 | A USBSTOR / setupapi record means a device with this serial was connected to this machine | Strong | Who connected it |
| R2 | A registry mapping links a device serial to a volume serial | Strong | That the volume was not reformatted later (a format assigns a new volume serial) |
| R3 | An LNK or jump-list entry means its target path, on the volume it records, was opened on this machine | Strong | Which person was at the keyboard; only the profile that owns the LNK |
| R4 | Windows keeps the modified time on copy and sets a new created time, so created after modified means the file was copied here | **Heuristic** | Archive extraction and some downloads leave the same signature |
| R5 | A Recycle Bin `$I` record gives the original path and the deletion time | Strong | That the content is unrecoverable |
| R6 | A ReadyBoost (`EMDMgmt`) registry key, or the volume block inside a shortcut, means this PC saw a volume with this label and serial; its time is the key's last write, or when the shortcut's target was opened | Strong | Which physical device carried the volume |
| R7 | The volume serial read from a seized image identifies the volume in that image. A hardware device serial comes only from supported removable-device E01 acquisition metadata or an explicit shared acquisition manifest; otherwise the device identity is scoped to the image and exhibit | Strong | What volume the device held earlier; a USB identity for an image-scoped unknown device; an optical drive serial does not identify its disc |
| R8 | Two volume records share a user-chosen label; this is a candidate association only | **Heuristic** | Physical-device identity or reformatting: labels are not unique |
| R9 | A browser history row means this search URL was visited in this profile at this time | Strong | Who typed it, and that it was typed and not followed as a link |
| R10 | A file system timestamp is what the file system recorded | Strong | That the clock was right, or that the timestamp was not set by a tool |
| R11 | A message stored in the user's mailbox file was sent with this subject, at this submit time, between these display names | Strong | That the named people wrote or read it; for received mail the time comes from the sender's side, not this PC's clock |
| R12 | Optical-disc activity may leave temporary files, exclusive-access locks (`cdrom` event 133 in this image), or CD Burning configuration changes. Each record states only that observation | **Heuristic** | Whether a write occurred or finished, its contents, its physical disc, or use of a particular burning application |
| R13 | A recovered directory entry records a name and timestamps on the examined device. FAT unallocated entries and older UDF allocation-table states are different recovery sources | Strong | A previous filesystem or reformat, the original volume serial, or survival of content; UDF can retain earlier states of the same filesystem |
| R14 | A system setting is what the registry or the image's own structures record (name, value, key last-write time) | Strong | That the value was true at any other time, or who set it |
| R15 | An account record is what the account database or a client's configuration holds | Strong | Who used the account |
| R16 | A logon, logoff, startup or shutdown record is what the account database or an event log recorded | Strong | That every such event was logged; logs roll over and can be cleared |
| R17 | An installed-program record is what the system's uninstall list holds | Strong | That the program was ever run, or is still present |
| R18 | An application artifact names an executable/path and attaches a timestamp with its declared meaning. Only explicit prefetch, UserAssist or process-creation run-time provenance is rendered as execution time | Strong, about the artifact | Compatibility-cache file modification, cache modification, registry last-write or task configuration records do not establish execution at that time. An execution flag cannot turn file mtime into run time. Missing/unknown provenance remains an application observation; no attribution to a user or inference of behavior |
| R19 | A browser history row means this URL was loaded in this browser profile at this time | Strong | Who was at the keyboard, and that the page was read |
| R20 | A download record gives the source URL, the saved path and the start time as the browser stored them | Strong | That the file was opened, or still exists |
| R21 | Text kept by the operating system's search box was typed there | Strong | When, beyond the time the artifact attaches |
| R22 | A cloud client's log or database row records this event for this file | Strong | That the file's content reached or left the cloud; that needs the provider's records |
| R23 | A note's text is what the note application stored | Strong | Who wrote it |
| R24 | A shell-bag or similar record means the folder was displayed in the file browser under this user profile | Strong | When, beyond the time the artifact attaches; what was done in the folder |
| R25 | A change-journal rename record gives the old name, the new name and the time | Strong | Who renamed it, or why |
| R26 | A secondary artifact (search index, thumbnail cache, shadow copy, recent list) holds a record of this path | Strong | That the file still exists, or what it contained |
| R27 | A shadow copy exists with this id and creation time | Strong | What changed between it and the live volume, unless stated by other facts |
| R28 | The SHA-256 of the bytes read for a file. Two records with the same hash have the same content. For an entry recovered from unallocated space the bytes are read as one contiguous run from its first cluster; the record says so | Strong | That the bytes are the file's original content if the run was partly overwritten: a matching hash rules that out, a non-matching one proves nothing |
| R29 | An NTFS change-journal record carries a FILE_DELETE removal flag for this path and volume at its recorded time | Strong, about the record | Exact deletion onset (flags can accumulate until CLOSE), Recycle Bin use, wiping, or unrecoverability |
| R30 | A UDF file-set descriptor read from an identified disc records this timestamp for this volume | Strong, about the descriptor | Examination time, completion of a format or write, or whether a PC-wide lock involved this disc |
| R31 | An NTFS change-journal record carries a FILE_CREATE creation flag for this path and volume at its recorded time | Strong, about the record | Exact creation onset (flags can accumulate until CLOSE), a filesystem creation timestamp, or a copy signature |
| R32 | Journal name, parent-reference and removal-flag observations carry an image-scoped identity consisting of full NTFS volume serial, file record and sequence. Exact identity equality supports joins; each observation retains its own timestamp | Strong, about recorded identities | Creation onset, unchanged content, continuous existence, an earlier event at a later alias, deletion of every hardlink, secure wiping, copying or a disc write. Current MFT names are context only when preceding journal names cannot resolve the historical ancestor chain |
| R33 | A child journal path can be constrained by directory identities and an intact retained USN-v2 byte interval. Every record is size/version/offset/name validated; only zero tail padding to the immediately next page is permitted. A future OLD_NAME needs a following NEW_NAME and no conflicting directory state, creation, removal, rename-new or hard-link change in between. Unknown higher ancestors are marked explicitly | Strong, about reconstructed journal state under the NTFS journal contract | Filesystem creation onset, copies, disc writes, secure wiping, facts outside the validated interval, or an invented current-MFT prefix. This does not prove the journal was never tampered with; the extractor/raw-byte trust boundary remains |
| C1 | A census counts every record of one kind in the evidence file. The kernel checks the count over the list in the certificate; the verifier checks that the list is every record of that kind | Strong, about the records | Anything about events that left no record, or records the extractor does not read. The sentence says so every time |
| T | A tag fact says the extractor (or an LLM, if `prov.source = "llm"`) labeled an entity | Depends on the tag's source | Anything beyond the stated rule; an LLM tag is a judgment, never evidence |

## Sets

A set is a named composition of primitive bricks (`Sets.lean`) with an English template
(`checker/claims.py`). Lean guarantees the composition is checked as written. A human
approves the template, because that is where the meaning lives.

| Set | Rules | Strength | English template |
|---|---|---|---|
| `usbMountedAs u m` | R1, R2 | Strong | USB device {serial} was connected ({time}) and mounted as volume {vol}. |
| `openedFromMount l m` | R2, R3 | Strong | {path} was opened ({time}) from volume {vol}. |
| `copiedHere c m` | R4 | Heuristic | {path} was likely copied onto volume {vol}: it was created there ({time}) after its last modification ({time}). This rests on heuristic rule R4. |
| `deletedAfter d x` | R5 | Strong | {path} was deleted ({time}) after {event}. |
| `deviceHolds u d` | R1, R7 | Strong | USB device {serial} was connected to this PC ({time}). The seized device with that serial holds volume {vol}. |
| `openedFromDevice l d` | R3, R7 | Strong | {path} was opened ({time}) from volume {vol}, the volume on seized device {serial}. |
| `openedFromRecorded l s` | R3, R6 | Strong | {path} was opened ({time}) from volume {vol}, which this PC recorded under the label "{label}" ({time}). |
| `recordedOnDevice s d` | R6, R7 | Strong | Volume {vol}, which this PC recorded under the label "{label}" ({time}), is the volume on seized device {serial}. |
| `sameLabel a b` | R6, R8 | Heuristic | This PC recorded volume {vol} ({time}) and volume {vol} ({time}) under the same label "{label}". A shared label does not identify a physical device; different devices can share it (heuristic rule R8). |
| `usbConnected u` | R1 | Strong | USB device {serial} was connected to this PC ({time}). |
| `opened l` | R3 | Strong | {path} on {volume or network share} was opened ({time}). |
| `searched w` | R9 | Strong | A web search for "{term}" was made in {browser} ({time}). |
| `fileCreatedAt c`, `fileModifiedAt m` | R10 | Strong | {path} was created / last modified on volume {vol} ({time}). |
| `fileDeletedAt d` | R5 | Strong | {path} on volume {vol} was sent to the Recycle Bin ({time}). |
| `emailed e` | R11 | Strong | An e-mail with the subject "{subject}" was sent {from A to B} ({time}). |
| `burnTrace b` | R12 | Heuristic | Optical-disc-related record in the {source}: {trace} ({time}). A record alone does not establish a write, completion, contents or physical disc. Event 133 means an exclusive-access lock; a registry last-write means a configuration change. |
| `deviceExamined u d` | R1, R13 | Strong | USB device {serial} was connected to this PC ({time}). The seized device with that serial has directory entries left in unallocated space. |
| `recoveredOnDevice c d` | R10, R13 | Strong | A directory entry for {path}, created ({time}), was recovered from the recovery area on seized device {serial}. Recovery alone does not establish a reformat; an optical disc may retain older states of the same filesystem. |
| `tagged f s g T` | T | Strong, or judgment for an LLM tag | {entity} is tagged "{tag}" ({rule that computed it, or "an LLM judgment"}). |
| `before a b` | none | Strong | {event a} happened before {event b}: the gap of {Δ} exceeds the combined timestamp uncertainty of {r}. |
| `settingRecorded`, `accountRecorded`, `sessionRecorded`, `programInstalledAt`, `programRan`, `visited`, `downloaded`, `typedInSearchBox`, `cloudEvent`, `noteFound`, `folderRecorded`, `renamed`, `fileRecorded`, `shadowCopyMade`, `contentHashed` (one record each) | R14 to R28 | Strong | One sentence saying what that record holds. `programRan` preserves the artifact's timestamp meaning and states execution time only for explicit run-time sources. |
| `sameContent a b` | R28 | Strong | {path a} and {path b} have identical content: both read as {hash}. |
| `fileRemovedAt r` | R29 | Strong | An NTFS change-journal record for {path} on volume {volume} carries a removal flag ({time}). This is the record timestamp, not necessarily deletion onset; it does not establish wiping or Recycle Bin use. |
| `fileCreationRecordedAt r` | R31 | Strong | An NTFS change-journal record for {path} on volume {volume} carries a creation flag ({time}). This is not a filesystem creation timestamp and cannot be used by `copiedHere`. |
| `volumeRecordedAt v` | R30 | Strong | The UDF file-set descriptor on {disc}, volume {volume}, records its timestamp as {time}. This is descriptor recording time, not examination time or proof of completed formatting/writing. |
| `createdAfterVolumeRecord c v` | R10, R30 | Strong | The filesystem creation timestamp of {path} follows the UDF file-set descriptor recording timestamp on {disc}, on the same volume, by more than combined uncertainty. This orders recorded timestamps; it does not establish a completed burn or copy. |
| `journalNamed n`, `journalParentRecorded p`, `journalRemovalObserved r` | R32 | Strong | A journal name, child-parent reference or removal flag was observed at its recorded time. A name is not creation onset; a removal flag is not secure wiping. |
| `sameJournalFile a b` | R32 | Strong | The two names at their own observation times share the same scoped NTFS file-record identity, not necessarily unchanged contents or simultaneous aliases. |
| `removedFilePreviouslyNamed n r` | R32 | Strong | A later removal-flag observation shares the identity of the earlier name, beyond timestamp uncertainty. It does not assign the removal time to the earlier alias or prove wiping. |
| `journalChildNamedDirectory c p d` | R32 | Strong | The child's name, child-parent reference and directory's name join through their scoped identities. Each retains its own time; no presence at a different-time alias, creation onset, copy or disc write is inferred. |
| `journalPathAt p`, `journalPathForFile n p` | R33; R32+R33 | Strong | A bounded path or explicitly incomplete suffix belongs to the child's journal observation time; a direct name joins only through the same scoped identity. No filesystem birth, copying or disc-write time is asserted. |
| `exactly kind n` | C1 | Strong | The evidence holds exactly {n} {kind} records: {each one}. This counts records in the evidence file. An event that left no record, or a record the extractor does not read, is not counted. |
| `exactlyDistinct kind slot n` | C1 | Strong | The {N} {kind} records in the evidence name exactly {n} different {field}s: {values}. (Same closing note.) |
| `exactlyWith kind slot v n` | C1 | Strong | Of the {N} {kind} records in the evidence, exactly {n} have {field} {v} ("none has" when n is 0). (Same closing note.) |

A census is checked by `counts` in `Census.lean`, not by `holds`: it is about every
record of a kind, so adding a record can make it false, and it cannot be joined to
other claims with `both`.

## Deterministic tags

Tags are computed by plain code in `extractor/tags.py`; each tag fact carries its rule.
Case-specific tags require an explicit public manifest `_policy`, shared with all compared
systems. Its optional fields are `source`, `authorized_device_serials`,
`authorized_device_serials_complete`, and `confidential_path_markers`. An absent policy
adds no authorization or confidentiality labels. Unknown image-scoped device identities
are never classified from the authorization list.

| Tag | Rule | What it does not establish |
|---|---|---|
| `authorized-device` / `unauthorized-device` | A known hardware serial is on the supplied public allowlist; a nonmember is tagged only if `authorized_device_serials_complete` is true | Who owns the device; an incomplete list does not classify nonmembers |
| `confidential` | The path carries a confidential-path marker from the supplied public policy | What the file contains |
| `watch-list-search` | The search term contains a word from a generic watch list written before looking at this case | Intent |
| `e-mail in the Deleted Items folder` | The mailbox file lists every message with this subject in its Deleted Items folder | Who moved it there, or when |
| `same size and last-modified time as a file elsewhere: N bytes, T` | Another file record, on a different volume or in a device's unallocated space, has this size and this last-modified time (within 2 s). A copy keeps both, so this is how a renamed copy shows up | That the contents are the same: nothing was hashed or compared |

## Timestamps

- `t` is UTC microseconds. NTFS stores UTC. FAT stores local time with no zone, so the
  extractor must convert it using the time zone of the machine that wrote it and record
  that zone in provenance. exFAT stores local time plus a UTC offset.
- Windows writes a FAT stamp with the UTC offset in force at the moment of writing, not
  the offset of the stamp's own date. A copy made in March (UTC-4) of a file last
  modified in December stores the December time shifted by 4 hours, not 5. So a FAT
  modified time older than the entry's created time is converted with the offset at
  creation. On this case that reproduces the UTC times exFAT recorded for the same
  files on RM#1; the zone's December offset would be one hour off.
- `res` is the uncertainty of `t`: the true time lies within `(t - res, t + res)`.
  Use 1 for NTFS, 10 000 for exFAT and FAT creation times, 2 000 000 for FAT
  modification times. `before a b` needs a gap larger than `a.res + b.res`.
- A tag fact's `t` is when the tag was assigned, never 0.
