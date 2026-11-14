"""The claim surface the agents write, and its two renderings: Lean and English.

Agents propose instances of approved sets, snapped together with "both":

    {"usbMountedAs":    [usb, mount]}            R1+R2
    {"openedFromMount": [lnk, mount]}            R3
    {"copiedHere":      [created, modified]}     R4 (heuristic)
    {"deletedAfter":    [deletion, event]}       R5
    {"tagged":          [fact, "obj"|"aux", tag_fact, tag_id]}
    {"before":          [a, b]}
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
