"""Run the AI investigator with public case context and optional deterministic scoring.

    python3 -m agent.run --name agent1                       # on this machine's Claude Code login
    uv run --extra agent python -m agent.run --backend deepagents --name agent2   # API key
    python3 -m agent.run --facts evidence/other.json --case-profile public-case.json --name other

Writes runs/<name>/: every proposal and certificate, run.json for the front end,
optional results.json from the scorer, and summary.md (the investigator's own closing words).
Existing run directories are never overwritten. Evaluation needs explicit --reference, --questions and --adapter/--answers.
Scoring references are never included in the investigator prompt.

Backends
  claude-code   Headless Claude Code with only our evidence and workflow tools (no shell, no files). No API key.
  deepagents    LangChain deepagents on the Anthropic API. Needs ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from agent.brief import investigator_brief
from agent.case import read_question_profile, select_case, with_questions
from agent import run_manifest
from checker import export, report
from checker.facts import open_source
from eval import gate, pipeline

ROOT = Path(__file__).resolve().parent.parent
SUMMARY_LIMIT = 1500


def case_summary(text) -> str:
    """The paragraph that starts with "SUMMARY:" in the investigator's closing reply, or ''."""
    if not isinstance(text, str):
        return ""
    found = re.search(r"^[\s*#_]*SUMMARY[*_]*:[*_]*[ \t]*(.+?)(?:\n[ \t]*\n|\Z)", text, re.S | re.M)
    return found.group(1).strip()[:SUMMARY_LIMIT] if found else ""


INVESTIGATOR_TOOLS = ("forms", "sql", "fact", "check", "conclude", "plan", "update_question", "evidence_needs", "collect", "review", "answer", "inventory_page")


def run_claude_code(model: str, run_dir: Path, env: dict, timeout_s: int, prompt: str,
                    tools=INVESTIGATOR_TOOLS, transcript: str = "transcript.jsonl") -> dict:
    """The investigator as a headless Claude Code session.

    It gets restricted tools through agent/mcp_server.py and nothing else: every built-in
    tool is switched off (--tools ""), so it has no shell and cannot read any file. It
    runs in an empty directory so no project file is in reach either."""
    servers = {"mcpServers": {"cop": {
        "command": sys.executable, "args": ["-m", "agent.mcp_server"],
        "env": {"PYTHONPATH": str(ROOT), "COP_FACTS": env["COP_FACTS"],
                "COP_RUN_DIR": env["COP_RUN_DIR"], "COP_PROPOSER": env["COP_PROPOSER"],
                "COP_TOOLS": ",".join(tools),
                "PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}}}}
    cmd = ["claude", "-p", prompt, "--tools", "", "--mcp-config", json.dumps(servers),
           "--strict-mcp-config", "--allowedTools", ",".join(f"mcp__cop__{t}" for t in tools),
           "--permission-prompts", "none", "--model", model,
           "--output-format", "stream-json", "--verbose"]
    started, final, calls = time.time(), {}, 0
    with tempfile.TemporaryDirectory() as empty, open(run_dir / transcript, "w") as log:
        proc = subprocess.Popen(cmd, cwd=empty, stdout=subprocess.PIPE, text=True,
                                start_new_session=(os.name == "posix"))
        expired = threading.Event()

        def stop():
            try:
                if os.name == "posix":
                    os.killpg(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
            except ProcessLookupError:
                pass

        def expire():
            expired.set()
            stop()

        # A silent subprocess must not evade the investigation time limit.
        watchdog = threading.Timer(timeout_s, expire)
        watchdog.daemon = True
        watchdog.start()
        try:
            for line in proc.stdout:
                log.write(line)
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "assistant":
                    for block in event.get("message", {}).get("content", []):
                        if block.get("type") == "tool_use":
                            calls += 1
                            what = json.dumps(block.get("input", {}), ensure_ascii=False)
                            print(f"  [{calls:>3}] {block.get('name', '').split('__')[-1]} "
                                  f"{what[:140]}", flush=True)
                elif event.get("type") == "result":
                    final = event
        except BaseException:
            stop()
            raise
        finally:
            try:
                proc.wait()
            finally:
                watchdog.cancel()
                proc.stdout.close()
    if expired.is_set():
        print("  stopped: time limit reached")
    subtype = final.get("subtype")
    result_error = bool(final.get("is_error")) or (
        isinstance(subtype, str) and subtype.startswith("error"))
    if expired.is_set():
        ended = "time_limit"
    elif proc.returncode:
        ended = "process_error"
    elif result_error:
        ended = subtype if isinstance(subtype, str) and subtype.startswith("error") else "result_error"
    else:
        ended = subtype or "no result event"
    summary = final.get("result")
    return {"summary": summary if isinstance(summary, str) else "", "turns": final.get("num_turns"),
            "tool_calls": calls, "seconds": round(time.time() - started),
            "ended": ended, "result_subtype": subtype, "is_error": result_error,
            "exit_code": proc.returncode}


def _create_api_agent(model, tools):
    from deepagents import create_deep_agent
    from deepagents.middleware import FilesystemMiddleware
    from agent.api import EvidenceToolsOnly

    return create_deep_agent(model=model, tools=tools,
        middleware=[
            # A restricted investigator cannot retrieve an evicted result through
            # read_file. Keep supplied evidence and public prompts in messages.
            FilesystemMiddleware(tool_token_limit_before_evict=None,
                                 human_message_token_limit_before_evict=None),
            EvidenceToolsOnly(INVESTIGATOR_TOOLS),
        ])


def run_deepagents(model: str, run_dir: Path, facts: str, prompt: str,
                   timeout_s: int = 45 * 60) -> dict:
    """API investigator, covered by offline graph tests; live access needs credentials."""
    from langchain_core.tools import tool

    from agent.tools import Workbench

    bench = Workbench(facts, run_dir, f"agent:deepagents:{model}")
    tool_lock = threading.Lock()
    stop_work = threading.Event()
    budget_expired = threading.Event()

    class ToolBudgetExpired(Exception):
        """Stop queued evidence work without confusing a provider timeout."""

    def call_tool(function, *args, **kwargs):
        # Cancelling an asyncio task does not stop its worker thread. Check after
        # acquiring this lock so queued calls cannot begin after cancellation.
        with tool_lock:
            if stop_work.is_set():
                raise ToolBudgetExpired()
            if time.monotonic() >= deadline:
                budget_expired.set()
                stop_work.set()
                raise ToolBudgetExpired()
            return function(*args, **kwargs)

    def call_validated(function, *args, **kwargs):
        # A malformed binding or expired cursor is recoverable model input, not
        # a reason to discard the rest of the investigation. Audited methods
        # record the failed call before this response is returned to the model.
        try:
            return call_tool(function, *args, **kwargs)
        except ValueError as error:
            return {'status': 'not_applied', 'error': str(error)}

    @tool
    def forms() -> str:
        """The statement forms you may propose, with their arguments."""
        return json.dumps(call_tool(bench.forms), ensure_ascii=False)

    @tool
    def sql(query: str) -> str:
        """Run one read-only SELECT over the facts table."""
        return json.dumps(call_tool(bench.sql, query), ensure_ascii=False)

    @tool
    def fact(id: int) -> str:
        """One record in full, with where it came from."""
        return json.dumps(call_tool(bench.fact, id), ensure_ascii=False)

    @tool
    def check(question: str, claims: list, revises: str | None = None) -> str:
        """Propose claims for checking; optionally name the prior proposal being revised."""
        # Each proof is one synchronous operation; stop between claims instead
        # of finishing an unbounded batch after the investigation has expired.
        revision = {"revises": revises} if revises is not None else {}
        return json.dumps([call_tool(bench.check, question, c, **revision) for c in claims], ensure_ascii=False)

    @tool
    def conclude(text: str, finding_ids: list[str]) -> str:
        """Record an uncertified inference citing certified findings from this run."""
        return json.dumps(call_tool(bench.conclude, text, finding_ids), ensure_ascii=False)

    @tool
    def plan() -> str:
        """Read saved question progress and unresolved work; status is agent-reported."""
        return json.dumps(call_tool(bench.plan), ensure_ascii=False)

    @tool
    def update_question(question_id: str, finding_ids: list[str] | None = None,
                        searched: list[str] | None = None, unresolved: list[str] | None = None,
                        next_actions: list[str] | None = None, status: str | None = None) -> str:
        """Save work notes and checked finding links for a public question."""
        return json.dumps(call_tool(bench.update_question, question_id, finding_ids,
            searched, unresolved, next_actions, status), ensure_ascii=False)

    @tool
    def evidence_needs(proof_gap: dict | None = None) -> str:
        """List approved readers and diagnostic evidence needs."""
        return json.dumps(call_tool(bench.evidence_needs, proof_gap), ensure_ascii=False)

    @tool
    def collect(reader: str, exhibit: str) -> str:
        """Extract an approved reader/exhibit into a NEW snapshot for continuation."""
        return json.dumps(call_tool(bench.collect, reader, exhibit), ensure_ascii=False)

    @tool
    def review() -> str:
        """Inspect conservative evidence conflict diagnostics; these are not findings."""
        return json.dumps(call_tool(bench.review), ensure_ascii=False)

    @tool
    def answer(question_id: str, bindings: list[dict] | None = None, replace: bool = False, preview: bool = False,
               section: str | None = None, offset: int | None = None, page_size: int | None = None,
               state_token: str | None = None) -> str:
        """Bind fields or preview bounded diagnostics. Omit bindings for read-only section pages; continue with next_offset and state_token."""
        return json.dumps(call_validated(bench.answer, question_id, bindings, replace=replace, preview=preview,
                                        section=section, offset=offset, page_size=page_size,
                                        state_token=state_token), ensure_ascii=False)

    @tool
    def inventory_page(question_id: str, kinds: list[str] | None = None,
                       exhibits: list[str] | None = None, page_size: int = 100,
                       cursor: str | None = None) -> str:
        """Read an ID-ordered evidence page; continue with its cursor and unchanged filters. Saves progress."""
        return json.dumps(call_validated(bench.inventory_page, question_id, kinds=kinds,
                                   exhibits=exhibits, page_size=page_size, cursor=cursor), ensure_ascii=False)

    agent = _create_api_agent(model=f"anthropic:{model}",
                              tools=[forms, sql, fact, check, conclude, plan, update_question,
                                     evidence_needs, collect, review, answer, inventory_page])
    started = time.monotonic()
    deadline = started + timeout_s
    async def invoke():
        task = asyncio.create_task(agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"recursion_limit": 500}))
        try:
            return await asyncio.wait_for(task, timeout=max(0.0, deadline - time.monotonic()))
        except ToolBudgetExpired:
            return None
        except asyncio.TimeoutError:
            if not task.cancelled():
                raise  # A provider/tool timeout is a failed run, not our budget.
            budget_expired.set()
            return None
        finally:
            # Also stop queued workers when another tool/provider fails. One
            # already active synchronous proof must finish before asyncio exits.
            stop_work.set()

    state = asyncio.run(invoke())
    if state is None or budget_expired.is_set():
        return {"summary": "Investigation time limit reached. Saved certificates remain available.",
                "turns": None, "tool_calls": None, "seconds": round(time.monotonic() - started),
                "ended": "time_limit"}
    last = state["messages"][-1].content
    text = last if isinstance(last, str) else "".join(
        b.get("text", "") for b in last if isinstance(b, dict))
    return {"summary": text, "turns": len(state["messages"]), "tool_calls": None,
            "seconds": round(time.monotonic() - started), "ended": "success"}


def prepare_run_dir(name: str, root: Path = ROOT) -> Path:
    """Create a new directory under runs; reject aliases, traversal and old runs."""
    parts = name.split("/")
    if not parts or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", p) for p in parts):
        raise ValueError("--name must be a relative run name, such as dev/run-2; "
                         "absolute paths, empty components, '.' and '..' are not allowed")
    base = root.resolve() / "runs"
    current = base
    for part in [None] + parts:
        if part is not None:
            current = current / part
        if current.is_symlink():
            raise ValueError(f"run paths cannot traverse symlinks: {current}")
    if current.exists():
        raise ValueError(f"run already exists; choose a new --name: {current}")
    # exist_ok=False also catches a second process claiming this name during setup.
    current.mkdir(parents=True, exist_ok=False)
    return current


def _input_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_file():
        raise ValueError(f"input file does not exist: {path}")
    return path


def _expected_backend_error(error: Exception) -> bool:
    """Recognize setup/runtime and optional SDK failures without requiring the SDK.

    A provider used by the backend is already imported when its exception escapes.
    Keep unexpected programming errors visible after saving the failed run.
    """
    if isinstance(error, (OSError, ImportError, RuntimeError)):
        return True
    for module_name, base_name in (("anthropic", "AnthropicError"), ("httpx", "HTTPError")):
        base = getattr(sys.modules.get(module_name), base_name, None)
        if isinstance(base, type) and isinstance(error, base):
            return True
    return False


def _execution_failed(meta: dict) -> bool:
    # Reaching our own budget remains an ordinary partial run. A provider error
    # observed before that deadline still fails, even if the watchdog later fires.
    if meta.get("is_error"):
        return True
    if meta.get("ended") == "time_limit":
        return False
    return meta.get("ended") != "success" or meta.get("exit_code") not in (None, 0)


def _main(argv=None, *, resources) -> int:
    ap = argparse.ArgumentParser(description="Run the investigator; optionally evaluate neutral structured answers.")
    ap.add_argument("--name", default="dev/agent")
    ap.add_argument("--backend", choices=("claude-code", "deepagents"), default="claude-code")
    ap.add_argument("--model", help="default: opus (claude-code) or claude-opus-5-5 (deepagents)")
    ap.add_argument("--facts", help="fact snapshot; continuation defaults to the bound previous input")
    ap.add_argument("--minutes", type=int, default=45)
    ap.add_argument("--case-profile", help="public case context; no expected answers")
    ap.add_argument("--questions", help="public schema-v2 question/answer-shape profile")
    ap.add_argument("--reference", help="explicit private schema-v2 reference, used only after investigation")
    answer = ap.add_mutually_exclusive_group()
    answer.add_argument("--adapter", choices=("nist", "claims"), help="claims: explicit field bindings for any case; nist: legacy case adapter")
    answer.add_argument("--answers", help="external structured answers for another case or system")
    ap.add_argument("--labeled-claims", help="explicit independent false-claim gate fixture")
    ap.add_argument("--resume-from", help="previous run directory; continue in a new run")
    ap.add_argument("--intake-config", help="trusted image intake configuration for approved extraction")
    ap.add_argument("--no-score", action="store_true", help="record evaluation as not measured")
    args = ap.parse_args(argv)
    model = args.model or ("opus" if args.backend == "claude-code" else "claude-opus-5-5")
    try:
        if args.minutes <= 0:
            raise ValueError("--minutes must be positive")
        from agent import continuation
        previous = continuation.parent(_input_path(args.resume_from) if Path(args.resume_from or "").is_file()
                                       else ROOT / args.resume_from) if args.resume_from else None
        facts_path = _input_path(args.facts) if args.facts else (continuation.default_facts(previous) if previous else _input_path("evidence/case_facts.json"))
        profile_path = _input_path(args.case_profile) if args.case_profile else (previous["directory"] / "case-profile.json" if previous else None)
        questions_path = _input_path(args.questions) if args.questions else (previous["directory"] / "questions.json" if previous and previous["questions"] else None)
        profile, profile_source = select_case(facts_path, profile_path,
                                               default_facts=ROOT / "evidence" / "case_facts.json")
        if questions_path:
            profile = with_questions(profile, read_question_profile(questions_path))
            profile_source += "+questions"
        reference = _input_path(args.reference) if args.reference and not args.no_score else None
        answers = _input_path(args.answers) if args.answers and not args.no_score else None
        plan = pipeline.prepare(reference, questions_path, args.adapter, answers,
                                profile.case_id, args.no_score)
        labeled = _input_path(args.labeled_claims) if args.labeled_claims else None
        if labeled:
            gate.load_fixture(labeled, profile.case_id, profile.time_zone)
        prompt = investigator_brief(profile)
        run_dir = prepare_run_dir(args.name, ROOT)
        resources.enter_context(continuation.active_run(run_dir))
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    public = read_question_profile(questions_path) if questions_path else None
    if previous:
        receipt = continuation.prepare(previous, run_dir, facts_path)
        prompt += continuation.prompt_context(receipt)
    if args.intake_config:
        from agent.evidence_requests import bind_config
        bind_config(run_dir, _input_path(args.intake_config), facts_path)
    (run_dir / "case-profile.json").write_text(json.dumps(profile.public_dict(), indent=2) + "\n")
    (run_dir / "prompt.md").write_text(prompt)
    if questions_path is not None:
        (run_dir / "questions.json").write_bytes(questions_path.read_bytes())
    try:
        manifest = run_manifest.create(run_dir, facts=facts_path, backend=args.backend,
            model=model, minutes=args.minutes, root=ROOT,
            questions=run_dir / "questions.json" if questions_path else None)
    except (ValueError, OSError) as error:
        ap.error(str(error))
    if previous:
        continuation.restore(previous, run_dir, facts_path, profile, public)
    else:
        from agent.investigation import Investigation
        Investigation(run_dir).initialize(profile, public)
    print(f"investigator: {args.backend} / {model} -> {run_dir.relative_to(ROOT)}")
    started = time.monotonic()
    backend_error = None
    try:
        if args.backend == "claude-code":
            env = dict(COP_FACTS=str(facts_path), COP_RUN_DIR=str(run_dir),
                       COP_PROPOSER=f"agent:claude-code:{model}")
            meta = run_claude_code(model, run_dir, env, args.minutes * 60, prompt=prompt)
        else:
            meta = run_deepagents(model, run_dir, str(facts_path), prompt=prompt,
                                 timeout_s=args.minutes * 60)
    except Exception as error:
        # Only the backend invocation is caught: even an unexpected backend bug
        # must not erase the trial from our records. Re-raise such bugs below,
        # after finalization. Never serialize exception text or request payloads.
        backend_error = error
        meta = {"summary": "Investigation failed. Saved proposals and certificates remain available.",
                "turns": None, "tool_calls": None, "seconds": round(time.monotonic() - started),
                "ended": "backend_error", "is_error": True, "error_type": type(error).__name__}
        print(f"  stopped: backend failed ({meta['error_type']}); see run.json")
    closing = meta.pop("summary")
    (run_dir / "summary.md").write_text(closing + "\n")
    case_metadata = dict(backend=args.backend, model=model, case_id=profile.case_id,
                        time_zone=profile.time_zone, profile_source=profile_source,
                        scoring_requested=plan.measured,
                        run_manifest="run-manifest.json",
                        facts_sha256=manifest["inputs"]["facts"]["sha256"], **meta)
    if case_summary(closing):
        case_metadata["case_summary"] = case_summary(closing)
    # Always run a final conservative review, even if the model skipped its tool.
    from agent.tools import Workbench
    try:
        Workbench(facts_path, run_dir, proposer="final-review").review()
    except Exception as error:
        # Optional diagnostic review must not erase already checked findings.
        from agent.investigation import atomic_json
        case_metadata["review_error_type"] = type(error).__name__
        atomic_json(run_dir / "review.json", {"schema_version": 1, "status": "unavailable", "scope": {"records_examined": None},
            "diagnostics": [], "reason": "Final conflict review failed; no consistency conclusion is available.",
            "error_type": type(error).__name__})
    data = export.bundle(run_dir, profile.name, case_metadata=case_metadata)
    (run_dir / "run.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    (run_dir / "report.md").write_text(report.render(data))
    print(f"\n{meta['tool_calls']} tool calls, {meta['seconds']} s, ended: {meta['ended']}")
    print(f"proposals {data['stats']['proposals']}, certified {data['stats']['verified']}, "
          f"refused {data['stats']['rejected']}, conclusions {len(data['conclusions'])}\n")
    # Save the investigation before optional regression work can fail. Gate probes
    # remain separate from findings; a failed gate does not bypass verification.
    regression, gate_error = None, None
    if labeled:
        try:
            regression = gate.measure(labeled, open_source(facts_path), profile.case_id,
                                      profile.time_zone, run_dir / "gate-probes")
        except Exception as error:
            gate_error = error
            regression = {"measured": False, "reason": "Gate regression failed",
                          "error_type": type(error).__name__}
            data["case"]["gate_error_type"] = type(error).__name__
            (run_dir / "run.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            (run_dir / "report.md").write_text(report.render(data))
            print(f"  gate failed ({type(error).__name__}); see run.json")
    try:
        pipeline.evaluate(plan, data, run_dir / "answers.json", run_dir / "results.json",
                          regression, facts_path=facts_path,
                          verification_output=run_dir / "verification.json")
    except (ValueError, OSError) as error:
        ap.error(str(error))
    if (run_dir / "answers.json").is_file():
        # Count answer presence only after the explicit evaluation path produced
        # a submission. Preserve the already exported audit/certificate snapshot;
        # this summary never reads the reference or awards correctness credit.
        from agent.coverage import summarize_coverage
        submission = json.loads((run_dir / "answers.json").read_text())
        data["coverage"]["questions"] = summarize_coverage(data,
            public_questions=plan.questions, answers=submission)["questions"]
        (run_dir / "run.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        (run_dir / "report.md").write_text(report.render(data))
    if backend_error is not None and not _expected_backend_error(backend_error):
        raise backend_error
    if gate_error is not None and not isinstance(
            gate_error, (OSError, ValueError, RuntimeError, subprocess.SubprocessError)):
        raise gate_error
    failed_execution = _execution_failed(meta)
    return 1 if failed_execution or gate_error is not None or data["audit"]["status"] == "invalid" or (
        regression and not regression["all_as_expected"]) else 0


def main(argv=None) -> int:
    with ExitStack() as resources:
        return _main(argv, resources=resources)


if __name__ == "__main__":
    sys.exit(main())
