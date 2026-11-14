"""How many of NIST's answer rows does a written report state? One text matcher for all.

    python3 -m eval.report_coverage --report runs/investigator/report.md --label ours
    python3 -m eval.report_coverage --report data/baselines/mulder/opus-4.6-run1/ndlc.report.md --label mulder-run1

The scorer in eval/score.py needs structured rows, which only our pipeline has. To put
another tool's prose report on the same footing, this reads any report as plain text
and asks two things of every answer-key row:

  named       the row's entity (file name, URL, search text, serial, program, value)
              appears in the report
  with time   and the row's time appears within 400 characters of it, to the second,
              in UTC or in either of the key's local offsets (UTC-4, UTC-5)

It is a text match, so it is blunt in both directions: it cannot tell a correct mention
from a wrong one, and it misses a paraphrase. It is blunt in the same way for every
report, which is the point. Rows with no entity of their own (a logon, a burn trace)
are matched on the time alone and listed separately.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

from eval import score as scorer

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "eval" / "reference_full.json"
NEAR = 400
VALUE_KINDS = ("systemSetting",)          # the thing to find is the value, not the setting's name
NO_ENTITY = ("sessionEvent", "cdBurn")    # the row is an event at a time, nothing to name


def norm(text: str) -> str:
    text = text.lower().replace("\\\\", "\\").replace("+", " ").replace("%20", " ")
    return re.sub(r"\s+", " ", text)


def entity(expect: dict):
    """The text a report must contain to have named this row, or None."""
    kind = expect["kind"]
    if kind in NO_ENTITY:
        return None
    if kind in VALUE_KINDS:
        raw = expect.get("aux") or expect.get("aux_contains")
    else:
        raw = expect.get("obj") or expect.get("obj_endswith") or expect.get("obj_contains")
    if not raw:
        return None
    raw = raw.rstrip("\\/")
    if "\\" in raw and not raw.startswith("\\\\"):
        raw = raw.rsplit("\\", 1)[-1]                 # a path: its last part
    raw = re.sub(r"^https?://", "", raw)
    return norm(raw).strip() or None


def clock_strings(utc: str):
    t = datetime.fromisoformat(utc)
    return {(t - timedelta(hours=h)).strftime("%H:%M:%S") for h in (0, 4, 5)}


def score(reference: dict, report: str) -> dict:
    text = norm(report)
    items = []
    for item in reference["items"]:
        e = item["expect"]
        if e is None:
            continue
        name = entity(e)
        clocks = clock_strings(e["utc"]) if "utc" in e else set()
        if name is None:
            named, timed = None, any(c in text for c in clocks) if clocks else None
        else:
            spots = [m.start() for m in re.finditer(re.escape(name), text)]
            named = bool(spots)
            timed = None
            if clocks:
                timed = any(c in text[max(0, s - NEAR):s + len(name) + NEAR]
                            for s in spots for c in clocks)
        items.append({"id": item["id"], "question": item["question"],
                      "book": item.get("book", "open"), "named": named, "with_time": timed})
    by_q = OrderedDict()
    for i in items:
        q = by_q.setdefault(i["question"], {"rows": 0, "named": 0, "timed_rows": 0, "with_time": 0})
        q["rows"] += 1
        q["named"] += bool(i["named"]) if i["named"] is not None else bool(i["with_time"])
        q["timed_rows"] += i["with_time"] is not None
        q["with_time"] += bool(i["with_time"])
    return {"items": items, "by_question": by_q,
            "totals": {k: sum(q[k] for q in by_q.values())
                       for k in ("rows", "named", "timed_rows", "with_time")}}


def line(label: str, result: dict) -> str:
    t = result["totals"]
    return (f"{label:<28} names {t['named']:>4} of {t['rows']} answer rows; "
            f"with the time {t['with_time']:>4} of {t['timed_rows']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Text-match a report against the NIST answer rows.")
    ap.add_argument("--report", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--reference", default=str(FULL))
    ap.add_argument("--out", help="write the per-row result here")
    args = ap.parse_args(argv)
    result = score(json.loads(Path(args.reference).read_text()), Path(args.report).read_text())
    result["label"] = args.label
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(line(args.label, result))
    for q, c in result["by_question"].items():
        print(f"   Q{int(q):<3}{scorer.QUESTION_NAMES.get(int(q), ''):<34}{c['named']:>4} /{c['rows']:>4}"
              f"   time {c['with_time']:>3} /{c['timed_rows']:>3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
