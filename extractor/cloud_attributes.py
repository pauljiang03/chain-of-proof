"""Typed, bounded observations from retained Google Drive client containers.

Log grammar and snapshot schema references:
https://github.com/log2timeline/plaso/blob/main/plaso/parsers/text_plugins/gdrive_synclog.py
https://github.com/log2timeline/plaso/blob/main/plaso/parsers/sqlite_plugins/gdrive.py

Client log statements are source observations, not successful remote operations,
authentication or personal attribution. Document joins never cross a container
hash, source origin or document ID. Conflicting filenames block the deletion join;
there is no filename fallback, inferred rename or latest-version selection.
The deletion relation requires one unchanged literal name and modified value.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile

from .attributes import emit_attribute
from .source_scope import merge_scope, subject_scope

MAX_FILES = 256
MAX_BYTES = 64 << 20
MAX_TOTAL_BYTES = 128 << 20
MAX_LINES = 200000
MAX_LINE_BYTES = 256 << 10
MAX_RECORDS = 100000
CANDIDATE_PREFIX_BYTES = 4096
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
PREFIX = 'cloud.google_drive.'
HEAD = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d[,.]\d{3}) ([+-])(\d\d)(\d\d) '
                  r'([A-Z]+) pid=(\d+) (\d+):(\S+)\s+(\S+):(\d+) (.*)$')
DOC = r'[A-Za-z0-9_-]{1,256}'
ENTRY = re.compile(r'(?<![\w])(?:Immutable)?CloudEntry\(doc_id=(' + DOC + r'),filename=(.*?),'
                   r'modified=(\d+|None),created=(\d+|None),acl_role=')
DELETE = re.compile(r'WorkerDeleteCloudEvent\(doc_id=(' + DOC + r'), server_mod_time=(\d+)(?=,|\))')
CREDENTIALS = re.compile(r'^Initializing User instance with new credentials\. ([^\s@]+@[^\s@]+)$')
WORKER = re.compile(r'^Worker (starting on|successfully completed) \[(.*)\]$')
SNAPSHOT_SCHEMA = {
    'cloud_entry': {'resource_id', 'filename', 'modified', 'created', 'size', 'doc_type', 'shared', 'checksum', 'url'},
    'cloud_relations': {'parent_resource_id', 'child_resource_id'},
    'local_entry': {'inode_number', 'filename', 'modified', 'checksum', 'size'},
    'local_relations': {'child_inode_number', 'parent_inode_number'},
}


def candidate_kind(prefix):
    """Select possible formats from a bounded prefix, without naming a service."""
    if prefix.startswith(b'SQLite format 3\0'):
        return 'sqlite'
    if re.search(rb'(?m)^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d[,.]\d{3} [+-]\d{4} '
                 rb'[A-Z]+ pid=\d+ \d+:\S+\s+\S+:\d+ ', prefix):
        return 'log'
    return None


def _iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _seconds(value):
    if not re.fullmatch(r'\d{1,12}', value):
        raise ValueError('unsupported server timestamp')
    return _iso(EPOCH + timedelta(seconds=int(value)))


def _calls(text, name):
    """Balanced record spans, respecting quoted Python string literals."""
    pattern = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(name) + r'\(')
    cursor = 0
    while match := pattern.search(text, cursor):
        depth, quote, escaped = 1, None, False
        index = match.end()
        while index < len(text) and depth:
            char = text[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == quote:
                    quote = None
            elif char in "'\"":
                quote = char
            elif char == '(':
                depth += 1
                if depth > 64:
                    raise ValueError('log record nesting bound exceeded')
            elif char == ')':
                depth -= 1
            index += 1
        if depth or quote:
            raise ValueError('unclosed log record')
        yield match.start(), index, text[match.end():index - 1]
        cursor = index


def _worker_fields(body):
    prefix = re.match(r'Direction\.(UPLOAD|DOWNLOAD), Action\.([A-Z_]+), ', body)
    if not prefix:
        raise ValueError('unsupported worker direction/action syntax')
    tail, positions = body[prefix.end():], []
    depth, quote, escaped = 0, None, False
    for index, char in enumerate(tail):
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char in '([{':
            depth += 1
        elif char in ')]}':
            depth -= 1
            if depth < 0:
                raise ValueError('unbalanced worker fields')
        elif depth == 0 and (index == 0 or tail[index - 2:index] == ', '):
            key = re.match(r'([A-Za-z_][A-Za-z_0-9]*)=', tail[index:])
            if key:
                positions.append((index, key.group(1), index + key.end()))
    if quote or depth or not positions or positions[0][0] != 0:
        raise ValueError('unclosed or missing worker fields')
    fields = {}
    for (start, key, value_start), end in zip(positions, [p[0] - 2 for p in positions[1:]] + [len(tail)]):
        if key in fields:
            raise ValueError('duplicate worker field')
        fields[key] = tail[value_start:end]
    if 'name' not in fields:
        raise ValueError('worker record has no explicit filename')
    value = fields['name']
    if value.startswith(("'", '"', "u'", 'u"')):
        value = ast.literal_eval(value)
    elif ',' in value or any(char in value for char in '()[]{}'):
        raise ValueError('ambiguous unquoted worker filename')
    if type(value) is not str or not value or value == 'None' or any(ord(c) < 32 for c in value):
        raise ValueError('worker filename is absent or invalid')
    return prefix.group(1), prefix.group(2), value


def parse_drive_log_bytes(data):
    """Return (records, diagnostics); every locator addresses the original UTF-8 bytes."""
    if not data or len(data) > MAX_BYTES:
        raise ValueError('Google Drive log byte bound exceeded or empty file')
    data.decode('utf-8', errors='strict')  # Reject replacement-decoded identities.
    records, problems, modules, offset = [], [], set(), 0
    for number, raw in enumerate(data.splitlines(keepends=True), 1):
        if number > MAX_LINES or len(raw) > MAX_LINE_BYTES:
            raise ValueError('Google Drive log line bound exceeded')
        text = raw.decode('utf-8').rstrip('\r\n')
        match = HEAD.fullmatch(text)
        locator = {'line': number, 'byte_offset': offset, 'byte_length': len(raw),
                   'line_sha256': hashlib.sha256(raw).hexdigest()}
        offset += len(raw)
        if not match:
            if re.match(r'^\d{4}-\d\d-\d\d ', text):
                raise ValueError(f'malformed timestamped log line {number}')
            continue
        stamp, sign, hours, minutes, level, pid, thread_id, thread, module, source_line, message = match.groups()
        if int(hours) > 23 or int(minutes) > 59:
            raise ValueError(f'invalid UTC offset on line {number}')
        delta = timedelta(hours=int(hours), minutes=int(minutes)) * (-1 if sign == '-' else 1)
        when = datetime.strptime(stamp.replace('.', ','), '%Y-%m-%d %H:%M:%S,%f').replace(tzinfo=timezone(delta))
        locator.update(logger=module, logger_source_line=int(source_line), pid=int(pid),
                       thread_id=int(thread_id), thread=thread, log_level=level,
                       log_recorded_at=_iso(when), printed_utc_offset=sign + hours + minutes)
        def record_locator(start, end):
            return dict(locator, record_byte_offset=locator['byte_offset'] + len(text[:match.start(11)].encode('utf-8'))
                        + len(message[:start].encode('utf-8')),
                        record_byte_length=len(message[start:end].encode('utf-8')))
        modules.add(module)
        if module == 'common.service.user' and (credentials := CREDENTIALS.fullmatch(message)):
            records.append(dict(kind='credentials', locator=locator,
                                fields={PREFIX + 'credentials_account': credentials.group(1),
                                        PREFIX + 'credentials_used_at': _iso(when)}))
        if module == 'common.cloud.cloud_watcher':
            for name in ('CloudEntry', 'ImmutableCloudEntry'):
                for start, end, body in _calls(message, name):
                    full = message[start:end]
                    entry = ENTRY.match(full)
                    if not entry:
                        raise ValueError(f'unsupported cloud entry fields on line {number}')
                    if any(len(re.findall(r'(?:^|,)' + field + '=', body)) != 1
                           for field in ('doc_id', 'filename', 'modified', 'created', 'acl_role')):
                        raise ValueError(f'ambiguous duplicate cloud entry fields on line {number}')
                    doc, filename, modified, created = entry.groups()
                    if (not filename or filename == 'None' or any(ord(c) < 32 for c in filename)
                            or re.search(r',(?:doc_id|filename|modified|created|acl_role)=', filename)):
                        raise ValueError(f'ambiguous cloud filename on line {number}')
                    fields = {PREFIX + 'document_id': doc, PREFIX + 'file_name': filename}
                    if modified != 'None':
                        fields[PREFIX + 'server_modified_at'] = _seconds(modified)
                    records.append(dict(kind='cloud_entry', doc_id=doc, modified=None if modified == 'None' else int(modified),
                                        locator=record_locator(start, end), fields=fields))
            for start, end, body in _calls(message, 'WorkerDeleteCloudEvent'):
                deletion = DELETE.match(message[start:end])
                if not deletion:
                    raise ValueError(f'unsupported cloud deletion fields on line {number}')
                doc, deleted = deletion.groups()
                records.append(dict(kind='server_deletion', doc_id=doc, deleted=int(deleted),
                    locator=record_locator(start, end),
                    fields={PREFIX + 'document_id': doc, PREFIX + 'deletion_record_server_modified_at': _seconds(deleted)}))
        if module == 'common.workers' and (worker := WORKER.fullmatch(message)):
            try:
                calls = list(_calls(worker.group(2), 'ImmutableChange'))
                if not calls:
                    raise ValueError('worker statement has no ImmutableChange')
                pending = []
                previous = 0
                for start, end, body in calls:
                    gap = worker.group(2)[previous:start].strip()
                    if gap != ('' if previous == 0 else ','):
                        raise ValueError('unexpected text between worker records')
                    direction, action, filename = _worker_fields(body)
                    pending.append(dict(kind='worker', locator=record_locator(worker.start(2) + start, worker.start(2) + end),
                        fields={PREFIX + 'worker_stage': 'started' if worker.group(1) == 'starting on' else 'completed',
                                PREFIX + 'worker_direction': direction, PREFIX + 'worker_action': action,
                                PREFIX + 'worker_file_name': filename, PREFIX + 'worker_recorded_at': _iso(when)}))
                    previous = end
                if worker.group(2)[previous:].strip():
                    raise ValueError('unexpected text after worker record')
                records.extend(pending)
            except (ValueError, SyntaxError) as error:
                problems.append(f'line {number}: {error}; worker fields withheld')
        if len(records) > MAX_RECORDS:
            raise ValueError('Google Drive record bound exceeded')
    # The directory layout merely selects candidates. Require the client-specific
    # record syntax and separate client module names before classifying a log.
    recognized = {'common.sync_app', 'common.service.user', 'common.cloud.cloud_watcher', 'common.workers'}
    if not records or len(modules & recognized) < 2:
        raise ValueError('Google Drive client log structure not established')
    records.sort(key=lambda row: row['locator'].get('record_byte_offset', row['locator']['byte_offset']))
    return records, problems


def deletion_relations(records):
    """Join only one unchanged prior name/version for an exact document ID."""
    entries, joined, issues = defaultdict(list), [], []
    for record in records:
        if record['kind'] == 'cloud_entry':
            entries[record['doc_id']].append(record)
        elif record['kind'] == 'server_deletion':
            prior = entries[record['doc_id']]
            names = {row['fields'][PREFIX + 'file_name'] for row in prior}
            versions = {row['modified'] for row in prior}
            if (len(names) != 1 or len(versions) != 1 or None in versions
                    or next(iter(versions), record['deleted'] + 1) > record['deleted']):
                issues.append(f"line {record['locator']['line']}: deletion join withheld: missing prior document entry, "
                              'conflicting filenames/possible rename, multiple versions, or incompatible recorded modified time')
                continue
            joined.append(dict(kind='deleted_document', doc_id=record['doc_id'],
                locator=record['locator'], fields=dict(prior[0]['fields'], **record['fields']),
                related_locators=[row['locator'] for row in prior],
                identity_rule='same scoped container hash and exact document ID; one literal prior filename; '
                              'one unchanged recorded modified value not after deletion-record server_mod_time; '
                              'not actual deletion time, a complete history or an inferred rename'))
    return joined, issues


def classify_snapshot_sqlite(data):
    """Validate the documented snapshot schema; unrelated SQLite remains unknown."""
    if not data.startswith(b'SQLite format 3\0') or len(data) > MAX_BYTES:
        raise ValueError('not a bounded SQLite container')
    with tempfile.TemporaryDirectory(prefix='conan-drive-sqlite-') as directory:
        path = Path(directory) / 'snapshot'
        path.write_bytes(data)
        db = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
        try:
            remaining = [2000]
            def progress():
                remaining[0] -= 1
                return int(remaining[0] <= 0)
            db.set_progress_handler(progress, 1000)
            db.execute('PRAGMA query_only=ON')
            db.execute('PRAGMA trusted_schema=OFF')
            if db.execute('PRAGMA quick_check(1)').fetchall() != [('ok',)]:
                raise ValueError('SQLite quick_check failed')
            tables = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'").fetchmany(257))
            if len(tables) > 256:
                raise ValueError('SQLite table bound exceeded')
            for table, columns in SNAPSHOT_SCHEMA.items():
                if table not in tables or not str(tables[table]).upper().startswith('CREATE TABLE'):
                    raise ValueError('Google Drive snapshot table missing or not an ordinary table')
                actual = {row[1] for row in db.execute('PRAGMA table_info("' + table + '")')}
                if not columns <= actual:
                    raise ValueError('Google Drive snapshot columns missing')
                db.execute('SELECT * FROM "' + table + '" LIMIT 1').fetchone()
            return {'format': 'Google Drive snapshot SQLite database', 'validated_tables': sorted(SNAPSHOT_SCHEMA),
                    'validation': 'SQLite quick_check, ordinary required tables/columns and first-row decode',
                    'wal_policy': 'retained base database only; no WAL replay or current-state inference'}
        finally:
            db.close()


def _read(path):
    size = path.stat().st_size
    if not 0 < size <= MAX_BYTES:
        raise ValueError('cloud container size bound exceeded or empty file')
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) != size:
        raise ValueError('cloud container size changed while reading')
    return data


def _allocation(target, source):
    """Read the exact container's NTFS flag; pathname presence is insufficient."""
    if target is None or not re.match(r'^[A-Za-z]:\\', source):
        return None
    mounts = {str(name).lower(): fs for name, fs in target.fs.mounts.items()}
    fs = mounts.get(source[:2].lower())
    ntfs = getattr(fs, 'ntfs', None)
    if ntfs is None:
        return None
    relative = source[3:]
    record = ntfs.mft.get(relative)
    if not record.is_file() or record.is_reparse_point():
        raise ValueError('cloud container NTFS record is not a regular file')
    if relative.casefold() not in {str(path).casefold() for path in record.full_paths()}:
        raise ValueError('cloud container NTFS record path does not match')
    return not bool(int(record.header.Flags) & 1), dict(mft_segment=int(record.segment),
        mft_sequence=int(record.header.SequenceNumber), allocation_field='MFT FILE record header in-use flag')


def extract_paths(ev, paths, ctx, *, target=None):
    """Validate and emit independent container/record/related-document subjects."""
    from .artifact_containers import _windows_path
    total, seen = 0, set()
    for number, path in enumerate(paths, 1):
        if number > MAX_FILES:
            raise ValueError('cloud candidate file bound exceeded')
        source = _windows_path(target, path) if target is not None else str(path).replace('/', '\\')
        if source.casefold() in seen:
            continue
        seen.add(source.casefold())
        try:
            if path.is_symlink():
                raise ValueError('cloud container symlink is not a direct source file')
            if total + path.stat().st_size > MAX_TOTAL_BYTES:
                raise ValueError('cloud aggregate byte bound exceeded before read')
            data = _read(path)
            total += len(data)
            digest = hashlib.sha256(data).hexdigest()
            records, issues = [], []
            wal_details, additional_identity = {}, []
            if data.startswith(b'SQLite format 3\0'):
                view = data
                wal_path = path.with_name(str(path.name) + '-wal')
                if wal_path.exists():
                    if wal_path.is_symlink() or total + wal_path.stat().st_size > MAX_TOTAL_BYTES:
                        raise ValueError('adjacent SQLite WAL is a symlink or exceeds byte budget')
                    wal = _read(wal_path) if wal_path.stat().st_size else b''
                    total += len(wal)
                    from .sqlite_wal import committed_view
                    view, wal_details = committed_view(data, wal)
                    wal_details.update(sqlite_wal_path=str(wal_path).replace('/', '\\'),
                                       sqlite_wal_source_scope=merge_scope(ctx['common']))
                    additional_identity = [wal_details['sqlite_wal_sha256'], wal_details['sqlite_view_sha256']]
                validation = classify_snapshot_sqlite(view)
                if wal_details:
                    validation['wal_policy'] = wal_details['wal_policy']
            else:
                records, issues = parse_drive_log_bytes(data)
                validation = {'format': 'Google Drive sync log', 'validation': 'strict UTF-8; offset-bearing log headers; '
                              'client-specific record grammar and multiple client modules'}
            scope = merge_scope(ctx['common'])
            base = subject_scope(scope) + [source, digest] + additional_identity
            provenance = dict(scope, artifact=source, source_path=source, parser='extractor.cloud_attributes',
                              container_sha256=digest, container_bytes=len(data), hash_complete=True,
                              service='Google Drive', container_validation=validation, **wal_details)
            def emit(fields, suffix, details):
                subject = json.dumps(base + suffix, separators=(',', ':'), ensure_ascii=True)
                for role, value in fields.items():
                    emit_attribute(ev, subject, role, value, ctx['examined_at'],
                                   **dict(provenance, **details, source_field=role))
            container_fields = {'cloud.container.service': 'Google Drive',
                                'cloud.container.type': validation['format'], 'cloud.container.path': source}
            details = {}
            try:
                allocation = _allocation(target, source)
                if allocation is not None:
                    container_fields['filesystem.deleted_flag'], details = allocation
            except Exception as error:
                ev.problem(source + ': allocation metadata', error)
            emit(container_fields, ['container'], details)
            joined, join_issues = deletion_relations(records)
            for issue in issues + join_issues:
                ev.problem(source, ValueError(issue))
            for record in records + joined:
                suffix = [record['kind'], record.get('doc_id'), record['locator']['line'],
                          record['locator'].get('record_byte_offset', record['locator']['byte_offset'])]
                details = {key: value for key, value in record.items()
                           if key not in ('fields', 'kind', 'doc_id', 'modified', 'deleted')}
                details['observation_kind'] = record['kind']
                emit(record['fields'], suffix, details)
        except Exception as error:
            ev.problem(source, error)


def extract(ev, target, ctx):
    """Inspect bounded client profile folders; layout selects, content classifies."""
    from .webcloud import _users
    paths, folders = [], 0
    counts = dict(scanned_files=0, selected_files=0, unrecognized_files=0, skipped_sidecars=0,
                  skipped_symlinks=0, prefix_bytes=CANDIDATE_PREFIX_BYTES,
                  scope='Google Drive candidate profile folders to depth three; prefix selection is not service absence')
    for _, home in _users(target):
        top = home.joinpath('AppData/Local/Google/Drive')
        if not top.exists():
            continue
        pending = [(top, 0)]
        while pending:
            folder, depth = pending.pop()
            folders += 1
            if folders > MAX_FILES:
                raise ValueError('cloud candidate folder bound exceeded')
            for path in sorted(folder.iterdir(), key=str):
                if path.is_symlink():
                    counts['skipped_symlinks'] += 1
                    continue
                if path.is_dir() and depth < 3:
                    pending.append((path, depth + 1))
                elif path.is_file():
                    if str(path.name).endswith(('-wal', '-shm', '-journal')):
                        counts['skipped_sidecars'] += 1
                        continue
                    counts['scanned_files'] += 1
                    if counts['scanned_files'] > MAX_FILES:
                        raise ValueError('cloud candidate file bound exceeded')
                    try:
                        with path.open('rb') as stream:
                            prefix = stream.read(CANDIDATE_PREFIX_BYTES)
                    except Exception as error:
                        ev.problem(str(path), error)
                        continue
                    if candidate_kind(prefix) is None:
                        counts['unrecognized_files'] += 1
                    else:
                        paths.append(path)
                        counts['selected_files'] += 1
    extract_paths(ev, paths, ctx, target=target)
    return counts
