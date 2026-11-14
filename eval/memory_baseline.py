"""Memory-only baseline: what does the model know about this case with no evidence?

    python3 -m eval.memory_baseline --name memory

The case is public, so a model may have read its answer key in training. This asks the
model, with no tools, no records and an empty working directory, to list every fact it
remembers, as rows in the reference vocabulary. The rows are scored with the same
matcher as everything else:

  entity   the model named the right thing (a search term, a file, a serial number)
  full     and gave the time to within the tolerance

A high entity score with a low full score means the model knows the story, not the
record. The numbers bound how much of any AI system's score on this case could come
from memory instead of from the evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path

from eval import score as scorer

ROOT = Path(__file__).resolve().parent.parent

PROMPT = """\
This is a memory test. You have no tools, no files and no records. Do not ask for any.

The subject is a public forensic training dataset: the NIST CFReDS "Data Leakage Case"
(a Windows 7 PC, two USB sticks and a CD-R, with a published answer key). Write down
every specific fact about its contents that you remember: values an examiner would
find on the images. If you remember nothing specific about some area, leave it out.
Do not invent plausible values: a wrong row is worse than a missing one. If you do
give a value you are unsure of, set "sure" to false.

Answer with one JSON object per line and nothing else. Each line:

  {"kind": K, "obj": text, "aux": text or "", "utc": "YYYY-MM-DDTHH:MM:SS" or null, "sure": true/false}

Kinds, and what `obj` / `aux` hold:
  usbInsert         USB device serial number / ""                (utc = first connection)
  volumeSeen        volume label / volume serial
  lnkTarget         path of a file that was opened, without drive letter / ""
  fileCreated       file path without drive letter / ""
  fileModified      file path without drive letter / ""
  fileDeleted       original path of a file sent to the Recycle Bin / ""
  webSearch         search keywords / ""
  emailSent         e-mail subject / ""
  cdBurn            "" / ""                                       (utc = when a disc was burned)
  systemSetting     one of: computer name, operating system, operating system installed,
                    registered owner, time zone, last shutdown, network address / the value
  accountSeen       account name or e-mail address / what it is an account of
  sessionEvent      logon, logoff, startup or shutdown / account name
  programInstalled  program name / version
  programRun        executable file name / full path
  webVisit          URL / browser
  fileDownloaded    saved path / source URL
  localSearch       text typed into the Windows Explorer search box / ""
  folderOpened      folder path / ""
  cloudFile         file name / "<service>: <event>"
  fileRenamed       old name / new name
  fileSeen          file path / artifact that records it
  shadowCopy        shadow copy id / volume
  noteText          text of a sticky note / application

Times are UTC. Give a time only if you remember it; otherwise null.
"""


def ask(model: str, out_dir: Path, timeout_s: int) -> str:
    """One headless call: no built-in tools, no MCP servers, an empty directory."""
    cmd = ["claude", "-p", PROMPT, "--tools", "", "--mcp-config", '{"mcpServers": {}}',
           "--strict-mcp-config", "--permission-prompts", "none", "--model", model,
           "--output-format", "json"]
    with tempfile.TemporaryDirectory() as empty:
        done = subprocess.run(cmd, cwd=empty, capture_output=True, text=True, timeout=timeout_s)
    try:
        answer = json.loads(done.stdout).get("result", "")
    except json.JSONDecodeError:
        answer = done.stdout
    (out_dir / "answer.txt").write_text(answer + "\n")
    return answer


def parse(answer: str):
    rows = []
    for line in answer.splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("{"):
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(r, dict) or not isinstance(r.get("kind"), str):
            continue
        utc = r.get("utc")
        t = None
        if isinstance(utc, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", utc):
            try:
                t = scorer._us(utc)
            except ValueError:
                t = None
        rows.append({"id": len(rows) + 1, "kind": r["kind"], "t": t, "res": 0,
                     "obj_text": str(r.get("obj") or ""), "aux_text": str(r.get("aux") or ""),
                     "prov": {}, "sure": bool(r.get("sure", True))})
    return rows


def score(reference: dict, rows, time_zone=None) -> dict:
    """Per reference item: did a remembered row name the entity, and the time as well?"""
    tol = reference["tolerance_s"]
    zone = scorer.reference_zone(reference, time_zone)
    items = []
    for item in reference["items"]:
        e = item["expect"]
        if not scorer.supported_expect(e):
            continue
        # the model was not asked for volume serials or exhibits on file rows
        loose = {k: v for k, v in e.items() if k not in ("aux", "aux_contains", "exhibit")}
        if not any(k in loose for k in ("obj", "obj_endswith", "obj_contains")):
            continue                               # the answer row names no entity to remember
        same = [r for r in rows if scorer.same_entity(loose, r)]
        timed = "utc" in e or "local_day" in e
        full = [r for r in same if r["t"] is not None and timed
                and scorer.time_match(e, r, tol, zone) in ("tolerance", "day")]
        items.append({"id": item["id"], "question": item["question"],
                      "book": item.get("book", "open"), "entity": bool(same),
                      "timed": timed, "full": bool(full) if timed else None})
    by_q = OrderedDict()
    for i in items:
        q = by_q.setdefault(i["question"], {"rows": 0, "entity": 0, "timed": 0, "full": 0})
        q["rows"] += 1
        q["entity"] += i["entity"]
        q["timed"] += i["timed"]
        q["full"] += bool(i["full"])
    matched = set()
    for item in reference["items"]:
        e = item["expect"]
        if not scorer.supported_expect(e):
            continue
        loose = {k: v for k, v in e.items() if k not in ("aux", "aux_contains", "exhibit")}
        matched.update(r["id"] for r in rows if scorer.same_entity(loose, r))
    return {"rows_remembered": len(rows), "rows_matching_no_answer": len(rows) - len(matched),
            "items": items, "by_question": by_q, "time_zone": zone,
            "question_names": {str(q): scorer.question_name(reference, q) for q in by_q},
            "totals": {k: sum(q[k] for q in by_q.values()) for k in ("rows", "entity", "timed", "full")}}


def report(result: dict) -> str:
    L = [f"Memory-only baseline: {result['rows_remembered']} rows written from memory, "
         f"{result['rows_matching_no_answer']} of them match no answer-key row",
         f"   {'question':<32}{'rows':>5}{'entity':>8}{'with time':>11}"]
    for q, c in result["by_question"].items():
        name = result.get("question_names", {}).get(str(q), "")
        label = f"Q{q} {name}".strip()
        L.append(f"   {label:<32}{c['rows']:>5}{c['entity']:>8}"
                 f"{c['full']:>6} /{c['timed']:>3}")
    t = result["totals"]
    L.append(f"   {'total':<32}{t['rows']:>5}{t['entity']:>8}{t['full']:>6} /{t['timed']:>3}")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Score what the model remembers with no evidence.")
    ap.add_argument("--name", default="memory")
    ap.add_argument("--model", default="opus")
    ap.add_argument("--minutes", type=int, default=15)
    ap.add_argument("--answer", help="score this saved answer instead of asking again")
    args = ap.parse_args(argv)
    out_dir = ROOT / "runs" / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    answer = Path(args.answer).read_text() if args.answer else ask(args.model, out_dir, args.minutes * 60)
    rows = parse(answer)
    reference = json.loads(scorer.REFERENCE.read_text())
    result = score(reference, rows)
    result["model"] = args.model
    (out_dir / "memory.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
