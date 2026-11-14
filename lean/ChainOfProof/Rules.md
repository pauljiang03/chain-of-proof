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
| R7 | The volume serial read from a seized device's image is the volume that device holds now; the device's serial comes from the acquisition record | Strong | What volume the device held earlier: a format assigns a new serial |
| R8 | Two volumes recorded under the same label are probably one device, reformatted | **Heuristic** | Labels are chosen by users and are not unique |
| R9 | A browser history row means this search URL was visited in this profile at this time | Strong | Who typed it, and that it was typed and not followed as a link |
| R10 | A file system timestamp is what the file system recorded | Strong | That the clock was right, or that the timestamp was not set by a tool |
| R11 | A message stored in the user's mailbox file was sent with this subject, at this submit time, between these display names | Strong | That the named people wrote or read it; for received mail the time comes from the sender's side, not this PC's clock |
| R12 | Windows leaves these traces when it writes a disc: temporary files named `DAT#####.tmp`, `FIL#####.tmp`, `POST#####.tmp`, a `cdrom` driver event 133, and a change to the user's CD Burning settings (method from the NIST answer key, question 33) | **Heuristic** | What was written, to which disc, or that the write finished |
| R13 | A FAT directory entry found in a cluster no current file owns was written by an earlier use of the device, for example before a quick format; its name and times are what that entry recorded | Strong | Which file system (volume serial) it belonged to, and that the file's content is still there |
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
| `sameLabel a b` | R6, R8 | Heuristic | This PC recorded volume {vol} ({time}) and volume {vol} ({time}) under the same label "{label}". A shared label suggests one physical device but does not prove it (heuristic rule R8). |
| `usbConnected u` | R1 | Strong | USB device {serial} was connected to this PC ({time}). |
| `opened l` | R3 | Strong | {path} on {volume or network share} was opened ({time}). |
| `searched w` | R9 | Strong | A web search for "{term}" was made in {browser} ({time}). |
| `fileCreatedAt c`, `fileModifiedAt m` | R10 | Strong | {path} was created / last modified on volume {vol} ({time}). |
| `fileDeletedAt d` | R5 | Strong | {path} on volume {vol} was sent to the Recycle Bin ({time}). |
| `emailed e` | R11 | Strong | An e-mail with the subject "{subject}" was sent {from A to B} ({time}). |
| `burnTrace b` | R12 | Heuristic | CD-burn trace in the {source}: {trace} ({time}). Windows leaves this trace when it writes a disc; it does not show what was written (heuristic rule R12). |
| `deviceExamined u d` | R1, R13 | Strong | USB device {serial} was connected to this PC ({time}). The seized device with that serial has directory entries left in unallocated space. |
| `recoveredOnDevice c d` | R10, R13 | Strong | A directory entry for {path}, created ({time}), was recovered from unallocated space on seized device {serial}. It was written before the device's current file system. |
| `tagged f s g T` | T | Strong, or judgment for an LLM tag | {entity} is tagged "{tag}" ({rule that computed it, or "an LLM judgment"}). |
| `before a b` | none | Strong | {event a} happened before {event b}: the gap of {Δ} exceeds the combined timestamp uncertainty of {r}. |

## Deterministic tags

Tags are computed by plain code in `extractor/tags.py`; each tag fact carries its rule.

| Tag | Rule | What it does not establish |
|---|---|---|
| `authorized-device` / `unauthorized-device` | The device serial is, or is not, on the authorized list in the case brief | Who owns the device |
| `confidential` | The path carries the confidential-project marker named in the case brief | What the file contains |
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
