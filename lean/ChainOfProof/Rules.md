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
