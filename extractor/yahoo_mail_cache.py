"""Yahoo Mail pages in the legacy IE cache, matched through index.dat URL records."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import re
import struct
from urllib.parse import parse_qs, urljoin, urlsplit

from .attributes import emit_attribute
from .source_scope import merge_scope, subject_scope

ROLE = 'browser.yahoo_mail_cache_file_name'
MAX_HTML = 8 << 20
MAX_NODES = 100000
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
        'param', 'source', 'track', 'wbr'}
IGNORED_TEXT = {'script', 'style', 'head', 'title', 'template', 'noscript'}


def _component(value):
    return (isinstance(value, str) and bool(value) and value not in ('.', '..')
            and not re.search(r'[\x00-\x1f\x7f\\/:*?"<>|]', value)
            and not value.endswith((' ', '.')))


def _message_url(value, *, require_id=True):
    """The historical message-view route, not a generic Yahoo or mail URL."""
    try:
        if not isinstance(value, str) or re.search(r'[\x00-\x20\\]', value):
            return None
        url = urlsplit(value)
        host = (url.hostname or '').lower()
        if (url.scheme not in ('http', 'https') or url.username is not None
                or url.password is not None or url.port not in (None, 80, 443)
                or not (host == 'mail.yahoo.com' or host.endswith('.mail.yahoo.com'))
                or url.path != '/ym/ShowLetter' or url.fragment):
            return None
        query = parse_qs(url.query, keep_blank_values=True, max_num_fields=128)
        ids = query.get('MsgId', [])
        if require_id and (len(ids) != 1 or not ids[0] or re.search(r'[\x00-\x20]', ids[0])):
            return None
        if len(ids) > 1:
            return None
        # Attachment download/preview responses are not the message page.
        if any(key in query for key in ('bodyPart', 'tnef', 'VScan')):
            return None
        return {'host': host, 'message_id': ids[0] if ids else None}
    except ValueError:
        return None


class _HTML(HTMLParser):
    """Small bounded tree with byte locators; latin-1 makes offsets one-to-one."""
    def __init__(self, data):
        super().__init__(convert_charrefs=True)
        self.text = data.decode('latin-1')
        self.lines = [0]
        self.lines.extend(match.end() for match in re.finditer('\n', self.text))
        self.root = {'tag': '', 'children': [], 'start': 0, 'end': len(data)}
        self.stack, self.nodes = [self.root], []

    def byte_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attributes):
        if len(self.nodes) >= MAX_NODES or len(self.stack) >= 256:
            raise ValueError('Yahoo message HTML structure bound exceeded')
        # HTML may omit row and cell end tags; close them only within this table.
        if tag in ('tr', 'td', 'th'):
            for index in range(len(self.stack) - 1, 0, -1):
                prior = self.stack[index]['tag']
                if prior == 'table' or (tag != 'tr' and prior == 'tr'):
                    break
                if prior == tag or (tag in ('td', 'th') and prior in ('td', 'th')):
                    del self.stack[index:]
                    break
        if len(dict(attributes)) != len(attributes):
            raise ValueError('ambiguous duplicate HTML attributes')
        node = {'tag': tag, 'attrs': dict(attributes), 'children': [],
                'start': self.byte_offset(), 'end': None,
                'ignored': self.stack[-1].get('ignored', False)
                           or self.stack[-1]['tag'] in IGNORED_TEXT,
                'table': next((parent['start'] for parent in reversed(self.stack)
                               if parent['tag'] == 'table'), None)}
        self.stack[-1]['children'].append(node)
        self.nodes.append(node)
        if tag not in VOID:
            self.stack.append(node)
        else:
            node['end'] = self.byte_offset() + len(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index]['tag'] == tag:
                self.stack[index]['end'] = self.text.find('>', self.byte_offset()) + 1
                del self.stack[index:]
                break

    def handle_data(self, text):
        self.stack[-1]['children'].append(text)


def _nodes(node):
    for child in node['children']:
        if isinstance(child, dict):
            yield child
            yield from _nodes(child)


def _text(node):
    if node['tag'] in IGNORED_TEXT:
        return ''
    return ''.join(child if isinstance(child, str) else _text(child)
                   for child in node['children'])


def message_content(data, source_url):
    """Validate the supported English legacy message layout, returning locators."""
    url = _message_url(source_url)
    if url is None or not data or len(data) > MAX_HTML or b'\x00' in data:
        return None
    page = _HTML(data)
    page.feed(page.text)
    page.close()
    forms = []
    for node in page.nodes:
        attrs = node['attrs']
        if (node['ignored'] or node['tag'] != 'form'
                or attrs.get('name', '').lower() != 'showletter' or not node['end']):
            continue
        action = _message_url(urljoin(source_url, attrs.get('action', '')), require_id=False)
        if action is None or action['host'] != url['host'] or attrs.get('method', '').lower() != 'post':
            return None
        if action['message_id'] not in (None, url['message_id']):
            return None
        ids = [child for child in _nodes(node) if child['tag'] == 'input'
               and child['attrs'].get('name') == 'MsgId'
               and child['attrs'].get('type', '').lower() == 'hidden']
        if len(ids) == 1 and ids[0]['attrs'].get('value') == url['message_id']:
            forms.append((node, ids[0]))
        else:
            return None
    bodies = [node for node in page.nodes if not node['ignored'] and node['tag'] == 'div'
              and node['attrs'].get('id') == 'message' and node['end'] and _text(node).strip()]
    if not forms or len(bodies) != 1:
        return None
    body = bodies[0]
    header_tables = {}
    ambiguous_tables = set()
    for node in page.nodes:
        if node['ignored'] or node['tag'] != 'tr' or node['start'] >= body['start']:
            continue
        cells = [child for child in node['children'] if isinstance(child, dict)
                 and child['tag'] in ('td', 'th')]
        if len(cells) < 2:
            continue
        label = ' '.join(_text(cells[0]).split()).lower()
        # An empty From cell still marks the header layout, but gives no sender.
        if label in ('from:', 'subject:', 'date:') and (label == 'from:' or _text(cells[1]).strip()):
            items = header_tables.setdefault(node['table'], {})
            if label[:-1] in items:
                ambiguous_tables.add(node['table'])
            items[label[:-1]] = {
                'byte_offset': node['start'], 'label': label, 'structure': 'message header table row',
                'value_text_empty': _text(cells[1]) == ''}
    headers = [items for table, items in header_tables.items()
               if table is not None and table not in ambiguous_tables
               and set(items) == {'from', 'subject', 'date'}]
    if len(headers) != 1:
        return None
    return {'message_id': url['message_id'], 'message_form_byte_offset': forms[0][0]['start'],
            'message_id_input_byte_offset': forms[0][1]['start'],
            'message_body_byte_offset': body['start'],
            'message_body_byte_length': body['end'] - body['start'],
            'message_header_locators': headers[0],
            'classification': 'legacy Yahoo message form, matching MsgId, English headers and closed nonempty body'}


def cache_records(data):
    """Select exact directory+filename bindings from allocated normal URL records."""
    from .hacking import msie_url_records
    records = list(msie_url_records(data))  # Validate before returning any observation.
    count = struct.unpack_from('<I', data, 72)[0]
    if not 1 <= count <= 32:
        raise ValueError('IE cache directory table count is unsupported')
    directories = []
    for index in range(count):
        start = 80 + 12 * index
        name = bytes(data[start:start + 8]).decode('ascii')
        if not _component(name):
            raise ValueError('invalid IE cache directory component')
        directories.append(name)
    if len({name.lower() for name in directories}) != count:
        raise ValueError('ambiguous IE cache directory table')
    version47 = data[:28].split(b'\x00', 1)[0] == b'Client UrlCache MMF Ver 4.7'
    directory_field, flags_field = (60, 68) if version47 else (56, 64)
    for record in records:
        if _message_url(record['location']) is None or not _component(record['filename']):
            continue
        offset = record['byte_offset']
        flags = struct.unpack_from('<I', data, offset + flags_field)[0]
        if flags & (0x8 | 0x10000 | 0x100000 | 0x200000):
            continue  # edited, sparse, cookie or history entries
        directory_index = data[offset + directory_field]
        if directory_index >= count:
            raise ValueError('IE URL record has no valid cache directory')
        size = struct.unpack_from('<I' if version47 else '<Q', data, offset + 32)[0]
        yield dict(record, cache_directory=directories[directory_index],
                   cache_directory_index=directory_index, cache_entry_flags=flags,
                   cache_size_bytes=size,
                   cache_directory_locator={'byte_offset': 80 + 12 * directory_index, 'byte_length': 8},
                   cache_directory_index_byte_offset=offset + directory_field)


def extract(ev, paths, ctx):
    """Called by hacking.extract with its file inventory."""
    from .hacking import _path, _read
    by_path = {}
    for path in paths:
        by_path.setdefault(_path(path).lower(), []).append(path)
    for index in paths:
        source = _path(index)
        if (index.name.lower() != 'index.dat' or '\\temporary internet files\\' not in source.lower()
                or index.parent.name.lower() != 'content.ie5'):
            continue
        try:
            data = _read(index)
            records = list(cache_records(data))
            digest = hashlib.sha256(data).hexdigest()
            for record in records:
                expected = index.parent / record['cache_directory'] / record['filename']
                matches = by_path.get(_path(expected).lower(), [])
                if len(matches) != 1:
                    if matches:
                        ev.problem(source, ValueError('ambiguous retained IE cache path'))
                    continue
                path = matches[0]
                content = _read(path)
                if len(content) != record['cache_size_bytes']:
                    ev.problem(_path(path), ValueError('retained cache size differs from its index entry'))
                    continue
                classified = message_content(content, record['location'])
                if classified is None:
                    continue
                content_digest = hashlib.sha256(content).hexdigest()
                provenance = merge_scope(ctx['common'], dict(
                    artifact=source, source_path=_path(path), parser='extractor.yahoo_mail_cache',
                    source_record_type='allocated IE URL record and retained Yahoo message HTML',
                    index_sha256=digest, cache_content_sha256=content_digest, hash_complete=True,
                    cache_path=_path(path), index_path=source, **record, **classified,
                    note='retained message-page cache observation; no ownership, visit, sender authenticity or completeness claim'))
                subject = json.dumps(subject_scope(provenance) +
                                     [source, digest, record['byte_offset'], _path(path), content_digest], separators=(',', ':'))
                # Dissect may return a wchar str subclass; store a plain str.
                emit_attribute(ev, subject, ROLE, str(path.name), ctx['examined_at'], **provenance)
        except Exception as error:
            ev.problem(source, error)
