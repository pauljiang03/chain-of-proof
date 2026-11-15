"""The Windows PC: USB devices, volumes, shortcuts, jump lists, searches, files, Recycle Bin, mail."""
from __future__ import annotations

import io
import hashlib
import json
import re
import struct
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from dissect.ole import OLE
from dissect.shellitem.lnk import Lnk
from dissect.target import Target

from .store import Evidence, us, us_from_filetime, us_from_unix
from .profiles import user_profiles, ntfs_volume_serial
from .source_scope import base_volume_scope, merge_scope, subject_scope
from .attributes import emit_attribute

USER_DIRS = ("Desktop", "Documents", "My Documents", "Downloads")
SEARCH_PARAMS = dict.fromkeys(("google.com", "google.co.uk", "google.ca", "google.de",
                              "google.fr", "google.com.au", "google.co.jp", "google.co.in",
                              "bing.com"), "q") | {"yahoo.com": "p"}
MAX_SEARCH_URL = 65536
MAX_USB_RECORDS = 10000
MAX_SETUPAPI_BYTES = 64 * 1024 * 1024


def _usb_component(value):
    """Keep the instance ID text as is; it may encode a port location, not a hardware serial."""
    if not isinstance(value, str):
        raise ValueError('USB instance components must be source text')
    value = str.__str__(value)  # plain str from Dissect's str subclasses
    if (not value or len(value) > 16384 or '\\' in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError('USB instance component is empty, oversized or malformed')
    return value


def _usb_context(ev, common, examined_at, where):
    if type(examined_at) is not int or examined_at <= 0:
        ev.problem(where, ValueError('explicit positive examination time required; USB attributes omitted'))
        return None
    if any(not isinstance(common.get(key), str) or not common[key].strip()
           for key in ('image', 'exhibit')):
        ev.problem(where, ValueError('explicit image and exhibit required; USB attributes omitted'))
        return None
    return merge_scope(common)


def _usb_observation(ev, common, examined_at, device, instance, source_type,
                     artifact, locator, recorded_time=None, record_time_meaning=None, **details):
    device, instance = _usb_component(device), _usb_component(instance)
    device_id = 'USBSTOR\\' + device
    instance_id = device_id + '\\' + instance
    provenance = merge_scope(common, dict(artifact=artifact, source_entry=locator,
        reader='windows.usb_instances', source_type=source_type,
        device_identity_kind='windows_device_instance',
        hardware_serial_status='not established from a Windows instance identifier',
        **details))
    # This identifies one retained source observation, not a physical device.
    subject = json.dumps(subject_scope(provenance) + [source_type, artifact, locator, instance_id],
                         sort_keys=True, ensure_ascii=True, separators=(',', ':'))
    fields = [('usb.device_instance_id', instance_id), ('usb.device_id', device_id),
              ('usb.instance_id', instance), ('usb.source_type', source_type)]
    if recorded_time is not None:
        fields += [('usb.recorded_time', recorded_time),
                   ('usb.record_time_meaning', record_time_meaning)]
        provenance.update(recorded_time=recorded_time, recorded_time_meaning=record_time_meaning)
    for role, value in fields:
        emit_attribute(ev, subject, role, value, examined_at, **provenance)


def _usb(ev, t, common, *, examined_at=None):
    """USBSTOR key observations; key names are not validated hardware serials."""
    common = _usb_context(ev, common, examined_at, 'USB registry instances')
    if common is None:
        return 0
    # The registry view does not say which hive file a key came from.
    common = merge_scope(common, {'source_variant': 'unknown'})
    path = "HKLM\\SYSTEM\\CurrentControlSet\\Enum\\USBSTOR"
    from dissect.target.exceptions import RegistryKeyNotFoundError
    try:
        devices = t.registry.key(path)
    except RegistryKeyNotFoundError:
        return 0  # An absent key does not prove that no device was used.
    count = 0
    seen = 0
    for device_index, dev in enumerate(devices.subkeys()):
        if device_index >= MAX_USB_RECORDS:
            ev.problem(path, ValueError('USB registry device enumeration limit reached'))
            break
        try:
            device = _usb_component(dev.name)
            for instance_index, inst in enumerate(dev.subkeys()):
                if seen >= MAX_USB_RECORDS:
                    ev.problem(path, ValueError('USB registry instance enumeration limit reached'))
                    return count
                seen += 1
                where = f'{path}\\{device} instance {instance_index}'
                try:
                    instance = _usb_component(inst.name)
                    where = f'{path}\\{device}\\{instance}'
                    stamp = None
                    try:
                        value = inst.timestamp
                        if not isinstance(value, datetime) or value.utcoffset() is None:
                            raise ValueError('registry key last-write timestamp has no explicit UTC offset')
                        stamp = value.isoformat()
                    except Exception as error:
                        ev.problem(where, error)
                    locator = dict(device_index=device_index, instance_index=instance_index,
                                   registry_key=where, decoded_last_write=stamp)
                    _usb_observation(ev, common, examined_at, device, instance, 'USBSTOR registry key',
                        where, locator, stamp, 'registry key last-write timestamp decoded by the parser',
                        source_path=where, registry_hive_identity='not supplied by the virtual registry API')
                    count += 1
                except Exception as error:
                    ev.problem(where, error)
        except Exception as error:
            ev.problem(f'{path} device {device_index}', error)
    return count


def _setupapi(ev, t, common, tz=None, *, examined_at=None):
    """USBSTOR install sections and their local time text; `tz` is unused (today's zone may differ)."""
    common = _usb_context(ev, common, examined_at, 'SetupAPI USB instances')
    if common is None:
        return 0
    path = t.fs.path("C:/Windows/inf/setupapi.dev.log")
    if not path.exists():
        return 0
    source = r'C:\Windows\inf\setupapi.dev.log'
    with path.open('rb') as handle:
        raw = handle.read(MAX_SETUPAPI_BYTES + 1)
    if len(raw) > MAX_SETUPAPI_BYTES:
        raise ValueError('SetupAPI log exceeds the 64 MiB parsing limit')
    # SetupAPI logs are ANSI: latin-1 finds the ASCII structure without guessing a code page.
    # Non-ASCII identifiers are reported, never guessed.
    # https://learn.microsoft.com/en-us/windows-hardware/drivers/install/setupapi-text-logs
    encoding, prefix = 'latin-1', 0
    for bom, candidate in ((b'\xef\xbb\xbf', 'utf-8'), (b'\xff\xfe', 'utf-16-le'),
                           (b'\xfe\xff', 'utf-16-be')):
        if raw.startswith(bom):
            encoding, prefix = candidate, len(bom)
            break
    # Split only on CR/LF: an ANSI byte like 0x85 must not become a line break.
    lines = [line for line in re.findall(r'[^\r\n]*(?:\r\n|\r|\n|\Z)', raw[prefix:].decode(encoding)) if line]
    offsets, offset = [], prefix
    for line in lines:
        offsets.append(offset)
        offset += len(line.encode(encoding))
    digest = hashlib.sha256(raw).hexdigest()
    head = re.compile(r'^>>>[ \t]+\[Device Install \(Hardware initiated\) - USBSTOR\\([^\\\]\r\n]+)\\([^\\\]\r\n]+)\][ \t]*$')
    start = re.compile(r'^>>>[ \t]+Section start ([0-9]{4}/[0-9]{2}/[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3})[ \t]*$')
    count = 0
    seen = 0
    for i, line in enumerate(lines):
        match = head.fullmatch(line.rstrip('\r\n'))
        if match is None:
            continue
        if seen >= MAX_USB_RECORDS:
            ev.problem(source, ValueError('SetupAPI USB section enumeration limit reached'))
            break
        seen += 1
        where = f'{source} line {i + 1}'
        try:
            if not prefix and any(not part.isascii() for part in match.groups()):
                raise ValueError('non-ASCII SetupAPI identifier requires an established source code page')
            when = start.fullmatch(lines[i + 1].rstrip('\r\n')) if i + 1 < len(lines) else None
            stamp = None
            length = len(line.encode(encoding))
            if when is not None:
                # Validate the calendar fields but preserve the original wall-clock text.
                try:
                    datetime.strptime(when.group(1), '%Y/%m/%d %H:%M:%S.%f')
                    stamp = when.group(1)
                    length += len(lines[i + 1].encode(encoding))
                except ValueError as error:
                    ev.problem(where, error)
            else:
                ev.problem(where, ValueError('USB install header lacks an adjacent supported section timestamp'))
            locator = dict(source_sha256=digest, header_line=i + 1,
                           byte_offset=offsets[i], byte_length=length,
                           encoding=encoding if prefix else 'ASCII fields; ANSI source code page unknown')
            if stamp is not None:
                locator['section_start_line'] = i + 2
            _usb_observation(ev, common, examined_at, *match.groups(), 'SetupAPI install section',
                where, locator, stamp, 'SetupAPI section start local wall-clock text; UTC offset not recorded',
                source_path=source, source_sha256=digest,
                event_scope='retained install-section observation, not first connection or physical insertion')
            count += 1
        except Exception as error:
            ev.problem(where, error)
    return count


def _volumes_seen(ev, t, common):
    common = merge_scope(common, {'source_variant': 'unknown'})
    path = "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\EMDMgmt"
    from dissect.target.exceptions import RegistryKeyNotFoundError
    try:
        volumes = t.registry.key(path)
    except RegistryKeyNotFoundError:
        return
    for sub in volumes.subkeys():
        m = re.match(r"^(.{6})(.*)_(\d+)$", sub.name)
        if not m:
            continue
        ev.add("volumeSeen", us(sub.timestamp), 1, m.group(2), "%08X" % int(m.group(3)),
               artifact=f"{path}\\{sub.name}", time_meaning="registry key last-write time",
               **common)


def _lnk_fact(ev, lnk: Lnk, t_us: int, common: dict, **prov) -> bool:
    """One lnkTarget: obj = path without drive, aux = volume serial or network share."""
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
    for user in user_profiles(t):
        for rel in ("AppData/Roaming/Microsoft/Windows/Recent",
                    "AppData/Roaming/Microsoft/Office/Recent", "Recent",
                    "Application Data/Microsoft/Office/Recent"):
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
                            time_meaning="shortcut file last-modified time",
                            shortcut_created=us_from_unix(st.st_birthtime))
                except Exception as e:
                    ev.problem(str(p), e)
    return n


class _EmptyOLEChain:
    def open(self):
        return io.BytesIO(b"")


class _JumpListOLE(OLE):
    """Handles an absent MiniFAT (MS-CFB 2.4), whose ENDOFCHAIN Dissect OLE 3.12 reads as a sector."""
    def chain(self, sect, size=None):
        if sect == 0xFFFFFFFE:
            if self.header._sectDirStart == sect:
                raise ValueError("CFB directory chain is absent")
            if size == 0 or (size is None and self.header._sectMiniFatStart == sect
                             and self.header._csectMiniFat == 0):
                return _EmptyOLEChain()
            raise ValueError("CFB nonempty chain starts at ENDOFCHAIN")
        return super().chain(sect, size)

    def minichain(self, sect, size=None):
        if sect == 0xFFFFFFFE:
            if size == 0:
                return _EmptyOLEChain()
            raise ValueError("CFB nonempty mini stream starts at ENDOFCHAIN")
        return super().minichain(sect, size)


def _destlist(data: bytes) -> dict:
    """DestList v1-v4: numbered LNK stream -> (entry-update FILETIME, raw path).

    The v2+ trailer is a property-store byte count. Format: https://github.com/libyal/dtformats/blob/main/documentation/Jump%20lists%20format.asciidoc
    """
    if not data:                         # an empty DestList stream is valid
        return {}
    if len(data) < 32:
        raise ValueError("DestList header is truncated")
    version, count = struct.unpack_from("<II", data)
    if version not in (1, 2, 3, 4):
        raise ValueError(f"unsupported DestList version {version}")
    path_offset = 112 if version == 1 else 128
    out, off = {}, 32
    for _ in range(count):
        if off + path_offset + 2 > len(data):
            raise ValueError(f"DestList entry header is truncated at byte {off}")
        entry = struct.unpack_from("<I", data, off + 88)[0]
        filetime = struct.unpack_from("<Q", data, off + 100)[0]
        length = struct.unpack_from("<H", data, off + path_offset)[0]
        start, end = off + path_offset + 2, off + path_offset + 2 + 2 * length
        if end > len(data):
            raise ValueError(f"DestList path is truncated at byte {off}")
        path = data[start:end].decode("utf-16-le")
        if "\x00" in path:
            raise ValueError(f"DestList path contains a NUL at byte {off}")
        if version > 1:
            if end + 4 > len(data):
                raise ValueError(f"DestList property-store size is truncated at byte {end}")
            extra = struct.unpack_from("<I", data, end)[0]
            end += 4 + extra
            if end > len(data):
                raise ValueError(f"DestList property store is truncated at byte {off}")
        key = f"{entry:x}"
        if key in out:
            raise ValueError(f"duplicate DestList stream number {key}")
        out[key] = (filetime, path)
        off = end
    if off != len(data):
        raise ValueError(f"DestList header declares {count} entries but {len(data) - off} bytes remain")
    return out


def _jumplist_stream(ole, name):
    entry = ole.get(name)
    if entry.size > 16 * 1024 * 1024:
        raise ValueError(f"JumpList stream {name} exceeds the 16 MiB parsing limit")
    data = entry.open().read()
    if len(data) != entry.size:
        raise ValueError(f"JumpList stream {name} read {len(data)} of {entry.size} bytes")
    return data


def _jumplists(ev, t, common):
    n = 0
    for user in user_profiles(t):
        folder = user.joinpath("AppData/Roaming/Microsoft/Windows/Recent/AutomaticDestinations")
        if not folder.exists():
            continue
        for p in sorted(folder.iterdir(), key=lambda x: x.name):
            try:
                with p.open("rb") as stream:
                    ole = _JumpListOLE(stream)
                    names = list(ole.root.listdir())
                    if "DestList" not in names:
                        continue
                    raw = _jumplist_stream(ole, "DestList")
                    dest = _destlist(raw)
                    version = struct.unpack_from("<I", raw)[0] if raw else None
                    for name, (filetime, dest_path) in dest.items():
                        where = f"{str(p).replace('/', chr(92))} stream {name}"
                        try:
                            if name not in names:
                                raise ValueError("DestList references a missing numbered LNK stream")
                            t_us = us_from_filetime(filetime)
                            if not 0 < t_us < 4_102_444_800_000_000:
                                raise ValueError("DestList entry FILETIME is outside supported 1970-2100 range")
                            lnk = Lnk(io.BytesIO(_jumplist_stream(ole, name)))
                            prov = dict(artifact=where, user=user.name, destlist_path=dest_path,
                                        destlist_version=version, destlist_filetime=filetime,
                                        timestamp_semantics="destlist_entry_update", source="JumpList",
                                        time_meaning="jump list DestList entry last-update FILETIME "
                                                     "(shell access record, not target-file modification)")
                            if _lnk_fact(ev, lnk, t_us, common, **prov):
                                n += 1
                            elif re.match(r"^[A-Za-z]:\\", dest_path):
                                # No volume serial is stored; none is inferred from the drive letter.
                                ev.add("lnkTarget", t_us, 1, dest_path[2:].rstrip("\\") or "\\", "",
                                       drive_letter=dest_path[:2],
                                       volume="not recorded by this jump list entry", **prov, **common)
                                n += 1
                            else:
                                ev.problem(where, ValueError(
                                    "DestList target is not a supported filesystem path; "
                                    "no file-target fact emitted: " + repr(dest_path)))
                        except Exception as error:
                            ev.problem(where, error)
            except Exception as e:
                ev.problem(str(p), e)
    return n


def search_query(url):
    """Search text from a URL of a supported search provider (exact host match), decoded once."""
    if not isinstance(url, str) or len(url) > MAX_SEARCH_URL:
        raise ValueError("search URL is not bounded text")
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("control character in search URL")
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or parts.username is not None:
        return None
    host = (parts.hostname or "").lower().rstrip('.')
    match = next(((domain, param) for domain, param in SEARCH_PARAMS.items()
                  if host == domain or host.endswith('.' + domain)), None)
    if match is None:
        return None
    domain, param = match
    prefix = host[:-len(domain)].rstrip('.')
    allowed_prefixes = ('', 'www', 'images', 'encrypted') if domain.startswith('google.') else (
        ('', 'www', 'search') if domain == 'yahoo.com' else ('', 'www'))
    allowed_paths = ('/', '/search', '/webhp') if domain.startswith('google.') else ('/', '/search')
    if prefix not in allowed_prefixes or (parts.path or '/') not in allowed_paths:
        return None  # A redirect/login/mail endpoint's q/p parameter is not a search.
    # Only for Google, the fragment overrides the query string.
    locations = [("query", parts.query)]
    if domain.startswith('google.'):
        locations.insert(0, ("fragment", parts.fragment))
    for location, raw in locations:
        if re.search(r'%(?![0-9a-fA-F]{2})', raw):
            raise ValueError("malformed percent escape in search parameters")
        values = parse_qs(raw, keep_blank_values=True, errors='strict', max_num_fields=1024).get(param)
        if values is None:
            continue
        if len(values) != 1:
            raise ValueError("ambiguous repeated search parameter")
        query = values[0]  # parse_qs already decodes percent escapes and '+' once.
        if not query.strip():
            return None
        if any(ord(char) < 32 or ord(char) == 127 for char in query):
            raise ValueError("control character in decoded search query")
        return query, dict(search_provider_domain=domain, query_parameter=param,
                           query_component=location, query_decoding='one UTF-8 form-decoding pass')
    return None


def _searches(ev, t, common, *, examined_at=None):
    n = 0
    typed_time = type(examined_at) is int and examined_at > 0
    if not typed_time:
        ev.problem('search attributes', ValueError('explicit positive examination time required; typed fields omitted'))
    if hasattr(t, "has_function") and not t.has_function("browser.history"):
        return n  # legacy IE history is read elsewhere
    for r in t.browser.history():
        source = str(r.source or '').replace('/', '\\')
        try:
            url = str(r.url or "")
            parsed = search_query(url)
            if parsed is None or r.ts is None:
                continue
            query, derivation = parsed
            recorded_us = us(r.ts)  # rejects naive dates; never use examination time.
            browser = str(r.browser or '')
            provenance = merge_scope(common, dict(artifact=source, source_path=source,
                url=url, user=getattr(r, 'username', None), reader='windows.searches',
                parser='dissect.target.browser.history', **derivation))
            ev.add("webSearch", recorded_us, 1, query, browser,
                   time_meaning="browser history visit time", **provenance)
            n += 1
            if not typed_time:
                continue
            record_id = getattr(r, 'id', None)
            if not source or record_id is None or not str(record_id) or not browser:
                raise ValueError("history record lacks a source, record identifier or browser; no typed tuple")
            provenance.update(history_record_id=str(record_id), recorded_time_us=recorded_us,
                recorded_time_meaning=('WebCache history AccessedTime' if browser == 'iexplore'
                                       else 'browser history visit timestamp'),
                limitation='retained search URL and source timestamp; not physical user attribution')
            # Some ESE containers reuse EntryId values, so the values are part of the subject.
            subject = json.dumps(subject_scope(provenance) + [source, browser, str(record_id),
                recorded_us, url], ensure_ascii=True, separators=(',', ':'))
            stamp = r.ts.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            for role, value in (('browser.search.url', url), ('browser.search.query', query),
                                ('browser.search.browser', browser), ('browser.search.recorded_time', stamp)):
                emit_attribute(ev, subject, role, value, examined_at, **provenance)
        except Exception as error:
            ev.problem(source or 'browser history search', error)
    return n


def _user_files(ev, t, common):
    n = 0
    for user in user_profiles(t):
        vsn = ntfs_volume_serial(t, user)
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
    """One volumeSeen row per (label, serial) recorded by shortcuts, from the earliest one."""
    import json as _json
    first = {}
    for kind, t_us, _res, _obj, aux, prov in ev.rows():
        if kind != "lnkTarget":
            continue
        pv = _json.loads(prov)
        if any(pv.get(key) != common.get(key) for key in ("image", "exhibit")):
            continue
        label = pv.get("volume_label")
        origin = merge_scope(pv)
        key = (label, aux, origin['source_snapshot'], origin['source_variant'])
        if label and key not in first:      # rows() is sorted by time within a kind
            first[key] = (t_us, _res, pv)
    for (label, serial, snapshot, variant), (t_us, resolution, pv) in sorted(first.items()):
        ev.add("volumeSeen", t_us, resolution, label, serial,
               artifact=f"volume block of shortcut: {pv.get('artifact', '')}",
               drive_type=DRIVE_TYPES.get(pv.get("drive_type"), str(pv.get("drive_type"))),
               time_meaning=pv.get("time_meaning") or "unspecified originating shortcut record timestamp",
               timestamp_semantics=pv.get("timestamp_semantics", "shortcut_record_observation"),
               limitation="retained shortcut volume metadata; not proof of target opening or mount time",
               **merge_scope(common, {'source_snapshot': snapshot, 'source_variant': variant}))
    return len(first)


RECYCLE_INDEX = re.compile(r"^\$I[0-9A-Z]{6}(\.[^\\/:\x00-\x1f]*)?$", re.I)
MAX_RECYCLE_INDEX = 28 + 2 * 32768


def parse_recycle_index(data):
    """Validated $I v1/v2 fields with byte locators and the full original path."""
    if len(data) < 26 or len(data) > MAX_RECYCLE_INDEX:
        raise ValueError('truncated or oversized Recycle Bin index')
    version, size, filetime = struct.unpack_from('<QQQ', data)
    if version == 1:
        if len(data) != 544:
            raise ValueError('version 1 Recycle Bin index must have its 260-character path field')
        start, raw = 24, data[24:]
    elif version == 2:
        if len(data) < 30:
            raise ValueError('truncated version 2 Recycle Bin index')
        count = struct.unpack_from('<I', data, 24)[0]
        if not 1 <= count <= 32768 or len(data) != 28 + count * 2:
            raise ValueError('version 2 path character count does not match retained bytes')
        start, raw = 28, data[28:]
    else:
        raise ValueError(f'unknown Recycle Bin index version {version}')
    # Find aligned UTF-16 NUL before decoding; v1 padding after it is not text.
    end = next((offset for offset in range(0, len(raw), 2) if raw[offset:offset + 2] == b'\0\0'), None)
    if end is None or (version == 2 and end != len(raw) - 2):
        raise ValueError('Recycle Bin path lacks its expected UTF-16 terminator')
    original = raw[:end].decode('utf-16-le', errors='strict')
    if (not re.match(r'^[A-Za-z]:\\', original)
            or any(ord(char) < 32 for char in original)):
        raise ValueError('Recycle Bin original path is not a literal drive-qualified path')
    ticks = filetime - 116444736000000000
    if ticks < 0:
        raise ValueError('Recycle Bin timestamp predates the supported Unix epoch')
    seconds, fraction = divmod(ticks, 10000000)
    stamp = datetime.fromtimestamp(seconds, timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    stamp += f'.{fraction:07d}Z'  # Keep the source FILETIME's 100-nanosecond precision.
    return dict(version=version, original_size=size, filetime=filetime,
                deleted_at=stamp, deleted_at_us=ticks // 10, original_path=original,
                path_byte_offset=start, path_byte_length=end,
                path_field_byte_length=len(raw))


def _recycle_bin(ev, t, common, *, examined_at=None):
    """Recycle Bin $I records from the file table; resident, they survive emptying until reused."""
    typed_time = type(examined_at) is int and examined_at > 0
    if not typed_time:
        ev.problem('Recycle Bin attributes', ValueError('explicit positive examination time required; typed fields omitted'))
    n = 0
    seen = set()
    for mount, fs in sorted(t.fs.mounts.items()):
        if not re.fullmatch('[A-Za-z]:', mount) or id(fs) in seen or not getattr(fs, 'ntfs', None):
            continue
        seen.add(id(fs))  # Deduplicate aliases only for the identical filesystem object.
        vsn = "%08X" % (fs.ntfs.serial & 0xFFFFFFFF)
        for rec in fs.ntfs.mft.segments():
            name = None
            try:
                name = rec.filename
                if not isinstance(name, str) or not name or not RECYCLE_INDEX.fullmatch(name) or rec.header.Flags & 2:
                    continue
                name = str(name)  # Dissect's WCHAR text subclass retains the same characters.
                with rec.open() as stream:
                    data = stream.read(MAX_RECYCLE_INDEX + 1)
                parsed = parse_recycle_index(data)
                original = parsed['original_path']
                in_use = bool(rec.header.Flags & 1)
                provenance = merge_scope(common, dict(
                    artifact=f'Recycle Bin index {name}, {mount.upper()} file table record {rec.segment}',
                    source_path=mount.upper() + r'\$MFT', filesystem_mount=mount.upper(),
                    mft_segment=int(rec.segment), mft_sequence_number=int(rec.header.SequenceNumber),
                    mft_flags=int(rec.header.Flags), index_file_name=name,
                    index_sha256=hashlib.sha256(data).hexdigest(), index_bytes=len(data),
                    index_record_in_use=in_use, original_drive=original[:2],
                    size=parsed['original_size'], parser='windows.parse_recycle_index',
                    format_version=parsed['version'], path_byte_offset=parsed['path_byte_offset'],
                    path_byte_length=parsed['path_byte_length'], time_byte_offset=16, time_byte_length=8,
                    raw_filetime=parsed['filetime'],
                    limitation='retained index metadata; not actor identity, emptying of the bin, recoverability or current original-file allocation'))
                if not in_use:
                    provenance.update(source_variant='unallocated-recovery', recovered=True)
                ev.add('fileDeleted', parsed['deleted_at_us'], 1, original[2:], vsn,
                       time_meaning='deletion time stored in the Recycle Bin index', **provenance)
                n += 1
                if not typed_time:
                    continue
                subject = json.dumps(subject_scope(provenance) + [mount.upper(), '$MFT',
                    int(rec.segment), int(rec.header.SequenceNumber), provenance['index_sha256']],
                    ensure_ascii=True, separators=(',', ':'))
                for role, value in (('recycle.index_file_name', name),
                                    ('recycle.original_path', original),
                                    ('recycle.index_deleted_at', parsed['deleted_at'])):
                    emit_attribute(ev, subject, role, value, examined_at, **provenance)
            except Exception as error:
                ev.problem(f'{mount} file table record {rec.segment} ({name})', error)
    return n


BURN_TEMP = re.compile(r"^(DAT|FIL|POST)\d{5}\.tmp$", re.I)
BURN_KEY = "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\CD Burning"


def _burn_traces(ev, t, common):
    """CD-burn traces: journal temp files, cdrom event 133, CD Burning key; none proves a write."""
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
    # 2. System event log: cdrom driver event 133 (exclusive-access lock)
    try:
        records = t.evtx() if not hasattr(t, "has_function") or t.has_function("evtx") else ()
        for r in records:
            d = r._asdict()
            if str(d.get("Provider_Name")) != "cdrom" or str(d.get("EventID")) != "133":
                continue
            ev.add("cdBurn", us(d["ts"]), 1, f"cdrom driver event 133 for {d.get('Data_0')}",
                   "System event log", artifact=str(d.get("source", "")).replace("/", "\\"),
                   event_record_id=str(d.get("EventRecordID")), channel=str(d.get("Channel")),
                   event_id=int(d["EventID"]), event_meaning="device locked for exclusive access",
                   physical_disc_identified=False, time_meaning="exclusive-access event time", **common)
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
                   time_meaning="registry key last-write time",
                   **merge_scope(common, {'source_variant': 'unknown'}))
            n += 1
    except Exception as e:
        ev.problem(BURN_KEY, e)
    return n


MAPI_DISPLAY_TO, MAPI_SENDER_SMTP, MAPI_MESSAGE_ID = 0x0E04, 0x5D01, 0x1035


def _mapi_text_property(message, wanted: int):
    """(text, availability) of one property; absent and empty are different."""
    for record_set in message.record_sets:
        for entry in record_set.entries:
            if entry.entry_type == wanted:
                if entry.data is None or entry.value_type not in (0x1E, 0x1F):
                    return None, "unavailable"
                if entry.value_type == 0x1F:
                    value = entry.data.decode("utf-16-le", "replace").rstrip("\x00")
                else:
                    value = entry.data.decode("utf-8", "replace").rstrip("\x00")
                return value, "present" if value else "empty"
    return None, "missing"


def _mapi_text(message, wanted: int) -> str:
    return _mapi_text_property(message, wanted)[0] or ""


def _email(ev, t, common):
    """Messages the user's OST/PST still lists, via libpff (recoverable items are not exposed)."""
    files = []
    for user in user_profiles(t):
        for layout in ("AppData/Local/Microsoft/Outlook", "Local Settings/Application Data/Microsoft/Outlook"):
            box = user.joinpath(layout)
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
                sender, sender_status = _mapi_text_property(m, MAPI_SENDER_SMTP)
                ev.add("emailSent", us_from_filetime(sent), 1_000_000, subject,
                       f"from {m.sender_name} to {to}",
                       artifact=f"{source} folder {' / '.join(here[-2:])}", mailbox_user=user,
                       folder=here[-1], sender_address=sender, sender_address_status=sender_status,
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
            with path.open("rb") as handle:
                contents = handle.read()
            box.open_file_object(io.BytesIO(contents))
            walk(box.get_root_folder(), [], user, source)
        except Exception as e:
            ev.problem(source, e)
    return n


def _step(ev: Evidence, name: str, fn, default=0):
    """Run one part of the reader; a missing artifact is reported and the rest continues."""
    try:
        return fn()
    except Exception as e:
        ev.problem(name, e)
        return default


def extract_pc(ev: Evidence, path, tool: str, exhibit: str = "PC", *, examined_at=None):
    t = Target.open(path)
    common = dict(image=path.name, exhibit=exhibit, tool=tool, **base_volume_scope())
    _step(ev, "USB instances in the registry", lambda: _usb(ev, t, common, examined_at=examined_at))
    _step(ev, "device install log", lambda: _setupapi(ev, t, common, examined_at=examined_at))
    _step(ev, "volumes recorded in the registry", lambda: _volumes_seen(ev, t, common))
    parts = (("shortcuts", lambda: _lnk_files(ev, t, common)),
             ("jump list entries", lambda: _jumplists(ev, t, common)),
             ("volume labels in shortcuts", lambda: _volumes_in_shortcuts(ev, common)),
             ("searches", lambda: _searches(ev, t, common, examined_at=examined_at)),
             ("user files", lambda: _user_files(ev, t, common)),
             ("Recycle Bin records", lambda: _recycle_bin(ev, t, common, examined_at=examined_at)),
             ("CD-burn traces", lambda: _burn_traces(ev, t, common)),
             ("e-mails", lambda: _email(ev, t, common)))
    counts = {name: _step(ev, name, fn) for name, fn in parts}
    info = {"hostname": t.hostname, "os": str(t.version), "time_zone": str(t.timezone)}
    return info, [f"{path.name}: {info['hostname']}, {info['os']}, zone {info['time_zone']}; "
                  + ", ".join(f"{v} {k}" for k, v in counts.items())]
