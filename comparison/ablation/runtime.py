"""Protocol-versioned local bridge for fresh gpt-6.1-sol ablation subagents.

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
from comparison.ablation.mcp_server import dispatch, make_workbench, PROTOCOLS
from comparison.ablation.prompt import build_prompt

MODEL = "gpt-6.1-sol"
STATUSES = ("completed", "time_limit", "failed", "cancelled")
# Pin the complete shared module surface so a newly imported helper cannot be
# omitted silently. This includes module bytes only, never private data/artifacts.
_REPOSITORY = Path(__file__).resolve().parents[2]
SOURCES = tuple(sorted({str(path.relative_to(_REPOSITORY))
    for package in ("agent", "checker", "verifier", "comparison/ablation")
    for path in (_REPOSITORY / package).glob("*.py")} | {
    "lean/lean-toolchain", "lean/lakefile.toml", "lean/ChainOfProof.lean",
    *(str(path.relative_to(_REPOSITORY)) for path in (_REPOSITORY / "lean/ChainOfProof").glob("*.lean"))}))

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
    protocol = session.get("protocol", "literal-v1")
    if protocol not in PROTOCOLS:
        raise ValueError("invalid session protocol")
    if (protocol == "claim-bindings-v2") != ("run-manifest.json" in session["inputs"]):
        raise ValueError("session protocol does not match its bound public inputs")
    facts = session["facts"]
    if not isinstance(facts.get("path"), str) or not Path(facts["path"]).is_absolute():
        raise ValueError("facts path must be absolute")
    if _binding(facts["path"]) != {k: facts[k] for k in ("sha256", "bytes")}:
        raise ValueError("facts changed since session initialization")
    for name in ("case-profile.json", "questions.json", "prompt.md"):
        if _binding(run / name) != session["inputs"][name]:
            raise ValueError("public session input changed: " + name)
    if protocol == "claim-bindings-v2":
        if _binding(run / "run-manifest.json") != session["inputs"]["run-manifest.json"]:
            raise ValueError("evidence manifest changed since session initialization")
    repository = Path(__file__).resolve().parents[2]
    if set(session["software"]["source_sha256"]) != set(SOURCES):
        raise ValueError("pinned tool implementation source set changed since session initialization")
    for name in SOURCES:
        if _binding(repository / name)["sha256"] != session["software"]["source_sha256"][name]:
            raise ValueError("tool implementation changed since session initialization: " + name)
    return session


def init_session(*, arm, facts, case_profile, questions, out, protocol="literal-v1"):
    if arm not in ("A", "C"):
        raise ValueError("arm must be A or C")
    if protocol not in PROTOCOLS:
        raise ValueError("unknown ablation protocol")
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
                "prompt.md": build_prompt(profile, public, arm, protocol=protocol).encode("utf-8")}
    if protocol == "claim-bindings-v2":
        payloads["run-manifest.json"] = _encoded({"schema_version": 1, "protocol": protocol,
            "inputs": {"facts": dict(facts_binding, path=str(facts))}})
    repository = Path(__file__).resolve().parents[2]
    session = {"schema_version": 1, "kind": "ablation-subagent-session", "arm": arm,
               "created_at": _now(), "requested_model": MODEL, "protocol": protocol,
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
    if protocol == "claim-bindings-v2":
        from agent.investigation import Investigation
        Investigation(out).initialize(profile, public)
    return session


def _record_call(run, bench, tool, arguments, protocol="literal-v1"):
    # This runtime-owned record retains batch positions; each claim has its own
    # normal Workbench audit event too. close is transport and is never audited.
    call_id = "bridge-" + uuid.uuid4().hex
    started, started_ns = _now(), time.monotonic_ns()
    result, error = None, None
    try:
        result = dispatch(bench, tool, arguments, protocol=protocol)
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
        bench = make_workbench(session["arm"], session["facts"]["path"], directory, protocol=session.get("protocol", "literal-v1"))
        try:
            yield directory, session, bench
        finally:
            bench._db.close()
            _close_source(bench.source)


def call_tool(run, tool, arguments):
    # Normalize through strict finite JSON for callers that do not use the CLI.
    arguments = _json(json.dumps(arguments, allow_nan=False))
    with _bench(run) as (directory, session, bench):
        return _record_call(directory, bench, tool, arguments, protocol=session.get("protocol", "literal-v1"))


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
                                      request.get("arguments", {}), protocol=session.get("protocol", "literal-v1"))
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
                    "arm": session["arm"], "protocol": session.get("protocol", "literal-v1"),
                    "status": status, "finalized_at": _now(),
                    "investigator_status": status,
                    "requested_model": MODEL, "observed_model_ids": None,
                    "immutable_model_revision": None, "model_usage": None,
                    "model_observation_status": "not_observed_by_bridge",
                    "elapsed_seconds": elapsed_seconds,
                    "elapsed_source": "controller_supplied" if elapsed_seconds is not None else "unavailable",
                    "session": session_binding, "facts": session["facts"],
                    "summary": _binding(directory / "summary.md"), "scope": SCOPE}
        candidate_binding = None
        data = verification = None
        if session["arm"] == "A":
            from comparison.ablation.capture import seal_candidates
            seal = seal_candidates(directory, facts_path=session["facts"]["path"], metadata=metadata)
            metadata["candidate_seal"] = _binding(directory / "seal.json")
            metadata["candidates"] = seal["candidates"]["count"]
            metadata["claim_status"] = "unverified"
            candidate_binding = {"exists": True, **{key: seal["candidates"][key] for key in ("sha256", "bytes")}}
        else:
            from checker.export import bundle
            from checker.facts import open_source
            from checker.report import render
            from checker import claims
            from checker.check import render_lean
            from verifier.verify import verify_run
            public = read_question_profile(directory / "questions.json")
            profile = with_questions(read_profile(directory / "case-profile.json"), public)
            if session.get("protocol", "literal-v1") == "claim-bindings-v2":
                candidate_binding = _candidate_binding(directory / "proposals.jsonl")
            data = bundle(directory, profile.name, public_questions=public,
                          case_metadata={"backend": "codex-subagent", "model": MODEL,
                                         "ended": "success" if status == "completed" else status,
                                         "facts_sha256": session["facts"]["sha256"],
                                         "ablation_arm": "C"})
            source = open_source(session["facts"]["path"])
            try:
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
            finally:
                _close_source(source)
            _write(directory / "run.json", _encoded(data))
            _write(directory / "verification.json", _encoded(verification))
            if verification["passed"]:
                _write(directory / "report.md", render(data).encode("utf-8"))
            metadata["certificate_replay"] = verification
            metadata["run"] = _binding(directory / "run.json")
        if session.get("protocol", "literal-v1") == "claim-bindings-v2":
            metadata["projection"] = _finalize_projection(directory, session, summary_raw,
                candidate_binding=candidate_binding, verified_bundle=data, verification=verification)
        # Detect changed inputs during finalization, before publishing completion.
        _session(directory, active=False)
        if _binding(directory / "session.json") != session_binding:
            raise ValueError("session changed during finalization")
        _write(directory / "trial.json", _encoded(metadata))
        return metadata


def _close_source(source):
    close = getattr(source, "close", None)
    if callable(close):
        close()
    else:
        database = getattr(source, "_db", None)
        if database is not None:
            database.close()


def _candidate_binding(path):
    if path.is_symlink():
        raise ValueError("candidate log must not be a symlink")
    if not path.exists():
        return {"exists": False, "sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0}
    return {"exists": True, **_binding(path)}


def _certified_candidates(candidates, bundle, verification):
    """Match every admitted proposal to its exact independently replayed certificate."""
    from agent.answer_projection import claim_digest
    if not isinstance(verification, dict) or verification.get("passed") is not True:
        raise ValueError("certificate replay did not pass")
    findings = bundle.get("findings") if isinstance(bundle, dict) else None
    receipts = verification.get("findings")
    if not isinstance(findings, list) or not isinstance(receipts, list):
        raise ValueError("certificate bundle and individual replay receipts are required")
    certificates, checked = {}, {}
    for row in findings:
        fid = row.get("finding_id") if isinstance(row, dict) else None
        if not isinstance(fid, str) or not fid or fid in certificates or "claim" not in row:
            raise ValueError("missing or ambiguous certificate identity")
        certificates[fid] = row
    for row in receipts:
        fid = row.get("finding_id") if isinstance(row, dict) else None
        if (not isinstance(fid, str) or not fid or fid in checked or row.get("problems") != []):
            raise ValueError("missing, ambiguous or unsuccessful individual replay receipt")
        checked[fid] = row
    if (set(certificates) != set(checked)
            or type(verification.get("checked")) is not int or verification["checked"] != len(checked)
            or type(verification.get("verified")) is not int or verification["verified"] != len(checked)
            or type(verification.get("failed")) is not int or verification["failed"] != 0):
        raise ValueError("certificate replay coverage does not match the bundle")
    for candidate in candidates:
        if candidate.get("status") != "verified":
            continue
        fid = candidate.get("finding_id")
        certificate = certificates.get(fid)
        if certificate is None or fid not in checked:
            raise ValueError("verified proposal has no matching independently replayed certificate: " + str(fid))
        if certificate.get("status") != "verified" or claim_digest(candidate["claim"]) != claim_digest(certificate["claim"]):
            raise ValueError("verified proposal differs from its independently replayed certificate: " + str(fid))


def _finalize_projection(directory, session, summary_raw, *, candidate_binding, verified_bundle=None, verification=None):
    """Retain the exact final binding proposal, then project without answer repair."""
    from comparison.ablation.bindings import extract_bindings, resolve_hashes
    from comparison.ablation.projection import project_a, project_c
    from checker.facts import open_source
    public = read_question_profile(directory / "questions.json")
    report = {"status": "unavailable", "protocol": "claim-bindings-v2",
              "scope": "Claim-field projection only; no private scoring or answer completeness certification.",
              "captured_candidates": candidate_binding}
    stage = "binding_document"
    try:
        document, raw = extract_bindings(summary_raw, public)
        _write(directory / "bindings.raw.json", raw)
        _write(directory / "bindings.json", _encoded(document))
        report["raw_bindings"] = _binding(directory / "bindings.raw.json")
        report["bindings"] = _binding(directory / "bindings.json")
        stage = "candidate_resolution"
        name = "candidates.jsonl" if session["arm"] == "A" else "proposals.jsonl"
        path = directory / name
        if path.is_symlink():
            raise ValueError("candidate log must not be a symlink")
        stage = "candidate_integrity"
        if _candidate_binding(path) != candidate_binding:
            raise ValueError("candidate bytes changed after capture or seal")
        raw_candidates = _read(path) if path.exists() else b""
        if {"exists": path.exists(), "sha256": hashlib.sha256(raw_candidates).hexdigest(), "bytes": len(raw_candidates)} != candidate_binding:
            raise ValueError("candidate bytes changed while reading projection inputs")
        stage = "candidate_resolution"
        if raw_candidates and not raw_candidates.endswith(b"\n"):
            raise ValueError("candidate log has an incomplete final entry")
        candidates = [_json(line) for line in raw_candidates.splitlines()]
        resolved, resolutions = resolve_hashes(document["bindings"], candidates)
        _write(directory / "bindings-resolved.json", _encoded(resolved))
        _write(directory / "binding-resolution.json", _encoded(resolutions))
        report["candidate_log"] = {"file": name, "sha256": hashlib.sha256(raw_candidates).hexdigest(),
                                   "bytes": len(raw_candidates)}
        report["resolved_bindings"] = _binding(directory / "bindings-resolved.json")
        report["hash_resolution"] = _binding(directory / "binding-resolution.json")
        stage = "projection"
        if session["arm"] == "C" and (not isinstance(verification, dict) or verification.get("passed") is not True):
            report["reason"] = "certificate_replay_failed"
        else:
            if session["arm"] == "C":
                stage = "certificate_binding"
                _certified_candidates(candidates, verified_bundle, verification)
            stage = "projection"
            source = open_source(session["facts"]["path"])
            try:
                projector = project_a if session["arm"] == "A" else project_c
                projection = projector(public, candidates, resolved, source)
            finally:
                _close_source(source)
            stage = "candidate_integrity"
            if _candidate_binding(path) != candidate_binding:
                raise ValueError("candidate bytes changed during projection")
            _write(directory / "projection.json", _encoded(projection))
            _write(directory / "projected-answers.json", _encoded(projection["submission"]))
            if _candidate_binding(path) != candidate_binding:
                raise ValueError("candidate bytes changed before publishing projection")
            report.update(status="available", output=_binding(directory / "projection.json"),
                          submission=_binding(directory / "projected-answers.json"))
    except (ValueError, TypeError, KeyError, OSError, RecursionError) as error:
        report.update(reason="invalid_or_unavailable_" + stage, failure_stage=stage, error_type=type(error).__name__, detail=str(error))
    _write(directory / "projection-status.json", _encoded(report))
    return dict(report, status_artifact=_binding(directory / "projection-status.json"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a new public session")
    init.add_argument("--arm", choices=("A", "C"), required=True)
    init.add_argument("--protocol", choices=PROTOCOLS, default="literal-v1")
    for option in ("facts", "case-profile", "questions", "out"):
        init.add_argument("--" + option, required=True)
    session = commands.add_parser("session", help="persistent newline-JSON stdio bridge")
    session.add_argument("--run", required=True)
    tool = commands.add_parser("tool", help="one tool call (reloads the facts)")
    tool.add_argument("--run", required=True)
    choices = tool.add_subparsers(dest="tool", required=True)
    choices.add_parser("forms")
    choices.add_parser("plan")
    update = choices.add_parser("update_question")
    update.add_argument("--question-id", required=True)
    for name in ("searched", "unresolved", "next-actions"):
        update.add_argument("--" + name, action="append")
    update.add_argument("--status")
    inventory = choices.add_parser("inventory_page")
    inventory.add_argument("--question-id", required=True)
    inventory.add_argument("--kinds", action="append")
    inventory.add_argument("--exhibits", action="append")
    inventory.add_argument("--page-size", type=int, default=100)
    inventory.add_argument("--cursor")
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
                                  questions=args.questions, out=args.out, protocol=args.protocol)
        elif args.command == "session":
            return serve_session(args.run)
        elif args.command == "finalize":
            result = finalize_session(args.run, summary=args.summary, status=args.status,
                                      elapsed_seconds=args.elapsed_seconds)
        else:
            arguments = {}
            if args.tool == "update_question":
                arguments = {"question_id": args.question_id}
                for name in ("searched", "unresolved", "next_actions", "status"):
                    if getattr(args, name) is not None:
                        arguments[name] = getattr(args, name)
            elif args.tool == "inventory_page":
                arguments = {"question_id": args.question_id, "page_size": args.page_size}
                for name in ("kinds", "exhibits", "cursor"):
                    if getattr(args, name) is not None:
                        arguments[name] = getattr(args, name)
            elif args.tool == "sql":
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
