"""Independent Lean gate regression probes; no answer-coverage metrics or answer key.

    python -m eval.gate --facts evidence/case_facts.json \
        --labeled-claims fixtures/nist_false_claims.json --case-id nist-cfreds-data-leakage \
        --out /path/new-gate.json

Fixtures select records from evidence and propose labeled claims. They never enter
an investigator prompt or the certified investigation report. No fixture is implicit.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo
from checker import check as checker, claims as claims_mod
from checker.facts import FactSource, KINDS, open_source

def _us(utc: str) -> int:
    dt = datetime.fromisoformat(utc.replace("Z", "+00:00"))
    if dt.tzinfo is None:                     # the field is explicitly named UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(microseconds=1)



EXPECT_KEYS = {"kind", "obj", "obj_endswith", "obj_contains", "aux", "aux_contains",
               "utc", "local_day", "exhibit"}


def supported_expect(expect) -> bool:
    """This matcher compares positive structured records, never absence or free prose."""
    return (isinstance(expect, dict) and isinstance(expect.get("kind"), str)
            and bool(expect["kind"]) and set(expect) <= EXPECT_KEYS)


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


def time_match(expect: dict, row: dict, tol_s: int, time_zone: Optional[str] = None) -> Optional[str]:
    """How the row's time meets the expected one: "tolerance" (within tol_s seconds),
    "row uncertainty" (further off, but within the uncertainty the row itself states, as
    for a date stored without a time of day), "day" (the answer key gives a date only),
    "untimed" (it gives no time), or None."""
    if "utc" in expect:
        if row.get("t") is None:
            return None
        off = abs(row["t"] - _us(expect["utc"]))
        if off <= tol_s * 1_000_000:
            return "tolerance"
        return "row uncertainty" if off <= row.get("res", 0) else None
    if "local_day" in expect:
        if time_zone is None:
            raise ValueError("local_day matching requires an explicit time_zone")
        if row.get("t") is None:
            return None
        when = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=row["t"])
        return "day" if when.astimezone(ZoneInfo(time_zone)).strftime("%Y-%m-%d") == expect["local_day"] else None
    return "untimed"


def matches(expect: dict, row: dict, tol_s: int, time_zone: Optional[str] = None) -> bool:
    return (supported_expect(expect) and same_entity(expect, row)
            and time_match(expect, row, tol_s, time_zone) is not None)



def resolve(labeled: dict, rows: List[dict], tol_s: int,
            time_zone: Optional[str] = None) -> Dict[str, Optional[dict]]:
    if time_zone is None and any("local_day" in s for s in labeled["facts"].values()):
        raise ValueError("gate local_day selectors require an explicit time_zone")
    return {name: next((r for r in rows if matches(sel, r, tol_s, time_zone)), None)
            for name, sel in labeled["facts"].items()}


def _fill(node, named: Dict[str, Optional[dict]], source: FactSource, missing: List[str]):
    """Replace selector names with fact ids ('@name.aux' with that fact's aux id)."""
    if isinstance(node, dict):
        return {k: _fill(v, named, source, missing) for k, v in node.items()}
    if isinstance(node, list):
        return [_fill(v, named, source, missing) for v in node]
    if isinstance(node, str) and node not in claims_mod.SLOTS and node not in KINDS:
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
               out_dir: Optional[Path] = None, time_zone: Optional[str] = None) -> List[dict]:
    named = resolve(labeled, rows, tol_s, time_zone)
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



def load_fixture(path, case_id=None, time_zone=None):
    labeled = json.loads(Path(path).read_text())
    if not isinstance(labeled, dict) or not isinstance(labeled.get("facts"), dict) or not isinstance(labeled.get("claims"), list):
        raise ValueError("gate fixture needs facts selectors and a claims list")
    if labeled.get("case_id") and labeled["case_id"] != case_id:
        raise ValueError("gate fixture case_id does not match this case")
    zone = labeled.get("time_zone") or time_zone
    if zone is not None:
        ZoneInfo(zone)
    tolerance = labeled.get("tolerance_s", 2)
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or tolerance < 0:
        raise ValueError("gate tolerance_s must be non-negative")
    if zone is None and any("local_day" in s for s in labeled["facts"].values()):
        raise ValueError("gate local_day selectors require an explicit time_zone")
    return labeled, zone, tolerance


def measure(path, source, case_id=None, time_zone=None, out_dir=None, false_only=True):
    if path is None:
        return {"measured": False, "reason": "No explicit gate fixture supplied"}
    labeled, zone, tolerance = load_fixture(path, case_id, time_zone)
    labeled = copy.deepcopy(labeled)
    labeled["claims"] = [c for c in labeled["claims"] if not false_only or c["label"] is False]
    for n, claim in enumerate(labeled["claims"], 1):
        claim["source_id"] = claim["id"]
        claim["id"] = f"P{n:04d}"
        claim.setdefault("ask", "Gate regression probe")
        claim.setdefault("basis", "Explicitly labeled gate fixture")
    results = score_gate(labeled, source, rows_of(source), tolerance, out_dir, zone)
    for result, claim in zip(results, labeled["claims"]):
        result["source_id"] = claim["source_id"]
    return {"measured": True, "fixture": str(path),
            "fixture_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "case_id": case_id, "time_zone": zone, "false_only": false_only,
            "probes": results, "all_as_expected": all(r["as_expected"] for r in results),
            "false_claims": sum(not r["label"] for r in results),
            "false_claims_rejected": sum(not r["label"] and r["verdict"] == "rejected" for r in results),
            "note": "Gate regression only; not forensic answer accuracy or a false-positive rate."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts", required=True)
    parser.add_argument("--labeled-claims", required=True)
    parser.add_argument("--case-id")
    parser.add_argument("--time-zone")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    output = Path(args.out)
    if output.exists() or output.is_symlink():
        parser.error("refusing to overwrite existing gate output")
    try:
        result = measure(args.labeled_claims, open_source(args.facts), args.case_id, args.time_zone)
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(f"Gate: {result['false_claims_rejected']}/{result['false_claims']} false probes refused")
    return 0 if result["all_as_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
