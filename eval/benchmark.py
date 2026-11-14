"""Implementation-neutral, deterministic scoring of typed question answers.

    python -m eval.benchmark --reference eval/benchmark_nist.json \
        --answers /path/answers.json --out /path/results.json

Neither facts nor Lean kinds occur in this contract. A reference question declares
its expected JSON answer and optional matching rules. All required fields and list
members must match, without extras, for FOUND. This is a new explicit rubric, not a
reproduction of Mulder's historical prose judgments or false-positive rate.

Unknown/unanswered is a response status; false and null are ordinary answer values.
Unevaluable questions remain in the question denominator and are reported separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import ntpath
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


VERSION = "2.0"
STRING_MODES = {"exact", "casefold", "casefold_whitespace", "prefix"}
RUBRIC = {"fully_correct": "FOUND", "partial": "PARTIAL", "unanswered": "MISSED",
          "incorrect": "INCORRECT", "unevaluable": "UNEVALUABLE"}


def _hash(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                         allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _json(value):
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, list):
        for element in value:
            _json(element)
        return
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for element in value.values():
            _json(element)
        return
    raise ValueError("answers and expected values must contain finite JSON values only")


def _pointer(parent, key):
    return parent + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _rule(rules, path, default=None):
    """Rules address expected-answer paths; '*' matches one array/object level."""
    matches = []
    for pattern, value in rules.items():
        parts, target = pattern.split("/"), path.split("/")
        if len(parts) == len(target) and all(a == b or a == "*" for a, b in zip(parts, target)):
            matches.append((sum(p != "*" for p in parts), pattern, value))
    if not matches:
        return default
    matches.sort(key=lambda m: (-m[0], m[1]))
    best = matches[0]
    if any(m[0] == best[0] and m[2] != best[2] for m in matches[1:]):
        raise ValueError(f"ambiguous matching rules at {path or '/'}")
    return best[2]


def _atoms(value, path=""):
    # An explicitly empty object/list is itself an assertion, not zero obligations.
    if isinstance(value, dict) and value:
        return [(p, v) for k, child in value.items() for p, v in _atoms(child, _pointer(path, k))]
    if isinstance(value, list) and value:
        return [(p, v) for i, child in enumerate(value) for p, v in _atoms(child, _pointer(path, i))]
    return [(path, value)]


def _event(status, expected_path=None, answer_path=None, expected=None, actual=None, reason=None):
    event = {"status": status}
    if expected_path is not None:
        event.update(expected_path=expected_path, expected=expected)
    if answer_path is not None:
        event.update(answer_path=answer_path, actual=actual)
    if reason:
        event["reason"] = reason
    return event


def _missing(value, path, reason=None):
    return [_event("missing", expected_path=p, expected=v, reason=reason) for p, v in _atoms(value, path)]


def _wrong(value, path, reason=None):
    return [_event("wrong", answer_path=p, actual=v, reason=reason) for p, v in _atoms(value, path)]


def _counts(events):
    c = Counter(e["status"] for e in events)
    return {"true_positive": c["match"], "missing": c["missing"], "wrong": c["wrong"]}


def _instant(value, zone):
    if not isinstance(value, str) or not ("T" in value or " " in value):
        raise ValueError("an instant requires an ISO datetime, not a date alone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        if zone is None:
            raise ValueError("a timestamp without an offset requires a declared time_zone")
        tz = ZoneInfo(zone)
        first, second = parsed.replace(tzinfo=tz, fold=0), parsed.replace(tzinfo=tz, fold=1)
        if first.utcoffset() != second.utcoffset():
            raise ValueError("ambiguous or nonexistent local timestamp requires an explicit offset")
        if first.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != parsed:
            raise ValueError("nonexistent local timestamp")
        parsed = first
    return parsed.astimezone(timezone.utc)


def _day(value, zone):
    if isinstance(value, str) and len(value) == 10:
        return date.fromisoformat(value)
    if zone is None:
        raise ValueError("local_day matching requires a declared time_zone")
    return _instant(value, zone).astimezone(ZoneInfo(zone)).date()


def _windows_path(value, rule):
    """Canonicalize spelling while retaining an explicit drive/share identity.

    A declared root permits image-relative paths to match that one volume. It
    never strips or replaces a different drive or UNC share in an answer.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("path must be a nonempty string")
    value = value.replace("/", "\\")
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    if any(c in value for c in "*?"):
        raise ValueError("a concrete path cannot contain wildcards")
    drive, tail = ntpath.splitdrive(value)
    if drive and not tail.startswith("\\"):
        raise ValueError("drive-relative paths have an unknown current directory")
    root = rule.get("root")
    if not drive and root:
        value = root.rstrip("\\") + "\\" + tail.lstrip("\\")
    value = ntpath.normpath(value)
    return value if rule.get("case_sensitive", False) else value.casefold()


def _normalize_string(value, mode):
    if mode == "casefold":
        return value.casefold()
    if mode == "casefold_whitespace":
        return " ".join(value.casefold().split())
    return value


def _assignment(weights):
    """Maximum-weight rectangular assignment, with rows <= columns (Hungarian)."""
    n = len(weights)
    if not n:
        return []
    m = len(weights[0])
    if n > m or any(len(row) != m for row in weights):
        raise ValueError("assignment needs a rectangular matrix with rows <= columns")
    u, v, p, way = [0] * (n + 1), [0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minimum, used = [math.inf] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], math.inf, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cost = -weights[i0 - 1][j - 1] - u[i0] - v[j]
                    if cost < minimum[j]:
                        minimum[j], way[j] = cost, j0
                    if minimum[j] < delta:
                        delta, j1 = minimum[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    return sorted((p[j] - 1, j - 1) for j in range(1, m + 1) if p[j])


class Matcher:
    def __init__(self, config=None, time_zone=None):
        self.config = config or {}
        self.zone = time_zone
        if self.zone is not None:
            ZoneInfo(self.zone)
        unknown = set(self.config) - {"strings", "string_modes", "string_aliases", "paths", "list_order", "timestamps"}
        if unknown:
            raise ValueError(f"unknown matching settings: {sorted(unknown)}")
        if self.config.get("strings", "exact") not in STRING_MODES:
            raise ValueError("unknown string matching mode")
        if self.config.get("list_order", "unordered") not in ("ordered", "unordered"):
            raise ValueError("list_order must be ordered or unordered")
        for pointer, mode in self.config.get("string_modes", {}).items():
            if (pointer and not pointer.startswith("/")) or mode not in STRING_MODES:
                raise ValueError("string_modes needs JSON pointers and recognized modes")
        for pointer, groups in self.config.get("string_aliases", {}).items():
            if (pointer and not pointer.startswith("/")) or not isinstance(groups, list):
                raise ValueError("string_aliases needs JSON pointers and lists of equivalence classes")
            if any(not isinstance(g, list) or len(g) < 2 or
                   any(not isinstance(s, str) or not s for s in g) for g in groups):
                raise ValueError("string alias classes need at least two nonempty strings")
        for pointer, rule in self.config.get("paths", {}).items():
            if (pointer and not pointer.startswith("/")) or not isinstance(rule, dict):
                raise ValueError("paths needs JSON pointers and rule objects")
            if set(rule) - {"style", "root", "case_sensitive", "scope"} or rule.get("style") != "windows":
                raise ValueError("path rules require style windows and recognized settings")
            if not isinstance(rule.get("case_sensitive", False), bool):
                raise ValueError("path case_sensitive must be boolean")
            root = rule.get("root")
            if root is not None and (not isinstance(root, str) or not (
                    re.fullmatch(r"[A-Za-z]:", root) or re.fullmatch(r"\\\\[^\\*?]+\\[^\\*?]+", root))):
                raise ValueError("path root must identify one drive or UNC share")
        for pointer, rule in self.config.get("timestamps", {}).items():
            if (pointer and not pointer.startswith("/")) or not isinstance(rule, dict):
                raise ValueError("timestamps needs JSON pointers and rule objects")
            if set(rule) - {"tolerance_seconds", "granularity", "time_zone"}:
                raise ValueError("unknown timestamp matching setting")
            tolerance = rule.get("tolerance_seconds", 0)
            if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or tolerance < 0:
                raise ValueError("timestamp tolerance must be a finite nonnegative number")
            if rule.get("granularity", "instant") not in ("instant", "local_day"):
                raise ValueError("timestamp granularity must be instant or local_day")
            if rule.get("time_zone") is not None:
                ZoneInfo(rule["time_zone"])

    def validate_expected(self, expected):
        _json(expected)
        for path, value in _atoms(expected):
            path_rule = _rule(self.config.get("paths", {}), path)
            if path_rule is not None and value is not None:
                _windows_path(value, path_rule)
            rule = _rule(self.config.get("timestamps", {}), path)
            if rule is not None and value is not None:
                zone = rule.get("time_zone", self.zone)
                (_day if rule.get("granularity") == "local_day" else _instant)(value, zone)
            mode = _rule(self.config.get("string_modes", {}), path, self.config.get("strings", "exact"))
            if mode == "prefix" and isinstance(value, str) and not value:
                raise ValueError("an empty prefix would accept every string")

    def compare(self, expected, actual, ep="", ap=""):
        path_rule = _rule(self.config.get("paths", {}), ep)
        if path_rule is not None and expected is not None:
            wanted = _windows_path(expected, path_rule)
            try:
                equal = wanted == _windows_path(actual, path_rule)
            except (ValueError, TypeError):
                equal = False
            if equal:
                return [_event("match", ep, ap, expected, actual, "declared volume-aware path contract")]
            return _missing(expected, ep, "path or volume mismatch") + _wrong(actual, ap, "path or volume mismatch")
        rule = _rule(self.config.get("timestamps", {}), ep)
        if rule is not None and expected is not None:
            zone = rule.get("time_zone", self.zone)
            parser = _day if rule.get("granularity") == "local_day" else _instant
            wanted = parser(expected, zone)
            try:
                got = parser(actual, zone)
                equal = (wanted == got if parser is _day else
                         abs((wanted - got).total_seconds()) <= rule.get("tolerance_seconds", 0))
            except (TypeError, ValueError, OverflowError):
                equal = False
            if equal:
                return [_event("match", ep, ap, expected, actual, "declared timestamp contract")]
            return _missing(expected, ep, "timestamp mismatch") + _wrong(actual, ap, "timestamp mismatch")
        if isinstance(expected, dict) and isinstance(actual, dict) and expected:
            events = []
            for key, value in expected.items():
                events.extend(self.compare(value, actual[key], _pointer(ep, key), _pointer(ap, key))
                              if key in actual else _missing(value, _pointer(ep, key), "required field missing"))
            for key in sorted(actual.keys() - expected.keys()):
                events.extend(_wrong(actual[key], _pointer(ap, key), "unexpected field"))
            return events
        if isinstance(expected, list) and isinstance(actual, list) and expected and actual:
            if self.config.get("list_order", "unordered") == "ordered":
                events = []
                for i in range(max(len(expected), len(actual))):
                    if i >= len(expected):
                        events.extend(_wrong(actual[i], _pointer(ap, i), "extra list member"))
                    elif i >= len(actual):
                        events.extend(_missing(expected[i], _pointer(ep, i), "list member missing"))
                    else:
                        events.extend(self.compare(expected[i], actual[i], _pointer(ep, i), _pointer(ap, i)))
                return events
            # Rectangular matching avoids padding a short reference list to the
            # size of a large submitted list. Only chosen pairs retain audits.
            transpose = len(expected) > len(actual)
            n, m = min(len(expected), len(actual)), max(len(expected), len(actual))
            weights = []
            scale = len(_atoms(expected)) + len(_atoms(actual)) + 1
            expected_sizes = [len(_atoms(value)) for value in expected]
            actual_sizes = [len(_atoms(value)) for value in actual]
            for i in range(n):
                row = []
                for j in range(m):
                    ei, ai = (j, i) if transpose else (i, j)
                    events = self.compare(expected[ei], actual[ai], _pointer(ep, ei), _pointer(ap, ai))
                    counts = _counts(events)
                    # Missing-all and wrong-all are the constant unmatched
                    # baseline. Reward the improvement from joining this pair.
                    row.append(counts["true_positive"] * scale + expected_sizes[ei] + actual_sizes[ai]
                               - counts["missing"] - counts["wrong"])
                weights.append(row)
            pairs = [(j, i) if transpose else (i, j) for i, j in _assignment(weights)]
            used_expected, used_actual = {i for i, _ in pairs}, {j for _, j in pairs}
            events = [event for i, j in sorted(pairs)
                      for event in self.compare(expected[i], actual[j], _pointer(ep, i), _pointer(ap, j))]
            events.extend(event for i, value in enumerate(expected) if i not in used_expected
                          for event in _missing(value, _pointer(ep, i), "list member missing"))
            events.extend(event for j, value in enumerate(actual) if j not in used_actual
                          for event in _wrong(value, _pointer(ap, j), "extra list member"))
            return events
        # bool is intentionally different from 0/1 despite Python's equality rules.
        numeric = (isinstance(expected, (int, float)) and not isinstance(expected, bool)
                   and isinstance(actual, (int, float)) and not isinstance(actual, bool))
        equal = (numeric or type(expected) is type(actual)) and expected == actual
        if isinstance(expected, str) and isinstance(actual, str):
            mode = _rule(self.config.get("string_modes", {}), ep, self.config.get("strings", "exact"))
            equal = (actual.startswith(expected) if mode == "prefix" else
                     _normalize_string(expected, mode) == _normalize_string(actual, mode))
            for group in _rule(self.config.get("string_aliases", {}), ep, []):
                normalized = {_normalize_string(s, mode) for s in group}
                if _normalize_string(expected, mode) in normalized and _normalize_string(actual, mode) in normalized:
                    equal = True
        if equal:
            return [_event("match", ep, ap, expected, actual)]
        # Empty submitted containers have no factual assertions when nonempty
        # members were required; their required members are simply missing.
        wrong = [] if isinstance(actual, (list, dict)) and not actual and expected else _wrong(actual, ap)
        return _missing(expected, ep, "value or type mismatch") + wrong


def validate_reference(reference):
    if reference.get("schema_version") != 2 or not isinstance(reference.get("case_id"), str) or not reference["case_id"]:
        raise ValueError("reference needs schema_version: 2 and a nonempty case_id")
    if not isinstance(reference.get("questions"), list):
        raise ValueError("reference needs a questions list")
    ids = set()
    for question in reference["questions"]:
        if not isinstance(question, dict) or not isinstance(question.get("id"), (str, int)) or isinstance(question["id"], bool):
            raise ValueError("each question needs a string or integer id")
        qid = str(question["id"])
        if not qid or qid in ids:
            raise ValueError("question ids must be nonempty and unique")
        ids.add(qid)
        if not isinstance(question.get("prompt"), str):
            raise ValueError(f"question {qid} needs its public prompt")
        evaluation = question.get("evaluation", {"status": "scorable"})
        status = evaluation.get("status")
        if status not in ("scorable", "unevaluable"):
            raise ValueError(f"question {qid} has an unknown evaluation status")
        if status == "unevaluable":
            if not evaluation.get("reason"):
                raise ValueError(f"unevaluable question {qid} needs a reason")
        elif "expected" not in question:
            raise ValueError(f"scorable question {qid} needs expected (null is a literal value)")
        matcher = Matcher(question.get("match"), reference.get("time_zone"))
        if status == "scorable":
            matcher.validate_expected(question["expected"])


def score(reference, submission):
    """Score submitted answers against a versioned reference, without an LLM judge."""
    validate_reference(reference)
    if submission.get("schema_version") != 2 or submission.get("case_id") != reference["case_id"]:
        raise ValueError("answers need schema_version: 2 and the reference's exact case_id")
    if not isinstance(submission.get("answers"), list):
        raise ValueError("submission needs an answers list")
    answers = defaultdict(list)
    for index, response in enumerate(submission["answers"]):
        if not isinstance(response, dict) or not isinstance(response.get("question_id"), (str, int)) or isinstance(response["question_id"], bool):
            raise ValueError("each answer needs a string or integer question_id")
        if response.get("status") not in ("answered", "unknown", "unanswered"):
            raise ValueError("answer status must be answered, unknown, or unanswered")
        if response["status"] == "answered" and "answer" not in response:
            raise ValueError("answered responses need an answer value (false and null are allowed)")
        if "answer" in response:
            _json(response["answer"])
        answers[str(response["question_id"])].append((index, response))
    results, totals = [], Counter()
    unscored_atoms = 0
    for question in reference["questions"]:
        qid = str(question["id"])
        responses = answers.pop(qid, [])
        evaluation = question.get("evaluation", {"status": "scorable"})
        result = {"question_id": question["id"], "prompt": question["prompt"],
                  "source": question.get("source"), "response_indices": [i for i, _ in responses]}
        if evaluation["status"] == "unevaluable":
            known_atoms = len(_atoms(question["expected"])) if "expected" in question else None
            unscored_atoms += known_atoms or 0
            result.update(status="unevaluable", reason=evaluation["reason"],
                          atomic={"true_positive": 0, "missing": 0, "wrong": 0},
                          unscored_expected_atoms=known_atoms, audit=[])
        else:
            expected = question["expected"]
            response = responses[0][1] if responses else None
            response_status = response["status"] if response else "unanswered"
            matcher = Matcher(question.get("match"), reference.get("time_zone"))
            events = (matcher.compare(expected, response["answer"], "", f"/answers/{responses[0][0]}/answer")
                      if response_status == "answered" else _missing(expected, "", response_status))
            for index, extra in responses[1:]:
                events.extend(_wrong(extra.get("answer"), f"/answers/{index}/answer", "duplicate question response"))
            atomic = _counts(events)
            if response_status != "answered" and not responses[1:]:
                status = "unanswered"
            elif atomic["missing"] == 0 and atomic["wrong"] == 0:
                status = "fully_correct"
            elif atomic["true_positive"]:
                status = "partial"
            else:
                status = "incorrect"
            result.update(status=status, response_status=response_status, atomic=atomic, audit=events)
        result["rubric_label"] = RUBRIC[result["status"]]
        totals.update(result["atomic"])
        results.append(result)
    unexpected = []
    for qid, responses in answers.items():
        for index, response in responses:
            events = _wrong(response.get("answer"), f"/answers/{index}/answer", "unexpected question id")
            totals.update(_counts(events))
            unexpected.append({"question_id": qid, "response_index": index, "audit": events})
    question_counts = {status: sum(r["status"] == status for r in results) for status in RUBRIC}
    question_counts["total"] = len(results)
    scorable_questions = len(results) - question_counts["unevaluable"]
    expected_atoms = totals["true_positive"] + totals["missing"]
    attempted_atoms = totals["true_positive"] + totals["wrong"]
    denominator = expected_atoms + unscored_atoms
    extra_reasons = {"extra list member", "unexpected field", "duplicate question response", "unexpected question id"}
    wrong_events = [event for item in results + unexpected for event in item["audit"] if event["status"] == "wrong"]
    extra_atoms = sum(event.get("reason") in extra_reasons for event in wrong_events)
    return {"schema_version": 2, "scorer_version": VERSION, "case_id": reference["case_id"],
            "reference_sha256": _hash(reference), "submission_sha256": _hash(submission),
            "scorer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "question_counts": question_counts,
            "fully_correct_question_rate": (question_counts["fully_correct"] / len(results) if results else None),
            "fully_correct_question_rate_meaning": "Confirmed-correct lower bound over every reference question; unevaluable questions are unresolved, not failed.",
            "scorable_questions": scorable_questions,
            "scorable_question_rate": (question_counts["fully_correct"] / scorable_questions if scorable_questions else None),
            "mulder_style_labels": {RUBRIC[k]: question_counts[k] for k in RUBRIC},
            "atomic": {**{k: totals[k] for k in ("true_positive", "missing", "wrong")},
                       "extra_or_unexpected_atoms": extra_atoms,
                       "mismatched_value_atoms": totals["wrong"] - extra_atoms,
                       "scorable_reference_atoms": expected_atoms, "unscored_expected_atoms": unscored_atoms,
                       "known_reference_atoms": denominator,
                       "match_rate": totals["true_positive"] / denominator if denominator else None,
                       "match_rate_meaning": "Confirmed-match lower bound among known expected atoms; this excludes unknown atomic denominators and does not mark unevaluable atoms wrong.",
                       "scorable_match_rate": totals["true_positive"] / expected_atoms if expected_atoms else None,
                       "precision": totals["true_positive"] / attempted_atoms if attempted_atoms else None},
            "questions": results, "unexpected_questions": unexpected,
            "perfect_submission": bool(results) and question_counts["fully_correct"] == len(results) and not unexpected,
            "note": "Deterministic answer correctness under this versioned contract; not Lean proof verification "
                    "or Mulder's historical false-positive rate. Unevaluable questions remain in the question "
                    "denominator. Atomic rates cover known expected atoms; questions lacking an expected answer "
                    "have an unknown atomic denominator. Extra assertions are wrong under the declared answer "
                    "schema, not a general assessment of forensic truth."}


def report(result):
    q, a = result["question_counts"], result["atomic"]
    labels = ", ".join(f"{label} {count}" for label, count in result["mulder_style_labels"].items())
    return (f"Confirmed fully correct questions (lower bound): {q['fully_correct']} / {q['total']}\n"
            f"Among scorable questions: {q['fully_correct']} / {result['scorable_questions']}; "
            f"unevaluable {q['unevaluable']} (unresolved, not failed)\n{labels}\n"
            f"Atomic answers: {a['true_positive']} matched, {a['missing']} missing, {a['wrong']} wrong; "
            f"{a['unscored_expected_atoms']} known atoms unevaluable\n"
            f"Contract mismatches: {a['extra_or_unexpected_atoms']} extra/unexpected atoms, "
            f"{a['mismatched_value_atoms']} unequal values (not forensic false-positive counts)\n"
            f"Unexpected question responses: {len(result['unexpected_questions'])}\n{result['note']}")


def _load(path):
    def invalid(value):
        raise ValueError(f"non-finite JSON number: {value}")
    value = json.loads(Path(path).read_text(), parse_constant=invalid)
    if not isinstance(value, dict):
        raise ValueError(f"scoring input must be a JSON object: {path}")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    output = Path(args.out)
    try:
        if output.exists() or output.is_symlink():
            raise ValueError(f"refusing to overwrite existing scoring output: {output}")
        result = score(_load(args.reference), _load(args.answers))
        result["inputs"] = {name: {"path": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                            for name, path in (("reference", args.reference), ("answers", args.answers))}
        encoded = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation also protects a file or symlink created after the check.
        with output.open("x") as stream:
            stream.write(encoded)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    print(report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
