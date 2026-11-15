"""Bind a future investigation to its actual public inputs and local software.

These are recorded measurements, not authentication or a proof of extraction quality.
No environment variables, private reference, or provider request payload is collected.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import subprocess


def file_binding(path):
    path = Path(path)
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"path": str(path), "bytes": size, "sha256": digest.hexdigest()}


def _git(root):
    if not (root / ".git").exists():
        return {"commit": None, "dirty": None}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                                capture_output=True, text=True, timeout=5)
        state = subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal"],
                               cwd=root, capture_output=True, text=True, timeout=5)
        value = commit.stdout.strip()
        return {"commit": value if commit.returncode == 0 and re.fullmatch(r"[0-9a-f]{40,64}", value) else None,
                "dirty": bool(state.stdout.strip()) if state.returncode == 0 else None}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def create(run_dir, *, facts, backend, model, minutes, root, questions=None, health=None):
    """Write a new manifest after the public prompt/profile have been materialized."""
    run_dir, root = Path(run_dir), Path(root)
    inputs = {"facts": file_binding(facts),
              "case_profile": file_binding(run_dir / "case-profile.json"),
              "prompt": file_binding(run_dir / "prompt.md")}
    for name, path in (("questions", questions), ("extraction_health", health)):
        if path is not None:
            inputs[name] = file_binding(path)
    for name in ("continuation.json", "intake-config.json"):
        path = run_dir / name
        if path.is_file():
            inputs[name.removesuffix(".json").replace("-", "_")] = file_binding(path)
    packages = {}
    for name in ("chain-of-proof", "deepagents", "langchain-anthropic", "duckdb", "dissect.target"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    toolchain = root / "lean" / "lean-toolchain"
    sources = {}
    # A commit alone is insufficient when a checkout has uncommitted changes.
    for directory in ("agent", "checker", "verifier", "lean/ChainOfProof"):
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and path.suffix in (".py", ".lean"):
                sources[str(path.relative_to(root))] = file_binding(path)["sha256"]
    value = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": inputs,
        "software": {"python": platform.python_version(), "git": _git(root),
                     "packages": packages, "source_sha256": sources,
                     "lean_toolchain": toolchain.read_text().strip() if toolchain.is_file() else None},
        "investigator": {"backend": backend, "requested_model": model,
                         "resolved_model": None, "resolved_model_status": "not_observed",
                         "requested_minutes": minutes},
        "scope": "Hashes bind the supplied files. They do not authenticate the original evidence, "
                 "prove parser correctness, or establish which immutable model revision a provider used.",
    }
    with (run_dir / "run-manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return value
