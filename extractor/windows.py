"""The Windows PC image: USB devices, volumes the registry recorded, shortcuts,
jump lists, web searches, the user's files, Recycle Bin records, CD-burn traces and
the user's mailbox."""
from __future__ import annotations

import io
import re
import struct
from datetime import datetime
from urllib.parse import parse_qs, unquote_plus, urlsplit
from zoneinfo import ZoneInfo

from dissect.ole import OLE
from dissect.shellitem.lnk import Lnk
from dissect.target import Target

from .store import Evidence, us, us_from_filetime, us_from_unix

USER_DIRS = ("Desktop", "Documents", "Downloads")
SEARCH_PARAMS = {"google.": "q", "bing.": "q", "yahoo.": "p"}


def _usb(ev, t, common):
    path = "HKLM\\SYSTEM\\CurrentControlSet\\Enum\\USBSTOR"
    for dev in t.registry.key(path).subkeys():
        for inst in dev.subkeys():
            ev.add("usbInsert", us(inst.timestamp), 1, inst.name.split("&")[0], "",
                   artifact=f"{path}\\{dev.name}\\{inst.name}", device=dev.name,
                   time_meaning="registry key last-write time", **common)


def _setupapi(ev, t, common, tz: str):
    """First connection of each USB storage device, from the device install log.
    The log prints local time with no zone; convert with the PC's zone."""
    path = t.fs.path("C:/Windows/inf/setupapi.dev.log")
    if not path.exists():
        return
    lines = path.open("rb").read().decode("utf-8", "replace").splitlines()
    head = re.compile(r"^>>>\s+\[Device Install \(Hardware initiated\) - USBSTOR\\([^\\]+)\\([^\]]+)\]")
    start = re.compile(r"^>>>\s+Section start (\d{4})/(\d\d)/(\d\d) (\d\d):(\d\d):(\d\d)\.(\d{3})")
    for i, line in enumerate(lines[:-1]):
        m, when = head.match(line), start.match(lines[i + 1])
        if not (m and when):
            continue
        y, mo, d, h, mi, sec, ms = map(int, when.groups())
        local = datetime(y, mo, d, h, mi, sec, ms * 1000, tzinfo=ZoneInfo(tz))
        ev.add("usbInsert", us(local), 1000, m.group(2).split("&")[0], "",
               artifact=f"C:\\Windows\\inf\\setupapi.dev.log line {i + 1}", device=m.group(1),
               time_meaning="device install section start (first connection)",
               time_zone=f"log local time, converted from {tz}", **common)


def _volumes_seen(ev, t, common):
    path = "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\EMDMgmt"
    for sub in t.registry.key(path).subkeys():
        m = re.match(r"^(.{6})(.*)_(\d+)$", sub.name)
        if not m:
            continue
        ev.add("volumeSeen", us(sub.timestamp), 1, m.group(2), "%08X" % int(m.group(3)),
               artifact=f"{path}\\{sub.name}", time_meaning="registry key last-write time",
               **common)


def _lnk_fact(ev, lnk: Lnk, t_us: int, common: dict, **prov) -> bool:
    """One lnkTarget fact from a parsed shortcut. obj = path without the drive letter,
    aux = the volume serial for a local target, or the share for a network target."""
    info = getattr(lnk, "linkinfo", None)
    if info is None or getattr(info, "flags", None) is None:
        return False            # a shortcut with no LinkInfo block names no volume
    base = getattr(info, "local_base_path", None)
    base = base.decode("utf-8", "replace") if isinstance(base, bytes) else (base or "")
    vol = getattr(info, "volumeid", None)
    net = getattr(info, "common_network_relative_link", None)
    net_name = ""
    if net is not None:
        raw = getattr(net, "net_name", b"") or b""
        raw = getattr(raw, "net_name", raw) or b""      # older dissect wraps it once more
        net_name = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
    suffix = getattr(info, "common_path_suffix", b"") or b""
    suffix = suffix.decode("utf-8", "replace") if isinstance(suffix, bytes) else str(suffix)
    if base and vol is not None and re.match(r"^[A-Za-z]:\\", base):
        label = (vol.data or b"").split(b"\x00")[0].decode("utf-8", "replace")
        ev.add("lnkTarget", t_us, 1, base[2:], "%08X" % vol.drive_serial_number,
               drive_letter=base[:2], volume_label=label, drive_type=int(vol.drive_type),
               **prov, **common)
        return True
    if net_name:
        ev.add("lnkTarget", t_us, 1, "\\" + suffix.lstrip("\\"), net_name.lower(),
               network_share=net_name, **prov, **common)
        return True
    return False


def _lnk_files(ev, t, common):
    n = 0
    for user in t.fs.path("C:/Users").iterdir():
        for rel in ("AppData/Roaming/Microsoft/Windows/Recent",
                    "AppData/Roaming/Microsoft/Office/Recent"):
            folder = user.joinpath(rel)
            if not folder.exists():
                continue
            for p in sorted(folder.iterdir(), key=lambda x: x.name):
                if not p.name.lower().endswith(".lnk"):
                    continue
                try:
                    with p.open("rb") as fh:
                        lnk = Lnk(fh)
                        st = p.lstat()
                        n += _lnk_fact(
                            ev, lnk, us_from_unix(st.st_mtime), common,
                            artifact=str(p).replace("/", "\\"), user=user.name,
                            time_meaning="shortcut file last-modified time (last open via the shell)",
                            shortcut_created=us_from_unix(st.st_birthtime))
                except Exception as e:
                    ev.problem(str(p), e)
    return n


def _destlist(data: bytes) -> dict:
    """Windows 7 DestList (version 1): stream name -> (last access FILETIME, path)."""
    if len(data) < 32 or struct.unpack_from("<I", data, 0)[0] != 1:
        return {}
    out, off = {}, 32
    while off + 0x72 <= len(data):
        entry = struct.unpack_from("<Q", data, off + 0x58)[0]
        filetime = struct.unpack_from("<Q", data, off + 0x64)[0]
        length = struct.unpack_from("<H", data, off + 0x70)[0]
        path = data[off + 0x72: off + 0x72 + 2 * length].decode("utf-16-le", "replace")
        out["%x" % entry] = (filetime, path)
        off += 0x72 + 2 * length
    return out


def _jumplists(ev, t, common):
    n = 0
    for user in t.fs.path("C:/Users").iterdir():
        folder = user.joinpath("AppData/Roaming/Microsoft/Windows/Recent/AutomaticDestinations")
        if not folder.exists():
            continue
        for p in sorted(folder.iterdir(), key=lambda x: x.name):
            try:
                ole = OLE(p.open("rb"))
                names = list(ole.root.listdir())
                if "DestList" not in names:
                    continue
                dest = _destlist(ole.get("DestList").open().read())
                for name in names:
                    if name == "DestList" or name not in dest:
                        continue
                    filetime, dest_path = dest[name]
                    t_us = us_from_filetime(filetime)
                    if not 0 < t_us < 4_102_444_800_000_000:   # sanity: before 2100
                        continue
                    lnk = Lnk(io.BytesIO(ole.get(name).open().read()))
                    prov = dict(artifact=f"{str(p).replace('/', chr(92))} stream {name}",
                                user=user.name, destlist_path=dest_path,
                                time_meaning="jump list DestList last-access time for this entry")
                    if _lnk_fact(ev, lnk, t_us, common, **prov):
                        n += 1
                    elif re.match(r"^[A-Za-z]:\\", dest_path):
                        # no LinkInfo block, so no volume serial: keep the path, leave
                        # the volume empty rather than guess it from the drive letter
                        ev.add("lnkTarget", t_us, 1, dest_path[2:].rstrip("\\") or "\\", "",
                               drive_letter=dest_path[:2],
                               volume="not recorded by this jump list entry", **prov, **common)
                        n += 1
            except Exception as e:
                ev.problem(str(p), e)
    return n


def _searches(ev, t, common):
    n = 0
    for r in t.browser.history():
        url = r.url or ""
        parts = urlsplit(url)
        param = next((p for host, p in SEARCH_PARAMS.items() if host in parts.netloc), None)
        if param is None or r.ts is None:
            continue
        # Google puts the search being shown in the fragment (#q=...); the query string
        # may still carry an earlier search, so the fragment wins.
        query = parse_qs(parts.fragment).get(param) or parse_qs(parts.query).get(param)
        if not query or not query[0].strip():
            continue
        ev.add("webSearch", us(r.ts), 1, unquote_plus(query[0]).strip(), str(r.browser),
               artifact=str(r.source).replace("/", "\\"), url=url[:300], user=r.username,
               time_meaning="browser history visit time", **common)
        n += 1
    return n


def _user_files(ev, t, common):
    fs = t.fs.mounts["c:"]
    vsn = "%08X" % (fs.ntfs.serial & 0xFFFFFFFF)
    n = 0
    for user in t.fs.path("C:/Users").iterdir():
        for d in USER_DIRS:
            top = user.joinpath(d)
            if not top.exists():
                continue
            for p in sorted(top.rglob("*"), key=str):
                try:
                    if not p.is_file():
                        continue
                    st = p.lstat()
                except Exception as e:
                    ev.problem(str(p), e)
                    continue
                rel = str(p).replace("/", "\\")
                rel = rel[2:] if re.match(r"^[A-Za-z]:", rel) else rel
                base = dict(artifact=f"NTFS $STANDARD_INFORMATION of {rel}", size=st.st_size,
                            user=user.name, **common)
                ev.add("fileCreated", us_from_unix(st.st_birthtime), 1, rel, vsn, **base)
                ev.add("fileModified", us_from_unix(st.st_mtime), 1, rel, vsn, **base)
                n += 1
    return n


DRIVE_TYPES = {2: "removable", 3: "fixed", 4: "network", 5: "CD-ROM"}


def _volumes_in_shortcuts(ev, common):
    """A shortcut stores the label and serial of the volume its target was on. Emit one
    volumeSeen row per (label, serial): the earliest shortcut that recorded it."""
    import json as _json
    first = {}
    for kind, t_us, _res, _obj, aux, prov in ev.rows():
        if kind != "lnkTarget":
            continue
        pv = _json.loads(prov)
        label = pv.get("volume_label")
        if label and (label, aux) not in first:      # rows() is sorted by time within a kind
            first[(label, aux)] = (t_us, pv)
    for (label, serial), (t_us, pv) in sorted(first.items()):
        ev.add("volumeSeen", t_us, 1, label, serial,
               artifact=f"volume block of shortcut: {pv.get('artifact', '')}",
               drive_type=DRIVE_TYPES.get(pv.get("drive_type"), str(pv.get("drive_type"))),
               time_meaning="when the shortcut's target was opened", **common)
    return len(first)


RECYCLE_INDEX = re.compile(r"^\$I[0-9A-Z]{6}(\.[^\\]*)?$")


def _recycle_bin(ev, t, common):
    """Recycle Bin index records ($I files), read from the file table itself.

    Emptying the Recycle Bin deletes the $I files, but each is small enough to live
    inside its file-table record, so the original path and the deletion time stay
    readable until that record is reused."""
    fs = t.fs.mounts["c:"]
    vsn = "%08X" % (fs.ntfs.serial & 0xFFFFFFFF)
    n = 0
    for rec in fs.ntfs.mft.segments():
        try:
            name = rec.filename
        except Exception:
            continue
        if not name or not RECYCLE_INDEX.match(name):
            continue
        try:
            data = rec.open().read(1100)
            version, size, filetime = struct.unpack_from("<QQQ", data, 0)
            if version == 1:
                raw = data[24:544]
            elif version == 2:
                raw = data[28:28 + 2 * struct.unpack_from("<I", data, 24)[0]]
            else:
                raise ValueError(f"unknown $I version {version}")
            original = raw.decode("utf-16-le").split("\x00")[0]
            if not re.match(r"^[A-Za-z]:\\", original):
                raise ValueError(f"no original path in {name}")
        except Exception as e:
            ev.problem(f"file table record {rec.segment} ({name})", e)
            continue
        in_use = bool(rec.header.Flags & 1)
        ev.add("fileDeleted", us_from_filetime(filetime), 1, original[2:], vsn,
               artifact=f"Recycle Bin index {name}, file table record {rec.segment}",
               original_drive=original[:2], size=size, index_record_in_use=in_use,
               note=("" if in_use else "the Recycle Bin was emptied: this index file is "
                     "deleted, and was read from its file table record"),
               time_meaning="deletion time stored in the Recycle Bin index", **common)
        n += 1
    return n


BURN_TEMP = re.compile(r"^(DAT|FIL|POST)\d{5}\.tmp$", re.I)
BURN_KEY = "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\CD Burning"


def _burn_traces(ev, t, common):
    """Traces Windows leaves when its built-in burner writes a disc (Rules.md, R12).

    Three independent sources: temporary files in the change journal, the cdrom
    driver's event 133 in the System log, and the user's CD Burning settings key."""
    n = 0
    # 1. change journal: the first creation of each DAT/FIL/POST#####.tmp file
    first = {}
    try:
        for r in t.usnjrnl():
            path = str(r.path or "").replace("/", "\\")
            name = path.rsplit("\\", 1)[-1]
            if BURN_TEMP.match(name) and "FILE_CREATE" in str(r.reason) and name not in first:
                first[name] = (us(r.ts), path, int(r.usn))
    except Exception as e:
        ev.problem("NTFS change journal", e)
    sessions = []
    for name, (t_us, path, usn) in sorted(first.items(), key=lambda kv: (kv[1][0], kv[1][2])):
        # a session opens with DAT files and ends with a FIL/POST pair
        closed = not sessions or any(not x[0].upper().startswith("DAT") for x in sessions[-1])
        if name.upper().startswith("DAT") and closed:
            sessions.append([])
        if sessions:
            sessions[-1].append((name, t_us, path, usn))
    for files in sessions:
        ev.add("cdBurn", files[0][1], 1, "temporary files " + ", ".join(f[0] for f in files),
               "NTFS change journal", artifact="C:\\$Extend\\$UsnJrnl:$J",
               folder=files[0][2].rsplit("\\", 1)[0], first_usn=files[0][3],
               time_meaning="creation of the first temporary file of the session", **common)
        n += 1
    # 2. System event log: cdrom driver event 133
    try:
        for r in t.evtx():
            d = r._asdict()
            if str(d.get("Provider_Name")) != "cdrom" or str(d.get("EventID")) != "133":
                continue
            ev.add("cdBurn", us(d["ts"]), 1, f"cdrom driver event 133 for {d.get('Data_0')}",
                   "System event log", artifact=str(d.get("source", "")).replace("/", "\\"),
                   event_record_id=str(d.get("EventRecordID")), channel=str(d.get("Channel")),
                   time_meaning="event time", **common)
            n += 1
    except Exception as e:
        ev.problem("System event log", e)
    # 3. the user's CD Burning settings, once the user has picked a burn method
    try:
        for key in t.registry.keys(BURN_KEY):
            values = {v.name: v.value for v in key.values()}
            if "DefaultToMastered" not in values:
                continue
            staging = ""
            for sub in key.subkeys():
                if sub.name == "StagingInfo":
                    for vol in sub.subkeys():
                        staging = str({v.name: v.value for v in vol.values()}.get("StagingPath", ""))
            m = re.match(r"^[A-Za-z]:\\Users\\([^\\]+)\\", staging)
            user = m.group(1) if m else "unknown"
            ev.add("cdBurn", us(key.timestamp), 1,
                   f"CD Burning settings of user {user} last changed "
                   f"(DefaultToMastered={values['DefaultToMastered']})",
                   "registry", artifact=BURN_KEY, staging_path=staging,
                   time_meaning="registry key last-write time", **common)
            n += 1
    except Exception as e:
        ev.problem(BURN_KEY, e)
    return n


MAPI_DISPLAY_TO, MAPI_SENDER_SMTP, MAPI_MESSAGE_ID = 0x0E04, 0x5D01, 0x1035


def _mapi_text(message, wanted: int) -> str:
    for record_set in message.record_sets:
        for entry in record_set.entries:
            if entry.entry_type == wanted and entry.data:
                if entry.value_type == 0x1F:
                    return entry.data.decode("utf-16-le", "replace").rstrip("\x00")
                return entry.data.decode("utf-8", "replace").rstrip("\x00")
    return ""


def _email(ev, t, common):
    """Messages in the user's Outlook mailbox file (OST/PST), read with libpff.

    Only messages the mailbox still lists are read. Messages purged from the mailbox
    (libpff calls them recoverable items) are not: the Python binding does not expose them."""
    files = []
    for user in t.fs.path("C:/Users").iterdir():
        box = user.joinpath("AppData/Local/Microsoft/Outlook")
        if box.exists():
            files += [(user.name, p) for p in sorted(box.iterdir(), key=str)
                      if p.suffix.lower() in (".ost", ".pst")]
    if not files:
        return 0
    try:
        import pypff
    except ImportError as e:
        ev.problem("mailbox files (install the 'extract' extra for libpff-python)", e)
        return 0
    n = 0

    def walk(folder, trail, user, source):
        nonlocal n
        here = trail + [folder.name] if folder.name else trail
        for i in range(folder.number_of_sub_messages):
            try:
                m = folder.get_sub_message(i)
                to, subject = _mapi_text(m, MAPI_DISPLAY_TO), (m.subject or "").strip()
                sent = m.get_client_submit_time_as_integer()
                if not to or not subject or not sent or "Sync Issues" in here:
                    continue                      # Outlook's own synchronization logs
                ev.add("emailSent", us_from_filetime(sent), 1_000_000, subject,
                       f"from {m.sender_name} to {to}",
                       artifact=f"{source} folder {' / '.join(here[-2:])}", mailbox_user=user,
                       folder=here[-1], sender_address=_mapi_text(m, MAPI_SENDER_SMTP),
                       message_id=_mapi_text(m, MAPI_MESSAGE_ID),
                       attachments=m.number_of_attachments,
                       time_meaning="client submit time stored in the message", **common)
                n += 1
            except Exception as e:
                ev.problem(f"{source} folder {folder.name} message {i}", e)
        for i in range(folder.number_of_sub_folders):
            walk(folder.get_sub_folder(i), here, user, source)

    for user, path in files:
        source = str(path).replace("/", "\\")
        try:
            box = pypff.file()
            box.open_file_object(io.BytesIO(path.open("rb").read()))
            walk(box.get_root_folder(), [], user, source)
        except Exception as e:
            ev.problem(source, e)
    return n


def _step(ev: Evidence, name: str, fn, default=0):
    """Run one part of the reader. An image that lacks the artifact (a PC no USB stick
    was ever plugged into has no USBSTOR key) is reported, and the reader goes on."""
    try:
        return fn()
    except Exception as e:
        ev.problem(name, e)
        return default


def extract_pc(ev: Evidence, path, tool: str):
    t = Target.open(path)
    common = dict(image=path.name, exhibit="PC", tool=tool)
    _step(ev, "USB devices in the registry", lambda: _usb(ev, t, common))
    _step(ev, "device install log", lambda: _setupapi(ev, t, common, str(t.timezone)))
    _step(ev, "volumes recorded in the registry", lambda: _volumes_seen(ev, t, common))
    parts = (("shortcuts", lambda: _lnk_files(ev, t, common)),
             ("jump list entries", lambda: _jumplists(ev, t, common)),
             ("volume labels in shortcuts", lambda: _volumes_in_shortcuts(ev, common)),
             ("searches", lambda: _searches(ev, t, common)),
             ("user files", lambda: _user_files(ev, t, common)),
             ("Recycle Bin records", lambda: _recycle_bin(ev, t, common)),
             ("CD-burn traces", lambda: _burn_traces(ev, t, common)),
             ("e-mails", lambda: _email(ev, t, common)))
    counts = {name: _step(ev, name, fn) for name, fn in parts}
    info = {"hostname": t.hostname, "os": str(t.version), "time_zone": str(t.timezone)}
    return info, [f"{path.name}: {info['hostname']}, {info['os']}, zone {info['time_zone']}; "
                  + ", ".join(f"{v} {k}" for k, v in counts.items())]
