"""Bounded PE string resources for retained indirect timezone labels.

No Windows loader or evidence code executes. RT_STRING block numbering follows
https://learn.microsoft.com/windows/win32/menurc/resource-types . MUI association
uses the retained RC Config checksum and language, not the examiner's locale:
https://learn.microsoft.com/windows/win32/intl/mui-resource-management .
RC Config offsets are documented by Wine's primary implementation of
GetFileMUIInfo in dlls/kernelbase/locale.c (struct mui_resource).
"""
from __future__ import annotations

import hashlib
import re
import struct

from .application_identity import _bytes, _unpack

MAX_PE_BYTES = 4 << 20
MAX_ENTRIES = 4096


def resources(data, wanted):
    """Return a selected PE resource type with exact physical file offsets."""
    if len(data) > MAX_PE_BYTES or _bytes(data, 0, 2, 'DOS header') != b'MZ':
        raise ValueError('not a bounded resource PE')
    pe, = _unpack('<I', data, 60, 'PE pointer')
    if pe < 64 or _bytes(data, pe, 4, 'PE signature') != b'PE\0\0':
        raise ValueError('invalid PE signature')
    count, = _unpack('<H', data, pe + 6, 'section count')
    size, = _unpack('<H', data, pe + 20, 'optional header size')
    if not 1 <= count <= 96:
        raise ValueError('unsupported section count')
    optional = _bytes(data, pe + 24, size, 'optional header')
    magic, = _unpack('<H', optional, 0, 'optional header magic')
    if magic not in (0x10b, 0x20b):
        raise ValueError('unsupported optional header')
    dd = 96 if magic == 0x10b else 112
    directories, = _unpack('<I', optional, dd - 4, 'directory count')
    if directories < 3:
        return []
    rva, length = _unpack('<II', optional, dd + 16, 'resource directory')
    if rva == length == 0:
        return []
    if not rva or not 16 <= length <= MAX_PE_BYTES:
        raise ValueError('invalid resource directory size')
    headers, = _unpack('<I', optional, 60, 'header size')
    sections = []
    for i in range(count):
        row = _bytes(data, pe + 24 + size + 40 * i, 40, 'section')
        _, address, raw_size, raw = struct.unpack_from('<IIII', row, 8)
        if raw_size:
            _bytes(data, raw, raw_size, 'section content')
            sections.append((address, raw_size, raw))
    def physical(address, length):
        found = [raw + address - start for start, size, raw in sections
                 if start <= address and address + length <= start + size]
        if address + length <= headers <= len(data):
            found.append(address)
        if len(found) != 1:
            raise ValueError('resource address has missing or ambiguous file mapping')
        _bytes(data, found[0], length, 'resource payload')
        return found[0]
    base = physical(rva, length)
    table = data[base:base + length]
    seen = 0
    def directory(at, ancestors):
        nonlocal seen
        if at in ancestors:
            raise ValueError('cyclic resource directory')
        named, numeric = _unpack('<HH', table, at + 12, 'resource counts')
        seen += named + numeric
        if seen > MAX_ENTRIES:
            raise ValueError('resource entry bound exceeded')
        found, names = [], set()
        for i in range(named + numeric):
            name, child = _unpack('<II', table, at + 16 + 8 * i, 'resource entry')
            if name & 0x80000000:
                offset = name & 0x7fffffff
                n, = _unpack('<H', table, offset, 'resource name length')
                if n > 256:
                    raise ValueError('resource name bound exceeded')
                name = _bytes(table, offset + 2, n * 2, 'resource name').decode('utf-16-le')
            elif name > 0xffff:
                raise ValueError('noncanonical numeric resource identifier')
            if name in names:
                raise ValueError('duplicate resource identifier')
            names.add(name)
            found.append((name, child & 0x7fffffff, bool(child & 0x80000000)))
        return found
    found = []
    for kind, a, is_dir in directory(0, ()):
        if kind != wanted:
            continue
        if not is_dir:
            raise ValueError('resource type is not a directory')
        for name, b, is_dir in directory(a, (0,)):
            if not is_dir:
                raise ValueError('resource name is not a directory')
            for language, c, is_dir in directory(b, (0, a)):
                if is_dir or not isinstance(language, int):
                    raise ValueError('invalid resource language entry')
                address, n, cp, reserved = _unpack('<IIII', table, c, 'resource data entry')
                if not 1 <= n <= MAX_PE_BYTES or reserved:
                    raise ValueError('invalid resource payload size/reserved field')
                offset = physical(address, n)
                found.append(dict(data=data[offset:offset + n], byte_offset=offset,
                                  resource_name=name, resource_language=language,
                                  resource_codepage=cp, resource_data_entry_offset=base + c))
    return found


def string_resource(data, identifier, language):
    if type(identifier) is not int or not 1 <= identifier <= 65535:
        raise ValueError('invalid string resource identifier')
    matches = [r for r in resources(data, 6) if r['resource_name'] == identifier // 16 + 1
               and r['resource_language'] == language]
    if len(matches) != 1:
        raise ValueError('selected string block/language is missing or ambiguous')
    record = matches[0]
    at, selected = 0, None
    for i in range(16):
        n, = _unpack('<H', record['data'], at, 'string length')
        start = at + 2
        value = _bytes(record['data'], start, n * 2, 'string').decode('utf-16-le')
        if i == identifier % 16:
            selected = (value, record['byte_offset'] + start, n * 2)
        at = start + n * 2
    if at != len(record['data']):
        raise ValueError('unexpected bytes after sixteen-string block')
    value, offset, size = selected
    if not value or value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('selected resource label is empty or contains unsupported characters')
    provenance = {k: v for k, v in record.items() if k != 'data'}
    provenance.update(string_resource_id=identifier, string_byte_offset=offset, string_byte_length=size)
    return str(value), provenance


def mui_config(data):
    matches = [r for r in resources(data, 'MUI') if r['resource_name'] == 1]
    if len(matches) != 1:
        raise ValueError('MUI configuration is missing or ambiguous')
    record = matches[0]
    raw = record['data']
    signature, size, version = _unpack('<III', raw, 0, 'MUI header')
    if signature != 0xfecdfecd or size != len(raw) or size < 132 or version != 0x10000:
        raise ValueError('unsupported MUI configuration header')
    flags, = _unpack('<I', raw, 16, 'MUI file type')
    kind = flags & 3  # RC Config stores main/MUI as low bits; retain other flags.
    if kind not in (1, 2):
        raise ValueError('unsupported MUI file type')
    spans = {}
    for name, pos in [('path', 68), ('ln_types_named', 84), ('ln_types', 92),
                      ('mui_types_named', 100), ('mui_types', 108),
                      ('language', 116), ('fallback_language', 124)]:
        at, n = _unpack('<II', raw, pos, 'MUI ' + name)
        if n and at < 132:
            raise ValueError('MUI payload overlaps its header')
        spans[name] = _bytes(raw, at, n, 'MUI ' + name)
    def language(name):
        value = spans[name]
        if not value:
            return None
        if len(value) % 2 or not value.endswith(b'\0\0'):
            raise ValueError('MUI language is not terminated Unicode')
        text = value[:-2].decode('utf-16-le')
        if not re.fullmatch(r'[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', text):
            raise ValueError('MUI language name is malformed')
        return text
    checksum = raw[44:60]
    if checksum == bytes(16):
        raise ValueError('MUI association checksum is absent')
    return dict(file_type=kind, raw_file_type=flags, resource_language=record['resource_language'],
                checksum=checksum.hex(), service_checksum=raw[28:44].hex(),
                language=language('language'), fallback_language=language('fallback_language'),
                byte_offset=record['byte_offset'], byte_length=len(raw))


def resolve_timezone_label(target, indirect, language_name, language_id):
    """Resolve one ID using the caller's single recorded installed UI language.

    This is a retained-resource interpretation, not the historical process/thread
    UI choice. Other DLLs, locale fallbacks and search paths remain unsupported.
    """
    match = re.fullmatch(r'@tzres\.dll,-([1-9][0-9]{0,4})', indirect, re.I)
    if not match or not re.fullmatch(r'[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', language_name):
        raise ValueError('unsupported indirect timezone label or language name')
    if not isinstance(language_id, int) or isinstance(language_id, bool) or not 0 < language_id <= 65535:
        raise ValueError('installed UI language has no supported literal LANGID')
    identifier = int(match[1])
    root = target.resolve('%windir%/system32')
    if root.is_symlink() or root.joinpath(language_name).is_symlink():
        raise ValueError('timezone resource directory is a link')
    paths = [root.joinpath('tzres.dll'), root.joinpath(language_name).joinpath('tzres.dll.mui')]
    payloads, files = [], []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise ValueError('required source timezone resource is missing or a link')
        with path.open('rb') as stream:
            data = stream.read(MAX_PE_BYTES + 1)
        if len(data) > MAX_PE_BYTES:
            raise ValueError('timezone resource file exceeds bound')
        payloads.append(data)
        files.append({'source_path': str(path).replace('/', '\\'), 'sha256': hashlib.sha256(data).hexdigest(),
                      'bytes': len(data), 'mui_config': mui_config(data)})
    main, localized = (f['mui_config'] for f in files)
    if (main['file_type'] != 1 or localized['file_type'] != 2 or main['checksum'] != localized['checksum']
            or any(c['resource_language'] not in (0, int(language_id)) for c in (main, localized))
            or not localized['language'] or localized['language'].casefold() != language_name.casefold()):
        raise ValueError('base/MUI resource identity or language does not agree')
    value, location = string_resource(payloads[1], identifier, int(language_id))
    return value, dict(indirect_value=indirect, language_name=language_name, language_id=int(language_id),
                       resources=files, **location,
                       selection='single current-hive installed UI language; exact MUI checksum/language correspondence',
                       limitation='retained resource text; not proof of historical user/process UI language or source authenticity')
