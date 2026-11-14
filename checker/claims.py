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
    {"both":            [claim, claim, ...]}

Numbers are fact ids (and one tag id). Nothing here accepts free text, so the Lean
term and the English sentence are functions of the claim tree and the cited facts
alone. Each set mirrors a definition in lean/ChainOfProof/Sets.lean: add both together.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Tuple

from .facts import Fact, FactSource

MAX_PARTS = 64
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


_EVENT = {
    "usbInsert": "the connection of USB device {obj}",
    "volumeMount": "the mounting of USB device {obj} as volume {aux}",
    "lnkTarget": "the opening of {obj} on volume {aux}",
    "fileCreated": "the creation of {obj} on volume {aux}",
    "fileModified": "the last modification of {obj} on volume {aux}",
    "fileDeleted": "the deletion of {obj} from volume {aux}",
    "webSearch": 'the web search "{obj}"',
    "emailSent": "the sending of email {obj} to {aux}",
    "cdBurn": "the CD burn {obj}",
    "tag": 'the tagging of {obj} as "{aux}"',
    "volumeSeen": 'this PC recording volume {aux} under the label "{obj}"',
    "volumeOnDevice": "the examination of device {obj}, which holds volume {aux}",
}


def _event(f: Fact, src: FactSource) -> str:
    text = _EVENT[f.kind].format(obj=src.string(f.obj), aux=src.string(f.aux))
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
    return (f"{src.string(c.obj)} was likely copied onto volume {src.string(c.aux)}: it was "
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


def _en_created(args, facts, src):
    c = facts[args[0]]
    return f"{src.string(c.obj)} was created on volume {src.string(c.aux)} ({_utc(c.t)})."


def _en_modified(args, facts, src):
    m = facts[args[0]]
    return f"{src.string(m.obj)} was last modified on volume {src.string(m.aux)} ({_utc(m.t)})."


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
}


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
        if (a not in SLOTS) if kind == "slot" else (not _is_id(a)):
            want = 'one of "obj", "aux"' if kind == "slot" else "a non-negative integer id"
            raise ClaimError(f'"{name}": expected {want}, got {a!r}')
    if name == "sameLabel" and args[0] == args[1]:
        raise ClaimError('"sameLabel" needs two different facts')
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
    rendered = " ".join(f".{a}" if kind == "slot" else str(a)
                        for kind, a in zip(SETS[name].params, args))
    return f"{SETS[name].lean} {rendered}"


def to_json(c: Claim):
    if c[0] == "both":
        return {"both": [to_json(p) for p in parts(c)]}
    return {c[0]: list(c[1])}


def english(c: Claim, facts: Dict[int, Fact], src: FactSource) -> str:
    """The sentence shown to the investigator. One sentence per part, in claim order."""
    return " ".join(SETS[name].english(args, facts, src) for name, args in parts(c))
