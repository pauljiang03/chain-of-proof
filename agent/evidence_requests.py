"""Bounded collection from trusted intake inputs, never arbitrary agent paths/code.

Collection writes a new full evidence version for a later investigation stage.
Existing facts, certificates and run bindings are never changed by a request.
Recommendations are deterministic diagnostics, not assurances that evidence exists.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

from extractor.intake import extend, load_config, sha256_file
from checker.catalog import ROLES

_LOCK = threading.RLock()
NOTE = ("Diagnostic only. A reader may find no relevant artifact; collecting more records "
        "does not establish the proposed claim or resolve contradictory evidence. "
        "New snapshots require new queries and proofs; existing fact IDs cannot be reused.")
KINDS = {
    "windows": {"usbInsert", "volumeSeen", "lnkTarget", "webSearch", "fileCreated",
                "fileModified", "fileDeleted", "emailSent", "cdBurn"},
    "media": {"volumeOnDevice", "fileCreated", "fileModified", "unallocatedOnDevice"},
    "system": {"systemSetting", "accountSeen", "sessionEvent", "programInstalled", "programRun"},
    "webcloud": {"webVisit", "fileDownloaded", "cloudFile", "accountSeen", "localSearch", "noteText"},
    "filetraces": {"folderOpened", "fileSeen", "fileRenamed", "shadowCopy", "fileRemoved",
                   "fileCreationRecorded", "journalName", "journalParent", "journalRemoval", "journalPath"},
    "inventory": {"fileSeen", "fileContent"}, "content": {"fileContent"},
    "optical": {"systemSetting", "volumeOnDevice", "fileCreated", "fileModified", "volumeRecorded", "unallocatedOnDevice"},
}
# Explicit reviewed USB source observations only. These registry/log strings do
# not establish hardware serials, physical-device identity or device counts.
_USB_SOURCE_ROLES = (
    'usb.device_instance_id', 'usb.device_id', 'usb.instance_id',
    'usb.recorded_time', 'usb.record_time_meaning', 'usb.source_type',
)
KINDS['windows'].update({'attributeSubject', 'attributeTextValue',
                         *(ROLES[role].kind for role in _USB_SOURCE_ROLES)})

# These identify existing reader families, not evidence guarantees or new rules.
RULE_READERS = {
    "R1": {"windows"}, "R3": {"windows"},
    "R4": {"windows", "media", "optical"}, "R5": {"windows"}, "R6": {"windows"},
    "R7": {"media", "optical"}, "R8": {"windows"}, "R9": {"windows"},
    "R10": {"windows", "media", "optical"}, "R11": {"windows"}, "R12": {"windows"},
    "R13": {"media", "optical"}, "R14": {"system"}, "R15": {"system", "webcloud"},
    "R16": {"system"}, "R17": {"system"}, "R18": {"system"}, "R19": {"webcloud"},
    "R20": {"webcloud"}, "R21": {"webcloud"}, "R22": {"webcloud"}, "R23": {"webcloud"},
    "R24": {"filetraces"}, "R25": {"filetraces"}, "R26": {"filetraces", "inventory"},
    "R27": {"filetraces"}, "R28": {"content", "inventory"},
}


def _run(run_dir):
    path = Path(run_dir)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("run directory must already exist and must not be a symlink")
    return path.resolve()


def bind_config(run_dir, config_path, facts_path):
    """Copy trusted intake configuration once, only for its exact bound fact store."""
    run = _run(run_dir)
    cfg = load_config(config_path)
    facts = Path(facts_path)
    if (facts.is_symlink() or not facts.is_file()
            or facts.resolve() != Path(cfg["facts"]["path"]).resolve()
            or sha256_file(facts) != cfg["facts"]["sha256"]):
        raise ValueError("run facts do not match the trusted intake snapshot")
    target = run / "intake-config.json"
    with target.open("xb") as stream:
        stream.write(Path(config_path).read_bytes())
    return {"config": str(target), "snapshot_id": cfg["snapshot_id"],
            "facts": str(facts.resolve()), "facts_sha256": cfg["facts"]["sha256"]}


def catalog(run_dir):
    """Approved reader/exhibit IDs; this function does not inspect image contents."""
    from extractor.build import READER_ORDER, READER_ROLES
    cfg = load_config(_run(run_dir) / "intake-config.json", verify_facts=False)
    selected = {(p["reader"], p["exhibit"]) for p in cfg["selected"]}
    return [{"reader": reader, "exhibit": entry["exhibit"], "role": entry["role"],
             "already_collected": (reader, entry["exhibit"]) in selected,
             "supported_record_kinds": sorted(KINDS.get(reader, ())) }
            for reader in READER_ORDER
            for name, entry in sorted(cfg["manifest"].items()) if not name.startswith("_")
            and entry["role"] in READER_ROLES[reader]]


def _pending(run, *, verify_facts=False):
    latest = run / "latest-collection.json"
    if latest.is_symlink():
        raise ValueError("latest collection receipt must not be a symlink")
    if not latest.exists():
        return None
    receipt = json.loads(latest.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict) or receipt.get("status") not in ("completed", "completed_with_limitations"):
        raise ValueError("invalid pending collection receipt")
    if (run / "evidence-snapshots").is_symlink():
        raise ValueError("evidence snapshot directory must not be a symlink")
    config_path = Path(receipt.get("config", ""))
    if (config_path.name != "intake-config.json" or config_path.parent.parent != run / "evidence-snapshots"
            or config_path.parent.is_symlink()):
        raise ValueError("pending collection points outside this run's snapshots")
    cfg = load_config(config_path, verify_facts=verify_facts)
    original = load_config(run / "intake-config.json", verify_facts=False)
    if (cfg.get("parent_facts") != original["facts"] or receipt.get("facts") != cfg["facts"]["path"]
            or receipt.get("facts_sha256") != cfg["facts"]["sha256"]
            or receipt.get("snapshot_id") != cfg["snapshot_id"]):
        raise ValueError("pending collection does not match the bound parent snapshot")
    return receipt


@contextmanager
def _collection_lock(run):
    marker = run / ".evidence-collection.lock"
    try:
        stream = marker.open("x", encoding="utf-8")
    except FileExistsError:
        raise ValueError("another collection is active or was interrupted; inspect the run before retrying") from None
    try:
        with stream:
            stream.write("Collection in progress. An interrupted request requires operator review.\n")
        yield
    finally:
        marker.unlink()


def recommendations(run_dir, proof_gap=None):
    try:
        available = catalog(run_dir)
        pending = _pending(_run(run_dir))
    except (ValueError, OSError, TypeError):
        return {"status": "unavailable", "catalog": [], "recommendations": [],
                "evidence_needs": [], "reason": "No valid trusted image intake is configured for this run.", "note": NOTE}
    if pending:
        for row in available:
            if row["reader"] == pending["reader"] and row["exhibit"] == pending["exhibit"]:
                row["already_collected"] = True
        return {"status": "diagnostic", "catalog": available, "recommendations": [],
                "evidence_needs": [], "continuation_required": True,
                "pending_collection": pending, "reason": "Continue with the new snapshot before requesting another collection.", "note": NOTE}
    if proof_gap is not None and (not isinstance(proof_gap, dict)
            or proof_gap.get("status") != "diagnostic"
            or not isinstance(proof_gap.get("requirements"), list)):
        return {"status": "diagnostic", "catalog": available, "recommendations": [],
                "evidence_needs": [], "reason": "Supply a checker proof_gap diagnostic, not a claim verdict.", "note": NOTE}
    needs, wanted = [], set()
    for item in (proof_gap or {}).get("requirements", []):
        if not isinstance(item, dict):
            continue
        category = item.get("category")
        readers = set()
        required = item.get("required") if isinstance(item.get("required"), dict) else {}
        if category in ("missing_record", "wrong_record_type"):
            kind = required.get("kind")
            if isinstance(kind, str):
                readers.update(reader for reader, kinds in KINDS.items() if kind in kinds)
            for rule in required.get("rules", []) if isinstance(required.get("rules", []), list) else []:
                if isinstance(rule, str):
                    readers.update(RULE_READERS.get(rule, ()))
        wanted.update(readers)
        needs.append({"category": category, "reason": item.get("reason"),
                      "action": item.get("action"), "candidate_readers": sorted(readers),
                      "requires_review": category not in ("missing_record", "wrong_record_type")})
    suggested = [row for row in available if row["reader"] in wanted and not row["already_collected"]]
    return {"status": "diagnostic", "catalog": available, "recommendations": suggested,
            "evidence_needs": needs, "note": NOTE}


def collect(run_dir, reader, exhibit):
    """Collect one approved pair into a NEW snapshot; never rebind a running agent."""
    with _LOCK:
        try:
            run = _run(run_dir)
            with _collection_lock(run):
                return _collect(run, reader, exhibit)
        except (ValueError, OSError, TypeError) as error:
            return {"status": "rejected", "reason": str(error), "continuation_required": False,
                    "reader": reader, "exhibit": exhibit, "note": NOTE}


def _collect(run, reader, exhibit):
    pending = _pending(run, verify_facts=True)
    if pending:
        if pending["reader"] == reader and pending["exhibit"] == exhibit:
            return dict(pending, reused=True)
        return {"status": "rejected", "continuation_required": True,
                "reason": "A collection is already complete; continue with that snapshot before collecting another reader.",
                "pending_collection": pending, "note": NOTE}
    config = run / "intake-config.json"
    if not config.is_file() or config.is_symlink():
        raise ValueError("no trusted image intake is configured for this run")
    candidates = catalog(run)
    if not isinstance(reader, str) or not isinstance(exhibit, str):
        raise ValueError("reader and exhibit must be configured identifiers")
    chosen = next((row for row in candidates if row["reader"] == reader and row["exhibit"] == exhibit), None)
    if chosen is None:
        raise ValueError("reader/exhibit pair is not in the configured collection catalog")
    if chosen["already_collected"]:
        raise ValueError("this reader/exhibit pair was already collected for the bound snapshot")
    parent = run / "evidence-snapshots"
    if parent.is_symlink():
        raise ValueError("evidence snapshot directory must not be a symlink")
    output = parent / ("collection-" + uuid.uuid4().hex)
    receipt = extend(config, reader, exhibit, output)
    receipt.update(reader=reader, exhibit=exhibit, note=NOTE)
    # Each immutable snapshot keeps its receipt. The latest pointer is a
    # replaceable convenience for the runner, never a fact-store mutation.
    with (output / "collection.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    latest = run / "latest-collection.json"
    if latest.is_symlink():
        raise ValueError("latest collection receipt must not be a symlink")
    temp = run / (".collection-" + uuid.uuid4().hex + ".json")
    with temp.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temp, latest)
    return receipt
