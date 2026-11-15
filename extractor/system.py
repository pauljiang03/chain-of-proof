"""The Windows PC image: the machine, its accounts, and what ran on it.

Emits systemSetting, accountSeen, sessionEvent, programInstalled and programRun rows.
Every row is one record of one artifact; nothing is joined up or inferred. dissect is
imported inside functions, so the decoders in the first half of this file can be tested
with plain Python 3.9.

Copies of the same artifact (RegBack hives, non-current control sets) are read too, but
only rows that differ from what the live copy gave are kept.
"""
from __future__ import annotations

import codecs
import html
import io
import json
import re
import struct
from collections import namedtuple
from datetime import datetime, timedelta

from .store import EPOCH, us, us_from_filetime, us_from_unix

DAY_US = 86_400_000_000
NEVER = 0x7FFFFFFFFFFFFFFF
LOCAL_ACCOUNT = "windows local account"

# ---------------------------------------------------------------- pure decoders


def filetime_us(ft):
    """FILETIME -> UTC microseconds; None when unset, 'never', or before 1970."""
    if not ft or ft >= NEVER:
        return None
    t = us_from_filetime(ft)
    return t if t >= 0 else None


def iso(t_us):
    """UTC microseconds -> text for provenance."""
    if t_us is None:
        return None
    return (EPOCH + timedelta(microseconds=t_us)).strftime("%Y-%m-%d %H:%M:%S.%f") + "Z"


def systemtime(data, offset=0):
    """A 16-byte SYSTEMTIME as a naive datetime (it carries no zone); None when unset."""
    y, mo, _dow, d, h, mi, s, ms = struct.unpack_from("<8H", data, offset)
    if y == 0:
        return None
    return datetime(y, mo, d, h, mi, s, ms * 1000)


def local_us(naive, zone):
    """Wall-clock time in the named IANA zone -> UTC microseconds."""
    from zoneinfo import ZoneInfo
    return us(naive.replace(tzinfo=ZoneInfo(zone)))


def exe_name(path):
    """Last component of a path as recorded, without surrounding quotes."""
    return path.strip().strip('"').replace("/", "\\").rstrip("\\").rsplit("\\", 1)[-1]


def sid_text(data):
    """Binary SID -> S-1-5-21-..."""
    count = data[1]
    authority = int.from_bytes(data[2:8], "big")
    subs = struct.unpack_from("<%dI" % count, data, 8)
    return "S-%d-%d" % (data[0], authority) + "".join("-%d" % s for s in subs)


ACB = ((0x0001, "account disabled"), (0x0002, "home directory required"),
       (0x0004, "password not required"), (0x0008, "temporary duplicate account"),
       (0x0010, "normal user account"), (0x0020, "MNS logon account"),
       (0x0040, "interdomain trust account"), (0x0080, "workstation trust account"),
       (0x0100, "server trust account"), (0x0200, "password does not expire"),
       (0x0400, "account locked out"))


def acb_flags(value):
    return [name for bit, name in ACB if value & bit]


def parse_sam_f(data):
    """The fixed part of a SAM user record (value F)."""
    if len(data) < 0x44:
        raise ValueError("SAM F value is %d bytes, expected at least 68" % len(data))
    last_logon, _, pw_set, expires, last_failed = struct.unpack_from("<5Q", data, 8)
    rid, group, acb = struct.unpack_from("<3I", data, 0x30)
    failed, logons = struct.unpack_from("<2H", data, 0x40)
    return {"last_logon": filetime_us(last_logon), "password_last_set": filetime_us(pw_set),
            "account_expires": filetime_us(expires), "last_failed_logon": filetime_us(last_failed),
            "rid": rid, "primary_group": group, "flags": acb & 0xFFFF,
            "failed_logons": failed, "logon_count": logons}


def parse_sam_v(data):
    """The strings of a SAM user record (value V): offsets are relative to 0xCC."""
    def text(index):
        off, length = struct.unpack_from("<2I", data, 0x0C + 12 * index)
        return data[0xCC + off: 0xCC + off + length].decode("utf-16-le", "replace")
    if len(data) < 0xCC:
        raise ValueError("SAM V value is %d bytes, expected at least 204" % len(data))
    return {"name": text(0), "full_name": text(1), "comment": text(2), "user_comment": text(3),
            "home_directory": text(5), "logon_script": text(7), "profile_path": text(8)}


def parse_alias_c(data):
    """A SAM local group (value C): its name and the SIDs of its members."""
    name_off, name_len = struct.unpack_from("<2I", data, 0x10)
    mem_off, mem_len, count = struct.unpack_from("<3I", data, 0x28)
    name = data[0x34 + name_off: 0x34 + name_off + name_len].decode("utf-16-le", "replace")
    members, pos, end = [], 0x34 + mem_off, 0x34 + mem_off + mem_len
    for _ in range(count):
        if pos + 8 > end or pos + 8 > len(data):
            break
        size = 8 + 4 * data[pos + 1]
        members.append(sid_text(data[pos: pos + size]))
        pos += size
    return name, members


def parse_userassist(data):
    """One UserAssist counter. Windows 7+ records are 72 bytes, XP records 16."""
    if len(data) == 72:
        _session, runs, focus, focus_ms = struct.unpack_from("<4I", data, 0)
        return {"run_count": runs, "focus_count": focus, "focus_time_ms": focus_ms,
                "last_run": filetime_us(struct.unpack_from("<Q", data, 60)[0])}
    if len(data) == 16:
        _session, runs, ft = struct.unpack_from("<IIQ", data, 0)
        return {"run_count": max(runs - 5, 0), "focus_count": None, "focus_time_ms": None,
                "last_run": filetime_us(ft)}
    return None


def userassist_path(decoded):
    """Path part of a decoded UserAssist name; None for bookkeeping entries."""
    for prefix in ("UEME_RUNPATH:", "UEME_RUNPIDL:", "UEME_RUNCPL:"):
        if decoded.startswith(prefix):
            return decoded[len(prefix):]
    if decoded.startswith("UEME_"):
        return None
    return decoded


def scca_hash_vista(path):
    h = 314159
    for b in path.encode("utf-16-le"):
        h = (h * 37 + b) & 0xFFFFFFFF
    return h


def scca_hash_2008(path):
    """Prefetch path hash of Windows 7 / Server 2008 R2 and later."""
    p = path.encode("utf-16-le")
    h, i = 314159, 0
    while i + 8 < len(p):
        c = p[i + 1] * 37
        for k in (2, 3, 4, 5, 6):
            c = (c + p[i + k]) * 37
        c += p[i] * 442596621 + p[i + 7]
        h = (c - h * 803794207) & 0xFFFFFFFF
        i += 8
    while i < len(p):
        h = (37 * h + p[i]) & 0xFFFFFFFF
        i += 1
    return h


def scca_hash_xp(path):
    h = 0
    for b in path.encode("utf-16-le"):
        h = (h * 37 + b) & 0xFFFFFFFF
    h = (h * 314159269) & 0xFFFFFFFF
    if h > 0x80000000:
        h = 0x100000000 - h
    return (h % 1000000007) & 0xFFFFFFFF


def parse_prefetch(data):
    """Header of an uncompressed prefetch file: name, hash, run count, run times, file list."""
    if len(data) < 0x9C or data[4:8] != b"SCCA":
        raise ValueError("not a prefetch file (no SCCA signature)")
    version = struct.unpack_from("<I", data, 0)[0]
    name = data[16:76].decode("utf-16-le", "replace").split("\x00")[0]
    path_hash = struct.unpack_from("<I", data, 76)[0]
    strings_off, strings_size = struct.unpack_from("<2I", data, 0x64)
    if version == 17:
        times, count_at = [struct.unpack_from("<Q", data, 0x78)[0]], 0x90
    elif version == 23:
        times, count_at = [struct.unpack_from("<Q", data, 0x80)[0]], 0x98
    elif version in (26, 30, 31):
        times = list(struct.unpack_from("<8Q", data, 0x80))
        count_at = 0xC8 if struct.unpack_from("<I", data, 0x54)[0] == 0x128 else 0xD0
    else:
        raise ValueError("unknown prefetch version %d" % version)
    files = [s for s in data[strings_off: strings_off + strings_size]
             .decode("utf-16-le", "replace").split("\x00") if s]
    return {"version": version, "name": name, "hash": path_hash,
            "run_count": struct.unpack_from("<I", data, count_at)[0],
            "run_times": [t for t in (filetime_us(x) for x in times) if t is not None],
            "files": files}


def prefetch_path(pf):
    """The executable's own path from the prefetch file's file list.

    Returns (path, how). A candidate whose path hash equals the hash in the header is
    certain; a single name match is taken; anything else is left empty, not guessed."""
    name = pf["name"].upper()
    cands = []
    for f in pf["files"]:
        base = f.rsplit("\\", 1)[-1].upper()
        if (base == name or (len(name) == 29 and base.startswith(name))) and f not in cands:
            cands.append(f)
    hashes = (scca_hash_xp,) if pf["version"] == 17 else (scca_hash_2008, scca_hash_vista)
    for c in cands:
        if any(fn(c) == pf["hash"] for fn in hashes):
            return c, "path hash in the prefetch header matches this entry of its file list"
    if len(cands) == 1:
        return cands[0], "only entry with this file name in the prefetch file list"
    return "", "%d entries with this file name in the prefetch file list" % len(cands)


def parse_shimcache_nt61(data):
    """AppCompatCache of Windows 7 / Server 2008 R2 (magic 0xBADC0FEE), 32 or 64 bit."""
    if len(data) < 0x80 or struct.unpack_from("<I", data, 0)[0] != 0xBADC0FEE:
        raise ValueError("not a Windows 7 AppCompatCache value")
    count = struct.unpack_from("<I", data, 4)[0]
    wide = count == 0 or struct.unpack_from("<I", data, 0x84)[0] == 0   # padding = 64 bit
    size = 48 if wide else 32
    out = []
    for i in range(count):
        at = 0x80 + i * size
        if at + size > len(data):
            raise ValueError("AppCompatCache entry %d lies outside the value" % i)
        if wide:
            length, _max, _pad, off, ft, file_flags, flags = struct.unpack_from("<HHIQQII", data, at)
        else:
            length, _max, off, ft, file_flags, flags = struct.unpack_from("<HHIQII", data, at)
        out.append({"path": data[off: off + length].decode("utf-16-le", "replace"),
                    "modified": filetime_us(ft), "executed": bool(file_flags & 2),
                    "file_flags": file_flags, "shim_flags": flags})
    return out


def shimcache_entry(item):
    """Normalize a generic parser entry; the unset 1601 time is not an event."""
    raw = item[0]
    modified = _as_us(raw) if raw is not None else None
    return {"path": item[1], "modified": modified if modified is not None and modified >= 0 else None,
            "raw_modified": raw.isoformat() if isinstance(raw, datetime) else str(raw) if raw is not None else None,
            "executed": None, "file_flags": None, "shim_flags": None}


def parse_recentfilecache(data):
    """RecentFileCache.bcf: a 20-byte header, then length-prefixed UTF-16 paths."""
    if len(data) < 20 or struct.unpack_from("<I", data, 0)[0] != 0xFFEEFFFE:
        raise ValueError("not a RecentFileCache.bcf file")
    out, off = [], 20
    while off + 4 <= len(data):
        n = struct.unpack_from("<I", data, off)[0]
        out.append(data[off + 4: off + 4 + 2 * n].decode("utf-16-le", "replace"))
        off += 4 + 2 * n + 2
    return out


def parse_job(data):
    """A Task Scheduler 1.0 .job file: program, parameters, last run (local wall clock)."""
    if len(data) < 0x48:
        raise ValueError(".job file is %d bytes, expected at least 72" % len(data))
    off = struct.unpack_from("<H", data, 0x14)[0]
    strings = []
    for _ in range(2):
        n = struct.unpack_from("<H", data, off)[0]
        strings.append(data[off + 2: off + 2 + 2 * n].decode("utf-16-le", "replace").rstrip("\x00"))
        off += 2 + 2 * n
    return {"application": strings[0], "parameters": strings[1], "last_run": systemtime(data, 0x34)}


def parse_mbr(sector):
    """Primary partition entries of a master boot record."""
    if len(sector) < 512 or sector[510:512] != b"\x55\xaa":
        raise ValueError("sector 0 has no boot signature")
    out = []
    for i in range(4):
        e = sector[446 + 16 * i: 462 + 16 * i]
        if e[4] == 0:
            continue
        start, count = struct.unpack_from("<2I", e, 8)
        out.append({"number": i + 1, "type": e[4], "bootable": e[0] == 0x80,
                    "start": start, "sectors": count})
    return out


def parse_install_date(value):
    """InstallDate 'YYYYMMDD' (text or number) -> naive midnight; None if it is not one."""
    text = str(value).strip() if isinstance(value, (str, int)) else ""
    if not re.match(r"^\d{8}$", text):
        return None
    try:
        return datetime(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def task_commands(data):
    """<Command> elements of a Task Scheduler 2.0 task file (the programs it runs)."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = data.decode("utf-16", "replace")
    else:
        text = data.decode("utf-8-sig", "replace")
    return [html.unescape(m).strip() for m in re.findall(r"<Command>(.*?)</Command>", text, re.S)
            if m.strip()]


def mru_order(data):
    """MRUListEx -> value names, most recent first."""
    out = []
    for i in range(0, len(data) - 3, 4):
        n = struct.unpack_from("<I", data, i)[0]
        if n == 0xFFFFFFFF:
            break
        out.append(str(n))
    return out


def utf16z(data):
    """Leading NUL-terminated UTF-16 string of a binary value."""
    end = 0
    while end + 1 < len(data) and data[end:end + 2] != b"\x00\x00":
        end += 2
    return data[:end].decode("utf-16-le", "replace")


# ---------------------------------------------------------------- plumbing

Hive = namedtuple("Hive", "name hive path backup account sid")
ROOTS = {"SYSTEM": "HKLM\\SYSTEM", "SOFTWARE": "HKLM\\SOFTWARE", "SAM": "HKLM\\SAM",
         "SECURITY": "HKLM\\SECURITY", "DEFAULT": "HKU\\.DEFAULT"}
WELL_KNOWN = {"S-1-5-18": "SYSTEM", "S-1-5-19": "LOCAL SERVICE", "S-1-5-20": "NETWORK SERVICE"}


class _Out:
    """Adds the common provenance, and drops a row from a backup copy of an artifact
    when the live copy already gave the same (kind, time, obj, aux)."""

    def __init__(self, ev, common):
        self.ev, self.common, self.seen = ev, common, set()

    def add(self, kind, t, res, obj, aux="", _copy=False, **prov):
        key = (kind, t, obj, aux)
        if _copy and key in self.seen:
            return False
        self.seen.add(key)
        prov = {k: v for k, v in prov.items() if v is not None and v != "" and v != []}
        self.ev.add(kind, int(t), int(res), obj, aux, **prov, **self.common)
        return True


def _hives(ev, target):
    reg = target.registry
    try:
        reg.load_user_hives()
    except Exception as e:
        ev.problem("user registry hives", e)
    out = []
    for name, hive, path in reg.iterhives():
        p = str(path).replace("/", "\\")
        account = sid = None
        try:
            details = reg.get_user_details(hive.root())
            if details:
                account, sid = details.user.name, details.user.sid
        except Exception as e:
            ev.problem(p, e)
        out.append(Hive(name.upper(), hive, p, "\\regback\\" in p.lower(), account, sid))
    return sorted(out, key=lambda h: (h.backup, h.path))       # live copies first


def _open(ev, h, path):
    from dissect.target.exceptions import RegistryError
    try:
        return h.hive.key(path)
    except RegistryError:
        return None
    except Exception as e:
        ev.problem("%s: %s" % (h.path, path), e)
        return None


def _art(h, key_path, value=None):
    root = ROOTS.get(h.name) or "HKU\\" + h.name
    return "%s\\%s%s" % (root, key_path, " value %s" % value if value else "")


def _where(h):
    prov = {"hive": h.path}
    if h.backup:
        prov["copy"] = "RegBack backup of the hive"
    if h.account:
        prov["account"] = h.account
    return prov


def _vals(ev, h, key):
    out = {}
    for v in key.values():
        try:
            out[v.name] = v.value
        except Exception as e:
            ev.problem(_art(h, key.path, v.name), e)
    return out


def _subkeys(ev, h, key):
    try:
        return sorted(key.subkeys(), key=lambda k: k.name)
    except Exception as e:
        ev.problem(_art(h, key.path), e)
        return []


def _text(value):
    return value.strip("\x00").strip() if isinstance(value, str) else ""


def _control_sets(ev, h):
    """(current, all control sets with the current one first) of a SYSTEM hive."""
    current, sel = None, _open(ev, h, "Select")
    if sel is not None:
        cur = _vals(ev, h, sel).get("Current")
        if isinstance(cur, int):
            current = "ControlSet%03d" % cur
    names = [k.name for k in _subkeys(ev, h, h.hive.root()) if re.match(r"(?i)^ControlSet\d{3}$", k.name)]
    return current, sorted(names, key=lambda n: (n != current, n))


def _path(target, rel):
    for root in ("C:/", "sysvol/"):
        p = target.fs.path(root + rel)
        try:
            if p.exists():
                return p
        except Exception:
            continue
    return None


def _win(path):
    s = str(path).replace("/", "\\")
    return "C:" + s[6:] if s.lower().startswith("sysvol\\") else s


def _zone(ev, target):
    try:
        from zoneinfo import ZoneInfo
        zone = str(target.timezone)
        ZoneInfo(zone)
        return zone
    except Exception as e:
        ev.problem("time zone named by the registry (local-time artifacts were skipped)", e)
        return None


# ---------------------------------------------------------------- system settings


def _settings(out, ev, target, hives, zone, ctx):
    setting = "registry key last-write time"
    for h in hives:
        if h.backup:
            continue
        if h.name == "SOFTWARE":
            _registry_settings(out, ev, h, "Microsoft\\Windows Search",
                               ("DataDirectory", "DefaultDataDirectory", "SetupCompletedSuccessfully"), setting)
            path = "Microsoft\\Windows NT\\CurrentVersion"
            key = _open(ev, h, path)
            if key is None:
                continue
            v, t, art = _vals(ev, h, key), us(key.timestamp), _art(h, path)
            if _text(v.get("SystemRoot")):
                out.add("systemSetting", t, 1, "system root", _text(v["SystemRoot"]),
                        artifact=_art(h, path, "SystemRoot"), time_meaning=setting, **_where(h))
            product, sp = _text(v.get("ProductName")), _text(v.get("CSDVersion"))
            if product:
                out.add("systemSetting", t, 1, "operating system", (product + " " + sp).strip(),
                        artifact=art, values="ProductName, CSDVersion", edition=_text(v.get("EditionID")),
                        product_id=_text(v.get("ProductId")), time_meaning=setting, **_where(h))
            version, build = _text(v.get("CurrentVersion")), _text(v.get("CurrentBuildNumber"))
            if version:
                out.add("systemSetting", t, 1, "operating system version",
                        ".".join(x for x in (version, build) if x), artifact=art,
                        values="CurrentVersion, CurrentBuildNumber", build_lab=_text(v.get("BuildLabEx")),
                        time_meaning=setting, **_where(h))
            if _text(v.get("RegisteredOwner")):
                out.add("systemSetting", t, 1, "registered owner", _text(v["RegisteredOwner"]),
                        artifact=_art(h, path, "RegisteredOwner"),
                        registered_organization=_text(v.get("RegisteredOrganization")),
                        time_meaning=setting, **_where(h))
            if isinstance(v.get("InstallDate"), int) and v["InstallDate"] > 0:
                out.add("systemSetting", v["InstallDate"] * 1_000_000, 1_000_000,
                        "operating system installed", "", artifact=_art(h, path, "InstallDate"),
                        time_meaning="InstallDate value (seconds since 1970, UTC)", **_where(h))
        if h.name == "SYSTEM":
            current, sets = _control_sets(ev, h)
            cs = current or (sets[0] if sets else None)
            if cs:
                _system_hive_settings(out, ev, target, hives, h, cs, zone, setting)
    _partitions(out, ev, target, ctx)


def _registry_settings(out, ev, h, path, names, setting):
    """Preserve selected configuration values verbatim, without expanding paths."""
    key = _open(ev, h, path)
    if key is None:
        return
    values = _vals(ev, h, key)
    for name in names:
        value = values.get(name)
        if not isinstance(value, (str, int, list)) or isinstance(value, bool):
            continue
        if isinstance(value, list) and not all(isinstance(v, str) for v in value):
            continue
        identifier = _art(h, path, name)
        rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":")) if isinstance(value, list) else str(value)
        out.add("systemSetting", us(key.timestamp), 1, identifier, rendered,
                artifact=identifier, registry_value=value, registry_path=_art(h, path),
                registry_value_name=name, time_meaning=setting, **_where(h))


def _system_hive_settings(out, ev, target, hives, h, cs, zone, setting):
    _registry_settings(out, ev, h, cs + "\\Services\\WSearch",
                       ("Start", "DelayedAutoStart", "ImagePath"), setting)
    _registry_settings(out, ev, h, cs + "\\Control\\BackupRestore\\FilesNotToSnapshot",
                       ("OutlookOST",), setting)
    path = cs + "\\Control\\ComputerName\\ComputerName"
    key = _open(ev, h, path)
    if key is not None and _text(_vals(ev, h, key).get("ComputerName")):
        out.add("systemSetting", us(key.timestamp), 1, "computer name",
                _text(_vals(ev, h, key)["ComputerName"]), artifact=_art(h, path, "ComputerName"),
                time_meaning=setting, **_where(h))
    path = cs + "\\Services\\Tcpip\\Parameters"
    tcpip = _open(ev, h, path)
    if tcpip is not None and _text(_vals(ev, h, tcpip).get("Hostname")):
        out.add("systemSetting", us(tcpip.timestamp), 1, "computer name",
                _text(_vals(ev, h, tcpip)["Hostname"]), artifact=_art(h, tcpip.path, "Hostname"),
                note="TCP/IP host name", time_meaning=setting, **_where(h))
    path = cs + "\\Control\\TimeZoneInformation"
    key = _open(ev, h, path)
    if key is not None:
        v = _vals(ev, h, key)
        name = _text(v.get("TimeZoneKeyName")) or _text(v.get("StandardName"))

        if _text(v.get("TimeZoneKeyName")):
            for software in hives:
                if software.name == "SOFTWARE" and not software.backup:
                    _registry_settings(out, ev, software,
                                       "Microsoft\\Windows NT\\CurrentVersion\\Time Zones\\" + name,
                                       ("Display", "Std", "Dlt"), setting)

        def signed(x):
            return (x - (1 << 32) if x >= (1 << 31) else x) if isinstance(x, int) else None
        if name:
            out.add("systemSetting", us(key.timestamp), 1, "time zone", name, artifact=_art(h, path),
                    bias_minutes=signed(v.get("Bias")), active_bias_minutes=signed(v.get("ActiveTimeBias")),
                    daylight_bias_minutes=signed(v.get("DaylightBias")),
                    standard_name=_text(v.get("StandardName")), daylight_name=_text(v.get("DaylightName")),
                    iana_zone=zone, time_meaning=setting, **_where(h))
    path = cs + "\\Control\\Windows"
    key = _open(ev, h, path)
    if key is not None:
        raw = _vals(ev, h, key).get("ShutdownTime")
        t = filetime_us(struct.unpack("<Q", raw)[0]) if isinstance(raw, bytes) and len(raw) == 8 else None
        if t is not None:
            out.add("systemSetting", t, 1, "last shutdown", "", artifact=_art(h, path, "ShutdownTime"),
                    time_meaning="ShutdownTime value", **_where(h))
    _network(out, ev, hives, h, cs, setting)


def _network(out, ev, hives, h, cs, setting):
    names, cards = {}, {}
    net = _open(ev, h, cs + "\\Control\\Network\\{4D36E972-E325-11CE-BFC1-08002BE10318}")
    for sub in (_subkeys(ev, h, net) if net is not None else []):
        conn = _open(ev, h, sub.path + "\\Connection")
        if conn is not None:
            names[sub.name.upper()] = _text(_vals(ev, h, conn).get("Name"))
    for s in hives:
        if s.name == "SOFTWARE" and not s.backup:
            key = _open(ev, s, "Microsoft\\Windows NT\\CurrentVersion\\NetworkCards")
            for sub in (_subkeys(ev, s, key) if key is not None else []):
                v = _vals(ev, s, sub)
                cards[_text(v.get("ServiceName")).upper()] = _text(v.get("Description"))
    ifaces = _open(ev, h, cs + "\\Services\\Tcpip\\Parameters\\Interfaces")
    for sub in (_subkeys(ev, h, ifaces) if ifaces is not None else []):
        v = _vals(ev, h, sub)

        def many(*keys):
            found = []
            for k in keys:
                x = v.get(k)
                for item in (x if isinstance(x, list) else [x]):
                    if isinstance(item, str) and item.strip("\x00 ") not in ("", "0.0.0.0", "255.255.255.255"):
                        found.append(item.strip("\x00 "))
            return found

        def lease(k):
            return iso(v[k] * 1_000_000) if isinstance(v.get(k), int) and v[k] > 0 else None
        guid = sub.name.upper()
        prov = dict(artifact=_art(h, sub.path), adapter_guid=sub.name, adapter_name=names.get(guid),
                    adapter_description=cards.get(guid), dhcp_enabled=bool(v.get("EnableDHCP")),
                    dhcp_server=", ".join(many("DhcpServer")),
                    subnet_mask=", ".join(many("DhcpSubnetMask", "SubnetMask")),
                    default_gateway=", ".join(many("DhcpDefaultGateway", "DefaultGateway")),
                    name_server=", ".join(many("DhcpNameServer", "NameServer")),
                    dns_domain=", ".join(many("DhcpDomain", "Domain")),
                    lease_obtained=lease("LeaseObtainedTime"), lease_terminates=lease("LeaseTerminatesTime"),
                    lease_seconds=v.get("Lease") if isinstance(v.get("Lease"), int) else None,
                    time_meaning=setting, **_where(h))
        t = us(sub.timestamp)
        for ip in many("DhcpIPAddress", "IPAddress"):
            out.add("systemSetting", t, 1, "network address", ip, **prov)
        for ip in many("DhcpDefaultGateway", "DefaultGateway"):
            out.add("systemSetting", t, 1, "default gateway", ip, **prov)
        for ip in many("DhcpServer"):
            out.add("systemSetting", t, 1, "dhcp server", ip, **prov)


def _partitions(out, ev, target, ctx):
    filesystems = {}
    for vol in target.volumes:
        try:
            filesystems[vol.offset] = (getattr(vol.fs, "__type__", None) or "").upper()
        except Exception:
            continue
    for index, disk in enumerate(target.disks):
        try:
            disk.seek(0)
            sector = disk.read(512)
            signature = "%08X" % struct.unpack_from("<I", sector, 0x1B8)[0]
            for p in parse_mbr(sector):
                kind = filesystems.get(p["start"] * 512) or "type 0x%02X" % p["type"]
                out.add("systemSetting", ctx["examined_at"], 1, "disk partition",
                        "partition %d: %s, start sector %d, sectors %d"
                        % (p["number"], kind, p["start"], p["sectors"]),
                        artifact="partition table in sector 0 of disk %d, entry %d" % (index, p["number"]),
                        partition_type="0x%02X" % p["type"], bootable=p["bootable"],
                        disk_signature=signature, byte_offset=p["start"] * 512,
                        size_bytes=p["sectors"] * 512, note="512-byte sectors",
                        time_meaning="when the image was examined; a partition table records no time")
        except Exception as e:
            ev.problem("partition table of disk %d" % index, e)


# ---------------------------------------------------------------- accounts


def _accounts(out, ev, hives, sids):
    profiles = {}
    for h in hives:
        if h.name == "SOFTWARE" and not h.backup:
            key = _open(ev, h, "Microsoft\\Windows NT\\CurrentVersion\\ProfileList")
            for sub in (_subkeys(ev, h, key) if key is not None else []):
                profiles[sub.name] = _text(_vals(ev, h, sub).get("ProfileImagePath"))
    for h in hives:
        if h.name != "SAM":
            continue
        base = "SAM\\Domains\\Account"
        users = _open(ev, h, base + "\\Users")
        if users is None:
            continue
        machine = None
        try:
            raw = _vals(ev, h, _open(ev, h, base)).get("V")
            machine = sid_text(raw[-24:]) if isinstance(raw, bytes) and len(raw) >= 24 else None
        except Exception as e:
            ev.problem(_art(h, base, "V"), e)
        groups = {}
        aliases = _open(ev, h, "SAM\\Domains\\Builtin\\Aliases")
        for sub in (_subkeys(ev, h, aliases) if aliases is not None else []):
            raw = _vals(ev, h, sub).get("C")
            if not isinstance(raw, bytes):
                continue
            try:
                name, members = parse_alias_c(raw)
                for sid in members:
                    groups.setdefault(sid, []).append(name)
            except Exception as e:
                ev.problem(_art(h, sub.path, "C"), e)
        names = {}
        key = _open(ev, h, base + "\\Users\\Names")
        for sub in (_subkeys(ev, h, key) if key is not None else []):
            names[sub.name.lower()] = sub
        for sub in _subkeys(ev, h, users):
            if not re.match(r"^[0-9A-Fa-f]{8}$", sub.name):
                continue
            v = _vals(ev, h, sub)
            try:
                f, s = parse_sam_f(v["F"]), parse_sam_v(v["V"])
            except Exception as e:
                ev.problem(_art(h, sub.path), e)
                continue
            sid = "%s-%d" % (machine, f["rid"]) if machine else None
            if sid and not h.backup:
                sids[sid] = s["name"]
            hint = v.get("UserPasswordHint")
            name_key = names.get(s["name"].lower())
            if name_key is not None:
                t, art = us(name_key.timestamp), _art(h, name_key.path)
                meaning = ("last-write time of the account's SAM Names key, written when the "
                           "account is created (or renamed)")
            else:
                t, art = us(sub.timestamp), _art(h, sub.path)
                meaning = "last-write time of the account's SAM record; no creation time is recorded"
            out.add("accountSeen", t, 1, s["name"], LOCAL_ACCOUNT, _copy=h.backup, artifact=art,
                    record=_art(h, sub.path), rid=f["rid"], sid=sid, full_name=s["full_name"],
                    comment=s["comment"], last_logon=iso(f["last_logon"]), logon_count=f["logon_count"],
                    last_password_change=iso(f["password_last_set"]),
                    last_failed_logon=iso(f["last_failed_logon"]), failed_logons=f["failed_logons"],
                    account_expires=iso(f["account_expires"]) or "never",
                    account_flags=acb_flags(f["flags"]), groups=sorted(groups.get(sid, [])),
                    profile_path=profiles.get(sid),
                    password_hint=hint.decode("utf-16-le", "replace") if isinstance(hint, bytes) else None,
                    time_meaning=meaning, **_where(h))
            if f["last_logon"] is not None:
                out.add("sessionEvent", f["last_logon"], 1, "logon", s["name"], _copy=h.backup,
                        artifact=_art(h, sub.path, "F"), source="account database (SAM)",
                        logon_count=f["logon_count"], rid=f["rid"],
                        time_meaning="last logon time stored in the account's SAM record", **_where(h))


# ---------------------------------------------------------------- registry: sessions


def _registry_sessions(out, ev, hives):
    for h in hives:
        if h.name != "SYSTEM":
            continue
        for cs in _control_sets(ev, h)[1]:
            path = cs + "\\Control\\Windows"
            key = _open(ev, h, path)
            if key is None:
                continue
            raw = _vals(ev, h, key).get("ShutdownTime")
            t = filetime_us(struct.unpack("<Q", raw)[0]) if isinstance(raw, bytes) and len(raw) == 8 else None
            if t is not None:
                out.add("sessionEvent", t, 1, "shutdown", "", _copy=True,
                        artifact=_art(h, path, "ShutdownTime"), source="registry",
                        time_meaning="ShutdownTime value of this control set", **_where(h))


# ---------------------------------------------------------------- event logs

A, K, P = "microsoft-windows-security-auditing", "microsoft-windows-kernel-general", "microsoft-windows-kernel-power"
# (provider, event id) -> (what, where the account is, what the event says)
SESSION_EVENTS = {
    (A, 4624): ("logon", "TargetUserName", "an account was successfully logged on"),
    (A, 4634): ("logoff", "TargetUserName", "an account was logged off"),
    (A, 4647): ("logoff", "TargetUserName", "user initiated logoff"),
    (A, 4608): ("startup", None, "Windows is starting up"),
    (A, 4609): ("shutdown", None, "Windows is shutting down"),
    (A, 4616): ("time change", None, "the system time was changed"),
    ("microsoft-windows-eventlog", 1100): ("shutdown", None, "the event logging service has shut down"),
    ("eventlog", 6005): ("startup", None, "the Event Log service was started"),
    ("eventlog", 6006): ("shutdown", None, "the Event Log service was stopped"),
    ("eventlog", 6009): ("startup", None, "operating system version logged at boot"),
    (K, 12): ("startup", None, "the operating system started"),
    (K, 13): ("shutdown", None, "the operating system is shutting down"),
    (K, 1): ("time change", None, "the system time has changed"),
    (P, 109): ("shutdown", None, "the kernel power manager has initiated a shutdown transition"),
    (P, 42): ("sleep", None, "the system is entering sleep"),
    (P, 506): ("sleep", None, "the system is entering connected standby"),
    (P, 107): ("wake", None, "the system has resumed from sleep"),
    (P, 507): ("wake", None, "the system is exiting connected standby"),
    (P, 41): ("startup", None, "the system has rebooted without cleanly shutting down first"),
    ("microsoft-windows-power-troubleshooter", 1): ("wake", None, "the system has returned from a low power state"),
    ("user32", 1074): ("shutdown", None, "a process has initiated the restart or power off of the computer"),
    ("microsoft-windows-winlogon", 7001): ("logon", "sid:UserSid", "user logon notification"),
    ("microsoft-windows-winlogon", 7002): ("logoff", "sid:UserSid", "user logoff notification"),
    ("microsoft-windows-terminalservices-localsessionmanager", 21):
        ("logon", "EventXML_User", "session logon succeeded"),
    ("microsoft-windows-terminalservices-localsessionmanager", 23):
        ("logoff", "EventXML_User", "session logoff succeeded"),
    ("microsoft-windows-user profiles service", 1):
        ("logon", "sid:Security_UserID", "received user logon notification"),
    ("microsoft-windows-user profiles service", 3):
        ("logoff", "sid:Security_UserID", "received user logoff notification"),
}
PERFORMANCE = {100: ("startup", "BootStartTime", "boot performance record"),
               200: ("shutdown", "ShutdownStartTime", "shutdown performance record")}
NOT_DATA = {"hostname", "domain", "ts", "Provider_Name", "EventID", "Channel", "Computer", "source",
            "Correlation_ActivityID", "Correlation_RelatedActivityID", "EventID_Qualifiers",
            "EventRecordID", "Execution_ProcessID", "Execution_ThreadID", "Keywords", "Level",
            "Opcode", "Provider_Guid", "Task", "Version", "Provider_EventSourceName"}


def _as_us(value):
    if isinstance(value, datetime):
        return us(value if value.tzinfo else value.replace(tzinfo=EPOCH.tzinfo))
    dt = datetime.fromisoformat(str(value).strip())
    return us(dt if dt.tzinfo else dt.replace(tzinfo=EPOCH.tzinfo))


def _events(out, ev, target, sids):
    try:
        records = target.evtx()
    except Exception as e:
        ev.problem("event logs", e)
        return
    try:
        for r in records:
            d = r._asdict()
            where = "%s record %s" % (str(d.get("source", "")).replace("/", "\\"), d.get("EventRecordID"))
            try:
                _event(out, ev, d, where, sids)
            except Exception as e:
                ev.problem(where, e)
    except Exception as e:
        ev.problem("event logs (reading stopped early)", e)


def _event(out, ev, d, where, sids):
    try:
        eid = int(d.get("EventID"))
    except (TypeError, ValueError):
        return
    provider, channel, ts = str(d.get("Provider_Name") or ""), str(d.get("Channel") or ""), d.get("ts")
    if ts is None:
        return
    t, res = us(ts), (1 if ts.microsecond else 1_000_000)
    data = {k: str(v)[:300] for k, v in d.items()
            if not k.startswith("_") and k not in NOT_DATA and "xmlns" not in k and v is not None and str(v) != ""}
    base = dict(artifact=where, event_id=eid, provider=provider, channel=channel, data=data)
    low = provider.lower()

    def account(spec):
        if not spec:
            return ""
        sid = spec.startswith("sid:")
        value = str(d.get(spec[4:] if sid else spec) or "")
        return sids.get(value, value) if sid else value.rsplit("\\", 1)[-1]

    hit = SESSION_EVENTS.get((low, eid))
    if hit and not (low == "microsoft-windows-user profiles service" and channel == "Application"):
        what, spec, says = hit
        out.add("sessionEvent", t, res, what, account(spec), source="event log", event=says,
                time_meaning="time the event was logged", **base)
    elif low == "microsoft-windows-diagnostics-performance" and eid in PERFORMANCE:
        what, field, says = PERFORMANCE[eid]
        if d.get(field) is not None:
            out.add("sessionEvent", _as_us(d[field]), 1, what, "", source="event log", event=says,
                    time_meaning="%s field of the event (the event itself was logged %s)" % (field, iso(t)),
                    **base)
    elif low == "eventlog" and eid == 6008:
        ev.problem(where, NotImplementedError(
            "event 6008 (unexpected shutdown) gives the shutdown time as local-time text; not converted"))
    elif low == A and eid == 4720 and d.get("SamAccountName"):
        out.add("accountSeen", t, res, str(d["SamAccountName"]), LOCAL_ACCOUNT, event="a user account was created",
                sid=str(d.get("TargetSid") or ""), created_by=str(d.get("SubjectUserName") or ""),
                time_meaning="time the account-creation event was logged", **base)
    elif low == A and eid == 4688 and d.get("NewProcessName"):
        path = str(d["NewProcessName"])
        out.add("programRun", t, res, exe_name(path), path, source="Security event log: process creation",
                account=str(d.get("SubjectUserName") or ""), time_meaning="time the process was created", **base)
    elif low == "msiinstaller" and eid == 1033 and str(d.get("Data_3")) == "0" and d.get("Data_0"):
        version = str(d.get("Data_1") or "")
        out.add("programInstalled", t, res, str(d["Data_0"]), "" if version == "(NULL)" else version,
                source="Application event log: Windows Installer installed the product",
                publisher=str(d.get("Data_4") or ""), account=account("sid:Security_UserID"),
                time_meaning="time the Windows Installer logged the completed installation", **base)


# ---------------------------------------------------------------- installed programs

UNINSTALL = (("Microsoft\\Windows\\CurrentVersion\\Uninstall", "native"),
             ("Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall", "32-bit (Wow6432Node)"))


def _installed(out, ev, hives, zone):
    for h in hives:
        if h.name == "SOFTWARE":
            prefix, scope = "", "machine-wide"
        elif h.sid and not h.name.endswith("_CLASSES"):
            prefix, scope = "Software\\", "per user"
        else:
            continue
        seen = set()
        for base, view in UNINSTALL:
            key = _open(ev, h, prefix + base)
            for sub in (_subkeys(ev, h, key) if key is not None else []):
                seen.add(_program(out, ev, h, sub, zone, view, scope, "uninstall entry"))
        if h.name != "SOFTWARE":
            continue
        data = _open(ev, h, "Microsoft\\Windows\\CurrentVersion\\Installer\\UserData")
        for user in (_subkeys(ev, h, data) if data is not None else []):
            products = _open(ev, h, user.path + "\\Products")
            for prod in (_subkeys(ev, h, products) if products is not None else []):
                props = _open(ev, h, prod.path + "\\InstallProperties")
                if props is None:
                    continue
                v = _vals(ev, h, props)
                if (_text(v.get("DisplayName")), _text(v.get("DisplayVersion"))) in seen:
                    continue            # the same product already has an uninstall entry
                _program(out, ev, h, props, zone, "Windows Installer product data", scope,
                         "Windows Installer product record", installed_for=user.name)


def _program(out, ev, h, key, zone, view, scope, what, **extra):
    v = _vals(ev, h, key)
    name, version = _text(v.get("DisplayName")), _text(v.get("DisplayVersion"))
    prov = dict(artifact=_art(h, key.path), registry_view=view, scope=scope,
                publisher=_text(v.get("Publisher")), install_location=_text(v.get("InstallLocation")),
                install_date_value=str(v["InstallDate"]) if v.get("InstallDate") not in (None, "") else None,
                system_component=bool(v.get("SystemComponent")) or None,
                name_source=None if name else "key name; the entry has no DisplayName",
                **extra, **_where(h))
    shown = name or key.name
    out.add("programInstalled", us(key.timestamp), 1, shown, version, _copy=h.backup,
            time_meaning="last-write time of the %s" % what, **prov)
    day = parse_install_date(v.get("InstallDate"))
    if day is not None and zone:
        out.add("programInstalled", local_us(day, zone), DAY_US, shown, version, _copy=h.backup,
                time_meaning="InstallDate value: a date with no time of day",
                time_zone="local date, converted from %s" % zone, **prov)
    return name, version


# ---------------------------------------------------------------- programs run


def _prefetch(out, ev, target):
    folder = _path(target, "Windows/Prefetch")
    if folder is None:
        return
    for p in sorted(folder.iterdir(), key=lambda x: x.name):
        if not p.name.lower().endswith(".pf"):
            continue
        art = _win(p)
        try:
            data = p.open("rb").read()
            if data[:4] == b"MAM\x04":
                from dissect.util.compression import lzxpress_huffman
                data = lzxpress_huffman.decompress(io.BytesIO(data[8:]))
            pf = parse_prefetch(data)
            st = p.lstat()
            path, how = prefetch_path(pf)
            if not pf["run_times"]:
                raise ValueError("no run time in the prefetch header")
            for n, t in enumerate(pf["run_times"]):
                out.add("programRun", t, 1, pf["name"], path, artifact=art, source="prefetch",
                        run_count=pf["run_count"], prefetch_hash="%08X" % pf["hash"],
                        format_version=pf["version"], path_source=how,
                        prefetch_file_created=iso(us_from_unix(st.st_birthtime)),
                        prefetch_file_modified=iso(us_from_unix(st.st_mtime)),
                        time_meaning="last run time in the prefetch header" if n == 0
                        else "earlier run time %d in the prefetch header" % n)
        except Exception as e:
            ev.problem(art, e)


def _userassist(out, ev, hives):
    try:
        from dissect.target.helpers.shell_folder_ids import DESCRIPTIONS
    except Exception:
        DESCRIPTIONS = {}
    for h in hives:
        if not h.sid or h.name.endswith("_CLASSES"):
            continue
        root = _open(ev, h, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist")
        for guid in (_subkeys(ev, h, root) if root is not None else []):
            count = _open(ev, h, guid.path + "\\Count")
            if count is None:
                continue
            for name, raw in sorted(_vals(ev, h, count).items()):
                decoded = codecs.decode(name, "rot-13")
                path = userassist_path(decoded)
                if path is None or not isinstance(raw, bytes):
                    continue
                rec = parse_userassist(raw)
                if rec is None:
                    ev.problem(_art(h, count.path, name), ValueError("UserAssist record of %d bytes" % len(raw)))
                    continue
                if rec["last_run"] is None:
                    continue                    # counted focus only: no run time recorded
                m = re.match(r"^\{([0-9A-Fa-f-]{36})\}", path)
                out.add("programRun", rec["last_run"], 1, exe_name(path), path if "\\" in path else "",
                        _copy=h.backup, artifact=_art(h, count.path, name), source="UserAssist",
                        entry=decoded, run_count=rec["run_count"], focus_count=rec["focus_count"],
                        focus_time_ms=rec["focus_time_ms"], userassist_list=guid.name,
                        known_folder=DESCRIPTIONS.get(m.group(1).lower()) if m else None,
                        time_meaning="last run time stored in the UserAssist entry", **_where(h))


def _shimcache(out, ev, target, hives):
    for h in hives:
        if h.name != "SYSTEM":
            continue
        current, sets = _control_sets(ev, h)
        for cs in sets:
            path = cs + "\\Control\\Session Manager\\AppCompatCache"
            key = _open(ev, h, path)
            raw = _vals(ev, h, key).get("AppCompatCache") if key is not None else None
            if not isinstance(raw, bytes):
                continue
            art, copy = _art(h, path, "AppCompatCache"), h.backup or cs != current
            try:
                if struct.unpack_from("<I", raw, 0)[0] == 0xBADC0FEE:
                    entries = parse_shimcache_nt61(raw)
                else:
                    from dissect.target.plugins.os.windows.regf.shimcache import ShimCache
                    entries = []
                    for item in ShimCache(io.BytesIO(raw), str(target.ntversion), False):
                        if isinstance(item, Exception):
                            ev.problem(art, item)
                            continue
                        try:
                            entries.append(shimcache_entry(item))
                        except (ValueError, TypeError, OverflowError) as e:
                            ev.problem(art, e)
            except Exception as e:
                ev.problem(art, e)
                continue
            for n, e in enumerate(entries):
                shown = re.sub(r"^\\\?\?\\", "", e["path"])
                t, meaning = e["modified"], ("last-modified time of the file as stored in the "
                                             "compatibility cache; not a run time")
                if t is None:
                    t, meaning = us(key.timestamp), ("last-write time of the AppCompatCache key; "
                                                     "this entry stores no file time")
                out.add("programRun", t, 1, exe_name(shown), shown, _copy=copy,
                        artifact="%s entry %d" % (art, n), source="application compatibility cache",
                        path_recorded=e["path"], executed_flag=e["executed"], control_set=cs,
                        raw_modified_time=e.get("raw_modified"),
                        time_meaning=meaning, **_where(h))


def _recentfilecache(out, ev, target):
    p = _path(target, "Windows/AppCompat/Programs/RecentFileCache.bcf")
    if p is None:
        return
    art = _win(p)
    try:
        t = us_from_unix(p.lstat().st_mtime)
        for n, path in enumerate(parse_recentfilecache(p.open("rb").read())):
            out.add("programRun", t, 1, exe_name(path), path, artifact="%s entry %d" % (art, n),
                    source="RecentFileCache.bcf",
                    time_meaning="last-modified time of RecentFileCache.bcf; the cache keeps no time per program")
    except Exception as e:
        ev.problem(art, e)


USER_LISTS = (
    ("Local Settings\\Software\\Microsoft\\Windows\\Shell\\MuiCache", "MUICache", True),
    ("Software\\Microsoft\\Windows\\ShellNoRoam\\MUICache", "MUICache", False),
    ("Software\\Microsoft\\Windows NT\\CurrentVersion\\AppCompatFlags\\Compatibility Assistant\\Persisted",
     "Program Compatibility Assistant", False),
    ("Software\\Microsoft\\Windows NT\\CurrentVersion\\AppCompatFlags\\Compatibility Assistant\\Store",
     "Program Compatibility Assistant", False),
)
DIALOG_MRU = ("Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ComDlg32\\LastVisitedPidlMRU",
              "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ComDlg32\\LastVisitedMRU")


def _user_lists(out, ev, hives):
    """Per-user lists of programs that keep no time per program: the key's last-write
    time is the only time the artifact attaches, and the row says so."""
    for h in hives:
        if not h.sid:
            continue
        classes = h.name.endswith("_CLASSES")
        for path, source, in_classes in USER_LISTS:
            key = _open(ev, h, path) if in_classes == classes else None
            if key is None:
                continue
            for name in sorted(_vals(ev, h, key)):
                if "\\" not in name or name.startswith("@"):
                    continue                    # LangID and resource strings, not programs
                out.add("programRun", us(key.timestamp), 1, exe_name(name), name, _copy=h.backup,
                        artifact=_art(h, path, name), source=source,
                        time_meaning="last-write time of the registry key; the list keeps no time per program",
                        **_where(h))
        for path in (() if classes else DIALOG_MRU):
            key = _open(ev, h, path)
            if key is None:
                continue
            v = _vals(ev, h, key)
            order = mru_order(v["MRUListEx"]) if isinstance(v.get("MRUListEx"), bytes) else []
            for name, raw in sorted(v.items()):
                if name == "MRUListEx" or not isinstance(raw, bytes):
                    continue
                program = utf16z(raw)
                if not program:
                    continue
                out.add("programRun", us(key.timestamp), 1, exe_name(program), "", _copy=h.backup,
                        artifact=_art(h, path, name), source="open/save dialog history",
                        mru_position=order.index(name) + 1 if name in order else None,
                        time_meaning="last-write time of the registry key (set when the most recent "
                                     "entry, position 1, was written); the list keeps no time per program",
                        **_where(h))


def _jobs(out, ev, target, zone):
    folder = _path(target, "Windows/Tasks")
    if folder is None:
        return
    for p in sorted(folder.iterdir(), key=lambda x: x.name):
        if not p.name.lower().endswith(".job"):
            continue
        art = _win(p)
        try:
            job = parse_job(p.open("rb").read())
            if job["last_run"] is None or not job["application"]:
                continue
            if not zone:
                raise ValueError("local last-run time, and no usable time zone")
            out.add("programRun", local_us(job["last_run"], zone), 1000, exe_name(job["application"]),
                    job["application"], artifact=art, source="scheduled task file (.job)",
                    parameters=job["parameters"], time_meaning="last run time stored in the task file",
                    time_zone="local time, converted from %s" % zone)
        except Exception as e:
            ev.problem(art, e)


def _task_cache(out, ev, target, hives):
    """Task Scheduler 2.0: the registry keeps each task's last run time, the task file
    (named by the registry's Path value) names the program the task runs."""
    for h in hives:
        if h.name != "SOFTWARE":
            continue
        tasks = _open(ev, h, "Microsoft\\Windows NT\\CurrentVersion\\Schedule\\TaskCache\\Tasks")
        for sub in (_subkeys(ev, h, tasks) if tasks is not None else []):
            v = _vals(ev, h, sub)
            info, name = v.get("DynamicInfo"), _text(v.get("Path"))
            if not isinstance(info, bytes) or len(info) < 20 or not name:
                continue
            t = filetime_us(struct.unpack_from("<Q", info, 12)[0])
            if t is None:
                continue
            art = _art(h, sub.path, "DynamicInfo")
            try:
                xml = _path(target, "Windows/System32/Tasks" + name.replace("\\", "/"))
                if xml is None:
                    raise FileNotFoundError("task file for %s" % name)
                for command in task_commands(xml.open("rb").read()):
                    out.add("programRun", t, 1, exe_name(command), command.strip('"'), _copy=h.backup,
                            artifact=art, source="scheduled task (TaskCache)", task=name, task_file=_win(xml),
                            time_meaning="last run time of the scheduled task whose action runs this program",
                            **_where(h))
            except Exception as e:
                ev.problem("%s (%s)" % (art, name), e)


# ---------------------------------------------------------------- entry point


def extract(ev, target, ctx):
    out = _Out(ev, dict(ctx["common"]))
    zone = _zone(ev, target)
    try:
        hives = _hives(ev, target)
    except Exception as e:
        ev.problem("registry", e)
        hives = []
    sids = dict(WELL_KNOWN)
    steps = (
        ("system settings", lambda: _settings(out, ev, target, hives, zone, ctx)),
        ("accounts", lambda: _accounts(out, ev, hives, sids)),
        ("event logs", lambda: _events(out, ev, target, sids)),
        ("shutdown times in the registry", lambda: _registry_sessions(out, ev, hives)),
        ("installed programs", lambda: _installed(out, ev, hives, zone)),
        ("prefetch", lambda: _prefetch(out, ev, target)),
        ("UserAssist", lambda: _userassist(out, ev, hives)),
        ("application compatibility cache", lambda: _shimcache(out, ev, target, hives)),
        ("RecentFileCache.bcf", lambda: _recentfilecache(out, ev, target)),
        ("per-user program lists", lambda: _user_lists(out, ev, hives)),
        ("scheduled task files", lambda: _jobs(out, ev, target, zone)),
        ("scheduled task cache", lambda: _task_cache(out, ev, target, hives)),
    )
    for name, step in steps:
        try:
            step()
        except Exception as e:
            ev.problem(name, e)
