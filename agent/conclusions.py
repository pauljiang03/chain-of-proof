"""Conclusions: the investigator's own judgment, kept apart from certified findings.

A certified finding is a sentence the proof checker generated from records. A conclusion
is a sentence the investigator wrote ("the files were copied to take them out of the
company"). The checker cannot prove a conclusion, so it is never shown as a finding. It
is accepted into the report only if:

  1. it cites at least one finding, and every finding it cites was certified in this run;
  2. every specific detail in it (a date, a time, a number, a serial, a file name, a
     quoted name) appears in the sentences of the findings it cites.

Rule 2 is a text check, not a proof. It stops a conclusion from carrying a fact that no
certificate stands behind; the inference itself remains the investigator's, and the
report says so.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

MAX_CHARS = 700
NOTE = ("Judgment, not checked by the proof checker. Every finding it cites is certified, "
        "and every date, time, number and name in it appears in those findings. The "
        "inference is the investigator's.")
MONTHS = {m: i for i, m in enumerate(
    ("january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"), 1)}
_MONTH = "|".join(list(MONTHS) + [m[:3] for m in MONTHS])
_DAY_MONTH = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH})[a-z]*\.?(?:,?\s+(\d{{4}}))?", re.I)
_MONTH_DAY = re.compile(rf"\b({_MONTH})[a-z]*\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?", re.I)
_QUOTED = re.compile(r"[\"\u201c`]([^\"\u201d`]{2,})[\"\u201d`]")
_TOKEN = re.compile(r"[^\s,;()\[\]{}<>\"\u201c\u201d`]+")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def details(text: str) -> List[str]:
    """The specific details in a conclusion that a certificate must stand behind."""
    out = []
    for m in _QUOTED.finditer(text):
        out.append(m.group(1).strip())
    spoken = set()
    for rx, day, month in ((_DAY_MONTH, 1, 2), (_MONTH_DAY, 2, 1)):
        for m in rx.finditer(text):
            mm = MONTHS.get(m.group(month).lower()) or MONTHS[next(
                k for k in MONTHS if k.startswith(m.group(month).lower()[:3]))]
            year = m.group(3)
            out.append(f"{year}-{mm:02d}-{int(m.group(day)):02d}" if year
                       else f"-{mm:02d}-{int(m.group(day)):02d}")
            spoken.update(g for g in (m.group(day), year) if g)
    for m in _TOKEN.finditer(text):
        tok = m.group(0).strip(".:!?\u2019'")
        if not any(ch.isdigit() for ch in tok) and not re.search(r"\w\.\w{2,4}$", tok):
            continue                    # a plain word: not a detail
        if tok in spoken:
            continue                    # the day or year of a date written with a month name
        if re.fullmatch(r"\d{1,2}", tok) or re.fullmatch(r"[A-Za-z]+#?\d", tok):
            continue                    # a small count; an exhibit or question label (RM#2, Q5)
        out.append(tok)
    seen, uniq = set(), []
    for d in out:
        if d.lower() not in seen:
            seen.add(d.lower())
            uniq.append(d)
    return uniq


def ungrounded(text: str, sentences: List[str]) -> List[str]:
    """Details in `text` that appear in none of the cited sentences."""
    hay = _norm(" ".join(sentences))
    return [d for d in details(text) if _norm(d) not in hay]


class Conclusions:
    def __init__(self, run_dir):
        self.path = Path(run_dir) / "conclusions.jsonl"

    def all(self) -> List[dict]:
        if not self.path.is_file():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def add(self, text: str, finding_ids, proposals: List[dict], author: str) -> dict:
        text = " ".join(str(text or "").split())
        ids = [str(i) for i in (finding_ids or [])]
        if not text:
            return {"status": "rejected", "reason": "empty conclusion"}
        if len(text) > MAX_CHARS:
            return {"status": "rejected", "reason": f"keep a conclusion under {MAX_CHARS} characters"}
        if not ids:
            return {"status": "rejected", "reason": "a conclusion must cite the certified "
                    "findings it rests on (finding_ids)"}
        by_id = {p["finding_id"]: p for p in proposals}
        bad = [i for i in ids if by_id.get(i, {}).get("status") != "verified"]
        if bad:
            return {"status": "rejected", "reason": f"not certified findings of this run: {bad}"}
        loose = ungrounded(text, [by_id[i]["english"] for i in ids])
        if loose:
            return {"status": "rejected", "not_in_cited_findings": loose,
                    "reason": "these details appear in none of the findings you cite. Cite the "
                              "finding that certifies each one, write it exactly as the finding "
                              "does (times are UTC), or drop it"}
        earlier = self.all()
        for c in earlier:
            if c["text"] == text:
                return {"status": "accepted", "conclusion_id": c["conclusion_id"], "note": "already recorded"}
        strengths = {by_id[i].get("strength") for i in ids}
        row = {"conclusion_id": f"C{len(earlier) + 1:03d}", "text": text, "finding_ids": ids,
               "strength": "judgment", "rests_on_heuristic": "heuristic" in strengths,
               "note": NOTE, "author": author}
        with self.path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return {"status": "accepted", "conclusion_id": row["conclusion_id"], "strength": "judgment"}
