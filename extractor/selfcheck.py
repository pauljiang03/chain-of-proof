"""Sanity checks on an evidence file. The proof checker trusts these rows; this does not.

    python3 -I extractor/selfcheck.py evidence/case_facts.json

The kernel proves that a finding follows from the rows it cites. It cannot know whether
a row is right. These checks catch the mistakes a reader can make that need no outside
knowledge to see: a time before the PC era or after the examination, a row with no
source, a hash that is not a hash, the same row twice. They do not prove the rows
correct. That is what the answer-key score (eval/score.py) and independently built
readers are for.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checker.facts import KINDS          # noqa: E402

EARLIEST = 315532800 * 1_000_000         # 1980-01-01, the first date a FAT stamp can hold
SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
NEEDS = ("image", "exhibit", "artifact", "tool")


def problems(data: dict):
    strings = data["strings"]
    text = (lambda i: strings[str(i)]) if isinstance(strings, dict) else (lambda i: strings[i])
    facts = data["facts"]
    examined = max((f["t"] for f in facts if f["kind"] in ("volumeOnDevice", "unallocatedOnDevice")),
                   default=None)
    seen, out = set(), Counter()
    examples = {}

    def flag(check: str, f: dict):
        out[check] += 1
        examples.setdefault(check, f["id"])

    for n, f in enumerate(facts):
        if f["kind"] not in KINDS:
            flag("unknown kind", f)
        if not isinstance(f["t"], int) or f["t"] < 0 or not isinstance(f["res"], int) or f["res"] < 1:
            flag("time or uncertainty is not a positive whole number", f)
        elif f["t"] < EARLIEST:
            flag("time before 1980", f)
        elif examined is not None and f["t"] > examined:
            flag("time after the examination", f)
        for slot in ("obj", "aux"):
            try:
                text(f[slot])
            except (KeyError, IndexError, TypeError):
                flag("entity id with no string", f)
        missing = [k for k in NEEDS if not f.get("prov", {}).get(k)]
        if missing and f["kind"] != "tag":
            flag("no source given (" + ", ".join(missing) + ")", f)
        if f["kind"] == "fileContent" and not SHA256.fullmatch(text(f["aux"])):
            flag("content record without a sha256", f)
        if f["kind"] not in ("cdBurn", "sessionEvent") and not text(f["obj"]).strip():
            flag("empty entity", f)
        key = (f["kind"], f["t"], f["res"], f["obj"], f["aux"], json.dumps(f.get("prov"), sort_keys=True))
        if key in seen:
            flag("the same row twice", f)
        seen.add(key)
        if n and KINDS.index(f["kind"]) < KINDS.index(facts[n - 1]["kind"]):
            flag("rows out of order (ids would not be reproducible)", f)
    ids = [f["id"] for f in facts]
    if len(set(ids)) != len(ids):
        out["duplicate ids"] += len(ids) - len(set(ids))
    return out, examples


def main(argv) -> int:
    path = Path(argv[0] if argv else ROOT / "evidence" / "case_facts.json")
    data = json.loads(path.read_text())
    found, examples = problems(data)
    print(f"{path}: {len(data['facts'])} rows, {sum(found.values())} flagged")
    for check, n in found.most_common():
        print(f"   {n:>6}  {check}   (first: row {examples.get(check, '-')})")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
