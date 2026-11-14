"""Run the AI investigator on the case, then score it with the same scorer as the miner.

    python3 -m agent.run --name agent1                       # on this machine's Claude Code login
    uv run --extra agent python -m agent.run --backend deepagents --name agent2   # API key

Writes runs/<name>/: every proposal and certificate, run.json for the front end,
results.json from the scorer, and summary.md (the investigator's own closing words).

Backends
  claude-code   Headless Claude Code with only our four tools (no shell, no files). No API key.
  deepagents    LangChain deepagents on the Anthropic API. Needs ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from agent.brief import BRIEF
from checker import export
from eval import score as scorer

ROOT = Path(__file__).resolve().parent.parent
TOOL_NAMES = ["mcp__cop__forms", "mcp__cop__sql", "mcp__cop__fact", "mcp__cop__check"]


def run_claude_code(model: str, run_dir: Path, env: dict, timeout_s: int) -> dict:
    """The investigator as a headless Claude Code session.

    It gets our four tools through agent/mcp_server.py and nothing else: every built-in
    tool is switched off (--tools ""), so it has no shell and cannot read any file. It
    runs in an empty directory so no project file is in reach either."""
    servers = {"mcpServers": {"cop": {
        "command": sys.executable, "args": ["-m", "agent.mcp_server"],
        "env": {"PYTHONPATH": str(ROOT), "COP_FACTS": env["COP_FACTS"],
                "COP_RUN_DIR": env["COP_RUN_DIR"], "COP_PROPOSER": env["COP_PROPOSER"],
                "PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}}}}
    cmd = ["claude", "-p", BRIEF, "--tools", "", "--mcp-config", json.dumps(servers),
           "--strict-mcp-config", "--allowedTools", ",".join(TOOL_NAMES),
           "--permission-prompts", "none", "--model", model,
           "--output-format", "stream-json", "--verbose"]
    started, final, calls = time.time(), {}, 0
    with tempfile.TemporaryDirectory() as empty, open(run_dir / "transcript.jsonl", "w") as log:
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


def run_deepagents(model: str, run_dir: Path, facts: str) -> dict:
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

    agent = create_deep_agent(model=f"anthropic:{model}", tools=[forms, sql, fact, check])
    started = time.time()
    state = agent.invoke({"messages": [{"role": "user", "content": BRIEF}]},
                         config={"recursion_limit": 500})
    last = state["messages"][-1].content
    text = last if isinstance(last, str) else "".join(
        b.get("text", "") for b in last if isinstance(b, dict))
    return {"summary": text, "turns": len(state["messages"]), "tool_calls": None,
            "seconds": round(time.time() - started), "ended": "success"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the AI investigator and score it.")
    ap.add_argument("--name", default="agent")
    ap.add_argument("--backend", choices=("claude-code", "deepagents"), default="claude-code")
    ap.add_argument("--model", help="default: opus (claude-code) or claude-opus-5-5 (deepagents)")
    ap.add_argument("--facts", default="evidence/case_facts.json")
    ap.add_argument("--minutes", type=int, default=45, help="time limit for the run")
    args = ap.parse_args(argv)

    model = args.model or ("opus" if args.backend == "claude-code" else "claude-opus-5-5")
    run_dir = ROOT / "runs" / args.name
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    print(f"investigator: {args.backend} / {model} -> {run_dir.relative_to(ROOT)}")
    if args.backend == "claude-code":
        env = dict(COP_FACTS=str((ROOT / args.facts).resolve()), COP_RUN_DIR=str(run_dir),
                   COP_PROPOSER=f"agent:claude-code:{model}")
        meta = run_claude_code(model, run_dir, env, args.minutes * 60)
    else:
        meta = run_deepagents(model, run_dir, args.facts)

    (run_dir / "summary.md").write_text(meta.pop("summary") + "\n")
    data = export.bundle(run_dir, "NIST CFReDS Data Leakage Case")
    data["case"].update(backend=args.backend, model=model, **meta)
    (run_dir / "run.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"\n{meta['tool_calls']} tool calls, {meta['seconds']} s, ended: {meta['ended']}")
    print(f"proposals {data['stats']['proposals']}, certified {data['stats']['verified']}, "
          f"refused {data['stats']['rejected']}\n")
    os.chdir(ROOT)      # relative paths in results.json, not this machine's directories
    rel = run_dir.relative_to(ROOT)
    return scorer.main(["--facts", args.facts, "--run", str(rel / "run.json"),
                        "--out", str(rel / "results.json")])


if __name__ == "__main__":
    sys.exit(main())
