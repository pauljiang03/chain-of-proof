"""Removable-media images: which volume the seized device holds, and its file times."""
from __future__ import annotations

import struct
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dissect.target import Target

from .store import Evidence, us, us_from_unix

FAT_EPOCH = 315532800  # 1980-01-01, what an unset FAT timestamp decodes to


def _fat_local_to_utc_us(naive_seconds: float, tz: ZoneInfo) -> int:
    """FAT stores local wall-clock time with no zone. dissect returns it as if it were
    UTC; reinterpret it in the zone of the machine that wrote it."""
    wall = datetime.fromtimestamp(naive_seconds, timezone.utc).replace(tzinfo=None)
    return us(wall.replace(tzinfo=tz).astimezone(timezone.utc))


def extract_media(ev: Evidence, path, exhibit: dict, fat_tz: str, examined_at: int, tool: str):
    image = path.name
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
                    created = _fat_local_to_utc_us(st.st_ctime, ZoneInfo(fat_tz))
                    modified = _fat_local_to_utc_us(st.st_mtime, ZoneInfo(fat_tz))
                    res_c, res_m, zone = 10_000, 2_000_000, f"FAT local time, converted from {fat_tz}"
                else:
                    created, modified = us_from_unix(st.st_ctime), us_from_unix(st.st_mtime)
                    res_c, res_m, zone = 10_000, 10_000, "exFAT local time with its recorded UTC offset"
                files.append((rel, created, res_c, modified, res_m, zone, st.st_size))
        common = dict(image=image, exhibit=exhibit["exhibit"], tool=tool)
        ev.add("volumeOnDevice", examined_at, 1, exhibit["device_serial"], vsn,
               artifact=f"volume boot record, partition at byte offset {getattr(vol, 'offset', None)}",
               filesystem=kind, volume_label=label, disk_signature=signature,
               device_serial_source="exhibits.json (NIST case documentation)",
               time_meaning="when the image was examined, not an event on the device", **common)
        for rel, created, res_c, modified, res_m, zone, size in files:
            base = dict(artifact=f"{kind} directory entry {rel}", size=size, time_zone=zone, **common)
            ev.add("fileCreated", created, res_c, rel, vsn, **base)
            ev.add("fileModified", modified, res_m, rel, vsn, **base)
        summary.append(f"{image}: {kind} volume {vsn} label {label!r} disk signature {signature}, "
                       f"{len(files)} files")
    return summary or [f"{image}: no FAT/exFAT volume found"]
