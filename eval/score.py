"""The scorer. No LLM anywhere: same evidence, same reference, same run -> same numbers.

    python3 -m eval.score --facts evidence/case_facts.json --run ui/public/run.json

Three independent checks, each against the NIST answer key (eval/reference.json):

  A. Extraction.  Does the evidence file hold the row the answer key says exists
                  (kind, entity, time within the tolerance)? Lean cannot check this,
                  so this is the test of the layer everything else trusts.
  B. Gate.        Labeled claims (eval/labeled_claims.json): the kernel must certify
                  the true ones and refuse the false ones.
  C. Run.         For a run file: which answer-key rows does a certified finding state?

A row counts as certified only if a verified finding *states* it: the row's fact must be
an argument of a set whose sentence prints that fact's entity and time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from checker import check as checker
from checker import claims as claims_mod
from checker.facts import FactSource, open_source

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "eval" / "reference.json"
LABELED = ROOT / "eval" / "labeled_claims.json"

# `tagged` names the entity and the tag but not the tagged record's time, so it does
# not count as stating that record.
NOT_STATING = {"tagged"}


def _us(utc: str) -> int:
    dt = datetime.strptime(utc, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp()) * 1_000_000


def rows_of(source: FactSource) -> List[dict]:
    return [{"id": f.id, "kind": f.kind, "t": f.t, "res": f.res, "obj_text": source.string(f.obj),
             "aux_text": source.string(f.aux), "prov": f.prov} for f in source.all()]


def same_entity(expect: dict, row: dict) -> bool:
    """Kind and entity match; time is not looked at. Text is compared without case."""
    if row["kind"] != expect["kind"]:
        return False
    obj, aux = row["obj_text"].lower(), row["aux_text"].lower()
    if "obj" in expect and obj != expect["obj"].lower():
        return False
    if "obj_endswith" in expect and not obj.endswith(expect["obj_endswith"].lower()):
        return False
    if "obj_contains" in expect and expect["obj_contains"].lower() not in obj:
        return False
    if "aux" in expect and aux != expect["aux"].lower():
        return False
    if "aux_contains" in expect and expect["aux_contains"].lower() not in aux:
        return False
    if "exhibit" in expect and row.get("prov", {}).get("exhibit") != expect["exhibit"]:
        return False
    return True


LOCAL_ZONE = ZoneInfo("America/New_York")     # the zone NIST's local times and dates are in


def time_match(expect: dict, row: dict, tol_s: int) -> Optional[str]:
    """How the row's time meets the expected one: "tolerance" (within tol_s seconds),
    "row uncertainty" (further off, but within the uncertainty the row itself states, as
    for a date stored without a time of day), "day" (the answer key gives a date only),
    "untimed" (it gives no time), or None."""
    if "utc" in expect:
        off = abs(row["t"] - _us(expect["utc"]))
        if off <= tol_s * 1_000_000:
            return "tolerance"
        return "row uncertainty" if off <= row.get("res", 0) else None
    if "local_day" in expect:
        when = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=row["t"])
        return "day" if when.astimezone(LOCAL_ZONE).strftime("%Y-%m-%d") == expect["local_day"] else None
    return "untimed"


def matches(expect: dict, row: dict, tol_s: int) -> bool:
    return same_entity(expect, row) and time_match(expect, row, tol_s) is not None


# ---- A. extraction ----------------------------------------------------------------

def score_extraction(reference: dict, rows: List[dict]) -> List[dict]:
    tol = reference["tolerance_s"]
    out = []
    for item in reference["items"]:
        e = item["expect"]
        entry = {"id": item["id"], "question": item["question"], "book": item.get("book", "open")}
        if e is None:                              # no kind can state this answer row
            out.append(dict(entry, status="not_expressible", fact_ids=[]))
            continue
        same = [r for r in rows if same_entity(e, r)]
        how = {r["id"]: time_match(e, r, tol) for r in same}
        hit = [i for i, h in how.items() if h]
        entry.update(status="match" if hit else ("time_differs" if same else "missing"),
                     fact_ids=hit)
        if hit:
            order = ("tolerance", "day", "untimed", "row uncertainty")
            entry["within"] = min((how[i] for i in hit), key=order.index)
        elif same and "utc" in e:
            best = min(same, key=lambda r: abs(r["t"] - _us(e["utc"])))
            entry["closest_fact"] = best["id"]
            entry["off_by_s"] = round((best["t"] - _us(e["utc"])) / 1e6, 1)
        out.append(entry)
    return out


# ---- B. gate ----------------------------------------------------------------------

def resolve(labeled: dict, rows: List[dict], tol_s: int) -> Dict[str, Optional[dict]]:
    return {name: next((r for r in rows if matches(sel, r, tol_s)), None)
            for name, sel in labeled["facts"].items()}


def _fill(node, named: Dict[str, Optional[dict]], source: FactSource, missing: List[str]):
    """Replace selector names with fact ids ('@name.aux' with that fact's aux id)."""
    if isinstance(node, dict):
        return {k: _fill(v, named, source, missing) for k, v in node.items()}
    if isinstance(node, list):
        return [_fill(v, named, source, missing) for v in node]
    if isinstance(node, str) and node not in claims_mod.SLOTS:
        name, _, field = node.lstrip("@").partition(".")
        row = named.get(name)
        if row is None:
            missing.append(name)
            return -1
        if node.startswith("@"):
            return getattr(source.get([row["id"]])[row["id"]], field)
        return row["id"]
    return node


def score_gate(labeled: dict, source: FactSource, rows: List[dict], tol_s: int,
               out_dir: Optional[Path] = None) -> List[dict]:
    named = resolve(labeled, rows, tol_s)
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for c in labeled["claims"]:
            missing: List[str] = []
            claim = _fill(c["claim"], named, source, missing)
            entry = {"id": c["id"], "label": c["label"], "ask": c["ask"], "basis": c["basis"]}
            if missing:
                entry.update(verdict="unresolved", missing_facts=sorted(set(missing)))
            else:
                r = checker.check(claim, c["id"], source, c["ask"], out_dir or Path(tmp))
                entry.update(verdict=r["status"], claim=r["claim"])
                if r["status"] == "verified":
                    entry["strength"] = r["strength"]
            entry["as_expected"] = entry["verdict"] == ("verified" if c["label"] else "rejected")
            out.append(entry)
    return out


# ---- C. run -----------------------------------------------------------------------

def stated_rows(finding: dict) -> List[dict]:
    """The cited facts whose entity and time the finding's sentences print."""
    ids = set()
    for part in finding.get("parts", []):
        (name, args), = part["part"].items()
        if name in NOT_STATING:
            continue
        params = claims_mod.SETS[name].params
        ids.update(a for kind, a in zip(params, args) if kind == "fact")
    return [f for f in finding["cited_facts"] if f["id"] in ids]


def score_run(reference: dict, run: dict) -> dict:
    tol = reference["tolerance_s"]
    stated = [(f["finding_id"], f["strength"], stated_rows(f)) for f in run["findings"]]
    items, used = [], set()
    for item in reference["items"]:
        by = [(fid, strength) for fid, strength, rows in stated
              if item["expect"] is not None
              and any(matches(item["expect"], r, tol) for r in rows)]
        used.update(fid for fid, _ in by)
        order = claims_mod.STRENGTHS
        best = min((s for _, s in by), key=order.index) if by else None
        items.append({"id": item["id"], "question": item["question"], "certified": bool(by),
                      "findings": [fid for fid, _ in by], "best_strength": best})
    return {
        "proposals": run["stats"]["proposals"], "verified": run["stats"]["verified"],
        "rejected": run["stats"]["rejected"], "by_strength": run["stats"]["by_strength"],
        "items": items,
        "findings_outside_reference": sorted(f["finding_id"] for f in run["findings"]
                                             if f["finding_id"] not in used),
    }


# ---- report -----------------------------------------------------------------------

def _by_question(entries: List[dict], key) -> "OrderedDict[int, List[dict]]":
    groups: "OrderedDict[int, List[dict]]" = OrderedDict()
    for e in entries:
        groups.setdefault(e["question"], []).append(e)
    return groups


QUESTION_NAMES = {
    1: "image hashes", 2: "partitions", 3: "operating system", 4: "time zone",
    5: "computer name", 6: "accounts", 7: "last logon", 8: "last shutdown",
    9: "network interface", 10: "installed applications", 11: "application runs",
    12: "power and logon events", 13: "browsers used", 14: "browser history paths",
    15: "websites visited", 16: "web searches", 17: "Explorer search box",
    18: "e-mail application", 19: "e-mail file", 20: "e-mail account", 21: "e-mails",
    22: "USB devices", 23: "renamed files", 24: "network drive address",
    25: "folders browsed on RM#2", 26: "opened on RM#2", 27: "folders on network drive",
    28: "opened on network drive", 29: "cloud service traces", 30: "deleted from cloud",
    31: "cloud account", 32: "burn method", 33: "CD burns", 34: "copied to CD-R",
    35: "opened from CD-R", 36: "resignation letter times", 37: "printing",
    38: "thumbnail cache files", 39: "thumbnails", 40: "sticky note files",
    41: "sticky notes", 42: "search indexing", 43: "search database", 44: "IE in search db",
    45: "e-mail in search db", 46: "Desktop in search db", 47: "shadow copies",
    48: "cloud in shadow copy", 49: "cloud deletions", 50: "mail in shadow copy",
    51: "Recycle Bin", 52: "anti-forensics on PC", 53: "recovered from RM#2",
    54: "anti-forensics on RM#2", 55: "copied to RM#2", 56: "hidden files on CD-R",
    57: "anti-forensics on CD-R"}

BOOKS = (("open", "Open book: questions whose record-readers were written with the answer key open"),
         ("closed", "Closed book: record-readers built without the answer key, scored once"))


def report(results: dict) -> str:
    L = []
    L.append(f"Evidence  {results['evidence']['path']}  sha256 {results['evidence']['sha256'][:16]}…"
             f"  ({results['evidence']['facts']} facts)")
    L.append(f"Reference {results['reference']['items']} answer-key rows, tolerance "
             f"{results['reference']['tolerance_s']} s\n")
    ex = results["extraction"]
    run_items = {i["id"]: i for i in results["run"]["items"]} if results.get("run") else {}
    L.append("A. Extraction against the answer key" + ("   |  C. certified by the run" if run_items else ""))
    head = (f"   {'question':<32}{'rows':>5}{'match':>7}{'time off':>10}{'missing':>9}"
            f"{'no kind':>9}")
    grand = [0] * 6
    for book, title in BOOKS:
        part = [e for e in ex if e.get("book", "open") == book]
        if not part:
            continue
        L.append(f"   {title}")
        L.append(head + (f"   |{'certified':>10}" if run_items else ""))
        tot = [0] * 6
        for q, group in _by_question(part, "question").items():
            n = len(group)
            m = sum(e["status"] == "match" for e in group)
            t = sum(e["status"] == "time_differs" for e in group)
            x = sum(e["status"] == "missing" for e in group)
            u = sum(e["status"] == "not_expressible" for e in group)
            c = sum(run_items[e["id"]]["certified"] for e in group) if run_items else 0
            for i, v in enumerate((n, m, t, x, u, c)):
                tot[i] += v
                grand[i] += v
            line = f"   Q{q:<3}{QUESTION_NAMES.get(q, ''):<28}{n:>5}{m:>7}{t:>10}{x:>9}{u:>9}"
            L.append(line + (f"   |{c:>10}" if run_items else ""))
        line = f"   {'subtotal':<32}{tot[0]:>5}{tot[1]:>7}{tot[2]:>10}{tot[3]:>9}{tot[4]:>9}"
        L.append(line + (f"   |{tot[5]:>10}" if run_items else ""))
    line = f"   {'total':<32}{grand[0]:>5}{grand[1]:>7}{grand[2]:>10}{grand[3]:>9}{grand[4]:>9}"
    L.append(line + (f"   |{grand[5]:>10}" if run_items else ""))
    loose = sum(e.get("within") == "row uncertainty" for e in ex)
    if loose:
        L.append(f"   {loose} of the matches are further than the tolerance but within the "
                 f"uncertainty the row itself states")
    off = [e for e in ex if e["status"] == "time_differs" and "off_by_s" in e]
    for e in off[:12]:
        L.append(f"   time off: {e['id']} closest fact {e['closest_fact']} is {e['off_by_s']:+} s")
    if len(off) > 12:
        L.append(f"   ... and {len(off) - 12} more with a different time (see results.json)")
    gate = results["gate"]
    true = [g for g in gate if g["label"]]
    false = [g for g in gate if not g["label"]]
    L.append("\nB. Gate on labeled claims")
    L.append(f"   true claims certified : {sum(g['verdict'] == 'verified' for g in true)} / {len(true)}")
    L.append(f"   false claims refused  : {sum(g['verdict'] == 'rejected' for g in false)} / {len(false)}")
    for g in gate:
        if not g["as_expected"]:
            L.append(f"   not as labeled: {g['id']} ({'true' if g['label'] else 'false'}) -> "
                     f"{g['verdict']}: {g['ask']}")
    if results.get("run"):
        r = results["run"]
        L.append(f"\nC. Run {r['path']}")
        L.append(f"   proposals {r['proposals']}, certified {r['verified']}, refused {r['rejected']}"
                 f"; by strength {r['by_strength']}")
        cert = sum(i["certified"] for i in r["items"])
        present = sum(e["status"] == "match" for e in ex)
        L.append(f"   answer-key rows certified: {cert} / {len(r['items'])}"
                 f"  ({cert} / {present} of the rows present in the evidence)")
        L.append(f"   certified findings that state no answer-key row: "
                 f"{len(r['findings_outside_reference'])} (not scored; listed in results.json)")
    return "\n".join(L)


def score(facts_path: Path, run_path: Optional[Path], reference_path: Optional[Path] = None) -> dict:
    reference = json.loads(Path(reference_path or REFERENCE).read_text())
    labeled = json.loads(LABELED.read_text())
    source = open_source(facts_path)
    rows = rows_of(source)
    results = {
        "evidence": {"path": str(facts_path), "facts": len(rows),
                     "sha256": hashlib.sha256(Path(facts_path).read_bytes()).hexdigest()},
        "reference": {"source": reference["source"], "items": len(reference["items"]),
                      "tolerance_s": reference["tolerance_s"]},
        "extraction": score_extraction(reference, rows),
        "gate": score_gate(labeled, source, rows, reference["tolerance_s"]),
    }
    if run_path:
        results["run"] = dict(path=str(run_path), **score_run(reference, json.loads(run_path.read_text())))
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Score evidence, gate and a run against the NIST key.")
    ap.add_argument("--facts", default="evidence/case_facts.json")
    ap.add_argument("--run", help="a run.json to score (optional)")
    ap.add_argument("--out", default="eval/results.json")
    ap.add_argument("--reference", help="answer key (default eval/reference.json, the 10 "
                    "open-book questions; eval/reference_full.json is all 57)")
    args = ap.parse_args(argv)
    results = score(Path(args.facts), Path(args.run) if args.run else None, args.reference)
    Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n")
    print(report(results))
    gate_ok = all(g["as_expected"] or g["id"] in KNOWN_MISSES for g in results["gate"])
    false_ok = all(g["verdict"] == "rejected" for g in results["gate"] if not g["label"])
    return 0 if (gate_ok and false_ok) else 1


# True claims we expect the gate to refuse, each explained in labeled_claims.json.
KNOWN_MISSES = {"T15"}

if __name__ == "__main__":
    sys.exit(main())
