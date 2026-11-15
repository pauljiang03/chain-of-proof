"""Legacy Windows application evidence, read without executing evidence programs.

The public case prompts guide artifact coverage; this module contains no answer
values, suspect names or case-specific paths. Configuration and traffic fields
are source observations, not personal identity, intent, or victim attribution.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import struct
from pathlib import PureWindowsPath

from .attributes import emit_attribute
from .store import us_from_filetime

MAX_FILE = 32 << 20
MAX_FILES = 100000
MAX_PACKETS = 100000
OBSERVED = 'when the source was examined, not an event on the device'
PCAP_MAGIC = {b'\xd4\xc3\xb2\xa1': ('<', 1000000), b'\xa1\xb2\xc3\xd4': ('>', 1000000),
              b'\x4d\x3c\xb2\xa1': ('<', 1000000000), b'\xa1\xb2\x3c\x4d': ('>', 1000000000)}
EMAIL = re.compile(rb'(?<![A-Za-z0-9_.+%-])[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}(?![A-Za-z0-9.-])')


def text_lines(data):
    """Decode text while retaining exact source byte offsets and physical lines."""
    prefix = 0
    if data.startswith(b'\xff\xfe'):
        encoding, prefix = 'utf-16-le', 2
    elif data.startswith(b'\xfe\xff'):
        encoding, prefix = 'utf-16-be', 2
    elif data.startswith(b'\xef\xbb\xbf'):
        encoding, prefix = 'utf-8', 3
    else:
        encoding = 'cp1252'
    try:
        text = data[prefix:].decode(encoding)
    except UnicodeDecodeError:
        if prefix:
            raise ValueError('invalid BOM-declared text encoding') from None
        encoding, text = 'latin-1', data.decode('latin-1')
    offset = prefix
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        size = len(line.encode(encoding))
        yield {'line': number, 'byte_offset': offset, 'byte_length': size,
               'text_encoding': encoding, 'raw_line': line.rstrip('\r\n')}
        offset += size


def ini_entries(data):
    """Read literal INI entries; duplicate keys remain separate observations."""
    section = ''
    for row in text_lines(data):
        line = row['raw_line'].strip()
        if not line or line.startswith((';', '#')):
            continue
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1].strip()
        elif '=' in line:
            key, value = line.split('=', 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
            yield dict(row, section=section, key=key.strip(), value=value)


INI_ROLES = {
    ('profile', 'fullname'): 'app.config.real_name',
    ('profile', 'emailaddress'): 'app.config.email',
    ('profile', 'username'): 'app.config.username',
    ('servers', 'newsserver'): 'app.config.nntp_server',
    ('servers', 'mailserver'): 'app.config.smtp_server',
    ('mirc', 'user'): 'app.config.real_name',
    ('mirc', 'email'): 'app.config.email',
    ('mirc', 'nick'): 'app.config.nickname',
    ('mirc', 'anick'): 'app.config.alternate_nickname',
    ('mirc', 'host'): 'app.config.irc_server',
    ('ident', 'userid'): 'app.config.username',
    ('variables', '%username%'): 'app.config.real_name',
    ('variables', '%regowner%'): 'app.config.registered_owner',
    ('variables', '%lanuser%'): 'app.config.username',
    ('variables', '%lanhost%'): 'app.config.hostname',
    ('variables', '%lanip%'): 'network.ip_address',
    ('variables', '%lannic%'): 'network.mac_address',
    ('variables', '%productname%'): 'app.name',
    ('variables', '%isuserntadmin%'): 'app.config.is_admin',
}


def config_attributes(data):
    for entry in ini_entries(data):
        role = INI_ROLES.get((entry['section'].lower(), entry['key'].lower()))
        if not role or not entry['value']:
            continue
        value = entry.pop('value')
        if role == 'app.config.is_admin':
            if value.upper() not in ('TRUE', 'FALSE'):
                raise ValueError('unrecognized installer administrator flag')
            value = value.upper() == 'TRUE'
        elif role == 'network.mac_address':
            compact = re.sub(r'[-:.]', '', value)
            if not re.fullmatch(r'[0-9A-Fa-f]{12}', compact):
                raise ValueError('invalid configured MAC address')
            entry['original_value'] = value
            entry['normalization'] = 'six validated hexadecimal bytes, uppercase colon-separated'
            value = ':'.join(compact[i:i + 2].upper() for i in range(0, 12, 2))
        yield role, value, entry


def irc_channels(data):
    """Logged Session Ident channels only; a default channel list is not use."""
    for row in text_lines(data):
        match = re.fullmatch(r'Session Ident:\s*(#[^\s,]+)\s*', row['raw_line'])
        if match:
            yield match.group(1), row


def dbx_mailbox(data):
    """A typed message-file header names retained news storage, not subscription.

    Format: https://www.infobyte.hr/oedbx/doc/OE_Dbx_FileInfo.html
    The original folder name can survive renaming; that caveat is exported.
    """
    signature = bytes.fromhex('cfad12fec5fd746f66e3d1119a4e00c04fa309d4')
    if not data.startswith(signature) or len(data) < 0x24bc:
        raise ValueError('not an Outlook Express message DBX header')
    length = struct.unpack_from('<I', data, 0x1c)[0]
    if length < 0x205 or 0x24bc + length > len(data):
        raise ValueError('truncated DBX file-info object')
    info = data[0x24bc:0x24bc + length]
    if info[:4] != b'\x01\0\0\0' or info[4] not in (0, 1, 3):
        raise ValueError('unsupported DBX message source type')
    if info[4] != 0:
        return None
    def field(offset):
        raw = info[offset:offset + 256]
        end = raw.find(b'\0')
        if end < 0:
            raise ValueError('unterminated DBX file-info text')
        return raw[:end].decode('cp1252')
    name, account = field(0x105), field(5)
    if not name:
        raise ValueError('DBX news mailbox has no original folder name')
    return {'name': name, 'account_key': account, 'byte_offset': 0x24bc + 0x105,
            'source_type': 0, 'note': 'initial newsgroup mailbox name, possibly retained after renaming; '
            'file presence does not establish current subscription'}


def msie_url_records(data):
    """Allocated IE 4.7/5.2 URL records with bounded in-record string pointers.

    Format: libyal/libmsiecf documentation/MSIE Cache File (index.dat) format.
    No free-space carving and no interpreting a cache timestamp as a visit.
    """
    signature = bytes(data[:28]).split(b'\0', 1)[0]
    versions = {b'Client UrlCache MMF Ver 4.7': (56, 64),
                b'Client UrlCache MMF Ver 5.2': (52, 60)}
    if signature not in versions or len(data) < 0x4000:
        raise ValueError('unsupported or truncated IE index.dat header')
    location_field, filename_field = versions[signature]
    offset = 0x4000
    while offset + 128 <= len(data):
        block = (offset - 0x4000) // 128
        if 0x250 + block // 8 >= 0x4000:
            raise ValueError('IE index.dat allocation bitmap bound exceeded')
        if not (data[0x250 + block // 8] >> (block % 8)) & 1:
            offset += 128
            continue
        kind = data[offset:offset + 4]
        if kind not in (b'URL ', b'HASH', b'REDR', b'LEAK'):
            offset += 128
            continue
        blocks = struct.unpack_from('<I', data, offset + 4)[0]
        end = offset + blocks * 128
        if not blocks or end > len(data):
            raise ValueError(f'invalid IE record length at byte {offset}')
        for part in range(block, block + blocks):
            if 0x250 + part // 8 >= 0x4000 or not (data[0x250 + part // 8] >> (part % 8)) & 1:
                raise ValueError(f'IE record overlaps unallocated blocks at byte {offset}')
        if kind == b'URL ':
            row = data[offset:end]
            def field(at):
                pointer = struct.unpack_from('<I', row, at)[0]
                if not pointer:
                    return None, None
                stop = row.find(b'\0', pointer)
                if pointer < 104 or pointer >= len(row) or stop < 0:
                    raise ValueError(f'invalid IE string pointer at byte {offset + at}')
                raw = row[pointer:stop]
                try:
                    value, encoding = raw.decode('cp1252'), 'cp1252'
                except UnicodeDecodeError:
                    value, encoding = raw.decode('latin-1'), 'latin-1'
                return value, {'byte_offset': offset + pointer, 'byte_length': len(raw), 'encoding': encoding}
            location, location_locator = field(location_field)
            filename, filename_locator = field(filename_field)
            if location:
                yield {'location': location, 'filename': filename,
                       'location_locator': location_locator, 'filename_locator': filename_locator,
                       'byte_offset': offset, 'byte_length': len(row), 'allocated': True,
                       'primary_filetime': struct.unpack_from('<Q', row, 16)[0],
                       'secondary_filetime': struct.unpack_from('<Q', row, 8)[0]}
        offset = end


def info2_records(data):
    """XP/2000 INFO2 records. A recycle entry does not mean data is unallocated."""
    if len(data) < 20:
        raise ValueError('truncated INFO2 header')
    version, _, _, record_size, _ = struct.unpack_from('<5I', data)
    if version not in (4, 5) or record_size not in (280, 800):
        raise ValueError('unsupported INFO2 version or record size')
    if (len(data) - 20) % record_size:
        raise ValueError('truncated INFO2 record')
    for offset in range(20, len(data), record_size):
        row = data[offset:offset + record_size]
        index, drive, filetime, size = struct.unpack_from('<IIQI', row, 260)
        if drive > 25:
            raise ValueError('invalid INFO2 drive number')
        if record_size == 800:
            path = row[280:800].decode('utf-16-le').split('\x00', 1)[0]
        else:
            path = row[:260].split(b'\x00', 1)[0].decode('cp1252')
        if not re.match(r'^[A-Za-z]:\\', path):
            raise ValueError('INFO2 original path unavailable; no path invented')
        deleted = us_from_filetime(filetime)
        if deleted < 0:
            raise ValueError('INFO2 deletion timestamp predates Unix epoch')
        yield {'original_path': path, 'record_index': index, 'drive': chr(65 + drive),
               'deleted_us': deleted, 'size': size, 'byte_offset': offset, 'record_size': record_size}


def pcap_tcp_payloads(data):
    """Bounded classic-PCAP Ethernet/IPv4 TCP payloads, preserving packet locators."""
    if data[:4] not in PCAP_MAGIC or len(data) < 24:
        raise ValueError('not a complete classic PCAP header')
    endian, fraction = PCAP_MAGIC[data[:4]]
    major, minor, _, _, snaplen, linktype = struct.unpack_from(endian + 'HHIIII', data, 4)
    if (major, minor) != (2, 4) or linktype != 1 or not snaplen:
        raise ValueError('only classic PCAP 2.4 Ethernet captures are supported')
    offset, number, epochs = 24, 0, {}
    while offset < len(data):
        number += 1
        if number > MAX_PACKETS or offset + 16 > len(data):
            raise ValueError('PCAP packet bound or truncated packet header')
        sec, subsec, captured, original = struct.unpack_from(endian + '4I', data, offset)
        if captured > snaplen or captured > original or subsec >= fraction or offset + 16 + captured > len(data):
            raise ValueError('invalid or truncated PCAP packet')
        packet, start = data[offset + 16:offset + 16 + captured], offset + 16
        offset += 16 + captured
        if len(packet) < 14:
            continue
        ethertype, ip_at = int.from_bytes(packet[12:14], 'big'), 14
        if ethertype == 0x8100 and len(packet) >= 18:
            ethertype, ip_at = int.from_bytes(packet[16:18], 'big'), 18
        if ethertype != 0x0800 or len(packet) < ip_at + 20:
            continue
        ip = packet[ip_at:]
        ihl, total = (ip[0] & 15) * 4, int.from_bytes(ip[2:4], 'big')
        if ip[0] >> 4 != 4 or ihl < 20 or total < ihl + 20 or total > len(ip):
            continue
        if ip[9] != 6 or int.from_bytes(ip[6:8], 'big') & 0x3fff:
            continue  # no fragment reassembly or non-TCP attribution
        tcp = ip[ihl:total]
        tcp_size = (tcp[12] >> 4) * 4
        if tcp_size < 20 or tcp_size > len(tcp):
            continue
        source_port, dest_port, sequence = struct.unpack_from('>HHI', tcp)
        flow = (str(ipaddress.IPv4Address(ip[12:16])), source_port,
                str(ipaddress.IPv4Address(ip[16:20])), dest_port)
        if tcp[13] & 2:
            epochs[flow] = epochs.get(flow, 0) + 1
            sequence = (sequence + 1) & 0xffffffff
        payload = tcp[tcp_size:]
        if payload:
            yield {'flow': flow + (epochs.get(flow, 0),), 'sequence': sequence, 'payload': payload,
                   'packet_number': number, 'packet_time_us': sec * 1000000 + subsec * 1000000 // fraction,
                   'byte_offset': start + ip_at + ihl + tcp_size, 'byte_length': len(payload)}


def http_requests(data):
    """Parse complete request headers; split TCP gaps, reject conflicting overlaps."""
    flows = {}
    for packet in pcap_tcp_payloads(data):
        flows.setdefault(packet['flow'], []).append(packet)
    for flow, packets in flows.items():
        runs, current, first, end, locations = [], bytearray(), None, None, []
        for packet in sorted(packets, key=lambda p: p['sequence']):
            seq, value = packet['sequence'], packet['payload']
            if end is None or seq > end:
                if current:
                    runs.append((bytes(current), locations))
                current, locations, first, end = bytearray(), [], seq, seq
            overlap = max(0, end - seq)
            compared = min(overlap, len(value))
            if compared and current[seq - first:seq - first + compared] != value[:compared]:
                raise ValueError('conflicting TCP retransmission bytes; HTTP fields withheld')
            locations.append({key: val for key, val in packet.items() if key not in ('payload', 'flow')})
            current.extend(value[overlap:])
            end = first + len(current)
        if current:
            runs.append((bytes(current), locations))
        for stream, locations in runs:
            cursor = 0
            while cursor < len(stream):
                stop = stream.find(b'\r\n\r\n', cursor, cursor + 65536)
                if stop < 0:
                    break
                lines = stream[cursor:stop].split(b'\r\n')
                request = re.fullmatch(rb'(GET|HEAD|POST|PUT|DELETE|OPTIONS|PATCH|CONNECT) ([^\x00-\x20]+) HTTP/1\.[01]', lines[0])
                if not request:
                    break  # response bodies and arbitrary embedded text are not requests
                fields = []
                for line in lines[1:]:
                    key, sep, value = line.partition(b':')
                    if sep and re.fullmatch(rb'[A-Za-z0-9-]+', key):
                        fields.append((key.decode('ascii').lower(), value.strip().decode('latin-1')))
                headers = {}
                for key, value in fields:
                    headers.setdefault(key, []).append(value)
                yield {'method': request[1].decode('ascii'), 'request_target': request[2].decode('latin-1'),
                       'headers': headers, 'stream_offset': cursor, 'header_length': stop + 4 - cursor,
                       'flow': list(flow), 'packets': locations}
                if headers.get('transfer-encoding'):
                    break  # no guessing chunked body boundaries
                lengths = headers.get('content-length', ['0'])
                if len(set(lengths)) != 1 or not lengths[0].isdigit():
                    break
                cursor = stop + 4 + int(lengths[0])


def _path(path):
    return str(path).replace('/', '\\')


def _subject(ctx, path):
    return json.dumps([ctx['common'].get('image'), ctx['common'].get('exhibit'), path], separators=(',', ':'))


def _emit(ev, ctx, path, role, value, **locator):
    provenance = dict(ctx['common'], artifact=path, source_path=path,
                      parser='extractor.hacking', **locator)
    return emit_attribute(ev, _subject(ctx, path), role, value, ctx['examined_at'], **provenance)


def _read(path):
    size = path.stat().st_size
    if size > MAX_FILE:
        raise ValueError(f'file exceeds bounded reader limit of {MAX_FILE} bytes')
    with path.open('rb') as source:
        data = source.read(MAX_FILE + 1)
    if len(data) != size:
        raise ValueError('file content length disagrees with filesystem metadata')
    return data


def _content(ev, ctx, path, data, **extra):
    source = _path(path)
    ev.add('fileContent', ctx['examined_at'], 1, source, 'sha256:' + hashlib.sha256(data).hexdigest(),
           **dict(ctx['common'], artifact=source, source_path=source, size=len(data), hash_complete=True,
                  parser='extractor.hacking', time_meaning=OBSERVED, **extra))
    _emit(ev, ctx, source, 'source.path', source, **extra)


def _configs(ev, paths, ctx):
    for path in paths:
        if path.name.lower() not in ('mirc.ini', 'agent.ini', 'irunin.ini'):
            continue
        try:
            data = _read(path)
            _content(ev, ctx, path, data)
            for role, value, locator in config_attributes(data):
                _emit(ev, ctx, _path(path), role, value, **locator)
        except Exception as error:
            ev.problem(_path(path), error)


def _logs(ev, paths, ctx):
    for path in paths:
        if path.suffix.lower() != '.log' or '\\mirc\\logs\\' not in _path(path).lower():
            continue
        try:
            data = _read(path)
            _content(ev, ctx, path, data)
            for channel, locator in irc_channels(data):
                _emit(ev, ctx, _path(path), 'app.config.irc_channel', channel, **locator)
                _emit(ev, ctx, _path(path), 'app.config.irc_log_file_name', path.name,
                      channel_from_session_ident=channel, **locator)
        except Exception as error:
            ev.problem(_path(path), error)


def _mail_accounts(ev, target, ctx):
    """Per-user Internet Account Manager values, shared by Outlook Express."""
    roles = {'SMTP Email Address': 'app.config.email', 'NNTP Email Address': 'app.config.email',
             'SMTP Server': 'app.config.smtp_server', 'NNTP Server': 'app.config.nntp_server',
             'SMTP Display Name': 'app.config.real_name', 'NNTP Display Name': 'app.config.real_name',
             'NNTP User Name': 'app.config.username', 'POP3 User Name': 'app.config.username'}
    target.registry.load_user_hives()
    from .system import _hives
    for hive in _hives(ev, target):
        if not hive.path.lower().endswith('ntuser.dat'):
            continue
        try:
            key = hive.hive.key('Software\\Microsoft\\Internet Account Manager\\Accounts')
        except Exception as error:
            if type(error).__name__ not in ('RegistryKeyNotFoundError', 'RegistryKeyNotFoundException', 'RegistryKeyNotFound'):
                ev.problem(hive.path, error)
            continue
        for account in key.subkeys():
            source = hive.path + ':' + account.path
            for value in account.values():
                if value.name in roles and isinstance(value.value, str) and value.value:
                    _emit(ev, ctx, source, roles[value.name], value.value, hive_path=hive.path,
                          registry_key=account.path, registry_value=value.name,
                          account=hive.account, account_sid=hive.sid,
                          application_family='Microsoft Internet Account Manager / Outlook Express')


def _news(ev, paths, ctx):
    for path in paths:
        source = _path(path)
        if path.suffix.lower() != '.dbx':
            continue
        try:
            data = _read(path)
            if path.name.lower() == 'folders.dbx':
                _content(ev, ctx, path, data, inventory_category='legacy_news_folder_database')
                ev.problem(source, ValueError('subscription state unsupported: Folders.dbx includes '
                           'unselected groups, and documented active-folder flags do not prove subscription'))
                continue
            # Other DBX stores (UIDL/offline) have different CLSIDs.
            if data[:8] != bytes.fromhex('cfad12fec5fd746f'):
                continue
            item = dbx_mailbox(data)
            if item:
                _content(ev, ctx, path, data, inventory_category='legacy_news_mailbox')
                _emit(ev, ctx, source, 'app.news.group_mailbox', item.pop('name'), **item)
        except Exception as error:
            ev.problem(source, error)


def _traffic(ev, paths, ctx):
    for path in paths:
        try:
            with path.open('rb') as source:
                magic = source.read(4)
            if magic not in PCAP_MAGIC:
                continue
            data = _read(path)
            requests = list(http_requests(data))  # reject ambiguity before emitting any fields
            _content(ev, ctx, path, data, content_format='classic PCAP')
            _emit(ev, ctx, _path(path), 'traffic.file_name', path.name, content_format='classic PCAP')
            for request in requests:
                locator = {key: value for key, value in request.items() if key != 'headers'}
                locator['parser_scope'] = ('complete HTTP/1 request headers in contiguous, nonconflicting '
                                           'Ethernet/IPv4 TCP payloads; encrypted/fragmented traffic not decoded')
                _emit(ev, ctx, _path(path), 'traffic.http_method', request['method'], **locator)
                for field, role in (('host', 'traffic.http_host'), ('user-agent', 'traffic.user_agent')):
                    for value in request['headers'].get(field, []):
                        _emit(ev, ctx, _path(path), role, value, header_field=field, **locator)
                target = request['request_target']
                if target.startswith(('http://', 'https://')):
                    _emit(ev, ctx, _path(path), 'traffic.url', target, **locator)
                elif target.startswith('/') and len(request['headers'].get('host', [])) == 1:
                    host = request['headers']['host'][0]
                    if re.fullmatch(r'[A-Za-z0-9.\-:\[\]]+', host):
                        _emit(ev, ctx, _path(path), 'traffic.url', 'http://' + host + target,
                              derivation='cleartext HTTP request target plus its single Host header', **locator)
        except Exception as error:
            ev.problem(_path(path) + ': traffic inspection', error)


def _browser(ev, paths, ctx):
    for path in paths:
        source = _path(path)
        if '\\temporary internet files\\' not in source.lower() or path.name.lower() == 'desktop.ini':
            continue
        try:
            data = _read(path)
            _content(ev, ctx, path, data, inventory_category='legacy_browser_cache')
            _emit(ev, ctx, source, 'browser.cache_file_name', path.name,
                  note='observed cache filename, not a declaration of message ownership')
            for match in EMAIL.finditer(data):
                _emit(ev, ctx, source, 'browser.email_address', match[0].decode('ascii'),
                      byte_offset=match.start(), byte_length=len(match[0]),
                      note='literal email-address text in a browser artifact; ownership not inferred')
        except Exception as error:
            ev.problem(source, error)


def _browser_indexes(ev, paths, ctx):
    for path in paths:
        if path.name.lower() != 'index.dat':
            continue
        source = _path(path)
        try:
            with path.open('rb') as stream:
                signature = stream.read(28)
            if not signature.startswith(b'Client UrlCache MMF Ver '):
                continue
            data = _read(path)
            records = list(msie_url_records(data))
            _content(ev, ctx, path, data, inventory_category='legacy_browser_index')
            global_history = source.lower().endswith('\\history\\history.ie5\\index.dat')
            for record in records:
                location = record['location']
                if location.startswith('Visited:') and '@' in location:
                    location = location.split('@', 1)[1]
                if not location.lower().startswith(('http://', 'https://', 'ftp://')):
                    continue
                locator = dict(record, parser_scope='allocated IE URL records; cache access is not a user visit',
                               primary_time_meaning=('global history last visited UTC' if global_history
                                                     else 'source-specific; no visit time inferred'))
                _emit(ev, ctx, source, 'browser.url', location, **locator)
                if record['filename']:
                    _emit(ev, ctx, source, 'browser.cache_file_name', record['filename'], **locator)
                raw_time = record['primary_filetime']
                if global_history and 116444736000000000 <= raw_time < 0x7fffffffffffffff:
                    ev.add('webVisit', us_from_filetime(raw_time), 1, location, 'Internet Explorer',
                           **dict(ctx['common'], artifact=source, source_path=source,
                                  parser='extractor.hacking.msie', time_meaning='global history last visited UTC',
                                  **locator))
        except Exception as error:
            ev.problem(source, error)


def _recycle(ev, target, paths, ctx):
    bins = [path for path in paths if re.search(r'\\(?:recycler|recycled)\\', _path(path), re.I)]
    executables = []
    for path in bins:
        if path.suffix.lower() == '.exe':
            with path.open('rb') as source:
                if source.read(2) == b'MZ':
                    executables.append(_path(path))
                    _emit(ev, ctx, _path(path), 'recycle.file_present', True,
                          definition='path resolves as a file and starts with MZ; not an execution claim')
        if path.name.lower() != 'info2':
            continue
        try:
            data = _read(path)
            _content(ev, ctx, path, data)
            for record in info2_records(data):
                stored = path.parent / ('D' + record['drive'].lower() + str(record['record_index'])
                                        + PureWindowsPath(record['original_path']).suffix)
                locator = dict(record, stored_path=_path(stored))
                subject = _path(path) + ':record:' + str(record['record_index'])
                _emit(ev, ctx, subject, 'recycle.original_path', record['original_path'], **locator)
                _emit(ev, ctx, subject, 'recycle.stored_path', _path(stored), **locator)
                _emit(ev, ctx, subject, 'recycle.file_present', stored.is_file(), **locator)
                if stored.is_file():
                    # Read the actual retained file's in-use bit; presence alone
                    # is not an inverse deletion flag and is never projected as one.
                    fs = target.fs.mounts[record['drive'].lower() + ':']
                    entry = fs.ntfs.mft.get(str(stored)[3:])
                    _emit(ev, ctx, subject, 'filesystem.deleted_flag', not bool(entry.header.Flags & 1),
                          mft_segment=entry.segment, **locator)
                ev.add('fileDeleted', record['deleted_us'], 1, record['original_path'],
                       **dict(ctx['common'], artifact=_path(path), parser='extractor.hacking.info2',
                              time_meaning='time moved to the Recycle Bin, not filesystem deallocation', **locator))
        except Exception as error:
            ev.problem(_path(path), error)
    _emit(ev, ctx, 'filesystem Recycle Bin inventory', 'recycle.executable_count', len(executables),
          source_paths=executables, definition='allocated namespace .exe files under RECYCLER/Recycled with MZ signature',
          enumeration_complete=True)


def _deleted(ev, target, ctx):
    """Count distinct valid, named, non-directory MFT entries marked unallocated."""
    seen = set()
    for mount, fs in target.fs.mounts.items():
        ntfs = getattr(fs, 'ntfs', None)
        if ntfs is None or id(ntfs) in seen:
            continue
        seen.add(id(ntfs))
        deleted, examined, errors = [], 0, []
        for record in ntfs.mft.segments():
            examined += 1
            if record.header.Flags & 3:
                continue
            base = record.header.BaseFileRecordSegment
            if base.SegmentNumberLowPart or base.SegmentNumberHighPart:
                continue  # extension records are not additional files
            try:
                paths = list(record.full_paths(ignore_dos=True))
                if not paths or not record.filename:
                    continue
                locator = dict(mft_segment=record.segment, sequence_number=record.header.SequenceNumber,
                               filesystem_mount=mount, allocation_flag=False)
                deleted.append(record.segment)
                for path in paths:
                    _emit(ev, ctx, str(mount) + ':MFT:' + str(record.segment),
                          'filesystem.deleted_path', path, **locator)
                    _emit(ev, ctx, str(mount) + ':MFT:' + str(record.segment),
                          'filesystem.allocated', False, **locator)
                    _emit(ev, ctx, str(mount) + ':MFT:' + str(record.segment),
                          'filesystem.deleted_flag', True, **locator)
            except Exception as error:
                errors.append(str(record.segment))
                ev.problem(f'MFT record {record.segment}', error)
        if not errors:
            _emit(ev, ctx, str(mount) + ':$MFT', 'filesystem.deleted_count', len(set(deleted)),
                  records_examined=examined, mft_segments=sorted(set(deleted)),
                  definition='distinct valid named non-directory MFT base records with in-use flag clear; '
                             'invalid/uninitialized slots excluded by the NTFS parser; not a count of recoverable files',
                  enumeration_complete=True)


def extract(ev, target, ctx):
    """Inspect bounded legacy user/application namespaces; report every reader failure."""
    paths, seen = [], set()
    # XP profiles and earlier standalone document folders are both supported.
    for root in ('C:/Program Files', 'C:/Program Files (x86)', 'C:/Documents and Settings',
                 'C:/Users', 'C:/My Documents', 'C:/RECYCLER', 'C:/Recycled'):
        top = target.fs.path(root)
        if not top.exists():
            continue
        for path in top.rglob('*'):
            if path.is_file() and _path(path).lower() not in seen:
                seen.add(_path(path).lower())
                paths.append(path)
                if len(paths) > MAX_FILES:
                    raise ValueError('legacy namespace inventory bound exceeded; no completeness claim emitted')
    paths.sort(key=lambda path: _path(path).lower())
    for label, reader in (
        ('legacy application configuration', lambda: _configs(ev, paths, ctx)),
        ('IRC session logs', lambda: _logs(ev, paths, ctx)),
        ('legacy mail/news accounts', lambda: _mail_accounts(ev, target, ctx)),
        ('legacy newsgroup storage', lambda: _news(ev, paths, ctx)),
        ('packet capture content', lambda: _traffic(ev, paths, ctx)),
        ('legacy browser cache', lambda: _browser(ev, paths, ctx)),
        ('legacy browser indexes', lambda: _browser_indexes(ev, paths, ctx)),
        ('legacy Recycle Bin', lambda: _recycle(ev, target, paths, ctx)),
        ('NTFS deleted entries', lambda: _deleted(ev, target, ctx)),
    ):
        try:
            reader()
        except Exception as error:
            ev.problem(label, error)
