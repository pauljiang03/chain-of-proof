"""FAT directory entries left in clusters that no current file owns.

A quick format rewrites the boot sector, the allocation table and the root directory.
It does not touch the old subdirectory clusters, and each of those still begins with
its "." and ".." entries. That signature is how they are found here. Nothing is
guessed: an entry's name, size and times are read from the entry, and a folder whose
own name sat in the overwritten root is called "[lost folder N]" (N = its first cluster).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from .store import us

DOT = b".          "
DOTDOT = b"..         "
ATTR_VOLUME, ATTR_DIR, ATTR_LONG = 0x08, 0x10, 0x0F


@dataclass
class Entry:
    name: str
    short_name: str
    is_dir: bool
    deleted: bool               # first byte 0xE5: removed before the format
    first_cluster: int
    size: int
    created: Optional[datetime]     # local wall-clock time, as FAT stores it
    modified: Optional[datetime]


@dataclass
class Directory:
    own: int                    # first cluster, from the "." entry
    parent: int                 # from the ".." entry; 0 means the root directory
    entries: List[Entry] = field(default_factory=list)
    complete: bool = True       # False: no end marker inside the cluster, or a bad entry


def _stamp(date: int, time: int, tenths: int = 0) -> Optional[datetime]:
    if date == 0:
        return None
    try:
        base = datetime(1980 + (date >> 9), (date >> 5) & 15, date & 31,
                        time >> 11, (time >> 5) & 63, min((time & 31) * 2, 59))
    except ValueError:
        return None
    return base + timedelta(milliseconds=10 * tenths)


def _checksum(short11: bytes) -> int:
    s = 0
    for c in short11:
        s = (((s & 1) << 7) + (s >> 1) + c) & 0xFF
    return s


def _cluster(entry: bytes) -> int:
    return struct.unpack_from("<H", entry, 20)[0] << 16 | struct.unpack_from("<H", entry, 26)[0]


def starts_directory(buf: bytes) -> bool:
    return (len(buf) >= 64 and buf[0:11] == DOT and buf[32:43] == DOTDOT
            and bool(buf[11] & ATTR_DIR) and bool(buf[43] & ATTR_DIR))


def parse_directory(buf: bytes) -> Optional[Directory]:
    """One directory cluster -> its entries. None if it does not start like one."""
    if not starts_directory(buf):
        return None
    d = Directory(own=_cluster(buf[0:32]), parent=_cluster(buf[32:64]), complete=False)
    long_parts: List[bytes] = []
    long_sum = None
    for i in range(64, len(buf) - 31, 32):
        e = buf[i:i + 32]
        if e[0] == 0x00:
            d.complete = True
            break
        attr = e[11]
        if attr & 0x3F == ATTR_LONG:                 # one piece of a long file name
            if e[0] != 0xE5 and e[0] & 0x40:
                long_parts = []                      # pieces are stored last-first
            long_parts.insert(0, e[1:11] + e[14:26] + e[28:32])
            long_sum = e[13]
            continue
        if attr & 0xC0 or any(c < 0x20 for c in e[1:11]):
            break                                    # not a directory entry: stop here
        if attr & ATTR_VOLUME:
            long_parts = []
            continue
        deleted = e[0] == 0xE5
        base, ext = e[0:8].decode("cp437").rstrip(), e[8:11].decode("cp437").rstrip()
        if deleted:
            base = "?" + base[1:]                    # the first character is overwritten
        if e[12] & 0x08:
            base = base.lower()
        if e[12] & 0x10:
            ext = ext.lower()
        short = base + ("." + ext if ext else "")
        name = short
        if long_parts and (deleted or long_sum == _checksum(e[0:11])):
            text = b"".join(long_parts).decode("utf-16-le", "replace").split("\x00")[0]
            name = text or short
        long_parts, long_sum = [], None
        ctime, cdate = struct.unpack_from("<HH", e, 14)
        mtime, mdate = struct.unpack_from("<HH", e, 22)
        d.entries.append(Entry(name=name, short_name=short, is_dir=bool(attr & ATTR_DIR),
                               deleted=deleted, first_cluster=_cluster(e),
                               size=struct.unpack_from("<I", e, 28)[0],
                               created=_stamp(cdate, ctime, e[13]),
                               modified=_stamp(mdate, mtime)))
    return d


def carve_fat32(vol, bytes_per_sector: int, sectors_per_cluster: int, reserved_sectors: int,
                fat_count: int, fat_sectors: int, total_sectors: int) -> Dict[int, Directory]:
    """Directory clusters marked free in the allocation table, keyed by cluster number."""
    cluster_size = bytes_per_sector * sectors_per_cluster
    data_start = (reserved_sectors + fat_count * fat_sectors) * bytes_per_sector
    clusters = (total_sectors * bytes_per_sector - data_start) // cluster_size
    vol.seek(reserved_sectors * bytes_per_sector)
    fat = vol.read(min(fat_sectors * bytes_per_sector, (clusters + 2) * 4))

    def free(cluster: int) -> bool:
        return struct.unpack_from("<I", fat, cluster * 4)[0] & 0x0FFFFFFF == 0

    found: Dict[int, Directory] = {}
    chunk = cluster_size * 256
    end = data_start + clusters * cluster_size
    for off in range(data_start, end, chunk):
        vol.seek(off)
        buf = vol.read(min(chunk, end - off))
        for i in range(0, len(buf) - 63, cluster_size):
            if not starts_directory(buf[i:i + 64]):
                continue
            cluster = 2 + (off + i - data_start) // cluster_size
            if free(cluster):
                found[cluster] = parse_directory(buf[i:i + cluster_size])
    return found


def folder_paths(found: Dict[int, Directory]) -> Dict[int, str]:
    """A path for each recovered folder, from the folders that list it.

    A folder is only trusted to name its children when its own "." entry agrees with
    where it was found; otherwise it comes from an older layout of the device."""
    names: Dict[int, str] = {}
    for cluster, d in found.items():
        if d.own != cluster:
            continue
        for e in d.entries:
            if e.is_dir and not e.deleted:
                names[e.first_cluster] = e.name

    def path(cluster: int, depth: int = 0) -> str:
        d = found[cluster]
        if d.own != cluster:
            return f"\\[lost folder at cluster {cluster}, older layout]"
        if cluster not in names or depth > 64:
            return f"\\[lost folder {cluster}]"
        return path(d.parent, depth + 1) + "\\" + names[cluster]

    return {cluster: path(cluster) for cluster in sorted(found)}


def fat_times_utc(created: datetime, modified: datetime, tz: ZoneInfo):
    """FAT stores local wall-clock time with no zone -> (created µs, modified µs, note).

    Windows converts with the UTC offset in force at the moment it writes the stamp,
    not the offset that applied on the stamp's own date. A copy writes the entry once
    and keeps the source's modified time, so a modified time older than the created
    time was written at creation and takes that moment's offset. (On this case the
    rule reproduces, to the second, the UTC times exFAT recorded for the same files.)"""
    made = created.replace(tzinfo=tz)
    offset = made.utcoffset()
    created_us = us(made.astimezone(timezone.utc))
    if modified < created:
        modified_us = us((modified - offset).replace(tzinfo=timezone.utc))
        note = (f"FAT local time, written when the entry was created, so converted with "
                f"that moment's UTC offset ({made.strftime('%z')}, zone {tz.key})")
    else:
        modified_us = us(modified.replace(tzinfo=tz).astimezone(timezone.utc))
        note = f"FAT local time, converted from {tz.key}"
    return created_us, modified_us, note
