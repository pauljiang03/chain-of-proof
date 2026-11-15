"""Bounded selection of explicit historical filesystem sources.

This module returns observations, not actor/transfer claims or proof verdicts.
Callers own image opening and fact publication. No source is selected by time.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID

from .source_scope import merge_scope, vss_snapshot


class SourceSelectionError(ValueError):
    """The requested identity does not select one completely inventoried source."""


class LimitExceeded(ValueError):
    """An explicit resource limit prevented complete observation."""


class UnsupportedSource(ValueError):
    """A source cannot safely be interpreted by this bounded reader."""


class _PathAbsent(FileNotFoundError):
    pass


@dataclass(frozen=True)
class Limits:
    max_volumes: int = 16
    max_catalog_entries: int = 256
    max_sources: int = 64
    max_files: int = 32
    max_file_bytes: int = 64 * 1024 * 1024
    max_total_bytes: int = 256 * 1024 * 1024
    max_metadata_bytes: int = 16 * 1024 * 1024
    max_io_bytes: int = 512 * 1024 * 1024
    max_read_calls: int = 100_000
    max_path_components: int = 128
    max_optical_entries: int = 100_000

    def __post_init__(self):
        if any(type(value) is not int or value <= 0 for value in asdict(self).values()):
            raise ValueError("historical-source limits must be positive integers")


@dataclass
class _Budget:
    limit: int
    calls_limit: int
    used: int = 0
    calls: int = 0

    def reserve(self, count):
        if type(count) is not int or count < 0:
            raise LimitExceeded("unbounded stream reads are not supported")
        if self.used + count > self.limit or self.calls >= self.calls_limit:
            raise LimitExceeded("underlying source read budget exhausted")
        # Charge requested bytes, including short/failed reads, to bound attempts.
        self.used += count
        self.calls += 1


class _BoundedStream:
    """Seekable non-owning view; never closes the caller's evidence stream."""

    def __init__(self, stream, budget):
        self.stream, self.budget = stream, budget

    def read(self, count=-1):
        self.budget.reserve(count)
        data = self.stream.read(count)
        if not isinstance(data, (bytes, bytearray)) or len(data) > count:
            raise OSError("source returned an invalid read")
        return data

    def readinto(self, buf):
        data = self.read(len(buf))
        buf[:len(data)] = data
        return len(data)

    def seek(self, offset, whence=0):
        return self.stream.seek(offset, whence)

    def tell(self):
        return self.stream.tell()

    def seekable(self):
        return True

    def readable(self):
        return True

    def close(self):
        pass


@dataclass
class _Source:
    metadata: dict
    store: object
    volume: object
    bounded: _BoundedStream


@dataclass
class VssInventory:
    common: dict
    limits: Limits
    sources: list = field(default_factory=list)
    volumes: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    complete: bool = True

    def as_dict(self):
        return copy.deepcopy(dict(schema_version=1, kind="vss_inventory",
            complete=self.complete, sources=[source.metadata for source in self.sources],
            volumes=self.volumes, issues=self.issues, limits=asdict(self.limits)))


def _common(common, expected):
    resolved = merge_scope(common)
    if any(not isinstance(resolved.get(key), str) or not resolved[key].strip()
           for key in ("image", "exhibit")):
        raise ValueError("explicit image and exhibit identity are required")
    if resolved["source_snapshot"] != expected or resolved["source_variant"] == "unknown":
        raise ValueError("explicit unmixed " + expected + " source scope is required")
    return resolved


def _uint(value, name, *, positive=False, bits=64):
    if not isinstance(value, int) or isinstance(value, bool) or not (int(positive) <= value < 2 ** bits):
        raise ValueError(name + " must be an unsigned integer" + (" greater than zero" if positive else ""))
    return int(value)


def _filetime(value):
    value = _uint(value, "FILETIME")
    # Keep all seven FILETIME fractional digits; do not use binary floating point.
    seconds, fraction = divmod(value, 10_000_000)
    stamp = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S") + f".{fraction:07d}Z"


def _status(error):
    if isinstance(error, LimitExceeded):
        return "limit_exceeded"
    if isinstance(error, (UnsupportedSource, NotImplementedError, ImportError)):
        return "unsupported"
    return "unreadable"


def _failure(error):
    return dict(status=_status(error), error_type=type(error).__name__, detail=str(error))


def _parse_vss(stream, limits):
    """Preflight every catalog block before Dissect's eager catalog construction.

    Dissect's read_block follows linked blocks without a cycle/count limit. The
    preflight bounds entries and links, validates complete blocks, and rejects
    cycles before that routine runs. A shared byte/call budget also bounds reads
    from later lazy store block maps. None of this copies an image.
    """
    from dissect.volume import vss
    stream.seek(vss.VOLUME_HEADER_OFFSET)
    header = vss.c_vss.volume_header(stream)
    if header.identifier != vss.VSS_IDENTIFIER:
        return None
    offset = int(header.catalog_offset)
    if not offset:
        return None
    seen, entries, ended = set(), 0, False
    while offset:
        if offset in seen:
            raise UnsupportedSource("cyclic VSS catalog block chain")
        if len(seen) >= limits.max_catalog_entries:
            raise LimitExceeded("VSS catalog block limit exhausted")
        seen.add(offset)
        block_header, data = vss.read_block_data(stream, offset, vss.c_vss.catalog_header)
        if len(data) != vss.BLOCK_SIZE - 128:
            raise OSError("truncated VSS catalog block")
        for position in range(0, len(data), vss.CATALOG_ENTRY_SIZE):
            kind = int.from_bytes(data[position:position + 8], "little")
            if kind == 0:
                ended = True
                continue
            # Dissect stops processing at the first empty entry. Padding across
            # later linked blocks is normal, but hidden later entries are not.
            if ended:
                raise UnsupportedSource("VSS catalog contains entries after an empty entry")
            entries += 1
            if entries > limits.max_catalog_entries:
                raise LimitExceeded("VSS catalog entry limit exhausted")
            if kind not in (1, 2, 3):
                raise UnsupportedSource("unsupported VSS catalog entry type")
        offset = int(block_header.next_offset)
    return vss.VSS(stream)


def discover_vss(target, common, *, limits=None):
    """Inventory catalog/store-header metadata on explicitly identified base bytes.

    Does not open snapshot content. The caller's target and streams stay open.
    Incomplete discovery is reported and cannot support unambiguous selection.
    """
    limits = limits or Limits()
    result = VssInventory(_common(common, "base-volume"), limits)
    mounts = getattr(target.fs, "mounts", {})
    seen = set()
    budget = _Budget(limits.max_metadata_bytes, limits.max_read_calls)
    for fs in target.filesystems:
        if getattr(fs, "__type__", "") != "ntfs" or id(fs) in seen:
            continue
        if len(seen) >= limits.max_volumes:
            result.complete = False
            result.issues.append(_failure(LimitExceeded("NTFS volume inventory limit exhausted")))
            break
        seen.add(id(fs))
        drives = sorted({name.upper() for name, mounted in mounts.items()
                         if mounted is fs and re.fullmatch(r"[A-Za-z]:", name)})
        volume = dict(drive=drives[0] if len(drives) == 1 else None, mounted_drives=drives)
        try:
            serial = _uint(fs.ntfs.serial, "NTFS serial")
            volume.update(ntfs_volume_serial=f"{serial:016X}", volume_serial=f"{serial & 0xffffffff:08X}")
            for key in ("offset", "size", "number"):
                value = getattr(fs.volume, key, None)
                if type(value) is int and value >= 0:
                    volume["volume_" + key] = value
            stream = _BoundedStream(fs.volume, budget)
            parsed = _parse_vss(stream, limits)
            if parsed is None:
                result.volumes.append(dict(volume, status="absent", detail="No VSS signature/catalog in examined volume header"))
                continue
            volume.update(vss_volume_uuid=str(UUID(str(parsed.volume_identifier))),
                          vss_store_volume_uuid=str(UUID(str(parsed.store_volume_identifier))))
            identity = json.dumps([result.common["image"], result.common["exhibit"], volume],
                                  sort_keys=True, separators=(",", ":"))
            volume["volume_identity"] = identity
            for store in parsed.catalog.stores:
                if len(result.sources) >= limits.max_sources:
                    raise LimitExceeded("VSS source inventory limit exhausted")
                store_uuid = UUID(bytes_le=bytes(store.desc2.store_identifier))
                if bytes(store.desc3.store_identifier) != store_uuid.bytes_le:
                    raise ValueError("VSS catalog descriptors refer to different stores")
                copy_uuid, set_uuid = UUID(str(store.copy_identifier)), UUID(str(store.copy_set_identifier))
                created = _uint(store.desc2.creation_time, "VSS creation FILETIME")
                if created != store.creation_time:
                    raise ValueError("VSS creation time differs from linked catalog descriptor")
                catalog_offset = _uint(parsed.header.catalog_offset, "catalog offset", positive=True)
                header_offset = _uint(store.desc3.store_header_offset, "store header offset", positive=True)
                meta = dict(snapshot_id=vss_snapshot(copy_uuid), copy_uuid=str(copy_uuid),
                    store_uuid=str(store_uuid), set_uuid=str(set_uuid), creation_filetime=created,
                    created_at=_filetime(created), volume=dict(volume),
                    provenance=dict(result.common, parser="extractor.historical_sources.vss_catalog",
                        catalog_offset=catalog_offset, store_header_offset=header_offset,
                        source_record_type="VSS catalog descriptors and linked store information",
                        time_meaning="VSS catalog creation FILETIME; not a file creation or transfer time",
                        metadata_scope="base-volume catalog/header; snapshot content not opened"))
                result.sources.append(_Source(meta, store, fs.volume, stream))
            result.volumes.append(dict(volume, status="present"))
        except Exception as error:
            result.complete = False
            issue = dict(volume=volume, **_failure(error))
            result.issues.append(issue)
            result.volumes.append(dict(volume, **_failure(error)))
    result.sources.sort(key=lambda source: (source.metadata["volume"]["volume_identity"],
                                             source.metadata["copy_uuid"], source.metadata["store_uuid"]))
    if not seen:
        result.complete = False
        result.issues.append(_failure(UnsupportedSource("VSS inventory requires an NTFS filesystem; none is exposed by this target")))
    return result


def select_vss(inventory, snapshot_id, *, volume_identity=None):
    """Select exactly one copy UUID; never infer latest/earliest from ordering."""
    if not isinstance(inventory, VssInventory):
        raise TypeError("a VssInventory is required")
    if not inventory.complete:
        raise SourceSelectionError("VSS discovery is incomplete; uniqueness cannot be established")
    if not isinstance(snapshot_id, (str, UUID)):
        raise SourceSelectionError("an explicit VSS copy UUID is required")
    try:
        value = str(snapshot_id)
        identity = vss_snapshot(value[4:] if value.startswith("vss:") else value)
    except ValueError as error:
        raise SourceSelectionError("an explicit VSS copy UUID is required; time aliases are unsupported") from error
    matches = [source for source in inventory.sources if source.metadata["snapshot_id"] == identity
               and (volume_identity is None or source.metadata["volume"]["volume_identity"] == volume_identity)]
    if not matches:
        raise SourceSelectionError("requested VSS copy UUID/volume is absent from the complete inventory")
    if len(matches) != 1:
        raise SourceSelectionError("VSS copy UUID is ambiguous; supply an exact unique volume_identity")
    return matches[0]


def _paths(paths, limits):
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("a nonempty explicit list of drive-qualified paths is required")
    if len(paths) > limits.max_files:
        raise LimitExceeded("requested path count exceeds max_files")
    normalized = []
    for path in paths:
        if not isinstance(path, str) or not re.fullmatch(r"[A-Za-z]:\\[^\x00-\x1f]+", path):
            raise ValueError("each path must be explicitly drive-qualified with backslash separators")
        parts = path[3:].split("\\")
        if (len(parts) > limits.max_path_components or len(path) > 32767
                or any(not part or part in (".", "..") or any(c in part for c in '/:*?<>|"') for part in parts)):
            raise ValueError("invalid, wildcard, stream, relative or overlong file path")
        normalized.append(path[0].upper() + path[1:])
    if len({path.casefold() for path in normalized}) != len(normalized):
        raise ValueError("duplicate paths are not allowed")
    return normalized


def _open_ntfs(stream):
    from dissect.ntfs import NTFS
    return NTFS(stream)


def _record(ntfs, path):
    # Resolve the actual directory index references and verify sequence numbers.
    # Mft.get(path) follows junctions and does not itself check those sequences.
    record = ntfs.mft.root
    for part in path[3:].split("\\"):
        if record.is_reparse_point():
            raise UnsupportedSource("reparse point in selected path; cross-source traversal refused")
        if not int(record.header.Flags) & 1:
            raise UnsupportedSource("unallocated/deleted MFT record; allocated-path comparison unavailable")
        if not record.is_dir():
            raise UnsupportedSource("selected path has a non-directory ancestor")
        try:
            entry = record.index("$I30").search(part)
        except KeyError as error:
            raise _PathAbsent(path) from error
        record = entry.dereference()
        ref = entry.header.FileReference
        segment = int(ref.SegmentNumberLowPart) | (int(ref.SegmentNumberHighPart) << 32)
        if record.segment != segment or int(record.header.SequenceNumber) != int(ref.SequenceNumber):
            raise UnsupportedSource("directory index reference resolves to a different MFT sequence/record")
    if record.is_reparse_point():
        raise UnsupportedSource("reparse point in selected path; cross-source traversal refused")
    if not int(record.header.Flags) & 1:
        raise UnsupportedSource("unallocated/deleted MFT record; allocated-path comparison unavailable")
    if not record.is_file():
        raise UnsupportedSource("selected path is not a regular file")
    return record


def _stat(record):
    size = _uint(record.size(), "file size")
    attr = record.attributes.STANDARD_INFORMATION.attr
    times = {key: _uint(getattr(attr, field), "NTFS " + field) for key, field in (
        ("created", "CreationTime"), ("modified", "LastModificationTime"),
        ("record_changed", "LastChangeTime"), ("accessed", "LastAccessTime"))}
    return dict(size=size, mft_segment=int(record.segment), mft_sequence=int(record.header.SequenceNumber),
                allocated=True, timestamps_filetime=times,
                timestamps_utc={key: _filetime(value) for key, value in times.items()},
                timestamp_source="$STANDARD_INFORMATION; file metadata, not snapshot or transfer time")


def _observe(ntfs, path, provenance, limits, content_budget):
    result = dict(path=path, provenance=dict(provenance, source_path=path, source_stream="::$DATA"))
    try:
        try:
            record = _record(ntfs, path)
        except _PathAbsent:
            return dict(result, status="absent", detail="path not present in this selected filesystem namespace")
        stat = _stat(record)
        result["stat"] = stat
        size = stat["size"]
        if size > limits.max_file_bytes or content_budget[0] + size > limits.max_total_bytes:
            raise LimitExceeded("file content byte limit exhausted")
        digest, received = hashlib.sha256(), 0
        stream = record.open()
        try:
            while received < size:
                count = min(1024 * 1024, size - received)
                chunk = stream.read(count)
                if not isinstance(chunk, (bytes, bytearray)) or not chunk or len(chunk) > count:
                    raise OSError("file stream is truncated or returned an invalid read")
                received += len(chunk)
                content_budget[0] += len(chunk)
                digest.update(chunk)
            # Do not add an extra byte beyond a declared resource cap. NTFS's
            # stream length and metadata must still agree after the complete read.
            if _stat(record) != stat:
                raise OSError("file metadata changed during content read")
        finally:
            stream.close()
        result.update(status="present", bytes_read=received, sha256=digest.hexdigest(),
                      hash_scope="complete logical unnamed data stream; no slack or alternate streams")
    except Exception as error:
        result.update(_failure(error))
    return result


def compare_versions(inventory, snapshot_id, paths, *, volume_identity=None):
    """Read/hash each explicit path in base plus one explicitly selected VSS copy.

    Returns JSON-safe observations and a same/different-content result only when
    both complete logical streams were read. Equality never implies direction,
    actor, causation or transfer. Absence never means deletion was established.
    """
    source = select_vss(inventory, snapshot_id, volume_identity=volume_identity)
    limits = inventory.limits
    paths = _paths(paths, limits)
    volume = source.metadata["volume"]
    if volume["drive"] is None or any(path[:2] != volume["drive"] for path in paths):
        raise SourceSelectionError("paths must address the selected volume's single explicit drive mapping")
    # Separate operation budget; shared across base and snapshot, including all
    # lazy snapshot reconstruction and metadata reads, not just returned content.
    budget = _Budget(limits.max_io_bytes, limits.max_read_calls)
    source.bounded.budget = budget
    origin = dict(inventory.common, volume=copy.deepcopy(volume), parser="extractor.historical_sources.ntfs")
    sides = [("base", dict(origin, source_snapshot="base-volume")),
             ("snapshot", dict(origin, source_snapshot=source.metadata["snapshot_id"],
                               copy_uuid=source.metadata["copy_uuid"], store_uuid=source.metadata["store_uuid"],
                               set_uuid=source.metadata["set_uuid"]))]
    report = dict(schema_version=1, kind="vss_file_version_comparison", selected_source=copy.deepcopy(source.metadata),
                  paths=[], limits=asdict(limits), interpretation="Observed content versions only; no actor, transfer direction or deletion event inferred")
    content_budget, observed = [0], {}
    for side, provenance in sides:
        snapshot_stream = None
        try:
            if side == "base":
                ntfs = _open_ntfs(_BoundedStream(source.volume, budget))
            else:
                if volume["vss_volume_uuid"] != volume["vss_store_volume_uuid"]:
                    raise UnsupportedSource("VSS storage on a different volume requires an explicit cross-volume binding")
                snapshot_stream = source.store.open()
                ntfs = _open_ntfs(_BoundedStream(snapshot_stream, budget))
            if f"{_uint(ntfs.serial, 'opened NTFS serial'):016X}" != volume["ntfs_volume_serial"]:
                raise UnsupportedSource("opened filesystem serial differs from selected source volume")
            observed[side] = [_observe(ntfs, path, provenance, limits, content_budget) for path in paths]
        except Exception as error:
            observed[side] = [dict(path=path, provenance=dict(provenance, source_path=path), **_failure(error))
                              for path in paths]
        finally:
            if snapshot_stream is not None:
                snapshot_stream.close()
    for base, snapshot in zip(observed["base"], observed["snapshot"]):
        complete = base["status"] == snapshot["status"] == "present"
        comparison = ("same_content" if (base["sha256"], base["bytes_read"]) ==
                      (snapshot["sha256"], snapshot["bytes_read"]) else "different_content") if complete else "not_comparable"
        report["paths"].append(dict(path=base["path"], base=base, snapshot=snapshot, comparison=comparison))
    report["usage"] = dict(content_bytes=content_budget[0], requested_io_bytes=budget.used, read_calls=budget.calls)
    return report


@dataclass
class OpticalSource:
    """An exact UDF descriptor selection in a caller-owned, already parsed survey."""
    metadata: dict
    version: object


@dataclass
class OpticalInventory:
    sources: list
    limits: Limits
    issues: list = field(default_factory=list)
    complete: bool = True

    def as_dict(self):
        return copy.deepcopy(dict(schema_version=1, kind="optical_descriptor_inventory",
            complete=self.complete, sources=[source.metadata for source in self.sources],
            issues=self.issues, limits=asdict(self.limits), session_selection=optical_session_capability()))


def optical_session_capability():
    """An audited, specific capability gap; session ordinals are not snapshots."""
    return dict(status="unsupported", capability="select coherent historical filesystem by optical session number",
        audited_source=["extractor.optical.ewf_sessions", "extractor.optical.Udf._versions",
                        "extractor.optical.Survey.session"],
        reason="EWF session metadata supplies flags and start sectors. Udf._versions reconstructs states by VAT and FSD sectors, not session ordinals. Survey.session associates sector positions with acquisition starts; it does not reconstruct a session-specific descriptor sequence.",
        supported_alternative="Explicit VAT/FSD descriptor identity in an already parsed UDF survey")


def discover_optical(survey, common, *, limits=None):
    """Index retained UDF states without initiating an image scan or content read.

    ``optical.survey`` currently scans the disc to discover descriptors. Its prior
    work is outside this API's bounds. Admission here is limited by source count,
    retained directory-entry count and retained VAT metadata bytes. A partial
    survey is never silently upgraded to a complete namespace.
    """
    from .optical import parse_fsd, udf_serial32
    limits = limits or Limits()
    common = _common(common, "optical-image")
    result = OpticalInventory([], limits)
    udf = survey.udf
    try:
        if len(udf.versions) > limits.max_sources:
            raise LimitExceeded("optical descriptor source count exceeds max_sources")
        if len(udf.entries) > limits.max_optical_entries:
            raise LimitExceeded("optical retained file entries exceed max_optical_entries")
        total_entries = total_metadata = 0
        for index, version in enumerate(udf.versions):
            total_entries += len(version.files) + len(version.nameless)
            if total_entries > limits.max_optical_entries:
                raise LimitExceeded("optical namespace entries exceed max_optical_entries")
            fsd = _uint(version.fsd_sector, "file set descriptor sector")
            vat = None if version.vat_sector is None else _uint(version.vat_sector, "VAT sector")
            if vat is None and version.vat is not None:
                raise UnsupportedSource("UDF allocation table lacks its descriptor sector identity")
            if vat is not None:
                entry = udf.entries.get(vat)
                if entry is None or not udf._is_vat(entry) or version.vat is None:
                    raise UnsupportedSource("UDF VAT sector does not identify the retained VAT entry")
                total_metadata += 4 * len(version.vat.entries)
            raw = udf.fsd_copies.get(fsd)
            if not isinstance(raw, bytes) or len(raw) != 512:
                raise UnsupportedSource("selected UDF state lacks retained file set descriptor bytes")
            total_metadata += len(raw)
            if total_metadata > limits.max_metadata_bytes:
                raise LimitExceeded("optical retained descriptor metadata exceeds max_metadata_bytes")
            parse_fsd(raw)  # Recheck checksum/CRC and descriptor type.
            if version.serial != udf_serial32(raw) or version.fsd is None:
                raise UnsupportedSource("UDF version serial/descriptor linkage is inconsistent")
            if any(item.version != index for item in version.files):
                raise UnsupportedSource("UDF file list contains mixed version identities")
            if version.recorded is not None and (not isinstance(version.recorded, bytes) or len(version.recorded) != 12):
                raise UnsupportedSource("UDF recorded timestamp is not an exact 12-byte timestamp field")
            descriptor_id = f"udf:vat={vat if vat is not None else 'none'}:fsd={fsd}"
            metadata = dict(descriptor_id=descriptor_id, vat_sector=vat, fsd_sector=fsd,
                fsd_sha256=hashlib.sha256(raw).hexdigest(), volume_serial=f"{version.serial:08X}",
                retained_files=len(version.files), deleted_entries=sum(bool(item.deleted) for item in version.files),
                nameless_deleted_entries=len(version.nameless),
                recorded_timestamp_hex=version.recorded.hex() if version.recorded is not None else None,
                provenance=dict(common, source_variant=descriptor_id,
                    parser="extractor.optical.Udf._versions", source_record_type="explicit VAT/FSD descriptor state",
                    time_meaning="raw VAT file-entry modification timestamp, when available; not a session or transfer time",
                    artifact=f"UDF VAT sector {vat}; file set descriptor sector {fsd}"))
            result.sources.append(OpticalSource(metadata, version))
        if udf.problems:
            result.complete = False
            for location, error in udf.problems[:limits.max_catalog_entries]:
                result.issues.append(dict(location=location, **_failure(error)))
            if len(udf.problems) > limits.max_catalog_entries:
                result.issues.append(_failure(LimitExceeded("additional optical issues omitted by limit")))
    except Exception as error:
        result.complete = False
        result.issues.append(_failure(error))
    result.sources.sort(key=lambda source: source.metadata["descriptor_id"])
    return result


def select_optical(inventory, descriptor_id):
    """Select one exact VAT/FSD identity, never a time, ordinal or latest alias."""
    if not isinstance(inventory, OpticalInventory):
        raise TypeError("an OpticalInventory is required")
    if not inventory.complete:
        raise SourceSelectionError("optical discovery is incomplete; namespace/source completeness is unavailable")
    if not isinstance(descriptor_id, str) or not re.fullmatch(r"udf:vat=(?:none|[0-9]+):fsd=[0-9]+", descriptor_id):
        raise SourceSelectionError("an explicit udf:vat=<sector|none>:fsd=<sector> identity is required")
    matches = [source for source in inventory.sources if source.metadata["descriptor_id"] == descriptor_id]
    if len(matches) != 1:
        raise SourceSelectionError("optical descriptor identity is absent or ambiguous")
    return matches[0]


def _file_identity(path):
    """Filesystem identity only: deliberately does not hash an image/segment."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("input must be an existing regular file, not a symlink: " + str(path))
    stat = path.stat()
    if not stat.st_size:
        raise ValueError("input file is empty: " + str(path))
    return dict(name=path.name, path=str(path), bytes=stat.st_size, device=stat.st_dev,
                inode=stat.st_ino, modified_ns=stat.st_mtime_ns, changed_ns=stat.st_ctime_ns)


def _input_receipt(image, exhibit, config_path=None, *, config_limit=16 * 1024 * 1024):
    """Bind names/stats; optionally retain checked but unrecomputed intake hashes."""
    from pathlib import Path
    from .intake import FORMATS, _digest, _segments
    if image.suffix.lower() not in FORMATS:
        raise ValueError("unsupported image extension: " + image.suffix)
    parts = _segments(image.parent, image.name)
    identity = dict(image=str(image), exhibit=exhibit, format=FORMATS[image.suffix.lower()],
                    segments=[dict(_file_identity(part), content_sha256=None,
                                   content_hash_status="not_recomputed") for part in parts],
                    identity_scope="canonical paths and filesystem stats; full image/segment content not hashed by this command")
    if config_path is None:
        return identity
    config_path = Path(config_path).absolute()
    config_stat = _file_identity(config_path)
    if config_stat["bytes"] > config_limit:
        raise LimitExceeded("intake configuration exceeds metadata byte limit")
    with config_path.open("rb") as stream:
        raw = stream.read(config_limit + 1)
    if len(raw) > config_limit or _file_identity(config_path) != config_stat:
        raise ValueError("intake configuration changed while reading or exceeds its byte limit")
    config = json.loads(raw)
    if (not isinstance(config, dict) or config.get("schema_version") != 1
            or config.get("config_sha256") != _digest({key: value for key, value in config.items() if key != "config_sha256"})):
        raise ValueError("intake configuration schema or digest is invalid")
    manifest = config.get("manifest", {})
    if (config.get("images_root") != str(image.parent) or not isinstance(manifest, dict)
            or not isinstance(manifest.get(image.name), dict)
            or manifest[image.name].get("exhibit") != exhibit):
        raise ValueError("intake configuration does not bind the explicit image path and exhibit")
    bindings = config.get("images")
    if not isinstance(bindings, list):
        raise ValueError("intake configuration has no image bindings")
    matches = [entry for entry in bindings if isinstance(entry, dict) and entry.get("image") == image.name]
    if len(matches) != 1 or matches[0].get("exhibit") != exhibit:
        raise ValueError("intake image binding is missing, ambiguous, or names another exhibit")
    declared = matches[0].get("segments")
    if (not isinstance(declared, list) or any(not isinstance(entry, dict) for entry in declared)
            or [(entry.get("name"), entry.get("bytes")) for entry in declared]
            != [(entry["name"], entry["bytes"]) for entry in identity["segments"]]):
        raise ValueError("current image segment names/sizes differ from the intake declaration")
    for observed, entry in zip(identity["segments"], declared):
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError("intake segment declaration lacks a valid SHA-256")
        observed.update(content_sha256=digest.lower(), content_hash_status="declared_by_intake_not_recomputed")
    identity["intake_config"] = dict(config_stat, file_sha256=hashlib.sha256(raw).hexdigest(),
        file_hash_status="recomputed", config_sha256=config["config_sha256"],
        snapshot_id=config.get("snapshot_id"),
        validation_scope="configuration JSON digest and image/exhibit/segment names and sizes checked; segment content hashes not recomputed; facts not read")
    return identity


def _code_receipt():
    from importlib.metadata import PackageNotFoundError, version
    from pathlib import Path
    path = Path(__file__).resolve()
    dependencies = {}
    for name in ("dissect.target", "dissect.ntfs", "dissect.volume"):
        try:
            dependencies[name] = version(name)
        except PackageNotFoundError:
            dependencies[name] = None
    return dict(module="extractor.historical_sources", path=str(path),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), hash_status="recomputed",
                hash_scope="this module source file on disk only; dependency code excluded",
                dependency_versions=dependencies)


def _target_open(path):
    from dissect.target import Target
    return Target.open(path)


def main(argv=None):
    """Standalone explicit VSS discovery/comparison; writes only a new JSON report."""
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Observe explicit VSS sources or file versions; this does not produce a proof verdict.")
    commands = parser.add_subparsers(dest="command", required=True)

    def copy_uuid(value):
        try:
            return str(UUID(value[4:] if value.startswith("vss:") else value))
        except ValueError as error:
            raise argparse.ArgumentTypeError("an explicit copy UUID is required; latest/time aliases are unsupported") from error

    defaults = asdict(Limits())
    exposed_limits = tuple(name for name in defaults if name != "max_optical_entries")
    for command in ("discover", "compare"):
        sub = commands.add_parser(command, help="inventory catalog metadata" if command == "discover" else "compare explicit paths in base and one copy")
        sub.add_argument("--image", required=True, help="explicit raw image or first E01 segment")
        sub.add_argument("--exhibit", required=True, help="explicit exhibit identity")
        sub.add_argument("--out", required=True, help="new JSON report path; existing files are refused")
        sub.add_argument("--intake-config", help="optional checked intake declaration; segment hashes are retained, not recomputed")
        for name in exposed_limits:
            sub.add_argument("--" + name.replace("_", "-"), type=int, default=defaults[name])
        if command == "compare":
            sub.add_argument("--copy-uuid", required=True, type=copy_uuid)
            sub.add_argument("--path", required=True, action="append", help="one explicit drive-qualified file path; repeat for more files")
            sub.add_argument("--volume-identity", help="exact inventory volume_identity if the copy UUID is ambiguous")
    args = parser.parse_args(argv)
    try:
        limits = Limits(**{name: getattr(args, name) for name in exposed_limits})
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._#()-]{0,79}", args.exhibit):
            raise ValueError("exhibit must be an explicit safe identifier of at most 80 characters")
        output = Path(args.out).absolute()
        if output.exists() or output.is_symlink():
            raise FileExistsError("output already exists; choose a new report path: " + str(output))
        if not output.parent.is_dir():
            raise ValueError("output parent directory must already exist")
        requested_image = Path(args.image).absolute()
        _file_identity(requested_image)  # Refuse a symlink before canonicalizing.
        image = requested_image.resolve(strict=True)
        paths = _paths(args.path, limits) if args.command == "compare" else None
        started = datetime.now(timezone.utc).isoformat()
        source = _input_receipt(image, args.exhibit, args.intake_config, config_limit=limits.max_metadata_bytes)
        code = _code_receipt()
        target = _target_open(image)
        inventory = discover_vss(target, dict(image=image.name, exhibit=args.exhibit,
            source_snapshot="base-volume", source_variant="primary"), limits=limits)
        if args.command == "compare":
            result = compare_versions(inventory, args.copy_uuid, paths, volume_identity=args.volume_identity)
            complete = all(row[side]["status"] in ("present", "absent")
                           for row in result["paths"] for side in ("base", "snapshot"))
        else:
            result, complete = inventory.as_dict(), inventory.complete
        if _input_receipt(image, args.exhibit, args.intake_config, config_limit=limits.max_metadata_bytes) != source:
            raise ValueError("input segment identity or intake configuration changed during observation; report not published")
        if _code_receipt() != code:
            raise ValueError("module code or dependency version changed during observation; report not published")
        source["stat_stability"] = "segment identities, sizes, modification/change times checked before and after; content immutability not established"
        report = dict(schema_version=1, kind="historical_source_observation_receipt", command=args.command,
            interpretation="Observation-only report; no proof verdict, actor attribution, transfer direction, deletion event or acquisition authenticity established",
            started_at=started, completed_at=datetime.now(timezone.utc).isoformat(),
            request=dict(image=str(requested_image), exhibit=args.exhibit,
                         copy_uuid=getattr(args, "copy_uuid", None), paths=paths,
                         volume_identity=getattr(args, "volume_identity", None)),
            input=source, code=code, result=result)
        encoded = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
        # Exclusive create also protects against a file or symlink appearing
        # after the preflight. No existing output or image is opened for writing.
        with output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
        print(str(output))
        return 0 if complete else 1
    except Exception as error:
        parser.exit(2, f"historical_sources: {type(error).__name__}: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
