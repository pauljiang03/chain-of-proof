"""Validated browser, mail, thumbnail and Sticky Notes containers and their literal text."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import tempfile

from .attributes import emit_attribute
from .inventory import candidates as inventory_candidates, _children, _homes, _win
from .source_scope import merge_scope, subject_scope
from .webcloud import mshist_days, split_history_url

MAX_FILES = 1024
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_RECORDS = 20000
MAX_FOLDERS = 4096
MAX_DEPTH = 32
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_MAIL_TEXT_BYTES = 32 * 1024 * 1024
MAX_NOTE_TEXT_BYTES = 32 * 1024 * 1024
MAX_PARSE_READS = 200000
CHUNK = 1024 * 1024

BROWSER_LAYOUTS = (
    ('AppData/Local/Google/Chrome/User Data', 'History', 'chromium', 'Google Chrome'),
    ('AppData/Local/Microsoft/Edge/User Data', 'History', 'chromium', 'Microsoft Edge'),
    ('AppData/Local/BraveSoftware/Brave-Browser/User Data', 'History', 'chromium', 'Brave'),
    ('AppData/Roaming/Mozilla/Firefox/Profiles', 'places.sqlite', 'firefox', 'Mozilla Firefox'),
)
PATH_ROLES = {'chromium': 'browser.history.path', 'firefox': 'browser.history.path',
              'ie_webcache': 'browser.history.path', 'ie_legacy_history': 'browser.history.path',
              'outlook_mailbox': 'mail.store.path',
              'thumbnail_cache': 'thumbcache.container.path', 'sticky_notes': 'sticky_notes.container.path'}


def _windows_path(target, path):
    """Map a mount to its drive letter only when exactly one drive mount is the same filesystem."""
    rendered = _win(path)
    if re.match(r'^[A-Za-z]:\\', rendered) or re.match(r'^\\\\[^\\]+\\[^\\]+(?:\\|$)', rendered):
        return rendered
    alias, separator, relative = str(path).replace('\\', '/').lstrip('/').partition('/')
    mounts = {str(name).casefold(): filesystem for name, filesystem in target.fs.mounts.items()}
    filesystem = mounts.get(alias.casefold())
    drives = [name.upper() for name, mounted in mounts.items()
              if re.fullmatch(r'[a-z]:', name) and mounted is filesystem]
    if not separator or filesystem is None or len(drives) != 1:
        raise ValueError('virtual container path has no unique concrete Windows drive mapping')
    return drives[0] + '\\' + relative.replace('/', '\\')


class ParseBytes(io.BytesIO):
    """Limit parser I/O and refuse pointers outside the captured byte snapshot."""
    def __init__(self, data):
        super().__init__(data)
        self.length, self.calls, self.read_bytes = len(data), 0, 0

    def seek(self, offset, whence=0):
        position = offset if whence == 0 else self.tell() + offset if whence == 1 else self.length + offset
        if whence not in (0, 1, 2) or not 0 <= position <= self.length:
            raise ValueError('container parser seek is outside captured bytes')
        return super().seek(position)

    def read(self, size=-1):
        self.calls += 1
        if self.calls > MAX_PARSE_READS:
            raise ValueError('container parser read-operation budget exceeded')
        if size is None or size < 0:
            size = self.length - self.tell()
        if size > self.length:
            raise ValueError('container parser requested more than the captured length')
        self.read_bytes += min(size, self.length - self.tell())
        if self.read_bytes > max(CHUNK, 16 * self.length):
            raise ValueError('container parser byte budget exceeded')
        return super().read(size)


def candidates(ev, target):
    for path, category, home in inventory_candidates(ev, target):
        if category in ('outlook_mailbox', 'thumbnail_cache', 'sticky_notes'):
            yield path, category, None, home
    drives = sorted({str(m).upper() for m in target.fs.mounts if re.fullmatch(r'[A-Za-z]:', str(m))})
    for home in _homes(ev, target, drives):
        for layout, basename, family, browser in BROWSER_LAYOUTS:
            for profile in _children(ev, home.joinpath(layout)):
                if profile.is_dir() and not profile.is_symlink():
                    path = profile.joinpath(basename)
                    if path.exists():
                        yield path, family, browser, home
        path = home.joinpath('AppData/Local/Microsoft/Windows/WebCache/WebCacheV01.dat')
        if path.exists():
            yield path, 'ie_webcache', 'Internet Explorer', home
        for layout in ('Local Settings/History/History.IE5',
                       'AppData/Local/Microsoft/Windows/History/History.IE5',
                       'AppData/Local/Microsoft/Windows/History/Low/History.IE5'):
            top = home.joinpath(layout)
            path = top.joinpath('index.dat')
            if path.exists():
                yield path, 'ie_legacy_history', 'Internet Explorer', home
            for dated in _children(ev, top):
                if dated.is_dir() and not dated.is_symlink() and mshist_days(dated.name) is not None:
                    path = dated.joinpath('index.dat')
                    if path.exists():
                        yield path, 'ie_legacy_history', 'Internet Explorer', home


def _read(path, size, budget):
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_FILE_BYTES:
        raise ValueError('container size is empty, invalid, or exceeds per-file limit')
    if size > MAX_TOTAL_BYTES - budget[0]:
        raise ValueError('container exceeds remaining total read budget')
    chunks, count = [], 0
    with path.open('rb') as stream:
        while True:
            chunk = stream.read(min(CHUNK, size - count + 1))
            if not chunk:
                break
            count += len(chunk)
            budget[0] += len(chunk)
            if count > size or budget[0] > MAX_TOTAL_BYTES:
                raise ValueError('container bytes exceed recorded size or total read budget')
            chunks.append(chunk)
    if count != size:
        raise ValueError('container bytes do not match recorded file size')
    return b''.join(chunks)


def _integer(value):
    """Accept parser int subclasses as plain ints, but reject bools."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError('decoded nonnegative integer is required')
    return int(value)


def _sqlite(data, family, *, with_notes=False, view_provenance=None):
    # A WAL-merged copy has its own sqlite_view_sha256; container_sha256 stays the captured file.
    with tempfile.TemporaryDirectory(prefix='cop-container-') as directory:
        path = Path(directory) / 'container.sqlite'
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
                raise ValueError('SQLite integrity check did not pass')
            tables = {row[0].casefold(): row[0] for row in
                      db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchmany(257)}
            if len(tables) > 256:
                raise ValueError('SQLite table budget exceeded')
            required = {
                'chromium': {'urls': {'id', 'url'}, 'visits': {'id', 'url', 'visit_time'}},
                'firefox': {'moz_places': {'id', 'url'}, 'moz_historyvisits': {'id', 'place_id', 'visit_date'}},
                # Published schema: SQLECmd Windows_MicrosoftStickyNotes_NotesDB.smap.
                'sticky_notes': {'note': {'id', 'text', 'createdat', 'updatedat'},
                                 'media': set(), 'insight': set(), 'user': set(), 'stroke': set()},
            }[family]
            for table, columns in required.items():
                if table not in tables:
                    raise ValueError('required container table is missing: ' + table)
                quoted = '"' + tables[table].replace('"', '""') + '"'
                actual = {row[1].casefold() for row in db.execute('PRAGMA table_info(' + quoted + ')')}
                if not columns <= actual:
                    raise ValueError('required container columns are missing: ' + table)
                db.execute('SELECT * FROM ' + quoted + ' LIMIT 1').fetchone()
            validation = {'parser': 'sqlite3', 'format': family + '_sqlite',
                          'validation': 'read-only SQLite quick_check, required table/column schema and first-row decoding',
                          'validated_tables': sorted(required), 'wal_policy': 'base database bytes only; WAL not replayed'}
            validation.update(view_provenance or {})
            return (validation, _sticky_sqlite_rows(db)) if with_notes else validation
        finally:
            db.close()


def _ese(data):
    from dissect.database.ese import ESE
    db = ESE(ParseBytes(data))
    table = db.table('Containers')
    if not {'ContainerId', 'Name', 'Directory'} <= set(table.column_names):
        raise ValueError('WebCache Containers schema is missing')
    found = []
    for index, row in enumerate(table.records()):
        if index >= MAX_RECORDS:
            raise ValueError('WebCache container record budget exceeded')
        name = row.get('Name')
        name = name.rstrip('\0') if isinstance(name, str) else ''
        if name != 'History' and mshist_days(name) is None:
            continue
        cid = _integer(row.get('ContainerId'))
        history = db.table('Container_' + str(cid))
        if not {'EntryId', 'Url'} <= set(history.column_names):
            raise ValueError('WebCache history table schema is missing')
        next(iter(history.records()), None)
        found.append(str(cid))
    if not found:
        raise ValueError('no structurally validated WebCache history container')
    return {'parser': 'dissect.database.ese', 'format': 'wininet_webcache_history',
            'validation': 'ESE catalog and Containers/history table schemas decoded', 'history_container_ids': found}


def _legacy_history(data):
    from .hacking import msie_url_records
    count, history = 0, 0
    for row in msie_url_records(data):
        count += 1
        if count > MAX_RECORDS:
            raise ValueError('legacy history record budget exceeded')
        parsed = split_history_url(row['location'])
        if parsed is None:
            continue
        prefix, _user, url = parsed
        if (prefix == 'Visited:' or re.fullmatch(r':\d{16}:', prefix)) and re.match(r'^(?:https?|ftp|file)://', url, re.I):
            history += 1
    if not history:
        raise ValueError('index.dat has no allocated URL record with an explicit history prefix')
    return {'parser': 'extractor.hacking.msie_url_records', 'format': 'ie_legacy_history',
            'records_validated': count, 'history_records_validated': history,
            'validation': 'versioned index.dat header, allocated record blocks and bounded strings; explicit Visited/daily-history prefix; generic cache records are insufficient'}


def _thumbcache(data):
    from dissect.thumbcache.thumbcache_file import ThumbcacheFile, ThumbcacheEntry
    from dissect.thumbcache.index import ThumbnailIndex
    stream = ParseBytes(data)
    if data[:4] != b'CMMM':
        index = ThumbnailIndex(stream)
        version = index.type
        total, used = int(index.total_entries), int(index.used_entries)
        if not 0 <= used <= total <= MAX_RECORDS:
            raise ValueError('thumbnail index count bounds failed')
        actual = sum(1 for _entry in index.entries())
        if actual != used:
            raise ValueError('thumbnail index used-entry count differs from decoded entries')
        return {'parser': 'dissect.thumbcache', 'format': 'thumbcache_index',
                'version': int(version), 'records_validated': total,
                'validation': 'known index version, bounded declared entries decoded, used-entry count checked'}
    cache = ThumbcacheFile(stream)
    version = cache.version
    start, end = int(cache.header.Offset), int(cache.header.Size)
    if not len(cache.header) <= start <= end <= len(data):
        raise ValueError('thumbnail cache entry region is outside captured bytes')
    offset, count, empty_slots = start, 0, []
    while offset < end:
        if count >= MAX_RECORDS or end - offset < 32:
            raise ValueError('thumbnail cache entry bounds or record budget failed')
        stream.seek(offset)
        entry = ThumbcacheEntry(stream, version)
        size = int(entry._header.Size)
        consumed = stream.tell() - offset
        if (size < 48 or size != consumed or offset + size > end
                or int(entry._header.IdentifierSize) % 2
                or int(entry._header.PaddingSize) > len(entry._data)):
            raise ValueError('thumbnail cache entry lengths do not match captured bytes')
        # A zero hash marks an empty slot; any bytes left in it are not a thumbnail.
        # Format: https://github.com/thumbcacheviewer/thumbcacheviewer/blob/master/thumbcache_viewer_cmd/thumbcache_viewer_cmd.cpp
        empty = (int(entry.hash, 16) == 0 and int(entry._header.IdentifierSize) == 0
                 and int(entry._header.PaddingSize) == 0 and int(entry._header.DataSize) == 0
                 and entry.data_checksum == bytes(8))
        if empty:
            empty_slots.append({'byte_offset': offset, 'slot_bytes': size,
                                'uninterpreted_bytes': len(entry.data),
                                'uninterpreted_sha256': hashlib.sha256(entry.data).hexdigest()})
        elif int(entry._header.DataSize) != len(entry.data):
            raise ValueError('thumbnail cache entry lengths do not match captured bytes')
        offset += size
        count += 1
    return {'parser': 'dissect.thumbcache', 'format': 'thumbcache_database',
            'version': int(version), 'records_validated': count,
            'empty_slot_count': len(empty_slots), 'empty_slot_samples': empty_slots[:16],
            'empty_slot_samples_omitted': max(0, len(empty_slots) - 16),
            'uninterpreted_slot_bytes': sum(slot['uninterpreted_bytes'] for slot in empty_slots),
            'validation': 'known cache version, bounded entry region and every entry header/length decoded; '
                          'nonempty payload lengths checked; zero-hash empty-slot residual bytes not interpreted'}


def _sticky_sqlite_rows(db):
    """Note.Text values; duplicate note IDs raise before anything is emitted."""
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_TEXT_BYTES + 4096)
    columns = {row[1].casefold() for row in db.execute('PRAGMA table_info("Note")')}
    if columns & {'rowid', '_rowid_', 'oid'}:
        raise ValueError('Sticky Notes row identifier is shadowed by a declared column')
    notes, seen, total = [], set(), 0
    for rowid, note_id, text in db.execute('SELECT _rowid_, Id, Text FROM Note ORDER BY _rowid_'):
        if len(notes) >= MAX_RECORDS:
            raise ValueError('Sticky Notes record budget exceeded')
        if not isinstance(note_id, str) or not note_id or len(note_id) > 1024 or '\0' in note_id:
            raise ValueError('Sticky Notes row has no bounded text identity')
        note_id.encode('utf-8', errors='strict')
        if note_id.casefold() in seen:
            raise ValueError('duplicate Sticky Notes Note.Id rows are ambiguous')
        seen.add(note_id.casefold())
        if not isinstance(text, str) or '\0' in text:
            raise ValueError('Sticky Notes Note.Text is not a literal Unicode string')
        size = len(text.encode('utf-8', errors='strict'))
        total += size
        if size > MAX_TEXT_BYTES or total > MAX_NOTE_TEXT_BYTES:
            raise ValueError('Sticky Notes text budget exceeded')
        notes.append(dict(text=text, note_locator={'table': 'Note', 'rowid': rowid, 'id': note_id},
                          source_field='Note.Text', text_byte_length=size,
                          text_encoding='SQLite Unicode text (UTF-8 byte length)'))
    return notes


def _ole_children(parent):
    """Direct directory children only, with bounded sibling trees and unique names."""
    pending = [parent.child] if parent.has_child else []
    seen, names, entries = set(), set(), {}
    while pending:
        entry = pending.pop()
        if entry.sid in seen or len(seen) >= MAX_RECORDS:
            raise ValueError('OLE directory sibling cycle or entry budget exceeded')
        seen.add(entry.sid)
        if entry.name.casefold() in names:
            raise ValueError('duplicate OLE directory names are ambiguous')
        names.add(entry.name.casefold())
        entries[entry.name] = entry
        if entry.has_left_sibling:
            pending.append(entry.left_sibling)
        if entry.has_right_sibling:
            pending.append(entry.right_sibling)
    return entries


def _sticky_ole(data, *, with_notes=False):
    from dissect.ole import OLE
    ole = OLE(ParseBytes(data))
    entries = _ole_children(ole.root)
    if len(entries) > MAX_RECORDS or not {'Version', 'Metafile'} <= set(entries):
        raise ValueError('Sticky Notes root stream layout is absent or too large')
    if not all(entries[name].is_stream for name in ('Version', 'Metafile')):
        raise ValueError('Sticky Notes root fields must be streams')
    version = entries['Version'].open().read(65)
    if not 1 <= len(version) <= 64:
        raise ValueError('Sticky Notes version stream is absent or too large')
    notes, total = [], 0
    for name, entry in entries.items():
        if not entry.is_storage:
            continue
        if not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F-]+', name):
            raise ValueError('unrecognized Sticky Notes storage identifier')
        streams = _ole_children(entry)
        if not {'0', '3'} <= set(streams) or not all(streams[n].is_stream for n in ('0', '3')):
            raise ValueError('Sticky Notes storage lacks paired rich/Unicode text streams')
        rich = streams['0'].open().read(MAX_TEXT_BYTES + 1)
        text = streams['3'].open().read(MAX_TEXT_BYTES + 1)
        if (len(rich) > MAX_TEXT_BYTES or len(text) > MAX_TEXT_BYTES or len(text) % 2
                or not re.match(rb'^\{\\rtf\d', rich) or not rich.rstrip(b'\0\r\n ').endswith(b'}')):
            raise ValueError('Sticky Notes text streams failed bounded format checks')
        value = text.decode('utf-16-le', errors='strict')
        if value.endswith('\0'):
            value = value[:-1]  # drop only the one NUL terminator
        if '\0' in value:
            raise ValueError('Sticky Notes Unicode stream has an embedded NUL')
        total += len(text)
        if total > MAX_NOTE_TEXT_BYTES:
            raise ValueError('Sticky Notes aggregate text budget exceeded')
        notes.append(dict(text=value, note_locator={'storage': name, 'storage_sid': int(entry.sid),
                                                   'stream': '3', 'stream_sid': int(streams['3'].sid)},
                          source_field='OLE note storage Unicode stream 3', text_byte_length=len(text),
                          text_encoding='UTF-16LE; at most one framing terminator removed'))
    if not notes:
        raise ValueError('empty OLE storage does not establish Sticky Notes subtype')
    validation = {'parser': 'dissect.ole', 'format': 'sticky_notes_snt', 'records_validated': len(notes),
                  'validation': 'OLE directory/streams decoded; Version/Metafile and note storages with paired RTF/UTF-16 streams'}
    return (validation, notes) if with_notes else validation


@contextmanager
def validated(data, family, *, sqlite_view=None):
    if family == 'outlook_mailbox':
        import pypff
        stream, box, opened = ParseBytes(data), pypff.file(), False
        try:
            box.open_file_object(stream)
            opened = True
            store, folder = box.get_message_store(), box.get_root_folder()
            if store is None or folder is None:
                raise ValueError('PFF message-store/root-folder structures are unavailable')
            for count in (folder.number_of_sub_folders, folder.number_of_sub_messages):
                _integer(count)
            yield {'parser': 'libpff', 'parser_version': pypff.get_version(), 'format': 'pff_mail_store',
                   'validation': 'PFF header, message store, root folder and folder/message counters decoded'}, box
        finally:
            if opened:
                box.close()
    elif family in ('chromium', 'firefox'):
        yield _sqlite(data, family, view_provenance=sqlite_view), None
    elif family == 'ie_webcache':
        yield _ese(data), None
    elif family == 'ie_legacy_history':
        yield _legacy_history(data), None
    elif family == 'thumbnail_cache':
        yield _thumbcache(data), None
    elif family == 'sticky_notes':
        validation, notes = (_sqlite(data, family, with_notes=True, view_provenance=sqlite_view) if data.startswith(b'SQLite format 3\0')
                             else _sticky_ole(data, with_notes=True))
        yield validation, notes
    else:
        raise ValueError('unsupported artifact-container family')


def _unicode_property(message, property_id):
    """Read exactly one PT_UNICODE property; missing and explicit empty differ."""
    values = []
    sets = _integer(message.number_of_record_sets)
    if sets > 64:
        raise ValueError('MAPI record-set budget exceeded')
    for set_index in range(sets):
        record_set = message.get_record_set(set_index)
        count = _integer(record_set.number_of_entries)
        if count > 4096:
            raise ValueError('MAPI property-entry budget exceeded')
        for entry_index in range(count):
            entry = record_set.get_entry(entry_index)
            if entry.entry_type != property_id:
                continue
            if entry.value_type != 0x1F:
                raise ValueError('requested MAPI text property is not PT_UNICODE')
            raw = entry.data
            if not isinstance(raw, bytes) or len(raw) > MAX_TEXT_BYTES or len(raw) % 2:
                raise ValueError('Unicode MAPI property bytes are invalid or exceed limit')
            text = raw.decode('utf-16-le', errors='strict')
            # One terminating NUL is storage framing, not replacement decoding.
            if text.endswith('\0'):
                text = text[:-1]
            if '\0' in text:
                raise ValueError('Unicode MAPI property contains an embedded NUL')
            values.append((text, set_index, entry_index, len(raw)))
    if len(values) > 1:
        raise ValueError('duplicate requested MAPI property occurrences are ambiguous')
    return values[0] if values else None


def mail_fields(ev, box, container_subject, provenance, examined_at):
    """Walk the mail store's live messages; recovered and orphan messages are not read."""
    from .mail_content import text_property
    pending, folders, messages, text_bytes = [(box.get_root_folder(), (), 0)], 0, 0, 0
    seen = set()
    while pending:
        folder, route, depth = pending.pop()
        folders += 1
        if folders > MAX_FOLDERS or depth > MAX_DEPTH:
            ev.problem(provenance['source_path'] + ' mail bodies', ValueError('mail folder/depth budget exceeded'))
            return
        folder_id = getattr(folder, 'identifier', None)
        if folder_id is not None:
            if folder_id in seen:
                ev.problem(provenance['source_path'] + ' mail bodies', ValueError('repeated/cyclic PFF folder identity'))
                continue
            seen.add(folder_id)
        try:
            count = _integer(folder.number_of_sub_messages)
            subfolders = _integer(folder.number_of_sub_folders)
            if messages + count > MAX_RECORDS or folders + len(pending) + subfolders > MAX_FOLDERS:
                raise ValueError('mail message/folder enumeration budget exceeded')
            for index in range(count):
                messages += 1
                locator = {'folder_route': list(route), 'message_index': index}
                try:
                    message = folder.get_sub_message(index)
                    locator['pff_item_identifier'] = getattr(message, 'identifier', None)
                    subject = json.dumps([container_subject, 'retained-message', locator], sort_keys=True, separators=(',', ':'))
                    for property_id in (0x0037, 0x1000, 0x1013):
                        try:
                            found = text_property(message, property_id, folder=folder)
                        except Exception as error:
                            ev.problem(provenance['source_path'] + ' ' + json.dumps(locator, sort_keys=True)
                                       + f' MAPI 0x{property_id:04X}', error)
                            continue
                        if found is None:
                            continue
                        value, role, byte_count = found['value'], found['role'], found['byte_count']
                        text_bytes += byte_count
                        if text_bytes > MAX_MAIL_TEXT_BYTES:
                            raise ValueError('aggregate mail text budget exceeded')
                        emit_attribute(ev, subject, role, value, examined_at,
                                       **dict(provenance, container_subject=container_subject, message_locator=locator,
                                              **found['provenance'],
                                              limitation='literal retained property; no sent/delivery/authorship claim; recovered/orphan items not scanned'))
                except Exception as error:
                    ev.problem(provenance['source_path'] + ' ' + json.dumps(locator, sort_keys=True), error)
                    if text_bytes > MAX_MAIL_TEXT_BYTES:
                        return
            for index in reversed(range(subfolders)):
                pending.append((folder.get_sub_folder(index), route + (index,), depth + 1))
        except Exception as error:
            ev.problem(provenance['source_path'] + ' folder ' + repr(route), error)


def _container_mtime(stat):
    """File modification time at its original precision."""
    value = getattr(stat, 'st_mtime_ns', None)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError('Sticky Notes container has no integer filesystem st_mtime_ns')
    seconds, nanos = divmod(int(value), 1_000_000_000)
    stamp = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    fraction = ('.' + f'{nanos:09d}'.rstrip('0')) if nanos else ''
    return stamp.strftime('%Y-%m-%dT%H:%M:%S') + fraction + 'Z', int(value)


def _sqlite_source_view(target, path, source, data, budget):
    """Apply the adjacent -wal file from the same filesystem, if there is one."""
    from .sqlite_wal import committed_view
    wal_path = target.fs.path(str(path) + '-wal')
    if not wal_path.exists():
        return data, None
    if wal_path.is_symlink() or not wal_path.is_file():
        raise ValueError('adjacent SQLite WAL is not a regular retained file')
    wal_path = wal_path.resolve(strict=True)
    wal_source = _windows_path(target, wal_path)
    if wal_source.casefold() != (source + '-wal').casefold():
        raise ValueError('resolved SQLite WAL is not adjacent to the selected container')
    size = wal_path.lstat().st_size
    if size == 0 and not isinstance(size, bool):
        with wal_path.open('rb') as stream:
            if stream.read(1):
                raise ValueError('zero-length SQLite WAL has unexpected bytes')
        wal = b''
    else:
        wal = _read(wal_path, size, budget)
    view, details = committed_view(data, wal)
    details['sqlite_wal_source_path'] = wal_source
    return view, details


def sticky_fields(ev, notes, container_subject, provenance, stat, examined_at):
    """Emit each note's text with its container's path and modification time."""
    modified = None
    try:
        modified, raw_time = _container_mtime(stat)
    except Exception as error:
        ev.problem(provenance['source_path'] + ': filesystem modification time', error)
    for note in notes:
        subject = json.dumps([container_subject, 'sticky-note', note['note_locator']],
                             sort_keys=True, ensure_ascii=True, separators=(',', ':'))
        details = dict(provenance, container_subject=container_subject,
                       note_locator=note['note_locator'],
                       limitation='literal retained note and container metadata; no authorship or user-action time')
        emit_attribute(ev, subject, 'sticky_notes.container.path', provenance['source_path'], examined_at,
                       **dict(details, source_field='validated container path'))
        emit_attribute(ev, subject, 'sticky_notes.note.text', note['text'], examined_at,
                       **dict(details, source_field=note['source_field'],
                              text_byte_length=note['text_byte_length'], text_encoding=note['text_encoding']))
        if modified is not None:
            emit_attribute(ev, subject, 'sticky_notes.container.modified_at', modified, examined_at,
                           **dict(details, source_field='filesystem lstat.st_mtime_ns',
                                  filesystem_mtime_ns=raw_time,
                                  timestamp_value_meaning='modification time of container file, not note-storage time'))


def extract(ev, target, ctx):
    common = merge_scope(ctx['common'])
    scope = subject_scope(common)
    if (not all(isinstance(value, str) and value.strip() for value in scope)
            or any(value == 'unknown' for value in scope[2:])):
        ev.problem('validated artifact containers', ValueError('explicit four-axis source scope is required'))
        return
    examined_at = ctx['examined_at']
    seen, budget = set(), [0]
    try:
        for path, family, browser, profile in candidates(ev, target):
            discovered = _win(path)
            try:
                if len(seen) >= MAX_FILES:
                    raise ValueError('artifact-container file-count budget exceeded')
                if path.is_symlink() or not path.is_file():
                    continue
                path = path.resolve(strict=True)
                source = _windows_path(target, path)
                if any(char in source for char in '*?\0'):
                    raise ValueError('container path is not concrete')
                if source.casefold() in seen:
                    continue
                seen.add(source.casefold())
                stat = path.lstat()
                data = _read(path, stat.st_size, budget)
                digest = hashlib.sha256(data).hexdigest()
                subject = json.dumps(['artifact-container', scope, source, 'sha256', digest], ensure_ascii=True, separators=(',', ':'))
                view, sqlite_view = data, None
                if family in ('chromium', 'firefox', 'sticky_notes') and data.startswith(b'SQLite format 3\0'):
                    view, sqlite_view = _sqlite_source_view(target, path, source, data, budget)
                    if sqlite_view is not None:
                        subject = json.dumps(['artifact-container', scope, source, 'sqlite-base-and-wal',
                                              digest, sqlite_view['sqlite_wal_sha256'], sqlite_view['sqlite_view_sha256']],
                                             ensure_ascii=True, separators=(',', ':'))
                with validated(view, family, sqlite_view=sqlite_view) as (validation, mailbox):
                    provenance = dict(common, artifact=source, source_path=source,
                                      source_field='validated container path', container_sha256=digest,
                                      container_size=len(data), container_locator=source, hash_complete=True,
                                      resolved_filesystem_locator=_win(path), discovered_path=discovered,
                                      path_mapping=('explicit Windows path' if source == _win(path) else
                                                    'virtual alias to unique drive mount of identical filesystem object'),
                                      profile_path=_windows_path(target, profile) if profile is not None else None,
                                      classification_basis='validated container structure/schema plus standard application layout',
                                      limitation='structural container observation; not authenticity, execution, ownership or exhaustive discovery',
                                      **validation)
                    emit_attribute(ev, subject, PATH_ROLES[family], source, examined_at, **provenance)
                    if browser is not None:
                        emit_attribute(ev, subject, 'browser.history.browser', browser, examined_at,
                                       **dict(provenance, source_field='validated history schema and product-specific profile layout',
                                              limitation='browser association from format and layout; not exclusive producer, installation, execution or user attribution'))
                    if family == 'sticky_notes':
                        if mailbox:
                            sticky_fields(ev, mailbox, subject, provenance, stat, examined_at)
                    elif mailbox is not None:
                        mail_fields(ev, mailbox, subject, provenance, examined_at)
            except Exception as error:
                ev.problem('validated artifact container ' + discovered, error)
                if len(seen) >= MAX_FILES or budget[0] >= MAX_TOTAL_BYTES:
                    break
    except Exception as error:
        ev.problem('validated artifact container discovery', error)
