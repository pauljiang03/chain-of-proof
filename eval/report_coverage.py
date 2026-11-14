"""How many of NIST's answer rows does a written report state? One text matcher for all.

    python3 -m eval.report_coverage --report runs/investigator/report.md --label ours
    python3 -m eval.report_coverage --report data/baselines/mulder/opus-4.6-run1/ndlc.report.md --label mulder-run1

The answer scorer in eval/score.py accepts structured rows from any system. This
separate diagnostic searches prose for mentions; it does not assess correctness.
It asks two things of each supported reference row:

  named       the row's entity (file name, URL, search text, serial, program, value)
              appears in the report
  with time   and the row's time appears within 400 characters of it, to the second,
              in UTC or in the reference's declared local timezone

It is a text match, so it is blunt in both directions: it cannot tell a correct mention
from a wrong one, it credits an everyday word that happens to be a folder name ("final",
"design"), and it misses a paraphrase. "With time" is the stricter and more telling
column. It is blunt in the same way for every
report, which is the point. Rows with no entity of their own (a logon, a burn trace)
are matched on the time alone and listed separately.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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


def clock_strings(utc: str, time_zone=None):
    t = datetime.fromisoformat(utc.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    clocks = {t.astimezone(timezone.utc).strftime("%H:%M:%S")}
    if time_zone is not None:
        clocks.add(t.astimezone(ZoneInfo(time_zone)).strftime("%H:%M:%S"))
    return clocks


def score(reference: dict, report: str, time_zone=None) -> dict:
    text = norm(report)
    zone = scorer.reference_zone(reference, time_zone)
    items = []
    for item in reference["items"]:
        e = item["expect"]
        if not scorer.supported_expect(e):
            continue
        name = entity(e)
        clocks = clock_strings(e["utc"], zone) if "utc" in e else set()
        if name is None:
            named, timed = None, any(c in text for c in clocks) if clocks else None
        else:
            # as a whole word or name: "pd" must not match inside "updated"
            spots = [m.start() for m in re.finditer(
                r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])", text)]
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
    return {"items": items, "by_question": by_q, "time_zone": zone,
            "metric": "prose_mention_diagnostic",
            "note": "Mentions do not establish correct answers or evidence support. "
                    "Use eval.score --answers for structured answer matching.",
            "totals": {k: sum(q[k] for q in by_q.values())
                       for k in ("rows", "named", "timed_rows", "with_time")}}


def line(label: str, result: dict) -> str:
    t = result["totals"]
    return (f"{label:<28} names {t['named']:>4} of {t['rows']} answer rows; "
            f"with the time {t['with_time']:>4} of {t['timed_rows']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Search a report for reference-row mentions (not correctness).")
    ap.add_argument("--report", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--reference", default=str(FULL))
    ap.add_argument("--time-zone", help="IANA zone overriding reference.time_zone")
    ap.add_argument("--out", help="write the per-row result here")
    args = ap.parse_args(argv)
    reference = json.loads(Path(args.reference).read_text())
    result = score(reference, Path(args.report).read_text(), args.time_zone)
    result["label"] = args.label
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(line(args.label, result))
    for q, c in result["by_question"].items():
        label = f"Q{q} {scorer.question_name(reference, q)}".strip()
        print(f"   {label:<38}{c['named']:>4} /{c['rows']:>4}"
              f"   time {c['with_time']:>3} /{c['timed_rows']:>3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
