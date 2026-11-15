"""Removable-media images: which volume the seized device holds, and its file times."""
from __future__ import annotations

import struct
from bisect import bisect_right
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dissect.target import Target
from dissect.util.stream import RangeStream, RunlistStream

from .fatcarve import carve_fat32, fat_times_utc, folder_paths, parse_directory
from .acquisition import area, provenance, resolve
from .store import Evidence, us, us_from_unix
from .source_scope import base_volume_scope, merge_scope

FAT_EPOCH = 315532800  # 1980-01-01, what an unset FAT timestamp decodes to
_UINT64 = 1 << 64
_MAX_DIRECTORY_BYTES = 16 * 1024 * 1024
_MAX_DIRECTORY_RUNS = 8192


def _uint(value, *, positive=False):
    return type(value) is int and (0 < value if positive else 0 <= value) and value < _UINT64


def _partition_context(target, vol, common):
    """Partition coordinates, only for a direct and unambiguous disk partition."""
    for key in ("image", "exhibit", "source_snapshot", "source_variant"):
        value = common.get(key)
        if (type(value) is not str or not value.strip() or value != value.strip()
                or value.lower() in {"unknown", "none", "(none)"}
                or any(ord(char) < 32 for char in value)
                or len(value.encode("utf-8")) > 512):
            raise ValueError(f"file occurrence requires explicit {key}")
    indices = [i for i, disk in enumerate(target.disks) if disk is vol.disk]
    if len(indices) != 1:
        raise ValueError("file occurrence requires one exact source disk")
    disk, vs, backing = vol.disk, vol.vs, vol.fh
    if (getattr(vs, "__type__", None) != "disk" or vs.fh is not disk or vs.disk is not disk
            or type(backing) is not RangeStream or backing._fh is not disk
            or backing.offset != vol.offset or backing.size != vol.size):
        raise ValueError("file occurrence requires a direct partition byte range")
    if (not _uint(vol.offset) or not _uint(vol.size, positive=True)
            or not _uint(getattr(disk, "size", None), positive=True)
            or vol.offset + vol.size > disk.size):
        raise ValueError("file occurrence partition bounds are invalid")
    return dict(schema_version=1, disk_index=indices[0],
                partition_offset_bytes=vol.offset, partition_size_bytes=vol.size)


def _stream_locator(stream, vol, seen=()):
    """Stream offset -> volume offset; FAT runs count data-area clusters, exFAT runs volume sectors."""
    size = getattr(stream, "size", None)
    if not _uint(size, positive=True):
        raise ValueError("directory stream has no bounded size")
    if id(stream) in seen or len(seen) >= 8:
        raise ValueError("directory stream chain is cyclic or too deep")
    if stream is vol:
        translate = lambda offset: offset
    elif type(stream) is RangeStream:
        offset = stream.offset
        parent = _stream_locator(stream._fh, vol, seen + (id(stream),))
        if not _uint(offset) or offset + size > stream._fh.size:
            raise ValueError("directory range exceeds its backing stream")
        translate = lambda position: parent(offset + position)
    elif type(stream) is RunlistStream:
        block_size, runs = stream.block_size, stream.runlist
        if (not _uint(block_size, positive=True) or block_size % 32
                or not runs or len(runs) > _MAX_DIRECTORY_RUNS):
            raise ValueError("directory runlist is unsupported or exceeds its bound")
        parent = _stream_locator(stream._fh, vol, seen + (id(stream),))
        starts, physical, end = [], [], 0
        for block, count in runs:
            if not _uint(block) or not _uint(count, positive=True):
                raise ValueError("directory has an invalid or sparse run")
            if (block + count) * block_size > stream._fh.size:
                raise ValueError("directory run exceeds its backing stream")
            starts.append(end)
            physical.append(block * block_size)
            end += count * block_size
        if end < size:
            raise ValueError("directory runlist does not cover its declared size")

        def translate(position):
            index = bisect_right(starts, position) - 1
            limit = starts[index + 1] if index + 1 < len(starts) else end
            if position + 32 > limit:
                raise ValueError("directory record crosses a noncontiguous run boundary")
            return parent(physical[index] + position - starts[index])
    else:
        raise ValueError("directory stream is not a supported native byte mapping")

    def locate(position):
        if not _uint(position) or position + 32 > size:
            raise ValueError("directory record exceeds its stream")
        return translate(position)

    return locate


def _read_directory(stream):
    size = getattr(stream, "size", None)
    if not _uint(size, positive=True) or size > _MAX_DIRECTORY_BYTES or size % 32:
        raise ValueError("directory size is invalid or exceeds the occurrence scan bound")
    previous = stream.tell()
    try:
        stream.seek(0)
        raw = stream.read(size)
    finally:
        stream.seek(previous)
    if len(raw) != size:
        raise ValueError("directory bytes are truncated")
    return raw


def _record_slots(raw, kind):
    """Yield (record bytes, directory offset): FAT short entries, or exFAT FILE entry sets."""
    offset = 0
    while offset < len(raw):
        record = raw[offset:offset + 32]
        if len(record) != 32:
            raise ValueError("truncated directory record")
        if record[0] == 0:
            break
        length = 32
        if kind == "fat":
            if record[0] != 0xE5 and record[11] & 0x3F != 0x0F:
                yield record, offset
        elif record[0] == 0x85:
            secondaries = record[1]
            if not 2 <= secondaries <= 18:
                raise ValueError("unsupported exFAT secondary-entry count")
            length = (secondaries + 1) * 32
            entryset = raw[offset:offset + length]
            if (len(entryset) != length or entryset[32] != 0xC0
                    or any(entryset[i] != 0xC1 for i in range(64, length, 32))):
                raise ValueError("invalid or truncated exFAT entry set")
            yield entryset, offset
        offset += length


def _directory_occurrences(vol, fs, dirpath):
    directory = fs.get(dirpath).entry
    kind = fs.__type__
    if kind == "fat":
        stream = directory.open()
    elif kind == "exfat":
        native = directory[0]
        if directory is fs.exfat.files["/"]:
            stream = fs.exfat.root_directory.root_dir
        else:
            # Match the installed parser's directory stream, whose runs are sectors.
            runs = fs.exfat.runlist(native.stream.location,
                                   not_fragmented=native.stream.flags.not_fragmented)
            stream = RunlistStream(fs.exfat.filesystem, runs, int(native.stream.data_length),
                                   fs.exfat.sector_size)
    else:
        raise ValueError("unsupported occurrence filesystem")
    locate = _stream_locator(stream, vol)
    slots = {}
    for record, offset in _record_slots(_read_directory(stream), kind):
        # Identical entries in different slots are ambiguous: pick neither.
        slots[record] = None if record in slots else locate(offset)
    return slots


def _file_occurrence(context, kind, entry_id):
    if not _uint(entry_id) or entry_id + 32 > context["partition_size_bytes"]:
        raise ValueError("native directory record is absent, ambiguous or out of bounds")
    return dict(context, entry_kind=f"{kind}_directory_entry", entry_id=entry_id)


def _native_key(entry, kind):
    if kind == "fat":
        return entry.entry.dirent.dumps()
    native = entry.entry[0]
    return (native.metadata.dumps() + native.stream.dumps()
            + b"".join(part.dumps() for part in native.fn_entries))


def _recovered_slots(raw, expected):
    """Recover physical short-entry slots while checking the existing parser result."""
    if parse_directory(raw) != expected:
        raise ValueError("recovered directory no longer matches its source bytes")
    offsets = []
    for offset in range(64, len(raw) - 31, 32):
        record = raw[offset:offset + 32]
        if record[0] == 0:
            break
        attr = record[11]
        if attr & 0x3F == 0x0F:
            continue
        if attr & 0xC0 or any(c < 0x20 for c in record[1:11]):
            break
        if not attr & 0x08:
            offsets.append(offset)
    if len(offsets) != len(expected.entries):
        raise ValueError("recovered directory slots do not match parsed entries")
    return offsets


def _wall(naive_seconds: float) -> datetime:
    """dissect returns a FAT stamp as if it were UTC; this is the wall-clock time stored."""
    return datetime.fromtimestamp(naive_seconds, timezone.utc).replace(tzinfo=None)


def _recovered_entries(ev, vol, fs, identity: dict, tz: ZoneInfo, examined_at: int, common: dict,
                       occurrence_context=None):
    """Entries in unallocated FAT32 clusters -> (folders, files); the old volume serial is gone."""
    bpb = fs.fatfs.bpb
    if bpb.BPB_RootEntCnt != 0:                      # FAT12/16: not handled
        return None
    found = carve_fat32(vol, bpb.BPB_BytsPerSec, bpb.BPB_SecPerClus, bpb.BPB_RsvdSecCnt,
                        bpb.BPB_NumFATs, fs.fatfs.bpb_ext.BPB_FATSz32, bpb.BPB_TotSec32)
    if not found:
        return 0, 0
    location = area(identity)
    paths = folder_paths(found)
    files = 0
    for cluster in sorted(found):
        d = found[cluster]
        occurrences = [None] * len(d.entries)
        if occurrence_context is not None:
            try:
                cluster_size = bpb.BPB_BytsPerSec * bpb.BPB_SecPerClus
                data_start = (bpb.BPB_RsvdSecCnt + bpb.BPB_NumFATs * fs.fatfs.bpb_ext.BPB_FATSz32) * bpb.BPB_BytsPerSec
                physical = data_start + (cluster - 2) * cluster_size
                if (not _uint(physical) or not 0 < cluster_size <= _MAX_DIRECTORY_BYTES
                        or physical + cluster_size > occurrence_context["partition_size_bytes"]):
                    raise ValueError("recovered directory cluster is out of bounds")
                vol.seek(physical)
                raw = vol.read(cluster_size)
                if len(raw) != cluster_size:
                    raise ValueError("recovered directory cluster is truncated")
                occurrences = [_file_occurrence(occurrence_context, "fat", physical + slot)
                               for slot in _recovered_slots(raw, d)]
            except Exception as error:
                ev.problem(f"{common['image']} cluster {cluster} file occurrence", error)
        if not d.complete:
            ev.problem(f"{common['image']} cluster {cluster}",
                       ValueError("directory has no end marker in its first cluster; "
                                  "later entries, if any, were not recovered"))
        for e, occurrence in zip(d.entries, occurrences):
            if e.is_dir or e.created is None or e.modified is None:
                continue
            rel = paths[cluster] + "\\" + e.name
            created, modified, note = fat_times_utc(e.created, e.modified, tz)
            base = merge_scope(common, dict(artifact=f"FAT directory entry in unallocated cluster {cluster}",
                        source_variant="unallocated-recovery",
                        recovered=True, removed_before_format=e.deleted, size=e.size,
                        short_name=e.short_name, first_cluster=e.first_cluster))
            if occurrence is not None:
                base["file_occurrence"] = occurrence
            ev.add("fileCreated", created, 10_000, rel, location,
                   time_zone=f"FAT local time, converted from {tz.key}", **base)
            ev.add("fileModified", modified, 2_000_000, rel, location, time_zone=note, **base)
            files += 1
    ev.add("unallocatedOnDevice", examined_at, 1, identity["device_identity"], location,
           artifact="FAT32 clusters the allocation table marks free", folders=len(found),
           file_entries=files,
           time_meaning="when the image was examined, not an event on the device", **common)
    return len(found), files


def extract_media(ev: Evidence, path, exhibit: dict, fat_tz: str, examined_at: int, tool: str,
                  acquisition: dict = None):
    image = path.name
    identity = acquisition if acquisition is not None else resolve(path, exhibit)
    target = Target.open(path)
    disk = target.disks[0]
    disk.seek(0x1B8)
    signature = "%08X" % struct.unpack("<I", disk.read(4))[0]
    summary = []
    for vol in target.volumes:
        fs = vol.fs
        kind = getattr(fs, "__type__", None)
        if kind not in ("fat", "exfat"):
            continue
        if kind == "exfat":
            serial = fs.exfat.vbr.volume_serial
            label = (fs.exfat.volume_label or "").strip()
        else:
            serial = int(fs.fatfs.volume_id, 16)
            label = ""
        vsn = "%08X" % serial
        common = dict(image=image, exhibit=exhibit["exhibit"], tool=tool,
                      **provenance(identity), **base_volume_scope())
        try:
            occurrence_context = _partition_context(target, vol, common)
        except Exception as error:
            ev.problem(f"{image} partition file occurrence", error)
            occurrence_context = None
        files = []
        for dirpath, _dirs, names in fs.walk("/"):
            slots = None
            if occurrence_context is not None and names:
                try:
                    slots = _directory_occurrences(vol, fs, dirpath)
                except Exception as error:
                    ev.problem(f"{image} {dirpath} file occurrence", error)
            for name in names:
                p = fs.path(dirpath).joinpath(name)
                entry = fs.get(str(p))
                st = entry.lstat()
                rel = str(p).replace("/", "\\")
                if kind == "fat":
                    if dirpath == "/" and st.st_size == 0 and st.st_ctime == FAT_EPOCH:
                        # the volume label, not a file; its time is when a format set the label
                        label = name.replace(".", "")
                        continue
                    created, modified, zone = fat_times_utc(_wall(st.st_ctime), _wall(st.st_mtime),
                                                            ZoneInfo(fat_tz))
                    res_c, res_m = 10_000, 2_000_000
                else:
                    created, modified = us_from_unix(st.st_ctime), us_from_unix(st.st_mtime)
                    res_c, res_m, zone = 10_000, 10_000, "exFAT local time with its recorded UTC offset"
                occurrence = None
                if slots is not None:
                    try:
                        occurrence = _file_occurrence(occurrence_context, kind,
                                                      slots.get(_native_key(entry, kind)))
                    except Exception as error:
                        ev.problem(f"{image} {rel} file occurrence", error)
                files.append((rel, created, res_c, modified, res_m, zone, st.st_size, occurrence))
        ev.add("volumeOnDevice", examined_at, 1, identity["device_identity"], vsn,
               artifact=f"volume boot record, partition at byte offset {getattr(vol, 'offset', None)}",
               filesystem=kind, volume_label=label, disk_signature=signature,
               time_meaning="when the image was examined, not an event on the device", **common)
        for rel, created, res_c, modified, res_m, zone, size, occurrence in files:
            base = dict(artifact=f"{kind} directory entry {rel}", size=size, time_zone=zone, **common)
            if occurrence is not None:
                base["file_occurrence"] = occurrence
            ev.add("fileCreated", created, res_c, rel, vsn, **base)
            ev.add("fileModified", modified, res_m, rel, vsn, **base)
        line = (f"{image}: {kind} volume {vsn} label {label!r} disk signature {signature}, "
                f"{len(files)} files")
        if kind == "fat":
            try:
                got = _recovered_entries(ev, vol, fs, identity, ZoneInfo(fat_tz),
                                         examined_at, common, occurrence_context)
            except Exception as e:
                ev.problem(f"{image} unallocated space", e)
                got = None
            if got:
                line += (f"; unallocated space: {got[1]} file entries in {got[0]} "
                         f"recovered folders")
        summary.append(line)
    return summary or [f"{image}: no FAT/exFAT volume found"]
