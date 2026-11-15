"""Exact bounded Recycle Bin namespace members and their actual NTFS flags.

The declaration means the described examination procedure completed, not that all
executables on disk were found. Namespace names and MZ bytes select members; only
matching NTFS file-reference sequences can supply allocation flags. INFO2 records
are separate historical observations and never replace those flags.
"""
from __future__ import annotations

import hashlib
import json
import re

from .attributes import emit_attribute
from .source_scope import merge_scope, subject_scope

ROOT_NAMES = frozenset(('recycler', 'recycled', '$recycle.bin'))
MAX_ENTRIES = 100000
MAX_DEPTH = 32
MAX_MEMBERS = 256
DEFINITION = ('Distinct file identities with an .exe namespace name and readable MZ prefix under '
              'RECYCLER, RECYCLED or $Recycle.Bin roots of every distinct drive-mounted filesystem '
              'in this source; NTFS index references must match record and sequence; aliases deduplicated; '
              'no reparse traversal; bounded to 100000 index/namespace entries, depth 32 and 256 members. '
              'This is not all disk executables, execution, secure deletion or recoverability.')


def _integer(value, maximum=None):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or (maximum is not None and value > maximum):
        raise ValueError('invalid nonnegative filesystem integer')
    return int(value)


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'))


def _record_identity(record):
    sequence = _integer(record.header.SequenceNumber, 0xffff)
    if not sequence:
        raise ValueError('uninitialized MFT sequence cannot identify a file')
    return (_integer(record.segment, (1 << 48) - 1), sequence)


def _dereference(entry):
    # Dissect's IndexEntry.dereference() resolves the record number, but does
    # not enforce its sequence. Microsoft's FILE_RECORD_SEGMENT_HEADER contract
    # requires the sequence match: https://learn.microsoft.com/en-us/windows/win32/devnotes/file-record-segment-header
    reference = entry.header.FileReference
    expected = (_integer(reference.SegmentNumberLowPart, 0xffffffff)
                | _integer(reference.SegmentNumberHighPart, 0xffff) << 32,
                _integer(reference.SequenceNumber, 0xffff))
    record = entry.dereference()
    if expected != _record_identity(record):
        raise ValueError('directory reference does not match the actual MFT record and sequence')
    base = record.header.BaseFileRecordSegment
    if any(_integer(value) for value in (base.SegmentNumberLowPart, base.SegmentNumberHighPart,
                                         base.SequenceNumber)):
        raise ValueError('directory reference points to an MFT extension record')
    return record


def _volumes(target):
    grouped = {}
    for name, filesystem in target.fs.mounts.items():
        if not re.fullmatch(r'[A-Za-z]:', str(name)):
            continue
        ntfs = getattr(filesystem, 'ntfs', None)
        key = id(ntfs) if ntfs is not None else id(filesystem)
        row = grouped.setdefault(key, {'filesystem': filesystem, 'ntfs': ntfs, 'drives': []})
        row['drives'].append(str(name).upper())
    return sorted(grouped.values(), key=lambda row: min(row['drives']))


def collect(ev, target, ctx):
    """Return reader observations; never compute an aggregate deletion Boolean."""
    common = merge_scope(ctx['common'])
    scope = subject_scope(common)
    result = {'common': common, 'scope': scope, 'definition': DEFINITION, 'members': {},
              'files': {}, 'ambiguous_paths': set(), 'issues': [], 'volumes': [],
              'entries_examined': 0, 'complete': True}

    def issue(where, error):
        result['complete'] = False
        result['issues'].append({'source': where, 'reason': str(error)})
        ev.problem(where, error)

    def tick():
        result['entries_examined'] += 1
        if result['entries_examined'] > MAX_ENTRIES:
            raise ValueError('Recycle Bin enumeration entry bound exceeded')

    if (not all(isinstance(value, str) and value.strip() for value in scope)
            or any(value == 'unknown' for value in scope[2:])):
        issue('Recycle Bin enumeration', ValueError('explicit image, exhibit, snapshot and variant are required'))
        return result
    volumes = _volumes(target)
    if not volumes:
        issue('Recycle Bin enumeration', ValueError('no concrete drive-mounted filesystems were available'))
        return result
    for volume in volumes:
        drive = min(volume['drives'])
        ntfs = volume['ntfs']
        descriptor = {'drive': drive, 'drive_aliases': sorted(set(volume['drives'])),
                      'filesystem_type': 'ntfs' if ntfs is not None else str(getattr(volume['filesystem'], '__type__', 'unknown')),
                      'ntfs_volume_serial': None}
        try:
            if ntfs is not None:
                descriptor['ntfs_volume_serial'] = f'{_integer(ntfs.serial, (1 << 64) - 1):016X}'
        except Exception as error:
            issue(drive + ' volume identity', error)
        result['volumes'].append(descriptor)
        volume['descriptor'] = descriptor
    result['set_subject'] = _json(['recycle-executable-set', scope, ctx['examined_at'], DEFINITION, result['volumes']])

    def member(path, record, descriptor, data):
        if not path.lower().endswith('.exe') or data != b'MZ':
            return
        flags = None
        if record is not None:
            segment, sequence = _record_identity(record)
            flags = _integer(record.header.Flags, 0xffff)
            identity = _json(['recycle-executable', scope, descriptor, segment, sequence])
            locator = {'mft_segment': segment, 'sequence_number': sequence, 'mft_header_flags': flags,
                       'flag_mask': 1, 'source_field': 'FILE_RECORD_SEGMENT_HEADER.Flags & FILE_RECORD_SEGMENT_IN_USE',
                       'mft_source': descriptor['drive'] + r'\$MFT'}
            if callable(getattr(record.header, 'dumps', None)):
                locator['parsed_mft_header_sha256'] = hashlib.sha256(record.header.dumps()).hexdigest()
        else:
            identity = _json(['recycle-executable-unknown-mft', scope, descriptor, path])
            locator = {'source_field': 'namespace file and MZ prefix; NTFS allocation metadata unavailable'}
        existing = result['members'].get(identity)
        if existing is not None:
            if existing['flags'] != flags:
                issue(path, ValueError('same scoped file identity has contradictory allocation observations'))
            existing['paths'].add(path)
            return
        if len(result['members']) >= MAX_MEMBERS:
            raise ValueError('Recycle Bin executable member bound exceeded')
        result['members'][identity] = {'identity': identity, 'paths': {path}, 'flags': flags,
                                      'volume': descriptor, 'locator': locator}

    for volume in volumes:
        descriptor, ntfs = volume['descriptor'], volume['ntfs']
        drive = descriptor['drive']
        if ntfs is None:
            issue(drive, ValueError('non-NTFS volume cannot supply required MFT allocation flags'))
            # Keep confidently identified members as unknown; never make them false.
            pending = [(target.fs.path(drive + '/' + root), 0)
                       for root in ('RECYCLER', 'Recycled', '$Recycle.Bin')]
            while pending:
                path, depth = pending.pop()
                try:
                    if not path.exists():
                        continue
                    if path.is_symlink():
                        raise ValueError('reparse/symlink entry prevents complete enumeration')
                    if path.is_dir():
                        if depth >= MAX_DEPTH:
                            raise ValueError('Recycle Bin directory depth bound exceeded')
                        for child in path.iterdir():
                            tick()
                            pending.append((child, depth + 1))
                    elif path.is_file():
                        source = str(path).replace('/', '\\').lstrip('\\')
                        key = source.casefold()
                        existing = result['files'].get(key)
                        if key in result['ambiguous_paths'] or (existing and existing['source_path'] != source):
                            result['files'].pop(key, None)
                            result['ambiguous_paths'].add(key)
                            raise ValueError('case-insensitive namespace path is ambiguous')
                        result['files'][key] = {'source_path': source, 'record': None,
                                                'path': path, 'volume': descriptor}
                        if source.lower().endswith('.exe'):
                            with path.open('rb') as stream:
                                member(source, None, descriptor, stream.read(2))
                except Exception as error:
                    issue(str(path), error)
                    if result['entries_examined'] > MAX_ENTRIES:
                        break
            continue
        if descriptor['ntfs_volume_serial'] is None:
            continue
        visited = set()

        def walk(record, source, depth, ancestors=()):
            identity = _record_identity(record)
            if identity in ancestors:
                raise ValueError('cycle in Recycle Bin directory identities')
            if identity in visited:
                return  # Another namespace alias for an already examined directory.
            if depth > MAX_DEPTH:
                raise ValueError('Recycle Bin directory depth bound exceeded')
            if record.is_reparse_point():
                raise ValueError('reparse directory prevents complete enumeration')
            if not _integer(record.header.Flags, 0xffff) & 2:
                raise ValueError('Recycle Bin root/child directory has no directory flag')
            visited.add(identity)
            # Include DOS aliases too; identity deduplication, not filename
            # filtering, determines the cardinality of the selected file set.
            for entry in record.iterdir():
                tick()
                path = source
                try:
                    name = entry.attribute.file_name
                    if name in ('.', '..'):
                        continue
                    if not isinstance(name, str) or not name or any(c in name for c in '/\\\0'):
                        raise ValueError('directory index name is not one unambiguous path component')
                    path = source + '\\' + name
                    child = _dereference(entry)
                    flags = _integer(child.header.Flags, 0xffff)
                    if child.is_reparse_point():
                        raise ValueError('reparse entry prevents complete enumeration')
                    if flags & 2:
                        walk(child, path, depth + 1, ancestors + (identity,))
                    else:
                        key = path.casefold()
                        if key in result['ambiguous_paths']:
                            raise ValueError('case-insensitive path remains ambiguous between MFT identities')
                        existing = result['files'].get(key)
                        if existing is not None and _record_identity(existing['record']) != _record_identity(child):
                            result['files'].pop(key)
                            result['ambiguous_paths'].add(key)
                            raise ValueError('case-insensitive path is ambiguous between MFT identities')
                        result['files'][key] = {'source_path': path, 'record': child, 'volume': descriptor}
                        if name.lower().endswith('.exe'):
                            with child.open() as stream:
                                member(path, child, descriptor, stream.read(2))
                except Exception as error:
                    issue(path, error)
                    if result['entries_examined'] > MAX_ENTRIES or len(result['members']) >= MAX_MEMBERS:
                        return
        try:
            root = ntfs.mft.root
            if root.is_reparse_point() or not _integer(root.header.Flags, 0xffff) & 2:
                raise ValueError('volume root cannot be enumerated as an ordinary NTFS directory')
            for entry in root.iterdir():
                tick()
                name = entry.attribute.file_name
                if not isinstance(name, str) or not name or any(c in name for c in '/\\\0'):
                    raise ValueError('volume-root index has an invalid namespace component')
                if name.casefold() in ROOT_NAMES:
                    path = drive + '\\' + name
                    try:
                        walk(_dereference(entry), path, 0)
                    except Exception as error:
                        issue(path, error)
        except Exception as error:
            issue(drive + '\\', error)
    return result


def emit(ev, inventory, ctx):
    """Emit complete-set declaration plus exact member facts; no reader Boolean."""
    if 'set_subject' not in inventory:
        return
    common, subject = inventory['common'], inventory['set_subject']
    base = dict(common, artifact='Recycle Bin namespace enumeration', source_path='Recycle Bin namespace enumeration',
                parser='extractor.recycle_inventory', definition=DEFINITION,
                enumeration_complete=inventory['complete'], entries_examined=inventory['entries_examined'],
                volume_descriptors=inventory['volumes'], examination_time=ctx['examined_at'],
                timestamp_semantics='examination_observation',
                time_meaning='when the scoped namespace and MFT flags were examined, not deletion time')
    for identity, member in sorted(inventory['members'].items()):
        paths = sorted(member['paths'])
        flags = member['flags']
        kind = ('filesystemMemberUnknown' if flags is None else
                'filesystemMemberAllocated' if flags & 1 else 'filesystemMemberDeleted')
        provenance = dict(base, **member['locator'], artifact=paths[0], source_path=paths[0],
                          source_paths=paths, volume=member['volume'], prefix_hex='4d5a',
                          prefix_byte_offset=0, prefix_byte_length=2,
                          limitation='membership requires .exe name and MZ prefix; not program execution or secure erasure')
        ev.add(kind, ctx['examined_at'], 1, subject, identity, **provenance)
        emit_attribute(ev, identity, 'recycle.file_present', True, ctx['examined_at'], **provenance)
        for path in paths:
            emit_attribute(ev, identity, 'recycle.stored_path', path, ctx['examined_at'], **provenance)
        if flags is not None:
            emit_attribute(ev, identity, 'filesystem.deleted_flag', not bool(flags & 1), ctx['examined_at'], **provenance)
    if inventory['complete']:
        ev.add('filesystemSet', ctx['examined_at'], 1, subject, DEFINITION, **base)
