"""Read historical LLM-grader outputs; these are NOT benchmark performance results.

LLM judging has been retired. This module cannot launch new grading calls. The
old results remain inspectable for the investigation trail only.
    python -m eval.mulder table

Use eval/RESULTS.md for frozen deterministic scores and eval/EVALUATION.md for
what is, and is not, comparable across systems.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "eval" / "mulder_items.json"
OUT = ROOT / "runs" / "mulder-compare"
STATUSES = ("FOUND", "PARTIAL", "MISSED", "FALSE_POSITIVE")

def parse(answer: str) -> dict:
    """The marker's JSON, validated: 20 items in order, each with a known status."""
    start, end = answer.find("{"), answer.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("the marker's answer holds no JSON object")
    data = json.loads(answer[start:end + 1])
    items = data.get("items", [])
    if [i.get("n") for i in items] != list(range(1, 21)):
        raise ValueError("the marker did not return items 1 to 20 in order")
    for i in items:
        i["status"] = str(i.get("status", "")).upper().replace(" ", "_")
        if i["status"] not in STATUSES:
            raise ValueError(f"item {i['n']}: unknown status {i['status']!r}")
    for key in ("other_false_positives", "labelled_inferences_contradicted"):
        data[key] = list(data.get(key, []))
    return data


def totals(statuses, other_fp: int) -> dict:
    n = len(statuses)
    found, partial = statuses.count("FOUND"), statuses.count("PARTIAL")
    fp = statuses.count("FALSE_POSITIVE") + other_fp
    return {"found": found, "partial": partial, "missed": statuses.count("MISSED"),
            "false_positive_items": statuses.count("FALSE_POSITIVE"),
            "false_positives_other": other_fp,
            "full_match_pct": round(100 * found / n), "detection_pct": round(100 * (found + partial) / n),
            "false_positive_pct": round(100 * fp / n)}


def published(path: Path) -> dict:
    """The marks a tool's authors published for themselves: the item table and the
    headline line of an ACCURACY-REPORT.md."""
    text = Path(path).read_text()
    marks = {}
    for m in re.finditer(r"^\|\s*(\d+)\s*\|[^|]*\|\s*(FOUND|PARTIAL|MISSED|FALSE POSITIVE)\s*\|",
                         text, re.M):
        marks.setdefault(int(m.group(1)), m.group(2).replace(" ", "_"))
    head = re.search(r"(\d+)% full match, (\d+)% detection rate.*?(\d+)% false positive rate", text)
    return {"statuses": [marks.get(n) for n in range(1, 21)],
            "headline": [int(g) for g in head.groups()] if head else None}


def table() -> str:
    rows = [json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))]
    L = ["HISTORICAL LLM JUDGMENTS — NOT PERFORMANCE SCORES", f"{'report':<26}{'full':>6}{'detect':>8}{'false+':>8}   F/P/M/FP    published by its authors   same marks",
         "-" * 100]
    for r in rows:
        t = r["totals"]
        line = (f"{r['label']:<26}{t['full_match_pct']:>5}%{t['detection_pct']:>7}%"
                f"{t['false_positive_pct']:>7}%   {t['found']}/{t['partial']}/{t['missed']}/"
                f"{t['false_positive_items']}+{t['false_positives_other']}"
                f" (+{len(r.get('labelled_inferences_contradicted', []))} labelled)")
        pub = r.get("published")
        if pub and pub.get("headline"):
            h = pub["headline"]
            line += f"{'':<4}{h[0]}% / {h[1]}% / {h[2]}%{'':<12}{pub['agreement']} of 20"
        L.append(line)
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("table",))
    ap.parse_args(argv)
    print(table())
    return 0


if __name__ == "__main__":
    sys.exit(main())
