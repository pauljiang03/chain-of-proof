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
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

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
    return [{"id": f.id, "kind": f.kind, "t": f.t, "obj_text": source.string(f.obj),
             "aux_text": source.string(f.aux), "prov": f.prov} for f in source.all()]


def same_entity(expect: dict, row: dict) -> bool:
    """Kind and entity match; time is not looked at."""
    if row["kind"] != expect["kind"]:
        return False
    obj = row["obj_text"].lower()
    if "obj" in expect and obj != expect["obj"].lower():
        return False
    if "obj_endswith" in expect and not obj.endswith(expect["obj_endswith"].lower()):
        return False
    if "aux" in expect and row["aux_text"].lower() != expect["aux"].lower():
        return False
    if "exhibit" in expect and row.get("prov", {}).get("exhibit") != expect["exhibit"]:
        return False
    return True


def matches(expect: dict, row: dict, tol_s: int) -> bool:
    if not same_entity(expect, row):
        return False
    return "utc" not in expect or abs(row["t"] - _us(expect["utc"])) <= tol_s * 1_000_000


# ---- A. extraction ----------------------------------------------------------------

def score_extraction(reference: dict, rows: List[dict]) -> List[dict]:
    tol = reference["tolerance_s"]
    out = []
    for item in reference["items"]:
        e = item["expect"]
        hit = [r["id"] for r in rows if matches(e, r, tol)]
        near = [r for r in rows if same_entity(e, r)] if not hit else []
        status = "match" if hit else ("time_differs" if near else "missing")
        entry = {"id": item["id"], "question": item["question"], "status": status, "fact_ids": hit}
        if status == "time_differs":
            best = min(near, key=lambda r: abs(r["t"] - _us(e["utc"])))
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
              if any(matches(item["expect"], r, tol) for r in rows)]
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


QUESTION_NAMES = {16: "web searches", 21: "e-mails", 22: "USB devices", 26: "opened on RM#2",
                  28: "opened on network drive", 33: "CD burns", 35: "opened from CD-R",
                  36: "resignation letter times", 51: "Recycle Bin", 55: "copied to RM#2"}


def report(results: dict) -> str:
    L = []
    L.append(f"Evidence  {results['evidence']['path']}  sha256 {results['evidence']['sha256'][:16]}…"
             f"  ({results['evidence']['facts']} facts)")
    L.append(f"Reference {results['reference']['items']} answer-key rows, tolerance "
             f"{results['reference']['tolerance_s']} s\n")
    ex = results["extraction"]
    run_items = {i["id"]: i for i in results["run"]["items"]} if results.get("run") else {}
    L.append("A. Extraction against the answer key" + ("   |  C. certified by the run" if run_items else ""))
    head = f"   {'question':<32}{'rows':>5}{'match':>7}{'time off':>10}{'missing':>9}"
    L.append(head + (f"   |{'certified':>10}" if run_items else ""))
    tot = [0, 0, 0, 0, 0]
    for q, group in _by_question(ex, "question").items():
        n = len(group)
        m = sum(e["status"] == "match" for e in group)
        t = sum(e["status"] == "time_differs" for e in group)
        x = sum(e["status"] == "missing" for e in group)
        c = sum(run_items[e["id"]]["certified"] for e in group) if run_items else 0
        for i, v in enumerate((n, m, t, x, c)):
            tot[i] += v
        line = f"   Q{q:<3}{QUESTION_NAMES.get(q, ''):<28}{n:>5}{m:>7}{t:>10}{x:>9}"
        L.append(line + (f"   |{c:>10}" if run_items else ""))
    line = f"   {'total':<32}{tot[0]:>5}{tot[1]:>7}{tot[2]:>10}{tot[3]:>9}"
    L.append(line + (f"   |{tot[4]:>10}" if run_items else ""))
    for e in ex:
        if e["status"] == "time_differs":
            L.append(f"   time off: {e['id']} closest fact {e['closest_fact']} is {e['off_by_s']:+} s")
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


def score(facts_path: Path, run_path: Optional[Path]) -> dict:
    reference = json.loads(REFERENCE.read_text())
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
    args = ap.parse_args(argv)
    results = score(Path(args.facts), Path(args.run) if args.run else None)
    Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n")
    print(report(results))
    gate_ok = all(g["as_expected"] or g["id"] in KNOWN_MISSES for g in results["gate"])
    false_ok = all(g["verdict"] == "rejected" for g in results["gate"] if not g["label"])
    return 0 if (gate_ok and false_ok) else 1


# True claims we expect the gate to refuse, each explained in labeled_claims.json.
KNOWN_MISSES = {"T15"}

if __name__ == "__main__":
    sys.exit(main())
