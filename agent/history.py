"""Claim attempts and explicit revision links, kept apart from proof validity."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta
import json
import re


_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z")
_CLASS = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\Z")
_STATES = ("accepted", "refused", "duplicate", "failed", "unknown")


def validate_revision(revises, previous_proposals, current_id=None):
    """Check that an explicit revision ID names an earlier proposal from this run.

    IDs are opaque: their numeric suffix never implies order.
    """
    if revises is None:
        return None
    if not isinstance(revises, str) or not _ID.fullmatch(revises):
        raise ValueError("revises must be a prior proposal finding_id")
    if current_id is not None and (not isinstance(current_id, str) or not _ID.fullmatch(current_id)):
        raise ValueError("current_id must be a proposal finding_id")
    if revises == current_id:
        raise ValueError("a proposal cannot revise itself")
    if not isinstance(previous_proposals, (list, tuple)) or any(
            not isinstance(row, dict) for row in previous_proposals):
        raise ValueError("previous_proposals must contain proposal objects from one run")
    rows = list(previous_proposals)
    if current_id is not None:
        cutoff = next((i for i, row in enumerate(rows) if row.get("finding_id") == current_id), len(rows))
        rows = rows[:cutoff]
    for field in ("case_id", "run_id"):
        scopes = [row[field] for row in rows if row.get(field) is not None]
        if scopes and any(scope != scopes[0] for scope in scopes[1:]):
            raise ValueError("previous proposals have conflicting run or case scopes")
    targets = [row for row in rows if row.get("finding_id") == revises]
    if not targets:
        raise ValueError("revises names an unknown or forward proposal; use a prior finding_id from this run")
    if any(row != targets[0] for row in targets[1:]):
        raise ValueError("revises names conflicting definitions of a proposal")
    return revises


def _rows(value, label):
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError(label + " must be a list of parsed log entries or None")
    return list(value)


def _finding_id(value):
    return value if isinstance(value, str) and _ID.fullmatch(value) else None


def _claim(value):
    # Claims may arrive as JSON strings; parse them only to compare IDs.
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            pass
    return value


def _timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if parsed.utcoffset() == timedelta(0) else None


def _error_class(value):
    if isinstance(value, dict):
        value = value.get("type", value.get("class"))
    return value if isinstance(value, str) and _CLASS.fullmatch(value) else None


def _base_attempt(attempt_id, source, index):
    return {"attempt_id": attempt_id, "source": source, "source_index": index,
            "audit_sequence": None, "call_id": None, "finding_id": None,
            "status": "unknown", "proof_status": "unknown", "new_proposal": None,
            "question": None, "claim": None, "started_at": None, "completed_at": None,
            "duration_ns": None, "error": None, "revises": None,
            "revision_status": "none", "revision_error": None, "duplicate_of": None,
            "proposal_index": None, "problems": []}


def _proposal_attempt(row, index):
    attempt = _base_attempt(f"proposal:{index}", "proposal_log", index)
    attempt["proposal_index"] = index
    if not isinstance(row, dict):
        attempt["problems"].append("proposal entry is not an object")
        return attempt
    status = row.get("status")
    attempt.update(finding_id=_finding_id(row.get("finding_id")),
                   question=deepcopy(row.get("question")), claim=deepcopy(row.get("claim")),
                   status={"verified": "accepted", "rejected": "refused", "error": "failed"}.get(status, "unknown"),
                   proof_status=status if status in ("verified", "rejected") else "unknown",
                   new_proposal=True)
    if attempt["finding_id"] is None:
        attempt["problems"].append("proposal finding_id is missing or invalid")
    # checked_in_ms is not a wall-clock time, so no timestamp is set.
    return attempt


def summarize_history(proposals, audit_events=None, audit_verification=None):
    """Return the observed attempt history without changing the inputs.

    Proposals the audit log does not match are listed separately. A passed audit check
    does not prove the history is complete.
    """
    proposal_rows = _rows(proposals, "proposals")
    events = _rows(audit_events, "audit_events")
    problems = []
    by_id = {}
    for index, row in enumerate(proposal_rows, 1):
        if isinstance(row, dict) and _finding_id(row.get("finding_id")):
            by_id.setdefault(row["finding_id"], []).append((index, row))
    integrity = "unavailable" if audit_events is None else "not_checked"
    if audit_events is not None and isinstance(audit_verification, dict):
        if audit_verification.get("passed") is True:
            integrity = "passed"
        elif audit_verification.get("passed") is False:
            integrity = "failed"
            problems.append("audit integrity verification failed; audit entries are diagnostic only")
    attempts, matched, observed = [], set(), {}
    if audit_events is None:
        attempts = [_proposal_attempt(row, i) for i, row in enumerate(proposal_rows, 1)]
    else:
        call_ids = set()
        for index, event in enumerate(events, 1):
            if not isinstance(event, dict):
                problems.append(f"audit entry {index} is not an object")
                continue
            if event.get("sequence") != index or isinstance(event.get("sequence"), bool):
                problems.append(f"audit entry {index} has missing, partial, or out-of-order sequence")
            if event.get("tool") != "check":
                continue
            attempt = _base_attempt(f"audit:{index}", "audit_log", index)
            attempt["audit_integrity"] = integrity
            attempt["audit_sequence"] = event.get("sequence") if type(event.get("sequence")) is int else None
            call_id = event.get("call_id")
            if isinstance(call_id, str) and call_id:
                attempt["call_id"] = call_id
                if call_id in call_ids:
                    attempt["problems"].append("duplicate audit call_id")
                call_ids.add(call_id)
            else:
                attempt["problems"].append("audit call_id is missing")
            args = event.get("arguments")
            result = event.get("result")
            args_valid = isinstance(args, dict) and "claim" in args and isinstance(args.get("question"), str)
            if args_valid:
                attempt.update(question=args["question"], claim=deepcopy(args["claim"]))
            else:
                attempt["problems"].append("check arguments are missing or incomplete")
            result = result if isinstance(result, dict) else {}
            result_status = result.get("status")
            attempt["proof_status"] = result_status if result_status in ("verified", "rejected") else "unknown"
            event_id, result_id = _finding_id(event.get("finding_id")), _finding_id(result.get("finding_id"))
            conflict = bool(event_id and result_id and event_id != result_id)
            if conflict:
                attempt["problems"].append("audit and result finding_id conflict")
            else:
                attempt["finding_id"] = event_id or result_id
            fid = attempt["finding_id"]
            bindings = by_id.get(fid, [])
            if bindings:
                if any(row != bindings[0][1] for _, row in bindings[1:]):
                    conflict = True
                    attempt["problems"].append("finding_id has conflicting proposal definitions")
                else:
                    proposal_index, proposal = bindings[0]
                    attempt["proposal_index"] = proposal_index
                    if args_valid and "claim" in proposal and _claim(args["claim"]) != _claim(proposal["claim"]):
                        conflict = True
                        attempt["problems"].append("check claim conflicts with its returned proposal ID")
                    if result_status in ("verified", "rejected") and proposal.get("status") != result_status:
                        conflict = True
                        attempt["problems"].append("check result conflicts with recorded proposal status")
                    if not conflict:
                        matched.update(i for i, _ in bindings)
            duplicate = bool(fid and (fid in observed or result.get("note") == f"already proposed as {fid}"))
            outcome = event.get("outcome")
            if outcome == "error":
                attempt["status"] = "failed"
            elif args_valid and not conflict:
                if duplicate and result_status in ("verified", "rejected"):
                    attempt.update(status="duplicate", duplicate_of=fid, new_proposal=False)
                elif result_status in ("verified", "rejected"):
                    attempt["status"] = "accepted" if result_status == "verified" else "refused"
                    attempt["new_proposal"] = bool(bindings) if proposals is not None else None
            if conflict:
                attempt["status"] = "unknown"
                attempt["proof_status"] = "unknown"
            if not result:
                attempt["problems"].append("check result is unavailable; a result hash is not its contents")
            for field in ("started_at", "completed_at"):
                attempt[field] = _timestamp(event.get(field))
            duration = event.get("duration_ns")
            attempt["duration_ns"] = duration if type(duration) is int and duration >= 0 else None
            attempt["error"] = _error_class(event.get("error"))
            if isinstance(args, dict) and args.get("revises") is not None:
                requested = args["revises"]
                attempt["revises"] = requested if isinstance(requested, str) else None
                cutoff = attempt["proposal_index"] or 0
                prior = [row for i, row in enumerate(proposal_rows, 1) if isinstance(row, dict) and (
                    i < cutoff or row.get("finding_id") in observed or (duplicate and row.get("finding_id") == fid))]
                known = {row.get("finding_id") for row in prior}
                prior.extend(row for previous_id, row in observed.items() if previous_id not in known)
                try:
                    if not args_valid or conflict:
                        raise ValueError("revision cannot be linked from incomplete or conflicting check metadata")
                    validate_revision(requested, prior, current_id=None if duplicate else fid)
                    attempt["revision_status"] = "valid"
                except ValueError as error:
                    attempt.update(revision_status="invalid", revision_error=str(error))
            elif not isinstance(args, dict):
                attempt["revision_status"] = "unknown"
            if fid and not conflict and result_status in ("verified", "rejected"):
                observed.setdefault(fid, {"finding_id": fid, "claim": deepcopy(attempt["claim"]),
                                          "status": result_status})
            attempts.append(attempt)
    unmatched = ([_proposal_attempt(row, i) for i, row in enumerate(proposal_rows, 1) if i not in matched]
                 if audit_events is not None else [])
    available = proposals is not None or audit_events is not None
    counted = Counter(attempt["status"] for attempt in attempts)
    counts = {state: counted[state] if available else None for state in _STATES}
    counts.update(attempts=len(attempts) if available else None,
                  explicit_revisions=sum(a["revision_status"] == "valid" for a in attempts) if available else None,
                  invalid_revisions=sum(a["revision_status"] == "invalid" for a in attempts) if available else None)
    return {"schema_version": 1, "available": available,
            "ordering": "audit_log_order" if audit_events is not None else "proposal_log_order",
            "attempts": attempts, "unmatched_proposals": unmatched, "counts": counts,
            "audit_integrity": {"status": integrity},
            "coverage": {"completeness": "recorded_events_only", "complete": False,
                         "proposal_log_available": proposals is not None, "audit_available": audit_events is not None,
                         "proposal_rows": len(proposal_rows) if proposals is not None else None,
                         "matched_proposal_rows": len(matched) if audit_events is not None and proposals is not None else None,
                         "unmatched_proposal_rows": len(unmatched) if audit_events is not None and proposals is not None else None,
                         "attempts_without_timestamps": sum(a["started_at"] is None or a["completed_at"] is None for a in attempts),
                         "interrupted_calls": "unmeasured",
                         "unmatched_proposal_placement": "unknown relative to audit events"},
            "problems": problems,
            "disclaimer": "Recorded attempts and explicit revision assertions only. Statuses are recorded checker results, "
                          "not independent certificate verification. Duplicate attempts do not create new proofs. "
                          "No revision is inferred from similar claims. Interrupted calls may be absent; audit integrity "
                          "does not establish complete history or authenticate an author."}
