"""VERSIONINFO strings from executables registered under Windows App Paths."""
from __future__ import annotations

import hashlib
import json
from pathlib import PureWindowsPath
import re
import struct

from .attributes import emit_attribute

MAX_BINARY_BYTES = 64 << 20
MAX_TOTAL_BYTES = 512 << 20
MAX_BINARIES = 128
MAX_REGISTRATIONS = 512
MAX_RESOURCE_BYTES = 16 << 20
MAX_RESOURCE_ENTRIES = 4096
MAX_VERSION_RESOURCES = 64
MAX_VERSION_NODES = 4096
FIELDS = {'ProductName': 'app.binary.product_name',
          'ProductVersion': 'app.binary.product_version',
          'FileDescription': 'app.binary.file_description',
          'FileVersion': 'app.binary.file_version'}
APP_PATHS = 'Microsoft\\Windows\\CurrentVersion\\App Paths'


def _bytes(data, offset, length, label):
    if offset < 0 or length < 0 or offset + length > len(data):
        raise ValueError(f'{label} outside source bounds')
    return data[offset:offset + length]


def _unpack(fmt, data, offset, label):
    return struct.unpack(fmt, _bytes(data, offset, struct.calcsize(fmt), label))


def version_resources(data):
    """Return RT_VERSION resources with unambiguous physical file offsets."""
    if len(data) > MAX_BINARY_BYTES or _bytes(data, 0, 2, 'DOS header') != b'MZ':
        raise ValueError('not a bounded PE binary')
    pe_at, = _unpack('<I', data, 0x3c, 'DOS PE pointer')
    if pe_at < 64 or _bytes(data, pe_at, 4, 'PE signature') != b'PE\0\0':
        raise ValueError('invalid PE signature or DOS pointer')
    section_count, = _unpack('<H', data, pe_at + 6, 'COFF section count')
    optional_size, = _unpack('<H', data, pe_at + 20, 'COFF optional-header size')
    if not 1 <= section_count <= 96:
        raise ValueError('PE section count outside supported bound')
    optional = _bytes(data, pe_at + 24, optional_size, 'optional header')
    magic, = _unpack('<H', optional, 0, 'optional magic')
    if magic not in (0x10b, 0x20b):
        raise ValueError('unsupported PE optional-header format')
    directory_at = 96 if magic == 0x10b else 112
    directory_count, = _unpack('<I', optional, directory_at - 4, 'directory count')
    if directory_count < 3:
        return []
    resource_rva, resource_size = _unpack('<II', optional, directory_at + 16, 'resource directory')
    if not resource_rva and not resource_size:
        return []
    if not resource_rva or not 16 <= resource_size <= MAX_RESOURCE_BYTES:
        raise ValueError('invalid or oversized resource directory')
    header_size, = _unpack('<I', optional, 60, 'header size')
    sections = []
    for index in range(section_count):
        section = _bytes(data, pe_at + 24 + optional_size + 40 * index, 40, 'section header')
        _, address, raw_size, raw_at = struct.unpack_from('<IIII', section, 8)
        if raw_size:
            _bytes(data, raw_at, raw_size, 'raw section')
            sections.append((address, raw_size, raw_at))

    def physical(rva, size):
        candidates = [raw + rva - address for address, raw_size, raw in sections
                      if address <= rva and rva + size <= address + raw_size]
        if rva + size <= header_size <= len(data):
            candidates.append(rva)
        if len(candidates) != 1:
            raise ValueError('resource RVA has missing or ambiguous physical mapping')
        _bytes(data, candidates[0], size, 'resource data')
        return candidates[0]

    base = physical(resource_rva, resource_size)
    resources = data[base:base + resource_size]
    entries_seen = 0

    def directory(offset, ancestors):
        nonlocal entries_seen
        if offset in ancestors:
            raise ValueError('cyclic PE resource directory')
        named, numeric = _unpack('<HH', resources, offset + 12, 'resource directory counts')
        count = named + numeric
        entries_seen += count
        if entries_seen > MAX_RESOURCE_ENTRIES:
            raise ValueError('PE resource entry limit exceeded')
        _bytes(resources, offset + 16, 8 * count, 'resource directory entries')
        result = []
        for index in range(count):
            name, child = _unpack('<II', resources, offset + 16 + 8 * index, 'resource entry')
            if name & 0x80000000:
                at = name & 0x7fffffff
                length, = _unpack('<H', resources, at, 'resource name length')
                if length > 256:
                    raise ValueError('PE resource name length limit exceeded')
                name = _bytes(resources, at + 2, 2 * length, 'resource name').decode('utf-16-le')
            else:
                name &= 0xffff
            result.append((name, child & 0x7fffffff, bool(child & 0x80000000)))
        return result

    result = []
    for resource_type, names_at, names_dir in directory(0, ()):
        if resource_type != 16:
            continue
        if not names_dir:
            raise ValueError('RT_VERSION type is not a directory')
        for name, languages_at, languages_dir in directory(names_at, (0,)):
            if not languages_dir:
                raise ValueError('RT_VERSION name is not a language directory')
            for language, entry_at, is_directory in directory(languages_at, (0, names_at)):
                if is_directory:
                    raise ValueError('RT_VERSION language does not point to data')
                rva, size, codepage, _ = _unpack('<IIII', resources, entry_at, 'resource data entry')
                if not 6 <= size <= 1 << 20:
                    raise ValueError('VERSIONINFO resource size outside supported bound')
                offset = physical(rva, size)
                result.append({'data': data[offset:offset + size], 'byte_offset': offset,
                               'resource_name': name, 'resource_language': language,
                               'resource_codepage': codepage, 'resource_data_entry_offset': base + entry_at})
                if len(result) > MAX_VERSION_RESOURCES:
                    raise ValueError('VERSIONINFO resource count limit exceeded')
    return result


def version_strings(data):
    """Read the four StringFileInfo strings, never the fixed numeric version fields."""
    nodes = 0
    align = lambda value: (value + 3) & ~3

    def node(start, limit, depth=0):
        nonlocal nodes
        nodes += 1
        if depth > 5 or nodes > MAX_VERSION_NODES:
            raise ValueError('VERSIONINFO structure limit exceeded')
        length, value_length, value_type = _unpack('<HHH', data, start, 'VERSIONINFO node')
        end = start + length
        if length < 8 or end > limit or value_type not in (0, 1):
            raise ValueError('invalid VERSIONINFO node bounds or value type')
        cursor = start + 6
        key_start = cursor
        while cursor + 2 <= end and data[cursor:cursor + 2] != b'\0\0':
            cursor += 2
        if cursor + 2 > end or cursor - key_start > 512:
            raise ValueError('unterminated or oversized VERSIONINFO key')
        key = data[key_start:cursor].decode('utf-16-le')
        value_at = align(cursor + 2)
        value_size = value_length * (2 if value_type == 1 else 1)
        if value_size and value_at + value_size > end:
            raise ValueError('VERSIONINFO value outside its node')
        value = _bytes(data, value_at, value_size, 'VERSIONINFO value') if value_size else b''
        children, cursor = [], align(value_at + value_size)
        while cursor < end:
            if end - cursor < 6 or data[cursor:cursor + 2] == b'\0\0':
                if any(data[cursor:end]):
                    raise ValueError('nonzero invalid VERSIONINFO child/padding')
                break
            child = node(cursor, end, depth + 1)
            children.append(child)
            cursor = align(child['end'])
        return {'key': key, 'type': value_type, 'value': value, 'value_at': value_at,
                'start': start, 'end': end, 'children': children}

    root = node(0, len(data))
    if root['key'] != 'VS_VERSION_INFO' or root['type'] != 0:
        raise ValueError('resource is not VS_VERSION_INFO')
    if root['value'] and (len(root['value']) != 52 or root['value'][:4] != b'\xbd\x04\xef\xfe'):
        raise ValueError('invalid VS_FIXEDFILEINFO value')
    result = []
    for container in root['children']:
        if container['key'] != 'StringFileInfo':
            continue
        if container['value']:
            raise ValueError('StringFileInfo has an unexpected value')
        for table in container['children']:
            if not re.fullmatch('[0-9a-fA-F]{8}', table['key']) or table['value']:
                raise ValueError('invalid VERSIONINFO language/codepage table')
            keys = set()
            for field in table['children']:
                if field['key'] in keys:
                    raise ValueError('duplicate VERSIONINFO key in one string table')
                keys.add(field['key'])
                if field['key'] not in FIELDS:
                    continue
                if field['type'] != 1 or field['children']:
                    raise ValueError('VERSIONINFO identity field is not a text leaf')
                raw = field['value']
                if raw and not raw.endswith(b'\0\0'):
                    raise ValueError('VERSIONINFO string is not null-terminated')
                value = (raw[:-2] if raw else raw).decode('utf-16-le')
                if '\0' in value:
                    raise ValueError('VERSIONINFO string contains an embedded terminator')
                result.append({'field': field['key'], 'value': value, 'string_table': table['key'],
                               'table_offset': table['start'], 'field_offset': field['start'],
                               'value_offset': field['value_at'], 'value_byte_length': len(raw),
                               'raw_value_hex': raw.hex()})
    return result


def registered_path(raw, target, sid=None):
    """Expand a literal local registration; never search PATH or parse commands."""
    if not isinstance(raw, str) or not raw or '\0' in raw:
        raise ValueError('App Paths default value is not a literal path')
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    if '"' in value:
        raise ValueError('App Paths default contains command syntax')
    value = target.expand_env(value, sid) if '%' in value else value
    path = PureWindowsPath(value)
    if '%' in value or not re.fullmatch('[A-Za-z]:', path.drive) or not path.is_absolute():
        raise ValueError('App Paths default does not resolve to an absolute image-local path')
    if path.suffix.casefold() not in ('.exe', '.com', '.dll'):
        raise ValueError('App Paths default is not a supported binary path')
    return str(path)


def _registered(ev, target):
    from .system import _hives, _open, _subkeys, _vals, _where
    count = 0
    for hive in _hives(ev, target):
        if _where(hive)['source_variant'] != 'primary':
            continue
        roots = [APP_PATHS, 'Wow6432Node\\' + APP_PATHS] if hive.name == 'SOFTWARE' else (
            ['Software\\' + APP_PATHS] if hive.sid and not hive.name.endswith('_CLASSES') else [])
        for root in roots:
            key = _open(ev, hive, root)
            for entry in _subkeys(ev, hive, key) if key is not None else []:
                values = _vals(ev, hive, entry)
                defaults = [(name, values[name]) for name in ('', '(Default)') if name in values]
                for name, raw in defaults:
                    count += 1
                    if count > MAX_REGISTRATIONS:
                        raise ValueError('registered application limit exceeded; reading stopped early')
                    locator = {'hive_path': hive.path, 'registry_key': entry.path,
                               'registry_value': name, 'registered_path': raw, 'account_sid': hive.sid}
                    try:
                        yield registered_path(raw, target, hive.sid), locator
                    except Exception as error:
                        ev.problem(hive.path + ':' + entry.path, error)


def extract(ev, target, ctx):
    """Emit version strings and file hashes for registered applications."""
    from .source_scope import merge_scope, subject_scope
    candidates = {}
    try:
        for source, registration in _registered(ev, target):
            candidates.setdefault(source.casefold(), {'path': source, 'registrations': []})['registrations'].append(registration)
            if len(candidates) > MAX_BINARIES:
                raise ValueError('registered binary count limit exceeded; no enumeration-completeness claim')
    except Exception as error:
        ev.problem('registered application inventory', error)
        return
    total = 0
    for candidate in candidates.values():
        source = candidate['path']
        try:
            path = target.fs.path(source)
            if not path.is_file():
                raise FileNotFoundError('registered binary is unavailable in the supplied image')
            size = path.stat().st_size
            if size < 64 or size > MAX_BINARY_BYTES:
                raise ValueError('registered binary exceeds supported size bounds')
            total += size
            if total > MAX_TOTAL_BYTES:
                raise ValueError('registered binary total-byte limit exceeded; reading stopped early')
            with path.open('rb') as stream:
                data = stream.read(MAX_BINARY_BYTES + 1)
            if len(data) != size:
                raise ValueError('registered binary length disagrees with source metadata')
            digest = hashlib.sha256(data).hexdigest()
            records = []
            for resource in version_resources(data):
                for field in version_strings(resource['data']):
                    records.append((resource, field))
            common = merge_scope(ctx['common'], dict(artifact=source, source_path=source,
                          parser='extractor.application_identity', registrations=candidate['registrations'],
                          file_sha256=digest, file_size=size,
                          limitation='literal binary metadata; no execution, use, authenticity, or marketing-year inference'))
            ev.add('fileContent', ctx['examined_at'], 1, source, 'sha256:' + digest,
                   **dict(common, hash_complete=True, timestamp_semantics='examination_observation',
                          time_meaning='when the image was examined, not an event on the device'))
            for resource, field in records:
                scope = subject_scope(common) + [source, digest,
                         resource['resource_name'], resource['resource_language'],
                         resource['byte_offset'], field['string_table'], field['table_offset']]
                locator = {key: value for key, value in resource.items() if key not in ('data', 'byte_offset')}
                locator.update({key: value for key, value in field.items() if key != 'value'})
                locator.update(resource_byte_offset=resource['byte_offset'],
                               byte_offset=resource['byte_offset'] + field['value_offset'],
                               byte_length=field['value_byte_length'], encoding='utf-16-le')
                emit_attribute(ev, json.dumps(scope, ensure_ascii=True, separators=(',', ':')),
                               FIELDS[field['field']], field['value'], ctx['examined_at'], **common, **locator)
        except Exception as error:
            ev.problem(source, error)
            if total > MAX_TOTAL_BYTES:
                break
