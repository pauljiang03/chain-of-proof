"""Mark a written report on Mulder's 20-item checklist, with one marker for every system.

    python3 -m eval.mulder grade --report PATH --label mulder-opus-run1 \\
        --published data/baselines/mulder/opus-4.6-run1/ACCURACY-REPORT.md
    python3 -m eval.mulder table

Mulder (https://github.com/calebevans/mulder) publishes a self-marked score on this case:
20 items, each FOUND / PARTIAL / MISSED / FALSE POSITIVE. To compare fairly, the same
marker has to mark both systems by the same rules without knowing whose report it reads:

  * the checklist and the marking rules are Mulder's own (eval/mulder_items.json);
  * the marker is one headless model call with no tools. It is given the checklist, the
    rules, the NIST answer key, and one report with the tool's name removed;
  * the marker is first run on Mulder's own published reports. `table` shows how far its
    marks agree with the marks Mulder published for itself. If they disagree widely, the
    marker is off and no comparison should be drawn from it.

Reports and the answer key are read from data/ (not in the repo: fetch Mulder's from the
URL in mulder_items.json; the answer key text is `pdftotext -layout` of NIST's PDF).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "eval" / "mulder_items.json"
OUT = ROOT / "runs" / "mulder-compare"
STATUSES = ("FOUND", "PARTIAL", "MISSED", "FALSE_POSITIVE")

INSTRUCTIONS = """\
You are marking a written forensic investigation report against a fixed checklist. You
have no tools and need none: the checklist, the marking rules, the official answer key
and the report are all in the document below. Do not ask for anything.

THE CASE
The NIST CFReDS Data Leakage Case: a Windows 7 PC (exhibit "PC") and three removable
media (RM#1 a company USB stick, RM#2 a personal USB stick, RM#3 a CD-R), with an
official answer key from NIST.

MARKING RULES
The checklist's authors define the marks like this (quoted):
{rubric}

Give each of the 20 items exactly one status:
  FOUND           the report states the item, the details the item names are right, and
                  the report shows the evidence for it
  PARTIAL         the report has part of the item, or related evidence only, or states it
                  with a wrong detail, or mentions it without evidence
  MISSED          the report says nothing that bears on the item
  FALSE_POSITIVE  what the report says about the item is contradicted by the answer key,
                  or is a causal attribution the evidence does not support, stated as
                  fact (not as a labelled inference)

Then list every OTHER claim in the report, outside the 20 items, that the answer key
contradicts or that is an unsupported causal attribution stated as fact. A statement the
report itself labels as an inference, a judgment or unverified is not a false positive.

Separately, list every statement the report labels as an inference, a judgment or
unverified that the answer key contradicts. Under the rules above these are not false
positives; they are recorded so that a label cannot hide an error.

Rules for you:
- Mark only what is written in the report. Give no credit for what its author could
  have found, and none for what you know about the case from elsewhere.
- The answer key prints local times (US Eastern: UTC-4 in its "Timezone is applied"
  tables for March 2015; a few of its tables run at UTC-5). Convert before comparing. A
  difference of a second or two is not a contradiction.
- Be even-handed: the same strictness for every item.
- You are not told which tool or person wrote the report, and it does not matter.

ANSWER FORMAT
One JSON object and nothing else, no code fence:
{{"items": [{{"n": 1, "status": "FOUND", "quote": "at most 300 characters copied from the report, or empty", "why": "one sentence"}}, ... all 20 in order],
 "other_false_positives": [{{"quote": "copied from the report", "why": "what the answer key says instead, with its question number"}}],
 "labelled_inferences_contradicted": [{{"quote": "copied from the report", "why": "what the answer key says instead"}}]}}

=== CHECKLIST ===
{items}

=== OFFICIAL ANSWER KEY (text of NIST's PDF) ===
{answers}

=== REPORT TO MARK ===
{report}
"""


def anonymous(text: str) -> str:
    """Remove the names that tell the marker whose report this is."""
    text = re.sub(r"(?i)mulder(-dfir)?", "the tool", text)
    return re.sub(r"(?i)chain[- ]of[- ]proof", "the tool", text)


def prompt_for(report: str, answers: str) -> str:
    spec = json.loads(ITEMS.read_text())
    return INSTRUCTIONS.format(
        rubric="\n".join(f'  "{r}"' for r in spec["rubric"]),
        items="\n".join(f"{n}. {t}" for n, t in enumerate(spec["items"], 1)),
        answers=answers, report=anonymous(report))


def ask(prompt: str, model: str, timeout_s: int) -> str:
    """One headless call: no built-in tools, no MCP servers, an empty directory. The
    document goes in on standard input."""
    cmd = ["claude", "-p", "Follow the instructions at the top of the document on standard "
           "input. Reply with the JSON object only.", "--tools", "",
           "--mcp-config", '{"mcpServers": {}}', "--strict-mcp-config",
           "--permission-prompts", "none", "--model", model, "--output-format", "json"]
    with tempfile.TemporaryDirectory() as empty:
        done = subprocess.run(cmd, cwd=empty, input=prompt, capture_output=True, text=True,
                              timeout=timeout_s)
    try:
        return json.loads(done.stdout).get("result", "")
    except json.JSONDecodeError:
        return done.stdout


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


def grade(report_path: Path, label: str, answers_path: Path, model: str, minutes: int,
          published_path=None) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    report = Path(report_path).read_text()
    answer = ask(prompt_for(report, Path(answers_path).read_text()), model, minutes * 60)
    (OUT / f"{label}.answer.txt").write_text(answer + "\n")
    data = parse(answer)
    statuses = [i["status"] for i in data["items"]]
    result = {"label": label, "marker_model": model, "report_chars": len(report),
              "totals": totals(statuses, len(data["other_false_positives"])),
              "items": data["items"], "other_false_positives": data["other_false_positives"],
              "labelled_inferences_contradicted": data["labelled_inferences_contradicted"]}
    if published_path:
        pub = published(published_path)
        same = sum(a == b for a, b in zip(statuses, pub["statuses"]))
        result["published"] = dict(pub, agreement=same)
    (OUT / f"{label}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    return result


def table() -> str:
    rows = [json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))]
    L = [f"{'report':<26}{'full':>6}{'detect':>8}{'false+':>8}   F/P/M/FP    published by its authors   same marks",
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
    ap = argparse.ArgumentParser(description="Mark a report on Mulder's 20 items.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grade")
    g.add_argument("--report", required=True)
    g.add_argument("--label", required=True)
    g.add_argument("--published", help="the authors' own ACCURACY-REPORT.md, to compare marks")
    g.add_argument("--answers", default="data/reference/leakage-answers.txt")
    g.add_argument("--model", default="opus")
    g.add_argument("--minutes", type=int, default=30)
    sub.add_parser("table")
    args = ap.parse_args(argv)
    if args.cmd == "grade":
        r = grade(Path(args.report), args.label, Path(args.answers), args.model, args.minutes,
                  args.published)
        print(json.dumps(r["totals"]), r.get("published", {}).get("agreement"))
    print(table())
    return 0


if __name__ == "__main__":
    sys.exit(main())
