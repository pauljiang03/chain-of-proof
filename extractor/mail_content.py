"""Literal MAPI text and HTML properties, decoded only by the code page the message records."""
from __future__ import annotations

import codecs
import hashlib
import struct

MAX_SETS = 64
MAX_ENTRIES = 4096
MAX_TEXT_BYTES = 2 * 1024 * 1024
SOURCES = (
    'https://learn.microsoft.com/en-us/office/client-developer/outlook/mapi/pidtagmessagecodepage-canonical-property',
    'https://learn.microsoft.com/en-us/office/client-developer/outlook/mapi/pidtaginternetcodepage-canonical-property',
    'https://learn.microsoft.com/en-us/office/client-developer/outlook/mapi/pidtaghtml-canonical-property',
)


def _count(value, maximum):
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
        raise ValueError('MAPI record count is invalid or exceeds its limit')
    return int(value)


def one_property(item, property_id, *, optional_object=False):
    if optional_object and not hasattr(item, 'number_of_record_sets'):
        return None
    found = []
    for set_index in range(_count(item.number_of_record_sets, MAX_SETS)):
        record_set = item.get_record_set(set_index)
        for entry_index in range(_count(record_set.number_of_entries, MAX_ENTRIES)):
            entry = record_set.get_entry(entry_index)
            if entry.entry_type == property_id:
                if found:
                    raise ValueError('duplicate MAPI property occurrences are ambiguous')
                raw = entry.data
                if not isinstance(raw, bytes) or len(raw) > MAX_TEXT_BYTES:
                    raise ValueError('MAPI property bytes are invalid or exceed the byte limit')
                found.append((entry.value_type, raw,
                              {'record_set': set_index, 'property_entry': entry_index,
                               'property_id': property_id, 'property_byte_length': len(raw)}))
    return found[0] if found else None


def _codepage(message, property_id, folder=None, *, allow_utf16=False):
    found = one_property(message, property_id)
    if found is None:
        raise ValueError('encoded MAPI text has no recorded code-page property')
    kind, raw, locator = found
    if kind != 0x0003 or len(raw) != 4:
        raise ValueError('MAPI code page must be one four-byte PT_LONG property')
    codepage = struct.unpack('<I', raw)[0]
    scope = 'message'
    if codepage == 0 and property_id == 0x3FFD and folder is not None:
        found = one_property(folder, property_id, optional_object=True)
        if found is None or found[0] != 0x0003 or len(found[1]) != 4:
            raise ValueError('zero message code page has no explicit folder code page')
        codepage = struct.unpack('<I', found[1])[0]
        locator = dict(found[2], message_codepage_locator=locator)
        scope = 'containing folder'
    # Windows code pages with exact Python codecs; nothing else is guessed.
    aliases = {65001: 'utf-8', 20127: 'ascii', 28591: 'iso8859-1', 28592: 'iso8859-2',
               20866: 'koi8-r', 21866: 'koi8-u'}
    if allow_utf16:
        aliases.update({1200: 'utf-16-le', 1201: 'utf-16-be'})
    single_or_multibyte = {437, 850, 852, 855, 857, 858, 860, 861, 862, 863, 864, 865,
                          866, 869, 874, 932, 936, 949, 950, *range(1250, 1259)}
    encoding = aliases.get(codepage, 'cp' + str(codepage) if codepage in single_or_multibyte else None)
    if encoding is None:
        raise ValueError('recorded MAPI code page is unsupported')
    encoding = codecs.lookup(encoding).name
    return encoding, dict(codepage=codepage, codepage_scope=scope, codepage_locator=locator)


def text_property(message, property_id, *, folder=None):
    """One property's value, its locators and how it was decoded."""
    found = one_property(message, property_id)
    if found is None:
        return None
    kind, raw, locator = found
    details = dict(locator, property_type=int(kind), property_sha256=hashlib.sha256(raw).hexdigest(),
                   interpretation_sources=list(SOURCES))
    if property_id in (0x0037, 0x1000):
        field = 'subject' if property_id == 0x0037 else 'body'
        if kind == 0x001F:
            if len(raw) % 2:
                raise ValueError('PT_UNICODE text has odd byte length')
            value = raw.decode('utf-16-le', errors='strict')
            role, encoding = 'mail.message.' + field + '_unicode', 'utf-16-le'
        elif kind == 0x001E:
            encoding, cp = _codepage(message, 0x3FFD if property_id == 0x0037 else 0x3FDE, folder)
            value = raw.decode(encoding, errors='strict')
            details.update(cp)
            role = 'mail.message.' + field + '_string8'
        else:
            raise ValueError('MAPI subject/body is neither PT_UNICODE nor PT_STRING8')
        if value.endswith('\0'):
            value = value[:-1]
        if '\0' in value:
            raise ValueError('MAPI text contains an embedded NUL')
    elif property_id == 0x1013:
        if kind != 0x0102:
            raise ValueError('MAPI HTML body is not PT_BINARY')
        encoding, cp = _codepage(message, 0x3FDE, allow_utf16=True)
        # The recorded code page decides; a BOM must agree and HTML meta tags are ignored.
        bom = next(((prefix, codec) for prefix, codec in ((b'\xef\xbb\xbf', 'utf-8'),
                    (b'\xff\xfe', 'utf-16-le'), (b'\xfe\xff', 'utf-16-be')) if raw.startswith(prefix)), None)
        if bom is not None:
            prefix, codec = bom
            if encoding != codec:
                raise ValueError('HTML BOM conflicts with recorded body code page')
            value = raw[len(prefix):].decode(encoding, errors='strict')
            details['encoding_prefix_bytes'] = len(prefix)
        else:
            value = raw.decode(encoding, errors='strict')
        if '\0' in value:
            raise ValueError('MAPI HTML has an embedded NUL')
        role = 'mail.message.body_html'
        details.update(cp, html_policy='literal decoded markup; no rendering, scripts, network or body-text inference')
    else:
        raise ValueError('unsupported MAPI text property')
    details.update(text_encoding=encoding, source_field=f'MAPI 0x{property_id:04X}/0x{kind:04X}',
                   validation='strict source-declared text encoding; original property bytes and locator retained')
    return dict(role=role, value=value, byte_count=len(raw), provenance=details)
