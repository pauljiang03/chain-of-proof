"""Synthetic namespace/MFT fixtures: no disk image, benchmark key or model output."""
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from extractor import hacking, recycle_inventory as inventory
from extractor.store import Evidence


CTX = {'common': {'image': 'synthetic.raw', 'exhibit': 'DISK',
                  'source_snapshot': 'base-volume', 'source_variant': 'primary'},
       'examined_at': 1700000000000000}


def reference(segment, sequence):
    return NS(SegmentNumberLowPart=segment & 0xffffffff,
              SegmentNumberHighPart=segment >> 32, SequenceNumber=sequence)


class Record:
    def __init__(self, segment, *, flags=1, sequence=2, data=b'MZ-test', entries=(), reparse=False):
        self.segment = segment
        self.header = NS(SequenceNumber=sequence, Flags=flags, BaseFileRecordSegment=reference(0, 0))
        self.entries, self.data, self.reparse = list(entries), data, reparse
        self.read_error = self.iter_error = None

    def is_reparse_point(self):
        return self.reparse

    def iterdir(self, **kwargs):
        if self.iter_error:
            raise self.iter_error
        yield from self.entries

    def open(self):
        if self.read_error:
            raise self.read_error
        return io.BytesIO(self.data)

    def size(self):
        return len(self.data)


class Entry:
    def __init__(self, name, record, *, sequence=None, segment=None):
        self.attribute = NS(file_name=name)
        self.header = NS(FileReference=reference(record.segment if segment is None else segment,
                           record.header.SequenceNumber if sequence is None else sequence))
        self.record, self.error = record, None

    def dereference(self):
        if self.error:
            raise self.error
        return self.record


class MountedPath:
    """A Windows mount path backed by tiny ordinary files for non-NTFS tests."""
    def __init__(self, root, logical):
        self.root, self.logical = root, logical
        self.actual = root / logical.split('/', 1)[1]

    def __str__(self):
        return self.logical

    def exists(self):
        return self.actual.exists()

    def is_symlink(self):
        return self.actual.is_symlink()

    def is_dir(self):
        return self.actual.is_dir()

    def is_file(self):
        return self.actual.is_file()

    def iterdir(self):
        return (MountedPath(self.root, self.logical + '/' + child.name) for child in self.actual.iterdir())

    def open(self, mode):
        return self.actual.open(mode)

    def stat(self):
        return self.actual.stat()


def filesystem(*entries, serial=0x1234567800ABCDEF):
    recycle = Record(20, flags=3, entries=entries)
    root = Record(5, flags=3, entries=[Entry('RECYCLER', recycle)])
    return NS(ntfs=NS(serial=serial, mft=NS(root=root)), __type__='ntfs')


def target(fs, **mounts):
    return NS(fs=NS(mounts={'c:': fs, 'sysvol': fs, **mounts}))


def run_collect(source, ctx=CTX):
    ev = Evidence()
    result = inventory.collect(ev, source, ctx)
    inventory.emit(ev, result, ctx)
    return ev, result


def rows(ev, kind):
    return [row for row in ev.rows() if row[0] == kind]


def attributes(ev, role):
    return [(json.loads(row[4]), json.loads(row[5]), row[3]) for row in ev.rows()
            if row[0] in ('attributeTextValue', 'attributeIntegerValue', 'attributeBooleanValue')
            and json.loads(row[5]).get('attribute_role') == role]


def info2(*paths, index=7, drive=3):
    data = struct.pack('<5I', 5, len(paths), len(paths), 800, 0)
    for path in paths:
        row = bytearray(800)
        raw = path.encode('utf-16-le')
        row[280:280 + len(raw)] = raw
        struct.pack_into('<IIQI', row, 260, index, drive, 133444736000000000, 9)
        data += row
    return data


class RecycleInventory(unittest.TestCase):
    def test_exact_members_share_set_and_actual_flags_not_presence(self):
        fs = filesystem(Entry('one.exe', Record(40, flags=1)), Entry('two.EXE', Record(41, flags=0)),
                        Entry('not-executable.txt', Record(42)), Entry('bad.exe', Record(43, data=b'NO')))
        ev, result = run_collect(target(fs))
        self.assertEqual(ev.problems, [])
        self.assertTrue(result['complete'])
        declaration, = rows(ev, 'filesystemSet')
        allocated, = rows(ev, 'filesystemMemberAllocated')
        deleted, = rows(ev, 'filesystemMemberDeleted')
        self.assertEqual(allocated[3], declaration[3])
        self.assertEqual(deleted[3], declaration[3])
        self.assertNotEqual(allocated[4], deleted[4])
        self.assertEqual(sorted(value for value, _, _ in attributes(ev, 'filesystem.deleted_flag')), [False, True])
        self.assertEqual([value for value, _, _ in attributes(ev, 'recycle.file_present')], [True, True])
        self.assertEqual(attributes(ev, 'recycle.executable_count'), [])
        for row in (allocated, deleted, declaration):
            prov = json.loads(row[5])
            self.assertEqual([prov[key] for key in ('image', 'exhibit', 'source_snapshot', 'source_variant')],
                             list(CTX['common'].values()))
            self.assertEqual(prov['timestamp_semantics'], 'examination_observation')
        self.assertEqual(json.loads(deleted[5])['mft_header_flags'], 0)

    def test_filesystem_mount_aliases_and_hardlinks_do_not_duplicate_members(self):
        executable = Record(45)
        fs = filesystem(Entry('long.exe', executable), Entry('LONG~1.EXE', executable))
        ev, result = run_collect(target(fs, **{'d:': fs}))
        self.assertEqual(ev.problems, [])
        self.assertEqual(len(result['volumes']), 1)
        self.assertEqual(result['volumes'][0]['drive_aliases'], ['C:', 'D:'])
        self.assertEqual(len(result['members']), 1)
        self.assertEqual(next(iter(result['members'].values()))['paths'],
                         {r'C:\RECYCLER\long.exe', r'C:\RECYCLER\LONG~1.EXE'})
        self.assertEqual(len(rows(ev, 'filesystemMemberAllocated')), 1)
        self.assertEqual(len(attributes(ev, 'recycle.stored_path')), 2)

    def test_distinct_volumes_with_same_serial_and_record_stay_distinct(self):
        first = filesystem(Entry('same.exe', Record(40)))
        second = filesystem(Entry('same.exe', Record(40)))
        ev, result = run_collect(target(first, **{'d:': second}))
        self.assertTrue(result['complete'])
        self.assertEqual(len(result['members']), 2)
        self.assertEqual(len(result['volumes']), 2)
        self.assertEqual(len(rows(ev, 'filesystemMemberAllocated')), 2)

    def test_every_source_axis_separates_membership_and_set_identity(self):
        fs = filesystem(Entry('same.exe', Record(40)))
        _, original = run_collect(target(fs))
        for axis, value in [('image', 'other.raw'), ('exhibit', 'OTHER'),
                            ('source_snapshot', 'vss:11111111-2222-3333-4444-555555555555'),
                            ('source_variant', 'recovered')]:
            ctx = dict(CTX, common=dict(CTX['common'], **{axis: value}))
            _, other = run_collect(target(fs), ctx)
            self.assertNotEqual(original['set_subject'], other['set_subject'])
            self.assertTrue(set(original['members']).isdisjoint(other['members']))

    def test_stale_file_reference_missing_record_and_extension_never_complete(self):
        bad = Record(40, sequence=5)
        stale = Entry('stale.exe', bad, sequence=4)
        missing = Entry('missing.exe', Record(41))
        missing.error = FileNotFoundError('MFT entry unavailable')
        extension = Record(42)
        extension.header.BaseFileRecordSegment = reference(4, 2)
        for entry in (stale, missing, Entry('extension.exe', extension)):
            with self.subTest(name=entry.attribute.file_name):
                ev, result = run_collect(target(filesystem(entry)))
                self.assertFalse(result['complete'])
                self.assertEqual(rows(ev, 'filesystemSet'), [])
                self.assertEqual(result['members'], {})
                self.assertTrue(ev.problems)

    def test_integer_subclasses_are_valid_but_boolean_and_zero_sequences_are_not(self):
        class Uint(int):
            pass
        good = Record(Uint(40), flags=Uint(1), sequence=Uint(2))
        ev, result = run_collect(target(filesystem(Entry('good.exe', good), serial=Uint(90))))
        self.assertTrue(result['complete'])
        self.assertEqual(len(rows(ev, 'filesystemMemberAllocated')), 1)
        for record in (Record(40, flags=True), Record(40, sequence=0), Record(True)):
            ev, result = run_collect(target(filesystem(Entry('bad.exe', record))))
            self.assertFalse(result['complete'])
            self.assertEqual(rows(ev, 'filesystemSet'), [])
            self.assertEqual(result['members'], {})

    def test_unreadable_prefix_cannot_be_silently_omitted_from_complete_set(self):
        bad = Record(41)
        bad.read_error = OSError('unreadable source bytes')
        ev, result = run_collect(target(filesystem(Entry('good.exe', Record(40)), Entry('bad.exe', bad))))
        self.assertEqual(len(result['members']), 1)
        self.assertFalse(result['complete'])
        self.assertEqual(rows(ev, 'filesystemSet'), [])
        self.assertTrue(any('unreadable' in problem for problem in ev.problems))

    def test_reparse_cycles_and_namespace_errors_leave_explicit_partial_state(self):
        cycle = Record(45, flags=3)
        cycle.entries = [Entry('again', cycle)]
        for entry in (Entry('link', Record(50, flags=3, reparse=True)), Entry('cycle', cycle),
                      Entry('bad/name.exe', Record(40))):
            ev, result = run_collect(target(filesystem(entry)))
            self.assertFalse(result['complete'])
            self.assertEqual(rows(ev, 'filesystemSet'), [])
            self.assertTrue(ev.problems)
        fs = filesystem()
        fs.ntfs.mft.root.entries.append(Entry(None, Record(40)))
        ev, result = run_collect(target(fs))
        self.assertFalse(result['complete'])
        self.assertEqual(rows(ev, 'filesystemSet'), [])

    def test_entry_depth_and_member_bounds_never_certify_truncated_set(self):
        directory = Record(55, flags=3, entries=[Entry('inside.exe', Record(42))])
        fs = filesystem(Entry('one.exe', Record(40)), Entry('two.exe', Record(41)), Entry('folder', directory))
        for limit, value in [('MAX_ENTRIES', 2), ('MAX_DEPTH', 0), ('MAX_MEMBERS', 1)]:
            with patch.object(inventory, limit, value):
                ev, result = run_collect(target(fs))
            self.assertFalse(result['complete'], limit)
            self.assertEqual(rows(ev, 'filesystemSet'), [], limit)
            self.assertTrue(ev.problems, limit)

    def test_non_ntfs_observed_executable_remains_unknown_no_zero_or_false(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / 'RECYCLER'
            root.mkdir()
            (root / 'observed.exe').write_bytes(b'MZ-content')
            fs = NS(__type__='fat')
            source = NS(fs=NS(mounts={'e:': fs}, path=lambda name: base / name.split('/', 1)[1]))
            ev, result = run_collect(source)
        self.assertFalse(result['complete'])
        self.assertEqual(len(rows(ev, 'filesystemMemberUnknown')), 1)
        self.assertEqual(rows(ev, 'filesystemSet'), [])
        self.assertEqual(attributes(ev, 'filesystem.deleted_flag'), [])
        self.assertEqual(attributes(ev, 'recycle.executable_count'), [])

    def test_no_concrete_mount_or_no_explicit_scope_cannot_certify_empty(self):
        fs = filesystem()
        sources = [(NS(fs=NS(mounts={'sysvol': fs})), CTX),
                   (target(fs), dict(CTX, common={'image': 'synthetic.raw', 'exhibit': 'DISK'}))]
        for source, ctx in sources:
            ev, result = run_collect(source, ctx)
            self.assertFalse(result['complete'])
            self.assertEqual(rows(ev, 'filesystemSet'), [])
            self.assertEqual(result['members'], {})
        ev, result = run_collect(target(filesystem()))
        self.assertTrue(result['complete'])
        self.assertEqual(len(rows(ev, 'filesystemSet')), 1)
        self.assertEqual(result['members'], {})  # The proof layer refuses the empty Boolean aggregate.
        self.assertEqual(attributes(ev, 'recycle.executable_count'), [])

    def test_info2_uses_actual_container_volume_and_keeps_missing_unknown(self):
        data = info2(r'D:\Old\first.exe', r'D:\Old\second.exe')
        fs = filesystem(Entry('INFO2', Record(50, data=data)), Entry('Dd7.exe', Record(40, flags=1)))
        ev = Evidence()
        hacking._recycle(ev, target(fs), [], CTX)
        self.assertEqual(len(rows(ev, 'fileDeleted')), 2)
        flags = attributes(ev, 'filesystem.deleted_flag')
        self.assertEqual(len(flags), 3)  # One exact member + both INFO2 occurrences, no ID collapse.
        self.assertTrue(all(value is False for value, _, _ in flags))
        info_flags = [row for row in flags if row[1]['parser'] == 'extractor.hacking.info2']
        self.assertEqual(len({row[2] for row in info_flags}), 2)
        self.assertEqual({row[1]['mft_source'] for row in info_flags}, {r'C:\$MFT'})
        self.assertEqual({row[1]['byte_offset'] for row in info_flags}, {20, 820})
        self.assertTrue(all(row[1]['drive'] == 'D' for row in info_flags))
        self.assertEqual(ev.problems, [])
        missing = Evidence()
        hacking._recycle(missing, target(filesystem(Entry('INFO2', Record(50, data=data)))), [], CTX)
        self.assertEqual(len(rows(missing, 'fileDeleted')), 2)
        self.assertEqual(attributes(missing, 'recycle.file_present'), [])
        self.assertEqual(attributes(missing, 'filesystem.deleted_flag'), [])
        self.assertTrue(any('unknown' in problem for problem in missing.problems))

    def test_info2_parse_failure_does_not_erase_narrow_namespace_flags(self):
        ev = Evidence()
        fs = filesystem(Entry('one.exe', Record(40, flags=0)), Entry('INFO2', Record(50, data=b'bad')))
        hacking._recycle(ev, target(fs), [], CTX)
        self.assertEqual(len(rows(ev, 'filesystemMemberDeleted')), 1)
        self.assertEqual(rows(ev, 'fileDeleted'), [])
        self.assertTrue(any('INFO2' in problem for problem in ev.problems))

    def test_info2_does_not_choose_first_ambiguous_namespace_target(self):
        fs = filesystem(Entry('INFO2', Record(50, data=info2(r'D:\Old\first.exe'))),
                        Entry('Dd7.exe', Record(40, flags=1)), Entry('dd7.EXE', Record(41, flags=0)))
        ev = Evidence()
        hacking._recycle(ev, target(fs), [], CTX)
        self.assertEqual(rows(ev, 'filesystemSet'), [])
        self.assertEqual(len(rows(ev, 'fileDeleted')), 1)
        self.assertFalse(any(prov['parser'] == 'extractor.hacking.info2'
                             for _, prov, _ in attributes(ev, 'filesystem.deleted_flag')))
        self.assertTrue(any('ambiguous' in problem for problem in ev.problems))

    def test_non_ntfs_preserves_info2_event_but_cannot_infer_allocation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'RECYCLER').mkdir()
            (root / 'RECYCLER' / 'INFO2').write_bytes(info2(r'D:\Old\first.exe'))
            (root / 'RECYCLER' / 'Dd7.exe').write_bytes(b'MZ-content')
            source = NS(fs=NS(mounts={'e:': NS(__type__='fat')},
                              path=lambda name: MountedPath(root, name)))
            ev = Evidence()
            hacking._recycle(ev, source, [], CTX)
        self.assertEqual(rows(ev, 'filesystemSet'), [])
        self.assertEqual(len(rows(ev, 'filesystemMemberUnknown')), 1)
        self.assertEqual(len(rows(ev, 'fileDeleted')), 1)
        self.assertEqual(attributes(ev, 'filesystem.deleted_flag'), [])
        self.assertEqual([value for value, _, _ in attributes(ev, 'recycle.file_present')], [True, True])
        self.assertTrue(all(prov['source_path'].startswith('E:')
                            for _, prov, _ in attributes(ev, 'recycle.stored_path')))
        self.assertTrue(any('unavailable' in problem for problem in ev.problems))

    def test_reader_members_replay_through_actual_kernel_and_independent_verifier(self):
        from checker.check import check
        from checker.facts import JsonFacts
        from verifier.verify import verify

        ev, _ = run_collect(target(filesystem(Entry('one.exe', Record(40, flags=1)),
                                             Entry('two.exe', Record(41, flags=0)))))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'facts.json'
            ev.write_json(path, {})
            source = JsonFacts(path)
            declaration = next(row for row in source.all() if row.kind == 'filesystemSet')
            cert = check({'filesystemSetDeleted': [declaration.id, 2, False]}, 'ReaderSet', source,
                         out_dir=Path(directory))
            self.assertEqual(cert['status'], 'verified', cert)
            self.assertEqual(cert['axioms'], [])
            self.assertEqual({row['kind'] for row in cert['cited_facts']},
                             {'filesystemSet', 'filesystemMemberAllocated', 'filesystemMemberDeleted'})
            self.assertEqual(verify(cert, source), [])


if __name__ == '__main__':
    unittest.main()
