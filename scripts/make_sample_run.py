"""Build ui/public/run.sample.json from the synthetic fixture.

    python3 scripts/make_sample_run.py

Gives the front end something real in shape to build against: verified findings of
each strength, and rejections with the failing brick named. The facts are synthetic.
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checker.check import check          # noqa: E402
from checker.export import bundle        # noqa: E402
from checker.facts import JsonFacts      # noqa: E402
import json                              # noqa: E402

USB = {"usbMountedAs": [4512, 4513]}
OPENED = {"openedFromMount": [4600, 4513]}
PROPOSALS = [
    ("F1", "Which USB devices were connected, and as which volumes?", USB),
    ("F2", "Which USB devices were connected, and as which volumes?", {"usbMountedAs": [4510, 4511]}),
    ("F3", "Was a confidential file opened from a removable device?",
     {"both": [USB, OPENED, {"before": [4512, 4600]}]}),
    ("X1", "Was a confidential file opened from a removable device?",
     {"both": [{"usbMountedAs": [4510, 4511]}, {"openedFromMount": [4600, 4511]}]}),
    ("N1", "Was a confidential file opened from an unauthorized USB device?",
     {"both": [USB, OPENED, {"tagged": [4600, "obj", 9001, 50]},
               {"tagged": [4512, "obj", 9002, 51]}, {"before": [3100, 4512]}]}),
    ("F4", "Were files copied onto the unauthorized device?", {"copiedHere": [4701, 4700]}),
    ("X2", "Were files copied onto the unauthorized device?", {"copiedHere": [4703, 4702]}),
    ("F5", "Was anything deleted afterwards?", {"deletedAfter": [4800, 4701]}),
    ("X3", "Did the search come after the device was connected?", {"before": [4512, 3100]}),
    ("J1", "Was the web search related to the leak?",
     {"both": [{"tagged": [3100, "obj", 9003, 52]}, {"before": [3100, 4512]}]}),
    ("X4", "Was the authorized device tagged unauthorized?", {"tagged": [4510, "obj", 9002, 51]}),
]

src = JsonFacts(ROOT / "fixtures" / "sample_facts.json")
tmp = Path(tempfile.mkdtemp())
try:
    for fid, question, claim in PROPOSALS:
        r = check(claim, fid, src, question, out_dir=tmp)
        print(f"{r['status']:9} {fid}")
    data = bundle(tmp, "Sample run (synthetic facts)")
finally:
    shutil.rmtree(tmp)
out = ROOT / "ui" / "public" / "run.sample.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {out.relative_to(ROOT)}: {data['stats']}")
