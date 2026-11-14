"""The claim surface the agents write, and its two renderings: Lean and English.

Agents propose instances of approved sets, snapped together with "both":

    {"usbMountedAs":    [usb, mount]}            R1+R2
    {"openedFromMount": [lnk, mount]}            R3
    {"copiedHere":      [created, modified]}     R4 (heuristic)
    {"deletedAfter":    [deletion, event]}       R5
    {"tagged":          [fact, "obj"|"aux", tag_fact, tag_id]}
    {"before":          [a, b]}
    {"deviceHolds":        [usb, device_exam]}       R1+R7
    {"openedFromDevice":   [lnk, device_exam]}       R3+R7
    {"openedFromRecorded": [lnk, volume_record]}     R3+R6
    {"recordedOnDevice":   [volume_record, device_exam]}  R6+R7
    {"sameLabel":          [volume_record, volume_record]} R8 (heuristic)
    {"usbConnected": [usb]}  {"opened": [lnk]}  {"searched": [search]}
    {"fileCreatedAt": [created]}  {"fileModifiedAt": [modified]}
    {"sameContent": [content, content]}  {"contentOf": [created, content]}   R28
    one-record forms for every other kind (settingRecorded, programRan, visited, ...)
    {"both":            [claim, claim, ...]}
    {"exactly": [kind, n]}  {"exactlyDistinct": [kind, slot, n]}
    {"exactlyWith": [kind, slot, entity_id, n]}      census: about ALL records of a kind

Numbers are fact ids (and one tag id). Nothing here accepts free text, so the Lean
term and the English sentence are functions of the claim tree and the cited facts
alone. Each set mirrors a definition in lean/ChainOfProof/Sets.lean: add both together.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Tuple

from .facts import KINDS, Fact, FactSource

MAX_PARTS = 64
MAX_CENSUS = 500          # a census cites every fact of its kind
SLOTS = ("obj", "aux")
STRENGTHS = ("strong", "heuristic", "judgment")   # weakest last

Claim = Tuple  # ("both", Claim, Claim) | (set_name, args)


class ClaimError(ValueError):
    pass


# ---- English, from fixed templates ------------------------------------------------

def _utc(t: int) -> str:
    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=t)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _span(us: int) -> str:
    if us < 1_000:
        return f"{us} µs"
    if us < 1_000_000:
        return f"{us / 1e3:g} ms"
    return f"{us / 1e6:g} s"


UNALLOCATED = "unallocated space of device "   # prefix of the area id the extractor writes


def _where(place: str) -> str:
    """How a file record's `aux` reads in a sentence."""
    if place.startswith(UNALLOCATED):
        return (f"an earlier file system of device {place[len(UNALLOCATED):]} (a directory "
                f"entry recovered from unallocated space)")
    if place in ("", "(none)"):
        return "a volume the record does not name"
    return f"volume {place}"


def _none(text: str) -> bool:
    return text in ("", "(none)")


def _who(account: str) -> str:
    return "the machine" if _none(account) else f"account {account}"


_EVENT = {
    "usbInsert": "the connection of USB device {obj}",
    "volumeMount": "the mounting of USB device {obj} as volume {aux}",
    "lnkTarget": "the opening of {obj} on volume {aux}",
    "fileCreated": "the creation of {obj} on {where}",
    "fileModified": "the last modification of {obj} on {where}",
    "fileDeleted": "the deletion of {obj} from volume {aux}",
    "webSearch": 'the web search "{obj}"',
    "emailSent": 'the sending of the e-mail "{obj}" {aux}',
    "cdBurn": "the CD-burn trace ({obj})",
    "tag": 'the tagging of {obj} as "{aux}"',
    "volumeSeen": 'this PC recording volume {aux} under the label "{obj}"',
    "volumeOnDevice": "the examination of device {obj}, which holds volume {aux}",
    "unallocatedOnDevice": "the examination of the unallocated space of device {obj}",
    "systemSetting": 'the system setting "{obj}" ({aux})',
    "accountSeen": "the record of account {obj} ({aux})",
    "sessionEvent": "the {obj} recorded for {who}",
    "programInstalled": "the recorded installation of {obj}",
    "programRun": "the recorded run of {obj}",
    "webVisit": "the visit to {obj} in {aux}",
    "fileDownloaded": "the download of {obj} from {aux}",
    "localSearch": 'the text "{obj}" typed into the {aux}',
    "cloudFile": 'the cloud record "{aux}" for {obj}',
    "noteText": 'the {aux} note "{obj}"',
    "folderOpened": "the {aux} record of folder {obj}",
    "fileRenamed": "the renaming of {obj} to {aux}",
    "fileSeen": "the {aux} record of {obj}",
    "shadowCopy": "the creation of shadow copy {obj}",
    "fileContent": "the reading of the content of {obj}",
}


def _event(f: Fact, src: FactSource) -> str:
    aux = src.string(f.aux)
    text = _EVENT[f.kind].format(obj=src.string(f.obj), aux=aux, where=_where(aux),
                                 who=_who(aux))
    return f"{text} ({_utc(f.t)})"


def _cap(text: str) -> str:
    return text[0].upper() + text[1:]


def _en_before(args, facts, src):
    x, y = facts[args[0]], facts[args[1]]
    return (f"{_cap(_event(x, src))} happened before {_event(y, src)}: the gap of "
            f"{_span(y.t - x.t)} exceeds the combined timestamp uncertainty of "
            f"{_span(x.res + y.res)}.")


def _en_usb(args, facts, src):
    u, m = facts[args[0]], facts[args[1]]
    return (f"USB device {src.string(u.obj)} was connected ({_utc(u.t)}) and mounted as "
            f"volume {src.string(m.aux)}.")


def _en_opened(args, facts, src):
    l, m = facts[args[0]], facts[args[1]]
    return f"{src.string(l.obj)} was opened ({_utc(l.t)}) from volume {src.string(m.aux)}."


def _en_copied(args, facts, src):
    c, m = facts[args[0]], facts[args[1]]
    return (f"{src.string(c.obj)} was likely copied onto {_where(src.string(c.aux))}: it was "
            f"created there ({_utc(c.t)}) after its last modification ({_utc(m.t)}). "
            f"This rests on heuristic rule R4.")


def _en_deleted(args, facts, src):
    d, x = facts[args[0]], facts[args[1]]
    return (f"{src.string(d.obj)} was deleted ({_utc(d.t)}) after {_event(x, src)}.")


def _en_device_holds(args, facts, src):
    u, d = facts[args[0]], facts[args[1]]
    return (f"USB device {src.string(u.obj)} was connected to this PC ({_utc(u.t)}). The "
            f"seized device with that serial holds volume {src.string(d.aux)}.")


def _en_opened_device(args, facts, src):
    l, d = facts[args[0]], facts[args[1]]
    return (f"{src.string(l.obj)} was opened ({_utc(l.t)}) from volume {src.string(l.aux)}, "
            f"the volume on seized device {src.string(d.obj)}.")


def _en_opened_recorded(args, facts, src):
    l, v = facts[args[0]], facts[args[1]]
    return (f"{src.string(l.obj)} was opened ({_utc(l.t)}) from volume {src.string(l.aux)}, "
            f'which this PC recorded under the label "{src.string(v.obj)}" ({_utc(v.t)}).')


def _en_recorded_device(args, facts, src):
    v, d = facts[args[0]], facts[args[1]]
    return (f'Volume {src.string(v.aux)}, which this PC recorded under the label '
            f'"{src.string(v.obj)}" ({_utc(v.t)}), is the volume on seized device '
            f"{src.string(d.obj)}.")


def _en_same_label(args, facts, src):
    a, b = facts[args[0]], facts[args[1]]
    return (f"This PC recorded volume {src.string(a.aux)} ({_utc(a.t)}) and volume "
            f'{src.string(b.aux)} ({_utc(b.t)}) under the same label "{src.string(a.obj)}". '
            f"A shared label suggests one physical device but does not prove it "
            f"(heuristic rule R8).")


def _en_usb_connected(args, facts, src):
    u = facts[args[0]]
    return f"USB device {src.string(u.obj)} was connected to this PC ({_utc(u.t)})."


def _en_opened_plain(args, facts, src):
    l = facts[args[0]]
    where = src.string(l.aux)
    if where in ("", "(none)"):
        return (f"{src.string(l.obj)} was opened ({_utc(l.t)}). The record does not name "
                f"the volume.")
    place = f"network share {where}" if where.startswith("\\\\") else f"volume {where}"
    return f"{src.string(l.obj)} on {place} was opened ({_utc(l.t)})."


def _en_searched(args, facts, src):
    w = facts[args[0]]
    return f'A web search for "{src.string(w.obj)}" was made in {src.string(w.aux)} ({_utc(w.t)}).'


def _file_time(f, src, verb: str) -> str:
    place = src.string(f.aux)
    if place.startswith(UNALLOCATED):
        return (f"A directory entry for {src.string(f.obj)}, {verb} ({_utc(f.t)}), was recovered "
                f"from the unallocated space of device {place[len(UNALLOCATED):]}.")
    if place in ("", "(none)"):
        return f"{src.string(f.obj)} was {verb} ({_utc(f.t)}). The record does not name the volume."
    return f"{src.string(f.obj)} was {verb} on volume {place} ({_utc(f.t)})."


def _en_created(args, facts, src):
    return _file_time(facts[args[0]], src, "created")


def _en_modified(args, facts, src):
    return _file_time(facts[args[0]], src, "last modified")


def _en_file_deleted(args, facts, src):
    d = facts[args[0]]
    return (f"{src.string(d.obj)} on volume {src.string(d.aux)} was sent to the Recycle Bin "
            f"({_utc(d.t)}).")


def _en_emailed(args, facts, src):
    e = facts[args[0]]
    return (f'An e-mail with the subject "{src.string(e.obj)}" was sent {src.string(e.aux)} '
            f"({_utc(e.t)}).")


def _en_burn_trace(args, facts, src):
    b = facts[args[0]]
    return (f"CD-burn trace in the {src.string(b.aux)}: {src.string(b.obj)} ({_utc(b.t)}). "
            f"Windows leaves this trace when it writes a disc; it does not show what was "
            f"written (heuristic rule R12).")


def _en_device_examined(args, facts, src):
    u, d = facts[args[0]], facts[args[1]]
    return (f"USB device {src.string(u.obj)} was connected to this PC ({_utc(u.t)}). The "
            f"seized device with that serial has directory entries left in unallocated space.")


def _en_recovered(args, facts, src):
    c, d = facts[args[0]], facts[args[1]]
    return (f"A directory entry for {src.string(c.obj)}, created ({_utc(c.t)}), was recovered "
            f"from unallocated space on seized device {src.string(d.obj)}. It was written "
            f"before the device's current file system.")


# One record, one sentence. Each says what the artifact records, not more: a record of
# a run is not proof of who ran it, and a time is the time the artifact attaches.

def _en_setting(args, facts, src):
    f = facts[args[0]]
    name, value = src.string(f.obj), src.string(f.aux)
    if _none(value):
        return f'The system records "{name}" at {_utc(f.t)}.'
    return f'The system setting "{name}" is recorded as "{value}" (record time {_utc(f.t)}).'


def _en_account(args, facts, src):
    f = facts[args[0]]
    return (f"An account named {src.string(f.obj)} is recorded ({src.string(f.aux)}; "
            f"record time {_utc(f.t)}).")


def _en_session(args, facts, src):
    f = facts[args[0]]
    return f"A {src.string(f.obj)} is recorded for {_who(src.string(f.aux))} ({_utc(f.t)})."


def _en_installed(args, facts, src):
    f = facts[args[0]]
    version = src.string(f.aux)
    name = src.string(f.obj) + ("" if _none(version) else f" {version}")
    return f"{name} is recorded as installed ({_utc(f.t)})."


def _en_ran(args, facts, src):
    f = facts[args[0]]
    path = src.string(f.aux)
    where = "" if _none(path) else f", path {path}"
    return f"A record shows {src.string(f.obj)} ran ({_utc(f.t)}{where})."


def _en_visited(args, facts, src):
    f = facts[args[0]]
    return f"The {src.string(f.aux)} history records a visit to {src.string(f.obj)} ({_utc(f.t)})."


def _en_downloaded(args, facts, src):
    f = facts[args[0]]
    return (f"A download from {src.string(f.aux)} to {src.string(f.obj)} is recorded "
            f"({_utc(f.t)}).")


def _en_typed(args, facts, src):
    f = facts[args[0]]
    return (f'The text "{src.string(f.obj)}" is recorded as typed into the {src.string(f.aux)} '
            f"(record time {_utc(f.t)}).")


def _en_cloud(args, facts, src):
    f = facts[args[0]]
    return (f'A cloud-client record reads "{src.string(f.aux)}" for {src.string(f.obj)} '
            f"({_utc(f.t)}).")


def _en_note(args, facts, src):
    f = facts[args[0]]
    return (f'A {src.string(f.aux)} note reads "{src.string(f.obj)}" (last modified '
            f"{_utc(f.t)}).")


def _en_folder(args, facts, src):
    f = facts[args[0]]
    return (f"A {src.string(f.aux)} record names the folder {src.string(f.obj)} (record time "
            f"{_utc(f.t)}).")


def _en_renamed(args, facts, src):
    f = facts[args[0]]
    return f"{src.string(f.obj)} was renamed to {src.string(f.aux)} ({_utc(f.t)})."


def _en_file_recorded(args, facts, src):
    f = facts[args[0]]
    return (f"The {src.string(f.aux)} holds a record of {src.string(f.obj)} (record time "
            f"{_utc(f.t)}).")


def _en_shadow(args, facts, src):
    f = facts[args[0]]
    return (f"Shadow copy {src.string(f.obj)} of volume {src.string(f.aux)} was created "
            f"({_utc(f.t)}).")


def _on(f: Fact) -> str:
    """Where a content record was read from, taken from the record's own provenance."""
    exhibit = f.prov.get("exhibit")
    return f" on exhibit {exhibit}" if exhibit else ""


def _read_how(f: Fact) -> str:
    """How the bytes were read, when the record says it was not an ordinary file read
    (a recovered entry, a derived layout). Such bytes may not be the file's own."""
    how, layout = f.prov.get("read_as"), f.prov.get("layout")
    if not how and not layout:
        return ""
    text = " The bytes were read as " + str(how or "one run") + (f" ({layout} layout)" if layout else "") + "."
    if layout or str(f.prov.get("recovered")) == "True":
        text += " If that space was reused since, they are not the file's original content."
    return text


def _en_content(args, facts, src):
    f = facts[args[0]]
    return (f"The content of {src.string(f.obj)}{_on(f)}, read from the image, has "
            f"{src.string(f.aux)}.{_read_how(f)}")


def _en_same_content(args, facts, src):
    a, b = facts[args[0]], facts[args[1]]
    return (f"{src.string(a.obj)}{_on(a)} and {src.string(b.obj)}{_on(b)} have identical "
            f"content: both read as {src.string(a.aux)}.")


# ---- Census: statements about all the records of one kind ----------------------------

# kind -> (what one record is, what `obj` holds, what `aux` holds)
_NOUN = {
    "usbInsert": ("USB connection", "device serial", "second field"),
    "volumeMount": ("volume mount", "device serial", "volume serial"),
    "lnkTarget": ("file-open", "path", "volume or share"),
    "fileCreated": ("file-creation", "path", "volume or area"),
    "fileModified": ("file-modification", "path", "volume or area"),
    "fileDeleted": ("Recycle Bin", "path", "volume"),
    "webSearch": ("web-search", "search text", "browser"),
    "emailSent": ("e-mail", "subject", "sender and recipient"),
    "cdBurn": ("CD-burn trace", "trace", "place it was found"),
    "tag": ("tag", "tagged entity", "tag"),
    "volumeSeen": ("recorded-volume", "label", "volume serial"),
    "volumeOnDevice": ("device-examination", "device", "volume serial"),
    "unallocatedOnDevice": ("unallocated-space", "device", "area"),
    "systemSetting": ("system-setting", "setting", "value"),
    "accountSeen": ("account", "account name", "kind of account"),
    "sessionEvent": ("session-event", "event", "account"),
    "programInstalled": ("installed-program", "program", "version"),
    "programRun": ("program-run", "executable", "path"),
    "webVisit": ("web-visit", "URL", "browser"),
    "fileDownloaded": ("download", "saved path", "source URL"),
    "localSearch": ("search-box", "text", "place it was typed"),
    "cloudFile": ("cloud-client", "file", "service and event"),
    "noteText": ("note", "text", "application"),
    "folderOpened": ("folder", "folder", "artifact"),
    "fileRenamed": ("rename", "old name", "new name"),
    "fileSeen": ("secondary file", "path", "artifact"),
    "shadowCopy": ("shadow-copy", "shadow copy id", "volume"),
    "fileContent": ("file-content", "path", "content hash"),
}
CENSUS_NOTE = ("This counts records in the evidence file. An event that left no record, or "
               "a record the extractor does not read, is not counted.")
LIST_UP_TO = 40


def _records(n: int, kind: str) -> str:
    return f"{n} {_NOUN[kind][0]} record{'' if n == 1 else 's'}"


def _slot_name(kind: str, slot: str) -> str:
    return _NOUN[kind][1 if slot == "obj" else 2]


def _en_total(args, facts, src):
    kind, n = args
    if n == 0:
        return f"The evidence holds no {_NOUN[kind][0]} record. {CENSUS_NOTE}"
    text = f"The evidence holds exactly {_records(n, kind)}"
    rows = sorted(facts.values(), key=lambda f: (f.t, f.id))
    if len(rows) <= LIST_UP_TO:
        text += ": " + "; ".join(_event(f, src) for f in rows)
    return f"{text}. {CENSUS_NOTE}"


def _en_distinct(args, facts, src):
    kind, slot, n = args
    values = sorted({src.string(getattr(f, slot)) for f in facts.values()})
    name = _slot_name(kind, slot)
    text = (f"The {_records(len(facts), kind)} in the evidence name exactly {n} different "
            f"{name}{'' if n == 1 else 's'}")
    if 0 < len(values) <= LIST_UP_TO:
        text += ": " + "; ".join(values)
    return f"{text}. {CENSUS_NOTE}"


def _en_total_with(args, facts, src):
    kind, slot, value, n = args
    how_many = "none has" if n == 0 else f"exactly {n} {'has' if n == 1 else 'have'}"
    return (f"Of the {_records(len(facts), kind)} in the evidence, {how_many} "
            f"{_slot_name(kind, slot)} {src.string(value)}. {CENSUS_NOTE}")


def census_actual(part: Claim, facts: Dict[int, Fact]) -> int:
    """What the count really is, in plain Python. Feedback for a refused census only:
    the verdict is the kernel's."""
    name, args = part
    rows = list(facts.values())
    if name == "exactly":
        return len(rows)
    if name == "exactlyDistinct":
        return len({getattr(f, args[1]) for f in rows})
    return sum(getattr(f, args[1]) == args[2] for f in rows)


def _en_tagged(args, facts, src):
    f, slot, g, tag_id = args
    entity = src.string(getattr(facts[f], slot))
    if _is_judgment(facts[g]):
        basis = "an LLM judgment, shown as an assumption and not as evidence"
    else:
        basis = f"rule: {facts[g].prov.get('rule', 'deterministic tag')}"
    return f'{entity} is tagged "{src.string(tag_id)}" ({basis}).'


def _is_judgment(tag_fact: Fact) -> bool:
    return tag_fact.prov.get("source") == "llm"


# ---- The approved sets ------------------------------------------------------------

@dataclass(frozen=True)
class SetDef:
    params: Tuple[str, ...]      # each "fact", "slot" or "const"
    lean: str                    # the Lean function it becomes
    rules: Tuple[str, ...]
    strength: str
    english: Callable


SETS: Dict[str, SetDef] = {
    "before": SetDef(("fact", "fact"), ".before", (), "strong", _en_before),
    "usbMountedAs": SetDef(("fact", "fact"), "Sets.usbMountedAs", ("R1", "R2"), "strong", _en_usb),
    "openedFromMount": SetDef(("fact", "fact"), "Sets.openedFromMount", ("R2", "R3"), "strong",
                              _en_opened),
    "copiedHere": SetDef(("fact", "fact"), "Sets.copiedHere", ("R4",), "heuristic", _en_copied),
    "deletedAfter": SetDef(("fact", "fact"), "Sets.deletedAfter", ("R5",), "strong", _en_deleted),
    "tagged": SetDef(("fact", "slot", "fact", "const"), "Sets.tagged", ("T",), "strong",
                     _en_tagged),
    "deviceHolds": SetDef(("fact", "fact"), "Sets.deviceHolds", ("R1", "R7"), "strong",
                          _en_device_holds),
    "openedFromDevice": SetDef(("fact", "fact"), "Sets.openedFromDevice", ("R3", "R7"), "strong",
                               _en_opened_device),
    "openedFromRecorded": SetDef(("fact", "fact"), "Sets.openedFromRecorded", ("R3", "R6"),
                                 "strong", _en_opened_recorded),
    "recordedOnDevice": SetDef(("fact", "fact"), "Sets.recordedOnDevice", ("R6", "R7"), "strong",
                               _en_recorded_device),
    "sameLabel": SetDef(("fact", "fact"), "Sets.sameLabel", ("R6", "R8"), "heuristic",
                        _en_same_label),
    "usbConnected": SetDef(("fact",), "Sets.usbConnected", ("R1",), "strong", _en_usb_connected),
    "opened": SetDef(("fact",), "Sets.opened", ("R3",), "strong", _en_opened_plain),
    "searched": SetDef(("fact",), "Sets.searched", ("R9",), "strong", _en_searched),
    "fileCreatedAt": SetDef(("fact",), "Sets.fileCreatedAt", ("R10",), "strong", _en_created),
    "fileModifiedAt": SetDef(("fact",), "Sets.fileModifiedAt", ("R10",), "strong", _en_modified),
    "fileDeletedAt": SetDef(("fact",), "Sets.fileDeletedAt", ("R5",), "strong", _en_file_deleted),
    "emailed": SetDef(("fact",), "Sets.emailed", ("R11",), "strong", _en_emailed),
    "burnTrace": SetDef(("fact",), "Sets.burnTrace", ("R12",), "heuristic", _en_burn_trace),
    "deviceExamined": SetDef(("fact", "fact"), "Sets.deviceExamined", ("R1", "R13"), "strong",
                             _en_device_examined),
    "recoveredOnDevice": SetDef(("fact", "fact"), "Sets.recoveredOnDevice", ("R10", "R13"),
                                "strong", _en_recovered),
    "settingRecorded": SetDef(("fact",), "Sets.settingRecorded", ("R14",), "strong", _en_setting),
    "accountRecorded": SetDef(("fact",), "Sets.accountRecorded", ("R15",), "strong", _en_account),
    "sessionRecorded": SetDef(("fact",), "Sets.sessionRecorded", ("R16",), "strong", _en_session),
    "programInstalledAt": SetDef(("fact",), "Sets.programInstalledAt", ("R17",), "strong",
                                 _en_installed),
    "programRan": SetDef(("fact",), "Sets.programRan", ("R18",), "strong", _en_ran),
    "visited": SetDef(("fact",), "Sets.visited", ("R19",), "strong", _en_visited),
    "downloaded": SetDef(("fact",), "Sets.downloaded", ("R20",), "strong", _en_downloaded),
    "typedInSearchBox": SetDef(("fact",), "Sets.typedInSearchBox", ("R21",), "strong", _en_typed),
    "cloudEvent": SetDef(("fact",), "Sets.cloudEvent", ("R22",), "strong", _en_cloud),
    "noteFound": SetDef(("fact",), "Sets.noteFound", ("R23",), "strong", _en_note),
    "folderRecorded": SetDef(("fact",), "Sets.folderRecorded", ("R24",), "strong", _en_folder),
    "renamed": SetDef(("fact",), "Sets.renamed", ("R25",), "strong", _en_renamed),
    "fileRecorded": SetDef(("fact",), "Sets.fileRecorded", ("R26",), "strong", _en_file_recorded),
    "shadowCopyMade": SetDef(("fact",), "Sets.shadowCopyMade", ("R27",), "strong", _en_shadow),
    "contentHashed": SetDef(("fact",), "Sets.contentHashed", ("R28",), "strong", _en_content),
    "sameContent": SetDef(("fact", "fact"), "Sets.sameContent", ("R28",), "strong",
                          _en_same_content),
    # census forms: Lean type `Census`, checked by `counts` against every fact of the kind
    "exactly": SetDef(("kind", "count"), ".total", ("C1",), "strong", _en_total),
    "exactlyDistinct": SetDef(("kind", "slot", "count"), ".distinct", ("C1",), "strong",
                              _en_distinct),
    "exactlyWith": SetDef(("kind", "slot", "const", "count"), ".totalWith", ("C1",), "strong",
                          _en_total_with),
}
CENSUS = ("exactly", "exactlyDistinct", "exactlyWith")


# ---- Parsing ----------------------------------------------------------------------

def _is_id(a) -> bool:
    return isinstance(a, int) and not isinstance(a, bool) and 0 <= a < 2**63


def parse(obj) -> Claim:
    claim = _parse(obj)
    if len(parts(claim)) > MAX_PARTS:
        raise ClaimError(f"a claim may have at most {MAX_PARTS} parts")
    return claim


def _parse(obj) -> Claim:
    if not isinstance(obj, dict) or len(obj) != 1:
        raise ClaimError(f"a claim is an object with exactly one key, got {obj!r}")
    (name, args), = obj.items()
    if name == "both":
        if not isinstance(args, list) or len(args) < 2:
            raise ClaimError('"both" takes a list of two or more claims')
        items = [_parse(a) for a in args]
        if any(i[0] in CENSUS for i in items):
            raise ClaimError("a census statement (exactly...) stands alone; it cannot be "
                             'part of "both"')
        claim = items[-1]
        for p in reversed(items[:-1]):
            claim = ("both", p, claim)
        return claim
    if name not in SETS:
        raise ClaimError(f"unknown claim {name!r}; expected one of {sorted(SETS)} or 'both'")
    params = SETS[name].params
    if not isinstance(args, list) or len(args) != len(params):
        raise ClaimError(f'"{name}" takes {len(params)} arguments {list(params)}, got {args!r}')
    for kind, a in zip(params, args):
        if kind == "slot":
            ok, want = a in SLOTS, 'one of "obj", "aux"'
        elif kind == "kind":
            ok, want = isinstance(a, str) and a in KINDS, f"a record kind, one of {list(KINDS)}"
        else:
            ok, want = _is_id(a), "a non-negative integer"
        if not ok:
            raise ClaimError(f'"{name}": expected {want}, got {a!r}')
    if name in ("sameLabel", "sameContent") and args[0] == args[1]:
        raise ClaimError(f'"{name}" needs two different facts')
    return (name, tuple(args))


# ---- Views of a claim -------------------------------------------------------------

def parts(c: Claim) -> List[Claim]:
    """The set instances of a claim, left to right."""
    return parts(c[1]) + parts(c[2]) if c[0] == "both" else [c]


def _fact_args(part: Claim) -> List[int]:
    name, args = part
    return [a for kind, a in zip(SETS[name].params, args) if kind == "fact"]


def fact_ids(c: Claim) -> List[int]:
    """Cited fact ids, in order of first use."""
    seen: Dict[int, None] = {}
    for p in parts(c):
        for i in _fact_args(p):
            seen.setdefault(i)
    return list(seen)


def census_of(c: Claim):
    """The census part if the claim is one, else None. A census is always the whole claim."""
    return c if c[0] in CENSUS else None


def cited_facts(c: Claim, src: FactSource) -> Tuple[List[int], Dict[int, Fact]]:
    """The facts a certificate for this claim cites: the ids the claim names, or, for a
    census, every fact of its kind in the evidence. Raises if one is missing."""
    census = census_of(c)
    if census:
        rows = [f for f in src.all() if f.kind == census[1][0]]
        if len(rows) > MAX_CENSUS:
            raise ClaimError(f"the evidence holds {len(rows)} records of kind {census[1][0]}; "
                             f"a census can cover at most {MAX_CENSUS}")
        return [f.id for f in rows], {f.id: f for f in rows}
    ids = fact_ids(c)
    found = src.get(ids)
    missing = [i for i in ids if i not in found]
    if missing:
        raise ClaimError(f"fact ids not in the evidence DB: {missing}")
    return ids, found


def rules(c: Claim) -> List[str]:
    return sorted({r for name, _ in parts(c) for r in SETS[name].rules})


def strength(c: Claim, facts: Dict[int, Fact]) -> str:
    """The weakest link: a judgment tag beats a heuristic set beats strong rules."""
    worst = 0
    for name, args in parts(c):
        s = SETS[name].strength
        if name == "tagged" and _is_judgment(facts[args[2]]):
            s = "judgment"
        worst = max(worst, STRENGTHS.index(s))
    return STRENGTHS[worst]


def to_lean(c: Claim) -> str:
    if c[0] == "both":
        return f".both ({to_lean(c[1])}) ({to_lean(c[2])})"
    name, args = c
    rendered = " ".join(f".{a}" if kind in ("slot", "kind") else str(a)
                        for kind, a in zip(SETS[name].params, args))
    return f"{SETS[name].lean} {rendered}"


def to_json(c: Claim):
    if c[0] == "both":
        return {"both": [to_json(p) for p in parts(c)]}
    return {c[0]: list(c[1])}


def english(c: Claim, facts: Dict[int, Fact], src: FactSource) -> str:
    """The sentence shown to the investigator. One sentence per part, in claim order."""
    return " ".join(SETS[name].english(args, facts, src) for name, args in parts(c))
