"""The Windows PC image: USB devices, volumes the registry recorded, shortcuts,
jump lists, web searches and the user's files."""
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


def extract_pc(ev: Evidence, path, tool: str):
    t = Target.open(path)
    common = dict(image=path.name, exhibit="PC", tool=tool)
    _usb(ev, t, common)
    _setupapi(ev, t, common, str(t.timezone))
    _volumes_seen(ev, t, common)
    counts = {"shortcuts": _lnk_files(ev, t, common), "jump list entries": _jumplists(ev, t, common),
              "searches": _searches(ev, t, common), "user files": _user_files(ev, t, common)}
    info = {"hostname": t.hostname, "os": str(t.version), "time_zone": str(t.timezone)}
    return info, [f"{path.name}: {info['hostname']}, {info['os']}, zone {info['time_zone']}; "
                  + ", ".join(f"{v} {k}" for k, v in counts.items())]
