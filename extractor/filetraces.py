"""What the PC remembers about folders and files, apart from the files themselves.

    folderOpened  shell bags of every user hive, typed paths, Run dialog paths, network
                  drive lists, mount points, Office recent places, open/save dialog folders
    fileSeen      desktop search index, thumbnail caches, recent-document lists, Office
                  and other per-application recent-file lists, print spool traces, files
                  that a shadow copy still holds but the live volume does not
    shadowCopy    every volume shadow copy
    fileRenamed   every rename in the NTFS change journal
    fileCreationRecorded  the first retained CREATE-flag observation per journal close cycle
    fileRemoved   the first retained DELETE-flag observation per journal close cycle

Every row is read from bytes of the image. Parsing helpers at the top are pure Python
(no dissect), so they can be tested on synthetic bytes; dissect is imported lazily.
"""
from __future__ import annotations

import re
import json
import struct
import uuid
from datetime import datetime, timedelta, timezone

from .store import us, us_from_filetime, us_from_unix
from .attributes import emit_attribute
from .journal_paths import JournalRanges
from .source_scope import merge_scope, subject_scope, vss_snapshot

# --------------------------------------------------------------------------- pure helpers

PATH_LIKE = re.compile(r"^(?:[A-Za-z]:\\|\\\\[^\\])")
OFFICE_MRU = re.compile(r"^\[F([0-9A-Fa-f]+)\]\[T([0-9A-Fa-f]+)\](?:\[O[0-9A-Fa-f]+\])?\*(.*)$", re.S)
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# Shell namespace identifiers documented by Microsoft (CLSIDs and KNOWNFOLDERIDs).
KNOWN_GUIDS = {
    "20d04fe0-3aea-1069-a2d8-08002b30309d": "My Computer",
    "208d2c60-3aea-1069-a2d7-08002b30309d": "Network",
    "f02c1a0d-be21-4350-88b0-7367fc96ef3c": "Network",
    "031e4825-7b94-4dc3-b131-e946b44c8dd5": "Libraries",
    "26ee0668-a00a-44d7-9371-beb064c98683": "Control Panel",
    "21ec2020-3aea-1069-a2dd-08002b30309d": "Control Panel",
    "645ff040-5081-101b-9f08-00aa002f954e": "Recycle Bin",
    "450d8fba-ad25-11d0-98a8-0800361b1103": "My Documents",
    "374de290-123f-4565-9164-39c4925e467b": "Downloads",
    "b4bfcc3a-db2c-424c-b029-7fe99a87c641": "Desktop",
    "fdd39ad0-238f-46af-adb4-6c85480369c7": "Documents",
    "33e28130-4e1e-4676-835a-98395c3bc3bb": "Pictures",
    "4bd8d571-6d19-48d3-be97-422220080e43": "Music",
    "18989b1d-99b5-455b-841c-ab7c74e4ddfc": "Videos",
    "7b0db17d-9cd2-4a93-9733-46cc89022e7c": "Documents",
    "a990ae9f-a03b-4e80-94bc-9912d7504104": "Pictures",
    "2112ab0a-c86a-4ffe-a368-0de96e47012e": "Music",
    "491e922f-5643-4af4-a7eb-4e7a138d8174": "Videos",
    "59031a47-3f72-44a7-89c5-5595fe6b30ee": "Users Files",
}
USERS_FILES = "59031a47-3f72-44a7-89c5-5595fe6b30ee"     # namespace root = the user's profile folder
CONTROL_PANEL_CATEGORIES = {
    0: "All Control Panel Items", 1: "Appearance and Personalization", 2: "Hardware and Sound",
    3: "Network and Internet", 4: "Sounds, Speech, and Audio Devices", 5: "System and Security",
    6: "Clock, Language, and Region", 7: "Ease of Access", 8: "Programs", 9: "User Accounts",
    10: "Security Center", 11: "Mobile PC",
}
ITEM_NAME_DISPLAY = ("b725f130-47ef-101a-a5f1-02608c9eebac", 10)
NAMED_PROPERTIES = "d5cdd505-2e9c-101b-9397-08002b2cf9ae"
PROPERTY_VIEW_SIGNATURES = (0x10141981, 0x23A3DFD5, 0x23FEBBEE, 0x3B93AFBB, 0xBEEBEE00)
DRIVE_CLASSES = (0x23, 0x25, 0x29, 0x2A, 0x2F)
FILE_CLASSES = (0x30, 0x31, 0x32, 0x35, 0x36, 0xB1)
NETWORK_CLASSES = (0x41, 0x42, 0x46, 0x47, 0x4C, 0xC3)

USN_FILE_CREATE, USN_FILE_DELETE = 0x100, 0x200
USN_RENAME_OLD, USN_RENAME_NEW = 0x1000, 0x2000
USN_CLOSE = 0x80000000


def _u16(buf, off):
    return struct.unpack_from("<H", buf, off)[0]


def _u32(buf, off):
    return struct.unpack_from("<I", buf, off)[0]


def iso(t_us: int) -> str:
    return (EPOCH + timedelta(microseconds=t_us)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def dos_datetime(date: int, time: int):
    """FAT date and time words -> 'YYYY-MM-DD HH:MM:SS' exactly as stored, or None."""
    day, month, year = date & 0x1F, (date >> 5) & 0x0F, 1980 + (date >> 9)
    sec, minute, hour = (time & 0x1F) * 2, (time >> 5) & 0x3F, time >> 11
    if not (1 <= day <= 31 and 1 <= month <= 12 and hour < 24 and minute < 60 and sec < 60):
        return None
    return "%04d-%02d-%02d %02d:%02d:%02d" % (year, month, day, hour, minute, sec)


def utf16_strings(buf: bytes, min_chars: int = 4, limit: int = 6) -> list:
    found = re.findall(rb"(?:[\x20-\x7e]\x00){%d,}" % min_chars, bytes(buf))
    return [s.decode("utf-16-le") for s in found[:limit]]


def split_idlist(buf: bytes) -> list:
    """A shell item id list -> the raw bytes of each item (size word included)."""
    out, off = [], 0
    while off + 2 <= len(buf):
        size = _u16(buf, off)
        if size < 2 or off + size > len(buf):
            break
        out.append(bytes(buf[off:off + size]))
        off += size
    return out


def property_strings(buf: bytes) -> list:
    """String values of every serialized property store ('1SPS') inside a shell item:
    [(format id, property id or name, text)]."""
    out, pos = [], 0
    while True:
        i = buf.find(b"1SPS", pos)
        if i < 0:
            break
        pos = i + 4
        if i < 4 or i + 20 > len(buf):
            continue
        start = i - 4
        size = _u32(buf, start)
        end = min(len(buf), start + size) if size >= 24 else len(buf)
        fmtid = str(uuid.UUID(bytes_le=bytes(buf[i + 4:i + 20])))
        p = i + 20
        while p + 9 <= end:
            vsize = _u32(buf, p)
            if vsize < 9 or p + vsize > end:
                break
            q = p + 4
            if fmtid == NAMED_PROPERTIES:
                nsize = _u32(buf, q)
                key = bytes(buf[q + 5:q + 5 + nsize]).decode("utf-16-le", "replace").rstrip("\x00")
                q += 5 + nsize
            else:
                key = _u32(buf, q)
                q += 5
            if q + 8 <= p + vsize and _u16(buf, q) == 0x1F:          # VT_LPWSTR
                chars = _u32(buf, q + 4)
                text = bytes(buf[q + 8:min(q + 8 + 2 * chars, p + vsize)])
                out.append((fmtid, key, text.decode("utf-16-le", "replace").split("\x00")[0]))
            p += vsize
    return out


def beef0004(buf: bytes):
    """The first file-entry extension block (signature 0xBEEF0004) of a shell item:
    {'long_name', 'created', 'accessed'} or None."""
    q = buf.find(b"\x04\x00\xef\xbe")
    if q < 4 or q + 14 > len(buf):
        return None
    ext = q - 4
    version = _u16(buf, ext + 2)
    out = {"created": dos_datetime(_u16(buf, ext + 8), _u16(buf, ext + 10)),
           "accessed": dos_datetime(_u16(buf, ext + 12), _u16(buf, ext + 14)), "long_name": ""}
    p = ext + 18
    if version >= 7:
        p += 18
    if version >= 3:
        p += 2
    if version >= 9:
        p += 4
    if version >= 8:
        p += 4
    if version >= 3 and p < len(buf):
        raw = bytes(buf[p:])
        raw = raw[:len(raw) - len(raw) % 2]
        out["long_name"] = raw.decode("utf-16-le", "replace").split("\x00")[0]
    return out


def _file_entry(buf: bytes, name_at: int = 14) -> dict:
    cls = buf[2]
    if cls & 0x04:
        raw = bytes(buf[name_at:])
        primary = raw[:len(raw) - len(raw) % 2].decode("utf-16-le", "replace").split("\x00")[0]
    else:
        primary = bytes(buf[name_at:]).split(b"\x00")[0].decode("cp1252", "replace")
    ext = beef0004(buf) or {}
    it = {"type": "folder" if cls & 0x01 else "file" if cls & 0x02 else "file system item",
          "name": ext.get("long_name") or primary}
    if primary and primary != it["name"]:
        it["short_name"] = primary
    if len(buf) >= name_at:
        it["size"] = _u32(buf, name_at - 10)
        modified = dos_datetime(_u16(buf, name_at - 6), _u16(buf, name_at - 4))
        if modified:
            it["item_modified"] = modified
    for k in ("created", "accessed"):
        if ext.get(k):
            it["item_" + k] = ext[k]
    return it


def _zip_item(buf: bytes):
    """An entry inside a compressed (zip) folder: name length at 0x54, name at 0x5C."""
    n = len(buf)
    if n < 0x60:
        return None
    n1, n2 = _u32(buf, 0x54), _u32(buf, 0x58)
    end = 0x5C + 2 * n1
    if not 0 < n1 < 260 or n2 > 1024 or end + 2 > n or bytes(buf[end:end + 2]) != b"\x00\x00":
        return None
    try:
        name = bytes(buf[0x5C:end]).decode("utf-16-le")
    except UnicodeDecodeError:
        return None
    if "\x00" in name or not name.isprintable():
        return None
    parent = bytes(buf[end + 2:end + 2 + 2 * n2]).decode("utf-16-le", "replace").split("\x00")[0]
    return name, parent


def parse_shell_item(buf: bytes, guid_names: dict = None) -> dict:
    """One shell item -> {'type', 'name', ...}. Only what the bytes hold; an item this
    code does not understand keeps a placeholder name and its readable strings."""
    names = guid_names or {}

    def guid_name(raw):
        g = str(uuid.UUID(bytes_le=bytes(raw)))
        return g, names.get(g) or KNOWN_GUIDS.get(g) or "{%s}" % g

    n = len(buf)
    if n < 3:
        return {"type": "unknown", "name": "<empty shell item>"}
    cls = buf[2]
    sig4 = _u32(buf, 4) if n >= 8 else None
    sig6 = _u32(buf, 6) if n >= 10 else None
    if sig4 == 0x4D677541 and n >= 0x24:                       # 'AugM': CD burn staging
        inner = bytes(buf[0x14:0x14 + _u16(buf, 0x14)])
        if len(inner) >= 16:
            it = _file_entry(inner)
            it["type"] = "cd burn folder"
            return it
    if sig4 == 0x39DE2184 and n >= 12:
        cat = _u32(buf, 8)
        return {"type": "control panel category",
                "name": CONTROL_PANEL_CATEGORIES.get(cat, "<control panel category %d>" % cat)}
    if sig6 in PROPERTY_VIEW_SIGNATURES:
        props = property_strings(buf)
        display = next((s for f, k, s in props if (f, k) == ITEM_NAME_DISPLAY and s), "")
        it = {"type": "property view item", "name": display or "<property view item 0x%08X>" % sig6}
        if sig6 == 0x23FEBBEE and n >= 0x1E:
            it["guid"], it["name"] = guid_name(buf[0x0E:0x1E])
            it["type"] = "known folder"
        elif sig6 == 0x23A3DFD5:
            it.update(type="search folder", name=display or "Search Folder",
                      strings=utf16_strings(buf[:0x400]))
        fs_path = next((s for _f, _k, s in props if PATH_LIKE.match(s)), "")
        if fs_path:
            it["fs_path"] = fs_path
        return it
    if sig6 == 0x46534643 and n >= 0x1A:                       # 'CFSF': delegate folder
        return _file_entry(bytes(buf[:2]) + bytes(buf[0x0C:0x0D]) + bytes(buf[3:]), name_at=0x18)
    if cls == 0x1F and n >= 20:
        g, name = guid_name(buf[4:20])
        return {"type": "root folder", "name": name, "guid": g}
    if cls == 0x2E and n >= 20:
        g, name = guid_name(buf[4:20])
        return {"type": "shell folder", "name": name, "guid": g}
    if cls in DRIVE_CLASSES:
        name = bytes(buf[3:]).split(b"\x00")[0].decode("cp1252", "replace")
        return {"type": "drive", "name": name}
    if cls in FILE_CLASSES and n >= 16:
        return _file_entry(buf)
    if cls in NETWORK_CLASSES and n >= 6:
        parts = bytes(buf[5:]).split(b"\x00")
        it = {"type": "network location", "name": parts[0].decode("cp1252", "replace")}
        flags, rest = buf[4], parts[1:]
        if flags & 0x80 and rest:
            it["description"] = rest.pop(0).decode("cp1252", "replace")
        if flags & 0x40 and rest:
            it["comment"] = rest.pop(0).decode("cp1252", "replace")
        return it
    if cls == 0x71 and n >= 30:
        g, name = guid_name(buf[14:30])
        return {"type": "control panel item", "name": name, "guid": g}
    z = _zip_item(buf)
    if z:
        it = {"type": "zip folder entry", "name": z[0]}
        if z[1]:
            it["path_in_zip"] = z[1]
        return it
    return {"type": "unknown", "name": "<shell item type 0x%02X>" % cls, "strings": utf16_strings(buf)}


def compose_path(parent, item: dict) -> str:
    """Path of a shell item under its parent. A drive or a network share starts the
    path anew; a file-system item directly under the namespace root is on the Desktop."""
    name = item["name"]
    if item["type"] == "drive":
        return name if name.endswith("\\") else name + "\\"
    if item["type"] == "network location" and name.startswith("\\\\"):
        return name
    if item.get("fs_path"):
        return item["fs_path"]
    if parent is None:
        return "Desktop\\" + name if item["type"] in ("folder", "file", "file system item") else name
    return parent.rstrip("\\") + "\\" + name


def idlist_path(buf: bytes, guid_names: dict = None):
    """(path, items) of a whole shell item id list."""
    path, items = None, []
    for raw in split_idlist(buf):
        it = parse_shell_item(raw, guid_names)
        path = compose_path(path, it)
        items.append(it)
    return path, items


def mru_order_ex(data) -> list:
    """MRUListEx: 32-bit entry numbers, most recent first, ended by 0xFFFFFFFF."""
    out = []
    if not isinstance(data, (bytes, bytearray)):
        return out
    for off in range(0, len(data) - 3, 4):
        v = _u32(data, off)
        if v == 0xFFFFFFFF:
            break
        out.append(v)
    return out


def recentdocs_name(data: bytes) -> str:
    """RecentDocs value: UTF-16 file name, a null, then the shortcut's shell item."""
    raw = bytes(data)
    for off in range(0, len(raw) - 1, 2):
        if raw[off:off + 2] == b"\x00\x00":
            return raw[:off].decode("utf-16-le", "replace")
    return raw[:len(raw) - len(raw) % 2].decode("utf-16-le", "replace")


def parse_office_mru(text: str):
    """'[F00000000][T01D0...][O00000000]*path' -> (FILETIME, path), or None."""
    m = OFFICE_MRU.match(text or "")
    return (int(m.group(2), 16), m.group(3)) if m else None


def mountpoint_to_unc(name: str):
    """MountPoints2 key '##server#share' -> '\\\\server\\share' (the key name cannot hold
    a backslash, so Explorer writes '#'), or None for any other key."""
    return name.replace("#", "\\") if name.startswith("##") and len(name) > 2 else None


def search_filetime(raw, big_endian: bool):
    """8-byte date of the search index -> FILETIME, or None when unset. Windows Vista/7
    (table SystemIndex_0A) store it big-endian, later versions little-endian."""
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != 8:
        return None
    ft = int.from_bytes(raw, "big" if big_endian else "little")
    return ft if ft > 1 else None


def thumbcache_id(raw: bytes) -> str:
    """Cache entry hash bytes -> the 16-digit id Windows prints (and the search index
    stores as System.ThumbnailCacheId)."""
    return "%016x" % int.from_bytes(bytes(raw), "little")


def pair_renames(records):
    """Change-journal records in journal order, as (usn, filetime, file ref, parent ref,
    name, reason), -> ([rename dicts], number of old-name records left without a new name)."""
    pending, out = {}, []
    for usn, ft, ref, parent, name, reason in records:
        if reason & USN_RENAME_OLD:
            pending[ref] = (usn, ft, parent, name)
        elif reason & USN_RENAME_NEW and ref in pending:
            o_usn, o_ft, o_parent, o_name = pending.pop(ref)
            out.append({"ref": ref, "old_usn": o_usn, "old_name": o_name, "old_parent": o_parent,
                        "new_usn": usn, "new_name": name, "new_parent": parent,
                        "filetime": ft, "old_filetime": o_ft})
    return out, len(pending)


def name_at(history, usn):
    """history: [(usn, name, parent reference)] of one file reference in journal order ->
    (name, parent reference) it had at that journal position. Before its first record it
    had the name that first record carries (the first record of a rename holds the old name)."""
    best = history[0]
    for entry in history:
        if entry[0] > usn:
            break
        best = entry
    return best[1], best[2]


# --------------------------------------------------------------------------- registry

BAG_ROOTS = ("Software\\Microsoft\\Windows\\Shell", "Software\\Microsoft\\Windows\\ShellNoRoam",
             "Local Settings\\Software\\Microsoft\\Windows\\Shell",
             "Local Settings\\Software\\Microsoft\\Windows\\ShellNoRoam",
             "Wow6432Node\\Local Settings\\Software\\Microsoft\\Windows\\Shell",
             "Wow6432Node\\Local Settings\\Software\\Microsoft\\Windows\\ShellNoRoam")
EXPLORER = "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer"
KEY_TIME = "registry key last-write time"
LIST_TIME = ("registry key last-write time (the moment the list last changed; only the "
             "most recent entry was added then)")


def _win(path) -> str:
    return str(path).replace("/", "\\")


def _guid_names() -> dict:
    try:
        from dissect.target.helpers import shell_folder_ids
        return dict(shell_folder_ids.DESCRIPTIONS)
    except Exception:
        return {}


def _hives(ev, target):
    """Every user registry hive on the volume: (account, profile folder, hive path, open hive)."""
    from dissect.regf import RegistryHive
    fs, seen, out = target.fs, set(), []
    homes = []
    for base in ("C:/Users", "C:/Documents and Settings", "C:/Windows/ServiceProfiles"):
        p = fs.path(base)
        try:
            if p.exists() and p.is_dir():
                homes += sorted((d for d in p.iterdir() if d.is_dir()), key=lambda d: d.name.lower())
        except Exception as e:
            ev.problem(_win(p), e)
    homes += [fs.path("C:/Windows/System32/config/systemprofile"),
              fs.path("C:/Windows/SysWOW64/config/systemprofile")]
    for home in homes:
        for rel in ("NTUSER.DAT", "AppData/Local/Microsoft/Windows/UsrClass.dat",
                    "Local Settings/Application Data/Microsoft/Windows/UsrClass.dat"):
            p = home.joinpath(rel)
            try:
                if not p.exists():
                    continue
                st = p.stat()
                if st.st_ino in seen or st.st_size == 0:
                    continue
                seen.add(st.st_ino)
                out.append((home.name, _win(home), _win(p), RegistryHive(p.open("rb"))))
            except Exception as e:
                ev.problem(_win(p), e)
    return out


def _open(hive, path):
    try:
        return hive.open(path)
    except Exception:
        return None


def _values(key) -> dict:
    out = {}
    for v in key.values():
        try:
            out[v.name] = v.value
        except Exception:
            out[v.name] = None
    return out


def _item_prov(it: dict) -> dict:
    return {k: v for k, v in it.items() if k not in ("name", "type") and v not in ("", None, [])}


def _walk_bags(ev, key, key_path, parent_path, hive_path, account, names, common, home=None, alias=None):
    values = _values(key)
    order = mru_order_ex(values.get("MRUListEx"))
    for name in sorted((n for n in values if n.isdigit()), key=int):
        where = f"{hive_path} key {key_path} value {name}"
        raw = values[name]
        try:
            items = split_idlist(raw) if isinstance(raw, (bytes, bytearray)) else []
            if not items:
                raise ValueError("no shell item in value")
            it = parse_shell_item(items[0], names)
            path = compose_path(parent_path, it)
            shell_path = (parent_path.rstrip("\\") + "\\" if parent_path else "") + it["name"]
            try:
                child = key.subkey(name)
            except Exception:
                child = None
            prov = dict(artifact=where, account=account, item_type=it["type"],
                        mru_position=order.index(int(name)) if int(name) in order else None,
                        **_item_prov(it), **common)
            if path != shell_path and it.get("fs_path"):
                prov["shell_path"] = shell_path
            fs_alias = None                  # the same folder as a disk path, where that is certain
            if it["type"] == "root folder" and it.get("guid") == USERS_FILES:
                fs_alias = home
            elif alias and it["type"] in ("folder", "file", "file system item"):
                fs_alias = alias + "\\" + it["name"]
            if fs_alias:
                prov.update(file_system_path=fs_alias, file_system_path_note="the namespace root "
                            "{%s} is the profile folder of the hive's owner" % USERS_FILES)
            own = us(child.timestamp) if child is not None else None
            if own is not None:
                node = _values(child).get("NodeSlot")
                ev.add("folderOpened", own, 1, path, "shell bag", node_slot=node,
                       time_meaning="last-write time of this folder's own BagMRU key", **prov)
            parent_t = us(key.timestamp)
            if order[:1] == [int(name)] and parent_t != own:
                ev.add("folderOpened", parent_t, 1, path, "shell bag",
                       time_meaning="last-write time of the parent BagMRU key, which lists "
                                    "this folder first in its most-recently-used order", **prov)
            elif own is None:
                ev.add("folderOpened", parent_t, 1, path, "shell bag",
                       time_meaning="last-write time of the parent BagMRU key (this folder "
                                    "has no key of its own)", **prov)
            if child is not None:
                _walk_bags(ev, child, key_path + "\\" + name, path, hive_path, account, names, common,
                           home, fs_alias)
        except Exception as e:
            ev.problem(where, e)


def _mru_letters(values: dict):
    """Old-style MRU key (values a, b, c... plus MRUList): [(position, name, text)]."""
    order = values.get("MRUList") if isinstance(values.get("MRUList"), str) else ""
    out = []
    for name, val in sorted(values.items()):
        if len(name) == 1 and name.isalpha() and isinstance(val, str):
            out.append((order.index(name) if name in order else None, name, val))
    return out


def _explorer_lists(ev, hive, hive_path, account, names, common):
    base = dict(account=account, **common)

    key = _open(hive, EXPLORER + "\\TypedPaths")
    if key is not None:
        for name, val in sorted(_values(key).items()):
            if isinstance(val, str) and val:
                ev.add("folderOpened", us(key.timestamp), 1, val, "typed path", value=name,
                       artifact=f"{hive_path} key {EXPLORER}\\TypedPaths value {name}",
                       time_meaning=LIST_TIME, **base)

    key = _open(hive, EXPLORER + "\\RunMRU")
    if key is not None:
        for pos, name, val in _mru_letters(_values(key)):
            typed = val[:-2] if val.endswith("\\1") else val
            if PATH_LIKE.match(typed):
                ev.add("folderOpened", us(key.timestamp), 1, typed, "run dialog", mru_position=pos,
                       artifact=f"{hive_path} key {EXPLORER}\\RunMRU value {name}",
                       note="a path typed into the Run dialog", time_meaning=LIST_TIME, **base)

    key = _open(hive, EXPLORER + "\\Map Network Drive MRU")
    if key is not None:
        for pos, name, val in _mru_letters(_values(key)):
            ev.add("folderOpened", us(key.timestamp), 1, val, "map network drive", mru_position=pos,
                   artifact=f"{hive_path} key {EXPLORER}\\Map Network Drive MRU value {name}",
                   time_meaning=LIST_TIME, **base)

    key = _open(hive, EXPLORER + "\\MountPoints2")
    if key is not None:
        for sub in key.subkeys():
            unc = mountpoint_to_unc(sub.name)
            if unc:
                ev.add("folderOpened", us(sub.timestamp), 1, unc, "mount point",
                       artifact=f"{hive_path} key {EXPLORER}\\MountPoints2\\{sub.name}",
                       time_meaning=KEY_TIME, **base)

    key = _open(hive, "Network")
    if key is not None:
        for sub in key.subkeys():
            remote = _values(sub).get("RemotePath")
            if isinstance(remote, str) and remote:
                ev.add("folderOpened", us(sub.timestamp), 1, remote, "mapped network drive",
                       drive_letter=sub.name.upper() + ":", artifact=f"{hive_path} key Network\\{sub.name}",
                       time_meaning=KEY_TIME, **base)

    key = _open(hive, EXPLORER + "\\RecentDocs")
    if key is not None:
        for sub_name, k in [("", key)] + [(s.name, s) for s in key.subkeys()]:
            values = _values(k)
            order = mru_order_ex(values.get("MRUListEx"))
            key_path = EXPLORER + "\\RecentDocs" + ("\\" + sub_name if sub_name else "")
            for name in sorted((n for n in values if n.isdigit()), key=int):
                where = f"{hive_path} key {key_path} value {name}"
                try:
                    doc = recentdocs_name(values[name])
                    if not doc:
                        raise ValueError("no name in value")
                    folder = sub_name.lower() == "folder"
                    ev.add("folderOpened" if folder else "fileSeen", us(k.timestamp), 1, doc,
                           "recent documents", artifact=where,
                           mru_position=order.index(int(name)) if int(name) in order else None,
                           note="the list keeps the name only, not the path",
                           time_meaning=LIST_TIME, **base)
                except Exception as e:
                    ev.problem(where, e)

    for list_name, kind in (("OpenSavePidlMRU", "fileSeen"), ("LastVisitedPidlMRU", "folderOpened")):
        key = _open(hive, EXPLORER + "\\ComDlg32\\" + list_name)
        if key is None:
            continue
        for sub_name, k in [("", key)] + [(s.name, s) for s in key.subkeys()]:
            values = _values(k)
            order = mru_order_ex(values.get("MRUListEx"))
            key_path = EXPLORER + "\\ComDlg32\\" + list_name + ("\\" + sub_name if sub_name else "")
            for name in sorted((n for n in values if n.isdigit()), key=int):
                where = f"{hive_path} key {key_path} value {name}"
                try:
                    raw, extra = bytes(values[name]), {}
                    if kind == "folderOpened":          # program name, a null, then the id list
                        extra["application"] = recentdocs_name(raw)
                        raw = raw[2 * len(extra["application"]) + 2:]
                    path, items = idlist_path(raw, names)
                    if not path and kind == "folderOpened" and raw[:2] == b"\x00\x00":
                        path, items = "Desktop", [{"type": "root folder", "name": "Desktop",
                                                   "note": "empty id list: the shell namespace root"}]
                    if not path:
                        raise ValueError("no shell items in value")
                    last = items[-1]
                    ev.add(kind, us(k.timestamp), 1, path, "open/save dialog", artifact=where,
                           mru_position=order.index(int(name)) if int(name) in order else None,
                           item_type=last["type"], time_meaning=LIST_TIME,
                           **_item_prov(last), **extra, **base)
                except Exception as e:
                    ev.problem(where, e)
    for list_name, kind in (("OpenSaveMRU", "fileSeen"), ("LastVisitedMRU", "folderOpened")):
        key = _open(hive, EXPLORER + "\\ComDlg32\\" + list_name)
        if key is None:
            continue
        for sub_name, k in [("", key)] + [(s.name, s) for s in key.subkeys()]:
            key_path = EXPLORER + "\\ComDlg32\\" + list_name + ("\\" + sub_name if sub_name else "")
            for pos, name, val in _mru_letters(_values(k)):
                ev.add(kind, us(k.timestamp), 1, val, "open/save dialog", mru_position=pos,
                       artifact=f"{hive_path} key {key_path} value {name}",
                       time_meaning=LIST_TIME, **base)


def _local_minutes(text: str, tz: str):
    """'2015-03-24T14:59' in the PC's zone -> UTC microseconds."""
    from zoneinfo import ZoneInfo
    local = datetime.strptime(text.strip(), "%Y-%m-%dT%H:%M").replace(tzinfo=ZoneInfo(tz))
    return us(local.astimezone(timezone.utc))


def _application_lists(ev, key, key_path, hive_path, account, tz, common, depth=0):
    """Recent-file lists that applications keep under their own keys, found by key name."""
    base = dict(account=account, **common)
    lname = key.name.lower()
    parts = key_path.split("\\")
    app = ""
    if "Office" in parts and parts.index("Office") + 2 < len(parts):
        app = parts[parts.index("Office") + 2]
    try:
        if lname in ("file mru", "place mru"):
            for name, val in sorted(_values(key).items()):
                parsed = parse_office_mru(val) if isinstance(val, str) else None
                if parsed is None:
                    continue
                kind, aux = (("fileSeen", "office recent files") if lname == "file mru"
                             else ("folderOpened", "office recent places"))
                ev.add(kind, us_from_filetime(parsed[0]), 1, parsed[1], aux, application=app,
                       artifact=f"{hive_path} key {key_path} value {name}",
                       time_meaning="time stored in the list entry (last opened in this application)",
                       **base)
        elif lname == "reading locations":
            for sub in key.subkeys():
                values = _values(sub)
                path, when = values.get("File Path"), values.get("Datetime")
                where = f"{hive_path} key {key_path}\\{sub.name}"
                if not isinstance(path, str) or not path:
                    continue
                ev.add("fileSeen", us(sub.timestamp), 1, path, "office reading locations",
                       application=app, artifact=where, time_meaning=KEY_TIME, **base)
                if isinstance(when, str) and when and tz:
                    try:
                        ev.add("fileSeen", _local_minutes(when, tz), 60_000_000, path,
                               "office reading locations", application=app, artifact=where,
                               stored_text=when, time_zone=f"local time, converted from {tz}",
                               time_meaning="Datetime value of the entry (when the document was "
                                            "last closed), stored to the minute", **base)
                    except Exception as e:
                        ev.problem(where, e)
        elif lname == "trustrecords":
            for name, val in sorted(_values(key).items()):
                if isinstance(val, (bytes, bytearray)) and len(val) >= 8:
                    ev.add("fileSeen", us_from_filetime(struct.unpack_from("<Q", val, 0)[0]), 1, name,
                           "office trusted documents", application=app,
                           artifact=f"{hive_path} key {key_path} value {name}",
                           time_meaning="time stored in the trust record", **base)
        elif lname in ("recent file list", "recentfilelist", "recenturllist"):
            for name, val in sorted(_values(key).items()):
                if isinstance(val, str) and val:
                    owner = parts[-2] if len(parts) > 1 else ""
                    ev.add("fileSeen", us(key.timestamp), 1, val, f"{owner} recent files".strip().lower(),
                           artifact=f"{hive_path} key {key_path} value {name}",
                           time_meaning=LIST_TIME, **base)
    except Exception as e:
        ev.problem(f"{hive_path} key {key_path}", e)
    if depth < 12 and lname not in ("bagmru", "bags", "clsid", "muicache"):
        try:
            subs = list(key.subkeys())
        except Exception as e:
            ev.problem(f"{hive_path} key {key_path}", e)
            subs = []
        for sub in subs:
            _application_lists(ev, sub, key_path + "\\" + sub.name, hive_path, account, tz, common, depth + 1)


def _registry(ev, target, tz, common):
    names = _guid_names()
    for account, home, hive_path, hive in _hives(ev, target):
        for root in BAG_ROOTS:
            key = _open(hive, root + "\\BagMRU")
            if key is not None:
                _walk_bags(ev, key, root + "\\BagMRU", None, hive_path, account, names, common, home)
        try:
            _explorer_lists(ev, hive, hive_path, account, names, common)
        except Exception as e:
            ev.problem(hive_path + " Explorer lists", e)
        software = _open(hive, "Software")
        if software is not None:
            _application_lists(ev, software, "Software", hive_path, account, tz, common)


# --------------------------------------------------------------------------- search index

SEARCH_DB = "C:/ProgramData/Microsoft/Search/Data/Applications/Windows/Windows.edb"
SEARCH_TABLES = (("SystemIndex_0A", True), ("SystemIndex_PropertyStore", False))
SEARCH_TIMES = (
    ("System_Search_GatherTime", "when the indexer last gathered the item"),
    ("System_DateModified", "the item's last-modified time as the index stores it"),
    ("System_DateCreated", "the item's creation time as the index stores it"),
    ("System_DateAccessed", "the item's last-access time as the index stores it"),
    ("System_Message_DateSent", "message sent time as the index stores it"),
    ("System_Message_DateReceived", "message received time as the index stores it"),
    ("System_Link_DateVisited", "link last-visited time as the index stores it"),
)
SID = re.compile(r"\{(S-1-[0-9-]+)\}")


def _sid_names(target) -> dict:
    out = {}
    try:
        key = target.registry.key("HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\ProfileList")
        for sub in key.subkeys():
            try:
                out[sub.name] = str(sub.value("ProfileImagePath").value).replace("/", "\\").rsplit("\\", 1)[-1]
            except Exception:
                continue
    except Exception:
        pass
    return out


MAX_SEARCH_DATABASE_BYTES = 512 * 1024 * 1024
MAX_SEARCH_RECORDS = 100000
MAX_SEARCH_TEXT = 65536
SEARCH_TEXT_FIELDS = (
    ('System_ItemUrl', 'search.index.item_url'),
    ('System_ItemPathDisplay', 'search.index.item_path'),
    ('System_Search_Store', 'search.index.store'),
    ('System_ItemType', 'search.index.item_type'),
)


def _search_iso_filetime(filetime):
    """Render all seven FILETIME fraction digits; no microsecond truncation."""
    from .store import FILETIME_EPOCH_100NS
    seconds, fraction = divmod(filetime - FILETIME_EPOCH_100NS, 10_000_000)
    return (EPOCH + timedelta(seconds=seconds)).strftime('%Y-%m-%dT%H:%M:%S') + f'.{fraction:07d}Z'


def _search_attributes(ev, record, get, columns, table, identifier, doc, ordinal, source,
                       digest, big_endian, common, examined_at, state):
    """Typed fields from one immutable ESE row; no inferred use or path fallback."""
    import hashlib

    if not isinstance(examined_at, int) or isinstance(examined_at, bool) or examined_at <= 0:
        return
    scope = subject_scope(common)
    if not all(isinstance(value, str) and value.strip() and value != 'unknown' for value in scope):
        raise ValueError('typed Search fields require all four explicit source-origin axes')
    if not isinstance(doc, int) or isinstance(doc, bool) or not 0 <= doc < 1 << 64:
        raise ValueError('Search row has no supported native nonnegative DocID/WorkID')
    doc = int(doc)
    subject = json.dumps(scope + ['windows-search-row', source, digest, table.name, identifier, doc, ordinal],
                         ensure_ascii=True, separators=(',', ':'))
    base = merge_scope(common, dict(artifact=f'{source} table {table.name} {identifier} {doc}',
        source_path=source, source_sha256=digest, parser='extractor.filetraces.search_index',
        ese_table=table.name, ese_identifier_column=columns[identifier], ese_document_id=doc,
        ese_record_ordinal=ordinal, ese_database_state=state, examination_time=examined_at,
        source_record_limit=MAX_SEARCH_RECORDS,
        limitation='literal retained index fields; no browsing, actor, actual filesystem event, latest-state or complete-enumeration claim'))
    node = getattr(record, '_node', None)
    if node is not None:
        try:
            tag = node.tag
            base.update(ese_page_number=int(tag.page.num), ese_tag_number=int(tag.num),
                        ese_tag_data_offset=int(tag.offset), ese_tag_data_size=int(tag.size),
                        ese_node_sha256=hashlib.sha256(bytes(node.data)).hexdigest())
        except (AttributeError, TypeError, ValueError):
            pass  # Container/table/row identity remains explicit when optional node metadata is unavailable.
    for role, value in (('search.index.container_path', source), ('search.index.table', str(table.name)),
                        ('search.index.document_id', doc), ('search.index.identifier_column', columns[identifier])):
        emit_attribute(ev, subject, role, value, examined_at, **base)
    for column, role in SEARCH_TEXT_FIELDS:
        raw = get(column)
        if raw is None:
            continue
        try:
            if not isinstance(raw, str) or len(raw) > MAX_SEARCH_TEXT or '\0' in raw:
                raise ValueError('indexed field is not bounded native text')
            emit_attribute(ev, subject, role, str(raw), examined_at,
                           **dict(base, ese_column=columns[column], source_field=column))
        except Exception as error:
            ev.problem(base['artifact'] + ' ' + column, error)
    for column, role in (('System_DateModified', 'search.index.date_modified'),
                         ('System_DateCreated', 'search.index.date_created')):
        raw = get(column)
        if raw is None:
            continue
        try:
            if not isinstance(raw, (bytes, bytearray)) or len(raw) != 8:
                raise ValueError('indexed FILETIME is not an eight-byte value')
            ft = search_filetime(raw, big_endian)
            if ft is None:
                continue  # Zero/one are unset, not an epoch or examination timestamp.
            value = us_from_filetime(ft)
            if value < 0:
                raise ValueError('indexed FILETIME predates supported Unix epoch')
            emit_attribute(ev, subject, role, _search_iso_filetime(ft), examined_at,
                           **dict(base, ese_column=columns[column], source_field=column,
                                  native_filetime_bytes=bytes(raw).hex(), byte_order='big' if big_endian else 'little',
                                  value_precision='100ns',
                                  value_time_meaning='exact timestamp stored in ' + column + '; not a user action time'))
        except Exception as error:
            ev.problem(base['artifact'] + ' ' + column, error)
    raw = get('System_Kind')
    if raw is not None:
        try:
            values = [raw] if isinstance(raw, str) else raw
            if (not isinstance(values, list) or len(values) > 32
                    or any(not isinstance(value, str) or len(value) > MAX_SEARCH_TEXT or '\0' in value for value in values)):
                raise ValueError('System_Kind is not a bounded native string/string-list; no category inferred')
            for index, value in enumerate(values):
                emit_attribute(ev, subject, 'search.index.kind', str(value), examined_at,
                               **dict(base, ese_column=columns['System_Kind'], source_field='System_Kind',
                                      native_value_index=index, native_value_count=len(values)))
        except Exception as error:
            ev.problem(base['artifact'] + ' System_Kind', error)


def _search_index(ev, target, common, examined_at=None) -> dict:
    """Retained index observations; thumbnail map remains a separate legacy output."""
    import hashlib
    import tempfile
    thumbs = {}
    p = target.fs.path(SEARCH_DB)
    if not p.exists():
        return thumbs
    from dissect.database.ese import ESE
    source, sids = _win(p), _sid_names(target)
    size = p.stat().st_size
    if (not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_SEARCH_DATABASE_BYTES):
        ev.problem(source, ValueError('Search database size is unavailable or exceeds the bounded reader limit'))
        return thumbs
    # Freeze the exact parser bytes while hashing. Large containers spill to an
    # automatically removed temporary file rather than consuming unbounded RAM.
    with p.open('rb') as original, tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode='w+b') as frozen:
        sha, copied = hashlib.sha256(), 0
        while True:
            block = original.read(min(1024 * 1024, size - copied + 1))
            if not block:
                break
            copied += len(block)
            if copied > size:
                raise ValueError('Search container exceeds its advertised file size')
            sha.update(block)
            frozen.write(block)
        if copied != size:
            raise ValueError('Search container is truncated relative to its advertised file size')
        digest = sha.hexdigest()
        frozen.seek(0)
        db = ESE(frozen)
        state = db.header.dbstate
        if not isinstance(state, int) or isinstance(state, bool):
            raise ValueError('Search database state is not a native integer')
        state = int(state)
        if state != 3:
            ev.problem(source, RuntimeWarning(f'database state {state}, not a clean shutdown: transaction logs were not replayed; newest index changes may be missing'))
        found = False
        for name, big_endian in SEARCH_TABLES:
            try:
                table = db.table(name)
            except Exception:
                continue
            found = True
            try:
                columns = {}
                for full in table.column_names:
                    if not isinstance(full, str):
                        raise ValueError('Search table has a non-text column name')
                    if '-' in full:
                        prefix, column = full.split('-', 1)
                        if not prefix.isascii() or not prefix.isdecimal():
                            raise ValueError('Search property prefix is not a decimal column identifier')
                    else:
                        column = full
                    if column in columns:
                        raise ValueError('Search table has ambiguous normalized column names')
                    columns[column] = full
                identifier = next((key for key in ('DocID', 'WorkID', 'WorkId') if key in columns), None)
                dates = [column for column in columns if 'Date' in column or column.endswith('GatherTime')]
                row_columns = {column for column, _ in SEARCH_TIMES}
                for ordinal, record in enumerate(table.records()):
                    if ordinal >= MAX_SEARCH_RECORDS:
                        raise ValueError('Search record bound reached; further rows were not examined')
                    def get(column):
                        return record.get(columns[column]) if column in columns else None
                    doc = get(identifier) if identifier else None
                    where = f'{source} table {table.name} {identifier or "missing identifier"} {doc}'
                    try:
                        _search_attributes(ev, record, get, columns, table, identifier, doc, ordinal,
                                           source, digest, big_endian, common, examined_at, state)
                    except Exception as error:
                        ev.problem(where, error)
                    try:
                        url, item_path = get('System_ItemUrl'), get('System_ItemPathDisplay')
                        # Retain the legacy fileSeen/thumbnail observation without
                        # promoting its display fallback to search.index.item_path.
                        path = item_path if isinstance(item_path, str) and item_path else url
                        if not isinstance(path, str) or not path:
                            continue
                        cache_id = get('System_ThumbnailCacheId')
                        if isinstance(cache_id, (bytes, bytearray)) and len(cache_id) == 8:
                            cid = '%016x' % int.from_bytes(cache_id, 'big' if big_endian else 'little')
                            thumbs.setdefault(cid, []).append((path, doc))
                        prov = merge_scope(common, dict(artifact=where, source_path=source, source_sha256=digest,
                            item_url=url if isinstance(url, str) else None,
                            store=get('System_Search_Store') if isinstance(get('System_Search_Store'), str) else None,
                            item_type=get('System_ItemType') if isinstance(get('System_ItemType'), str) else None,
                            ese_table=table.name, ese_record_ordinal=ordinal, ese_database_state=state))
                        raw_size = get('System_Size')
                        if isinstance(raw_size, (bytes, bytearray)) and len(raw_size) == 8:
                            prov['size'] = int.from_bytes(raw_size, 'big' if big_endian else 'little')
                        title = get('System_ItemNameDisplay')
                        if isinstance(title, str) and title and title != path:
                            prov['display_name'] = title[:200]
                        match = SID.search(url) if isinstance(url, str) else None
                        if match:
                            prov['sid'] = match.group(1)
                            if match.group(1) in sids:
                                prov['account'] = sids[match.group(1)]
                        other = {}
                        for column in dates:
                            ft = search_filetime(get(column), big_endian)
                            if ft and column not in row_columns and us_from_filetime(ft) >= 0:
                                other[column] = iso(us_from_filetime(ft))
                        if other:
                            prov['other_dates'] = other
                        times = {}
                        for column, meaning in SEARCH_TIMES:
                            ft = search_filetime(get(column), big_endian)
                            if ft is None:
                                continue
                            timestamp = us_from_filetime(ft)
                            if timestamp < 0:
                                ev.problem(where, ValueError(f'{column} is before 1970 and was left out'))
                                continue
                            times.setdefault(timestamp, []).append((column, meaning))
                        for timestamp, same in sorted(times.items()):
                            ev.add('fileSeen', timestamp, 1, path, 'windows search index',
                                   column=', '.join(column for column, _ in same),
                                   time_meaning='; '.join(meaning for _, meaning in same), **prov)
                    except Exception as error:
                        ev.problem(where, error)
            except Exception as error:
                ev.problem(source + ' table ' + name, error)
        if not found:
            ev.problem(source, ValueError('no supported property table found'))
    return thumbs

# --------------------------------------------------------------------------- thumbnail caches

def _thumbnail_caches(ev, target, thumbs, common):
    from dissect.thumbcache.index import ThumbnailIndex
    from dissect.thumbcache.thumbcache_file import ThumbcacheFile
    users = target.fs.path("C:/Users")
    if not users.exists():
        return
    for home in sorted(users.iterdir(), key=lambda d: d.name.lower()):
        folder = home.joinpath("AppData/Local/Microsoft/Windows/Explorer")
        try:
            if not folder.exists() or home.is_symlink():
                continue
            files = sorted((f for f in folder.iterdir() if f.name.lower().startswith("thumbcache_")
                            and f.name.lower().endswith(".db")), key=lambda f: f.name.lower())
        except Exception as e:
            ev.problem(_win(folder), e)
            continue
        found = {}          # cache id -> {"t": creation of the first file holding it, "entries": [...]}
        for f in files:
            source = _win(f)
            try:
                created = us_from_unix(f.lstat().st_birthtime)
                if f.name.lower().endswith("_idx.db"):
                    for entry in ThumbnailIndex(f.open("rb")).entries():
                        cid = thumbcache_id(entry.identifier)
                        found.setdefault(cid, {"t": created, "entries": []})["entries"].append(
                            {"file": f.name, "index_flags": int(entry.flags)})
                    continue
                cache = ThumbcacheFile(f.open("rb"))
                offset = int(cache.header.Offset)
                for entry in cache.entries():
                    size = int(entry._header.Size)
                    if int(entry.hash, 16):
                        cid = thumbcache_id(bytes.fromhex(entry.hash))
                        found.setdefault(cid, {"t": created, "entries": []})["entries"].append(
                            {"file": f.name, "offset": offset, "image_bytes": len(entry.data)})
                    if size <= 0:
                        break
                    offset += size
            except Exception as e:
                ev.problem(source, e)
        for cid, info in sorted(found.items()):
            matches = thumbs.get(cid, [])
            prov = dict(artifact=f"{_win(folder)}\\thumbcache_*.db cache id {cid}", account=home.name,
                        cache_id=cid, entries=info["entries"],
                        time_meaning="creation time of the thumbnail cache file: a cache entry "
                                     "stores no time, the thumbnail was added at or after this",
                        **common)
            if matches:
                for path, doc in matches:
                    ev.add("fileSeen", info["t"], 1, path, "thumbnail cache",
                           path_source=f"search index DocID {doc} has this System.ThumbnailCacheId",
                           **prov)
            else:
                ev.add("fileSeen", info["t"], 1, f"thumbnail cache id {cid}", "thumbnail cache",
                       path_source="the cache keeps no path and the search index does not hold this id",
                       **prov)


# --------------------------------------------------------------------------- NTFS: journal, shadow copies

def _ntfs_volumes(target):
    """(drive letter or volume name, filesystem) for each NTFS volume."""
    letters = {}
    for name, fs in target.fs.mounts.items():
        if re.match(r"^[a-z]:$", name):
            letters[id(fs)] = name.upper()
    out = []
    for fs in target.filesystems:
        if getattr(fs, "__type__", "") == "ntfs":
            serial = "%08X" % (fs.ntfs.serial & 0xFFFFFFFF)
            out.append((letters.get(id(fs), f"volume {serial}"), serial, fs))
    return out


def _ref(r):
    return (r.SegmentNumberLowPart | (r.SegmentNumberHighPart << 32), r.SequenceNumber)


def _folder_path(ntfs, cache, ref):
    """Path of a folder from its file reference, as the file table has it now; None when
    that record has since been reused (sequence number differs)."""
    if ref not in cache:
        path = None
        try:
            rec = ntfs.mft(ref[0])
            if rec.header.SequenceNumber == ref[1]:
                raw = rec.full_path()
                path = "" if ref[0] == 5 else (raw.replace("/", "\\").strip("\\") if raw else None)
        except Exception:
            path = None
        cache[ref] = path
    return cache[ref]


def _folder_at(ntfs, cache, history, ref, usn, depth=0, allow_future=True):
    """(path, True when the journal supplied the name) of a folder as it was at a journal
    position: the journal's own record of that folder where it has one, else the file table."""
    if ref[0] != 5 and ref in history and depth < 64:
        past = history[ref] if allow_future else [r for r in history[ref] if r[0] <= usn]
        if past:
            name, parent = name_at(past, usn)
            up, _ = _folder_at(ntfs, cache, history, parent, usn, depth + 1, allow_future)
            if up is not None:
                return (up + "\\" if up else "") + name, True
    return _folder_path(ntfs, cache, ref), False


def _historical_folder(ntfs, cache, history, ref, usn, seen=()):
    """Resolve only a chain of preceding journal names to the volume root.

    A current MFT name or a later rename's old name is useful context, but does
    not establish a directory's name at an earlier journal observation.
    """
    if ref in seen or len(seen) >= 64:
        return None
    if ref[0] == 5:
        return _folder_path(ntfs, cache, ref)
    past = [entry for entry in history.get(ref, []) if entry[0] <= usn]
    if not past:
        return None
    _when, name, parent = past[-1]
    above = _historical_folder(ntfs, cache, history, parent, usn, seen + (ref,))
    return None if above is None else (above + "\\" if above else "") + name


def _journal_identity(common, serial, ref):
    """Scoped identity, never a path: full NTFS volume serial plus record+sequence.

    Image/exhibit scope prevents joining unrelated evidence images that happen to
    carry the same serial. Shadow copies from that image retain the same scope.
    Reference equality across historical views does not establish equal source
    snapshots, continuous existence or authenticity. A selected-view answer must
    separately check the source origin of every supporting record.
    """
    return "NTFS identity " + json.dumps(
        [common.get("image", ""), common.get("exhibit", ""), f"{serial:016X}", *ref],
        ensure_ascii=False, separators=(",", ":"))


def _journal(ev, ntfs, drive, spool_dir, common, only_before=None, volume_serial=None, **source):
    """Creation/removal observations, renames and spool traces of one change journal.

    Reason flags accumulate until CLOSE (MS-FSCC USN_RECORD_V2, 2.3.62.2). Emit
    their first retained occurrence in that cycle, not a new action for each
    accumulated flag. The timestamp is when that observation was logged: a
    close-only record cannot recover the exact earlier action time. Return the
    first USN for the caller's live/VSS overlap boundary.
    """
    common = merge_scope(common, {key: source.pop(key) for key in
                                 ('source_snapshot', 'source_variant') if key in source})
    journal = ntfs.usnjrnl
    if not journal:
        return None
    artifact = f"{drive}\\$Extend\\$UsnJrnl:$J"
    spool_ref = None
    if spool_dir:
        try:
            rec = ntfs.mft.get(spool_dir[3:].replace("\\", "/"))
            spool_ref = (rec.segment, rec.header.SequenceNumber)
        except Exception:
            spool_ref = None
    wanted, spool, first, history, unreadable = [], {}, None, {}, 0
    events, active, observations = [], {}, []
    ranges = JournalRanges() if hasattr(journal, 'fh') else None
    for r in journal.records():
        rec = r.record
        if first is None:
            first = int(rec.Usn)
        if only_before is not None and int(rec.Usn) >= only_before:
            break
        if ranges is not None:
            ranges.capture(r.offset, int(rec.RecordLength), journal.fh)
        reason = int(rec.Reason)
        fref, parent = _ref(rec.FileReferenceNumber), _ref(rec.ParentFileReferenceNumber)
        usn, filetime = int(rec.Usn), int(rec.TimeStamp)
        try:
            name = r.filename
        except Exception:
            unreadable += 1
            # A malformed filename must not make accumulated flags leak into the
            # next close cycle for the same file reference.
            if reason & USN_CLOSE:
                for flag in (USN_FILE_CREATE, USN_FILE_DELETE):
                    event = active.pop((fref, flag), None)
                    if event is not None:
                        event["close_usn"] = usn
            continue
        known = history.setdefault(fref, [])          # every name and folder this file had
        if not known or known[-1][1:] != (name, parent):
            known.append((int(rec.Usn), name, parent))
        observations.append((usn, filetime, fref, parent, name, reason))
        if reason & (USN_RENAME_OLD | USN_RENAME_NEW):
            wanted.append((int(rec.Usn), int(rec.TimeStamp), fref, parent, name, reason))
        for flag, kind in ((USN_FILE_CREATE, "fileCreationRecorded"), (USN_FILE_DELETE, "fileRemoved")):
            if reason & flag:
                key = fref, flag
                if key not in active:
                    event = dict(kind=kind, usn=usn, filetime=filetime, ref=fref,
                                 parent=parent, name=name, reason=reason,
                                 matching_usns=[], close_usn=None)
                    active[key] = event
                    events.append(event)
                active[key]["matching_usns"].append(usn)
        if reason & USN_CLOSE:
            for flag in (USN_FILE_CREATE, USN_FILE_DELETE):
                event = active.pop((fref, flag), None)
                if event is not None:
                    event["close_usn"] = usn
        if spool_ref is not None and parent == spool_ref:
            info = spool.setdefault((fref, name), {})
            for flag, what in ((USN_FILE_CREATE, "created"), (USN_FILE_DELETE, "deleted")):
                if reason & flag and what not in info:
                    info[what] = (int(rec.TimeStamp), int(rec.Usn))
    if unreadable:
        ev.problem(artifact, RuntimeWarning(f"{unreadable} journal records have no readable name"))
    renames, unpaired = pair_renames(wanted)
    if unpaired:
        ev.problem(artifact, RuntimeWarning(f"{unpaired} old-name records have no new-name record"))
    cache = {}
    if ranges is not None:
        ranges.finish()
        if ranges.rejected:
            ev.problem(artifact + ' bounded-path coverage', RuntimeWarning(
                f'{ranges.rejected} records failed raw continuity checks; no path inference crosses them'))

    def full(folder, name):
        # The filename is copied as stored. Do not normalize slash-like characters
        # inside a raw name or invent a parent when its reference cannot be resolved.
        return name if folder is None else drive + "\\" + (folder + "\\" if folder else "") + name

    serial = volume_serial or ("%08X" % (ntfs.serial & 0xFFFFFFFF))
    root_reference = None
    scope = {'image': common.get('image'), 'exhibit': common.get('exhibit'),
             'ntfs_volume_serial': f'{ntfs.serial:016X}',
             'source_snapshot': common['source_snapshot'], 'source_variant': common['source_variant']}
    scope_complete = (all(isinstance(scope[key], str) and scope[key].strip()
                          for key in ('image', 'exhibit'))
                      and isinstance(ntfs.serial, int) and not isinstance(ntfs.serial, bool)
                      and 0 <= ntfs.serial < 1 << 64)
    if ranges is not None:
        try:
            root_reference = (5, int(ntfs.mft(5).header.SequenceNumber))
        except Exception:
            pass
        if not scope_complete:
            ev.problem(artifact + ' bounded-path scope', RuntimeWarning(
                'image, exhibit and full NTFS volume identity are required; no bounded path facts emitted'))

    def path_resolution(parent, usn):
        """Attach operational diagnostics, never a guessed prefix or new claim."""
        resolved = (ranges.resolve_folder(parent, usn, root_reference) if ranges is not None
                    else {'components': [], 'path_complete': False, 'anchors': [], 'diagnostic': {
                        'status': 'diagnostic', 'reason': 'raw_journal_coverage_unavailable',
                        'at_usn': usn,
                        'missing_ancestor': {'file_record': parent[0], 'file_sequence': parent[1]},
                        'resolved_chain_child_to_root': [],
                        'evidence_needed': 'Retained raw USN-v2 bytes with validated offsets and interval continuity, and historical ancestor observations for the exact identities.',
                        'limitation': 'No historical prefix is inferred from a current MFT path.'}})
        diagnostic = resolved['diagnostic']
        if not scope_complete:
            resolved['path_complete'] = False
            diagnostic = dict(diagnostic or {}, status='diagnostic', reason='identity_scope_incomplete',
                              at_usn=usn,
                              missing_ancestor={'file_record': parent[0], 'file_sequence': parent[1]},
                              resolved_chain_child_to_root=[],
                              evidence_needed='Bind the raw journal to an image, exhibit and full NTFS volume serial before using its identities.',
                              limitation='Unscoped identities do not support an absolute historical path.')
            resolved['diagnostic'] = diagnostic
        if diagnostic is not None:
            diagnostic.update(scope=dict(scope), scope_complete=scope_complete,
                              source_journal=artifact, shadow_copy=source.get('shadow_copy'))
            missing = diagnostic['missing_ancestor']
            missing['scoped_identity'] = (_journal_identity(common, ntfs.serial,
                (missing['file_record'], missing['file_sequence'])) if scope_complete else None)
            for item in diagnostic['resolved_chain_child_to_root']:
                item['scoped_identity'] = (_journal_identity(common, ntfs.serial,
                    (item['file_record'], item['file_sequence'])) if scope_complete else None)
        return resolved

    def historical_folder(parent, usn):
        # The older direct-name path must not bypass the raw resolver's refusals
        # (gaps, a rename in progress, conflicting type or reused identities).
        # Future OLD_NAME inference remains in the separate journalPath record.
        if not scope_complete or ranges is None:
            return None
        resolved = ranges.resolve_folder(parent, usn, root_reference)
        if (resolved['path_complete'] and all(
                a['method'] == 'preceding directory observation' for a in resolved['anchors'])):
            return '\\'.join(resolved['components'])
        return None

    if ranges is not None and scope_complete:
        latest_paths = {}
        for usn, filetime, fref, parent, name, reason in observations:
            if usn not in ranges.membership or us_from_filetime(filetime) < 0:
                continue
            resolved = path_resolution(parent, usn)
            folders, complete, anchors = (resolved['components'], resolved['path_complete'],
                                          resolved['anchors'])
            if not folders:
                continue
            # Existing direct historical names already cover full preceding paths.
            # This new kind exposes bounded future-name inference and useful suffixes.
            future = any(a['method'].startswith('future OLD_NAME') for a in anchors)
            if complete and not future:
                continue
            path = (drive + '\\' if complete else '[unresolved ancestor]\\') + '\\'.join(folders + [name])
            if latest_paths.get(fref) == path:
                continue
            latest_paths[fref] = path
            ev.add('journalPath', us_from_filetime(filetime), 1, path,
                   _journal_identity(common, ntfs.serial, fref),
                   artifact=f'{artifact} USN {usn}', usn=usn, raw_name=name,
                   file_record=fref[0], file_sequence=fref[1],
                   parent_record=parent[0], parent_sequence=parent[1],
                   volume_serial=serial, ntfs_volume_serial=f'{ntfs.serial:016X}',
                   reason_flags=reason, path_complete=complete, directory_anchors=anchors,
                   path_resolution_diagnostic=resolved['diagnostic'],
                   bounded_future_old_name=future, timestamp_semantics='journal_observation',
                   time_meaning='timestamp of the child journal observation; not filesystem creation onset',
                   rule='directory names constrained by exact identities and intact retained USN-v2 byte '
                        'intervals; any future OLD_NAME must be followed by NEW_NAME with no intervening '
                        'creation, removal, rename-new, conflicting name or hard-link change for that directory',
                   limitation='partial paths have an explicitly unresolved ancestor; this does not prove '
                              'a copy, disc write, secure wiping or continuous presence outside the interval',
                   **source, **common)
    # Name and parent observations expose identity as an IR field, not merely
    # provenance. Keep each transition, but collapse repeated same-state flags.
    names, parents, latest_name, latest_parent = [], [], {}, {}
    for usn, filetime, fref, parent, name, reason in observations:
        t = us_from_filetime(filetime)
        if t < 0:
            continue
        folder = historical_folder(parent, usn)
        path = full(folder, name)
        context, _ = _folder_at(ntfs, cache, history, parent, usn, allow_future=False)
        identity = _journal_identity(common, ntfs.serial, fref)
        parent_identity = _journal_identity(common, ntfs.serial, parent)
        detail = dict(usn=usn, raw_name=name, file_record=fref[0], file_sequence=fref[1],
                      parent_record=parent[0], parent_sequence=parent[1], volume_serial=serial,
                      ntfs_volume_serial=f"{ntfs.serial:016X}", reason_flags=reason,
                      timestamp_semantics="journal_observation", historical_path_resolved=folder is not None,
                      context_path=full(context, name),
                      context_path_source="journal or current file table; not asserted as the historical path",
                      last_observation_usn=usn, observation_count=1)
        if folder is None or not scope_complete:
            diagnostic = path_resolution(parent, usn)['diagnostic']
            if diagnostic is not None:
                detail['path_resolution_diagnostic'] = diagnostic
        old = latest_name.get(fref)
        name_key = (path, parent, folder is not None)
        if old is not None and old[0] == name_key:
            old[1][4]["last_observation_usn"] = usn
            old[1][4]["observation_count"] += 1
        else:
            row = (t, path, identity, usn, dict(detail))
            names.append(row)
            latest_name[fref] = (name_key, row)
        old = latest_parent.get(fref)
        if old is not None and old[0] == parent:
            old[1][4]["last_observation_usn"] = usn
            old[1][4]["observation_count"] += 1
        else:
            row = (t, identity, parent_identity, usn, dict(detail))
            parents.append(row)
            latest_parent[fref] = (parent, row)
    for kind, rows in (("journalName", names), ("journalParent", parents)):
        for t, obj, aux, usn, detail in rows:
            ev.add(kind, t, 1, obj, aux, artifact=f"{artifact} USN {usn}",
                   time_meaning="first journal observation of this consecutive name/parent state; "
                                "not creation onset or continuous presence between observations",
                   path_source="a full path is used only when validated raw journal coverage and "
                               "preceding directory names resolve every ancestor to the volume root; "
                               "otherwise raw_name is retained",
                   **detail, **source, **common)
    for event in events:
        folder = historical_folder(event["parent"], event["usn"])
        diagnostic = path_resolution(event['parent'], event['usn'])['diagnostic']
        context, _ = _folder_at(ntfs, cache, history, event["parent"], event["usn"],
                                allow_future=False)
        t = us_from_filetime(event["filetime"])
        if t < 0:
            ev.problem(f"{artifact} USN {event['usn']}", ValueError("journal time is before 1970"))
            continue
        flag_name = "FILE_CREATE" if event["kind"] == "fileCreationRecorded" else "FILE_DELETE"
        ev.add(event["kind"], t, 1, full(folder, event["name"]), serial,
               artifact=f"{artifact} USN {event['usn']}", usn=event["usn"],
               raw_name=event["name"], file_record=event["ref"][0],
               file_sequence=event["ref"][1], parent_record=event["parent"][0],
               parent_sequence=event["parent"][1], volume_serial=serial,
               parent_folder=(drive + "\\" + folder) if folder is not None else "not resolved",
               path_resolved=folder is not None,
               path_resolution_diagnostic=diagnostic,
               folder_names_from="change journal" if folder is not None else "not resolved",
               context_path=full(context, event["name"]),
               context_path_source="journal or current file table; not asserted as the historical path",
               reason_flags=event["reason"], matching_usns=event["matching_usns"],
               close_usn=event["close_usn"], timestamp_semantics="journal_observation",
               path_source="full path only when validated raw journal coverage and preceding directory names resolve "
                           "every ancestor to the volume root; otherwise the recorded basename "
                           "is retained and current file-table paths are context only",
               time_meaning=f"time the first retained {flag_name} observation was logged in "
                            "this close cycle, not a file-system timestamp or proof of exact "
                            "action onset; repeated accumulated flags before CLOSE are grouped",
               **source, **common)
        if event["kind"] == "fileRemoved":
            ev.add("journalRemoval", t, 1, full(folder, event["name"]),
                   _journal_identity(common, ntfs.serial, event["ref"]),
                   artifact=f"{artifact} USN {event['usn']}", usn=event["usn"],
                   raw_name=event["name"], file_record=event["ref"][0], file_sequence=event["ref"][1],
                   parent_record=event["parent"][0], parent_sequence=event["parent"][1],
                   volume_serial=serial, ntfs_volume_serial=f"{ntfs.serial:016X}",
                   historical_path_resolved=folder is not None,
                   path_resolution_diagnostic=diagnostic,
                   reason_flags=event["reason"], matching_usns=event["matching_usns"],
                   close_usn=event["close_usn"], timestamp_semantics="journal_observation",
                   time_meaning="first retained FILE_DELETE flag observation in this close cycle; "
                                "not deletion onset, removal of every alias, or secure wiping",
                   **source, **common)
    for rn in renames:
        old_dir = historical_folder(rn["old_parent"], rn["old_usn"])
        new_dir = historical_folder(rn["new_parent"], rn["new_usn"])
        old_context, _ = _folder_at(ntfs, cache, history, rn["old_parent"], rn["old_usn"],
                                    allow_future=False)
        new_context, _ = _folder_at(ntfs, cache, history, rn["new_parent"], rn["new_usn"],
                                    allow_future=False)

        ev.add("fileRenamed", us_from_filetime(rn["filetime"]), 1, full(old_dir, rn["old_name"]),
               full(new_dir, rn["new_name"]), artifact=f"{artifact} USN {rn['new_usn']}",
               old_name=rn["old_name"], new_name=rn["new_name"], old_name_usn=rn["old_usn"],
               file_record=rn["ref"][0], file_sequence=rn["ref"][1],
               volume_serial=serial, ntfs_volume_serial=f"{ntfs.serial:016X}",
               file_identity=_journal_identity(common, ntfs.serial, rn["ref"]),
               parent_folder=(drive + "\\" + old_dir) if old_dir is not None else "not resolved",
               new_parent_folder=(drive + "\\" + new_dir) if new_dir is not None else "not resolved",
               parent_record=rn["old_parent"][0], new_parent_record=rn["new_parent"][0],
               parent_sequence=rn["old_parent"][1], new_parent_sequence=rn["new_parent"][1],
               moved=rn["old_parent"] != rn["new_parent"],
               old_path_resolved=old_dir is not None, new_path_resolved=new_dir is not None,
               old_path_resolution_diagnostic=path_resolution(rn['old_parent'], rn['old_usn'])['diagnostic'],
               new_path_resolution_diagnostic=path_resolution(rn['new_parent'], rn['new_usn'])['diagnostic'],
               context_path=full(old_context, rn["old_name"]),
               new_context_path=full(new_context, rn["new_name"]),
               context_path_source="journal or current file table; not asserted as historical paths",
               folder_names_from="change journal where ancestors resolve; otherwise raw basenames",
               path_source="each rename side uses validated raw journal coverage, its own USN and preceding directory "
                           "names to resolve the ancestor chain; otherwise its raw basename "
                           "is retained. Current or later paths do not rewrite either side",
               time_meaning="time of the journal's new-name record", **source, **common)
    for (ref, name), info in sorted(spool.items()):
        for what, (ft, usn) in sorted(info.items()):
            ev.add("fileSeen", us_from_filetime(ft), 1, spool_dir + "\\" + name, "print job",
                   artifact=f"{artifact} USN {usn}", file_record=ref[0],
                   note="spool file of a print job, known only from the change journal",
                   time_meaning=f"spool file {what}", **source, **common)
    return first


def _spool_dir(target) -> str:
    try:
        key = target.registry.key("HKLM\\SYSTEM\\CurrentControlSet\\Control\\Print\\Printers")
        val = str(key.value("DefaultSpoolDirectory").value)
        if re.match(r"^[A-Za-z]:\\", val):
            return val.rstrip("\\")
    except Exception:
        pass
    return "C:\\Windows\\System32\\spool\\PRINTERS"


def _spool_files(ev, target, spool_dir, common):
    """Spool files still on disk. Their job records (.SHD) are listed, not decoded."""
    folder = target.fs.path(spool_dir.replace("\\", "/"))
    try:
        files = sorted(folder.iterdir(), key=lambda f: f.name.lower()) if folder.exists() else []
    except Exception as e:
        ev.problem(spool_dir, e)
        return
    for f in files:
        try:
            st = f.lstat()
            ev.add("fileSeen", us_from_unix(st.st_birthtime), 1, _win(f), "print job", size=st.st_size,
                   artifact=_win(f), time_meaning="spool file creation time", **common)
            if f.name.lower().endswith(".shd"):
                ev.problem(_win(f), NotImplementedError("print job record not decoded"))
        except Exception as e:
            ev.problem(_win(f), e)


def _print_log(ev, target, common):
    """Event 307 (document printed) of the PrintService logs, where the log is enabled."""
    logs = target.fs.path("C:/Windows/System32/winevt/Logs")
    if not logs.exists():
        return
    from dissect.eventlog.evtx import Evtx
    for f in sorted(logs.iterdir(), key=lambda f: f.name.lower()):
        if "printservice" not in f.name.lower():
            continue
        try:
            for rec in Evtx(f.open("rb")):
                if str(rec.get("EventID")) != "307":
                    continue
                params = {k: str(v) for k, v in rec.items() if "Param" in k}
                doc = next((v for k, v in sorted(params.items()) if k.endswith("Param2")), "")
                when = rec.get("TimeCreated_SystemTime")
                if not doc or when is None:
                    raise ValueError(f"event record {rec.get('EventRecordID')}: no document name")
                ev.add("fileSeen", us(when), 1, doc, "print job",
                       artifact=f"{_win(f)} record {rec.get('EventRecordID')}", fields=params,
                       time_meaning="event time (document printed)", **common)
        except Exception as e:
            ev.problem(_win(f), e)


PROFILE_ROOTS = ("Users", "Documents and Settings")


def _profile_files(top, rel, out, problems):
    """Every file under a folder record, by name index, without following reparse points:
    path lower-cased -> (path, size, modified, created, changed, accessed)."""
    try:
        entries = list(top.iterdir(ignore_dos=True))
    except Exception as e:
        problems.append((rel, e))
        return
    for entry in entries:
        try:
            fn = entry.attribute
            a = fn.attr
            attrs, path = int(a.FileAttributes), rel + "\\" + fn.file_name
            if attrs & 0x10000000:                       # a folder
                if not attrs & 0x400:                    # not a junction or symbolic link
                    _profile_files(entry.dereference(), path, out, problems)
            else:
                out[path.lower()] = (path, int(a.FileSize), int(a.LastModificationTime),
                                     int(a.CreationTime), int(a.LastChangeTime), int(a.LastAccessTime))
        except Exception as e:
            problems.append((rel, e))


def _tree(ntfs):
    out, problems = {}, []
    for root in PROFILE_ROOTS:
        try:
            top = ntfs.mft.get(root)
        except Exception:
            continue
        if top.is_dir() and not top.is_reparse_point():
            _profile_files(top, root, out, problems)
    return out, problems


def _vss_storage_path(ntfs, store, drive, store_id):
    """Resolve the catalog's exact NTFS reference before claiming a store path."""
    raw_reference = store.desc3.metadata_reference
    if not isinstance(raw_reference, int) or isinstance(raw_reference, bool) or not 0 < raw_reference < 2**64:
        raise ValueError('VSS store metadata reference is not an unsigned NTFS reference')
    reference = int(raw_reference)
    segment, sequence = reference & 0xffffffffffff, reference >> 48
    if not segment or not sequence:
        raise ValueError('VSS store has no complete NTFS metadata reference')
    record = ntfs.mft.get(segment)
    if (record.segment != segment or int(record.header.SequenceNumber) != sequence
            or not (int(record.header.Flags) & 1) or not record.is_file() or record.is_reparse_point()):
        raise ValueError('VSS metadata reference does not resolve to the same allocated file')
    expected = f'System Volume Information\\{{{store_id}}}{{3808876b-c176-4e48-b7ae-04046e6cc752}}'
    matches = [path for path in record.full_paths() if isinstance(path, str)
               and path.casefold() == expected.casefold()]
    if len(set(matches)) != 1:
        raise ValueError('VSS store pathname is absent or ambiguous in referenced NTFS record')
    resolved = ntfs.mft.get(matches[0])
    if resolved.segment != segment or int(resolved.header.SequenceNumber) != sequence:
        raise ValueError('VSS store pathname resolves to a different NTFS file reference')
    return drive + '\\' + matches[0], dict(metadata_file_reference=reference,
                                          mft_segment=segment, mft_sequence=sequence)


def _vss_catalog_attributes(ev, vss, store, drive, serial, common, examined_at, *, ntfs=None):
    """Describe one catalog/store-header pair without opening snapshot content.

    Dissect joins the type-2 and type-3 descriptors by store identifier. The
    copy and set identifiers reside in the linked store-information header;
    creation time resides in the type-2 catalog descriptor. These are all
    observations of metadata on the examined volume, not reads inside a copy.
    """
    if examined_at is None:
        return  # Historical direct callers have no examination timestamp.
    if type(examined_at) is not int or examined_at <= 0:
        raise ValueError('VSS attributes need a positive examination timestamp')
    store_id = uuid.UUID(bytes_le=bytes(store.desc2.store_identifier))
    if bytes(store.desc3.store_identifier) != store_id.bytes_le:
        raise ValueError('VSS catalog descriptors refer to different stores')
    copy_id = uuid.UUID(str(store.copy_identifier))
    set_id = uuid.UUID(str(store.copy_set_identifier))
    created_ft = store.desc2.creation_time
    if not isinstance(created_ft, int) or isinstance(created_ft, bool) or created_ft < 0:
        raise ValueError('VSS catalog creation time is not an unsigned FILETIME')
    created_ft = int(created_ft)
    created_at = iso(us_from_filetime(created_ft))
    if created_ft % 10:
        created_at = created_at[:-1] + str(created_ft % 10) + 'Z'  # Retain FILETIME's seventh decimal.
    catalog_offset = vss.header.catalog_offset
    header_offset = store.desc3.store_header_offset
    if any(not isinstance(offset, int) or isinstance(offset, bool) or offset <= 0
           for offset in (catalog_offset, header_offset)):
        raise ValueError('VSS metadata offsets must identify retained volume bytes')
    catalog_offset, header_offset = int(catalog_offset), int(header_offset)
    catalog_artifact = f'{drive} VSS catalog at volume offset {catalog_offset}'
    header_artifact = f'{drive} VSS store information at volume offset {header_offset}'
    common = merge_scope(common)
    subject = json.dumps(subject_scope(common) + [drive, serial, 'VSS catalog store',
                         str(store_id), catalog_offset, header_offset, created_ft,
                         str(copy_id), str(set_id)], separators=(',', ':'), ensure_ascii=True)
    provenance = dict(common, artifact=catalog_artifact, source_path=drive,
                      parser='extractor.filetraces.vss_catalog', volume_serial=serial,
                      source_record_type='VSS catalog descriptors and linked store information',
                      catalog_offset=catalog_offset, store_header_offset=header_offset,
                      store_id='{' + str(store_id) + '}',
                      catalog_creation_filetime=created_ft,
                      metadata_scope='catalog and linked store header on examined volume; snapshot content not read')
    fields = [
        ('vss.copy_id', '{' + str(copy_id) + '}', 'store_information.copy_identifier', header_artifact),
        ('vss.set_id', '{' + str(set_id) + '}', 'store_information.copy_set_identifier', header_artifact),
        ('vss.created_at', created_at, 'catalog_entry_2.creation_time', catalog_artifact),
    ]
    path_locator = {}
    if ntfs is not None:
        try:
            storage_path, path_locator = _vss_storage_path(ntfs, store, drive, store_id)
            fields.insert(2, ('vss.storage_path', storage_path,
                              'catalog_entry_3.metadata_reference and NTFS FILE_NAME', storage_path))
        except Exception as error:
            ev.problem(catalog_artifact + ': store path', error)
    for role, value, field, artifact in fields:
        details = dict(provenance, artifact=artifact, source_field=field)
        if role == 'vss.storage_path':
            details.update(path_locator, source_path=value,
                           path_validation='catalog NTFS record and sequence, allocated file, matching store GUID filename')
        emit_attribute(ev, subject, role, value, examined_at, **details)


def _shadow_copies(ev, target, spool_dir, common, *, examined_at=None):
    from dissect.ntfs import NTFS
    from dissect.volume.vss import VSS
    common = merge_scope(common)
    for drive, serial, fs in _ntfs_volumes(target):
        try:
            live_first = _journal(ev, fs.ntfs, drive, spool_dir if spool_dir[:2].upper() == drive else "",
                                  common, volume_serial=serial)
        except Exception as e:
            ev.problem(f"{drive}\\$Extend\\$UsnJrnl:$J", e)
            live_first = None
        try:
            vss = VSS(fs.volume)
        except Exception as e:
            if "VSS identifier" not in str(e):
                ev.problem(f"{drive} shadow copy storage", e)
            continue
        live = None
        for store in vss.catalog.stores:
            artifact = f'{drive} VSS catalog entry'
            try:
                copy_id = "{%s}" % store.copy_identifier
                store_id = "{%s}" % uuid.UUID(bytes_le=bytes(store.desc2.store_identifier))
                artifact = f"{drive}\\System Volume Information\\{store_id}{{3808876b-c176-4e48-b7ae-04046e6cc752}}"
                created = us_from_filetime(int(store.creation_time))
                ev.add("shadowCopy", created, 1, copy_id, drive, artifact=artifact,
                       volume_serial=serial, store_id=store_id,
                       shadow_copy_set_id="{%s}" % store.copy_set_identifier,
                       originating_machine=str(store.information.operating_machine),
                       service_machine=str(store.information.service_machine),
                       attributes=str(store.information.attributes).split(".")[-1],
                       time_meaning="creation time in the shadow copy catalog", **common)
                try:
                    _vss_catalog_attributes(ev, vss, store, drive, serial, common, examined_at, ntfs=fs.ntfs)
                except Exception as e:
                    ev.problem(artifact + ': catalog attributes', e)
                snap = NTFS(store.open())
                source = dict(shadow_copy=copy_id)
                # The copy identifier above is an object named by base-volume
                # catalog bytes. Only reads through this opened store have VSS
                # byte origin; do not change or mutate the live/catalog scope.
                snapshot_common = merge_scope(common, {'source_snapshot': vss_snapshot(store.copy_identifier)})
                if live_first is not None:
                    _journal(ev, snap, drive, spool_dir if spool_dir[:2].upper() == drive else "",
                             snapshot_common, only_before=live_first, volume_serial=serial, shadow_copy=copy_id,
                             journal_source=f"journal as kept in shadow copy {copy_id}")
                if live is None:
                    live, problems = _tree(fs.ntfs)
                    for where, e in problems:
                        ev.problem(f"{drive}\\{where}", e)
                old, problems = _tree(snap)
                for where, e in problems:
                    ev.problem(f"shadow copy {copy_id} {drive}\\{where}", e)
                for low, (path, size, modified, born, changed, accessed) in sorted(old.items()):
                    now = live.get(low)
                    if now is not None and now[1] == size and now[2] == modified:
                        continue
                    state = ("missing on the live volume" if now is None else
                             "different on the live volume: " + ", ".join(
                                 w for w, differs in (("size", now[1] != size), ("modified time", now[2] != modified))
                                 if differs))
                    directory = drive + "\\" + path.rsplit("\\", 1)[0]
                    prov = dict(artifact=f"shadow copy {copy_id} of {drive} ({artifact})", state=state,
                                source_path=directory, source_stream='$I30',
                                source_record_type='directory FILE_NAME index entry',
                                shadow_copy_container=artifact,
                                size=size, modified=iso(us_from_filetime(modified)),
                                created=iso(us_from_filetime(born)), record_changed=iso(us_from_filetime(changed)),
                                accessed=iso(us_from_filetime(accessed)), volume_serial=serial,
                                live_comparison_source={key: common.get(key) for key in
                                    ('image', 'exhibit', 'source_snapshot', 'source_variant')},
                                **source, **snapshot_common)
                    if now is not None:
                        prov.update(live_size=now[1], live_modified=iso(us_from_filetime(now[2])))
                    m = re.match(r"^(?:Users|Documents and Settings)\\([^\\]+)\\", path)
                    if m:
                        prov["account"] = m.group(1)
                    ev.add("fileSeen", created, 1, drive + "\\" + path, "shadow copy",
                           time_meaning="creation time of the shadow copy: the file existed "
                                        "in this state then",
                           timestamp_source=dict(prov['live_comparison_source'], artifact=artifact,
                                                 field='VSS catalog creation_time'), **prov)
                    times = {}                           # one row per distinct file time
                    for ft, meaning in ((born, "the file's creation time in the shadow copy"),
                                        (modified, "the file's last-modified time in the shadow copy")):
                        if us_from_filetime(ft) >= 0:
                            times.setdefault(us_from_filetime(ft), []).append(meaning)
                    for t, meanings in sorted(times.items()):
                        ev.add("fileSeen", t, 1, drive + "\\" + path, "shadow copy",
                               time_meaning="; ".join(meanings),
                               timestamp_source={key: prov.get(key) for key in
                                   ('image', 'exhibit', 'source_snapshot', 'source_variant',
                                    'source_path', 'source_stream', 'source_record_type')}, **prov)
            except Exception as e:
                ev.problem(artifact, e)


# --------------------------------------------------------------------------- entry point

def extract(ev, target, ctx):
    common = merge_scope(ctx["common"])
    try:
        tz = str(target.timezone)
    except Exception as e:
        ev.problem("time zone in the registry", e)
        tz = ""
    try:
        _registry(ev, target, tz, common)
    except Exception as e:
        ev.problem("user registry hives", e)
    thumbs = {}
    try:
        thumbs = _search_index(ev, target, common, examined_at=ctx.get('examined_at'))
    except Exception as e:
        ev.problem(_win(SEARCH_DB), e)
    try:
        _thumbnail_caches(ev, target, thumbs, common)
    except Exception as e:
        ev.problem("thumbnail caches", e)
    spool_dir = _spool_dir(target)
    observation = {'examined_at': ctx['examined_at']} if 'examined_at' in ctx else {}
    for step, where in ((lambda: _shadow_copies(ev, target, spool_dir, common, **observation), "change journal and shadow copies"),
                        (lambda: _spool_files(ev, target, spool_dir, common), spool_dir),
                        (lambda: _print_log(ev, target, common), "PrintService event logs")):
        try:
            step()
        except Exception as e:
            ev.problem(where, e)
