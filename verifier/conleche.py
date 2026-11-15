"""Recheck saved certificates with con-leche, a second proof checker.

    python -m verifier.conleche --run runs/current/run.json --facts evidence/facts.json [--jobs 8] [--out NEW.json]

Lean 4.35 bundles con-leche, a proof checker written separately from Lean's own kernel.
Each certificate's proof is first regenerated from its finding ID, claim and the supplied
facts. Its `verified` theorem is then exported with `leanexport` and checked by con-leche.
A finding passes only if con-leche exits 0 and the export declares that theorem; a
missing proof fails the whole run.

This checks proofs, not whether readers parsed the disk images correctly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from checker import claims
from checker.check import render_lean, valid_finding_id
from checker.facts import FactSource, open_source
from verifier.verify import verify

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
    """Check a proof term only. Use check_run to bind a saved finding to its facts."""
    try:
        return check_export(export(lean_text, workdir, tools), theorem_name(lean_text), tools)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        return {"accepted": False, "detail": str(error)}


def check_run(run: dict, tools: Toolchain, jobs: int = 4, *,
              source: Optional[FactSource] = None, facts_sha256: Optional[str] = None) -> dict:
    """Bind each finding to its facts and recheck it; missing facts or proofs fail.

    Source reads are serial (one DuckDB connection); proof checks run in parallel.
    """
    findings = run.get('findings') if isinstance(run, dict) else None
    if not isinstance(findings, list):
        raise ValueError('run must contain a findings list')
    ids = [f.get('finding_id') for f in findings if isinstance(f, dict)
           and isinstance(f.get('finding_id'), str)]
    duplicate_ids = {fid for fid, count in Counter(ids).items() if count > 1}
    case = run.get('case', {})
    if not isinstance(case, dict):
        raise ValueError('run case metadata must be an object')
    declared_digest = case.get('facts_sha256')
    digest_problem = (declared_digest is not None and
                      (not isinstance(declared_digest, str) or declared_digest != facts_sha256))
    results, pending = [], []
    without_proof = 0
    for index, finding in enumerate(findings):
        fid = finding.get('finding_id') if isinstance(finding, dict) else None
        saved = finding.get('lean') if isinstance(finding, dict) else None
        missing = not isinstance(saved, str) or not saved.strip()
        without_proof += missing
        result = {'finding_id': fid, 'accepted': False, 'checked': False}
        try:
            if not isinstance(finding, dict) or not valid_finding_id(fid):
                raise ValueError('finding must have a valid finding ID')
            if fid in duplicate_ids:
                raise ValueError('duplicate finding ID')
            if missing:
                raise ValueError('required certificate proof text is missing')
            if source is None:
                raise ValueError('an explicit facts source is required to bind the certificate')
            if digest_problem:
                raise ValueError('run facts digest differs from, or is not bound to, the supplied facts')
            problems = verify(finding, source)
            if problems:
                raise ValueError('fact-based replay failed: ' + '; '.join(problems))
            claim = claims.parse(finding['claim'])
            cited, found = claims.cited_facts(claim, source)
            generated = render_lean(fid, [found[item] for item in cited], claim)
            if saved != generated:
                raise ValueError('stored Lean proof differs from regeneration of this finding and its facts')
            pending.append((index, generated))
        except (ValueError, KeyError, TypeError, AttributeError, OSError,
                subprocess.SubprocessError) as error:
            result['detail'] = str(error)
        results.append(result)
    with tempfile.TemporaryDirectory(prefix="cop-conleche-") as scratch:
        def one(numbered):
            index, generated = numbered
            workdir = Path(scratch) / str(index)
            workdir.mkdir()
            result = check(generated, tools, workdir)
            shutil.rmtree(workdir, ignore_errors=True)
            return index, result
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
            for index, result in pool.map(one, pending):
                results[index].update(result, checked=True)
    accepted = sum(r['accepted'] for r in results)
    return {
        "checker": CHECKER,
        "mode": MODE,
        "lean": tools.version,
        "certificates": len(results),
        "total_findings": len(findings),
        "checked": sum(r['checked'] for r in results),
        "accepted": accepted,
        "passed": bool(results) and accepted == len(results),
        "facts_sha256": facts_sha256,
        "binding": "independent replay and exact proof regeneration from supplied facts",
        "without_proof_text": without_proof,
        "not_accepted": [r for r in results if not r["accepted"]],
    }


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_facts(path, directory):
    """Hash the exact bytes replay will read, without a pathname open/hash race."""
    destination = Path(directory) / ('facts.json' if str(path).endswith('.json') else 'facts.duckdb')
    digest = hashlib.sha256()
    with Path(path).open('rb') as incoming, destination.open('xb') as outgoing:
        for block in iter(lambda: incoming.read(1024 * 1024), b''):
            digest.update(block)
            outgoing.write(block)
    destination.chmod(0o400)
    return destination, digest.hexdigest()


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:400] if lines else "(no output)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="one bundled run containing certificates")
    ap.add_argument("--facts", required=True, help="explicit evidence DB (.duckdb) or JSON facts")
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
    try:
        # Replay the private copy, never the path again, so a swapped file cannot pass.
        # A DuckDB input must be a finalized file; WAL files are not copied.
        with tempfile.TemporaryDirectory(prefix='cop-conleche-facts-') as scratch:
            captured, observed = _snapshot_facts(args.facts, scratch)
            source = open_source(captured)
            result = check_run(json.loads(Path(args.run).read_text()), tools, args.jobs,
                               source=source, facts_sha256=observed)
            if _sha256(args.facts) != observed:
                raise ValueError('facts changed during certificate verification')
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'con-leche verification failed: {error}', file=sys.stderr)
        return 1
    if out:
        with out.open("x") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    for miss in result["not_accepted"]:
        print(f"NOT ACCEPTED {miss['finding_id']}: {miss['detail']}")
    print(f"{result['accepted']}/{result['certificates']} certificates accepted by "
          f"{CHECKER} ({MODE}); {result['checked']}/{result['total_findings']} second-checked; "
          f"{len(result['not_accepted'])} not accepted")
    return 0 if result['passed'] else 1


if __name__ == "__main__":
    raise SystemExit(main())
