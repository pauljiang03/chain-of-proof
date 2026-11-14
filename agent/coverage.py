"""Pure, key-free coverage summaries of supplied run artifacts.

Counts describe recorded activity, not investigation completeness or answer
accuracy. No files are read, proofs rechecked, or audit signatures authenticated.
Pass the result of ``agent.audit.verify_audit`` as ``audit_verification`` when
available. An absent input is unmeasured, not an empty successful operation.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import re


TOOLS = frozenset(("forms", "sql", "fact", "check", "conclude"))
LIMITATIONS = [
    "Extracted records do not establish completeness of the original evidence.",
    "Inspection counts successful fact-tool returns with matching record IDs; SQL results, including aggregates, are not counted as full-record inspection.",
    "Completed audit events do not establish that a model understood a record; interrupted calls may be absent.",
    "Audit integrity is separate from authorship and requires an externally retained checkpoint to detect a complete rewrite.",
    "Certified finding counts use the supplied run's verified status; this helper does not independently verify certificates.",
    "Answer presence is not answer accuracy or forensic truth; no private reference is used.",
]


def _number(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _identity(value):
    return isinstance(value, str) and bool(value.strip())


def _digest(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _utc(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() == timedelta(0)
    except ValueError:
        return False


def _metric(**values):
    return {"status": "unmeasured", **values, "problems": []}


def _extract(metadata, health):
    out = _metric(record_count=None, by_kind=None, source=None)
    for label, value in (("facts_metadata", metadata), ("health", health)):
        if value is not None and not isinstance(value, dict):
            out["problems"].append(f"{label} must be an object")
    if out["problems"]:
        out["status"] = "invalid"
        return out
    metadata, health = metadata or {}, health or {}
    counts = [("facts_metadata", metadata.get("facts")), ("health", health.get("fact_count"))]
    supplied = [(name, value) for name, value in counts if value is not None]
    if any(not _number(value) for _, value in supplied):
        out["problems"].append("extracted record counts must be nonnegative integers")
    elif len({value for _, value in supplied}) > 1:
        out["problems"].append("facts_metadata and health record counts disagree")
    elif supplied:
        out.update(status="measured", source=supplied[0][0], record_count=supplied[0][1])
    kinds = metadata.get("by_kind", health.get("by_kind"))
    if kinds is not None:
        if not isinstance(kinds, dict) or any(not _identity(k) or not _number(v) for k, v in kinds.items()):
            out["problems"].append("by_kind must map record-kind names to nonnegative counts")
        elif out["record_count"] is not None and sum(kinds.values()) != out["record_count"]:
            out["problems"].append("by_kind does not sum to the extracted record count")
        else:
            out["by_kind"] = dict(sorted(kinds.items()))
    if out["problems"]:
        out.update(status="invalid", record_count=None, by_kind=None)
    return out


def _audit(events, verification):
    out = _metric(record_count=None, record_ids=None, completed_tool_calls=None,
                  by_tool=None, audit_integrity="unavailable")
    errors = _metric(error_count=None, rejected_count=None, errors=None)
    if events is None:
        out["problems"].append("audit events were not supplied")
        if verification is not None:
            out.update(status="invalid", audit_integrity="failed")
            errors.update(status="invalid", problems=["audit verification supplied without decoded events"])
        return out, errors
    out["audit_integrity"] = "not_checked"
    if not isinstance(events, list):
        out["problems"].append("audit events must be a list of completed event objects")
    else:
        seen, previous = set(), None
        for index, event in enumerate(events, 1):
            if not isinstance(event, dict):
                out["problems"].append(f"audit event {index} is not an object")
                continue
            call = event.get("call_id")
            if (type(event.get("schema_version")) is not int or event["schema_version"] != 1
                    or not _number(event.get("sequence")) or event["sequence"] != index
                    or not _identity(call) or call in seen
                    or not _identity(event.get("tool")) or event["tool"] not in TOOLS
                    or not isinstance(event.get("arguments"), dict)
                    or not isinstance(event.get("success"), bool)
                    or event.get("outcome") not in ("success", "rejected", "error")
                    or event["success"] != (event["outcome"] == "success")
                    or "result" not in event
                    or not _utc(event.get("started_at")) or not _utc(event.get("completed_at"))
                    or not _number(event.get("duration_ns"))
                    or not _digest(event.get("result_sha256")) or not _digest(event.get("event_sha256"))
                    or "previous_sha256" not in event or event["previous_sha256"] != previous):
                out["problems"].append(f"audit event {index} has invalid completed-event fields")
            if _identity(call):
                seen.add(call)
            previous = event.get("event_sha256")
    if verification is not None:
        if not isinstance(verification, dict) or not isinstance(verification.get("passed"), bool):
            out["audit_integrity"] = "failed"
            out["problems"].append("audit verification result is malformed")
        elif not verification["passed"]:
            out["audit_integrity"] = "failed"
            out["problems"].append("audit integrity verification failed")
        elif isinstance(events, list):
            head = events[-1].get("event_sha256") if events and isinstance(events[-1], dict) else None
            if verification.get("count") != len(events) or verification.get("head") != head:
                out["audit_integrity"] = "failed"
                out["problems"].append("audit verification count/head does not match supplied events")
            else:
                out["audit_integrity"] = "passed"
    if out["problems"]:
        out["status"] = errors["status"] = "invalid"
        errors["problems"] = list(out["problems"])
        return out, errors
    inspected, failures = set(), []
    for event in events:
        result = event["result"]
        # F1 records the Workbench method's parameter (fact_id); API-level
        # synthetic receipts may use id. Conflicting explicit selectors do not
        # establish which record was inspected.
        arguments = event["arguments"]
        requested = arguments.get("fact_id", arguments.get("id"))
        selectors_agree = "fact_id" not in arguments or "id" not in arguments or arguments["fact_id"] == arguments["id"]
        if (event["tool"] == "fact" and event["success"] and event["outcome"] == "success"
                and isinstance(result, dict) and "error" not in result
                and _number(result.get("id")) and _number(requested)
                and selectors_agree and result["id"] == requested):
            inspected.add(result["id"])
        if event["outcome"] == "error":
            error = event.get("error")
            error_type = error.get("type") if isinstance(error, dict) else error
            if not isinstance(error_type, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", error_type):
                error_type = None
            failures.append({"sequence": event["sequence"], "call_id": event["call_id"],
                             "tool": event["tool"], "error_type": error_type})
    out.update(status="measured", record_count=len(inspected), record_ids=sorted(inspected),
               completed_tool_calls=len(events), by_tool=dict(sorted(Counter(e["tool"] for e in events).items())))
    errors.update(status="measured", error_count=len(failures), errors=failures,
                  rejected_count=sum(e["outcome"] == "rejected" for e in events))
    return out, errors


def _findings(run):
    certified = _metric(finding_count=None, finding_ids=None, verification="not_performed")
    citations = _metric(record_count=None, record_ids=None)
    rows = run.get("findings")
    if rows is None:
        return certified, citations
    if not isinstance(rows, list):
        certified.update(status="invalid", problems=["run findings must be a list"])
        citations.update(status="invalid", problems=["run findings must be a list"])
        return certified, citations
    finding_ids, fact_ids = set(), set()
    missing_citations = False
    for row in rows:
        if not isinstance(row, dict):
            certified["problems"].append("a finding is not an object")
            continue
        if row.get("status") != "verified":
            continue
        finding_id = row.get("finding_id")
        if not _identity(finding_id) or finding_id in finding_ids:
            certified["problems"].append("certified finding IDs are missing or duplicated")
        else:
            finding_ids.add(finding_id)
        cited = row.get("cited_facts")
        if cited is None:
            missing_citations = True
        elif not isinstance(cited, list) or any(not isinstance(f, dict) or not _number(f.get("id")) for f in cited):
            citations["problems"].append("cited_facts must contain record objects with integer IDs")
        else:
            fact_ids.update(f["id"] for f in cited)
    if certified["problems"]:
        certified["status"] = "invalid"
        citations.update(status="invalid", problems=citations["problems"] + certified["problems"])
    else:
        certified.update(status="measured", finding_count=len(finding_ids), finding_ids=sorted(finding_ids))
        if citations["problems"]:
            citations["status"] = "invalid"
        elif missing_citations:
            citations["problems"].append("some certified findings lack citation information")
        else:
            citations.update(status="measured", record_count=len(fact_ids), record_ids=sorted(fact_ids))
    return certified, citations


def _questions(run, public, answers):
    out = _metric(total_count=None, answered_count=None, unknown_count=None,
                  unanswered_count=None, missing_count=None, unknown_ids=None,
                  unanswered_ids=None, missing_ids=None, unexpected_ids=None)
    if public is None:
        out["problems"].append("public question contract was not supplied")
        return out
    if (not isinstance(public, dict) or public.get("schema_version") != 2
            or not _identity(public.get("case_id")) or not isinstance(public.get("questions"), list)):
        out.update(status="invalid", problems=["public questions must be a schema-version-2 contract"])
        return out
    allowed = {"schema_version", "case_id", "title", "time_zone", "instructions", "questions", "contract_revision"}
    ids = []
    if set(public) - allowed:
        out["problems"].append("public contract contains unsupported/private fields")
    for row in public["questions"]:
        if (not isinstance(row, dict) or set(row) - {"id", "prompt", "answer_schema", "match"}
                or not _identity(row.get("id")) or row["id"] in ids):
            out["problems"].append("public question IDs/fields are invalid or duplicated")
        else:
            ids.append(row["id"])
    case = run.get("case", {})
    if isinstance(case, dict) and case.get("case_id") not in (None, public["case_id"]):
        out["problems"].append("run and public question case IDs differ")
    if out["problems"]:
        out["status"] = "invalid"
        return out
    out["total_count"] = len(ids)
    if answers is None:
        out["problems"].append("public answers were not supplied")
        return out
    if (not isinstance(answers, dict) or answers.get("schema_version") != 2
            or answers.get("case_id") != public["case_id"] or not isinstance(answers.get("answers"), list)):
        out.update(status="invalid", problems=["answers version, case ID, or response list is invalid"])
        return out
    seen, statuses = set(), {}
    for row in answers["answers"]:
        if (not isinstance(row, dict) or not _identity(row.get("question_id"))
                or row["question_id"] in seen or row.get("status") not in ("answered", "unknown", "unanswered")
                or (row["status"] == "answered" and "answer" not in row)):
            out["problems"].append("answer IDs/statuses are malformed or duplicated")
        else:
            seen.add(row["question_id"])
            statuses[row["question_id"]] = row["status"]
    if out["problems"]:
        out["status"] = "invalid"
        return out
    out.update(status="measured", answered_count=sum(statuses.get(q) == "answered" for q in ids),
               unexpected_ids=sorted(seen - set(ids)))
    for status in ("unknown", "unanswered"):
        group = sorted(q for q in ids if statuses.get(q) == status)
        out[status + "_ids"], out[status + "_count"] = group, len(group)
    missing = sorted(set(ids) - seen)
    out.update(missing_ids=missing, missing_count=len(missing))
    return out


def _health(metadata, health, extraction):
    out = _metric(reader_failure_count=None, unsupported_source_count=None,
                  warning_count=None, unclassified_issue_count=None, issues=None,
                  source=None, health_report="missing" if health is None else "supplied")
    if extraction["status"] == "invalid":
        out.update(status="invalid", problems=list(extraction["problems"]))
        return out
    if isinstance(health, dict) and "issues" in health:
        issues, source = health["issues"], "health.issues"
    elif isinstance(metadata, dict) and "unparsed" in metadata:
        issues, source = metadata["unparsed"], "facts_metadata.unparsed"
    else:
        out["problems"].append("no extraction issue report was supplied")
        return out
    if issues is None:
        out["problems"].append("extraction issue information is unknown")
        return out
    if not isinstance(issues, list) or any(not isinstance(item, str) for item in issues):
        out.update(status="invalid", problems=["extraction issue report must be a list of strings"])
        return out
    categorized = []
    for issue in issues:
        if re.search(r": reader [^:]+: [A-Za-z_][A-Za-z0-9_]*:", issue):
            category = "reader_failure"
        elif re.search(r"\bunsupported\b|\bnot (?:a )?supported\b", issue, re.I):
            category = "unsupported_source"
        elif re.search(r"\b[A-Za-z]*Warning:", issue):
            category = "warning"
        else:
            category = "unclassified_issue"
        categorized.append({"category": category, "message": issue})
    counts = Counter(item["category"] for item in categorized)
    out.update(status="measured", source=source, issues=categorized)
    for category in ("reader_failure", "unsupported_source", "warning", "unclassified_issue"):
        out[category + "_count"] = counts[category]
    return out


def summarize_coverage(run, *, facts_metadata=None, audit_events=None,
                       public_questions=None, answers=None, health=None,
                       audit_verification=None):
    """Summarize supplied artifacts without inferring missing measurements.

    ``facts_metadata`` is the fact file's ``_meta`` object, not its record list.
    ``audit_events`` is a decoded completed-event list (``None`` means missing).
    ``public_questions`` and ``answers`` are public schema-v2 objects.
    ``audit_verification`` is optional F1 ``verify_audit`` output; its count/head
    must match these events. An absent verification is explicitly not checked.
    """
    if not isinstance(run, dict):
        raise ValueError("run must be an object")
    extraction = _extract(facts_metadata, health)
    inspection, tool_failures = _audit(audit_events, audit_verification)
    certification, citations = _findings(run)
    case = run.get("case") if isinstance(run.get("case"), dict) else {}
    ended = case.get("ended") if isinstance(case.get("ended"), str) else None
    state = "unmeasured"
    if ended is not None:
        state = "failed" if case.get("is_error") or ended not in ("success", "time_limit") else (
            "budget_exhausted" if ended == "time_limit" else "completed")
        if ended != "time_limit" and case.get("exit_code") not in (None, 0):
            state = "failed"
    elif case.get("is_error") is True or case.get("exit_code") not in (None, 0):
        state = "failed"
    return {"schema_version": 1, "extraction": extraction, "inspection": inspection,
            "citations": citations, "certification": certification,
            "questions": _questions(run, public_questions, answers),
            "failures": {"run": {"status": state, "ended": ended},
                         "tools": tool_failures,
                         "extraction": _health(facts_metadata, health, extraction)},
            "limitations": list(LIMITATIONS)}
