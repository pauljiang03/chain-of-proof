"""Receipt-only A submissions. No claim semantics are inspected in this module.

The seal is an integrity checkpoint, not an authenticity or completeness proof.
The caller must stop its investigator and all writers before explicitly sealing.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
from functools import wraps
import hashlib
import json
import math
import os
from pathlib import Path
import stat

from agent.audit import audited
from agent.tools import Workbench


CANDIDATES = "candidates.jsonl"
SEAL = "seal.json"


def _finite_json(value):
    """Reject Python coercions as well as non-finite numbers; preserve JSON values."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _finite_json(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _finite_json(item)
        return
    raise ValueError("Submission must contain only finite JSON values.")


def _encode(value):
    _finite_json(value)
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValueError("Non-finite JSON number.")


def _decode(raw):
    result = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    _finite_json(result)
    return result


@contextmanager
def _regular(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Expected a regular input file.")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            yield stream
    finally:
        if fd is not None:
            os.close(fd)


def _binding(path):
    digest, size = hashlib.sha256(), 0
    with _regular(path) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def _rows(raw):
    """Validate recording envelopes only, never claims, questions or revisions."""
    if raw and not raw.endswith(b"\n"):
        raise ValueError("Candidate log has an incomplete final entry.")
    entries = []
    for sequence, line in enumerate(raw.splitlines(), 1):
        entry = _decode(line)
        required = {"schema_version", "sequence", "candidate_id", "question", "claim"}
        if (not isinstance(entry, dict) or not required <= set(entry)
                or set(entry) - required - {"revises"}
                or type(entry.get("schema_version")) is not int or entry["schema_version"] != 1
                or type(entry.get("sequence")) is not int or entry["sequence"] != sequence
                or entry.get("candidate_id") != f"P{sequence:06d}"):
            raise ValueError("Candidate log has an invalid recording envelope or order.")
        entries.append(entry)
    return entries


@contextmanager
def _exclusive(run_dir):
    # A fresh bridge process may reconstruct the Workbench for every command.
    # Serialize the complete audited call, not only candidate ID allocation.
    path = Path(run_dir) / ".candidates.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Candidate lock must be a regular file.")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock, _exclusive(self.run_dir):
            return method(self, *args, **kwargs)
    return call


class ReceiptWorkbench(Workbench):
    """The existing read tools plus unchecked, non-deduplicated receipts.

    JSON strings stay strings: even a string containing a valid claim is not
    parsed. Unknown/self/forward revision values are recorded without feedback.
    Audit success describes completed receipt delivery, never proof acceptance.
    """

    def __init__(self, facts_path, run_dir, proposer="agent"):
        directory = Path(run_dir)
        directory.mkdir(parents=True, exist_ok=True)
        with _exclusive(directory):
            if (directory / SEAL).exists() or (directory / SEAL).is_symlink():
                raise ValueError("Candidate log is sealed; new submissions are forbidden.")
            path = directory / CANDIDATES
            try:
                with path.open("xb"):
                    pass
            except FileExistsError:
                pass
            with _regular(path) as stream:
                _rows(stream.read())
            super().__init__(facts_path, directory, proposer=proposer)

    @_serialized
    def forms(self):
        return super().forms()

    @_serialized
    def sql(self, query):
        return super().sql(query)

    @_serialized
    def fact(self, fact_id):
        return super().fact(fact_id)

    @_serialized
    @audited
    def check(self, question, claim, revises=None):
        if (self.run_dir / SEAL).exists() or (self.run_dir / SEAL).is_symlink():
            raise ValueError("Candidate log is sealed; new submissions are forbidden.")
        values = {"question": question, "claim": claim}
        if revises is not None:
            values["revises"] = revises
        _finite_json(values)
        path = self.run_dir / CANDIDATES
        with _regular(path) as stream:
            sequence = len(_rows(stream.read())) + 1
        candidate_id = f"P{sequence:06d}"
        entry = {"schema_version": 1, "sequence": sequence, "candidate_id": candidate_id, **values}
        # One serialized append; no semantic validation, normalization or dedup.
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "ab") as stream:
            stream.write(_encode(entry) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        return {"candidate_id": candidate_id, "status": "unverified", "receipt": "recorded"}

    def conclude(self, *args, **kwargs):
        raise RuntimeError("Conclusions are not available in the ablation tool contract.")


def seal_candidates(run_dir, *, facts_path, metadata=None):
    """Write seal.json once, after the caller has stopped all investigator work.

    Metadata is opaque finite JSON supplied by the caller; its paths are never
    followed. The fixed candidate log and explicit facts argument alone are read.
    The checkpoint binds retained bytes, not claim truth or unrecorded attempts.
    """
    directory = Path(run_dir)
    if not directory.is_dir():
        raise ValueError("Candidate run directory does not exist.")
    metadata = {} if metadata is None else metadata
    if not isinstance(metadata, dict):
        raise ValueError("Seal metadata must be a JSON object.")
    _finite_json(metadata)
    with _exclusive(directory):
        target = directory / SEAL
        if target.exists() or target.is_symlink():
            raise FileExistsError("Candidate seal already exists.")
        path = directory / CANDIDATES
        try:
            with path.open("xb"):
                pass
        except FileExistsError:
            pass
        with _regular(path) as stream:
            raw = stream.read()
        entries = _rows(raw)
        seal = {"schema_version": 1, "kind": "ablation-candidate-seal",
                "candidates": {"file": CANDIDATES, "sha256": hashlib.sha256(raw).hexdigest(),
                               "bytes": len(raw), "count": len(entries)},
                "facts": _binding(facts_path), "metadata": metadata}
        with target.open("xb") as stream:
            stream.write(_encode(seal) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        return seal
