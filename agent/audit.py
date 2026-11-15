"""Append-only integrity records for completed Workbench tool calls.

This is not an identity/authenticity proof. A hash chain detects changes relative
to its retained head; a complete rewrite is detectable only with an independently
retained expected head. Calls interrupted before completion may have no event.
Arguments and returned tool values are recorded, but exception messages, process
environment, credentials, shell commands and network state are never collected.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path


LIMITATION = ("Integrity only, not identity or authenticity. Complete rewrites require "
              "an independently retained expected head to detect. Only completed "
              "calls are logged; interrupted calls may be absent.")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = {"schema_version", "sequence", "call_id", "started_at", "completed_at",
           "duration_ns", "tool", "arguments", "result", "result_sha256", "success",
           "outcome", "error", "finding_id", "previous_sha256", "event_sha256"}
AUDITED_TOOLS = frozenset(("forms", "sql", "fact", "check", "conclude", "plan",
                           "update_question", "evidence_needs", "collect", "review",
                           "answer", "inventory_page"))


class AuditError(RuntimeError):
    """The audit cannot be appended safely; its existing bytes remain intact."""


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _sha256(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(_):
    raise ValueError("non-finite JSON number")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def verify_audit(path, expected_head=None) -> dict:
    """Read a log without modifying it; optionally compare an external chain head.

    ``count`` counts parsed event objects, and ``head`` is the final stored digest.
    Neither is trustworthy when ``passed`` is false. Errors never quote log data.
    A valid empty file has count 0 and head None; a missing file fails verification.
    """
    problems, count, head, call_ids = [], 0, None, set()
    try:
        with Path(path).open("rb") as stream:
            for line_number, raw in enumerate(stream, 1):
                prefix = f"line {line_number}: "
                if not raw.endswith(b"\n"):
                    problems.append(prefix + "incomplete event (missing final newline)")
                try:
                    event = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
                    if not isinstance(event, dict):
                        raise ValueError("event must be an object")
                except (ValueError, UnicodeError):
                    problems.append(prefix + "malformed JSON event")
                    continue
                count += 1
                if set(event) != _FIELDS:
                    problems.append(prefix + "unexpected or missing event fields")
                if event.get("schema_version") != 1 or type(event.get("schema_version")) is not int:
                    problems.append(prefix + "unsupported schema version")
                if event.get("sequence") != line_number or type(event.get("sequence")) is not int:
                    problems.append(prefix + "sequence mismatch")
                call_id = event.get("call_id")
                if (not isinstance(call_id, str)
                        or not re.fullmatch(r"call-[0-9a-f]{32}", call_id)):
                    problems.append(prefix + "invalid call ID")
                elif call_id in call_ids:
                    problems.append(prefix + "duplicate call ID")
                else:
                    call_ids.add(call_id)
                if event.get("previous_sha256") != head:
                    problems.append(prefix + "previous digest mismatch")
                stored = event.get("event_sha256")
                if not isinstance(stored, str) or not _DIGEST.fullmatch(stored):
                    problems.append(prefix + "invalid event digest")
                unsigned = {k: v for k, v in event.items() if k != "event_sha256"}
                try:
                    if stored != _sha256(unsigned):
                        problems.append(prefix + "event digest mismatch")
                    if event.get("result_sha256") != _sha256(event.get("result")):
                        problems.append(prefix + "result digest mismatch")
                except (ValueError, TypeError):
                    problems.append(prefix + "noncanonical JSON event")
                head = stored if isinstance(stored, str) else None
                if (not isinstance(event.get("tool"), str) or event["tool"] not in AUDITED_TOOLS
                        or not isinstance(event.get("arguments"), dict)):
                    problems.append(prefix + "invalid tool or arguments")
                duration = event.get("duration_ns")
                if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
                    problems.append(prefix + "invalid duration")
                for name in ("started_at", "completed_at"):
                    stamp = event.get(name)
                    try:
                        if not isinstance(stamp, str) or not stamp.endswith("Z"):
                            raise ValueError("not UTC")
                        datetime.fromisoformat(stamp.removesuffix("Z") + "+00:00")
                    except ValueError:
                        problems.append(prefix + "invalid " + name)
                outcome = event.get("outcome")
                if (outcome not in ("success", "rejected", "error")
                        or type(event.get("success")) is not bool
                        or event["success"] != (outcome == "success")):
                    problems.append(prefix + "inconsistent outcome")
                error = event.get("error")
                if error is not None and (not isinstance(error, dict)
                        or set(error) != {"type"} or not isinstance(error.get("type"), str)
                        or outcome != "error" or event.get("result") is not None):
                    problems.append(prefix + "invalid exception record")
                result = event.get("result")
                finding_id = result.get("finding_id") if isinstance(result, dict) else None
                if event.get("finding_id") != finding_id:
                    problems.append(prefix + "finding ID differs from returned result")
    except OSError as error:
        problems.append("cannot read audit: " + type(error).__name__)
    if expected_head is not None:
        if not isinstance(expected_head, str) or not _DIGEST.fullmatch(expected_head):
            problems.append("expected head must be a SHA-256 digest")
        elif head != expected_head:
            problems.append("external expected head mismatch")
    return {"passed": not problems, "count": count, "head": head,
            "problems": problems, "limitation": LIMITATION}


class AuditLog:
    """One Workbench's append-only log, serialized by its existing reentrant lock.

    Reopening a run verifies the entire existing chain. Every append verifies it
    again and refuses damage instead of repairing or truncating it. This lock
    coordinates threads of this Workbench, not independent writer processes.
    """

    def __init__(self, path, lock=None):
        self.path = Path(path)
        self.lock = lock if lock is not None else threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            with self.path.open("ab"):
                pass
            self._state()

    def _state(self) -> dict:
        state = verify_audit(self.path)
        if not state["passed"]:
            raise AuditError("existing audit is invalid; refusing to append")
        return state

    def record(self, tool, arguments, action):
        """Run a JSON tool call, append its completion, and return or re-raise it."""
        with self.lock:
            state = self._state()
            # Snapshot arguments before execution; a tool may mutate its inputs.
            arguments = json.loads(_canonical(arguments))
            start, clock = _utc(), time.perf_counter_ns()
            call_id = "call-" + uuid.uuid4().hex
            try:
                result = action()
                # A completed action may return bytes or non-finite numbers.
                # Treat an unrecordable result as a logged tool failure, while
                # leaving valid return objects untouched.
                _canonical(result)
            except BaseException as error:
                self._append(state, tool, arguments, call_id, start,
                             time.perf_counter_ns() - clock, None,
                             {"type": type(error).__name__})
                raise
            self._append(state, tool, arguments, call_id, start,
                         time.perf_counter_ns() - clock, result, None)
            return result

    def _append(self, state, tool, arguments, call_id, start, duration, result, error):
        # Deliberately do not stringify exceptions or inspect runtime state.
        outcome = "success"
        if error is not None or (isinstance(result, dict) and "error" in result):
            outcome = "error"
        elif isinstance(result, dict) and result.get("status") == "rejected":
            outcome = "rejected"
        event = {"schema_version": 1, "sequence": state["count"] + 1,
                 "call_id": call_id, "started_at": start, "completed_at": _utc(),
                 "duration_ns": duration, "tool": tool, "arguments": arguments,
                 "result": result, "result_sha256": _sha256(result),
                 "success": outcome == "success", "outcome": outcome, "error": error,
                 "finding_id": result.get("finding_id") if isinstance(result, dict) else None,
                 "previous_sha256": state["head"]}
        event["event_sha256"] = _sha256(event)
        with self.path.open("ab") as stream:
            stream.write(_canonical(event) + b"\n")


def audited(method):
    """Decorate a public Workbench tool, including malformed invocation attempts."""
    signature = inspect.signature(method)

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        try:
            bound = signature.bind(self, *args, **kwargs)
            arguments = {k: v for k, v in bound.arguments.items() if k != "self"}
        except TypeError:
            arguments = {"positional": list(args), "keyword": kwargs}
        return self._audit.record(method.__name__, arguments,
                                  lambda: method(self, *args, **kwargs))
    return wrapped
