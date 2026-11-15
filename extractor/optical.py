"""An optical disc image holding a UDF file system (ECMA-167 with the OSTA UDF rules).

What is read, and from where:

* the volume serial, the way the Windows UDF driver derives it: four byte-wise sums
  over the 512-byte File Set Descriptor;
* the recording timestamp stored in each distinct File Set Descriptor. This is a
  descriptor timestamp, not proof of a format action or a completed write;
* the files the disc lists now;
* files the disc no longer lists. A write-once disc written in packets never loses
  anything: every change appends new file entries and a new allocation table (the
  VAT), and each older table still describes the disc as it was. Files named only by
  an older table, or by a directory entry flagged "deleted", are emitted as recovered;
* the digests stored in the E01 container.

Everything below `open_image` is plain parsing of bytes and needs only the standard
library; dissect is imported inside the functions that open an image.
"""
from __future__ import annotations

import calendar
import struct
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Iterator, List, NamedTuple, Optional, Tuple

SECTOR = 2048
PARSER = "extractor/optical.py (ECMA-167 / OSTA UDF structures, read directly)"
OBSERVED = "when the image was examined, not an event on the device"

# ---------------------------------------------------------------- E01 container

EWF_MAGIC = (b"EVF\x09\x0d\x0a\xff\x00", b"LVF\x09\x0d\x0a\xff\x00")


def ewf_segments(path: Path) -> List[Path]:
    """pc.E01 -> [pc.E01, pc.E02, ...]; any other file -> [file]."""
    path = Path(path)
    ext = path.suffix
    if len(ext) != 4 or ext[1].upper() not in "ELS" or not path.parent.is_dir():
        return [path]
    out = [p for p in path.parent.iterdir()
           if p.stem == path.stem and len(p.suffix) == 4 and p.suffix[1:].isalnum()
           and p.suffix[1].isupper() == ext[1].isupper() and p.suffix[1:] >= ext[1:]]
    return sorted(out, key=lambda p: p.suffix) or [path]


def ewf_sections(fh) -> List[Tuple[str, int, int]]:
    """Sections of one EWF segment file: (type, offset of its data, size of its data)."""
    fh.seek(0)
    if fh.read(8) not in EWF_MAGIC:
        raise ValueError("not an EWF (E01) segment file")
    out, offset = [], 13
    while True:
        fh.seek(offset)
        d = fh.read(76)
        if len(d) < 76:
            raise ValueError(f"section descriptor at byte {offset} is cut short")
        if zlib.adler32(d[:72]) != struct.unpack_from("<I", d, 72)[0]:
            raise ValueError(f"section descriptor at byte {offset} fails its checksum")
        kind = d[:16].split(b"\x00")[0].decode("ascii", "replace")
        following, size = struct.unpack_from("<QQ", d, 16)
        out.append((kind, offset + 76, max(size - 76, 0)))
        if kind in ("done", "next") or following <= offset:
            return out
        offset = following


def _checked(fh, offset: int, length: int, what: str) -> bytes:
    """`length` bytes followed by their Adler-32."""
    fh.seek(offset)
    d = fh.read(length + 4)
    if len(d) < length + 4 or zlib.adler32(d[:length]) != struct.unpack_from("<I", d, length)[0]:
        raise ValueError(f"{what} at byte {offset} fails its checksum")
    return d[:length]


def ewf_digests(fh) -> List[Tuple[str, str, str, int]]:
    """Digests stored in a segment file: (algorithm, hex digest, section, data offset)."""
    out = []
    for kind, offset, size in ewf_sections(fh):
        if kind == "digest" and size >= 80:
            d = _checked(fh, offset, 76, "digest section")
            found = (("md5", d[:16]), ("sha1", d[16:36]))
        elif kind == "hash" and size >= 36:
            d = _checked(fh, offset, 32, "hash section")
            found = (("md5", d[:16]),)
        else:
            continue
        out += [(name, value.hex(), kind, offset) for name, value in found if any(value)]
    return out


def ewf_header(fh) -> Dict[str, str]:
    """The acquisition record of an E01 file (header2 if present, else header)."""
    best: Dict[str, str] = {}
    for kind, offset, size in ewf_sections(fh):
        if kind not in ("header2", "header") or (best and kind == "header"):
            continue
        fh.seek(offset)
        raw = zlib.decompress(fh.read(size))
        text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("latin-1")
        lines = text.replace("\r", "").split("\n")
        if len(lines) >= 4:
            best = dict(zip(lines[2].split("\t"), lines[3].split("\t")))
            best["_section"] = kind
            if kind == "header2":
                break
    return best


def ewf_sessions(fh) -> List[Tuple[int, int]]:
    """Optical-disc sessions the imager recorded: (flags, first sector)."""
    for kind, offset, size in ewf_sections(fh):
        if kind == "session" and size >= 36:
            count = struct.unpack_from("<I", _checked(fh, offset, 32, "session header"), 0)[0]
            body = _checked(fh, offset + 36, 32 * count, "session entries")
            return [struct.unpack_from("<II", body, 32 * i) for i in range(count)]
    return []


def ewf_unreadable(fh) -> List[Tuple[int, int]]:
    """Sectors the imager could not read (it stored zeros): (first sector, count)."""
    for kind, offset, size in ewf_sections(fh):
        if kind == "error2" and size >= 520:
            count = struct.unpack_from("<I", _checked(fh, offset, 516, "error2 header"), 0)[0]
            body = _checked(fh, offset + 520, 8 * count, "error2 entries")
            return [struct.unpack_from("<II", body, 8 * i) for i in range(count)]
    return []


def emit_image_digests(ev, path, ctx) -> int:
    """systemSetting rows `image md5` / `image sha1` for the digests an E01 stores."""
    from .source_scope import merge_scope
    common = merge_scope(ctx["common"], {'source_snapshot': 'evidence-image',
                                         'source_variant': 'acquisition-container'})
    header: Dict[str, str] = {}
    seen, n = set(), 0
    for seg in ewf_segments(Path(path)):
        try:
            with seg.open("rb") as fh:
                if fh.read(8) not in EWF_MAGIC:
                    continue                            # a raw image stores no digest
                if not header:
                    header = ewf_header(fh)
                found = ewf_digests(fh)
        except Exception as e:
            ev.problem(f"{seg.name} (E01 container sections)", e)
            continue
        for name, value, section, offset in found:
            if (name, value) in seen:
                continue
            seen.add((name, value))
            prov = dict(artifact=f"{seg.name}: E01 '{section}' section, data at byte offset {offset}",
                        stored_by="the imaging tool at acquisition; not recomputed here",
                        time_meaning=OBSERVED, **common)
            if header.get("m"):
                prov["acquired_as_recorded"] = header["m"]
            if header.get("av"):
                prov["acquired_with"] = f"version {header['av']} on {header.get('ov', '')}".strip()
            ev.add("systemSetting", ctx["examined_at"], 1, f"image {name}", value, **prov)
            n += 1
    return n


# ---------------------------------------------------------------- UDF: small pieces

TAG_PVD, TAG_AVDP, TAG_VDP, TAG_PD, TAG_LVD, TAG_TD = 1, 2, 3, 5, 6, 8
TAG_FSD, TAG_FID, TAG_AED, TAG_FE, TAG_EFE = 256, 257, 258, 261, 266
KNOWN_TAGS = frozenset(list(range(1, 10)) + list(range(256, 267)))
FT_DIRECTORY, FT_FILE, FT_REALTIME, FT_VAT = 4, 5, 249, 248
UNMAPPED = 0xFFFFFFFF

_CRC = []
for _i in range(256):
    _c = _i << 8
    for _ in range(8):
        _c = ((_c << 1) ^ 0x1021) & 0xFFFF if _c & 0x8000 else (_c << 1) & 0xFFFF
    _CRC.append(_c)


def crc_itu_t(data: bytes) -> int:
    """CRC-16, polynomial x^16+x^12+x^5+1, start value 0 (ECMA-167 3/7.2.6)."""
    crc = 0
    for b in data:
        crc = ((crc << 8) & 0xFFFF) ^ _CRC[(crc >> 8) ^ b]
    return crc


class Tag(NamedTuple):
    ident: int
    version: int
    serial: int
    crc: int
    crc_length: int
    location: int


def parse_tag(buf: bytes, check_crc: bool = True) -> Optional[Tag]:
    """The 16-byte descriptor tag, or None if its checksum (or CRC) does not hold."""
    if len(buf) < 16:
        return None
    ident, version, checksum, _r, serial, crc, crc_len, location = struct.unpack_from("<HHBBHHHI", buf)
    if ident not in KNOWN_TAGS or version not in (2, 3):
        return None
    if (sum(buf[0:4]) + sum(buf[5:16])) & 0xFF != checksum:
        return None
    if check_crc and (16 + crc_len > len(buf) or crc_itu_t(buf[16:16 + crc_len]) != crc):
        return None
    return Tag(ident, version, serial, crc, crc_len, location)


def cs0(data: bytes) -> str:
    """OSTA compressed unicode: first byte 8 = one byte per character, 16 = two.
    254 and 255 are the same two encodings, used for the name of a deleted entry (UDF 2.1.1)."""
    if not data:
        return ""
    if data[0] in (8, 254):
        return data[1:].decode("latin-1")
    if data[0] in (16, 255):
        return data[1:len(data) - (len(data) - 1) % 2].decode("utf-16-be", "replace")
    raise ValueError(f"unknown OSTA compression id {data[0]}")


def dstring(field_bytes: bytes) -> str:
    """A fixed-size dstring field: its last byte says how many bytes are in use."""
    if not field_bytes or field_bytes[-1] == 0:
        return ""
    used = field_bytes[-1]
    if used > len(field_bytes) - 1:
        raise ValueError("dstring length byte is larger than its field")
    return cs0(field_bytes[:used])


class Stamp(NamedTuple):
    kind: int                   # 0 = UTC, 1 = local time, 2 = by agreement
    offset: Optional[int]       # minutes east of UTC; None = not recorded
    wall_us: int                # the recorded date and time, read as if it were UTC


def parse_timestamp(raw: bytes) -> Stamp:
    """ECMA-167 1/7.3 timestamp (12 bytes)."""
    if len(raw) < 12:
        raise ValueError("timestamp is cut short")
    tz, year, month, day, hour, minute, second, cs, hus, us = struct.unpack_from("<HhBBBBBBBB", raw)
    if not any(raw[:12]):
        raise ValueError("timestamp is not set (all zero)")
    if cs > 99 or hus > 99 or us > 99:
        raise ValueError("timestamp sub-second fields out of range")
    offset = tz & 0x0FFF
    if offset & 0x800:
        offset -= 0x1000
    wall = datetime(year, month, day, hour, minute, second)      # ValueError if not a date
    wall_us = calendar.timegm(wall.timetuple()) * 1_000_000 + cs * 10_000 + hus * 100 + us
    return Stamp(tz >> 12, None if offset == -2047 else offset, wall_us)


def stamp_utc(raw: bytes, fallback_zone: Optional[str] = None) -> Tuple[int, str]:
    """Timestamp -> (UTC microseconds, how it was converted)."""
    s = parse_timestamp(raw)
    if s.kind == 0:
        out, note = s.wall_us, "UDF timestamp recorded as UTC"
    elif s.kind == 1 and s.offset is not None:
        if not -1440 <= s.offset <= 1440:
            raise ValueError(f"timestamp offset {s.offset} minutes is out of range")
        out = s.wall_us - s.offset * 60_000_000
        note = f"UDF timestamp: local time with its recorded offset of {s.offset:+d} minutes from UTC"
    elif s.kind == 1 and fallback_zone:
        from zoneinfo import ZoneInfo
        wall = datetime(1970, 1, 1) + timedelta(microseconds=s.wall_us)
        aware = wall.replace(tzinfo=ZoneInfo(fallback_zone))
        out = (aware - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(microseconds=1)
        note = f"UDF local time with no offset recorded, converted from {fallback_zone}"
    else:
        raise ValueError("timestamp cannot be placed in UTC (no offset recorded, or time 'by agreement')")
    if out < 0:
        raise ValueError("timestamp is before 1970")
    return out, note


def iso(us: int) -> str:
    return (datetime(1970, 1, 1) + timedelta(microseconds=us)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def udf_serial32(fsd: bytes) -> int:
    """Volume serial as Windows shows it for a UDF volume: four independent byte sums
    over the File Set Descriptor (byte i goes to sum i mod 4), read as one
    little-endian 32-bit number."""
    sums = [0, 0, 0, 0]
    for i, b in enumerate(fsd):
        sums[i & 3] = (sums[i & 3] + b) & 0xFF
    return sums[0] | sums[1] << 8 | sums[2] << 16 | sums[3] << 24


class Extent(NamedTuple):
    kind: int                   # 0 recorded, 1 allocated only, 2 hole, 3 more descriptors
    length: int                 # bytes
    block: int
    partition: Optional[int]    # partition reference; None = same partition as the entry


def parse_long_ad(buf: bytes, off: int = 0) -> Tuple[Extent, bytes]:
    length, block, part = struct.unpack_from("<IIH", buf, off)
    return Extent(length >> 30, length & 0x3FFFFFFF, block, part), bytes(buf[off + 10:off + 16])


def parse_allocation_descriptors(buf: bytes, ad_type: int) -> List[Extent]:
    """short_ad (type 0), long_ad (1) or ext_ad (2) list; a zero length ends it."""
    step = {0: 8, 1: 16, 2: 20}.get(ad_type)
    if step is None:
        raise ValueError(f"allocation descriptor type {ad_type} is not a list")
    out = []
    for off in range(0, len(buf) - step + 1, step):
        if ad_type == 0:
            length, block = struct.unpack_from("<II", buf, off)
            ext = Extent(length >> 30, length & 0x3FFFFFFF, block, None)
        elif ad_type == 1:
            ext = parse_long_ad(buf, off)[0]
        else:
            length, _rec, _inf, block, part = struct.unpack_from("<IIIIH", buf, off)
            ext = Extent(length >> 30, length & 0x3FFFFFFF, block, part)
        if ext.length == 0:
            break
        out.append(ext)
    return out


@dataclass
class FileEntry:
    extended: bool
    tag: Tag
    file_type: int
    icb_flags: int
    links: int
    size: int
    unique_id: int
    accessed: bytes
    modified: bytes
    created: Optional[bytes]            # only the Extended File Entry has it
    extents: List[Extent]
    embedded: Optional[bytes]
    stream_directory: Optional[Extent] = None

    @property
    def ad_type(self) -> int:
        return self.icb_flags & 7


def parse_file_entry(buf: bytes) -> FileEntry:
    """File Entry (tag 261) or Extended File Entry (tag 266)."""
    tag = parse_tag(buf)
    if tag is None or tag.ident not in (TAG_FE, TAG_EFE):
        raise ValueError("not a valid file entry")
    extended = tag.ident == TAG_EFE
    file_type = buf[27]
    icb_flags, = struct.unpack_from("<H", buf, 34)
    links, = struct.unpack_from("<H", buf, 48)
    size, = struct.unpack_from("<Q", buf, 56)
    if extended:
        accessed, modified, created = buf[80:92], buf[92:104], bytes(buf[104:116])
        stream = parse_long_ad(buf, 152)[0]
        unique_id, l_ea, l_ad = struct.unpack_from("<QII", buf, 200)
        base = 216
    else:
        accessed, modified, created, stream = buf[72:84], buf[84:96], None, None
        unique_id, l_ea, l_ad = struct.unpack_from("<QII", buf, 160)
        base = 176
    if base + l_ea + l_ad > len(buf):
        raise ValueError("file entry's descriptors run past its block")
    area = bytes(buf[base + l_ea:base + l_ea + l_ad])
    embedded, extents = None, []
    if icb_flags & 7 == 3:
        embedded = area
    else:
        extents = parse_allocation_descriptors(area, icb_flags & 7)
    return FileEntry(extended, tag, file_type, icb_flags, links, size, unique_id, bytes(accessed),
                     bytes(modified), created, extents, embedded,
                     stream if stream is not None and stream.length else None)


class Fid(NamedTuple):
    name: str
    characteristics: int
    icb: Extent
    unique_id: int              # low 32 bits of the child's unique id (UDF 2.3.4.3)
    offset: int

    @property
    def deleted(self) -> bool:
        return bool(self.characteristics & 0x04)

    @property
    def directory(self) -> bool:
        return bool(self.characteristics & 0x02)

    @property
    def parent(self) -> bool:
        return bool(self.characteristics & 0x08)


def parse_fids(data: bytes) -> Tuple[List[Fid], Optional[str]]:
    """File Identifier Descriptors of a directory -> (entries, what stopped the parse)."""
    out, off = [], 0
    while off + 38 <= len(data):
        if not any(data[off:off + 38]):
            off += 4                                    # padding between descriptors
            continue
        tag = parse_tag(data[off:off + 16], check_crc=False)
        if tag is None or tag.ident != TAG_FID:
            return out, f"no file identifier descriptor at byte {off} of the directory"
        chars, l_fi = data[off + 18], data[off + 19]
        icb, impl = parse_long_ad(data, off + 20)
        l_iu, = struct.unpack_from("<H", data, off + 36)
        length = (38 + l_iu + l_fi + 3) & ~3
        if off + length > len(data):
            return out, f"file identifier descriptor at byte {off} runs past the directory"
        if 16 + tag.crc_length <= length and crc_itu_t(data[off + 16:off + 16 + tag.crc_length]) != tag.crc:
            return out, f"file identifier descriptor at byte {off} fails its CRC"
        try:
            name = cs0(data[off + 38 + l_iu:off + 38 + l_iu + l_fi])
        except ValueError as e:
            return out, f"file identifier at byte {off}: {e}"
        out.append(Fid(name, chars, icb, struct.unpack_from("<I", impl, 2)[0], off))
        off += length
    return out, None


class Vat(NamedTuple):
    entries: Tuple[int, ...]
    previous: Optional[int]     # block of the VAT entry this one replaced
    label: Optional[str]
    files: Optional[int]
    directories: Optional[int]


VAT150_ID = b"*UDF Virtual Alloc Tbl"


def parse_vat(data: bytes, file_type: int) -> Vat:
    """Virtual Allocation Table: UDF 2.xx layout (file type 248) or the 1.50 layout."""
    if file_type == FT_VAT:
        if len(data) < 152:
            raise ValueError("VAT is shorter than its header")
        l_hd, _l_iu = struct.unpack_from("<HH", data, 0)
        previous, files, dirs = struct.unpack_from("<III", data, 132)
        if l_hd < 152 or l_hd > len(data) or (len(data) - l_hd) % 4:
            raise ValueError("VAT header length does not fit the table")
        body, label = data[l_hd:], dstring(data[4:132])
    else:
        if len(data) < 36 or (len(data) - 36) % 4 or data[-35:-35 + len(VAT150_ID)] != VAT150_ID:
            raise ValueError("not a UDF 1.50 VAT")
        previous, = struct.unpack_from("<I", data, len(data) - 4)
        body, label, files, dirs = data[:-36], None, None, None
    entries = struct.unpack("<%dI" % (len(body) // 4), body)
    return Vat(entries, None if previous == UNMAPPED else previous, label, files, dirs)


class PartitionMap(NamedTuple):
    kind: str                   # physical, virtual, sparable, metadata, unknown
    number: int


class Lvd(NamedTuple):
    sequence: int
    label: str
    block_size: int
    revision: str
    fsd: Extent
    maps: Tuple[PartitionMap, ...]


def parse_partition_maps(buf: bytes, count: int) -> Tuple[PartitionMap, ...]:
    out, off = [], 0
    for _ in range(count):
        kind, length = buf[off], buf[off + 1]
        if kind == 1 and length == 6:
            out.append(PartitionMap("physical", struct.unpack_from("<H", buf, off + 4)[0]))
        elif kind == 2 and length == 64:
            ident = bytes(buf[off + 5:off + 28])
            name = next((n for key, n in ((b"*UDF Virtual Partition", "virtual"),
                                          (b"*UDF Sparable Partition", "sparable"),
                                          (b"*UDF Metadata Partition", "metadata"))
                         if ident.startswith(key)), "unknown")
            out.append(PartitionMap(name, struct.unpack_from("<H", buf, off + 38)[0]))
        else:
            raise ValueError(f"partition map type {kind} with length {length}")
        off += length
    return tuple(out)


def parse_lvd(buf: bytes) -> Lvd:
    """Logical Volume Descriptor (tag 6)."""
    seq, = struct.unpack_from("<I", buf, 16)
    block_size, = struct.unpack_from("<I", buf, 212)
    rev, = struct.unpack_from("<H", buf, 240)               # domain identifier suffix
    table_len, count = struct.unpack_from("<II", buf, 264)
    return Lvd(seq, dstring(buf[84:212]), block_size, "%x.%02x" % (rev >> 8, rev & 0xFF),
               parse_long_ad(buf, 248)[0], parse_partition_maps(buf[440:440 + table_len], count))


class Fsd(NamedTuple):
    recorded: bytes
    label: str
    file_set: str
    root: Extent


def parse_fsd(buf: bytes) -> Fsd:
    """File Set Descriptor (tag 256, 512 bytes)."""
    tag = parse_tag(buf)
    if tag is None or tag.ident != TAG_FSD:
        raise ValueError("not a valid file set descriptor")
    return Fsd(bytes(buf[16:28]), dstring(buf[112:240]), dstring(buf[304:336]), parse_long_ad(buf, 400)[0])


# ---------------------------------------------------------------- UDF: the volume

@dataclass
class Listed:
    """One file as one state of the disc names it."""
    path: str
    deleted: bool               # its directory entry (or a folder above it) is flagged deleted
    entry: FileEntry
    sector: int                 # where its file entry is
    partition: int
    directory_sector: int
    version: int                # index into Udf.versions


@dataclass
class Version:
    """The disc as one allocation table (or, without one, the volume itself) describes it."""
    vat_sector: Optional[int]
    vat: Optional[Vat]
    recorded: Optional[bytes]
    fsd_sector: int = -1
    fsd: Optional[Fsd] = None
    serial: int = 0
    files: List[Listed] = field(default_factory=list)
    folders: Dict[int, str] = field(default_factory=dict)       # folder unique id -> path
    nameless: List[str] = field(default_factory=list)           # names whose file entry is gone


class Udf:
    def __init__(self, read: Callable[[int, int], bytes], sectors: int, session_starts=()):
        self.read, self.sectors, self.session_starts = read, sectors, tuple(session_starts)
        self.problems: List[Tuple[str, Exception]] = []
        self.entries: Dict[int, FileEntry] = {}                 # every valid file entry on the disc
        self.fsd_copies: Dict[int, bytes] = {}
        self.sector_kind = bytearray(sectors)                   # 0 zero, 1 data, 2 descriptor
        self.visited: set = set()
        self.versions: List[Version] = []
        self.partitions: Dict[int, Tuple[int, int]] = {}        # number -> (start sector, sectors)
        self.lvd: Optional[Lvd] = None
        self.volume_set = ""

    # -- volume structures
    def _anchor(self) -> Tuple[int, Tuple[int, int, int, int]]:
        spots = [s + 256 for s in reversed(self.session_starts)] + [256, self.sectors - 1,
                                                                    self.sectors - 257, 512]
        for s in spots:
            if 0 <= s < self.sectors:
                buf = self.read(s, 1)
                tag = parse_tag(buf)
                if tag and tag.ident == TAG_AVDP:
                    return s, struct.unpack_from("<IIII", buf, 16)
        raise ValueError("no UDF anchor volume descriptor pointer found")

    def _sequence(self, length: int, start: int) -> bool:
        seen = {}
        sector, end, hops = start, start + (length + SECTOR - 1) // SECTOR, 0
        while sector < end and hops < 64:
            buf = self.read(sector, 1)
            tag = parse_tag(buf)
            sector += 1
            if tag is None:
                continue
            if tag.ident == TAG_TD:
                break
            if tag.ident == TAG_VDP:
                length, start = struct.unpack_from("<II", buf, 20)
                sector, end, hops = start, start + (length + SECTOR - 1) // SECTOR, hops + 1
                continue
            seq, = struct.unpack_from("<I", buf, 16)
            key = (tag.ident, struct.unpack_from("<H", buf, 22)[0] if tag.ident == TAG_PD else 0)
            if key not in seen or seq >= seen[key][0]:
                seen[key] = (seq, buf)
        for (ident, number), (_seq, buf) in seen.items():
            if ident == TAG_PD:
                self.partitions[number] = struct.unpack_from("<II", buf, 188)
            elif ident == TAG_LVD:
                self.lvd = parse_lvd(buf)
            elif ident == TAG_PVD:
                self.volume_set = dstring(buf[72:200])
        return self.lvd is not None and bool(self.partitions)

    def load(self) -> "Udf":
        self.anchor_sector, (m_len, m_loc, r_len, r_loc) = self._anchor()
        if not self._sequence(m_len, m_loc) and not self._sequence(r_len, r_loc):
            raise ValueError("volume descriptor sequence has no logical volume or no partition")
        if self.lvd.block_size != SECTOR:
            raise ValueError(f"logical block size {self.lvd.block_size} is not handled")
        for i, m in enumerate(self.lvd.maps):
            if m.kind not in ("physical", "virtual"):
                self.problems.append((f"partition map {i}", ValueError(
                    f"{m.kind} partition is not handled; files addressed through it are not read")))
        self._scan()
        self._versions()
        return self

    def _scan(self) -> None:
        """One pass over the disc: every file entry and file set descriptor, wherever it is."""
        zero, step = bytes(SECTOR), 256
        for first in range(0, self.sectors, step):
            chunk = self.read(first, min(step, self.sectors - first))
            for i in range(len(chunk) // SECTOR):
                buf = chunk[i * SECTOR:(i + 1) * SECTOR]
                if buf == zero:
                    continue
                sector = first + i
                self.sector_kind[sector] = 1
                if buf[1:6] in (b"BEA01", b"NSR02", b"NSR03", b"TEA01", b"BOOT2", b"CD001", b"CDW02"):
                    self.sector_kind[sector] = 2            # volume recognition sequence
                    continue
                tag = parse_tag(buf)
                if tag is None:
                    continue
                self.sector_kind[sector] = 2
                if tag.ident == TAG_FSD:
                    self.fsd_copies[sector] = bytes(buf[:512])
                elif tag.ident in (TAG_FE, TAG_EFE):
                    try:
                        self.entries[sector] = parse_file_entry(buf)
                    except Exception as e:
                        self.problems.append((f"file entry at sector {sector}", e))

    # -- addressing
    def physical(self, block: int, partition: int, vat: Optional[Vat]) -> int:
        if self.lvd is None or self.lvd.block_size != SECTOR:
            raise ValueError("a supported logical block size is required for addressing")
        if type(block) is not int or block < 0:
            raise LookupError(f"invalid logical block {block}")
        if type(partition) is not int or not 0 <= partition < len(self.lvd.maps):
            raise LookupError(f"partition reference {partition} does not exist")
        m = self.lvd.maps[partition]
        if m.number not in self.partitions:
            raise LookupError(f"partition {m.number} has no descriptor")
        start, length = self.partitions[m.number]
        if type(start) is not int or start < 0 or type(length) is not int or length <= 0:
            raise LookupError(f"partition {m.number} has invalid physical bounds")
        if m.kind == "physical":
            physical_block = block
        elif m.kind == "virtual":
            if vat is None or block >= len(vat.entries) or vat.entries[block] == UNMAPPED:
                raise LookupError(f"virtual block {block} is not mapped")
            physical_block = vat.entries[block]
        else:
            raise LookupError(f"{m.kind} partition is not handled")
        if type(physical_block) is not int or not 0 <= physical_block < length:
            raise LookupError(f"block {block} maps outside partition {m.number}")
        sector = start + physical_block
        if sector >= self.sectors:
            raise LookupError(f"block {block} maps beyond the image at sector {sector}")
        return sector

    def _physical_ref(self, virtual_ref: Optional[int] = None) -> int:
        """Reference number of the physical partition (the one under a virtual map)."""
        number = self.lvd.maps[virtual_ref].number if virtual_ref is not None else None
        for i, m in enumerate(self.lvd.maps):
            if m.kind == "physical" and number in (None, m.number):
                return i
        raise LookupError("no physical partition map")

    @staticmethod
    def _append_run(out, sector, length):
        """Merge only byte ranges that are demonstrably adjacent."""
        if not length:
            return
        if out:
            previous, size = out[-1]
            if ((previous is None and sector is None) or
                    (previous is not None and sector is not None and size % SECTOR == 0
                     and previous + size // SECTOR == sector)):
                out[-1] = (previous, size + length)
                return
        out.append((sector, length))

    def _mapped_runs(self, block, length, partition, vat):
        """Resolve each logical block before forming physical byte ranges.

        Consecutive virtual blocks need not be physically adjacent. This applies
        to file data, directory data and allocation-descriptor continuations.
        """
        if type(length) is not int or length < 0:
            raise ValueError("invalid extent byte length")
        out = []
        for offset in range(0, length, SECTOR):
            sector = self.physical(block + offset // SECTOR, partition, vat)
            self._append_run(out, sector, min(SECTOR, length - offset))
        return out

    def runs(self, entry: FileEntry, partition: int, vat: Optional[Vat],
             unreadable: frozenset = frozenset()) -> List[Tuple[Optional[int], int]]:
        """Where a file's content is: (first sector, or None for a hole; bytes), in order."""
        out, todo, hops, left = [], list(entry.extents), 0, entry.size
        while todo and left > 0:
            ext = todo.pop(0)
            part = partition if ext.partition is None else ext.partition
            if ext.kind == 3:                               # the list continues elsewhere
                hops += 1
                if hops > 4096 or not 24 <= ext.length <= 16 * 1024 * 1024:
                    raise ValueError("allocation-descriptor continuation exceeds its parsing bound")
                locations = self._mapped_runs(ext.block, ext.length, part, vat)
                sector = locations[0][0]
                buf = b"".join(self._pieces_from_runs(locations, unreadable))
                tag = parse_tag(buf)
                if tag is None or tag.ident != TAG_AED:
                    raise ValueError(f"allocation extent descriptor expected at sector {sector}")
                l_ad, = struct.unpack_from("<I", buf, 20)
                step = {0: 8, 1: 16, 2: 20}.get(entry.ad_type)
                if step is None or l_ad > len(buf) - 24 or l_ad % step:
                    raise ValueError(f"allocation descriptors are truncated at sector {sector}")
                todo = parse_allocation_descriptors(buf[24:24 + l_ad], entry.ad_type)
                continue
            take = min(ext.length, left)
            if ext.kind == 0:
                for sector, length in self._mapped_runs(ext.block, take, part, vat):
                    self._append_run(out, sector, length)
            elif ext.kind in (1, 2):
                self._append_run(out, None, take)
            else:
                raise ValueError(f"unsupported allocation extent kind {ext.kind}")
            left -= take
        if left > 0:
            raise ValueError(f"file entry describes {entry.size - left} of its {entry.size} bytes")
        return out

    def pieces(self, entry: FileEntry, partition: int, vat: Optional[Vat],
               unreadable: frozenset = frozenset()) -> Iterator[bytes]:
        """File bytes in order; validate mappings and known unreadable ranges first."""
        if entry.embedded is not None:
            if len(entry.embedded) != entry.size:
                raise ValueError("embedded content is not as long as the file entry says")
            yield entry.embedded
            return
        runs = self.runs(entry, partition, vat, unreadable)
        yield from self._pieces_from_runs(runs, unreadable)

    def _pieces_from_runs(self, runs, unreadable):
        for sector, length in runs:
            if sector is None:
                continue
            count = (length + SECTOR - 1) // SECTOR
            if sector + count > self.sectors:
                raise ValueError(f"content at sectors {sector}-{sector + count - 1} is beyond the "
                                 f"end of the image ({self.sectors} sectors)")
            bad = sorted(s for s in unreadable if sector <= s < sector + count)
            if bad:
                raise ValueError(f"content includes sectors the imager could not read: {bad[:8]}")
        for sector, length in runs:
            done = 0
            while done < length:
                want = min(length - done, 512 * SECTOR)
                if sector is None:
                    data = bytes(want)
                else:
                    data = self.read(sector + done // SECTOR, (want + SECTOR - 1) // SECTOR)[:want]
                    if len(data) != want:
                        raise ValueError(f"short read at sector {sector + done // SECTOR}")
                yield data
                done += want

    # -- states of the disc
    def _is_vat(self, e: FileEntry) -> bool:
        if e.file_type == FT_VAT:
            return True
        return (e.file_type == 0 and e.embedded is not None and len(e.embedded) >= 36
                and e.embedded[-35:-35 + len(VAT150_ID)] == VAT150_ID)

    def _versions(self) -> None:
        virtual = next((i for i, m in enumerate(self.lvd.maps) if m.kind == "virtual"), None)
        if virtual is None:
            self.versions = [Version(None, None, None)]
        else:
            for sector in sorted(self.entries):
                e = self.entries[sector]
                if not self._is_vat(e):
                    continue
                try:
                    data = b"".join(self.pieces(e, self._physical_ref(virtual), None))
                    self.versions.append(Version(sector, parse_vat(data, e.file_type), e.modified))
                    self.visited.add(sector)
                except Exception as err:
                    self.problems.append((f"allocation table (VAT) at sector {sector}", err))
            if not self.versions:
                raise ValueError("the volume uses a virtual partition but no allocation table (VAT) was found")
        usable = []
        for index, v in enumerate(self.versions):
            where = f"sector {v.vat_sector}" if v.vat_sector is not None else "the volume"
            try:
                v.fsd_sector = self.physical(self.lvd.fsd.block, self.lvd.fsd.partition, v.vat)
                raw = self.read(v.fsd_sector, 1)
                v.fsd = parse_fsd(raw)
                v.serial = udf_serial32(raw[:512])
                usable.append(v)
                self._walk(v, len(usable) - 1, v.fsd.root, "", False, v.fsd_sector, 0)
            except Exception as err:
                self.problems.append((f"file set described by the allocation table at {where}", err))
        self.versions = usable
        if not usable:
            raise ValueError("no state of the volume could be read")

    def _walk(self, v: Version, index: int, icb: Extent, path: str, deleted: bool,
              named_by: int, depth: int) -> None:
        sector = self.physical(icb.block, icb.partition, v.vat)
        entry = self.entries.get(sector)
        if entry is None:
            raise ValueError(f"no valid file entry at sector {sector} for {path or chr(92)}")
        self.visited.add(sector)
        if entry.file_type != FT_DIRECTORY:
            if entry.file_type not in (0, FT_FILE, FT_REALTIME):
                self.problems.append((f"{path} (file entry at sector {sector})",
                                      ValueError(f"file type {entry.file_type} is not a regular file; not emitted")))
                return
            v.files.append(Listed(path, deleted, entry, sector, icb.partition, named_by, index))
            return
        if depth > 128:
            raise ValueError(f"folders nested deeper than 128 at {path}")
        if not deleted:
            v.folders.setdefault(entry.unique_id, path)
        fids, stopped = parse_fids(b"".join(self.pieces(entry, icb.partition, v.vat)))
        if stopped:
            self.problems.append((f"directory {path or chr(92)} at sector {sector}", ValueError(stopped)))
        for fid in fids:
            if fid.parent:
                continue
            child = path + "\\" + fid.name
            if fid.icb.length == 0:                     # UDF lets a deleted entry drop its address
                if deleted or fid.deleted:
                    v.nameless.append(child)
                else:
                    self.problems.append((f"{child} in the directory at sector {sector}",
                                          ValueError("directory entry gives no file entry address")))
                continue
            try:
                self._walk(v, index, fid.icb, child, deleted or fid.deleted, sector, depth + 1)
            except LookupError as err:
                if deleted or fid.deleted:
                    v.nameless.append(child)
                else:
                    self.problems.append((f"{child} in the directory at sector {sector}", err))
            except Exception as err:
                self.problems.append((f"{child} in the directory at sector {sector}", err))

    # -- what no state of the disc reaches
    def unreferenced(self) -> Tuple[List[int], List[Listed]]:
        """File entries no allocation table leads to -> (sectors of superseded copies of
        files that are listed somewhere, entries of files listed nowhere)."""
        known = {}
        for v in self.versions:
            for f in v.files:
                known[(f.entry.unique_id, f.entry.created)] = f
        folders = {}
        for v in self.versions:
            folders.update(v.folders)
        names: Dict[Tuple[int, int], Tuple[str, int]] = {}
        for sector, e in self.entries.items():
            if e.file_type == FT_DIRECTORY and e.embedded is not None:
                for fid in parse_fids(e.embedded)[0]:
                    if not fid.parent:
                        names.setdefault((fid.unique_id, fid.icb.block), (fid.name, e.unique_id))
        superseded, orphans = [], []
        for sector in sorted(set(self.entries) - self.visited):
            e = self.entries[sector]
            if self._is_vat(e) or e.file_type == FT_DIRECTORY:
                continue
            if (e.unique_id, e.created) in known:
                superseded.append(sector)
                continue
            name, parent = names.get((e.unique_id & 0xFFFFFFFF, e.tag.location), (None, None))
            if name is None:
                path = f"\\[file entry at sector {sector}]"
            else:
                path = folders.get(parent, f"\\[unlisted folder {parent}]") + "\\" + name
            try:
                partition = self._physical_ref()
            except LookupError:
                partition = 0
            orphans.append(Listed(path, True, e, sector, partition, -1, -1))
        return superseded, orphans

    def uncovered(self) -> List[Tuple[int, int]]:
        """Runs of non-zero sectors that no descriptor and no file entry accounts for."""
        covered = bytearray(self.sectors)
        try:
            physical = self._physical_ref()
        except LookupError:
            return []
        for e in self.entries.values():
            for ext in e.extents:
                part = physical if ext.partition is None else ext.partition
                if ext.kind != 0 or part >= len(self.lvd.maps) or self.lvd.maps[part].kind != "physical":
                    continue
                first = self.partitions.get(self.lvd.maps[part].number, (0, 0))[0] + ext.block
                last = min(first + (ext.length + SECTOR - 1) // SECTOR, self.sectors)
                covered[first:last] = b"\x01" * max(last - first, 0)
        out: List[Tuple[int, int]] = []
        for s in range(self.sectors):
            if self.sector_kind[s] == 1 and not covered[s]:
                if out and out[-1][0] + out[-1][1] == s:
                    out[-1] = (out[-1][0], out[-1][1] + 1)
                else:
                    out.append((s, 1))
        return out


# ---------------------------------------------------------------- the image, and rows

VRS_IDS = (b"CD001", b"BEA01", b"NSR02", b"NSR03", b"TEA01", b"BOOT2", b"CDW02")


def open_image(path) -> Tuple[Callable[[int, int], bytes], int, dict]:
    """-> (read(sector, count), sectors, what the container says about the disc)."""
    path = Path(path)
    segments = ewf_segments(path)
    with segments[0].open("rb") as fh:
        is_ewf = fh.read(8) in EWF_MAGIC
    info = {"sessions": [], "unreadable": []}
    if is_ewf:
        from dissect.evidence import EWF
        handles = [p.open("rb") for p in segments]
        ewf = EWF(handles)
        stream, size = ewf.open(), ewf.size
        for seg in segments:
            with seg.open("rb") as fh:
                info["sessions"] = info["sessions"] or ewf_sessions(fh)
                info["unreadable"] = info["unreadable"] or ewf_unreadable(fh)
    else:
        stream, size = path.open("rb"), path.stat().st_size
        handles = [stream]

    def read(sector: int, count: int) -> bytes:
        stream.seek(sector * SECTOR)
        return stream.read(count * SECTOR)

    info["close"] = lambda: [h.close() for h in handles] and None
    return read, size // SECTOR, info


def is_optical(path) -> bool:
    """True if the image starts with an optical-disc volume recognition sequence."""
    read, sectors, info = open_image(path)
    try:
        return sectors > 16 and read(16, 1)[1:6] in VRS_IDS
    finally:
        info["close"]()


@dataclass
class Survey:
    udf: Udf
    info: dict
    current: List[Listed]
    recovered: List[Tuple[Listed, dict]]        # (file, extra provenance)
    superseded: List[int]
    unreadable: frozenset

    def vat(self, f: Listed) -> Optional[Vat]:
        return self.udf.versions[f.version].vat if f.version >= 0 else None

    def content(self, f: Listed) -> Iterator[bytes]:
        return self.udf.pieces(f.entry, f.partition, self.vat(f), self.unreadable)

    def close(self) -> None:
        self.info["close"]()

    def session(self, sector: int) -> Optional[int]:
        starts = [s for _flags, s in self.info["sessions"]]
        if not starts:
            return None
        return max(1, sum(1 for s in starts if s <= sector))


def _times(f: Listed, zone: Optional[str]):
    created = stamp_utc(f.entry.created, zone) if f.entry.created is not None else None
    return created, stamp_utc(f.entry.modified, zone)


def survey(path, zone: Optional[str] = None) -> Survey:
    """Read the disc: its states, the files listed now, the files listed no more."""
    read, sectors, info = open_image(path)
    starts = sorted(s for _flags, s in info["sessions"])[1:]        # the first session starts the disc
    try:
        udf = Udf(read, sectors, starts).load()
    except Exception:
        info["close"]()
        raise
    unreadable = frozenset(s for first, count in info["unreadable"] for s in range(first, first + count))
    last = len(udf.versions) - 1
    current = [f for f in udf.versions[last].files if not f.deleted]

    def key(f: Listed):
        try:
            created, modified = _times(f, zone)
        except ValueError:
            return (f.path, f.entry.size, f.entry.created, f.entry.modified)
        return (f.path, f.entry.size, created and created[0], modified[0])

    live = {key(f) for f in current}
    found: Dict[tuple, Tuple[Listed, dict]] = {}
    for index in range(last, -1, -1):                   # newest state first: it holds the last word
        v = udf.versions[index]
        for f in v.files:
            k = key(f)
            if k in live or (index == last and not f.deleted):
                continue
            if k not in found:
                found[k] = (f, {"listed_by_allocation_tables_at_sectors": [],
                                "flagged_deleted_by_allocation_tables_at_sectors": []})
            which = ("flagged_deleted_by_allocation_tables_at_sectors" if f.deleted
                     else "listed_by_allocation_tables_at_sectors")
            if v.vat_sector is not None:
                found[k][1][which].insert(0, v.vat_sector)
            if v.recorded is not None:
                try:
                    when = iso(stamp_utc(v.recorded, zone)[0])
                    found[k][1]["first_flagged_deleted_utc" if f.deleted else "first_listed_utc"] = when
                    if not f.deleted:
                        found[k][1].setdefault("last_listed_utc", when)
                except ValueError:
                    pass
    superseded, orphans = udf.unreferenced()
    for f in orphans:
        found.setdefault(key(f), (f, {"note": "file entry that no allocation table leads to"}))
    recovered = sorted(found.values(), key=lambda x: (x[0].path, x[0].sector))
    return Survey(udf, info, current, recovered, superseded, unreadable)


def extract(ev, path, ctx) -> None:
    from .source_scope import merge_scope
    path = Path(path)
    common = merge_scope(ctx["common"], {'source_snapshot': 'optical-image', 'source_variant': 'primary'})
    examined = ctx["examined_at"]
    zone = ctx.get("pc_time_zone")
    disc = "disc " + common["exhibit"]
    area = "unallocated space of device " + disc
    try:
        emit_image_digests(ev, path, ctx)
    except Exception as e:
        ev.problem(f"{path.name} (E01 container)", e)
    try:
        if not is_optical(path):
            raise ValueError("no optical-disc volume recognition sequence at sector 16")
        s = survey(path, zone)
    except Exception as e:
        ev.problem(f"{path.name} (UDF volume)", e)
        return
    udf = s.udf
    for where, err in udf.problems:
        ev.problem(f"{path.name}: {where}", err)
    common = dict(common, parser=PARSER)

    # Read each descriptor itself, including descriptors no surviving VAT references.
    # A serial is only a 32-bit sum, so do not use it alone to deduplicate timestamps.
    recordings = {}
    recorded_groups = {}
    for sector, raw in sorted(udf.fsd_copies.items()):
        try:
            fsd = parse_fsd(raw)
            timestamp, conversion = stamp_utc(fsd.recorded, zone)
        except ValueError as e:
            ev.problem(f"{path.name}: UDF file set descriptor at sector {sector} recording time", e)
            continue
        recordings[sector] = (timestamp, conversion, fsd)
        recorded_groups.setdefault((udf_serial32(raw), timestamp), []).append(sector)

    # one row per distinct serial; the newest state that carries it describes it
    by_serial: Dict[int, Version] = {}
    for v in udf.versions:
        by_serial[v.serial] = v
    stray = {}
    for sector, raw in sorted(udf.fsd_copies.items()):
        stray.setdefault(udf_serial32(raw), []).append(sector)
    for serial, sectors_ in stray.items():
        v = by_serial.get(serial)
        fsd_sector = v.fsd_sector if v else sectors_[-1]
        label = (v.vat.label if v and v.vat and v.vat.label else None) or udf.lvd.label
        prov = dict(artifact=f"UDF file set descriptor at sector {fsd_sector} (byte offset {fsd_sector * SECTOR})",
                    filesystem="udf", udf_revision=udf.lvd.revision, volume_label=label,
                    volume_set=udf.volume_set, offset=fsd_sector * SECTOR,
                    serial_method="four byte-wise sums over the 512-byte file set descriptor, "
                                  "as the Windows UDF driver computes it",
                    identical_descriptor_copies_at_sectors=sectors_,
                    allocation_tables_at_sectors=[x.vat_sector for x in udf.versions
                                                  if x.serial == serial and x.vat_sector is not None],
                    states_of_the_volume=len(udf.versions),
                    referenced="by an allocation table" if v else "by no allocation table that survives",
                    partition_start_sector=min(p[0] for p in udf.partitions.values()),
                    sectors_in_image=udf.sectors,
                    sectors_the_imager_could_not_read=len(s.unreadable),
                    time_meaning=OBSERVED, **common)
        prov['source_variant'] = ('primary' if v is udf.versions[-1]
                                  else 'udf-descriptor:' + str(fsd_sector))
        session = s.session(fsd_sector)
        if session is not None:
            prov.update(session=session, track=session,
                        session_source=f"E01 session section ({len(s.info['sessions'])} entry)")
        if fsd_sector in recordings:
            prov["file_set_recorded_utc"] = iso(recordings[fsd_sector][0])
        ev.add("volumeOnDevice", examined, 1, disc, "%08X" % serial, **prov)

    # One event per disc/serial/recording-time; repeat FSD copies are provenance,
    # not extra events. Keep the examination observation above at examined_at.
    for (serial, timestamp), sectors_ in sorted(recorded_groups.items()):
        sector = sectors_[-1]
        _timestamp, conversion, fsd = recordings[sector]
        descriptor_scope = merge_scope(common, {'source_variant': (
            'primary' if sector == udf.versions[-1].fsd_sector else 'udf-descriptor:' + str(sector))})
        ev.add("volumeRecorded", timestamp, 1, disc, "%08X" % serial,
               artifact=f"UDF file set descriptor at sector {sector} (byte offset {sector * SECTOR})",
               filesystem="udf", udf_revision=udf.lvd.revision, volume_label=fsd.label,
               file_set=fsd.file_set, offset=sector * SECTOR,
               timestamp_offset=sector * SECTOR + 16,
               timestamp_bytes=fsd.recorded.hex(), time_zone=conversion,
               equivalent_record_copies_at_sectors=sectors_,
               referenced_by_allocation_tables_at_sectors=[
                   v.vat_sector for v in udf.versions
                   if v.fsd_sector in sectors_ and v.vat_sector is not None],
               time_meaning="UDF file-set descriptor recording time",
               note="This timestamp does not by itself establish a format action, "
                    "the start of writing files, or completion of a write.", **descriptor_scope)

    seen = set()

    def rows(f: Listed, aux: str, extra: dict) -> bool:
        try:
            created, modified = _times(f, zone)
        except ValueError as e:
            ev.problem(f"{path.name}: {f.path} (file entry at sector {f.sector})", e)
            return False
        v = udf.versions[f.version] if f.version >= 0 else None
        kind = "extended file entry" if f.entry.extended else "file entry"
        named = (f", named by the directory at sector {f.directory_sector}"
                 if f.directory_sector >= 0 else "")
        base = dict(artifact=f"UDF {kind} at sector {f.sector} (byte offset {f.sector * SECTOR}){named}",
                    size=f.entry.size, unique_id=f.entry.unique_id, **extra)
        base = merge_scope(common, base)
        if extra.get('recovered'):
            base['source_variant'] = 'udf-recovered-entry:' + str(f.sector)
        if v is not None and v.vat_sector is not None:
            base["allocation_table_at_sector"] = v.vat_sector
        session = s.session(f.sector)
        if session is not None:
            base["session"] = session
        if created is None:
            ev.problem(f"{path.name}: {f.path} (file entry at sector {f.sector})",
                       ValueError("plain file entry: it records no creation time; only fileModified emitted"))
        elif ("fileCreated", created[0], f.path, aux) not in seen:
            seen.add(("fileCreated", created[0], f.path, aux))
            ev.add("fileCreated", created[0], 1, f.path, aux, time_zone=created[1], **base)
        if ("fileModified", modified[0], f.path, aux) not in seen:
            seen.add(("fileModified", modified[0], f.path, aux))
            ev.add("fileModified", modified[0], 1, f.path, aux, time_zone=modified[1], **base)
        return True

    for f in s.current:
        rows(f, "%08X" % udf.versions[f.version].serial, {})
    n = sum(rows(f, area, dict(recovered=True, **extra)) for f, extra in s.recovered)

    loose = udf.uncovered()
    if loose:
        from .content import signature_of
        for first, count in loose:
            label = signature_of(udf.read(first, 1))[0]
            ev.problem(f"{path.name}: sectors {first}-{first + count - 1}",
                       ValueError(f"content that no file entry describes (leading bytes: {label}); "
                                  f"no name, size or time survives, so no file row was emitted"))
    nameless = sorted({name for v in udf.versions for name in v.nameless})
    if n or loose or nameless:
        ev.add("unallocatedOnDevice", examined, 1, disc, area,
               artifact="UDF directory entries flagged deleted, and file entries reachable only "
                        "through allocation tables (VAT) older than the current one",
               file_entries=n, earlier_states_of_the_volume=len(udf.versions) - 1,
               current_allocation_table_at_sector=udf.versions[-1].vat_sector,
               superseded_copies_of_file_entries_not_emitted=len(s.superseded),
               superseded_copies_at_sectors=s.superseded,
               deleted_names_without_a_file_entry=nameless,
               runs_of_content_without_a_file_entry=[list(x) for x in loose],
               time_meaning=OBSERVED, **common)
    s.close()
