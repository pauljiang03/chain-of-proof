"""Browsers, downloads, cloud-storage clients, e-mail accounts, the operating system's
search boxes and its note application, for every user profile of the Windows PC.

    extract(ev, target, ctx)     target is an open dissect Target

Kinds emitted: webVisit, fileDownloaded, localSearch, cloudFile, accountSeen, noteText.

Every row is one record of one artifact. Where an artifact holds two times for the same
thing (a history entry's accessed and modified time, a sync worker's start and finish),
each time is its own row and prov["time_meaning"] says which one it is.

dissect is imported inside the functions that need it, so the parsing helpers in the
first half of this file can be imported and tested with the standard library alone.
"""
from __future__ import annotations

import ast
import re
import struct
import uuid
from datetime import datetime, timedelta, timezone

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
FILETIME_EPOCH_US = 11_644_473_600_000_000        # 1601-01-01 to 1970-01-01, microseconds
UUID_EPOCH_US = 12_219_292_800_000_000            # 1582-10-15 to 1970-01-01, microseconds
SANE_FROM, SANE_TO = 631_152_000_000_000, 4_102_444_800_000_000     # 1990 .. 2100


# --------------------------------------------------------------------------- times

def us(dt: datetime) -> int:
    """Aware datetime -> UTC microseconds, exactly."""
    return (dt - EPOCH) // timedelta(microseconds=1)


def filetime_us(ft: int) -> int:
    """Windows FILETIME (100 ns since 1601, UTC) -> UTC microseconds since 1970."""
    return ft // 10 - FILETIME_EPOCH_US


def webkit_us(value: int) -> int:
    """Chrome time (microseconds since 1601, UTC) -> UTC microseconds since 1970."""
    return value - FILETIME_EPOCH_US


def local_filetime_us(ft: int, zone: str) -> int:
    """A FILETIME that holds local wall-clock time -> UTC microseconds since 1970."""
    from zoneinfo import ZoneInfo
    naive = datetime(1601, 1, 1) + timedelta(microseconds=ft // 10)
    return us(naive.replace(tzinfo=ZoneInfo(zone)))


def uuid1_us(text: str):
    """Creation time stored inside a version-1 GUID, as UTC microseconds; None for other versions."""
    try:
        u = uuid.UUID(text.strip().strip("{}"))
    except ValueError:
        return None
    return u.time // 10 - UUID_EPOCH_US if u.version == 1 else None


def decimal_seconds(text: str):
    """'1427141165.24' -> (UTC microseconds, resolution in microseconds), without float rounding."""
    whole, _, frac = text.partition(".")
    frac = frac[:6]
    return int(whole) * 1_000_000 + int(frac.ljust(6, "0") or 0), 10 ** (6 - len(frac))


def sane(t) -> bool:
    return isinstance(t, int) and SANE_FROM < t < SANE_TO


# ------------------------------------------------------- Internet Explorer history

MSHIST = re.compile(r"^MSHist01(\d{8})(\d{8})$")


def split_history_url(raw: str):
    """'Visited: user@http://x' or ':2015032320150324: user@http://x' -> (prefix, user, url).
    Returns None for a value that is not in that form."""
    raw = raw.rstrip("\x00")
    head, sep, url = raw.partition("@")
    if not sep or ": " not in head:
        return None
    prefix, _, user = head.rpartition(": ")
    return prefix + ":", user, url


def mshist_days(name: str):
    """Number of days a 'MSHist01<from><to>' container covers (1 = daily, 7 = weekly), else None."""
    m = MSHIST.match(name)
    if not m:
        return None
    try:
        a, b = (datetime.strptime(g, "%Y%m%d") for g in m.groups())
    except ValueError:
        return None
    return (b - a).days


def parse_iedownload(blob: bytes) -> dict:
    """The strings at the end of an IE download record: where the file came from and where
    it was saved. Raises ValueError when they are not there."""
    parts = blob.decode("utf-16-le", "ignore").split("\x00")
    if len(parts) < 3:
        raise ValueError("no strings in download record")
    url, path = parts[-3], parts[-2]
    if "://" not in url or not re.match(r"^([A-Za-z]:\\|\\\\)", path):
        raise ValueError("download record does not end with a URL and a saved path")
    out = {"url": url, "path": path}
    if len(parts) >= 6:
        if "://" in parts[-6]:
            out["referrer"] = parts[-6]
        if "/" in parts[-5] and " " not in parts[-5]:
            out["mime_type"] = parts[-5]
        if re.match(r"^[A-Za-z]:\\", parts[-4]):
            out["temporary_file"] = parts[-4]
    return out


# ------------------------------------------------------------------ protocol buffers

def _varint(buf: bytes, pos: int):
    value = shift = 0
    while True:
        b = buf[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not b & 0x80:
            return value, pos
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")


def pb_fields(buf: bytes):
    """Yield (field number, wire type, value) for one protocol-buffer message."""
    pos = 0
    while pos < len(buf):
        key, pos = _varint(buf, pos)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, pos = _varint(buf, pos)
        elif wire == 1:
            value, pos = buf[pos:pos + 8], pos + 8
        elif wire == 2:
            size, pos = _varint(buf, pos)
            if pos + size > len(buf):
                raise ValueError("field runs past the end of the message")
            value, pos = buf[pos:pos + size], pos + size
        elif wire == 5:
            value, pos = buf[pos:pos + 4], pos + 4
        else:
            raise ValueError(f"unsupported wire type {wire}")
        yield number, wire, value


def parse_history_provider_cache(buf: bytes):
    """Chrome's 'History Provider Cache' (InMemoryURLIndexCacheItem): the URL rows it
    cached, each with its recent visit times. Yields dicts."""
    for number, wire, value in pb_fields(buf):
        if number != 8 or wire != 2:                    # history_info_map
            continue
        for n2, w2, entry in pb_fields(value):
            if n2 != 2 or w2 != 2:                      # history_info_map_entry
                continue
            row = {"visits": []}
            for n3, w3, v3 in pb_fields(entry):
                if n3 == 1 and w3 == 0:
                    row["history_id"] = v3
                elif n3 == 2 and w3 == 0:
                    row["visit_count"] = v3
                elif n3 == 3 and w3 == 0:
                    row["typed_count"] = v3
                elif n3 == 4 and w3 == 0:
                    row["last_visit"] = v3
                elif n3 == 5 and w3 == 2:
                    row["url"] = v3.decode("utf-8", "replace")
                elif n3 == 6 and w3 == 2:
                    row["title"] = v3.decode("utf-8", "replace")
                elif n3 == 7 and w3 == 2:
                    visit = {n: v for n, w, v in pb_fields(v3) if w == 0}
                    if 1 in visit:
                        row["visits"].append((visit[1], visit.get(2, 0)))
            if "url" in row:
                yield row


# ------------------------------------------------------------- Google Drive sync log

LOG_HEAD = re.compile(r"^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d),(\d{3}) ([+-])(\d\d)(\d\d) "
                      r"(\w+) pid=(\d+) (\d+):(\S+)\s+(\S+?):(\d+) (.*)$")
PY_STR = r"""u?'(?:[^'\\]|\\.)*'|u?"(?:[^"\\]|\\.)*\""""
RAW_EVENT = re.compile(r"RawEvent\((\w+), path=(" + PY_STR + r"), time=(\d+(?:\.\d+)?)")
CHANGE = re.compile(r"ImmutableChange\(Direction\.(\w+), Action\.(\w+), ")
CHANGE_NAME = re.compile(r"name=(?:(" + PY_STR + r")|(.*?))(?:, (?:route|rid|ino|parent_ino|path|is_folder)=|\)$)")
CHANGE_PATH = re.compile(r"path=(" + PY_STR + r")")
CLOUD_ENTRY = re.compile(r"(?:Immutable)?CloudEntry\(doc_id=([^,]*),filename=(.*?),modified=(\d+|None),"
                         r"created=(\d+|None),acl_role=")
CLOUD_DELETE = re.compile(r"WorkerDeleteCloudEvent\(doc_id=([^,]*), server_mod_time=(\d+)")
CLOUD_NAME = re.compile(r"Updating cloud entry doc_id=([^,]*), filename=(.*)$")
LOCAL_ENTRY = re.compile(r"Updating local entry inode=(\d+), filename=(.*), modified=(\d+(?:\.\d+)?), "
                         r"checksum=(\w*), size=(\d+)$")
CREDENTIALS = re.compile(r"Initializing User instance with new credentials\. (\S+@\S+)$")
SYNC_ROOT = re.compile(r"^Sync root: (.*)$")
RAW_KINDS = {"CREATE": "created", "MODIFY": "modified", "DELETE": "deleted"}
SYNC_KINDS = {("UPLOAD", "CREATE"): "uploaded", ("UPLOAD", "MODIFY"): "uploaded",
              ("DOWNLOAD", "CREATE"): "downloaded", ("DOWNLOAD", "MODIFY"): "downloaded",
              ("UPLOAD", "DELETE"): "deleted", ("DOWNLOAD", "DELETE"): "deleted"}


def _py_str(literal: str) -> str:
    return ast.literal_eval(literal)


def _plain(path: str) -> str:
    return path[4:] if path.startswith("\\\\?\\") else path


def _in_folder(path: str, root: str) -> str:
    """Path relative to the sync folder when it lies inside it, else the path itself."""
    path = _plain(path)
    if root and path.lower().startswith(root.lower().rstrip("\\") + "\\"):
        return path[len(root.rstrip("\\")) + 1:]
    return path


def parse_drive_log(text: str):
    """Google Drive's sync_log.log -> (events, problems).

    An event is a dict: kind ('cloudFile' or 'accountSeen'), t, res, obj, event, line
    (1-based), meaning, and extra provenance. The log prints its own UTC offset on every
    line, so no time zone has to be assumed. An object the client logs several times
    (the same file-system event, the same cloud entry) gives one event, at its first line."""
    events, problems, seen = [], [], set()
    names = {}                                   # cloud document id -> file name, as logged
    root = ""
    line_t = None
    lines = text.splitlines()

    def add(key, **event):
        if key not in seen:
            seen.add(key)
            events.append(event)

    for number, line in enumerate(lines, start=1):
        root_m = SYNC_ROOT.match(line)
        if root_m:
            root = _plain(root_m.group(1).strip())
            continue
        m = LOG_HEAD.match(line)
        if not m:
            continue                             # continuation of a multi-line message
        y, mo, d, h, mi, s, ms = (int(x) for x in m.groups()[:7])
        offset = timedelta(hours=int(m.group(9)), minutes=int(m.group(10)))
        zone = timezone(-offset if m.group(8) == "-" else offset)
        line_t = us(datetime(y, mo, d, h, mi, s, ms * 1000, tzinfo=zone))
        msg = m.group(17)
        try:
            cm = CREDENTIALS.search(msg)
            if cm:
                add(("account", cm.group(1), line_t), kind="accountSeen", t=line_t, res=1000,
                    obj=cm.group(1), event="", line=number,
                    meaning="sync log line where the client starts using this account's credentials "
                            "(the account's creation time is not recorded)")
            for name_m in [CLOUD_NAME.search(msg)]:
                if name_m and name_m.group(2) not in ("None", ""):
                    names[name_m.group(1)] = name_m.group(2)
            for rm in RAW_EVENT.finditer(msg):
                kind, path, when = rm.group(1), _py_str(rm.group(2)), rm.group(3)
                if kind not in RAW_KINDS:
                    problems.append(f"line {number}: file-system event type {kind} not mapped")
                    continue
                t, res = decimal_seconds(when)
                add(("raw", kind, path, when), kind="cloudFile", t=t, res=res,
                    obj=_in_folder(path, root), event=RAW_KINDS[kind], line=number,
                    meaning="time of the file-system event the client saw in its sync folder",
                    local_path=_plain(path), log_event=f"RawEvent {kind}")
            wm = re.search(r"Worker (starting on|successfully completed) \[", msg)
            if wm:
                starts = [c.start() for c in CHANGE.finditer(msg)] + [len(msg)]
                for a, b in zip(starts, starts[1:]):
                    part = msg[a:b].rstrip(", ]")
                    direction, action = CHANGE.match(part).groups()
                    nm = CHANGE_NAME.search(part)
                    if not nm:
                        problems.append(f"line {number}: sync change without a file name")
                        continue
                    name = _py_str(nm.group(1)) if nm.group(1) else nm.group(2)
                    pm = CHANGE_PATH.search(part)
                    full = (_plain(_py_str(pm.group(1))).rstrip("\\") + "\\" + name) if pm else ""
                    stage = "started" if wm.group(1) == "starting on" else "completed"
                    add(("worker", stage, direction, action, name, line_t), kind="cloudFile",
                        t=line_t, res=1000, obj=_in_folder(full, root) if full else name,
                        event=SYNC_KINDS.get((direction, action), "synced"), line=number,
                        meaning=f"sync worker {stage} this change (log line time)",
                        log_event=f"Direction.{direction}, Action.{action}", local_path=full)
            for em in CLOUD_ENTRY.finditer(msg):
                doc, name, modified, created = em.groups()
                names.setdefault(doc, name)
                for label, value in (("created", created), ("modified", modified)):
                    if value != "None":
                        add(("cloud", doc, name, label, value), kind="cloudFile",
                            t=int(value) * 1_000_000, res=1_000_000, obj=name, event=label, line=number,
                            meaning=f"'{label}' time of the cloud entry, as the server reported it",
                            doc_id=doc)
            for dm in CLOUD_DELETE.finditer(msg):
                doc, when = dm.groups()
                add(("clouddel", doc, when), kind="cloudFile", t=int(when) * 1_000_000,
                    res=1_000_000, obj=names.get(doc, "document id " + doc), event="deleted",
                    line=number, doc_id=doc,
                    meaning="server modification time of the cloud-side deletion; the file name is "
                            "the one this log gives for the document id")
            lm = LOCAL_ENTRY.search(msg)
            if lm:
                inode, name, when, checksum, size = lm.groups()
                t, res = decimal_seconds(when)
                add(("local", inode, name, when), kind="cloudFile", t=t, res=res,
                    obj=_in_folder(name, root), event="modified", line=number,
                    meaning="last-modified time of the file itself, as the client stored it for "
                            "its local entry", md5=checksum, size=int(size))
        except (ValueError, SyntaxError) as e:
            problems.append(f"line {number}: {type(e).__name__}: {e}")
    return events, problems


# ------------------------------------------------------------------- small decoders

def reg_text(value) -> str:
    """A registry value as text. Office stores many strings as UTF-16 in binary values."""
    if isinstance(value, bytes):
        if len(value) % 2 == 0:
            try:
                return value.decode("utf-16-le").split("\x00")[0]
            except UnicodeDecodeError:
                pass
        return value.split(b"\x00")[0].decode("latin-1")
    return "" if value is None else str(value)


def mru_order(blob: bytes):
    """MRUListEx: 32-bit indexes, most recent first, ended by 0xFFFFFFFF."""
    out = []
    for (i,) in struct.iter_unpack("<I", blob[:len(blob) // 4 * 4]):
        if i == 0xFFFFFFFF:
            break
        out.append(i)
    return out


def note_text(raw: bytes) -> str:
    """Stream '3' of a Sticky Notes storage: the note as UTF-16 text."""
    return raw.decode("utf-16-le", "replace").split("\x00")[0].replace("\r\n", "\n").strip()


OEACCOUNT_FIELD = re.compile(r"<(\w+) type=\"(\w+)\">(.*?)</\1>", re.S)


def parse_oeaccount(raw: bytes) -> dict:
    """Windows Mail .oeaccount file (XML, usually UTF-16) -> {field: text}."""
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "replace")
    return {name: value for name, _type, value in OEACCOUNT_FIELD.findall(text)}


# ============================================================ the image (uses dissect)

def _win(path) -> str:
    return str(path).replace("/", "\\")


def _users(target):
    """(profile name, profile folder) for every real folder under C:\\Users."""
    out = []
    for p in sorted(target.fs.path("C:/Users").iterdir(), key=lambda x: x.name.lower()):
        try:
            if p.is_symlink() or not p.is_dir():
                continue
        except Exception:
            continue
        out.append((p.name, p))
    return out


def _hive_user(key) -> str:
    """Profile a registry key belongs to, from the path of the hive file it was read from."""
    path = str(getattr(key.hive, "filepath", "") or "").replace("\\", "/")
    m = re.search(r"/Users/([^/]+)/", path, re.I)
    if m:
        return m.group(1)
    parts = [x for x in path.split("/") if x]
    return parts[-2] if len(parts) >= 2 else ""


def _hive_path(key) -> str:
    return _win(getattr(key.hive, "filepath", "") or "")


def _keys(target, path):
    try:
        return list(target.registry.keys(path))
    except Exception:
        return []


# ------------------------------------------------------------------ Internet Explorer

def _ie_webcache(ev, target, common, zone):
    from dissect.database.ese import ESE
    for user, home in _users(target):
        path = home.joinpath("AppData/Local/Microsoft/Windows/WebCache/WebCacheV01.dat")
        if not path.exists():
            continue
        source = _win(path)
        try:
            db = ESE(path.open("rb"))
            containers = [(r.get("ContainerId"), (r.get("Name") or "").rstrip("\x00"),
                           (r.get("Directory") or "").rstrip("\x00"))
                          for r in db.table("Containers").records()]
        except Exception as e:
            ev.problem(source, e)
            continue
        for cid, name, folder in containers:
            days = mshist_days(name)
            if name != "History" and days is None and name.lower() != "iedownload":
                continue
            try:
                records = list(db.table(f"Container_{cid}").records())
            except Exception as e:
                ev.problem(f"{source} Container_{cid} ({name})", e)
                continue
            for r in records:
                where = f"{source} table Container_{cid} ({name}) EntryId {r.get('EntryId')}"
                try:
                    if name.lower() == "iedownload":
                        _ie_download(ev, r, where, user, folder, common)
                    else:
                        _ie_visit(ev, r, where, user, name, folder, days, zone, common)
                except Exception as e:
                    ev.problem(where, e)


def _ie_visit(ev, r, where, user, name, folder, days, zone, common):
    parts = split_history_url(r.get("Url") or "")
    if parts is None:
        raise ValueError(f"history entry not in 'prefix: user@url' form: {r.get('Url')!r}")
    prefix, owner, url = parts
    if url.startswith(":Host: "):
        return                      # a per-host grouping row of the daily/weekly index, not a page
    accessed, modified = r.get("AccessedTime") or 0, r.get("ModifiedTime") or 0
    base = dict(artifact=where, account=user, container=name, container_folder=folder,
                recorded_user=owner, access_count=r.get("AccessCount") or 0, **common)
    if days is None:                # the main history: both times are UTC
        if accessed:
            ev.add("webVisit", filetime_us(accessed), 1, url, "Internet Explorer",
                   time_meaning="AccessedTime of the history entry (last visit, UTC)", **base)
        if modified and modified != accessed:
            ev.add("webVisit", filetime_us(modified), 1, url, "Internet Explorer",
                   time_meaning="ModifiedTime of the history entry (a time before its last "
                                "access at which the entry was written, UTC)", **base)
        if not accessed and not modified:
            raise ValueError("history entry without a time")
        return
    span = "daily" if days == 1 else "weekly" if days == 7 else f"{days}-day"
    if modified:
        if not zone:
            raise ValueError("local-time entry, and the PC's time zone could not be read")
        ev.add("webVisit", local_filetime_us(modified, zone), 1, url, "Internet Explorer",
               time_meaning=f"ModifiedTime of the {span} history entry: last visit in that "
                            "period, stored as local time",
               time_zone=f"local time, converted from {zone} (the zone the PC's registry names)",
               period=prefix.strip(":"),
               accessed_time_utc=filetime_us(accessed) if accessed else 0, **base)
    elif accessed:
        ev.add("webVisit", filetime_us(accessed), 1, url, "Internet Explorer",
               time_meaning=f"AccessedTime of the {span} history entry (UTC)",
               period=prefix.strip(":"), **base)
    else:
        raise ValueError("history entry without a time")


def _ie_download(ev, r, where, user, folder, common):
    blob = r.get("ResponseHeaders")
    if not blob:
        raise ValueError("download record without data")
    d = parse_iedownload(bytes(blob))
    extra = {k: d[k] for k in ("referrer", "mime_type", "temporary_file") if k in d}
    record_id = (r.get("Url") or "").rstrip("\x00")
    base = dict(artifact=where, account=user, container_folder=folder, record_id=record_id,
                browser="Internet Explorer", **extra, **common)
    accessed = r.get("AccessedTime") or 0
    started = uuid1_us(record_id.partition(":")[2])
    if accessed:
        ev.add("fileDownloaded", filetime_us(accessed), 1, d["path"], d["url"],
               time_meaning="AccessedTime of the download record: its last update. The record has "
                            "no start-time field", **base)
    if started is not None and sane(started):
        ev.add("fileDownloaded", started, 1, d["path"], d["url"],
               time_meaning="creation time inside the version-1 GUID that names the download "
                            "record (when Internet Explorer created the record)", **base)
    if not accessed and started is None:
        raise ValueError("download record without a time")


def _ie_typed_urls(ev, target, common):
    base = "HKCU\\Software\\Microsoft\\Internet Explorer\\"
    times = {}
    for key in _keys(target, base + "TypedURLsTime"):
        for v in key.values():
            if isinstance(v.value, bytes) and len(v.value) == 8:
                times[(_hive_path(key), v.name.lower())] = struct.unpack("<Q", v.value)[0]
    for key in _keys(target, base + "TypedURLs"):
        hive = _hive_path(key)
        for v in key.values():
            try:
                url = reg_text(v.value)
                if not url:
                    continue
                prov = dict(artifact=f"{base}TypedURLs value {v.name}", hive=hive,
                            account=_hive_user(key), **common)
                ft = times.get((hive, v.name.lower()), 0)
                if ft:
                    ev.add("webVisit", filetime_us(ft), 1, url, "Internet Explorer",
                           time_meaning="TypedURLsTime: when this address was typed", **prov)
                else:
                    ev.add("webVisit", us(key.timestamp), 1, url, "Internet Explorer",
                           time_meaning="registry key last-write time; the key stores no time "
                                        "for this typed address", **prov)
            except Exception as e:
                ev.problem(f"{hive} {base}TypedURLs {v.name}", e)


# -------------------------------------------------------------------------- Chrome

VISIT_SOURCES = {0: "synced", 1: "browsed", 2: "extension", 3: "imported from Firefox",
                 4: "imported from Internet Explorer", 5: "imported from Safari"}


def _rows(db, table):
    t = db.table(table)
    return [] if t is None else list(t.rows())


def _chrome_profiles(home):
    top = home.joinpath("AppData/Local/Google/Chrome/User Data")
    if not top.exists():
        return []
    return [p for p in sorted(top.iterdir(), key=lambda x: x.name)
            if p.is_dir() and (p.joinpath("History").exists() or p.joinpath("Preferences").exists())]


def _chrome(ev, target, common):
    from dissect.database.sqlite3 import SQLite3
    for user, home in _users(target):
        for profile in _chrome_profiles(home):
            path = profile.joinpath("History")
            if path.exists():
                try:
                    _chrome_history(ev, SQLite3(path.open("rb")), _win(path), user, common)
                except Exception as e:
                    ev.problem(_win(path), e)
            path = profile.joinpath("Shortcuts")
            if path.exists():
                try:
                    for i, r in enumerate(_rows(SQLite3(path.open("rb")), "omni_box_shortcuts")):
                        if r.url and r.last_access_time:
                            ev.add("webVisit", webkit_us(r.last_access_time), 1, r.url, "Chrome",
                                   artifact=f"{_win(path)} table omni_box_shortcuts id {r.id}",
                                   account=user, typed_text=r.text or "", hits=r.number_of_hits or 0,
                                   time_meaning="last time this address-bar shortcut was used",
                                   **common)
                except Exception as e:
                    ev.problem(_win(path), e)
            path = profile.joinpath("History Provider Cache")
            if path.exists():
                try:
                    for row in parse_history_provider_cache(path.open("rb").read()):
                        prov = dict(artifact=f"{_win(path)} entry for history id {row.get('history_id')}",
                                    account=user, title=row.get("title", ""), **common)
                        for when, transition in row["visits"]:
                            ev.add("webVisit", webkit_us(when), 1, row["url"], "Chrome",
                                   time_meaning="visit time kept in Chrome's cache of its history",
                                   transition=transition, **prov)
                        if not row["visits"] and row.get("last_visit"):
                            ev.add("webVisit", webkit_us(row["last_visit"]), 1, row["url"], "Chrome",
                                   time_meaning="last-visit time kept in Chrome's cache of its history",
                                   **prov)
                except Exception as e:
                    ev.problem(_win(path), e)


def _chrome_history(ev, db, source, user, common):
    urls = {r.id: r for r in _rows(db, "urls")}
    sources = {r.id: r.source for r in _rows(db, "visit_source")}
    visited = set()
    for v in _rows(db, "visits"):
        u = urls.get(v.url)
        if u is None or not u.url:
            ev.problem(f"{source} table visits id {v.id}", ValueError(f"no urls row {v.url}"))
            continue
        visited.add(v.url)
        prov = dict(artifact=f"{source} table visits id {v.id}", account=user, title=u.title or "",
                    transition=v.transition or 0, from_visit=v.from_visit or 0,
                    time_meaning="visit time", **common)
        if v.id in sources:
            prov["visit_source"] = VISIT_SOURCES.get(sources[v.id], str(sources[v.id]))
        ev.add("webVisit", webkit_us(v.visit_time), 1, u.url, "Chrome", **prov)
    for uid, u in sorted(urls.items()):
        if uid not in visited and u.url and u.last_visit_time:
            ev.add("webVisit", webkit_us(u.last_visit_time), 1, u.url, "Chrome",
                   artifact=f"{source} table urls id {uid}", account=user, title=u.title or "",
                   time_meaning="last-visit time of a URL row that has no visit rows", **common)
    chains = {}
    for c in _rows(db, "downloads_url_chains"):
        chains.setdefault(c.id, []).append((c.chain_index, c.url))
    for d in _rows(db, "downloads"):
        saved = d.get("target_path") or d.get("current_path") or d.get("full_path")
        chain = sorted(chains.get(d.id, []))
        if not chain and d.get("url"):
            chain = [(0, d.get("url"))]                 # older schema: one URL column
        if not saved or not chain or not d.start_time:
            ev.problem(f"{source} table downloads id {d.id}", ValueError("no path, URL or start time"))
            continue
        for index, url in chain:
            ev.add("fileDownloaded", webkit_us(d.start_time), 1, saved, url,
                   artifact=f"{source} table downloads id {d.id}, downloads_url_chains index {index}",
                   account=user, browser="Chrome", url_chain_position=f"{index + 1} of {len(chain)}",
                   end_time=webkit_us(d.end_time) if d.get("end_time") else 0,
                   received_bytes=d.get("received_bytes") or 0, total_bytes=d.get("total_bytes") or 0,
                   state=d.get("state") or 0, referrer=d.get("referrer") or "",
                   time_meaning="start time of the download", **common)


# ----------------------------------------------------------------- cloud storage

def _google_drive(ev, target, common):
    for user, home in _users(target):
        top = home.joinpath("AppData/Local/Google/Drive")
        if not top.exists():
            continue
        for folder in sorted(top.iterdir(), key=lambda x: x.name):
            path = folder.joinpath("sync_log.log")
            try:
                if not folder.is_dir() or not path.exists():
                    continue
                text = path.open("rb").read().decode("utf-8", "replace")
            except Exception as e:
                ev.problem(_win(path), e)
                continue
            source = _win(path)
            events, problems = parse_drive_log(text)
            for p in problems:
                ev.problem(source, ValueError(p))
            for e in events:
                extra = {k: v for k, v in e.items()
                         if k not in ("kind", "t", "res", "obj", "event", "line", "meaning") and v != ""}
                prov = dict(artifact=f"{source} line {e['line']}", account=user,
                            time_meaning=e["meaning"],
                            time_zone="UTC offset printed on the log line", **extra, **common)
                if e["kind"] == "accountSeen":
                    ev.add("accountSeen", e["t"], e["res"], e["obj"], "google drive", **prov)
                else:
                    ev.add("cloudFile", e["t"], e["res"], e["obj"], "google drive: " + e["event"], **prov)


def _icloud(ev, target, common):
    """iCloud for Windows keeps the signed-in account in a property list."""
    import plistlib
    for user, home in _users(target):
        path = home.joinpath("AppData/Roaming/Apple Computer/Preferences/mobilemeaccounts.plist")
        if not path.exists():
            continue
        try:
            data = plistlib.loads(path.open("rb").read())
            t = round(path.lstat().st_mtime * 1_000_000)
            for account in data.get("Accounts", []):
                name = account.get("AccountID") or account.get("LoginAs") or ""
                if name:
                    ev.add("accountSeen", t, 1, str(name), "icloud", artifact=_win(path), account=user,
                           time_meaning="last-modified time of the property list (the account's "
                                        "creation time is not recorded)", **common)
        except Exception as e:
            ev.problem(_win(path), e)


# --------------------------------------------------------------- e-mail accounts

ACCOUNTS_KEY = "9375CFF0413111d3B88A00104B2A6676"
MAIL_VALUES = ("Email", "POP3 Server", "IMAP Server", "SMTP Server", "HTTP Server URL")


def _outlook_profiles(ev, target, common):
    roots = []
    for office in _keys(target, "HKCU\\Software\\Microsoft\\Office"):
        for version in office.subkeys():
            try:
                roots.append((f"HKCU\\Software\\Microsoft\\Office\\{version.name}\\Outlook\\Profiles",
                              version.subkey("Outlook").subkey("Profiles")))
            except Exception:
                continue
    old = "HKCU\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Windows Messaging Subsystem\\Profiles"
    roots += [(old, k) for k in _keys(target, old)]
    for root_path, root in roots:
        for profile in root.subkeys():
            try:
                accounts = profile.subkey(ACCOUNTS_KEY)
            except Exception:
                continue
            for acc in accounts.subkeys():
                where = f"{root_path}\\{profile.name}\\{ACCOUNTS_KEY}\\{acc.name}"
                try:
                    values = {v.name: reg_text(v.value) for v in acc.values()}
                    name = values.get("Account Name", "")
                    address = values.get("Email") or (name if "@" in name else "")
                    if not address and not any(values.get(v) for v in MAIL_VALUES):
                        continue                 # an address book or other non-mail service
                    ev.add("accountSeen", us(acc.timestamp), 1, address or name, "outlook e-mail",
                           artifact=where, hive=_hive_path(acc), account=_hive_user(acc),
                           outlook_profile=profile.name, account_name=name,
                           service=values.get("Service Name", ""),
                           display_name=values.get("Display Name", ""),
                           servers=", ".join(values[v] for v in MAIL_VALUES[1:] if values.get(v)),
                           time_meaning="registry key last-write time (the account's creation "
                                        "time is not recorded)", **common)
                except Exception as e:
                    ev.problem(where, e)


def _mail_files(ev, target, common):
    for user, home in _users(target):
        box = home.joinpath("AppData/Local/Microsoft/Outlook")
        if box.exists():
            for p in sorted(box.iterdir(), key=lambda x: x.name):
                stem, dot, ext = p.name.rpartition(".")
                if ext.lower() not in ("ost", "pst") or "@" not in stem:
                    continue
                try:
                    st = p.lstat()
                    ev.add("accountSeen", round(st.st_birthtime * 1_000_000), 1, stem, "outlook e-mail",
                           artifact=_win(p), account=user, size=st.st_size,
                           time_meaning="creation time of the mailbox file, which is named after "
                                        "the account (the account's creation time is not recorded)",
                           **common)
                except Exception as e:
                    ev.problem(_win(p), e)
        for rel, service in (("AppData/Local/Microsoft/Windows Mail", "windows mail e-mail"),
                             ("AppData/Local/Microsoft/Windows Live Mail", "windows live mail e-mail")):
            top = home.joinpath(rel)
            if not top.exists():
                continue
            for p in sorted(top.rglob("*.oeaccount"), key=str):
                try:
                    fields = parse_oeaccount(p.open("rb").read())
                    address = fields.get("SMTP_Email_Address", "")
                    if not address:
                        continue                 # news and directory-service accounts
                    stamp = fields.get("Last_Updated", "")
                    if re.fullmatch(r"[0-9a-fA-F]{16}", stamp):
                        t = filetime_us(struct.unpack("<Q", bytes.fromhex(stamp))[0])
                        meaning = "Last_Updated time stored in the account file"
                    else:
                        t = round(p.lstat().st_mtime * 1_000_000)
                        meaning = "last-modified time of the account file"
                    ev.add("accountSeen", t, 1, address, service, artifact=_win(p), account=user,
                           account_name=fields.get("Account_Name", ""),
                           servers=", ".join(fields[k] for k in ("POP3_Server", "IMAP_Server", "SMTP_Server")
                                             if fields.get(k)),
                           time_meaning=meaning, **common)
                except Exception as e:
                    ev.problem(_win(p), e)


# ------------------------------------------------------------ searches and notes

def _local_search(ev, target, common):
    path = "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\WordWheelQuery"
    for key in _keys(target, path):
        try:
            values = {v.name: v.value for v in key.values()}
            order = mru_order(values.get("MRUListEx") or b"")
            for name, raw in sorted(values.items()):
                if name == "MRUListEx" or not isinstance(raw, bytes):
                    continue
                text = raw.decode("utf-16-le", "replace").split("\x00")[0]
                if not text:
                    continue
                rank = order.index(int(name)) + 1 if name.isdigit() and int(name) in order else 0
                ev.add("localSearch", us(key.timestamp), 1, text, "Windows Explorer search box",
                       artifact=f"{path} value {name}", hive=_hive_path(key), account=_hive_user(key),
                       recency_rank=rank, entries=len(order),
                       time_meaning="registry key last-write time: the moment the most recent "
                                    "search (recency_rank 1) was typed; older entries were typed "
                                    "at or before it", **common)
        except Exception as e:
            ev.problem(f"{_hive_path(key)} {path}", e)


def _sticky_notes(ev, target, common):
    from dissect.ole import OLE
    for user, home in _users(target):
        path = home.joinpath("AppData/Roaming/Microsoft/Sticky Notes/StickyNotes.snt")
        if not path.exists():
            continue
        source = _win(path)
        try:
            ole = OLE(path.open("rb"))
            file_t = round(path.lstat().st_mtime * 1_000_000)
            for name, entry in sorted(ole.root.listdir().items()):
                if not entry.is_storage:
                    continue
                streams = entry.listdir()
                if "3" not in streams:
                    ev.problem(f"{source} storage {name}", ValueError("note without a text stream"))
                    continue
                text = note_text(streams["3"].open().read())
                base = dict(artifact=f"{source} storage {name} stream 3", account=user, note_id=name,
                            **common)
                ev.add("noteText", file_t, 1, text, "Sticky Notes",
                       time_meaning="last-modified time of the Sticky Notes file", **base)
                if entry.mtime is not None:
                    ev.add("noteText", us(entry.mtime), 1, text, "Sticky Notes",
                           time_meaning="modified time of this note's storage inside the Sticky "
                                        "Notes file", **base)
        except Exception as e:
            ev.problem(source, e)


# ----------------------------------------------------------------------- entry point

def extract(ev, target, ctx):
    common = ctx["common"]
    try:
        zone = str(target.timezone)          # dissect reads TimeZoneInformation from the registry
        if not zone or zone == "None":
            raise ValueError("no time zone in the registry")
    except Exception as e:
        ev.problem("HKLM\\SYSTEM\\CurrentControlSet\\Control\\TimeZoneInformation", e)
        zone = ""
    for step in (_ie_typed_urls, _chrome, _google_drive, _icloud, _outlook_profiles, _mail_files,
                 _local_search, _sticky_notes):
        try:
            step(ev, target, common)
        except Exception as e:
            ev.problem(step.__name__.strip("_"), e)
    try:
        _ie_webcache(ev, target, common, zone)
    except Exception as e:
        ev.problem("ie_webcache", e)
