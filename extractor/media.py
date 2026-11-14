"""Removable-media images: which volume the seized device holds, and its file times."""
from __future__ import annotations

import struct
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dissect.target import Target

from .fatcarve import carve_fat32, fat_times_utc, folder_paths
from .acquisition import area, provenance, resolve
from .store import Evidence, us, us_from_unix

FAT_EPOCH = 315532800  # 1980-01-01, what an unset FAT timestamp decodes to


def _wall(naive_seconds: float) -> datetime:
    """dissect returns a FAT stamp as if it were UTC; this is the wall-clock time stored."""
    return datetime.fromtimestamp(naive_seconds, timezone.utc).replace(tzinfo=None)


def _recovered_entries(ev, vol, fs, identity: dict, tz: ZoneInfo, examined_at: int, common: dict):
    """Directory entries left in unallocated FAT32 clusters, for example after a quick
    format. They belonged to an earlier file system whose volume serial is gone, so the
    rows carry an area id in `aux` and one unallocatedOnDevice row ties that area to the
    device. Returns (folders, files)."""
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
        if not d.complete:
            ev.problem(f"{common['image']} cluster {cluster}",
                       ValueError("directory has no end marker in its first cluster; "
                                  "later entries, if any, were not recovered"))
        for e in d.entries:
            if e.is_dir or e.created is None or e.modified is None:
                continue
            rel = paths[cluster] + "\\" + e.name
            created, modified, note = fat_times_utc(e.created, e.modified, tz)
            base = dict(artifact=f"FAT directory entry in unallocated cluster {cluster}",
                        recovered=True, removed_before_format=e.deleted, size=e.size,
                        short_name=e.short_name, first_cluster=e.first_cluster, **common)
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
        files = []
        for dirpath, _dirs, names in fs.walk("/"):
            for name in names:
                p = fs.path(dirpath).joinpath(name)
                st = p.lstat()
                rel = str(p).replace("/", "\\")
                if kind == "fat":
                    if dirpath == "/" and st.st_size == 0 and st.st_ctime == FAT_EPOCH:
                        # the volume-label directory entry, not a file; its write time is
                        # when the label was set, which a format does
                        label = name.replace(".", "")
                        continue
                    created, modified, zone = fat_times_utc(_wall(st.st_ctime), _wall(st.st_mtime),
                                                            ZoneInfo(fat_tz))
                    res_c, res_m = 10_000, 2_000_000
                else:
                    created, modified = us_from_unix(st.st_ctime), us_from_unix(st.st_mtime)
                    res_c, res_m, zone = 10_000, 10_000, "exFAT local time with its recorded UTC offset"
                files.append((rel, created, res_c, modified, res_m, zone, st.st_size))
        common = dict(image=image, exhibit=exhibit["exhibit"], tool=tool, **provenance(identity))
        ev.add("volumeOnDevice", examined_at, 1, identity["device_identity"], vsn,
               artifact=f"volume boot record, partition at byte offset {getattr(vol, 'offset', None)}",
               filesystem=kind, volume_label=label, disk_signature=signature,
               time_meaning="when the image was examined, not an event on the device", **common)
        for rel, created, res_c, modified, res_m, zone, size in files:
            base = dict(artifact=f"{kind} directory entry {rel}", size=size, time_zone=zone, **common)
            ev.add("fileCreated", created, res_c, rel, vsn, **base)
            ev.add("fileModified", modified, res_m, rel, vsn, **base)
        line = (f"{image}: {kind} volume {vsn} label {label!r} disk signature {signature}, "
                f"{len(files)} files")
        if kind == "fat":
            try:
                got = _recovered_entries(ev, vol, fs, identity, ZoneInfo(fat_tz),
                                         examined_at, common)
            except Exception as e:
                ev.problem(f"{image} unallocated space", e)
                got = None
            if got:
                line += (f"; unallocated space: {got[1]} file entries in {got[0]} "
                         f"recovered folders")
        summary.append(line)
    return summary or [f"{image}: no FAT/exFAT volume found"]
