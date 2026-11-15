"""Recheck saved certificates with con-leche, a second proof checker.

    python -m verifier.conleche --run runs/current/run.json [--jobs 8] [--out NEW.json]

Lean 4.35 bundles con-leche, a proof checker written separately from Lean's own
kernel. Its help text states the theorem it carries: in its default mode, a file that
declares a theorem of type False is never accepted. Here each certificate is compiled,
its `verified` theorem is exported with the toolchain's `leanexport`, and con-leche
checks the export.

A certificate passes only if con-leche exits 0 and the export declares the
certificate's own theorem. con-leche also exits 0 on an export with no declarations,
so the exit code alone is not enough.

This is a second opinion on the proof. It adds nothing about whether the cited records
match the evidence (verifier.verify checks that) or whether the readers parsed the
disk images correctly.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
LEAN_DIR = ROOT / "lean"
CHECKER = "con-leche"
MODE = "--verified"
MODULE = "Certificate"
_NAMESPACE = re.compile(r"^namespace\s+(Cert\.[A-Za-z_][A-Za-z0-9_]*)\s*$", re.M)


class Unavailable(RuntimeError):
    """The installed Lean toolchain has no con-leche or no exporter."""


class Toolchain:
    """Paths of the Lean programs used here, resolved once from `lean/lean-toolchain`."""

    def __init__(self) -> None:
        if not shutil.which("lean") or not shutil.which("lake"):
            raise Unavailable("lean and lake are not on PATH")
        prefix = Path(_run(["lean", "--print-prefix"], cwd=LEAN_DIR).stdout.strip())
        self.lean = prefix / "bin" / "lean"
        self.exporter = prefix / "bin" / "leanexport"
        self.checker = prefix / "bin" / CHECKER
        for program in (self.lean, self.exporter, self.checker):
            if not program.is_file():
                raise Unavailable(f"{program.name} is not part of this Lean toolchain ({prefix.name})")
        self.lean_path = _run(["lake", "env", "printenv", "LEAN_PATH"], cwd=LEAN_DIR).stdout.strip()
        self.version = _run([str(self.lean), "--version"], cwd=LEAN_DIR).stdout.strip()


def _run(argv: List[str], cwd: Path, env: Optional[Dict[str, str]] = None,
         timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def theorem_name(lean_text: str) -> str:
    """The full name of a certificate's theorem, read from its one namespace."""
    found = _NAMESPACE.findall(lean_text)
    if len(found) != 1:
        raise ValueError("a certificate must open exactly one Cert.<id> namespace")
    return found[0] + ".verified"


def export(lean_text: str, workdir: Path, tools: Toolchain) -> Path:
    """Compile one certificate in `workdir` and export its theorem with everything it uses."""
    theorem = theorem_name(lean_text)
    source = workdir / (MODULE + ".lean")
    source.write_text(lean_text)
    env = dict(os.environ, LEAN_PATH=tools.lean_path + os.pathsep + str(workdir))
    built = _run([str(tools.lean), f"--root={workdir}", "-o", str(workdir / (MODULE + ".olean")),
                  str(source)], cwd=LEAN_DIR, env=env)
    if built.returncode != 0:
        raise ValueError("Lean did not accept the certificate: " + _last_line(built.stdout + built.stderr))
    exported = _run([str(tools.exporter), MODULE, "--", theorem], cwd=LEAN_DIR, env=env)
    if exported.returncode != 0:
        raise ValueError("the proof could not be exported: " + _last_line(exported.stderr))
    path = workdir / (MODULE + ".ndjson")
    path.write_text(exported.stdout)
    return path


def declared_theorems(export_path: Path) -> List[str]:
    """Full names of the theorems an export declares."""
    names: Dict[int, str] = {0: ""}
    theorems: List[int] = []
    with export_path.open() as stream:
        for line in stream:
            entry = json.loads(line)
            if "in" in entry:
                part = entry.get("str") or entry.get("num")
                piece = str(part["str"] if "str" in part else part["i"])
                before = names.get(part["pre"], "")
                names[entry["in"]] = f"{before}.{piece}" if before else piece
            elif "thm" in entry:
                theorems.append(entry["thm"]["name"])
    return [names.get(index, "") for index in theorems]


def check_export(export_path: Path, theorem: str, tools: Toolchain) -> dict:
    """Run con-leche on one export. Accepted means: exit 0 and the theorem is in the export."""
    done = _run([str(tools.checker), MODE, str(export_path)], cwd=export_path.parent)
    said = _last_line(done.stdout + done.stderr)
    if done.returncode != 0:
        return {"accepted": False, "detail": said}
    if theorem not in declared_theorems(export_path):
        return {"accepted": False, "detail": f"the export does not declare {theorem}"}
    return {"accepted": True, "detail": said}


def check(lean_text: str, tools: Toolchain, workdir: Path) -> dict:
    """Compile, export and recheck one certificate. Never raises for a bad certificate."""
    try:
        return check_export(export(lean_text, workdir, tools), theorem_name(lean_text), tools)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        return {"accepted": False, "detail": str(error)}


def check_run(run: dict, tools: Toolchain, jobs: int = 4) -> dict:
    """Recheck every certificate in a run bundle."""
    findings = [f for f in run.get("findings", []) if f.get("lean")]
    with tempfile.TemporaryDirectory(prefix="cop-conleche-") as scratch:
        def one(numbered):
            index, finding = numbered
            workdir = Path(scratch) / str(index)
            workdir.mkdir()
            result = check(finding["lean"], tools, workdir)
            shutil.rmtree(workdir, ignore_errors=True)
            return {"finding_id": finding.get("finding_id"), **result}
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
            results = list(pool.map(one, enumerate(findings)))
    return {
        "checker": CHECKER,
        "mode": MODE,
        "lean": tools.version,
        "certificates": len(results),
        "accepted": sum(r["accepted"] for r in results),
        "without_proof_text": len(run.get("findings", [])) - len(findings),
        "not_accepted": [r for r in results if not r["accepted"]],
    }


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:400] if lines else "(no output)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="one bundled run containing certificates")
    ap.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--out", help="new JSON result file; an existing file is not overwritten")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else None
    if out and (out.exists() or out.is_symlink()):
        ap.error(f"refusing to overwrite existing output: {out}; choose a new path")
    try:
        tools = Toolchain()
    except Unavailable as error:
        print(f"con-leche is not available: {error}", file=sys.stderr)
        return 2
    result = check_run(json.loads(Path(args.run).read_text()), tools, args.jobs)
    if out:
        with out.open("x") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    for miss in result["not_accepted"]:
        print(f"NOT ACCEPTED {miss['finding_id']}: {miss['detail']}")
    print(f"{result['accepted']}/{result['certificates']} certificates accepted by "
          f"{CHECKER} ({MODE}); {len(result['not_accepted'])} not accepted")
    return 0 if result["certificates"] and not result["not_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
