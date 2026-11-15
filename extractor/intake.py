"""Explicit, versioned intake of supported disk images using existing readers.

Each output directory is created once. Hashes bind the bytes examined, not their
original authenticity. Unsupported artifacts and reader failures remain in health.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from extractor.store import Evidence
from extractor.tags import public_policy

FORMATS = {".e01": "ewf", ".dd": "raw", ".raw": "raw", ".img": "raw",
           ".bin": "raw", ".iso": "optical", ".udf": "optical"}
ROLES = {"pc", "removable", "optical"}
_META = {"_source", "_policy", "_time_zone", "_case"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._#()-]{0,79}\Z")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def observation_time(value=None):
    if value is None:
        stamp = datetime.now(timezone.utc)
    else:
        stamp = datetime.fromisoformat(value)
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("examined_at must include an explicit timezone")
    stamp = stamp.astimezone(timezone.utc)
    if stamp.year < 1970:
        raise ValueError("examined_at must not precede the Unix epoch")
    return stamp.isoformat()


def _image_name(name):
    if (not isinstance(name, str) or not name or name in (".", "..")
            or any(c in name for c in ("/", "\\", ":", "\x00"))
            or any(ord(c) < 32 for c in name)):
        raise ValueError("image names must be plain filenames inside the image directory")
    return name


def validated_manifest(images, manifest):
    if not isinstance(images, (str, Path)):
        raise ValueError("an explicit image directory is required")
    root = Path(images).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("images must be a directory")
    if isinstance(manifest, (str, Path)):
        manifest = json.loads(Path(manifest).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("an explicit image/exhibit/role manifest is required")
    result, ids = {}, set()
    for name, entry in manifest.items():
        if name in _META:
            continue
        _image_name(name)
        if name.startswith("_"):
            raise ValueError("underscore-prefixed image names are reserved for manifest metadata")
        if not isinstance(entry, dict) or set(entry) - {"exhibit", "role", "device_serial"}:
            raise ValueError("each image needs only explicit exhibit, role and optional device_serial")
        if entry.get("role") not in ROLES:
            raise ValueError("image role must be pc, removable or optical")
        exhibit = entry.get("exhibit")
        if not isinstance(exhibit, str) or not _ID.fullmatch(exhibit) or exhibit in ids:
            raise ValueError("exhibit IDs must be unique safe identifiers")
        ids.add(exhibit)
        if Path(name).suffix.lower() not in FORMATS:
            raise ValueError("unsupported image extension: " + Path(name).suffix)
        path = root / name
        if path.is_symlink() or not path.is_file() or path.resolve().parent != root:
            raise ValueError("configured image is missing, is not a regular file, or escapes the image directory: " + name)
        if path.stat().st_size == 0:
            raise ValueError("configured image is empty: " + name)
        if "device_serial" in entry and (not isinstance(entry["device_serial"], str)
                or not entry["device_serial"].strip()
                or any(ord(c) < 32 for c in entry["device_serial"])):
            raise ValueError("device_serial must be nonempty public acquisition text")
        result[name] = dict(entry)
    if not result:
        raise ValueError("manifest must configure at least one supported image")
    for key in ("_source", "_case"):
        if key in manifest:
            if not isinstance(manifest[key], str) or not manifest[key].strip():
                raise ValueError(key + " must be nonempty text")
            result[key] = manifest[key]
    if "_time_zone" in manifest:
        if not isinstance(manifest["_time_zone"], str):
            raise ValueError("_time_zone must be an IANA timezone name")
        ZoneInfo(manifest["_time_zone"])
        result["_time_zone"] = manifest["_time_zone"]
    if "_policy" in manifest:
        result["_policy"] = public_policy(manifest["_policy"])
    return root, result


def _segments(root, name):
    """Bind all numeric EWF segments the current reader can open, in order."""
    path = root / name
    if path.suffix.lower() != ".e01":
        return [path]
    from extractor.optical import EWF_MAGIC, ewf_segments
    with path.open("rb") as stream:
        if stream.read(8) not in EWF_MAGIC:
            raise ValueError("configured E01 lacks the supported EWF header: " + name)
    segments = ewf_segments(path)
    numbers = []
    for part in segments:
        _image_name(part.name)
        if part.is_symlink() or not part.is_file() or part.resolve().parent != root:
            raise ValueError("EWF segment is missing or escapes the image directory")
        if part.stat().st_size == 0:
            raise ValueError("EWF segment is empty")
        match = re.fullmatch(r"[Ee](\d{2})", part.suffix[1:])
        if not match:
            raise ValueError("this intake supports numeric E01-E99 segment names only")
        numbers.append(int(match[1]))
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError("EWF segment sequence contains a missing segment")
    return segments


def image_bindings(root, manifest):
    bindings = []
    for name, entry in sorted(manifest.items()):
        if name.startswith("_"):
            continue
        segments = []
        for path in _segments(root, name):
            size = path.stat().st_size
            digest = sha256_file(path)
            if path.stat().st_size != size:
                raise ValueError("image changed while hashing: " + path.name)
            segments.append({"name": path.name, "bytes": size, "sha256": digest})
        bindings.append({"image": name, "exhibit": entry["exhibit"], "role": entry["role"],
                         "format": FORMATS[Path(name).suffix.lower()], "segments": segments})
    return bindings


def load_config(path, *, verify_images=False, verify_facts=True):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("trusted intake configuration is missing or a symlink")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict) or cfg.get("schema_version") != 1:
        raise ValueError("unsupported intake configuration")
    checksum = cfg.get("config_sha256")
    if checksum != _digest({k: v for k, v in cfg.items() if k != "config_sha256"}):
        raise ValueError("intake configuration digest mismatch")
    root, manifest = validated_manifest(cfg.get("images_root"), cfg.get("manifest"))
    if str(root) != cfg.get("images_root"):
        raise ValueError("configured image directory changed or is no longer canonical")
    from extractor.build import READER_ROLES
    by_id = {e["exhibit"]: e for n, e in manifest.items() if not n.startswith("_")}
    pairs = cfg.get("selected")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("intake configuration has no approved extraction selection")
    seen = set()
    for item in pairs:
        if not isinstance(item, dict) or set(item) != {"reader", "exhibit"}:
            raise ValueError("invalid configured reader selection")
        reader, exhibit = item["reader"], item["exhibit"]
        if (not isinstance(reader, str) or reader not in READER_ROLES
                or not isinstance(exhibit, str) or exhibit not in by_id
                or by_id[exhibit]["role"] not in READER_ROLES[reader]):
            raise ValueError("unsupported configured reader/exhibit selection")
        if (reader, exhibit) in seen:
            raise ValueError("duplicate configured reader/exhibit selection")
        seen.add((reader, exhibit))
    facts = cfg.get("facts", {})
    fact_path = Path(facts.get("path", ""))
    if not fact_path.is_absolute() or fact_path.is_symlink() or not fact_path.is_file():
        raise ValueError("configured full facts snapshot is missing or unsafe")
    if verify_facts and sha256_file(fact_path) != facts.get("sha256"):
        raise ValueError("facts snapshot differs from the intake binding")
    if verify_images and image_bindings(root, manifest) != cfg.get("images"):
        raise ValueError("image bytes or segment set differ from the intake binding")
    return cfg


def _base_evidence(path):
    from checker.facts import Fact
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    strings = data["strings"]
    ev, seen, derived_tags = Evidence(), set(), 0
    for row in data["facts"]:
        fact = Fact(row["id"], row["kind"], row["t"], row["res"], row["obj"], row["aux"], row.get("prov", {}))
        if fact.id in seen:
            raise ValueError("duplicate record ID in prior snapshot")
        seen.add(fact.id)
        # Aggregate tags describe the evidence set at derivation time. Adding
        # source observations can invalidate them, so only these derived rows
        # are rebuilt; source observations and other tags retain their values.
        if fact.kind == "tag" and fact.prov.get("source") == "deterministic":
            derived_tags += 1
            continue
        ev.add(fact.kind, fact.t, fact.res, "" if fact.obj == 0 else strings[str(fact.obj)],
               "" if fact.aux == 0 else strings[str(fact.aux)], **fact.prov)
    meta = data.get("_meta", {})
    ev.problems.extend(meta.get("unparsed", []))
    return ev, meta, derived_tags


def _snapshot(root, manifest, output, *, case, examined_at, images, selected,
              requested=None, previous=None):
    from extractor.build import extract
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    snapshot_id = "evidence-" + uuid.uuid4().hex
    parent = previous.get("facts") if previous else None
    ev, previous_meta, derived_tags = _base_evidence(parent["path"]) if parent else (None, {}, 0)
    ev, metadata, log = extract(root, manifest, case=case, examined_at=examined_at,
                                selected=requested if requested is not None else selected,
                                evidence=ev, previous_meta=previous_meta,
                                manifest_source="trusted explicit intake manifest")
    facts_path = output / "facts.json"
    # Reading is complete before output becomes a configured snapshot.
    if image_bindings(root, manifest) != images:
        raise ValueError("image bytes changed during extraction; snapshot was not published")
    if parent and sha256_file(parent["path"]) != parent["sha256"]:
        raise ValueError("parent facts changed during extraction; snapshot was not published")
    metadata.update(snapshot_id=snapshot_id, parent_facts=parent,
                    selected_readers=selected, source_images=images)
    if parent:
        metadata["derived_tag_refresh"] = {
            "discarded_parent_tags": derived_tags,
            "recomputed_tags": sum(kind == "tag" and json.loads(prov).get("source") == "deterministic"
                                   for kind, _t, _res, _obj, _aux, prov in ev.rows()),
            "scope": "Only tag records whose provenance source is deterministic are refreshed from the combined source observations."}
    meta = ev.write_json(facts_path, metadata)
    binding = {"path": str(facts_path), "sha256": sha256_file(facts_path),
               "bytes": facts_path.stat().st_size}
    cfg = {"schema_version": 1, "snapshot_id": snapshot_id, "case": case,
           "created_at": datetime.now(timezone.utc).isoformat(), "examined_at": examined_at,
           "images_root": str(root), "manifest": manifest, "images": images,
           "selected": selected, "facts": binding, "parent_facts": parent,
           "parent_snapshot_id": previous.get("snapshot_id") if previous else None,
           "limitation": "Hashes bind supplied bytes, not original authenticity or extraction completeness. New snapshots require new proofs; fact IDs may change."}
    cfg["config_sha256"] = _digest(cfg)
    health = {"schema_version": 1, "snapshot_id": snapshot_id,
              "status": "completed_with_limitations" if meta["unparsed"] else "completed",
              "fact_count": meta["facts"], "by_kind": meta["by_kind"],
              "reader_attempts": meta["reader_attempts"], "issues": meta["unparsed"],
              "facts": binding, "parent_facts": parent,
              "scope": "Only configured readers and available artifacts; zero records do not prove absence."}
    if parent:
        health["derived_tag_refresh"] = metadata["derived_tag_refresh"]
    _write(output / "intake-config.json", cfg)
    _write(output / "health.json", health)
    with (output / "extraction.log").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(log + meta["unparsed"]) + "\n")
    return {"status": health["status"], "snapshot_id": snapshot_id,
            "facts": str(facts_path), "facts_sha256": binding["sha256"],
            "config": str(output / "intake-config.json"),
            "config_sha256": cfg["config_sha256"], "health": str(output / "health.json"),
            "fact_count": meta["facts"], "issues": len(meta["unparsed"]),
            "parent_facts": parent, "continuation_required": previous is not None}


def intake(images, manifest, output_dir, *, case="Supplied case", examined_at=None, readers=None):
    """Validate explicit images and write a new immutable-by-convention snapshot."""
    from extractor.build import selection
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise FileExistsError("intake output already exists")
    root, manifest = validated_manifest(images, manifest)
    if not isinstance(case, str) or not case.strip():
        raise ValueError("case must be nonempty text")
    selected = selection(manifest, readers)
    if not selected:
        raise ValueError("no configured exhibit supports the requested readers")
    bindings = image_bindings(root, manifest)
    return _snapshot(root, manifest, output, case=case, examined_at=observation_time(examined_at),
                     images=bindings, selected=selected)


def extend(config, reader, exhibit, output_dir):
    """Internal bounded collection: one allowlisted pair plus the prior full snapshot."""
    from extractor.build import READER_ROLES
    cfg = load_config(config, verify_images=True)
    entries = {e["exhibit"]: e for n, e in cfg["manifest"].items() if not n.startswith("_")}
    if (not isinstance(reader, str) or reader not in READER_ROLES
            or not isinstance(exhibit, str) or exhibit not in entries
            or entries[exhibit]["role"] not in READER_ROLES[reader]):
        raise ValueError("reader/exhibit pair is not in the configured collection catalog")
    pair = {"reader": reader, "exhibit": exhibit}
    if pair in cfg["selected"]:
        raise ValueError("this reader/exhibit pair was already collected for the snapshot")
    selected = cfg["selected"] + [pair]
    return _snapshot(Path(cfg["images_root"]), cfg["manifest"], output_dir,
                     case=cfg["case"], examined_at=observation_time(), images=cfg["images"],
                     selected=selected, requested=[pair], previous=cfg)
