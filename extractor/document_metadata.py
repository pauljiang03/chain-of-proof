"""Bounded OOXML core-property observations from concrete Windows user files.

The reader checks package relationships, content types and XML roots. It does not
execute documents, extract archives to disk, infer authorship, or turn document
properties into filesystem times. Other formats remain unsupported.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from collections import deque
from xml.etree import ElementTree as ET

from .attributes import emit_attribute
from .inventory import _win
from .profiles import user_profiles
from .source_scope import merge_scope, subject_scope

MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_XML_BYTES = 2 * 1024 * 1024
MAX_PROPERTY_BYTES = 64 * 1024
MAX_ZIP_ENTRIES = 4096
MAX_FILES = 1024
MAX_DIRECTORY_ENTRIES = 20000
MAX_DEPTH = 16
USER_FOLDERS = ('Desktop', 'Documents', 'My Documents', 'Downloads')
EXTENSIONS = ('.docx', '.docm', '.xlsx', '.xlsm', '.pptx', '.pptm')
REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
TYPE_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
CORE_NS = 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
DC_NS = 'http://purl.org/dc/elements/1.1/'
DCTERMS_NS = 'http://purl.org/dc/terms/'
OFFICE_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument'
CORE_REL = REL_NS + '/metadata/core-properties'
CORE_TYPE = 'application/vnd.openxmlformats-package.core-properties+xml'
MAIN_TYPES = {
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml':
        ('WordprocessingML', '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document'),
    'application/vnd.ms-word.document.macroEnabled.main+xml':
        ('WordprocessingML', '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml':
        ('SpreadsheetML', '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}workbook'),
    'application/vnd.ms-excel.sheet.macroEnabled.main+xml':
        ('SpreadsheetML', '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}workbook'),
    'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml':
        ('PresentationML', '{http://schemas.openxmlformats.org/presentationml/2006/main}presentation'),
    'application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml':
        ('PresentationML', '{http://schemas.openxmlformats.org/presentationml/2006/main}presentation'),
}
CORE_FIELDS = {
    '{' + DC_NS + '}title': 'document.core.title',
    '{' + DC_NS + '}subject': 'document.core.subject',
    '{' + DC_NS + '}creator': 'document.core.creator',
    '{' + CORE_NS + '}lastModifiedBy': 'document.core.last_modified_by',
    '{' + DC_NS + '}description': 'document.core.description',
    '{' + CORE_NS + '}keywords': 'document.core.keywords',
    '{' + DCTERMS_NS + '}created': 'document.core.created',
    '{' + DCTERMS_NS + '}modified': 'document.core.modified',
}


def _part_name(raw):
    if not isinstance(raw, str) or not raw or any(c in raw for c in '\\:%?#\x00'):
        raise ValueError('unsupported or nonlocal package part name')
    value = raw[1:] if raw.startswith('/') else raw
    if not value or any(piece in ('', '.', '..') for piece in value.split('/')):
        raise ValueError('ambiguous package part name')
    return value


def parse_ooxml(data):
    """Return literal reviewed properties after bounded package validation."""
    if not isinstance(data, bytes) or len(data) > MAX_FILE_BYTES:
        raise ValueError('document exceeds the byte limit')
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        entries = package.infolist()
        if len(entries) > MAX_ZIP_ENTRIES:
            raise ValueError('too many package entries')
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError('duplicate package entry names')
        for entry in entries:
            _part_name(entry.filename.rstrip('/'))
            if entry.flag_bits & 1:
                raise ValueError('encrypted package entries are unsupported')

        def xml(name):
            entry = package.getinfo(name)
            if entry.file_size > MAX_XML_BYTES:
                raise ValueError('XML part exceeds the byte limit: ' + name)
            with package.open(entry) as stream:
                blob = stream.read(MAX_XML_BYTES + 1)
            if len(blob) != entry.file_size or len(blob) > MAX_XML_BYTES:
                raise ValueError('XML part length mismatch: ' + name)
            # Decode before checking declarations so UTF-16 cannot hide a DTD.
            if blob.startswith((b'\xff\xfe', b'\xfe\xff')) or b'\x00' in blob[:100]:
                text = blob.decode('utf-16')
            else:
                text = blob.decode('utf-8-sig')
            if re.search(r'<!\s*(DOCTYPE|ENTITY)\b', text, re.I):
                raise ValueError('DTD/entity declarations are unsupported')
            return ET.fromstring(text), hashlib.sha256(blob).hexdigest()

        types, _ = xml('[Content_Types].xml')
        relations, _ = xml('_rels/.rels')
        if types.tag != '{' + TYPE_NS + '}Types' or relations.tag != '{' + REL_NS + '}Relationships':
            raise ValueError('invalid package content-types or relationships root')
        overrides, defaults = {}, {}
        for item in types:
            if item.tag == '{' + TYPE_NS + '}Override':
                key, target = _part_name(item.get('PartName')), overrides
            elif item.tag == '{' + TYPE_NS + '}Default':
                key, target = item.get('Extension'), defaults
                if not isinstance(key, str) or not key or '.' in key:
                    raise ValueError('invalid default content-type extension')
            else:
                raise ValueError('unsupported content-type declaration')
            if key in target or not item.get('ContentType'):
                raise ValueError('duplicate or invalid content-type declaration')
            target[key] = item.get('ContentType')

        def content_type(name):
            return overrides.get(name, defaults.get(name.rsplit('.', 1)[-1]))

        targets, identifiers = {}, set()
        for relation in relations:
            if relation.tag != '{' + REL_NS + '}Relationship':
                raise ValueError('invalid relationship element')
            identifier = relation.get('Id')
            if not identifier or identifier in identifiers:
                raise ValueError('missing or duplicate relationship ID')
            identifiers.add(identifier)
            kind = relation.get('Type')
            if kind not in (OFFICE_REL, CORE_REL):
                continue
            if kind in targets or relation.get('TargetMode', 'Internal') != 'Internal':
                raise ValueError('ambiguous or external document/core relationship')
            targets[kind] = _part_name(relation.get('Target'))
        main = targets.get(OFFICE_REL)
        if main is None or content_type(main) not in MAIN_TYPES:
            raise ValueError('no supported office-document relationship and content type')
        format_name, expected_root = MAIN_TYPES[content_type(main)]
        main_root, main_sha = xml(main)
        if main_root.tag != expected_root:
            raise ValueError('main XML root does not match its content type')
        result = {'format': format_name, 'main_part': main, 'main_part_sha256': main_sha,
                  'core_part': None, 'core_part_sha256': None, 'properties': []}
        core = targets.get(CORE_REL)
        if core is None:
            return result
        if content_type(core) != CORE_TYPE:
            raise ValueError('core-property content type is not declared')
        root, core_sha = xml(core)
        if root.tag != '{' + CORE_NS + '}coreProperties':
            raise ValueError('invalid core-property XML root')
        result.update(core_part=core, core_part_sha256=core_sha)
        seen = set()
        for field in root:
            if field.tag not in CORE_FIELDS:
                continue
            if field.tag in seen or len(field):
                raise ValueError('duplicate or nested core-property value')
            seen.add(field.tag)
            value = field.text or ''
            if len(value.encode('utf-8')) > MAX_PROPERTY_BYTES:
                raise ValueError('core-property value exceeds the byte limit')
            result['properties'].append((CORE_FIELDS[field.tag], value, field.tag))
        return result


def candidates(ev, target):
    queue, seen = deque(), set()
    for profile in user_profiles(target):
        for folder in USER_FOLDERS:
            path = profile.joinpath(folder)
            if path.exists():
                queue.append((path, 0))
    entries = 0
    while queue:
        directory, depth = queue.popleft()
        try:
            if directory.is_symlink() or not directory.is_dir():
                continue
            directory = directory.resolve(strict=True)
            identity = _win(directory).casefold()
            if identity in seen:
                continue
            seen.add(identity)
            children = []
            for path in directory.iterdir():
                entries += 1
                if entries > MAX_DIRECTORY_ENTRIES:
                    raise ValueError('document enumeration entry limit reached')
                children.append(path)
            for path in sorted(children, key=lambda p: (_win(p).casefold(), _win(p))):
                if path.is_symlink():
                    continue
                if path.is_dir():
                    if depth >= MAX_DEPTH:
                        ev.problem('document metadata directory ' + _win(path), ValueError('depth limit reached'))
                    else:
                        queue.append((path, depth + 1))
                elif path.is_file() and path.name.casefold().endswith(EXTENSIONS):
                    yield path
        except Exception as error:
            ev.problem('document metadata directory ' + _win(directory), error)
            if entries > MAX_DIRECTORY_ENTRIES:
                return


def extract(ev, target, ctx):
    total, seen = 0, set()
    for path in candidates(ev, target):
        try:
            path = path.resolve(strict=True)
            source = _win(path)
            if source.casefold() in seen:
                continue
            if len(seen) >= MAX_FILES:
                raise ValueError('document file limit reached')
            seen.add(source.casefold())
            recorded_size = path.lstat().st_size
            if isinstance(recorded_size, bool) or not isinstance(recorded_size, int) or recorded_size < 0:
                raise ValueError('invalid recorded document size')
            allowed = min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total)
            if recorded_size > allowed:
                raise ValueError('document exceeds file or total byte limit')
            with path.open('rb') as stream:
                data = stream.read(allowed + 1)
            total += len(data)
            if len(data) != recorded_size or len(data) > allowed:
                raise ValueError('document size changed or exceeds byte limit')
            parsed = parse_ooxml(data)
            sha256 = hashlib.sha256(data).hexdigest()
            provenance = merge_scope(ctx['common'], {
                'reader': 'document_metadata', 'artifact': source, 'source_path': source,
                'container_sha256': sha256, 'container_bytes': len(data),
                'validation': 'package relationships, declared content types and parsed XML roots',
                'main_part': parsed['main_part'], 'main_part_sha256': parsed['main_part_sha256'],
                'core_part': parsed['core_part'], 'core_part_sha256': parsed['core_part_sha256'],
                'limitation': 'literal package properties; not verified authorship or filesystem/event times',
            })
            subject = json.dumps(subject_scope(provenance) + [source, sha256], separators=(',', ':'), ensure_ascii=True)
            emit_attribute(ev, subject, 'document.container.path', source, ctx['examined_at'], **provenance)
            emit_attribute(ev, subject, 'document.container.format', parsed['format'], ctx['examined_at'], **provenance)
            for role, value, tag in parsed['properties']:
                emit_attribute(ev, subject, role, value, ctx['examined_at'],
                               xml_field=tag, property_part=parsed['core_part'], **provenance)
        except Exception as error:
            ev.problem('document metadata ' + _win(path), error)
            if len(seen) >= MAX_FILES or total >= MAX_TOTAL_BYTES:
                break
