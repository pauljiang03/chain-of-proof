"""The deterministic miner: every instance of the approved sets, no LLM.

    python3 -m miner.mine --facts evidence/case_facts.json --out certs

Candidate generation here is untrusted Python: a bug can miss a finding, but it cannot
certify a false one, because every candidate still goes through checker.check and the
Lean kernel. The output order and the finding ids (M001, M002, ...) depend only on the
evidence file, so two runs on the same evidence give the same findings.

This is the floor for the agents: anything they certify beyond it is their contribution.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from checker import check as checker
from checker.facts import Fact, FactSource, open_source

Q_DEVICES = "Which USB devices were connected to this PC, and what do they hold?"
Q_OPENED = "Which files were opened from removable devices or network shares?"
Q_SEARCH = "Which web searches match the watch list?"
Q_COPIED = "Which files look copied onto a volume?"
Q_TIMES = "When were the user's files created and last modified?"
Q_RECOVERED = "Which file records were recovered from a seized device's unallocated space?"
Q_DELETED = "Which files were sent to the Recycle Bin?"
Q_EMAIL = "Which e-mails does the user's mailbox hold?"
Q_BURN = "What traces of disc burning are there?"
Q_SAME = "Which files in different places have the same size and last-modified time?"
SAME = "same size and last-modified time as a file elsewhere"


def precedes(x: Fact, y: Fact) -> bool:
    return x.t + x.res + y.res < y.t


def _both(parts: List[dict]) -> dict:
    return parts[0] if len(parts) == 1 else {"both": parts}


def candidates(source: FactSource) -> List[Tuple[str, dict]]:
    facts = source.all()
    by_kind: Dict[str, List[Fact]] = defaultdict(list)
    for f in facts:
        by_kind[f.kind].append(f)
    tags: Dict[int, List[Fact]] = defaultdict(list)
    for g in by_kind["tag"]:
        tags[g.obj].append(g)
    usbs, devs, seen = by_kind["usbInsert"], by_kind["volumeOnDevice"], by_kind["volumeSeen"]
    # the PC's own volumes: anything hosting a file extracted from the PC image
    own = {f.aux for k in ("fileCreated", "fileModified") for f in by_kind[k]
           if f.prov.get("exhibit") == "PC"}

    def tagged(f: Fact, slot: str) -> List[dict]:
        return [{"tagged": [f.id, slot, g.id, g.aux]} for g in tags.get(getattr(f, slot), [])]

    def device_parts(d: Fact) -> List[dict]:
        """Tie examined device `d` to its earliest connection record on this PC."""
        mine = [u for u in usbs if u.obj == d.obj]
        if not mine:
            return []
        u = min(mine, key=lambda x: (x.t, x.id))
        return [{"deviceHolds": [u.id, d.id]}] + tagged(u, "obj")

    out: List[Tuple[str, dict]] = []

    for u in usbs:
        held = [d for d in devs if d.obj == u.obj]
        for d in held:
            out.append((Q_DEVICES, _both([{"deviceHolds": [u.id, d.id]}] + tagged(u, "obj"))))
        if not held:
            out.append((Q_DEVICES, _both([{"usbConnected": [u.id]}] + tagged(u, "obj"))))

    for l in by_kind["lnkTarget"]:
        if l.aux in own:
            continue
        on_device = [d for d in devs if d.aux == l.aux]
        recorded = sorted((s for s in seen if s.aux == l.aux), key=lambda x: (x.t, x.id))[:1]
        if on_device:
            for d in on_device:
                out.append((Q_OPENED, _both([{"openedFromDevice": [l.id, d.id]}]
                                            + tagged(l, "obj") + device_parts(d))))
        elif recorded:
            for s in recorded:
                base = [{"openedFromRecorded": [l.id, s.id]}] + tagged(l, "obj")
                bridges = [(s2, d2) for s2 in seen if s2.obj == s.obj and s2.aux != s.aux
                           for d2 in devs if d2.aux == s2.aux]
                bridges = sorted(bridges, key=lambda b: (b[0].t, b[0].id))[:1]
                if not bridges:
                    out.append((Q_OPENED, _both(base)))
                for s2, d2 in bridges:
                    out.append((Q_OPENED, _both(
                        base + [{"sameLabel": [s.id, s2.id]}, {"recordedOnDevice": [s2.id, d2.id]}]
                        + device_parts(d2))))
        else:
            out.append((Q_OPENED, _both([{"opened": [l.id]}] + tagged(l, "obj"))))

    for w in by_kind["webSearch"]:
        if tags.get(w.obj):
            out.append((Q_SEARCH, _both([{"searched": [w.id]}] + tagged(w, "obj"))))

    areas = {d.aux: d for d in by_kind["unallocatedOnDevice"]}

    def recovered_parts(c: Fact) -> List[dict]:
        """Tie a recovered directory entry to its device and that device's first connection."""
        d = areas.get(c.aux)
        if d is None:
            return []
        parts = [{"recoveredOnDevice": [c.id, d.id]}]
        mine = [u for u in usbs if u.obj == d.obj]
        if mine:
            u = min(mine, key=lambda x: (x.t, x.id))
            parts += [{"deviceExamined": [u.id, d.id]}] + tagged(u, "obj")
            if precedes(u, c):
                parts.append({"before": [u.id, c.id]})
        return parts

    modified = defaultdict(list)
    for m in by_kind["fileModified"]:
        modified[(m.obj, m.aux)].append(m)
    for c in by_kind["fileCreated"]:
        if c.aux in areas:
            copied = [{"copiedHere": [c.id, m.id]} for m in modified.get((c.obj, c.aux), [])
                      if precedes(m, c)]
            out.append((Q_RECOVERED, _both(recovered_parts(c) + copied + tagged(c, "obj"))))
            continue
        for m in modified.get((c.obj, c.aux), []):
            if precedes(m, c):
                out.append((Q_COPIED, _both([{"copiedHere": [c.id, m.id]}] + tagged(c, "obj"))))
            else:
                parts = [{"fileCreatedAt": [c.id]}, {"fileModifiedAt": [m.id]}]
                if precedes(c, m):
                    parts.append({"before": [c.id, m.id]})
                out.append((Q_TIMES, _both(parts)))
    # one finding per group of file records that share a same-size-and-time tag
    shared = defaultdict(list)
    for g in by_kind["tag"]:
        if source.string(g.aux).startswith(SAME):
            shared[g.aux].extend((m, g) for m in by_kind["fileModified"] if m.obj == g.obj)
    for tag_id in sorted(shared):
        pairs = sorted(shared[tag_id], key=lambda p: p[0].id)
        parts = []
        for m, g in pairs:
            parts += [{"fileModifiedAt": [m.id]}, {"tagged": [m.id, "obj", g.id, tag_id]}]
            if m.aux in areas:
                parts.append({"recoveredOnDevice": [next(
                    c.id for c in by_kind["fileCreated"] if (c.obj, c.aux) == (m.obj, m.aux)),
                    areas[m.aux].id]})
            parts += [{"tagged": [m.id, "obj", t.id, t.aux]} for t in tags.get(m.obj, [])
                      if t.aux != tag_id]
        if len(pairs) > 1:
            out.append((Q_SAME, _both(parts)))

    for d in by_kind["fileDeleted"]:
        out.append((Q_DELETED, _both([{"fileDeletedAt": [d.id]}] + tagged(d, "obj"))))
    for e in by_kind["emailSent"]:
        out.append((Q_EMAIL, _both([{"emailed": [e.id]}] + tagged(e, "obj"))))
    for b in by_kind["cdBurn"]:
        out.append((Q_BURN, {"burnTrace": [b.id]}))
    return out


def mine(source: FactSource, out_dir: Path, prefix: str = "M") -> List[dict]:
    results = []
    for n, (question, claim) in enumerate(candidates(source), start=1):
        results.append(checker.check(claim, f"{prefix}{n:03d}", source, question, out_dir))
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Mine every instance of the approved sets.")
    ap.add_argument("--facts", required=True)
    ap.add_argument("--out", default="certs")
    args = ap.parse_args(argv)
    results = mine(open_source(args.facts), Path(args.out))
    ok = sum(r["status"] == "verified" for r in results)
    print(f"{len(results)} candidates, {ok} verified, {len(results) - ok} rejected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
