"""Turn a proposed claim into a certificate or a rejection.

    python -m checker.check --facts fixtures/sample_facts.json --id F7 \\
        --claim '{"both": [{"usbMountedAs": [4512, 4513]}, {"openedFromMount": [4600, 4513]}]}'

The Lean file is written here from the claim tree and the evidence rows, so nothing the
agent types reaches Lean as text. The Lean kernel decides.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

from . import claims, needs
from .facts import Fact, FactSource, open_source

ROOT = Path(__file__).resolve().parent.parent
LEAN_DIR = ROOT / "lean"
CERTS_DIR = ROOT / "certs"

# Axioms a certificate may depend on. Ours depend on none; these three are Lean's
# standard ones and are reported as a weaker tier rather than refused.
STANDARD_AXIOMS = {"propext", "Quot.sound", "Classical.choice"}

_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z")
_built = False

# Census limits. Chunked definitions keep long lists under Lean's recursion limit.
CENSUS_CHUNK_SIZE = 128
CENSUS_MAX_REC_DEPTH = 8192
CENSUS_MAX_HEARTBEATS = 2_000_000


def valid_finding_id(value) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def render_lean(finding_id: str, facts: List[Fact], claim: claims.Claim) -> str:
    if not valid_finding_id(finding_id):
        raise claims.ClaimError("finding id must look like F7 (letters, digits, _)")
    rows = ",\n  ".join(f.to_lean() for f in facts)
    cited = f"def cited : List Fact := [\n  {rows} ]"
    options = ""
    if claims.census_of(claim):         # about every fact of a kind: `cited` is all of them
        options = (f"set_option maxRecDepth {CENSUS_MAX_REC_DEPTH}\n"
                   f"set_option maxHeartbeats {CENSUS_MAX_HEARTBEATS}\n\n")
        if len(facts) > CENSUS_CHUNK_SIZE:
            chunks, definitions = [], []
            for start in range(0, len(facts), CENSUS_CHUNK_SIZE):
                name = f"censusChunk{len(chunks)}"
                chunks.append(name)
                chunk = ",\n  ".join(f.to_lean() for f in facts[start:start + CENSUS_CHUNK_SIZE])
                definitions.append(f"def {name} : List Fact := [\n  {chunk} ]")
            cited = "\n\n".join(definitions) + "\n\ndef cited : List Fact := List.flatten [" + ", ".join(chunks) + "]"
        statement = (f"def census : Census := {claims.to_lean(claim)}\n\n"
                     f"theorem verified : counts cited census = true := by decide +kernel")
    else:
        statement = (f"def claim : Claim := {claims.to_lean(claim)}\n\n"
                     f"theorem verified : holds cited claim = true := by decide +kernel")
    return f"""import ChainOfProof
open ChainOfProof

{options}namespace Cert.{finding_id}

{cited}

{statement}

end Cert.{finding_id}

#print axioms Cert.{finding_id}.verified
"""


def _lean(text: str, timeout: int = 120) -> subprocess.CompletedProcess:
    global _built
    if not _built:
        subprocess.run(["lake", "build"], cwd=LEAN_DIR, check=True, capture_output=True)
        _built = True
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "Cert.lean"
        path.write_text(text)
        return subprocess.run(["lake", "env", "lean", str(path)], cwd=LEAN_DIR,
                              capture_output=True, text=True, timeout=timeout)


def run_kernel(lean_text: str, finding_id: str) -> dict:
    """Compile a certificate. Returns {"ok", "axioms", "tier", "output"}."""
    proc = _lean(lean_text)
    out = proc.stdout + proc.stderr
    name = re.escape(f"Cert.{finding_id}.verified")
    axioms: Optional[List[str]] = None
    if re.search(rf"'{name}' does not depend on any axioms", out):
        axioms = []
    else:
        m = re.search(rf"'{name}' depends on axioms: \[([^\]]*)\]", out, re.S)
        if m:
            axioms = [a.strip() for a in m.group(1).split(",") if a.strip()]
    ok = proc.returncode == 0 and axioms is not None and set(axioms) <= STANDARD_AXIOMS
    tier = None
    if ok:
        tier = "kernel" if not axioms else "kernel+standard-axioms"
    return {"ok": ok, "axioms": axioms, "tier": tier, "output": out.strip()}


def explain(facts: List[Fact], claim: claims.Claim) -> List[dict]:
    """Per-part verdicts from the Lean checker, as feedback for a rejected claim.

    Each part is one set instance; `bricks` lists the primitive checks it expands to.
    """
    if claims.census_of(claim):
        return [{"part": claims.to_json(claim), "ok": False,
                 "bricks": [claims.census_failure(claim, {f.id: f for f in facts})]}]
    rows = ", ".join(f.to_lean() for f in facts)
    parts = claims.parts(claim)
    text = f"import ChainOfProof\nopen ChainOfProof\ndef cited : List Fact := [{rows}]\n"
    for p in parts:
        text += (f'#eval IO.println ("--\\n" ++ String.intercalate "\\n" '
                 f"(explain cited ({claims.to_lean(p)})))\n")
    chunks = _lean(text).stdout.split("--\n")[1:]
    report = []
    for part, chunk in zip(parts, chunks):
        bricks = [re.sub(r"ChainOfProof\.(Claim|Slot|Kind)\.", "", l)
                  for l in chunk.splitlines() if l.startswith(("ok", "FAIL"))]
        report.append({"part": claims.to_json(part),
                       "ok": bool(bricks) and all(b.startswith("ok") for b in bricks),
                       "bricks": bricks})
    return report


def check(claim_json, finding_id: str, source: FactSource, question: str = "",
          out_dir: Path = CERTS_DIR, proposer: str = "") -> dict:
    """Check one proposed claim. Writes certs/<id>.lean and .json only if it verifies.

    Every call, verified or not, is appended to <out_dir>/proposals.jsonl.
    """
    started = time.time()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result: Dict = {"finding_id": finding_id, "question": question, "claim": claim_json,
                    "status": "rejected"}
    if proposer:
        result["proposer"] = proposer       # who proposed it: miner, probe, or an agent
    claim, found = None, None
    try:
        if not valid_finding_id(finding_id):
            raise claims.ClaimError("finding id must look like F7 (letters, digits, _)")
        claim = claims.parse(claim_json)
        result["claim"] = claims.to_json(claim)
        ids, found = claims.cited_facts(claim, source)
        facts = [found[i] for i in ids]
        lean_text = render_lean(finding_id, facts, claim)
        census_timeout = False
        try:
            kernel = run_kernel(lean_text, finding_id)
        except subprocess.TimeoutExpired:
            if not claims.census_of(claim):
                raise
            census_timeout = True
            kernel = {"ok": False, "output": "census kernel evaluation exceeded the 120-second wall-clock limit"}
        if not kernel["ok"]:
            if claims.census_of(claim) and (census_timeout or claims.census_satisfied(claim, found)):
                # A correct count can still exceed Lean's limits; Python never supplies a proof.
                result["reason"] = ("census kernel evaluation exceeded the 120-second wall-clock limit; no certificate was issued"
                                    if census_timeout else "census kernel execution did not certify the count within its execution/resource limits; no certificate was issued")
                result["parts"] = []
                result["lean_output"] = kernel["output"][-2000:]
            else:
                result["reason"] = "the cited facts do not support this claim"
                result["parts"] = explain(facts, claim)
                if not result["parts"]:
                    result["lean_output"] = kernel["output"][-2000:]
        else:
            (out_dir / f"{finding_id}.lean").write_text(lean_text)
            result.update({
                "status": "verified",
                "english": claims.english(claim, found, source),
                "cited_facts": [
                    {"id": f.id, "kind": f.kind, "t": f.t, "res": f.res,
                     "obj": f.obj, "obj_text": source.string(f.obj),
                     "aux": f.aux, "aux_text": source.string(f.aux),
                     "row_sha256": f.row_sha256(), "prov": f.prov}
                    for f in facts],
                "parts": [
                    {"part": claims.to_json(part),
                     "english": claims.english(part, found, source),
                     "rules": claims.rules(part),
                     "strength": claims.strength(part, found)}
                    for part in claims.parts(claim)],
                "rules": claims.rules(claim),
                "strength": claims.strength(claim, found),
                "lean_file": f"{finding_id}.lean",
                "trust_tier": kernel["tier"],
                "axioms": kernel["axioms"],
            })
            (out_dir / f"{finding_id}.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    except claims.ClaimError as e:
        result["reason"] = str(e)
    if result["status"] == "rejected":
        try:
            result["proof_gap"] = (needs.malformed(result.get("reason", "invalid finding id"))
                                   if not valid_finding_id(finding_id) else
                                   needs.diagnose(claim_json, source, parsed=claim, facts=found,
                                                  parts=result.get("parts"), reason=result.get("reason", "")))
        except Exception as error:  # diagnostic failure cannot revise or hide the original refusal
            result["proof_gap"] = needs.execution(
                f"Proof-gap diagnostics failed ({type(error).__name__}); the original rejection is retained.")
    result["checked_in_ms"] = round((time.time() - started) * 1000)
    with open(out_dir / "proposals.jsonl", "a") as log:
        log.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check a proposed forensic claim with Lean.")
    ap.add_argument("--facts", required=True, help="evidence DB (.duckdb) or fixture (.json)")
    ap.add_argument("--id", required=True, help="finding id, e.g. F7")
    ap.add_argument("--claim", required=True, help="claim as JSON, or @file.json")
    ap.add_argument("--question", default="")
    ap.add_argument("--out", default=str(CERTS_DIR))
    args = ap.parse_args(argv)
    raw = Path(args.claim[1:]).read_text() if args.claim.startswith("@") else args.claim
    result = check(json.loads(raw), args.id, open_source(args.facts), args.question,
                   Path(args.out))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "verified" else 1


if __name__ == "__main__":
    sys.exit(main())
