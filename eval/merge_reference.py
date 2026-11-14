"""Join the open-book reference and the blind-transcribed parts into one answer key.

    python3 -m eval.merge_reference          # writes eval/reference_full.json

  open    eval/reference.json: 10 questions, transcribed while the record readers for
          them were being written (so those readers may be fitted to the answers)
  closed  eval/reference_parts/part_*.json: the other 47 questions, transcribed by
          agents that saw only the answer key, and committed before any reader for
          them existed

Nothing is edited on the way: every item is copied as transcribed, with `book` added.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "reference_full.json"


def merged() -> dict:
    base = json.loads((HERE / "reference.json").read_text())
    items = [dict(i, book="open") for i in base["items"]]
    notes = {}
    for path in sorted((HERE / "reference_parts").glob("part_*.json")):
        part = json.loads(path.read_text())
        items += [dict(i, book="closed") for i in part["items"]]
        notes[path.name] = part.get("notes", "")
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "duplicate item ids across parts"
    return {"source": base["source"], "tolerance_s": base["tolerance_s"],
            "what_this_is": "Every answer row of section 6, questions 1 to 57, of the NIST "
                            "answer key. `book` says how the row was transcribed.",
            "books": {"open": base["selection_rule"],
                      "closed": "All other questions. Transcribed blind; see eval/reference_parts "
                                "and eval/blind_audit.py."},
            "not_included": "Questions 58 to 60 (a summary, a timeline and a diagram).",
            "time_zone": base["time_zone"] + " The transcribers found two tables (questions 6 "
                         "and 10) that run at UTC-5; their items say so in `note`.",
            "part_notes": notes, "items": items}


def main() -> int:
    data = merged()
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    closed = [i for i in data["items"] if i["book"] == "closed"]
    print(f"{OUT.name}: {len(data['items'])} items; open {len(data['items']) - len(closed)}, "
          f"closed {len(closed)} ({sum(i['expect'] is None for i in closed)} that no record kind can state)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
