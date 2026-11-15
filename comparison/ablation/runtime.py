"""Local four-tool bridge for fresh gpt-6.1-sol ablation subagents.

init creates a new public session; session serves newline JSON over stdin/stdout
with one loaded fact store. The controller must stop the investigator and close the
bridge before finalize. No provider, model launcher, scorer or private key is used.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import time
import uuid

from agent.case import read_profile, read_question_profile, with_questions
from comparison.ablation.mcp_server import dispatch, make_workbench
from comparison.ablation.prompt import build_prompt

MODEL = "gpt-6.1-sol"
STATUSES = ("completed", "time_limit", "failed", "cancelled")
SOURCES = ("comparison/ablation/runtime.py", "comparison/ablation/mcp_server.py",
           "comparison/ablation/prompt.py", "comparison/ablation/capture.py",
           "agent/tools.py", "agent/brief.py", "agent/case.py", "agent/audit.py",
           "agent/history.py", "agent/coverage.py", "checker/claims.py", "checker/check.py",
           "checker/facts.py", "checker/needs.py", "checker/export.py", "checker/report.py",
           "verifier/verify.py", "lean/lean-toolchain", "lean/lakefile.toml",
           "lean/ChainOfProof.lean", "lean/ChainOfProof/Theorems.lean", "lean/ChainOfProof/Sets.lean",
           "lean/ChainOfProof/Facts.lean", "lean/ChainOfProof/Claim.lean",
           "lean/ChainOfProof/Check.lean", "lean/ChainOfProof/Census.lean")
SCOPE = ("Tool restrictions are procedural instructions for a Codex subagent, not an OS "
         "sandbox. No independent model revision, token usage, cost or provider identity "
         "is observed by this bridge. Direct model answers remain unverified. Local "
         "hashes bind recorded bytes, not disk authenticity or complete agent behavior.")


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _json(raw):
    def constant(_):
        raise ValueError("non-finite JSON number")
    result = json.loads(raw, object_pairs_hook=_pairs, parse_constant=constant)
    json.dumps(result, allow_nan=False)  # also rejects overflow such as 1e999
    return result


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


@contextmanager
def _regular(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("input must be a regular file")
        yield stream


def _read(path):
    with _regular(path) as stream:
        return stream.read()


def _binding(path):
    digest, count = hashlib.sha256(), 0
    with _regular(path) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            count += len(chunk)
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "bytes": count}


def _write(path, raw):
    with Path(path).open("xb") as stream:
        stream.write(raw)


def _root(run):
    run = Path(run).absolute()
    if run.is_symlink() or not run.is_dir():
        raise ValueError("run must be an existing regular directory")
    return run.resolve()


@contextmanager
def _locked(run):
    run = _root(run)
    fd = os.open(run / ".bridge.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a+b") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("bridge lock must be a regular file")
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("run has an active bridge or finalizer") from error
        try:
            yield run
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _session(run, *, active=True):
    if active and any((run / name).exists() or (run / name).is_symlink()
                      for name in (".finalizing", "trial.json", "seal.json")):
        raise ValueError("run is frozen; further tool calls and finalization are refused")
    session = _json(_read(run / "session.json"))
    if (not isinstance(session, dict) or session.get("schema_version") != 1
            or session.get("arm") not in ("A", "C") or session.get("requested_model") != MODEL):
        raise ValueError("invalid session metadata")
    facts = session["facts"]
    if not isinstance(facts.get("path"), str) or not Path(facts["path"]).is_absolute():
        raise ValueError("facts path must be absolute")
    if _binding(facts["path"]) != {k: facts[k] for k in ("sha256", "bytes")}:
        raise ValueError("facts changed since session initialization")
    for name in ("case-profile.json", "questions.json", "prompt.md"):
        if _binding(run / name) != session["inputs"][name]:
            raise ValueError("public session input changed: " + name)
    repository = Path(__file__).resolve().parents[2]
    for name in SOURCES:
        if _binding(repository / name)["sha256"] != session["software"]["source_sha256"][name]:
            raise ValueError("tool implementation changed since session initialization: " + name)
    return session


def init_session(*, arm, facts, case_profile, questions, out):
    if arm not in ("A", "C"):
        raise ValueError("arm must be A or C")
    facts = Path(facts).absolute()
    facts_binding = _binding(facts)
    profile_bytes, question_bytes = _read(case_profile), _read(questions)
    _json(profile_bytes)
    _json(question_bytes)
    # Public readers reject reference fields. No path embedded in their JSON is followed.
    public = read_question_profile(Path(questions))
    profile = with_questions(read_profile(Path(case_profile)), public)
    if _read(case_profile) != profile_bytes or _read(questions) != question_bytes:
        raise ValueError("public input changed during initialization")
    payloads = {"case-profile.json": profile_bytes, "questions.json": question_bytes,
                "prompt.md": build_prompt(profile, public, arm).encode("utf-8")}
    repository = Path(__file__).resolve().parents[2]
    session = {"schema_version": 1, "kind": "ablation-subagent-session", "arm": arm,
               "created_at": _now(), "requested_model": MODEL,
               "model_pinning": "requested_platform_model; immutable_revision_not_observed",
               "facts": dict(facts_binding, path=str(facts)),
               "inputs": {name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                          for name, raw in payloads.items()},
               "software": {"python": sys.version, "source_sha256": {
                   name: _binding(repository / name)["sha256"] for name in SOURCES}},
               "scope": SCOPE}
    out = Path(out).absolute()
    out.mkdir(parents=True, exist_ok=False)
    for name, raw in payloads.items():
        _write(out / name, raw)
    _write(out / "session.json", _encoded(session))
    return session


def _record_call(run, bench, tool, arguments):
    # This runtime-owned record retains batch positions; each claim has its own
    # normal Workbench audit event too. close is transport and is never audited.
    call_id = "bridge-" + uuid.uuid4().hex
    started, started_ns = _now(), time.monotonic_ns()
    result, error = None, None
    try:
        result = dispatch(bench, tool, arguments)
        return result
    except BaseException as caught:
        error = {"type": type(caught).__name__}
        raise
    finally:
        values = result if isinstance(result, list) else [result]
        event = {"call_id": call_id, "tool": tool, "arguments": arguments,
                 "started_at": started, "completed_at": _now(),
                 "duration_ns": time.monotonic_ns() - started_ns,
                 "result": result, "error": error,
                 "batch": [{"position": index + 1,
                            "candidate_id": value.get("candidate_id"),
                            "finding_id": value.get("finding_id")}
                           for index, value in enumerate(values) if isinstance(value, dict)]}
        fd = os.open(run / "bridge-calls.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND
                     | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        with os.fdopen(fd, "ab") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("bridge log must be a regular file")
            stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False).encode() + b"\n")


@contextmanager
def _bench(run):
    with _locked(run) as directory:
        session = _session(directory)
        bench = make_workbench(session["arm"], session["facts"]["path"], directory)
        try:
            yield directory, session, bench
        finally:
            bench._db.close()


def call_tool(run, tool, arguments):
    # Normalize through strict finite JSON for callers that do not use the CLI.
    arguments = _json(json.dumps(arguments, allow_nan=False))
    with _bench(run) as (directory, _, bench):
        return _record_call(directory, bench, tool, arguments)


def serve_session(run, *, stdin=None, stdout=None):
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    def emit(value):
        print(json.dumps(value, ensure_ascii=False, allow_nan=False), file=stdout, flush=True)
    with _bench(run) as (directory, session, bench):
        emit({"status": "ready", "arm": session["arm"]})
        for line in stdin:
            try:
                request = _json(line)
                if not isinstance(request, dict) or set(request) - {"tool", "arguments"}:
                    raise ValueError("request must contain tool and optional arguments")
                if request.get("tool") == "close":
                    if request.get("arguments", {}) != {}:
                        raise ValueError("close takes no arguments")
                    break
                result = _record_call(directory, bench, request.get("tool"),
                                      request.get("arguments", {}))
                emit({"ok": True, "result": result})
            except (ValueError, TypeError, KeyError) as error:
                emit({"ok": False, "error": {"type": type(error).__name__, "message": str(error)}})
            except Exception as error:
                emit({"ok": False, "error": {"type": type(error).__name__}})
        emit({"status": "closed"})
    return 0


def finalize_session(run, *, summary, status, elapsed_seconds=None):
    if status not in STATUSES:
        raise ValueError("invalid terminal status")
    if elapsed_seconds is not None and (isinstance(elapsed_seconds, bool)
            or not isinstance(elapsed_seconds, (float, int))
            or not math.isfinite(elapsed_seconds) or elapsed_seconds < 0):
        raise ValueError("elapsed seconds must be finite and nonnegative")
    summary_raw = _read(summary)
    summary_raw.decode("utf-8")
    with _locked(run) as directory:
        session = _session(directory)
        session_binding = _binding(directory / "session.json")
        # Leave this marker on any failure: resuming tool calls would invalidate a
        # partial seal. Preserve all prior artifacts for coordinator inspection.
        _write(directory / ".finalizing", _encoded({"started_at": _now()}))
        _write(directory / "summary.md", summary_raw)
        metadata = {"schema_version": 1, "kind": "ablation-subagent-trial",
                    "arm": session["arm"], "status": status, "finalized_at": _now(),
                    "investigator_status": status,
                    "requested_model": MODEL, "observed_model_ids": None,
                    "immutable_model_revision": None, "model_usage": None,
                    "model_observation_status": "not_observed_by_bridge",
                    "elapsed_seconds": elapsed_seconds,
                    "elapsed_source": "controller_supplied" if elapsed_seconds is not None else "unavailable",
                    "session": session_binding, "facts": session["facts"],
                    "summary": _binding(directory / "summary.md"), "scope": SCOPE}
        if session["arm"] == "A":
            from comparison.ablation.capture import seal_candidates
            seal = seal_candidates(directory, facts_path=session["facts"]["path"], metadata=metadata)
            metadata["candidate_seal"] = _binding(directory / "seal.json")
            metadata["candidates"] = seal["candidates"]["count"]
            metadata["claim_status"] = "unverified"
        else:
            from checker.export import bundle
            from checker.facts import open_source
            from checker.report import render
            from checker import claims
            from checker.check import render_lean
            from verifier.verify import verify_run
            public = read_question_profile(directory / "questions.json")
            profile = with_questions(read_profile(directory / "case-profile.json"), public)
            data = bundle(directory, profile.name, public_questions=public,
                          case_metadata={"backend": "codex-subagent", "model": MODEL,
                                         "ended": "success" if status == "completed" else status,
                                         "facts_sha256": session["facts"]["sha256"],
                                         "ablation_arm": "C"})
            source = open_source(session["facts"]["path"])
            verification = verify_run(data, source)
            if verification["passed"]:
                # verify_run rebuilds proofs; it intentionally does not trust the
                # stored .lean text. Show that same regenerated source in the report.
                for finding in data["findings"]:
                    claim = claims.parse(finding["claim"])
                    ids, found = claims.cited_facts(claim, source)
                    finding["lean"] = render_lean(finding["finding_id"], [found[i] for i in ids], claim)
                metadata["report_proofs"] = "regenerated_from_frozen_facts"
            else:
                metadata["status"] = "failed"
                metadata["failure_reason"] = "certificate_replay_failed"
            _write(directory / "run.json", _encoded(data))
            _write(directory / "verification.json", _encoded(verification))
            if verification["passed"]:
                _write(directory / "report.md", render(data).encode("utf-8"))
            metadata["certificate_replay"] = verification
            metadata["run"] = _binding(directory / "run.json")
        # Detect changed inputs during finalization, before publishing completion.
        _session(directory, active=False)
        if _binding(directory / "session.json") != session_binding:
            raise ValueError("session changed during finalization")
        _write(directory / "trial.json", _encoded(metadata))
        return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a new public session")
    init.add_argument("--arm", choices=("A", "C"), required=True)
    for option in ("facts", "case-profile", "questions", "out"):
        init.add_argument("--" + option, required=True)
    session = commands.add_parser("session", help="persistent newline-JSON stdio bridge")
    session.add_argument("--run", required=True)
    tool = commands.add_parser("tool", help="one tool call (reloads the facts)")
    tool.add_argument("--run", required=True)
    choices = tool.add_subparsers(dest="tool", required=True)
    choices.add_parser("forms")
    choices.add_parser("sql").add_argument("query")
    choices.add_parser("fact").add_argument("id", type=int)
    check = choices.add_parser("check")
    check.add_argument("--question", required=True)
    check.add_argument("--claim", action="append", required=True, help="finite JSON; repeat for a batch")
    check.add_argument("--revises")
    final = commands.add_parser("finalize", help="freeze a stopped investigator's run")
    final.add_argument("--run", required=True)
    final.add_argument("--summary", required=True, help="unaltered final model response file")
    final.add_argument("--status", choices=STATUSES, required=True)
    final.add_argument("--elapsed-seconds", type=float)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init_session(arm=args.arm, facts=args.facts, case_profile=args.case_profile,
                                  questions=args.questions, out=args.out)
        elif args.command == "session":
            return serve_session(args.run)
        elif args.command == "finalize":
            result = finalize_session(args.run, summary=args.summary, status=args.status,
                                      elapsed_seconds=args.elapsed_seconds)
        else:
            arguments = {}
            if args.tool == "sql":
                arguments["query"] = args.query
            elif args.tool == "fact":
                arguments["id"] = args.id
            elif args.tool == "check":
                claims = [_json(raw) for raw in args.claim]
                arguments = {"question": args.question}
                arguments.update({"claim": claims[0]} if len(claims) == 1 else {"claims": claims})
                if args.revises is not None:
                    arguments["revises"] = args.revises
            result = call_tool(args.run, args.tool, arguments)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        if args.command == "finalize" and result.get("failure_reason"):
            return 1
        return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as error:
        print("ablation: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
