"""The Windows PC: settings, accounts, sessions, installed programs and programs run."""
from __future__ import annotations

import codecs
import hashlib
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
        start, end = 0xCC + off, 0xCC + off + length
        if length % 2 or start > len(data) or end > len(data):
            raise ValueError("SAM V string offset or length is outside the record")
        return data[start:end].decode("utf-16-le")
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
        times_at, count_at = 0x78, 0x90
        times = [struct.unpack_from("<Q", data, times_at)[0]]
    elif version == 23:
        times_at, count_at = 0x80, 0x98
        times = [struct.unpack_from("<Q", data, times_at)[0]]
    elif version in (26, 30, 31):
        times_at = 0x80
        times = list(struct.unpack_from("<8Q", data, times_at))
        count_at = 0xC8 if struct.unpack_from("<I", data, 0x54)[0] == 0x128 else 0xD0
    else:
        raise ValueError("unknown prefetch version %d" % version)
    files = [s for s in data[strings_off: strings_off + strings_size]
             .decode("utf-16-le", "replace").split("\x00") if s]
    time_entries = [{"time_us": t, "raw_filetime": raw, "slot": slot, "byte_offset": times_at + slot * 8}
                    for slot, raw in enumerate(times) if (t := filetime_us(raw)) is not None]
    return {"version": version, "name": name, "hash": path_hash,
            "run_count": struct.unpack_from("<I", data, count_at)[0],
            "run_count_byte_offset": count_at,
            "run_times": [entry['time_us'] for entry in time_entries], "run_time_entries": time_entries,
            "files": files}


def prefetch_path(pf):
    """Executable path from the prefetch file list -> (path, how): hash match, single name match, or empty."""
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


Hive = namedtuple("Hive", "name hive path backup account sid")
ROOTS = {"SYSTEM": "HKLM\\SYSTEM", "SOFTWARE": "HKLM\\SOFTWARE", "SAM": "HKLM\\SAM",
         "SECURITY": "HKLM\\SECURITY", "DEFAULT": "HKU\\.DEFAULT"}
WELL_KNOWN = {"S-1-5-18": "SYSTEM", "S-1-5-19": "LOCAL SERVICE", "S-1-5-20": "NETWORK SERVICE"}


class _Out:
    """Collects rows; deduplicates only within one source scope, so backup copies stay visible."""

    def __init__(self, ev, common, examined_at=None):
        self.ev, self.common, self.seen = ev, common, set()
        self.examined_at = examined_at

    def add(self, kind, t, res, obj, aux="", _copy=False, **prov):
        from .source_scope import merge_scope, subject_scope
        prov = merge_scope(self.common, prov)
        key = (*subject_scope(prov), prov.get('hive'), prov.get('control_set'), kind, t, obj, aux)
        if _copy and key in self.seen:
            return False
        self.seen.add(key)
        prov = {k: v for k, v in prov.items() if v is not None and v != "" and v != []}
        self.ev.add(kind, int(t), int(res), obj, aux, **prov)
        return True


def _execution_attributes(out, program, path, recorded_at, source_kind, artifact, entry, **details):
    """Typed execution attributes; `t` is the examination time, the source time a separate value."""
    from .source_scope import merge_scope, subject_scope
    provenance = merge_scope(out.common, dict(details, artifact=artifact, parser='extractor.system',
                      execution_source=source_kind, source_entry=entry, recorded_time_us=recorded_at,
                      limitation='observation of a reviewed execution artifact; not proof of a physical user, '
                                 'actual code execution, or source authenticity'))
    if (type(out.examined_at) is not int or out.examined_at <= 0
            or any(not isinstance(provenance.get(key), str) or not provenance[key].strip() for key in ('image', 'exhibit'))
            or not isinstance(artifact, str) or not artifact.strip() or not entry
            or type(recorded_at) is not int or recorded_at < 0):
        return
    try:
        # The source's own time, not the examination time.
        recorded_iso = (EPOCH + timedelta(microseconds=recorded_at)).isoformat(timespec='microseconds').replace('+00:00', 'Z')
    except (OverflowError, ValueError) as error:
        out.ev.problem(artifact + ' source timestamp', error)
        return
    from .attributes import emit_attribute
    scope = subject_scope(provenance) + [source_kind, artifact, entry, recorded_at]
    subject = json.dumps(scope, sort_keys=True, ensure_ascii=True, separators=(',', ':'))
    for role, value in (('app.execution.program', program), ('app.execution.path', path)):
        if isinstance(value, str) and value:
            emit_attribute(out.ev, subject, role, value, out.examined_at, **provenance)
    source_label = {'Prefetch header': 'Prefetch', 'UserAssist executable run path': 'UserAssist',
                    'Security process-creation event': 'Security process creation'}.get(source_kind)
    if source_label is None or not any(isinstance(v, str) and v for v in (program, path)):
        return
    # Labels describe source fields; they do not certify that an event happened.
    metadata = [
        ('recorded_time', recorded_iso, dict(details.get('recorded_time_locator') or {},
                                            field='recorded source timestamp',
                                            retained_resolution_us=details.get('recorded_time_resolution_us'))),
        ('source_type', source_label, {'field': 'reviewed artifact format', 'derivation': source_kind}),
        ('time_meaning', 'execution', {'field': 'timestamp interpretation',
                                     'derivation': details.get('recorded_time_meaning'),
                                     'limitation': 'artifact timestamp classification; not independent proof of execution'}),
    ]
    raw_count = details.get('raw_run_count')
    if source_label in ('Prefetch', 'UserAssist') and type(raw_count) is int and 0 <= raw_count <= 0xffffffff:
        locator = dict(details.get('run_count_locator') or {}, field='literal source run-counter DWORD')
        metadata.append(('raw_run_count', raw_count, locator))
        offset = 5 if source_label == 'UserAssist' and details.get('userassist_version') == 3 else 0
        if raw_count >= offset:
            metadata.append(('run_count', raw_count - offset,
                             dict(locator, field='format-interpreted source run counter',
                                  derivation='raw counter minus 5' if offset else 'literal counter, no adjustment',
                                  raw_value=raw_count, adjustment=offset)))
        else:
            out.ev.problem(artifact + ' run counter', ValueError(
                'UserAssist version 3 raw counter is below 5; interpreted count was not emitted'))
    for name, value, locator in metadata:
        # Keep the identity locator apart; its byte offset is not this field's location.
        field_prov = dict(provenance)
        identity_fields = ('source_field', 'source_value', 'byte_offset', 'byte_length', 'raw_value_hex', 'encoding')
        identity = {key: field_prov.pop(key) for key in identity_fields if key in field_prov}
        field_prov.update(execution_identity_locator=identity, attribute_value_source=locator,
                          source_field=locator['field'])
        emit_attribute(out.ev, subject, 'app.execution.' + name, value, out.examined_at, **field_prov)


def _explicit_execution_path(value, allow_device=False):
    """Literal .exe paths only; never expand a GUID, environment, or command."""
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(ord(char) < 32 for char in value)
            or any(char in value for char in ('"', '{', '}', '%', '/', '<', '>', '|', '?', '*'))
            or not value.lower().endswith('.exe')):
        return None
    drive = re.match(r'^[A-Za-z]:\\', value)
    device = allow_device and value.lower().startswith('\\device\\')
    if not drive and not device:
        return None
    remainder = value[3:] if drive else value[len('\\Device\\'):]
    if ':' in remainder or any(part in ('', '.', '..') for part in remainder.split('\\')):
        return None
    return value


def _userassist_execution_path(decoded, version, list_id, raw_length):
    # Executable lists only: version 3 with 16-byte records or version 5 with 72-byte records.
    # Format: https://www.magnetforensics.com/blog/artifact-profile-userassist/
    # dissect.regf returns REG_DWORD values as int subclasses; bools are rejected.
    if not isinstance(version, int) or isinstance(version, bool):
        return None
    if (version == 3 and raw_length == 16
            and list_id.casefold() == '{75048700-ef1f-11d0-9888-006097deacf9}'
            and decoded.startswith('UEME_RUNPATH:')):
        decoded = decoded[len('UEME_RUNPATH:'):]
    elif not (version == 5 and raw_length == 72
              and list_id.casefold() == '{cebff5cd-ace2-4f4f-9178-9926f41749ea}'
              and not decoded.startswith('UEME_')):
        return None
    return _explicit_execution_path(decoded)


def _prefetch_execution_name(data):
    """Executable name from the prefetch header only, never from the file list."""
    raw = data[16:76]
    end = next((i for i in range(0, len(raw), 2) if raw[i:i + 2] == b'\0\0'), len(raw))
    try:
        name = raw[:end].decode('utf-16-le')
    except UnicodeDecodeError:
        return None
    if not name or any(ord(char) < 32 for char in name) or '\\' in name or '/' in name:
        return None
    return name, raw[:end].hex(), end


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


def _where(h, control_set=None, current_control_set=None):
    """Variant of a registry copy: RegBack is a backup; only the Select/Current control set is primary."""
    path = str(h.path) if h.path is not None else ""
    backup = getattr(h, "backup", False) or "\\regback\\" in path.replace("/", "\\").casefold()
    prov = {"hive": path, "source_variant": "primary" if path.strip() else "unknown"}
    if control_set is not None:
        prov["control_set"] = control_set
        prov["current_control_set"] = current_control_set
        if not current_control_set:
            prov["source_variant"] = "unknown"
        elif control_set.casefold() != current_control_set.casefold():
            prov["source_variant"] = "noncurrent-control-set:" + control_set
    if backup:
        prov["source_variant"] = "registry-backup:" + path if path.strip() else "unknown"
        prov["copy"] = "RegBack backup of the hive"
    if getattr(h, "account", None):
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
        try:
            selectors = [v for v in sel.values()
                         if isinstance(v.name, str) and v.name.casefold() == 'current']
            if len(selectors) != 1:
                raise ValueError('Select\\Current missing or ambiguous')
            selector = selectors[0]
            cur = selector.value
            if (selector.type != 4 or not isinstance(cur, int) or isinstance(cur, bool)
                    or not 0 < cur <= 999):
                raise ValueError('Select\\Current must be a valid native REG_DWORD control-set number')
            current = "ControlSet%03d" % cur
        except Exception as error:
            ev.problem(_art(h, 'Select', 'Current'), error)
    names = [k.name for k in _subkeys(ev, h, h.hive.root()) if re.match(r"(?i)^ControlSet\d{3}$", k.name)]
    # Invalid/dangling Select values must not make a fallback look primary.
    current = next((name for name in names if current and name.casefold() == current.casefold()), None)
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
                _system_hive_settings(out, ev, target, hives, h, cs, zone, setting,
                                      current_control_set=current)
    _partitions(out, ev, target, ctx)


def _registry_settings(out, ev, h, path, names, setting, current_control_set=None):
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
        control_set = path.split("\\", 1)[0] if h.name == "SYSTEM" and re.match(r"(?i)^ControlSet\d{3}(?:\\|$)", path) else None
        out.add("systemSetting", us(key.timestamp), 1, identifier, rendered,
                artifact=identifier, registry_value=value, registry_path=_art(h, path),
                registry_value_name=name, time_meaning=setting,
                **_where(h, control_set, current_control_set))


def _system_hive_settings(out, ev, target, hives, h, cs, zone, setting, current_control_set=None):
    where = _where(h, cs, current_control_set)
    _registry_settings(out, ev, h, cs + "\\Services\\WSearch",
                       ("Start", "DelayedAutoStart", "ImagePath"), setting, current_control_set)
    _registry_settings(out, ev, h, cs + "\\Control\\BackupRestore\\FilesNotToSnapshot",
                       ("OutlookOST",), setting, current_control_set)
    path = cs + "\\Control\\ComputerName\\ComputerName"
    key = _open(ev, h, path)
    if key is not None and _text(_vals(ev, h, key).get("ComputerName")):
        out.add("systemSetting", us(key.timestamp), 1, "computer name",
                _text(_vals(ev, h, key)["ComputerName"]), artifact=_art(h, path, "ComputerName"),
                time_meaning=setting, **where)
    path = cs + "\\Services\\Tcpip\\Parameters"
    tcpip = _open(ev, h, path)
    if tcpip is not None and _text(_vals(ev, h, tcpip).get("Hostname")):
        out.add("systemSetting", us(tcpip.timestamp), 1, "computer name",
                _text(_vals(ev, h, tcpip)["Hostname"]), artifact=_art(h, tcpip.path, "Hostname"),
                note="TCP/IP host name", time_meaning=setting, **where)
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
                    iana_zone=zone, time_meaning=setting, **where)
    path = cs + "\\Control\\Windows"
    key = _open(ev, h, path)
    if key is not None:
        raw = _vals(ev, h, key).get("ShutdownTime")
        t = filetime_us(struct.unpack("<Q", raw)[0]) if isinstance(raw, bytes) and len(raw) == 8 else None
        if t is not None:
            out.add("systemSetting", t, 1, "last shutdown", "", artifact=_art(h, path, "ShutdownTime"),
                    time_meaning="ShutdownTime value", **where)
    _network(out, ev, hives, h, cs, setting, current_control_set)


def _network(out, ev, hives, h, cs, setting, current_control_set=None):
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
                    time_meaning=setting, **_where(h, cs, current_control_set))
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


def _registry_sessions(out, ev, hives):
    for h in hives:
        if h.name != "SYSTEM":
            continue
        current, sets = _control_sets(ev, h)
        for cs in sets:
            path = cs + "\\Control\\Windows"
            key = _open(ev, h, path)
            if key is None:
                continue
            raw = _vals(ev, h, key).get("ShutdownTime")
            t = filetime_us(struct.unpack("<Q", raw)[0]) if isinstance(raw, bytes) and len(raw) == 8 else None
            if t is not None:
                out.add("sessionEvent", t, 1, "shutdown", "", _copy=True,
                        artifact=_art(h, path, "ShutdownTime"), source="registry",
                        time_meaning="ShutdownTime value of this control set", **_where(h, cs, current))


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
    if hasattr(target, "has_function") and not target.has_function("evtx"):
        from .legacy_events import extract_sessions
        extract_sessions(out, ev, target)
        return
    try:
        records = target.evtx()
    except Exception as e:
        ev.problem("event logs", e)
        return
    try:
        for ordinal, r in enumerate(records, 1):
            d = r._asdict()
            where = "%s record %s" % (str(d.get("source", "")).replace("/", "\\"), d.get("EventRecordID"))
            try:
                _event(out, ev, d, where, sids, _parser_record_id_text=True, _parser_row_ordinal=ordinal)
            except Exception as e:
                ev.problem(where, e)
    except Exception as e:
        ev.problem("event logs (reading stopped early)", e)


def _event(out, ev, d, where, sids, *, _parser_record_id_text=False, _parser_row_ordinal=None):
    # Dissect's ts is EVTX TimeCreated; EventRecordID is a string.
    from .event_attributes import emit_event_attributes
    emit_event_attributes(out, ev, d, parser_record_id_text=_parser_record_id_text,
                          parser_row_ordinal=_parser_row_ordinal)
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
        literal = _explicit_execution_path(d["NewProcessName"], allow_device=True)
        record_id, source_path = d.get('EventRecordID'), str(d.get('source') or '')
        if (literal and channel.casefold() == 'security' and source_path.strip()
                and re.fullmatch(r'[1-9][0-9]*', str(record_id or ''))):
            _execution_attributes(out, literal.rsplit('\\', 1)[-1], literal, t,
                                  'Security process-creation event', where,
                                  {'event_record_id': str(record_id), 'event_id': eid, 'provider': provider},
                                  source_path=source_path, source_field='NewProcessName', source_value=literal,
                                  program_derivation='last path component of literal NewProcessName',
                                  recorded_time_meaning='event timestamp of Security process creation',
                                  recorded_time_locator={'field': 'event TimeCreated (parser ts)',
                                                         'raw_value': ts.isoformat(),
                                                         'conversion': 'UTC datetime to integer microseconds'},
                                  recorded_time_resolution_us=res, account=str(d.get('SubjectUserName') or ''),
                                  event_id=eid, provider=provider, channel=channel)
    elif low == "msiinstaller" and eid == 1033 and str(d.get("Data_3")) == "0" and d.get("Data_0"):
        version = str(d.get("Data_1") or "")
        out.add("programInstalled", t, res, str(d["Data_0"]), "" if version == "(NULL)" else version,
                source="Application event log: Windows Installer installed the product",
                publisher=str(d.get("Data_4") or ""), account=account("sid:Security_UserID"),
                time_meaning="time the Windows Installer logged the completed installation", **base)


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
            source_sha256 = hashlib.sha256(data).hexdigest()
            compressed = data[:4] == b"MAM\x04"
            if data[:4] == b"MAM\x04":
                from dissect.util.compression import lzxpress_huffman
                data = lzxpress_huffman.decompress(io.BytesIO(data[8:]))
            pf = parse_prefetch(data)
            literal_name = _prefetch_execution_name(data)
            st = p.lstat()
            path, how = prefetch_path(pf)
            if not pf["run_times"]:
                raise ValueError("no run time in the prefetch header")
            for n, time_entry in enumerate(pf['run_time_entries']):
                t = time_entry['time_us']
                out.add("programRun", t, 1, pf["name"], path, artifact=art, source="prefetch",
                        run_count=pf["run_count"], prefetch_hash="%08X" % pf["hash"],
                        format_version=pf["version"], path_source=how,
                        prefetch_file_created=iso(us_from_unix(st.st_birthtime)),
                        prefetch_file_modified=iso(us_from_unix(st.st_mtime)),
                        time_meaning="last run time in the prefetch header" if n == 0
                        else "earlier run time %d in the prefetch header" % n)
                if literal_name:
                    name, raw_hex, length = literal_name
                    _execution_attributes(out, name, None, t, 'Prefetch header', art,
                                          {'run_index': n, 'source_sha256': source_sha256},
                                          source_path=art, source_field='prefetch header executable name',
                                          source_value=name, source_sha256=source_sha256,
                                          byte_offset=16, byte_length=length, raw_value_hex=raw_hex,
                                          byte_offset_basis='decompressed Prefetch bytes' if compressed else 'source file bytes',
                                          encoding='utf-16-le', header_name_may_be_truncated=len(name) >= 29,
                                          format_version=pf['version'], run_count=pf['run_count'],
                                          raw_run_count=pf['run_count'], run_count_adjustment=0,
                                          run_count_interpretation='literal Prefetch counter; no adjustment',
                                          run_count_locator={'field': 'Prefetch run-counter DWORD',
                                                             'byte_offset': pf['run_count_byte_offset'], 'byte_length': 4,
                                                             'byte_offset_basis': 'decompressed Prefetch bytes' if compressed else 'source file bytes',
                                                             'encoding': 'little-endian uint32', 'raw_value': pf['run_count']},
                                          recorded_time_locator={'field': 'Prefetch run-time FILETIME',
                                                                 'byte_offset': time_entry['byte_offset'], 'byte_length': 8,
                                                                 'byte_offset_basis': 'decompressed Prefetch bytes' if compressed else 'source file bytes',
                                                                 'encoding': 'little-endian FILETIME',
                                                                 'raw_value': time_entry['raw_filetime'], 'slot': time_entry['slot'],
                                                                 'conversion': '(FILETIME - Unix epoch FILETIME) // 10; retained microseconds'},
                                          recorded_time_meaning='run timestamp stored in the Prefetch header',
                                          recorded_time_resolution_us=1, run_index=n)
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
            userassist_version = _vals(ev, h, guid).get('Version')
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
                raw_count = struct.unpack_from('<I', raw, 4)[0]
                m = re.match(r"^\{([0-9A-Fa-f-]{36})\}", path)
                out.add("programRun", rec["last_run"], 1, exe_name(path), path if "\\" in path else "",
                        _copy=h.backup, artifact=_art(h, count.path, name), source="UserAssist",
                        entry=decoded, run_count=rec["run_count"], focus_count=rec["focus_count"],
                        raw_run_count=raw_count,
                        run_count_interpretation='legacy display max(raw counter - 5, 0)' if len(raw) == 16
                                                else 'literal counter; no adjustment',
                        focus_time_ms=rec["focus_time_ms"], userassist_list=guid.name,
                        known_folder=DESCRIPTIONS.get(m.group(1).lower()) if m else None,
                        time_meaning="last run time stored in the UserAssist entry", **_where(h))
                literal_path = _userassist_execution_path(decoded, userassist_version, guid.name, len(raw))
                if literal_path and isinstance(h.path, str) and h.path.strip():
                    offset = 5 if userassist_version == 3 else 0
                    count_valid = raw_count >= offset
                    time_at = 8 if userassist_version == 3 else 60
                    _execution_attributes(out, literal_path.rsplit('\\', 1)[-1], literal_path,
                                          rec['last_run'], 'UserAssist executable run path',
                                          _art(h, count.path, name),
                                          {'hive': h.path, 'registry_key': count.path, 'registry_value': name,
                                           'raw_value_sha256': hashlib.sha256(raw).hexdigest()},
                                          source_field='ROT13-encoded UserAssist value name', source_value=name,
                                          decoded_value_name=decoded, raw_value_hex=raw.hex(),
                                          program_derivation='last path component of the explicit executable run path',
                                          run_count=raw_count - offset if count_valid else None,
                                          raw_run_count=raw_count, run_count_adjustment=offset,
                                          run_count_interpretation='raw counter minus 5' if offset else 'literal counter; no adjustment',
                                          run_count_status='interpreted' if count_valid else 'raw counter below interpretation offset; interpreted count unavailable',
                                          run_count_locator={'field': 'UserAssist run-counter DWORD',
                                                             'byte_offset': 4, 'byte_length': 4,
                                                             'byte_offset_basis': 'registry value bytes',
                                                             'encoding': 'little-endian uint32', 'raw_value': raw_count},
                                          recorded_time_locator={'field': 'UserAssist last-run FILETIME',
                                                                 'byte_offset': time_at, 'byte_length': 8,
                                                                 'byte_offset_basis': 'registry value bytes',
                                                                 'encoding': 'little-endian FILETIME',
                                                                 'raw_value': struct.unpack_from('<Q', raw, time_at)[0],
                                                                 'conversion': '(FILETIME - Unix epoch FILETIME) // 10; retained microseconds'},
                                          userassist_list=guid.name,
                                          userassist_version=userassist_version, userassist_record_bytes=len(raw),
                                          recorded_time_meaning='last run timestamp stored in the UserAssist entry',
                                          recorded_time_resolution_us=1, **_where(h))


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
                        path_recorded=e["path"], executed_flag=e["executed"],
                        raw_modified_time=e.get("raw_modified"),
                        time_meaning=meaning, **_where(h, cs, current))


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
    """Per-user program lists with no time per program; rows use the key's last-write time."""
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
    """Task Scheduler 2.0: last run from the registry, program from the task file at its Path."""
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


def extract(ev, target, ctx):
    out = _Out(ev, dict(ctx["common"]), ctx.get('examined_at'))
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
