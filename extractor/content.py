"""File contents: one `fileContent` row (SHA-256) for every file that has a
`fileCreated` row, on the removable media, the optical disc and the PC's user folders.

The path in `obj` is built exactly the way the module that emits the file's
`fileCreated` row builds it (extractor/media.py, extractor/windows.py,
extractor/optical.py), and `prov["location"]` repeats that row's `aux`.

A recovered FAT entry has no allocation chain any more. Its content is read as one
contiguous run from its first cluster, and `prov["read_as"]` says so. No hash is
emitted when that run cannot be trusted: it leaves the volume, touches clusters that
are in use now, or collides with another recovered file or folder.

The helpers above `extract` are plain byte parsing; dissect is imported inside the
functions that open an image.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from . import optical
from .acquisition import area, fallback, provenance

OBSERVED = "when the image was examined, not an event on the device"
FAT_EPOCH = 315532800           # what an unset FAT timestamp decodes to (see extractor/media.py)
HEAD = 4096

# ---------------------------------------------------------------- file signatures

ZIP_OFFICE = "zip-based office document"
OLE_OFFICE = "legacy OLE office document"

MAGIC = (                       # (offset, leading bytes, file type)
    (0, b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1", OLE_OFFICE),
    (0, b"%PDF-", "pdf"),
    (0, b"\xFF\xD8\xFF", "jpeg"),
    (0, b"\x89PNG\r\n\x1a\n", "png"),
    (0, b"GIF87a", "gif"),
    (0, b"GIF89a", "gif"),
    (0, b"II*\x00", "tiff"),
    (0, b"MM\x00*", "tiff"),
    (0, b"7z\xBC\xAF\x27\x1C", "7z"),
    (0, b"Rar!\x1A\x07", "rar"),
    (0, b"\x1F\x8B\x08", "gzip"),
    (0, b"SQLite format 3\x00", "sqlite"),
    (0, b"L\x00\x00\x00\x01\x14\x02\x00", "windows shortcut"),
    (0, b"{\\rtf", "rtf"),
    (0, b"#!AMR", "amr"),
    (0, b"\xE4\x52\x5C\x7B\x8C\xD8\xA7\x4D\xAE\xB1\x53\x78\xD0\x29\x96\xD3", "onenote"),
    (0, b"\x30\x26\xB2\x75\x8E\x66\xCF\x11", "asf"),
    (0, b"ID3", "mp3"),
    (0, b"OggS", "ogg"),
    (0, b"fLaC", "flac"),
    (4, b"ftyp", "mp4"),
    (0, b"<?xml", "xml"),
    (0, b"<svg", "svg"),
    (0, b"MZ", "windows executable"),
)
RIFF = {b"AVI ": "avi", b"WAVE": "wav", b"WEBP": "webp"}

EXTENSIONS = {                  # extensions that are ordinary for a file type
    ZIP_OFFICE: "docx docm dotx pptx pptm ppsx potx xlsx xlsm xltx xps oxps vsdx odt ods odp",
    OLE_OFFICE: "doc dot xls xlt ppt pps pot msg vsd pub",
    "zip": "zip jar xps oxps", "pdf": "pdf", "jpeg": "jpg jpeg jpe jfif", "png": "png", "gif": "gif",
    "bmp": "bmp dib", "tiff": "tif tiff", "7z": "7z", "rar": "rar", "gzip": "gz tgz",
    "sqlite": "sqlite sqlite3 db", "windows shortcut": "lnk", "rtf": "rtf", "amr": "amr",
    "onenote": "one", "asf": "asf wmv wma", "mp3": "mp3", "ogg": "ogg oga ogv", "flac": "flac",
    "mp4": "mp4 m4a m4v mov 3gp", "xml": "xml xsl xsd config manifest", "svg": "svg",
    "windows executable": "exe dll sys scr ocx cpl mui", "avi": "avi", "wav": "wav", "webp": "webp",
}
EXTENSIONS = {k: frozenset(v.split()) for k, v in EXTENSIONS.items()}


def zip_names(head: bytes) -> List[str]:
    """Names in the local file headers that lie inside the leading bytes of a zip."""
    names, off = [], 0
    while off + 30 <= len(head) and head[off:off + 4] == b"PK\x03\x04":
        flags, = struct.unpack_from("<H", head, off + 6)
        packed, = struct.unpack_from("<I", head, off + 18)
        n_len, x_len = struct.unpack_from("<HH", head, off + 26)
        names.append(head[off + 30:off + 30 + n_len].decode("utf-8", "replace"))
        if flags & 0x08:                    # sizes follow the data: the next header cannot be located
            break
        off += 30 + n_len + x_len + packed
    return names


def signature_of(head: bytes) -> Tuple[str, str]:
    """(file type the leading bytes indicate, detail); ("unknown", "") if none is known."""
    if head[:4] == b"PK\x03\x04":
        names = zip_names(head)
        if names and names[0] == "[Content_Types].xml":
            for prefix, detail in (("word/", "word"), ("ppt/", "powerpoint"), ("xl/", "excel")):
                if any(n.startswith(prefix) for n in names):
                    return ZIP_OFFICE, detail
            return ZIP_OFFICE, "open packaging container"
        if names and names[0] == "mimetype" and b"application/vnd.oasis.opendocument" in head[:128]:
            return ZIP_OFFICE, "opendocument"
        return "zip", ""
    if head[:4] == b"RIFF" and head[8:12] in RIFF:
        return RIFF[head[8:12]], ""
    if head[:2] == b"BM" and len(head) >= 10 and head[6:10] == b"\x00\x00\x00\x00":
        return "bmp", ""
    for offset, magic, name in MAGIC:
        if head[offset:offset + len(magic)] == magic:
            return name, ""
    return "unknown", ""


def extension_of(name: str) -> str:
    """Lower-case extension without the dot; "" if the name has none."""
    base = name.replace("/", "\\").rsplit("\\", 1)[-1]
    return base.rsplit(".", 1)[1].lower() if "." in base.strip(".") else ""


def digest_of(chunks: Iterable[bytes]) -> Tuple[str, int, bytes]:
    """-> (sha256 hex, number of bytes, leading bytes)."""
    h, size, head = hashlib.sha256(), 0, b""
    for chunk in chunks:
        if len(head) < HEAD:
            head += chunk[:HEAD - len(head)]
        h.update(chunk)
        size += len(chunk)
    return h.hexdigest(), size, head


# ---------------------------------------------------------------- recovered FAT entries

def contiguous_run(first_cluster: int, size: int, cluster_size: int, data_start: int,
                   volume_end: int) -> Tuple[int, int]:
    """Where a file sits if it is one unbroken run: (volume byte offset, clusters)."""
    count = -(-size // cluster_size)
    if count == 0:
        return data_start, 0
    if first_cluster < 2:
        raise ValueError(f"first cluster {first_cluster} is not a data cluster")
    offset = data_start + (first_cluster - 2) * cluster_size
    if offset + count * cluster_size > volume_end:
        raise ValueError(f"a contiguous run of {count} clusters from cluster {first_cluster} "
                         f"goes past the end of the volume")
    return offset, count


def _collide(files: Sequence[Tuple[int, int]], cluster_size: int) -> bool:
    """True if two of the (first cluster, size) runs would share a cluster."""
    end = None
    for first, size in sorted(files):
        if size <= 0:
            continue
        if end is not None and first < end:
            return True
        end = first + -(-size // cluster_size)
    return False


def older_layout(folder_offset: int, own_cluster: int, files: Sequence[Tuple[int, int]],
                 sector_size: int = 512, largest: int = 65536) -> Tuple[int, int]:
    """Cluster size and data-area start of an earlier layout of the device, of which
    only one folder survives. The folder was found at `folder_offset` (bytes into the
    volume) and its "." entry says it was cluster `own_cluster`. Nothing on the device
    records the old cluster size any more, so it is derived: it must be a power of two,
    the folder's files (each one contiguous run) must not overlap each other or the
    folder, and the data area must start inside the volume. Raises ValueError unless
    exactly one size fits."""
    if own_cluster < 2:
        raise ValueError("the folder's own cluster number is not a data cluster")
    fits = []
    size = sector_size
    while size <= largest:
        start = folder_offset - (own_cluster - 2) * size
        if start >= 0 and not _collide(list(files) + [(own_cluster, 1)], size):
            fits.append((size, start))
        size *= 2
    if len(fits) != 1:
        raise ValueError(f"{len(fits)} cluster sizes fit the older layout this folder comes from; "
                         f"its cluster numbers cannot be turned into positions")
    return fits[0]


def fat_in_use(fat: bytes, cluster: int) -> bool:
    return struct.unpack_from("<I", fat, cluster * 4)[0] & 0x0FFFFFFF != 0


# ---------------------------------------------------------------- rows

def _row(ev, ctx, obj: str, digest: str, size: int, head: bytes, location: str, artifact: str,
         **extra) -> None:
    signature, detail = signature_of(head)
    extension = extension_of(obj)
    prov = dict(artifact=artifact, size=size, location=location, signature=signature,
                extension=extension, leading_bytes=head[:8].hex(), time_meaning=OBSERVED,
                **extra, **ctx["common"])
    if detail:
        prov["signature_detail"] = detail
    if ctx.get("acquisition"):
        prov.update(provenance(ctx["acquisition"]))
    if signature != "unknown":
        prov["extension_fits_signature"] = extension in EXTENSIONS.get(signature, ())
    ev.add("fileContent", ctx["examined_at"], 1, obj, "sha256:" + digest, **prov)


def _stream(fh, size: Optional[int] = None, step: int = 1 << 20):
    left = size
    while left is None or left > 0:
        data = fh.read(step if left is None else min(step, left))
        if not data:
            return
        if left is not None:
            left -= len(data)
        yield data


def _pc(ev, target, ctx) -> None:
    """Files under each user profile's Desktop, Documents and Downloads: the files
    extractor/windows.py gives fileCreated rows to, walked the same way."""
    try:
        from .windows import USER_DIRS
    except Exception:
        USER_DIRS = ("Desktop", "Documents", "Downloads")
    import re
    from .profiles import user_profiles, ntfs_volume_serial
    for user in user_profiles(target):
        vsn = ntfs_volume_serial(target, user)
        for d in USER_DIRS:
            top = user.joinpath(d)
            if not top.exists():
                continue
            for p in sorted(top.rglob("*"), key=str):
                rel = str(p).replace("/", "\\")
                rel = rel[2:] if re.match(r"^[A-Za-z]:", rel) else rel
                try:
                    if not p.is_file():
                        continue
                    recorded = p.lstat().st_size
                    with p.open("rb") as fh:
                        digest, size, head = digest_of(_stream(fh))
                    if size != recorded:
                        raise ValueError(f"read {size} bytes; the file record says {recorded}")
                except Exception as e:
                    ev.problem(f"content of {rel}", e)
                    continue
                _row(ev, ctx, rel, digest, size, head, vsn,
                     f"NTFS $DATA of {rel}", account=user.name)


def _recovered(ev, vol, fs, ctx, identity: dict) -> None:
    """Content of the entries extractor/media.py recovers from unallocated FAT32 clusters."""
    from .fatcarve import carve_fat32, folder_paths
    bpb = fs.fatfs.bpb
    if bpb.BPB_RootEntCnt != 0:                      # FAT12/16: media.py recovers nothing there
        return
    bps, spc, rsv, nf = bpb.BPB_BytsPerSec, bpb.BPB_SecPerClus, bpb.BPB_RsvdSecCnt, bpb.BPB_NumFATs
    fat_sectors, total = fs.fatfs.bpb_ext.BPB_FATSz32, bpb.BPB_TotSec32
    found = carve_fat32(vol, bps, spc, rsv, nf, fat_sectors, total)
    if not found:
        return
    image = ctx["common"]["image"]
    location = area(identity)
    paths = folder_paths(found)
    cluster_size = bps * spc
    data_start = (rsv + nf * fat_sectors) * bps
    clusters = (total * bps - data_start) // cluster_size
    volume_end = data_start + clusters * cluster_size
    vol.seek(rsv * bps)
    fat = vol.read(min(fat_sectors * bps, (clusters + 2) * 4))

    plans = []                  # [obj, entry, folder cluster, offset, clusters, cluster size, older start]
    for cluster in sorted(found):
        d = found[cluster]
        files = [e for e in d.entries if not e.is_dir and e.created is not None and e.modified is not None]
        size_here, start_here, older = cluster_size, data_start, None
        if d.own != cluster and files:
            try:
                size_here, start_here = older_layout(data_start + (cluster - 2) * cluster_size, d.own,
                                                     [(e.first_cluster, e.size) for e in files], bps)
                older = start_here
            except ValueError as err:
                for e in files:
                    ev.problem(f"{image} content of {paths[cluster]}\\{e.name}", err)
                continue
        for e in files:
            obj = paths[cluster] + "\\" + e.name
            try:
                offset, count = contiguous_run(e.first_cluster, e.size, size_here, start_here, volume_end)
                if count and offset < data_start:
                    raise ValueError("the run lies in the area the current file system keeps for itself")
                first = 2 + (offset - data_start) // cluster_size
                last = 2 + (offset + count * size_here - 1 - data_start) // cluster_size
                used = [c for c in range(first, last + 1) if count and fat_in_use(fat, c)]
                if used:
                    raise ValueError(f"the run enters clusters now allocated to something else "
                                     f"(first: cluster {used[0]})")
            except ValueError as err:
                ev.problem(f"{image} content of {obj} (first cluster {e.first_cluster}, size {e.size})", err)
                continue
            plans.append([obj, e, cluster, offset, count, size_here, older])

    # two recovered things cannot own the same bytes; if they claim to, neither is trusted
    spans = [(p[3], p[3] + p[4] * p[5], i) for i, p in enumerate(plans) if p[4]]
    spans += [(data_start + (c - 2) * cluster_size, data_start + (c - 1) * cluster_size, None) for c in found]
    spans.sort(key=lambda s: (s[0], s[1]))
    bad = {}
    reach, holder = -1, None
    for begin, end, who in spans:
        if begin < reach:
            for i, other in ((who, holder), (holder, who)):
                if i is not None:
                    bad[i] = ("a recovered folder" if other is None else plans[other][0])
        if end > reach:
            reach, holder = end, who
    for i, p in enumerate(plans):
        obj, e, cluster, offset, count, size_here, older = p
        if i in bad:
            ev.problem(f"{image} content of {obj} (first cluster {e.first_cluster}, size {e.size})",
                       ValueError(f"read as one contiguous run it would share clusters with {bad[i]}"))
            continue
        try:
            vol.seek(offset)
            digest, size, head = digest_of(_stream(vol, e.size))
            if size != e.size:
                raise ValueError(f"read {size} of {e.size} bytes")
        except Exception as err:
            ev.problem(f"{image} content of {obj}", err)
            continue
        if count == 0:
            read_as = "empty file: its directory entry records size 0, so there is nothing to read"
        elif older is None:
            read_as = (f"one contiguous run of {count} clusters from the first cluster "
                       f"({e.first_cluster}); the allocation table no longer describes this file, "
                       f"so a fragmented file would hash wrongly")
        else:
            read_as = (f"one contiguous run of {count} clusters of {size_here} bytes from the first "
                       f"cluster ({e.first_cluster}), counted in an older layout of the device. That "
                       f"layout's cluster size and data-area start (volume byte {older}) are recorded "
                       f"nowhere any more; they were derived as the only power-of-two cluster size at "
                       f"which this folder's files do not overlap and the data area starts inside the volume")
        _row(ev, ctx, obj, digest, size, head, location,
             f"FAT directory entry in unallocated cluster {cluster}; content at volume byte offset {offset}",
             recovered=True, first_cluster=e.first_cluster, clusters=count, cluster_size=size_here,
             volume_offset=offset, layout="current" if older is None else "older, derived",
             read_as=read_as)


def _exfat_chunks(fs, entry, step: int = 1 << 20):
    """Content of an exFAT file, read from its run list.

    dissect's own ExfatFileEntry.open() (dissect.target 3.25) hands the run list, which
    counts in sectors, to a stream that counts in clusters, and so returns bytes from
    the wrong place. The run list itself is right, so it is read here in sectors."""
    ex = fs.exfat
    stream = entry.entry[0].stream
    left = stream.data_length
    valid = getattr(stream, "valid_data_length", left)     # bytes past this were never written: zeros
    done = 0
    if stream.flags.not_fragmented:
        runs = ex.runlist(stream.location, True, left)
    else:
        runs = ex.runlist(stream.location, False)
    for sector, count in runs:
        if left <= 0:
            break
        if sector is None:
            raise ValueError("run list names no sector")
        ex.filesystem.seek(sector * ex.sector_size)
        want = min(count * ex.sector_size, left)
        while want > 0:
            data = ex.filesystem.read(min(step, want))
            if not data:
                raise ValueError("the run list leaves the volume")
            want -= len(data)
            left -= len(data)
            keep = min(max(valid - done, 0), len(data))
            done += len(data)
            yield data if keep == len(data) else data[:keep] + bytes(len(data) - keep)
    if left > 0:
        raise ValueError(f"the allocation chain is {left} bytes shorter than the file")


def _removable(ev, target, ctx, identity: dict) -> None:
    image = ctx["common"]["image"]
    for vol in target.volumes:
        fs = vol.fs
        kind = getattr(fs, "__type__", None)
        if kind not in ("fat", "exfat"):
            continue
        serial = fs.exfat.vbr.volume_serial if kind == "exfat" else int(fs.fatfs.volume_id, 16)
        vsn = "%08X" % serial
        for dirpath, _dirs, names in fs.walk("/"):
            for name in names:
                p = fs.path(dirpath).joinpath(name)
                rel = str(p).replace("/", "\\")
                try:
                    st = p.lstat()
                    if kind == "fat" and dirpath == "/" and st.st_size == 0 and st.st_ctime == FAT_EPOCH:
                        continue                        # the volume-label entry, not a file
                    if kind == "exfat":
                        digest, size, head = digest_of(_exfat_chunks(fs, p.get()))
                    else:
                        with p.open("rb") as fh:
                            digest, size, head = digest_of(_stream(fh))
                    if size != st.st_size:
                        raise ValueError(f"read {size} bytes; the directory entry says {st.st_size}")
                except Exception as e:
                    ev.problem(f"{image} content of {rel}", e)
                    continue
                _row(ev, ctx, rel, digest, size, head, vsn,
                     f"content of {rel}, read through its {kind} allocation chain")
        if kind == "fat":
            try:
                _recovered(ev, vol, fs, ctx, identity)
            except Exception as e:
                ev.problem(f"{image} recovered entries", e)


def _disc(ev, path: Path, ctx) -> None:
    """Every file extractor/optical.py gives a fileCreated row to: listed now, or recovered."""
    zone = ctx.get("pc_time_zone")
    s = optical.survey(path, zone)
    try:
        _disc_rows(ev, path, ctx, s, zone)
    finally:
        s.close()


def _disc_rows(ev, path: Path, ctx, s, zone) -> None:
    area = "unallocated space of device disc " + ctx["common"]["exhibit"]
    todo = [(f, "%08X" % s.udf.versions[f.version].serial, {}) for f in s.current]
    todo += [(f, area, {"recovered": True}) for f, _extra in s.recovered]
    cache, seen = {}, set()
    for f, location, extra in todo:
        where = f"{path.name} content of {f.path} (file entry at sector {f.sector})"
        try:
            if optical._times(f, zone)[0] is None:
                continue                                # no fileCreated row exists for it
        except ValueError:
            continue                                    # optical.py reports the unreadable time
        key = (tuple(f.entry.extents), f.entry.size, f.entry.embedded, f.partition)
        try:
            if key not in cache:
                runs = [] if f.entry.embedded is not None else s.udf.runs(f.entry, f.partition, s.vat(f))
                cache[key] = digest_of(s.content(f)) + (runs,)
            digest, size, head, runs = cache[key]
            if size != f.entry.size:
                raise ValueError(f"read {size} bytes; the file entry says {f.entry.size}")
        except Exception as e:
            ev.problem(where, e)
            continue
        if (f.path, digest, location) in seen:
            continue
        seen.add((f.path, digest, location))
        placed = [r for r in runs if r[0] is not None]
        extra = dict(extra, extents=len(runs), read_as="the extents its UDF file entry lists")
        if placed:
            extra["first_sector"] = placed[0][0]
        session = s.session(f.sector)
        if session is not None:
            extra["session"] = session
        _row(ev, ctx, f.path, digest, size, head, location,
             f"content described by the UDF file entry at sector {f.sector}",
             parser=optical.PARSER, **extra)


def extract(ev, path, ctx) -> None:
    target = None
    if not isinstance(path, (str, Path)):           # an open dissect Target
        target, path = path, Path(str(path.path))
    path = Path(path)
    identity = ctx.get("acquisition") or fallback(path.name, ctx["common"]["exhibit"])
    ctx = dict(ctx, acquisition=identity)
    try:
        optical.emit_image_digests(ev, path, ctx)
    except Exception as e:
        ev.problem(f"{path.name} (E01 container)", e)
    try:
        disc = identity.get("is_optical")
        if disc is None:
            disc = optical.is_optical(path)
    except Exception:
        disc = False
    try:
        if disc:
            _disc(ev, path, ctx)
            return
        if target is None:
            from dissect.target import Target
            target = Target.open(path)
        if str(target.os) == "windows":
            _pc(ev, target, ctx)
        else:
            _removable(ev, target, ctx, identity)
    except Exception as e:
        ev.problem(f"{path.name} (file contents)", e)
