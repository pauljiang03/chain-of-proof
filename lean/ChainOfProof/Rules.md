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
| R6 | A ReadyBoost (`EMDMgmt`) registry key means this PC saw a volume with this label and serial; its time is the key's last write | Strong | Which physical device carried the volume |
| R7 | The volume serial read from a seized device's image is the volume that device holds now; the device's serial comes from the acquisition record | Strong | What volume the device held earlier: a format assigns a new serial |
| R8 | Two volumes recorded under the same label are probably one device, reformatted | **Heuristic** | Labels are chosen by users and are not unique |
| R9 | A browser history row means this search URL was visited in this profile at this time | Strong | Who typed it, and that it was typed and not followed as a link |
| R10 | A file system timestamp is what the file system recorded | Strong | That the clock was right, or that the timestamp was not set by a tool |
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
| `tagged f s g T` | T | Strong, or judgment for an LLM tag | {entity} is tagged "{tag}" ({rule that computed it, or "an LLM judgment"}). |
| `before a b` | none | Strong | {event a} happened before {event b}: the gap of {Δ} exceeds the combined timestamp uncertainty of {r}. |

## Timestamps

- `t` is UTC microseconds. NTFS stores UTC. FAT stores local time with no zone, so the
  extractor must convert it using the time zone of the machine that wrote it and record
  that zone in provenance. exFAT stores local time plus a UTC offset.
- `res` is the uncertainty of `t`: the true time lies within `(t - res, t + res)`.
  Use 1 for NTFS, 10 000 for exFAT and FAT creation times, 2 000 000 for FAT
  modification times. `before a b` needs a gap larger than `a.res + b.res`.
- A tag fact's `t` is when the tag was assigned, never 0.
