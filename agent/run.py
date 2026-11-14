"""Run the AI investigator with public case context and optional deterministic scoring.

    python3 -m agent.run --name agent1                       # on this machine's Claude Code login
    uv run --extra agent python -m agent.run --backend deepagents --name agent2   # API key
    python3 -m agent.run --facts evidence/other.json --case-profile public-case.json --name other

Writes runs/<name>/: every proposal and certificate, run.json for the front end,
optional results.json from the scorer, and summary.md (the investigator's own closing words).
Existing run directories are never overwritten. Evaluation needs explicit --reference, --questions and --adapter/--answers.
Scoring references are never included in the investigator prompt.

Backends
  claude-code   Headless Claude Code with only our five tools (no shell, no files). No API key.
  deepagents    LangChain deepagents on the Anthropic API. Needs ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from agent.brief import investigator_brief
from agent.case import read_question_profile, select_case, with_questions
from checker import export, report
from checker.facts import open_source
from eval import gate, pipeline

ROOT = Path(__file__).resolve().parent.parent
INVESTIGATOR_TOOLS = ("forms", "sql", "fact", "check", "conclude")


def run_claude_code(model: str, run_dir: Path, env: dict, timeout_s: int, prompt: str,
                    tools=INVESTIGATOR_TOOLS, transcript: str = "transcript.jsonl") -> dict:
    """The investigator as a headless Claude Code session.

    It gets our five tools through agent/mcp_server.py and nothing else: every built-in
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
        proc = subprocess.Popen(cmd, cwd=empty, stdout=subprocess.PIPE, text=True)
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
                if time.time() - started > timeout_s:
                    proc.kill()
                    print("  stopped: time limit reached")
                    break
        finally:
            proc.wait()
    return {"summary": final.get("result", ""), "turns": final.get("num_turns"),
            "tool_calls": calls, "seconds": round(time.time() - started),
            "ended": final.get("subtype", "no result event")}


def run_deepagents(model: str, run_dir: Path, facts: str, prompt: str) -> dict:
    """The investigator as a LangChain deep agent. Untested until an API key is present."""
    from deepagents import create_deep_agent
    from langchain_core.tools import tool

    from agent.tools import Workbench

    bench = Workbench(facts, run_dir, f"agent:deepagents:{model}")

    @tool
    def forms() -> str:
        """The statement forms you may propose, with their arguments."""
        return json.dumps(bench.forms(), ensure_ascii=False)

    @tool
    def sql(query: str) -> str:
        """Run one read-only SELECT over the facts table."""
        return json.dumps(bench.sql(query), ensure_ascii=False)

    @tool
    def fact(id: int) -> str:
        """One record in full, with where it came from."""
        return json.dumps(bench.fact(id), ensure_ascii=False)

    @tool
    def check(question: str, claims: list) -> str:
        """Propose claims (a list of claim objects). Each is certified or refused."""
        return json.dumps([bench.check(question, c) for c in claims], ensure_ascii=False)

    @tool
    def conclude(text: str, finding_ids: list[str]) -> str:
        """Record an uncertified inference citing certified findings from this run."""
        return json.dumps(bench.conclude(text, finding_ids), ensure_ascii=False)

    agent = create_deep_agent(model=f"anthropic:{model}",
                             tools=[forms, sql, fact, check, conclude])
    started = time.time()
    state = agent.invoke({"messages": [{"role": "user", "content": prompt}]},
                         config={"recursion_limit": 500})
    last = state["messages"][-1].content
    text = last if isinstance(last, str) else "".join(
        b.get("text", "") for b in last if isinstance(b, dict))
    return {"summary": text, "turns": len(state["messages"]), "tool_calls": None,
            "seconds": round(time.time() - started), "ended": "success"}


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the investigator; optionally evaluate neutral structured answers.")
    ap.add_argument("--name", default="dev/agent")
    ap.add_argument("--backend", choices=("claude-code", "deepagents"), default="claude-code")
    ap.add_argument("--model", help="default: opus (claude-code) or claude-opus-5-5 (deepagents)")
    ap.add_argument("--facts", default="evidence/case_facts.json")
    ap.add_argument("--minutes", type=int, default=45)
    ap.add_argument("--case-profile", help="public case context; no expected answers")
    ap.add_argument("--questions", help="public schema-v2 question/answer-shape profile")
    ap.add_argument("--reference", help="explicit private schema-v2 reference, used only after investigation")
    answer = ap.add_mutually_exclusive_group()
    answer.add_argument("--adapter", choices=("nist",), help="explicit case adapter over verified certificates")
    answer.add_argument("--answers", help="external structured answers for another case or system")
    ap.add_argument("--labeled-claims", help="explicit independent false-claim gate fixture")
    ap.add_argument("--no-score", action="store_true", help="record evaluation as not measured")
    args = ap.parse_args(argv)
    model = args.model or ("opus" if args.backend == "claude-code" else "claude-opus-5-5")
    try:
        if args.minutes <= 0:
            raise ValueError("--minutes must be positive")
        facts_path = _input_path(args.facts)
        profile_path = _input_path(args.case_profile) if args.case_profile else None
        questions_path = _input_path(args.questions) if args.questions else None
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
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    (run_dir / "case-profile.json").write_text(json.dumps(profile.public_dict(), indent=2) + "\n")
    (run_dir / "prompt.md").write_text(prompt)
    print(f"investigator: {args.backend} / {model} -> {run_dir.relative_to(ROOT)}")
    if args.backend == "claude-code":
        env = dict(COP_FACTS=str(facts_path), COP_RUN_DIR=str(run_dir),
                   COP_PROPOSER=f"agent:claude-code:{model}")
        meta = run_claude_code(model, run_dir, env, args.minutes * 60, prompt=prompt)
    else:
        meta = run_deepagents(model, run_dir, str(facts_path), prompt=prompt)
    (run_dir / "summary.md").write_text(meta.pop("summary") + "\n")
    # Regression probes are isolated from findings and never enter the investigator prompt.
    regression = gate.measure(labeled, open_source(facts_path), profile.case_id,
                              profile.time_zone, run_dir / "gate-probes") if labeled else None
    data = export.bundle(run_dir, profile.name)
    data["case"].update(backend=args.backend, model=model, case_id=profile.case_id,
                        time_zone=profile.time_zone, profile_source=profile_source,
                        scoring_requested=plan.measured, **meta)
    (run_dir / "run.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    (run_dir / "report.md").write_text(report.render(data))
    print(f"\n{meta['tool_calls']} tool calls, {meta['seconds']} s, ended: {meta['ended']}")
    print(f"proposals {data['stats']['proposals']}, certified {data['stats']['verified']}, "
          f"refused {data['stats']['rejected']}, conclusions {len(data['conclusions'])}\n")
    try:
        pipeline.evaluate(plan, data, run_dir / "answers.json", run_dir / "results.json",
                          regression, facts_path=facts_path,
                          verification_output=run_dir / "verification.json")
    except (ValueError, OSError) as error:
        ap.error(str(error))
    return 1 if regression and not regression["all_as_expected"] else 0


if __name__ == "__main__":
    sys.exit(main())
