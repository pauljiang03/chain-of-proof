"""The scorer. No LLM anywhere: same evidence, same reference, same run -> same numbers.

    python3 -m eval.score --facts evidence/case_facts.json --run ui/public/run.json

Three independent checks against a supplied reference (legacy default: NIST):

  A. Extraction.  Does the evidence file hold the row the answer key says exists
                  (kind, entity, time within the tolerance)? Lean cannot check this,
                  so this is the test of the layer everything else trusts.
  B. Gate.        Labeled claims (eval/labeled_claims.json): the kernel must certify
                  the true ones and refuse the false ones.
  C. Run.         For a run file: which answer-key rows does a certified finding state?

A row counts as certified only if a verified finding *states* it: the row's fact must be
an argument of a set whose sentence prints that fact's entity and time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from checker import check as checker
from checker import claims as claims_mod
from checker.facts import FactSource, open_source

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "eval" / "reference.json"
LABELED = ROOT / "eval" / "labeled_claims.json"
NIST_CASE_ID = "nist-cfreds-data-leakage"

# `tagged` names the entity and the tag but not the tagged record's time, so it does
# not count as stating that record.
NOT_STATING = {"tagged"}


def _us(utc: str) -> int:
    dt = datetime.fromisoformat(utc.replace("Z", "+00:00"))
    if dt.tzinfo is None:                     # the field is explicitly named UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(microseconds=1)


def is_nist_reference(reference: dict) -> bool:
    """Recognize the explicit case id or the metadata of the frozen old references."""
    return (reference.get("case_id") == NIST_CASE_ID
            or str(reference.get("source", "")).startswith("NIST CFReDS Data Leakage Case,"))


def reference_zone(reference: dict, time_zone: Optional[str] = None) -> Optional[str]:
    """Resolve an IANA zone. Only old NIST metadata receives its legacy NY fallback.

    An unfamiliar case without local-day matchers needs no local timezone; if it
    does have local-day matchers, require a declared zone instead of guessing.
    """
    zone = time_zone if time_zone is not None else reference.get("time_zone")
    if zone is not None:
        try:
            ZoneInfo(zone)
            return zone
        except (KeyError, ValueError, TypeError):
            if time_zone is not None or not is_nist_reference(reference):
                raise ValueError("time_zone must be an IANA timezone, such as America/Los_Angeles")
    if is_nist_reference(reference):
        return "America/New_York"
    if any(isinstance(i.get("expect"), dict) and "local_day" in i["expect"]
           for i in reference.get("items", [])):
        raise ValueError("reference has local_day matchers but declares no time_zone")
    return None


EXPECT_KEYS = {"kind", "obj", "obj_endswith", "obj_contains", "aux", "aux_contains",
               "utc", "local_day", "exhibit"}


def supported_expect(expect) -> bool:
    """This matcher compares positive structured records, never absence or free prose."""
    return (isinstance(expect, dict) and isinstance(expect.get("kind"), str)
            and bool(expect["kind"]) and set(expect) <= EXPECT_KEYS)


def rows_of(source: FactSource) -> List[dict]:
    return [{"id": f.id, "kind": f.kind, "t": f.t, "res": f.res, "obj_text": source.string(f.obj),
             "aux_text": source.string(f.aux), "prov": f.prov} for f in source.all()]


def same_entity(expect: dict, row: dict) -> bool:
    """Kind and entity match; time is not looked at. Text is compared without case."""
    if row["kind"] != expect["kind"]:
        return False
    obj, aux = row["obj_text"].lower(), row["aux_text"].lower()
    if "obj" in expect and obj != expect["obj"].lower():
        return False
    if "obj_endswith" in expect and not obj.endswith(expect["obj_endswith"].lower()):
        return False
    if "obj_contains" in expect and expect["obj_contains"].lower() not in obj:
        return False
    if "aux" in expect and aux != expect["aux"].lower():
        return False
    if "aux_contains" in expect and expect["aux_contains"].lower() not in aux:
        return False
    if "exhibit" in expect and row.get("prov", {}).get("exhibit") != expect["exhibit"]:
        return False
    return True


def time_match(expect: dict, row: dict, tol_s: int, time_zone: Optional[str] = None) -> Optional[str]:
    """How the row's time meets the expected one: "tolerance" (within tol_s seconds),
    "row uncertainty" (further off, but within the uncertainty the row itself states, as
    for a date stored without a time of day), "day" (the answer key gives a date only),
    "untimed" (it gives no time), or None."""
    if "utc" in expect:
        if row.get("t") is None:
            return None
        off = abs(row["t"] - _us(expect["utc"]))
        if off <= tol_s * 1_000_000:
            return "tolerance"
        return "row uncertainty" if off <= row.get("res", 0) else None
    if "local_day" in expect:
        if time_zone is None:
            raise ValueError("local_day matching requires an explicit time_zone")
        if row.get("t") is None:
            return None
        when = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=row["t"])
        return "day" if when.astimezone(ZoneInfo(time_zone)).strftime("%Y-%m-%d") == expect["local_day"] else None
    return "untimed"


def matches(expect: dict, row: dict, tol_s: int, time_zone: Optional[str] = None) -> bool:
    return (supported_expect(expect) and same_entity(expect, row)
            and time_match(expect, row, tol_s, time_zone) is not None)


# ---- A. extraction ----------------------------------------------------------------

def score_extraction(reference: dict, rows: List[dict], time_zone: Optional[str] = None) -> List[dict]:
    tol = reference["tolerance_s"]
    zone = reference_zone(reference, time_zone)
    out = []
    for item in reference["items"]:
        e = item["expect"]
        entry = {"id": item["id"], "question": item["question"],
                 "book": item.get("book", "open" if is_nist_reference(reference) else "unspecified")}
        if not supported_expect(e):               # not a supported positive-record matcher
            out.append(dict(entry, status="not_expressible", fact_ids=[]))
            continue
        same = [r for r in rows if same_entity(e, r)]
        how = {r["id"]: time_match(e, r, tol, zone) for r in same}
        hit = [i for i, h in how.items() if h]
        entry.update(status="match" if hit else ("time_differs" if same else "missing"),
                     fact_ids=hit)
        if hit:
            order = ("tolerance", "day", "untimed", "row uncertainty")
            entry["within"] = min((how[i] for i in hit), key=order.index)
        elif any(r.get("t") is not None for r in same) and "utc" in e:
            best = min((r for r in same if r.get("t") is not None),
                       key=lambda r: abs(r["t"] - _us(e["utc"])))
            entry["closest_fact"] = best["id"]
            entry["off_by_s"] = round((best["t"] - _us(e["utc"])) / 1e6, 1)
        out.append(entry)
    return out


# ---- B. gate ----------------------------------------------------------------------

def resolve(labeled: dict, rows: List[dict], tol_s: int,
            time_zone: Optional[str] = None) -> Dict[str, Optional[dict]]:
    if time_zone is None and any("local_day" in s for s in labeled["facts"].values()):
        raise ValueError("gate local_day selectors require an explicit time_zone")
    return {name: next((r for r in rows if matches(sel, r, tol_s, time_zone)), None)
            for name, sel in labeled["facts"].items()}


def _fill(node, named: Dict[str, Optional[dict]], source: FactSource, missing: List[str]):
    """Replace selector names with fact ids ('@name.aux' with that fact's aux id)."""
    if isinstance(node, dict):
        return {k: _fill(v, named, source, missing) for k, v in node.items()}
    if isinstance(node, list):
        return [_fill(v, named, source, missing) for v in node]
    if isinstance(node, str) and node not in claims_mod.SLOTS:
        name, _, field = node.lstrip("@").partition(".")
        row = named.get(name)
        if row is None:
            missing.append(name)
            return -1
        if node.startswith("@"):
            return getattr(source.get([row["id"]])[row["id"]], field)
        return row["id"]
    return node


def score_gate(labeled: dict, source: FactSource, rows: List[dict], tol_s: int,
               out_dir: Optional[Path] = None, time_zone: Optional[str] = None) -> List[dict]:
    named = resolve(labeled, rows, tol_s, time_zone)
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for c in labeled["claims"]:
            missing: List[str] = []
            claim = _fill(c["claim"], named, source, missing)
            entry = {"id": c["id"], "label": c["label"], "ask": c["ask"], "basis": c["basis"]}
            if missing:
                entry.update(verdict="unresolved", missing_facts=sorted(set(missing)))
            else:
                r = checker.check(claim, c["id"], source, c["ask"], out_dir or Path(tmp))
                entry.update(verdict=r["status"], claim=r["claim"])
                if r["status"] == "verified":
                    entry["strength"] = r["strength"]
            entry["as_expected"] = entry["verdict"] == ("verified" if c["label"] else "rejected")
            out.append(entry)
    return out


# ---- C. run -----------------------------------------------------------------------

def stated_rows(finding: dict) -> List[dict]:
    """The cited facts whose entity and time the finding's sentences print."""
    ids = set()
    for part in finding.get("parts", []):
        (name, args), = part["part"].items()
        if name in NOT_STATING:
            continue
        params = claims_mod.SETS[name].params
        ids.update(a for kind, a in zip(params, args) if kind == "fact")
    return [f for f in finding["cited_facts"] if f["id"] in ids]


def question_summary(items: List[dict], match_key: str) -> dict:
    """A question is complete only if every one of its reference items matches."""
    questions = OrderedDict()
    for item in items:
        q = questions.setdefault(item["question"], {"question": item["question"],
                                                     "items": 0, "matched": 0})
        q["items"] += 1
        q["matched"] += (item.get(match_key) == "match" if match_key == "status"
                          else bool(item.get(match_key)))
    for q in questions.values():
        q["status"] = ("complete" if q["matched"] == q["items"] else
                       "partial" if q["matched"] else "unanswered")
    counts = {s: sum(q["status"] == s for q in questions.values())
              for s in ("complete", "partial", "unanswered")}
    return {"total": len(questions), **counts,
            "accuracy": counts["complete"] / len(questions) if questions else None,
            "items": list(questions.values()),
            "definition": "Complete iff every reference item for the question matches. "
                          "This is accuracy under the declared matcher contract; unsupported "
                          "reference items prevent completion."}


def score_run(reference: dict, run: dict, time_zone: Optional[str] = None) -> dict:
    """Score a trusted checker-produced run; certificate replay is a separate check.

    Arbitrary system output belongs in score_answers, which makes no certification
    claim. A serialized run's contents alone are not a certificate verification.
    """
    tol = reference["tolerance_s"]
    zone = reference_zone(reference, time_zone)
    stated = [(f["finding_id"], f["strength"], stated_rows(f)) for f in run["findings"]]
    items, used = [], set()
    for item in reference["items"]:
        by = [(fid, strength) for fid, strength, rows in stated
              if item["expect"] is not None
              and any(matches(item["expect"], r, tol, zone) for r in rows)]
        used.update(fid for fid, _ in by)
        order = claims_mod.STRENGTHS
        best = min((s for _, s in by), key=order.index) if by else None
        items.append({"id": item["id"], "question": item["question"], "certified": bool(by),
                      "findings": [fid for fid, _ in by], "best_strength": best})
    return {
        "proposals": run["stats"]["proposals"], "verified": run["stats"]["verified"],
        "rejected": run["stats"]["rejected"], "by_strength": run["stats"]["by_strength"],
        "items": items,
        "question_summary": question_summary(items, "certified"),
        "findings_outside_reference": sorted(f["finding_id"] for f in run["findings"]
                                             if f["finding_id"] not in used),
    }


def answer_rows(answer_document):
    """Adapt structured assertions from any system, retaining incompatible entries.

    Input is a JSON list, or {"answers": [...]}. Each assertion needs kind/obj;
    aux defaults to empty, utc may be null, and exhibit may be top-level or in
    prov. No prose or negated assertion is silently converted to a positive fact.
    External uncertainty is not used to enlarge the reference's time tolerance.
    """
    answers = answer_document.get("answers") if isinstance(answer_document, dict) else answer_document
    if not isinstance(answers, list):
        raise ValueError("answers must be a JSON list or an object containing an answers list")
    rows, incompatible = [], []
    for number, answer in enumerate(answers, 1):
        reason = None
        if not isinstance(answer, dict):
            reason = "answer is not a structured object"
        elif not isinstance(answer.get("kind"), str) or not answer["kind"]:
            reason = "answer needs a non-empty kind"
        elif not isinstance(answer.get("obj"), str) or not isinstance(answer.get("aux", ""), str):
            reason = "obj and aux must be strings"
        elif (answer.get("polarity", "positive") != "positive" or answer.get("negated", False)
              or answer.get("absent", False)):
            reason = "negative or absence assertions are not supported by the positive-record matcher"
        elif (answer.get("supported") is False or answer.get("status", "asserted")
              not in ("asserted", "supported", "verified")):
            reason = "answer is explicitly unsupported, unverified, or withheld"
        elif not isinstance(answer.get("prov", {}), dict):
            reason = "prov must be an object"
        if reason:
            incompatible.append({"answer_index": number, "status": "incompatible", "reason": reason})
            continue
        provenance = dict(answer.get("prov", {}))
        if "exhibit" in answer:
            if "exhibit" in provenance and provenance["exhibit"] != answer["exhibit"]:
                incompatible.append({"answer_index": number, "status": "incompatible",
                                     "reason": "top-level exhibit conflicts with prov.exhibit"})
                continue
            provenance["exhibit"] = answer["exhibit"]
        try:
            when = _us(answer["utc"]) if answer.get("utc") is not None else None
        except (ValueError, TypeError, AttributeError):
            incompatible.append({"answer_index": number, "status": "incompatible",
                                 "reason": "utc must be an ISO datetime or null"})
            continue
        rows.append({"id": number, "kind": answer["kind"], "obj_text": answer["obj"],
                     "aux_text": answer.get("aux", ""), "t": when, "res": 0,
                     "prov": provenance})
    return answers, rows, incompatible


def score_answers(reference: dict, answer_document, time_zone: Optional[str] = None) -> dict:
    """Reference-row match rate for submitted structured answers, not precision.

    Every reference row stays in the denominator, including unsupported matchers.
    Extra assertions matching no reference are unassessed, not automatically false.
    """
    answers, rows, incompatible = answer_rows(answer_document)
    zone = reference_zone(reference, time_zone)
    tol, items, used = reference["tolerance_s"], [], set()
    for item in reference["items"]:
        expect = item["expect"]
        entry = {"id": item["id"], "question": item["question"]}
        if not supported_expect(expect):
            items.append(dict(entry, status="not_expressible", answer_indices=[]))
            continue
        same = [r for r in rows if same_entity(expect, r)]
        hits = [r for r in same if time_match(expect, r, tol, zone) is not None]
        if hits:
            status = "match"
        elif same and not any(r["t"] is not None for r in same):
            status = "untimed"
        else:
            status = "time_differs" if same else "missing"
        used.update(r["id"] for r in hits)
        entry.update(status=status, answer_indices=[r["id"] for r in hits])
        items.append(entry)
    matched = sum(i["status"] == "match" for i in items)
    total = len(items)
    return {"metric": "reference_row_match_rate", "matched": matched, "reference_rows": total,
            "match_rate": matched / total if total else None, "items": items,
            "question_summary": question_summary(items, "status"),
            "submitted_answers": len(answers), "compatible_answers": len(rows),
            "incompatible_answers": incompatible,
            "unassessed_answer_indices": [r["id"] for r in rows if r["id"] not in used],
            "note": "Deterministic positive-row matching only. Question completeness uses the "
                    "declared reference contract. This does not measure semantic precision, "
                    "evidence support, or Lean certification. "
                    "Unmatched extra assertions require separate assessment."}


# ---- report -----------------------------------------------------------------------

def _by_question(entries: List[dict], key) -> "OrderedDict[int, List[dict]]":
    groups: "OrderedDict[int, List[dict]]" = OrderedDict()
    for e in entries:
        groups.setdefault(e["question"], []).append(e)
    return groups


QUESTION_NAMES = {
    1: "image hashes", 2: "partitions", 3: "operating system", 4: "time zone",
    5: "computer name", 6: "accounts", 7: "last logon", 8: "last shutdown",
    9: "network interface", 10: "installed applications", 11: "application runs",
    12: "power and logon events", 13: "browsers used", 14: "browser history paths",
    15: "websites visited", 16: "web searches", 17: "Explorer search box",
    18: "e-mail application", 19: "e-mail file", 20: "e-mail account", 21: "e-mails",
    22: "USB devices", 23: "renamed files", 24: "network drive address",
    25: "folders browsed on RM#2", 26: "opened on RM#2", 27: "folders on network drive",
    28: "opened on network drive", 29: "cloud service traces", 30: "deleted from cloud",
    31: "cloud account", 32: "burn method", 33: "CD burns", 34: "copied to CD-R",
    35: "opened from CD-R", 36: "resignation letter times", 37: "printing",
    38: "thumbnail cache files", 39: "thumbnails", 40: "sticky note files",
    41: "sticky notes", 42: "search indexing", 43: "search database", 44: "IE in search db",
    45: "e-mail in search db", 46: "Desktop in search db", 47: "shadow copies",
    48: "cloud in shadow copy", 49: "cloud deletions", 50: "mail in shadow copy",
    51: "Recycle Bin", 52: "anti-forensics on PC", 53: "recovered from RM#2",
    54: "anti-forensics on RM#2", 55: "copied to RM#2", 56: "hidden files on CD-R",
    57: "anti-forensics on CD-R"}

BOOKS = (("open", "Open book: questions whose record-readers were written with the answer key open"),
         ("closed", "Closed book: record-readers built without the answer key, scored once"))


def question_name(reference: dict, question) -> str:
    names = reference.get("question_names", {})
    explicit = names.get(str(question), names.get(question))
    if explicit is not None:
        return str(explicit)
    if is_nist_reference(reference):
        return QUESTION_NAMES.get(question, QUESTION_NAMES.get(str(question), ""))
    return ""


def report(results: dict) -> str:
    L = []
    headline = results.get("headline")
    if headline and headline["measured"]:
        rate = headline["match_rate"]
        pct = f" ({rate:.1%})" if rate is not None else ""
        L.append(f"{headline['label']}: {headline['matched']} / {headline['reference_rows']}{pct}")
        q = headline["question_summary"]
        L.append(f"Questions with every reference item matched: "
                 f"{q['complete']} / {q['total']}; partial {q['partial']}; unanswered {q['unanswered']}")
    else:
        L.append("End-to-end answers: not measured (no run or structured answers supplied)")
    if results.get("evidence"):
        L.append(f"Evidence  {results['evidence']['path']}  sha256 {results['evidence']['sha256'][:16]}…"
                 f"  ({results['evidence']['facts']} facts)")
    L.append(f"Reference {results['reference']['items']} answer-key rows, tolerance "
             f"{results['reference']['tolerance_s']} s\n")
    ex = results["extraction"]
    run_items = {i["id"]: i for i in results["run"]["items"]} if results.get("run") else {}
    L.append("A. Extraction diagnostics against the answer key" + ("   |  C. certified by the run" if run_items else ""))
    if not results.get("evidence"):
        L.append("   not measured (no facts supplied)")
    head = (f"   {'question':<32}{'rows':>5}{'match':>7}{'time off':>10}{'missing':>9}"
            f"{'no kind':>9}")
    grand = [0] * 6
    books = list(BOOKS) + [(b, "Reference group: " + b) for b in
                          dict.fromkeys(e.get("book", "unspecified") for e in ex)
                          if b not in {name for name, _ in BOOKS}]
    for book, title in books:
        part = [e for e in ex if e.get("book", "unspecified") == book]
        if not part:
            continue
        L.append(f"   {title}")
        L.append(head + (f"   |{'certified':>10}" if run_items else ""))
        tot = [0] * 6
        for q, group in _by_question(part, "question").items():
            n = len(group)
            m = sum(e["status"] == "match" for e in group)
            t = sum(e["status"] == "time_differs" for e in group)
            x = sum(e["status"] == "missing" for e in group)
            u = sum(e["status"] == "not_expressible" for e in group)
            c = sum(run_items[e["id"]]["certified"] for e in group) if run_items else 0
            for i, v in enumerate((n, m, t, x, u, c)):
                tot[i] += v
                grand[i] += v
            label = f"Q{q} {question_name(results['reference'], q)}".strip()
            line = f"   {label:<32}{n:>5}{m:>7}{t:>10}{x:>9}{u:>9}"
            L.append(line + (f"   |{c:>10}" if run_items else ""))
        line = f"   {'subtotal':<32}{tot[0]:>5}{tot[1]:>7}{tot[2]:>10}{tot[3]:>9}{tot[4]:>9}"
        L.append(line + (f"   |{tot[5]:>10}" if run_items else ""))
    line = f"   {'total':<32}{grand[0]:>5}{grand[1]:>7}{grand[2]:>10}{grand[3]:>9}{grand[4]:>9}"
    L.append(line + (f"   |{grand[5]:>10}" if run_items else ""))
    loose = sum(e.get("within") == "row uncertainty" for e in ex)
    if loose:
        L.append(f"   {loose} of the matches are further than the tolerance but within the "
                 f"uncertainty the row itself states")
    off = [e for e in ex if e["status"] == "time_differs" and "off_by_s" in e]
    for e in off[:12]:
        L.append(f"   time off: {e['id']} closest fact {e['closest_fact']} is {e['off_by_s']:+} s")
    if len(off) > 12:
        L.append(f"   ... and {len(off) - 12} more with a different time (see results.json)")
    gate = results["gate"]
    true = [g for g in gate if g["label"]]
    false = [g for g in gate if not g["label"]]
    L.append("\nB. Gate on labeled claims")
    if results.get("gate_status", {}).get("measured", True):
        L.append(f"   true claims certified : {sum(g['verdict'] == 'verified' for g in true)} / {len(true)}")
        L.append(f"   false claims refused  : {sum(g['verdict'] == 'rejected' for g in false)} / {len(false)}")
    else:
        L.append("   not measured: " + results["gate_status"]["reason"])
    for g in gate:
        if not g["as_expected"]:
            L.append(f"   not as labeled: {g['id']} ({'true' if g['label'] else 'false'}) -> "
                     f"{g['verdict']}: {g['ask']}")
    if results.get("run"):
        r = results["run"]
        L.append(f"\nC. Run {r['path']}")
        L.append(f"   proposals {r['proposals']}, certified {r['verified']}, refused {r['rejected']}"
                 f"; by strength {r['by_strength']}")
        cert = sum(i["certified"] for i in r["items"])
        present = sum(e["status"] == "match" for e in ex)
        L.append(f"   answer-key rows certified: {cert} / {len(r['items'])}"
                 f"  ({cert} / {present} of the rows present in the evidence)")
        L.append(f"   certified findings that state no answer-key row: "
                 f"{len(r['findings_outside_reference'])} (not scored; listed in results.json)")
    if results.get("answers"):
        answers = results["answers"]
        L.append(f"\nStructured answers: {answers['submitted_answers']} submitted; "
                 f"{len(answers['incompatible_answers'])} incompatible")
        L.append("   " + answers["note"])
    return "\n".join(L)


def score(facts_path: Optional[Path] = None, run_path: Optional[Path] = None,
          reference_path: Optional[Path] = None, *, labeled_claims_path="auto",
          time_zone: Optional[str] = None, answers_path: Optional[Path] = None) -> dict:
    if run_path and answers_path:
        raise ValueError("supply a run or structured answers, not both")
    if reference_path is None:
        if answers_path is not None:
            raise ValueError("structured answers require an explicit --reference")
        if facts_path is not None and Path(facts_path).resolve() != (ROOT / "evidence" / "case_facts.json").resolve():
            raise ValueError("nondefault facts require an explicit --reference")
    ref_path = Path(reference_path or REFERENCE)
    reference = json.loads(ref_path.read_text())
    zone = reference_zone(reference, time_zone)
    source = open_source(facts_path) if facts_path else None
    rows = rows_of(source) if source is not None else []
    if labeled_claims_path == "auto":
        gate_path = LABELED if is_nist_reference(reference) else None
    else:
        gate_path = Path(labeled_claims_path) if labeled_claims_path is not None else None
    if gate_path and source is None and labeled_claims_path != "auto":
        raise ValueError("--labeled-claims requires --facts")
    measured_gate = gate_path is not None and source is not None
    gate = (score_gate(json.loads(gate_path.read_text()), source, rows,
                       reference["tolerance_s"], time_zone=zone) if measured_gate else [])
    known_misses = (sorted(KNOWN_MISSES) if measured_gate and is_nist_reference(reference)
                    and gate_path.resolve() == LABELED.resolve() else [])
    results = {
        "evidence": ({"path": str(facts_path), "facts": len(rows),
                      "sha256": hashlib.sha256(Path(facts_path).read_bytes()).hexdigest()}
                     if facts_path else None),
        "reference": {"source": reference.get("source", str(ref_path)),
                      "path": str(ref_path), "items": len(reference["items"]),
                      "sha256": hashlib.sha256(ref_path.read_bytes()).hexdigest(),
                      "tolerance_s": reference["tolerance_s"], "time_zone": zone,
                      "case_id": reference.get("case_id"),
                      "question_names": reference.get("question_names", {})},
        "extraction": score_extraction(reference, rows, zone) if facts_path else [],
        "gate": gate,
        "gate_status": {"measured": measured_gate,
                        "path": str(gate_path) if measured_gate else None,
                        "known_misses": known_misses,
                        "reason": (None if measured_gate else
                                   "no facts supplied" if source is None else
                                   "no labeled claims selected for this case")},
        "headline": {"measured": False},
    }
    if run_path:
        run = score_run(reference, json.loads(Path(run_path).read_text()), zone)
        results["run"] = dict(path=str(run_path), **run)
        matched, total = sum(i["certified"] for i in run["items"]), len(run["items"])
        results["headline"] = {"measured": True, "metric": "certified_reference_row_match_rate",
                               "label": "Certified answer-item match rate", "matched": matched,
                               "reference_rows": total, "match_rate": matched / total if total else None,
                               "question_summary": run["question_summary"]}
    if answers_path:
        answers = score_answers(reference, json.loads(Path(answers_path).read_text()), zone)
        results["answers"] = dict(path=str(answers_path), **answers)
        results["headline"] = {"measured": True, "metric": "reference_row_match_rate",
                               "label": "Structured answer-item match rate",
                               **{k: answers[k] for k in ("matched", "reference_rows", "match_rate",
                                                         "question_summary")}}
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deterministically score answers against a case reference.")
    ap.add_argument("--facts", help="extracted facts for diagnostics and the gate (legacy NIST default only)")
    submissions = ap.add_mutually_exclusive_group()
    submissions.add_argument("--run", help="a certified run.json to score")
    submissions.add_argument("--answers", help="structured external answers: JSON list or {answers: [...]} ")
    ap.add_argument("--out", default="eval/results.json")
    ap.add_argument("--reference", help="answer key (default eval/reference.json, the 10 "
                    "open-book questions; eval/reference_full.json is all 57)")
    gate = ap.add_mutually_exclusive_group()
    gate.add_argument("--labeled-claims", help="case-specific true/false gate probes")
    gate.add_argument("--no-gate", action="store_true", help="do not measure the labeled-claim gate")
    ap.add_argument("--time-zone", help="IANA zone overriding reference.time_zone for local-day matching")
    args = ap.parse_args(argv)
    try:
        if args.answers and not args.reference:
            ap.error("--answers requires an explicit --reference")
        reference = json.loads(Path(args.reference or REFERENCE).read_text())
        facts = args.facts
        if facts is None and not args.answers and is_nist_reference(reference):
            facts = "evidence/case_facts.json"
        if facts is None and not (args.run or args.answers):
            ap.error("supply --facts, --run, or --answers for this case")
        results = score(Path(facts) if facts else None, Path(args.run) if args.run else None,
                        args.reference, labeled_claims_path=(None if args.no_gate else
                                                           args.labeled_claims or "auto"),
                        time_zone=args.time_zone, answers_path=args.answers)
    except (ValueError, OSError) as error:
        ap.error(str(error))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n")
    print(report(results))
    gate_ok = all(g["as_expected"] or g["id"] in results["gate_status"]["known_misses"]
                  for g in results["gate"])
    false_ok = all(g["verdict"] == "rejected" for g in results["gate"] if not g["label"])
    return 0 if (gate_ok and false_ok) else 1


# True claims we expect the gate to refuse, each explained in labeled_claims.json.
KNOWN_MISSES = {"T15"}

if __name__ == "__main__":
    sys.exit(main())
