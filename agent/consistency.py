"""Conservative contradiction checks for explicit optical-write assertions.

This is not a semantic verifier for arbitrary prose. It recognizes affirmative
"disc <exhibit> was written/burned ..." clauses and ISO UTC timestamps. It catches
an unbound PC trace used as a device time and a window predating that disc's own
file-set record. Other wording can escape it; conclusions remain unverified.
"""
from datetime import datetime, timezone
import re

WRITE = re.compile(
    r"\b(?:disc|CD(?:-R)?)\s+(?P<exhibit>[\w#-]+)\s+"
    r"(?:was|had been)\s+(?:written|burned)\b(?P<clause>[^.!?]*)", re.I)
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\s+UTC)?")


def seconds(text):
    dt = datetime.fromisoformat(text.removesuffix(" UTC").replace("Z", "+00:00"))
    return int((dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp())


def optical_conflicts(text, findings):
    rows = {r["id"]: r for f in findings for r in f.get("cited_facts", [])}.values()
    issues = []
    for match in WRITE.finditer(text):
        exhibit, clause = match["exhibit"], match["clause"]
        try:
            times = [seconds(t.group()) for t in STAMP.finditer(clause)]
        except ValueError:
            issues.append("invalid date or time in optical-write assertion")
            continue
        own = [r for r in rows if r.get("prov", {}).get("exhibit", "").lower() == exhibit.lower()]
        pc_times = {r["t"] // 1_000_000 for r in rows if r["kind"] == "cdBurn"}
        # A PC trace has no physical-media identity in the current record contract.
        own_times = {r["t"] // 1_000_000 for r in own if r["kind"] == "fileCreated"}
        if any(t in pc_times and t not in own_times for t in times):
            issues.append(f"write time assigned to {exhibit} comes from a PC optical trace "
                          "with no physical-disc link; cite the disc's own records")
        if "between" in clause.lower() and len(times) >= 2:
            start, end = times[0], times[1]
            if start > end:
                issues.append("optical-write window ends before it starts")
            for row in own:
                stamp = row.get("prov", {}).get("file_set_recorded_utc")
                if stamp and end < seconds(stamp):
                    issues.append(f"write window for {exhibit} ends before its UDF file-set "
                                  f"recording time {stamp}")
                    break
    return issues
