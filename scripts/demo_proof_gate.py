"""Run a real Lean proof gate on the repository's hand-written synthetic fixture.

    .venv/bin/python scripts/demo_proof_gate.py
    .venv/bin/python scripts/demo_proof_gate.py --out /private/tmp/proof-gate-demo

No API, model, disk-image extraction, or benchmark grading is involved. --out must
name a new directory; without it, generated certificates are temporary.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checker.check import check  # noqa: E402
from checker.facts import JsonFacts  # noqa: E402
from verifier.verify import verify  # noqa: E402

FIXTURE = ROOT / "fixtures/sample_facts.json"
VALID = {"both": [{"usbMountedAs": [4512, 4513]},
                  {"openedFromMount": [4600, 4513]}, {"before": [4512, 4600]}]}
WRONG_DEVICE = {"both": [{"usbMountedAs": [4510, 4511]},
                         {"openedFromMount": [4600, 4511]}]}


def _write_new(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def _execute(directory, retained):
    raw = FIXTURE.read_bytes()
    with (directory / "facts.json").open("xb") as handle:
        handle.write(raw)
    source = JsonFacts(directory / "facts.json")
    facts = source.get([4510, 4511, 4512, 4513, 4600])
    opened, right_mount, wrong_mount = facts[4600], facts[4513], facts[4511]
    accepted = check(VALID, "DemoValid", source, out_dir=directory / "certificates",
                     proposer="fixed synthetic proof-gate demo")
    refused = check(WRONG_DEVICE, "DemoWrongDevice", source, out_dir=directory / "certificates",
                    proposer="deliberately invalid synthetic demo claim")
    _write_new(directory / "refused-claim.json", refused)
    if accepted["status"] != "verified":
        raise RuntimeError("valid fixture claim was not accepted: " + accepted.get("reason", "unknown reason"))

    # Reload the saved certificate and facts. The independent verifier regenerates
    # the claim, English and proof; it does not trust the original check result.
    certificate = json.loads((directory / "certificates/DemoValid.json").read_text())
    verification = verify(certificate, JsonFacts(directory / "facts.json"))
    tampered = copy.deepcopy(certificate)
    copied_row = next(row for row in tampered["cited_facts"] if row["id"] == opened.id)
    old_volume = copied_row["aux_text"]
    copied_row["aux_text"] = source.string(wrong_mount.aux)
    # Deliberately leave row_sha256 unchanged: a stored hash does not authenticate
    # an accompanying copied value unless the verifier compares both to its source.
    _write_new(directory / "tampered-certificate.json", tampered)
    tamper_problems = verify(tampered, JsonFacts(directory / "facts.json"))
    failures = [brick for part in refused.get("parts", [])
                for brick in part.get("bricks", []) if brick.startswith("FAIL")]
    report = {
        "schema_version": 1,
        "demo": "synthetic proof gate; not a benchmark or AI investigation",
        "fixture": {"source": str(FIXTURE.relative_to(ROOT)),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "note": json.loads(raw)["_note"]},
        "evidence": [
            {"id": row.id, "kind": row.kind, "object": source.string(row.obj),
             "related_identity": source.string(row.aux), "utc_microseconds": row.t,
             "uncertainty_microseconds": row.res}
            for row in (facts[4510], wrong_mount, facts[4512], right_mount, opened)],
        "valid_claim": {"status": accepted["status"], "claim": accepted["claim"],
                        "sentence": accepted["english"], "trust_tier": accepted["trust_tier"],
                        "axioms": accepted["axioms"]},
        "invalid_claim": {"status": refused["status"], "claim": refused["claim"],
                          "reason": refused.get("reason"), "failing_conditions": failures,
                          "identity_condition": {
                              "required": "file-open volume identity equals mounted volume identity",
                              "file_open_fact": opened.id, "mount_fact": wrong_mount.id,
                              "file_open_volume": source.string(opened.aux),
                              "mounted_volume": source.string(wrong_mount.aux),
                              "equal": opened.aux == wrong_mount.aux}},
        "independent_verification": {"passed": not verification, "problems": verification},
        "tamper": {"field": "cited_facts[id=4600].aux_text", "before": old_volume,
                   "after": copied_row["aux_text"], "stored_row_hash_unchanged": True,
                   "refused": bool(tamper_problems), "problems": tamper_problems},
        "passed": (refused["status"] == "rejected" and bool(failures)
                   and not verification and bool(tamper_problems)),
        "output_directory": str(directory.resolve()) if retained else None,
        "limitation": "The proof checks declared rules against these synthetic rows. "
                      "It does not prove that a parser, source image, or real-world allegation is correct.",
    }
    _write_new(directory / "result.json", report)
    return report


def run_demo(output=None):
    """Return observed outcomes, retaining artifacts only in a newly created directory."""
    if output is not None:
        directory = Path(output)
        if directory.exists() or directory.is_symlink():
            raise ValueError(f"refusing to overwrite existing output: {directory}")
        directory.mkdir(parents=True, exist_ok=False)
        return _execute(directory, True)
    with tempfile.TemporaryDirectory(prefix="proof-gate-demo-") as temporary:
        return _execute(Path(temporary), False)


def render(report):
    condition = report["invalid_claim"]["identity_condition"]
    evidence = {row["id"]: row for row in report["evidence"]}
    lines = ["SYNTHETIC PROOF-GATE DEMO — no AI or benchmark score",
             f"Evidence: {evidence[4600]['object']} names volume {condition['file_open_volume']}.",
             f"Device A: {evidence[4512]['object']} -> {evidence[4513]['related_identity']}",
             f"Device B: {evidence[4510]['object']} -> {condition['mounted_volume']}",
             f"1. Valid claim: {report['valid_claim']['status'].upper()} "
             f"(Lean {report['valid_claim']['trust_tier']}; axioms: {report['valid_claim']['axioms']})",
             "   " + report["valid_claim"]["sentence"],
             f"2. Wrong-device claim: {report['invalid_claim']['status'].upper()}",
             f"   Required volume equality fails: {condition['file_open_volume']} != {condition['mounted_volume']}.",
             "   " + "; ".join(report["invalid_claim"]["failing_conditions"]),
             "3. Independent verification: " + ("ACCEPTED" if report["independent_verification"]["passed"] else "FAILED"),
             "4. Copied-volume tamper, original row hash retained: " + ("REFUSED" if report["tamper"]["refused"] else "NOT REFUSED"),
             "   " + "; ".join(report["tamper"]["problems"]),
             report["limitation"]]
    if report["output_directory"]:
        lines.append("Artifacts: " + report["output_directory"])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="new directory for JSON, evidence snapshot, and Lean certificate")
    args = parser.parse_args(argv)
    try:
        report = run_demo(args.out)
    except (ValueError, OSError, RuntimeError) as error:
        parser.error(str(error))
    print(render(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
