"""Offline N4 probes. All writes use temporary directories; no model is invoked.

Run from the repository root with its Python environment:
    python -m eval.review_notes.n4_release_smoke

Print observations rather than treating known defects as passing assertions.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable
REAL_POPEN = subprocess.Popen


def command(*args):
    result = subprocess.run([PYTHON, *args], cwd=ROOT, capture_output=True,
                            text=True, timeout=30)
    return {"exit_code": result.returncode, "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()}


def write(path, value):
    path.write_text(json.dumps(value) + "\n")
    return path


def fixture(directory):
    reference = write(directory / "reference.json", {
        "schema_version": 2, "case_id": "n4-smoke",
        "questions": [{"id": "Q1", "prompt": "What is recorded?", "expected": True}]})
    answers = write(directory / "answers.json", {
        "schema_version": 2, "case_id": "n4-smoke",
        "answers": [{"question_id": "Q1", "status": "answered", "answer": True}]})
    facts = write(directory / "facts.json", {
        "_meta": {"case": "N4 synthetic case", "case_id": "n4-smoke", "time_zone": "UTC"},
        "facts": [], "strings": {}})
    return reference, answers, facts


def scorer_preservation():
    observations = {}
    for target in ("existing_result", "reference", "answers"):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name).resolve()
            reference, answers, _ = fixture(directory)
            output = {"reference": reference, "answers": answers}.get(target, directory / "results.json")
            if target == "existing_result":
                output.write_text("PRESERVE THIS PRIOR RESULT\n")
            before = output.read_bytes()
            result = command("-m", "eval.benchmark", "--reference", str(reference),
                             "--answers", str(answers), "--out", str(output))
            observations[target] = {"exit_code": result["exit_code"],
                                    "original_bytes_preserved": output.read_bytes() == before,
                                    "stderr": result["stderr"]}
    return observations


def backend_outcomes():
    from agent import run

    observations = {}
    for label, event, process_exit in (
        ("success_control", {"type": "result", "subtype": "success", "result": "done"}, 0),
        ("process_error_control", None, 3),
        ("error_result", {"type": "result", "subtype": "error_during_execution",
                          "is_error": True, "errors": ["synthetic provider error"]}, 1),
        ("success_event_nonzero_exit", {"type": "result", "subtype": "success", "result": "done"}, 3),
    ):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name).resolve()
            _, _, facts = fixture(directory)
            program = ("print(" + repr(json.dumps(event)) + ")\n" if event else "")
            program += f"raise SystemExit({process_exit})\n"

            def fake_cli(_command, **kwargs):
                # No Claude binary, provider, network or actual evidence tools.
                return REAL_POPEN([PYTHON, "-c", program], **kwargs)

            with patch.object(run, "ROOT", directory), \
                 patch("agent.run.subprocess.Popen", side_effect=fake_cli), \
                 contextlib.redirect_stdout(io.StringIO()):
                code = run.main(["--name", "probe", "--facts", str(facts), "--no-score"])
            saved = json.loads((directory / "runs/probe/run.json").read_text())
            observations[label] = {"cli_exit_code": code, "backend_exit_code": saved["case"]["exit_code"],
                                   "ended": saved["case"]["ended"]}

    for label, backend, function, error in (
        ("missing_cli", "claude-code", "run_claude_code", FileNotFoundError("synthetic missing executable")),
        ("api_error", "deepagents", "run_deepagents", RuntimeError("synthetic provider failure")),
    ):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name).resolve()
            _, _, facts = fixture(directory)
            with patch.object(run, "ROOT", directory), patch.object(run, function, side_effect=error), \
                 contextlib.redirect_stdout(io.StringIO()):
                try:
                    code = run.main(["--name", "probe", "--backend", backend, "--facts", str(facts), "--no-score"])
                    output = directory / "runs/probe"
                    saved = json.loads((output / "run.json").read_text())
                    observations[label] = {"cli_exit_code": code, "ended": saved["case"]["ended"],
                        "error_type": saved["case"].get("error_type"),
                        "remaining_artifacts": sorted(p.name for p in output.iterdir())}
                except Exception as exc:
                    observations[label] = {"uncaught_exception": type(exc).__name__,
                        "remaining_artifacts": sorted(p.name for p in (directory / "runs/probe").iterdir())}
    return observations


def preserved_outputs():
    with tempfile.TemporaryDirectory() as name:
        directory = Path(name).resolve()
        _, answers, facts = fixture(directory)
        public = write(directory / "questions.json", {
            "schema_version": 2, "case_id": "n4-smoke",
            "questions": [{"id": "Q1", "prompt": "What is recorded?", "answer_schema": {}}]})
        report = directory / "report.md"
        report.write_text("```json\n" + answers.read_text() + "```\n")
        sentinel = directory / "keep.json"
        sentinel.write_text("KEEP\n")
        output = {}
        for module, args in (
            ("eval.submission", ["--report", str(report), "--questions", str(public)]),
            ("verifier.verify", ["--run", str(ROOT / "runs/current/run.json"), "--facts", str(facts)]),
            ("eval.baseline", ["--facts", str(facts), "--certs", str(directory / "certs"),
                               "--run", str(directory / "run.json"), "--no-score"]),
            ("eval.pipeline", ["--run", str(ROOT / "runs/current/run.json"), "--facts", str(facts),
                               "--questions", str(public), "--reference", str(directory / "reference.json"),
                               "--adapter", "nist"]),
        ):
            result = command("-m", module, *args, "--out", str(sentinel))
            output[module] = {"exit_code": result["exit_code"], "preserved": sentinel.read_text() == "KEEP\n",
                              "traceback": "Traceback (most recent call last)" in result["stderr"]}
        return output


def public_packages():
    directory = ROOT / "comparison/mulder"
    manifest = json.loads((directory / "manifest.json").read_text())
    checks = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
              for name, digest in manifest["inputs"].items()}
    original = ROOT / "comparison/mulder-original20"
    sources = json.loads((original / "SOURCES.json").read_text())
    archived = {entry["path"]: hashlib.sha256((original / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
                and (original / entry["path"]).stat().st_size == entry["bytes"] for entry in sources["files"]}
    return {"public_input_hashes": checks, "original20_source_hashes_and_sizes": archived,
            "shared_questions_equal": json.loads((directory / "questions.json").read_text()) ==
                                      json.loads((ROOT / "eval/benchmark_nist_questions.json").read_text()),
            "evidence_segments_declared": len(manifest["evidence"]),
            "evidence_bytes_rehashed": False, "status": manifest["status"]}


def local_links():
    missing = []
    documents = ["README.md", "WORKSTREAMS.md", "TASKS.md", "eval/EVALUATION.md",
                 "eval/BENCHMARK_REFERENCE.md", "comparison/mulder/README.md",
                 "comparison/mulder-original20/README.md"]
    checked = 0
    for document in documents:
        source = ROOT / document
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", source.read_text()):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            checked += 1
            target = unquote(target.split("#", 1)[0])
            if not (source.parent / target).exists():
                missing.append({"document": document, "target": target})
    return {"documents": documents, "local_targets_checked": checked, "missing": missing,
            "scope": "local Markdown link targets; excludes external links, fragments and archived upstream docs"}


def main():
    modules = ("agent.run", "agent.cli", "eval.baseline", "eval.pipeline", "eval.benchmark",
               "eval.submission", "eval.package", "eval.key_audit", "eval.gate", "verifier.verify")
    observations = {
        "python": sys.version.split()[0],
        "help_exit_codes": {module: command("-m", module, "--help")["exit_code"] for module in modules},
        "scorer_output_preservation": scorer_preservation(),
        "backend_outcomes": backend_outcomes(),
        "other_output_preservation": preserved_outputs(),
        "packages": public_packages(),
        "local_links": local_links(),
    }
    print(json.dumps(observations, indent=2))


if __name__ == "__main__":
    main()
