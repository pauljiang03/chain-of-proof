"""Build and verify a portable directory of records and independently checked claims.

    python -m verifier.package build --run RUN --facts FACTS --out NEW_DIRECTORY
    python -m verifier.package verify --bundle DIRECTORY [--expected-manifest-sha256 HASH]

Verification uses the installed checker and Lean, never executable code from the
package. Integrity is not original-disk authenticity. An externally retained
manifest digest is needed to detect a complete replacement of an untrusted bundle.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess

from checker import claims, report
from checker.check import render_lean
from checker.facts import open_source
from agent.case import read_question_profile
from verifier.verify import verify_run


ROOT = Path(__file__).resolve().parent.parent
OPTIONAL = ("audit.jsonl", "proposals.jsonl", "conclusions.jsonl", "run-manifest.json",
            "extraction-metadata.json", "questions.json")
REQUIRED = {"run.json", "report.md", "verification.json", "toolchain.json"}
FACT_NAMES = {"facts.json", "facts.duckdb"}
ALLOWED = REQUIRED | FACT_NAMES | set(OPTIONAL)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SCOPE = ("Certificates are regenerated against the complete supplied fact store. "
         "This does not establish the authenticity or completeness of an original disk image, "
         "the correctness of extraction, or the truth of unverified judgments. File hashes and "
         "audit chains need an externally retained checkpoint to detect complete replacement. "
         "Coverage, history, and other run metadata remain recorded summaries; they are not "
         "independently established by certificate or audit-integrity verification.")


def _regular(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected a regular file, not a symlink: {path}")
    return path


def _open_read(path):
    """Reject final-component symlinks, including a replacement after the check."""
    path = _regular(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError(f"expected a regular file: {path}")
    return os.fdopen(fd, "rb")


def _fingerprint(path):
    digest, size = hashlib.sha256(), 0
    with _open_read(path) as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def _object(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"non-finite JSON number: {value}")

    with _open_read(path) as stream:
        value = json.load(stream, object_pairs_hook=unique, parse_constant=invalid)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _write(path, value):
    encoded = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(encoded)


def _copy(source, destination, expected):
    digest, size = hashlib.sha256(), 0
    with _open_read(source) as incoming, Path(destination).open("xb") as outgoing:
        for chunk in iter(lambda: incoming.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
            outgoing.write(chunk)
    if {"sha256": digest.hexdigest(), "bytes": size} != expected:
        raise ValueError(f"source changed while building the package: {source}")


def _audit(path, expected_head=None):
    try:
        from agent.audit import verify_audit
    except ImportError as error:
        raise ValueError("package includes an audit log but this installation has no audit verifier") from error
    result = verify_audit(path, expected_head=expected_head)
    if not isinstance(result, dict) or result.get("passed") is not True:
        raise ValueError("audit integrity verification failed")
    return {"status": "verified", "count": result["count"], "head": result["head"]}


def _toolchain():
    implementation = ["agent/audit.py", "agent/case.py", "checker/catalog.py", "checker/claims.py", "checker/facts.py", "checker/check.py",
                      "checker/citations.py", "checker/needs.py", "checker/report.py", "verifier/verify.py", "verifier/package.py",
                      "lean/lean-toolchain", "lean/lakefile.toml", "lean/ChainOfProof.lean"]
    implementation += [str(path.relative_to(ROOT)) for path in sorted((ROOT / "lean/ChainOfProof").glob("*.lean"))]
    identity = {"schema_version": 1,
                "purpose": "Exporter/verifier environment; not a claim about the original investigator runtime",
                "python": platform.python_version(),
                "declared_lean": (ROOT / "lean/lean-toolchain").read_text().strip(),
                "implementation": {name: _fingerprint(ROOT / name) for name in implementation}}
    for key, command, cwd in (
        ("source_revision", ["git", "rev-parse", "HEAD"], ROOT),
        ("lean_version", ["lake", "env", "lean", "--version"], ROOT / "lean"),
    ):
        try:
            process = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=15)
            identity[key] = process.stdout.strip() if process.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            identity[key] = None
    return identity


def _facts(path):
    try:
        source = open_source(path)
        return source, len(source.all())
    except Exception as error:
        # Optional database drivers have their own exception classes. Malformed
        # supplied databases must fail closed without requiring that driver here.
        raise ValueError("cannot read the supplied fact store: " + type(error).__name__) from error


def _recorded(value, source):
    known = isinstance(value, str) and bool(value)
    return {"status": "recorded" if known else "unknown", "value": value if known else None,
            "source": source if known else None}


def _report_run(data, source):
    """Stored Lean is display material, so bind it to independently regenerated code."""
    display = copy.deepcopy(data)
    for finding in display["findings"]:
        claim = claims.parse(finding["claim"])
        ids, found = claims.cited_facts(claim, source)
        lean = render_lean(finding["finding_id"], [found[i] for i in ids], claim)
        if finding.get("lean") not in (None, "", lean):
            raise ValueError(f"stored Lean source differs from regeneration: {finding['finding_id']}")
        finding["lean"] = lean
    return display


def _render_report(data, source):
    return report.render(_report_run(data, source)) + "\n## Verification package scope\n\n" + SCOPE + "\n"


def _original_inputs(run_manifest, files, facts_name):
    if run_manifest is None:
        return {"status": "unknown", "inputs": {}}
    inputs = run_manifest["inputs"]
    receipts = {}
    for role, binding in inputs.items():
        name = {"facts": facts_name, "questions": "questions.json"}.get(role)
        if name is None or name not in files:
            # Original paths are descriptive only. Do not resolve them to add
            # prompt, case-profile, health, or other inputs to the package.
            receipts[role] = {"status": "not_packaged", "file": None}
        else:
            if (not isinstance(binding, dict)
                    or any(binding.get(key) != files[name][key] for key in ("sha256", "bytes"))):
                raise ValueError(f"run manifest {role} binding differs from the packaged input")
            receipts[role] = {"status": "packaged_verified", "file": name}
    if "questions.json" in files and "questions" not in inputs:
        receipts["questions"] = {"status": "packaged_unbound", "file": "questions.json"}
    return {"status": "recorded", "inputs": receipts}


def _provenance(data, run_manifest, audit, files, facts_name):
    case = data["case"]
    investigator = run_manifest.get("investigator", {}) if run_manifest else {}
    software = run_manifest.get("software", {}) if run_manifest else {}
    if not isinstance(investigator, dict) or not isinstance(software, dict):
        raise ValueError("run manifest investigator/software metadata must be objects")
    git = software.get("git", {})
    if not isinstance(git, dict):
        raise ValueError("run manifest git metadata must be an object")
    requested = investigator.get("requested_model")
    backend = investigator.get("backend")
    return {
        "requested_model": _recorded(requested or case.get("model"),
                                     "run-manifest.json#/investigator/requested_model" if requested else "run.json#/case/model"),
        "resolved_model": _recorded(investigator.get("resolved_model"), "run-manifest.json#/investigator/resolved_model"),
        "backend": _recorded(backend or case.get("backend"),
                             "run-manifest.json#/investigator/backend" if backend else "run.json#/case/backend"),
        "original_code_revision": _recorded(git.get("commit"), "run-manifest.json#/software/git/commit"),
        "run_manifest": "included" if run_manifest is not None else "unknown",
        "original_inputs": _original_inputs(run_manifest, files, facts_name),
        "recorded_summaries": {name: "recorded_not_independently_verified" if name in data else "unavailable"
                               for name in ("coverage", "history")},
        "audit": audit,
    }


def _check_fact_binding(data, run_manifest, facts_hash):
    case = data.get("case", {})
    if not isinstance(case, dict):
        raise ValueError("run case metadata must be an object")
    if case.get("facts_sha256") is not None and case["facts_sha256"] != facts_hash["sha256"]:
        raise ValueError("run facts hash differs from the supplied complete fact store")
    if run_manifest is not None:
        if type(run_manifest.get("schema_version")) is not int or run_manifest["schema_version"] != 1:
            raise ValueError("unsupported run manifest schema")
        inputs = run_manifest.get("inputs")
        binding = inputs.get("facts") if isinstance(inputs, dict) else None
        if (not isinstance(binding, dict) or binding.get("sha256") != facts_hash["sha256"]
                or binding.get("bytes") != facts_hash["bytes"]):
            raise ValueError("run manifest facts binding differs from the complete fact store")


def _check_audit_binding(data, audit, fingerprint):
    declared = data.get("audit")
    if declared is None:
        return
    if not isinstance(declared, dict):
        raise ValueError("run audit metadata must be an object")
    if declared.get("status") == "unavailable" and fingerprint is None:
        return
    if (fingerprint is None or declared.get("status") != "valid" or declared.get("passed") is not True
            or declared.get("sha256") != fingerprint["sha256"] or declared.get("head") != audit["head"]
            or declared.get("count") != audit["count"]
            or declared.get("expected_head") not in (None, audit["head"])):
        raise ValueError("audit file does not match the run's declared audit checkpoint")


def _validate_toolchain(identity):
    if (identity.get("schema_version") != 1 or not isinstance(identity.get("python"), str)
            or not isinstance(identity.get("declared_lean"), str)
            or not isinstance(identity.get("implementation"), dict) or not identity["implementation"]):
        raise ValueError("missing exporter/verifier toolchain identity")
    for name, fingerprint in identity["implementation"].items():
        # These are identity labels, never executable paths or files to open.
        if (not isinstance(name, str) or not isinstance(fingerprint, dict)
                or not isinstance(fingerprint.get("sha256"), str)
                or not SHA256.fullmatch(fingerprint["sha256"])
                or type(fingerprint.get("bytes")) is not int or fingerprint["bytes"] < 0):
            raise ValueError("invalid toolchain source fingerprint")


def build_package(run, facts, out):
    """Reverify, then build a new directory. Return its manifest; never overwrite.

    A failed copy can leave an incomplete directory without manifest.json. Such a
    directory is deliberately unverifiable and must not be presented as a package.
    """
    run, facts, out = Path(run), Path(facts), Path(out)
    if out.exists() or out.is_symlink():
        raise ValueError(f"refusing to overwrite existing package directory: {out}")
    run_hash, facts_hash = _fingerprint(run), _fingerprint(facts)
    data = _object(run)
    if not isinstance(data.get("case"), dict) or not isinstance(data["case"].get("name"), str):
        raise ValueError("run needs case metadata with a name")
    source, count = _facts(facts)
    verification = verify_run(data, source)
    if not verification["passed"]:
        raise ValueError("certificate verification failed; no package exported")
    if _fingerprint(run) != run_hash or _fingerprint(facts) != facts_hash:
        raise ValueError("run or facts changed during certificate verification")
    rendered = _render_report(data, source)
    sidecars = {}
    for name in OPTIONAL:
        path = run.parent / name
        if path.exists() or path.is_symlink():
            sidecars[name] = _fingerprint(path)
    audit = _audit(run.parent / "audit.jsonl") if "audit.jsonl" in sidecars else {
        "status": "unknown", "count": None, "head": None}
    _check_audit_binding(data, audit, sidecars.get("audit.jsonl"))
    run_manifest = _object(run.parent / "run-manifest.json") if "run-manifest.json" in sidecars else None
    _check_fact_binding(data, run_manifest, facts_hash)
    if "questions.json" in sidecars:
        read_question_profile(run.parent / "questions.json")
    if "extraction-metadata.json" in sidecars:
        _object(run.parent / "extraction-metadata.json")
    toolchain = _toolchain()
    facts_name = "facts.json" if str(facts).endswith(".json") else "facts.duckdb"
    manifest = {
        "schema_version": 1,
        "format": "chain-of-proof-verification-directory",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "facts": {"path": facts_name, "complete_file": True, "records": count},
        "source_bindings": {"run": {"name": run.name, **run_hash},
                            "facts": {"name": facts.name, **facts_hash}},
        "provenance": _provenance(data, run_manifest, audit, {facts_name: facts_hash, **sidecars}, facts_name),
        "scope": SCOPE,
        "files": {},
    }
    # Reserve only after proof/input checks; exclusive creation handles racing builders.
    out.mkdir(parents=True, exist_ok=False)
    _copy(run, out / "run.json", run_hash)
    _copy(facts, out / facts_name, facts_hash)
    with (out / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(rendered)
    _write(out / "verification.json", verification)
    _write(out / "toolchain.json", toolchain)
    for name, fingerprint in sidecars.items():
        _copy(run.parent / name, out / name, fingerprint)
    payloads = REQUIRED | {facts_name} | set(sidecars)
    if {path.name for path in out.iterdir()} != payloads:
        raise ValueError("unexpected entries appeared while building the package")
    for name in sorted(payloads):
        manifest["files"][name] = _fingerprint(out / name)
    # Manifest is the completion marker and is never written for a failed build.
    _write(out / "manifest.json", manifest)
    return manifest


def _validate_manifest(manifest):
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("unsupported package manifest schema")
    if manifest.get("format") != "chain-of-proof-verification-directory":
        raise ValueError("not a verification-directory manifest")
    files = manifest.get("files")
    if not isinstance(files, dict) or not REQUIRED <= set(files) or not set(files) <= ALLOWED:
        raise ValueError("manifest has missing required files, unsafe paths, or non-allowlisted files")
    if len(set(files) & FACT_NAMES) != 1:
        raise ValueError("manifest must name exactly one complete fact store")
    for name, fingerprint in files.items():
        if not isinstance(fingerprint, dict) or not isinstance(fingerprint.get("sha256"), str) or not SHA256.fullmatch(fingerprint["sha256"]):
            raise ValueError(f"invalid file hash for {name}")
        if type(fingerprint.get("bytes")) is not int or fingerprint["bytes"] < 0:
            raise ValueError(f"invalid file size for {name}")
    facts = manifest.get("facts")
    if (not isinstance(facts, dict) or facts.get("path") not in FACT_NAMES or facts["path"] not in files
            or facts.get("complete_file") is not True or type(facts.get("records")) is not int or facts["records"] < 0):
        raise ValueError("missing complete-fact-store binding")
    bindings = manifest.get("source_bindings")
    if not isinstance(bindings, dict):
        raise ValueError("missing source bindings")
    for role, name in (("run", "run.json"), ("facts", facts["path"])):
        binding = bindings.get(role)
        if (not isinstance(binding, dict) or not isinstance(binding.get("name"), str)
                or any(binding.get(key) != files[name][key] for key in ("sha256", "bytes"))):
            raise ValueError(f"source binding disagrees with packaged {role}")
    if not isinstance(manifest.get("provenance"), dict):
        raise ValueError("missing provenance declaration (unknown values must be explicit)")
    return files


def verify_package(bundle, expected_manifest_sha256=None):
    """Check inventory/hashes first, then independently regenerate every proof."""
    result = {"passed": False, "problems": [], "manifest_sha256": None,
              "integrity": False, "externally_anchored": False, "certificates": None,
              "audit": {"status": "unknown", "count": None, "head": None}, "scope": SCOPE}
    try:
        bundle = Path(bundle)
        if bundle.is_symlink() or not bundle.is_dir():
            raise ValueError("bundle must be a directory, not a symlink")
        digest = _fingerprint(bundle / "manifest.json")["sha256"]
        result["manifest_sha256"] = digest
        if expected_manifest_sha256 is not None:
            if not isinstance(expected_manifest_sha256, str) or not SHA256.fullmatch(expected_manifest_sha256):
                raise ValueError("external manifest SHA-256 must contain 64 lowercase hexadecimal characters")
            if expected_manifest_sha256 != digest:
                raise ValueError("manifest does not match the externally retained SHA-256")
            result["externally_anchored"] = True
        manifest = _object(bundle / "manifest.json")
        files = _validate_manifest(manifest)
        if {path.name for path in bundle.iterdir()} != set(files) | {"manifest.json"}:
            raise ValueError("package contains missing or unlisted entries")
        for name, fingerprint in files.items():
            if _fingerprint(bundle / name) != {key: fingerprint[key] for key in ("sha256", "bytes")}:
                raise ValueError(f"file hash or size mismatch: {name}")
        result["integrity"] = True
        provenance = manifest["provenance"]
        declared_audit = provenance.get("audit")
        if not isinstance(declared_audit, dict):
            raise ValueError("missing audit provenance declaration")
        if "audit.jsonl" in files:
            if declared_audit.get("status") != "verified":
                raise ValueError("audit log lacks its declared verification checkpoint")
            result["audit"] = _audit(bundle / "audit.jsonl", declared_audit.get("head"))
            if result["audit"] != declared_audit:
                raise ValueError("audit count/head differs from the manifest")
        elif declared_audit != result["audit"]:
            raise ValueError("absent audit log must be marked unknown")
        _validate_toolchain(_object(bundle / "toolchain.json"))
        saved_verification = _object(bundle / "verification.json")
        if saved_verification.get("passed") is not True:
            raise ValueError("package was not exported from a passing certificate verification")
        data = _object(bundle / "run.json")
        _check_audit_binding(data, result["audit"], files.get("audit.jsonl"))
        run_manifest = _object(bundle / "run-manifest.json") if "run-manifest.json" in files else None
        _check_fact_binding(data, run_manifest, files[manifest["facts"]["path"]])
        if "questions.json" in files:
            read_question_profile(bundle / "questions.json")
        if "extraction-metadata.json" in files:
            _object(bundle / "extraction-metadata.json")
        if _provenance(data, run_manifest, result["audit"], files, manifest["facts"]["path"]) != provenance:
            raise ValueError("provenance declaration differs from the packaged run metadata")
        source, count = _facts(bundle / manifest["facts"]["path"])
        if count != manifest["facts"]["records"]:
            raise ValueError("fact count differs from the complete-store declaration")
        result["certificates"] = verify_run(data, source)
        if not result["certificates"]["passed"]:
            raise ValueError("certificate verification failed against bundled facts")
        if json.dumps(saved_verification, sort_keys=True) != json.dumps(result["certificates"], sort_keys=True):
            raise ValueError("saved verification summary differs from independent verification")
        with _open_read(bundle / "report.md") as stream:
            if stream.read().decode("utf-8") != _render_report(data, source):
                raise ValueError("report differs from regeneration; use the recorded renderer version")
        # Proof checking can take long enough for any artifact to change. Recheck
        # every listed payload, not only the run and its fact store.
        for name in files:
            if _fingerprint(bundle / name) != {key: files[name][key] for key in ("sha256", "bytes")}:
                raise ValueError(f"{name} changed during verification")
        if {path.name for path in bundle.iterdir()} != set(files) | {"manifest.json"}:
            raise ValueError("package inventory changed during verification")
        if _fingerprint(bundle / "manifest.json")["sha256"] != digest:
            raise ValueError("manifest changed during verification")
        result["passed"] = True
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result["problems"].append(str(error))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="reverify and export to a new directory")
    build.add_argument("--run", required=True)
    build.add_argument("--facts", required=True)
    build.add_argument("--out", required=True)
    verify = commands.add_parser("verify", help="verify a supplied directory with installed Lean/checker")
    verify.add_argument("--bundle", required=True)
    verify.add_argument("--expected-manifest-sha256", help="optional digest retained outside the package")
    args = parser.parse_args(argv)
    if args.command == "build":
        try:
            build_package(args.run, args.facts, args.out)
        except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
            parser.error(str(error))
        print(f"Built {args.out}; manifest SHA-256: {_fingerprint(Path(args.out) / 'manifest.json')['sha256']}")
        print(SCOPE)
        return 0
    result = verify_package(args.bundle, args.expected_manifest_sha256)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
