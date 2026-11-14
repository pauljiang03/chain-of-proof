"""Extract a system's typed answer block without interpreting or grading prose."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from agent.case import read_question_profile


def extract(report, public):
    candidates = []
    for block in re.findall(r"(?ms)^```json\s*\n(.*?)^```\s*$", report):
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "answers" in value:
            candidates.append(value)
    if len(candidates) != 1:
        raise ValueError("report must contain exactly one JSON submission block; no prose conversion is performed")
    answer = candidates[0]
    if answer.get("schema_version") != 2 or answer.get("case_id") != public["case_id"]:
        raise ValueError("submission version or case_id does not match the public contract")
    if not isinstance(answer["answers"], list):
        raise ValueError("submission answers must be a list")
    expected = {str(q["id"]) for q in public["questions"]}
    seen = set()
    for item in answer["answers"]:
        if not isinstance(item, dict):
            raise ValueError("each response must be an object")
        qid = str(item.get("question_id", ""))
        if qid not in expected or qid in seen:
            raise ValueError("unknown or duplicate question_id")
        seen.add(qid)
        if item.get("status") not in ("answered", "unknown", "unanswered"):
            raise ValueError("invalid response status")
        if item["status"] == "answered" and "answer" not in item:
            raise ValueError("answered response is missing its answer")
    if seen != expected:
        raise ValueError("include every question, with unknown status where necessary")
    # Reject non-finite numbers; preserve every submitted answer value unchanged.
    json.dumps(answer, allow_nan=False)
    return answer


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    answer = extract(Path(args.report).read_text(), read_question_profile(Path(args.questions)))
    answer["submission_origin"] = {"method": "verbatim JSON block extraction; no LLM judge",
                                    "report_sha256": hashlib.sha256(Path(args.report).read_bytes()).hexdigest()}
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        stream.write(json.dumps(answer, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
