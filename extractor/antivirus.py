"""Optional local ClamAV scan of readable allocated files in a mounted image.

Evidence is copied to numbered, nonexecutable temporary files. The scanner receives
only those copies. Results always state scan scope and limitations; a negative scan
is not proof that no malware exists, and a signature hit is not proof of execution.
This reader must be selected explicitly and never downloads signatures itself.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

MAX_FILES = 100_000
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024 * 1024
TIMEOUT = 300


def candidates(target):
    """Visit drive-letter roots once; do not follow links or alternate streams."""
    roots = sorted({str(name) for name in target.fs.mounts
                    if re.fullmatch(r"[A-Za-z]:", str(name))})
    if not roots:
        raise ValueError("no drive-letter filesystem roots are available for scanning")
    pending = [target.fs.path(root + "/") for root in reversed(roots)]
    visited = set()
    while pending:
        path = pending.pop()
        key = str(path).casefold()
        if key in visited:
            continue
        visited.add(key)
        if len(visited) > MAX_FILES * 4:
            raise ValueError("directory traversal budget exhausted")
        if path.is_symlink():
            continue
        if path.is_dir():
            entries = []
            for child in path.iterdir():
                if len(entries) >= MAX_FILES:
                    raise ValueError("directory entry budget exhausted")
                entries.append(child)
            pending.extend(reversed(sorted(entries, key=lambda item: str(item).casefold())))
        elif path.is_file():
            yield path


def copy_file(source, destination, size):
    if not isinstance(size, int) or isinstance(size, bool) or not 0 <= size <= MAX_FILE_BYTES:
        raise ValueError("file exceeds scan size limit or has invalid size")
    digest, total = hashlib.sha256(), 0
    with source.open("rb") as src, destination.open("xb") as dst:
        destination.chmod(0o600)
        while True:
            block = src.read(min(1024 * 1024, size - total + 1))
            if not block:
                break
            total += len(block)
            if total > size:
                raise ValueError("file stream exceeds recorded size")
            digest.update(block)
            dst.write(block)
    if total != size:
        raise ValueError("file stream is shorter than recorded size")
    return digest.hexdigest()


def parse_results(text, mapping, returncode):
    """Only scanner paths that we staged may name findings; retain errors separately."""
    detections, errors = [], []
    for line in text.splitlines():
        if line.endswith(" FOUND"):
            path, separator, signature = line[:-6].partition(": ")
            if not separator or path not in mapping:
                errors.append("scanner finding refers to an unknown staged file")
                continue
            detections.append({**mapping[path], "signature": signature})
        elif line.endswith(" ERROR") or "WARNING:" in line or "LibClamAV Error:" in line:
            errors.append(line)
    if returncode not in (0, 1):
        errors.append(f"scanner exited with error status {returncode}")
    if returncode == 1 and not detections:
        errors.append("scanner reported detections but no finding could be bound to a file")
    if returncode == 0 and detections:
        errors.append("scanner result contradicts its exit status")
    # Exceeded limits are reported as heuristic detections by ClamAV, not malware.
    limit_hits = [item for item in detections if item["signature"].startswith("Heuristics.Limits.Exceeded")]
    if limit_hits:
        errors.append("scanner limits were reached for one or more files")
    return {"detections": [item for item in detections if item not in limit_hits],
            "errors": errors, "limit_hits": limit_hits}


def database_bindings(directory):
    from .intake import sha256_file
    root = Path(directory)
    files = sorted(path for path in root.iterdir() if path.suffix.lower() in
                   (".cvd", ".cld", ".cud", ".hdb", ".hsb", ".ndb", ".ldb", ".sfp", ".fp", ".ign", ".ign2"))
    if not files or any(path.is_symlink() or not path.is_file() for path in files):
        raise ValueError("signature directory needs regular signature files")
    return [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in files]


def scan(target, *, executable=None, database=None):
    executable = executable or shutil.which("clamscan")
    if not executable:
        raise ValueError("ClamAV clamscan is unavailable; install ClamAV and its signature database, then select antivirus again")
    database = database or os.environ.get("COP_CLAMAV_DATABASE")
    if not database:
        raise ValueError("set COP_CLAMAV_DATABASE to an explicit local signature directory so scan inputs can be hashed")
    signatures = database_bindings(database)
    version = subprocess.run([executable, "--version"], capture_output=True, text=True,
                             timeout=30, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="cop-av-") as temporary:
        root = Path(temporary)
        files = root / "files"
        files.mkdir()
        mapping, omitted, total = {}, [], 0
        try:
            for source in candidates(target):
                if len(mapping) >= MAX_FILES:
                    omitted.append({"reason": "file count limit reached; remaining files not scanned"})
                    break
                destination = files / f"{len(mapping):08d}.bin"
                try:
                    size = source.stat().st_size
                    if not isinstance(size, int) or isinstance(size, bool) or total + size > MAX_TOTAL_BYTES:
                        raise ValueError("total scan byte budget exceeded or invalid file size")
                    digest = copy_file(source, destination, size)
                    mapping[str(destination)] = {"path": str(source), "sha256": digest, "bytes": size}
                    total += size
                except Exception as error:
                    destination.unlink(missing_ok=True)
                    omitted.append({"path": str(source), "reason": str(error)})
        except Exception as error:
            omitted.append({"reason": f"filesystem traversal incomplete: {error}"})
        if not mapping:
            raise ValueError("no readable files staged for scanning")
        command = [executable, "--recursive", "--infected", "--stdout", "--no-summary",
                   f"--database={Path(database).resolve()}",
                   "--follow-dir-symlinks=0", "--follow-file-symlinks=0",
                   "--bytecode-unsigned=no", "--alert-exceeds-max=yes",
                   "--max-scantime=10000",
                   f"--max-filesize={MAX_FILE_BYTES}", "--max-scansize=1073741824",
                   f"--tempdir={root}", str(files)]
        log = root / "scanner.log"
        timed_out = False
        with log.open("wb") as output:
            try:
                result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                # subprocess.run has killed and reaped the scanner. Its retained
                # positive observations still matter; never turn timeout into zero.
                timed_out = True
                result = subprocess.CompletedProcess(command, 124)
        raw = log.read_bytes()
        if len(raw) > 64 * 1024 * 1024:
            raise ValueError("scanner log exceeds result size limit")
        parsed = parse_results(raw.decode("utf-8", "replace"), mapping, result.returncode)
        if timed_out:
            parsed["errors"].append(f"scanner time limit {TIMEOUT} seconds reached; remaining files unscanned")
        if database_bindings(database) != signatures:
            parsed["errors"].append("signature database changed during scanning")
        # Keep the exact file list and scanner transcript in the evidence provenance.
        # Temporary host paths are replaced only in display text, not parsed identities.
        transcript = raw.decode("utf-8", "replace").replace(str(files), "<staged-files>")
        return {**parsed, "scanner_version": version, "exit_code": result.returncode,
                "files": list(mapping.values()), "bytes": total, "omitted": omitted,
                "signature_databases": signatures,
                "transcript": transcript, "transcript_sha256": hashlib.sha256(raw).hexdigest(),
                "options": command[1:-1], "complete_allocated_scope": not omitted and not parsed["errors"],
                "scope": "readable allocated regular files; symlinks, alternate streams, unallocated space and deleted files are excluded"}


def extract(ev, target, ctx):
    from .attributes import emit_attribute
    from .source_scope import merge_scope, subject_scope
    result = scan(target)
    inputs = merge_scope(ctx['common'])
    input_source = {key: inputs[key] for key in ('source_snapshot', 'source_variant')}
    receipt_hash = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    summary = {key: value for key, value in result.items() if key not in ("files", "transcript")}
    summary["staged_file_count"] = len(result["files"])
    common = merge_scope(ctx["common"], dict(artifact="local ClamAV scan", reader="antivirus",
                  source_snapshot="examination", source_variant="antivirus", input_source=input_source,
                  timestamp_semantics="examination_observation", scan=summary, scan_receipt_sha256=receipt_hash,
                  meaning="A scanner observation. A signature match does not establish execution; no detections do not prove absence."))
    subject = json.dumps(subject_scope(common) + [input_source, receipt_hash, 'allocated-file-scan'],
                         sort_keys=True, separators=(',', ':'))
    status = "incomplete" if not result["complete_allocated_scope"] else (
        "detections_reported" if result["detections"] else "no_detections_reported")
    for role, value in (("scanner.version", result["scanner_version"]),
                        ("scanner.result", status), ("scanner.scope", result["scope"])):
        # Keep the complete copied-file manifest once, on the declared scope.
        # Every other observation binds that receipt by its canonical hash.
        provenance = dict(common, scan_receipt=result) if role == "scanner.scope" else common
        emit_attribute(ev, subject, role, value, ctx["examined_at"], **provenance)
    if result["detections"] or result["complete_allocated_scope"]:
        emit_attribute(ev, subject, "scanner.detections_found", bool(result["detections"]),
                       ctx["examined_at"], **common)
    for finding in result["detections"]:
        file_subject = f"{subject}:{ctx['examined_at']}:{finding['path']}"
        emit_attribute(ev, file_subject, "scanner.signature", finding["signature"],
                       ctx["examined_at"], **dict(common, file_sha256=finding["sha256"]))
        emit_attribute(ev, file_subject, "source.path", finding["path"],
                       ctx["examined_at"], **dict(common, file_sha256=finding["sha256"]))
    if not result["complete_allocated_scope"]:
        ev.problem("antivirus", ValueError(f"scan incomplete: {len(result['omitted'])} omissions and {len(result['errors'])} scanner errors; see scan provenance"))
