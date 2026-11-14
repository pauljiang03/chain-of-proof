"""Artifact inventory uses real directory entries and keeps observations separate from times."""
from __future__ import annotations

import hashlib
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from extractor import inventory
from extractor.store import Evidence


class Path:
    def __init__(self, fs, name):
        self.fs, self.value = fs, name.rstrip('/')

    def __str__(self):
        return self.value

    @property
    def name(self):
        return self.value.rsplit('/', 1)[-1]

    def joinpath(self, name):
        return self.fs.path(self.value + '/' + name)

    def exists(self):
        return self.value in self.fs.nodes

    def is_symlink(self):
        return self.fs.nodes[self.value].get('symlink', False)

    def is_dir(self):
        return self.fs.nodes[self.value]['data'] is None

    def is_file(self):
        return not self.is_dir()

    def iterdir(self):
        if self.value in self.fs.failed_directories:
            raise OSError('unreadable directory')
        prefix = self.value + '/'
        for name in sorted(self.fs.nodes):
            if name.startswith(prefix) and '/' not in name[len(prefix):]:
                yield self.fs.path(name)

    def lstat(self):
        row = self.fs.nodes[self.value]
        return SimpleNamespace(st_size=row.get('size', len(row['data'] or b'')),
                               st_birthtime=row.get('birth', 100), st_mtime=row.get('modified', 200),
                               st_ctime=9999)

    def resolve(self, strict=True):
        return self.fs.path(self.fs.nodes[self.value].get('resolves_to', self.value))

    def open(self, mode):
        self.fs.opened.append(self.value)
        row = self.fs.nodes[self.value]
        if row.get('read_error'):
            raise OSError('unreadable content')
        return io.BytesIO(row['data'])


class FS:
    def __init__(self):
        self.nodes, self.opened, self.failed_directories = {}, [], set()
        self.mounts = {'c:': SimpleNamespace(ntfs=SimpleNamespace(serial=0x1122334455667788)),
                       'd:': SimpleNamespace(ntfs=SimpleNamespace(serial=0x8877665544332211))}

    def path(self, name):
        return Path(self, name)

    def add(self, name, data=b'container', **metadata):
        parts = name.split('/')
        for i in range(1, len(parts)):
            self.nodes.setdefault('/'.join(parts[:i]), {'data': None})
        self.nodes[name] = {'data': data, **metadata}


class Inventory(unittest.TestCase):
    def setUp(self):
        self.fs = FS()
        self.homes = []
        self.target = SimpleNamespace(fs=self.fs,
            user_details=SimpleNamespace(all_with_home=lambda: iter(self.homes)))
        self.ctx = {'common': {'image': 'arbitrary.E01', 'exhibit': 'Workstation', 'tool': 'test'},
                    'examined_at': 900_000_000}
        self.ev = Evidence()

    def extract(self):
        inventory.extract(self.ev, self.target, self.ctx)
        return [dict(kind=k, time=t, obj=obj, aux=aux, prov=json.loads(prov))
                for k, t, res, obj, aux, prov in self.ev.rows()]

    def test_actual_containers_from_two_profiles_drives_and_all_categories(self):
        paths = {
            'C:/Users/Alex/AppData/Local/Microsoft/Outlook/work.OST': 'outlook_mailbox',
            'C:/Users/Alex/Documents/Outlook Files/archive.PST': 'outlook_mailbox',
            'D:/Users/Jo/AppData/Local/Microsoft/Windows/Explorer/thumbcache_256.db': 'thumbnail_cache',
            'C:/Users/Alex/AppData/Roaming/Microsoft/Sticky Notes/StickyNotes.snt': 'sticky_notes',
            'D:/Users/Jo/AppData/Local/Packages/Microsoft.MicrosoftStickyNotes_abc/LocalState/plum.sqlite': 'sticky_notes',
            'C:/ProgramData/Microsoft/Search/Data/Applications/Windows/Windows.edb': 'windows_search',
            'D:/ProgramData/Microsoft/Search/Data/Applications/Windows/Windows.db': 'windows_search',
        }
        for path in paths:
            self.fs.add(path, data=b'actual bytes')
        self.fs.add('C:/Users/Alex/AppData/Local/Microsoft/Outlook/ignore.txt')
        self.fs.add('D:/Users/Jo/AppData/Local/Microsoft/Windows/Explorer/iconcache_256.db')
        rows = self.extract()
        self.assertEqual(len(rows), len(paths))
        self.assertFalse(self.ev.problems)
        for row in rows:
            source = row['obj'].replace('\\', '/')
            self.assertEqual(row['prov']['inventory_category'], paths[source])
            self.assertEqual(row['prov']['source_path'], row['obj'])
            self.assertEqual(row['aux'], 'sha256:' + hashlib.sha256(b'actual bytes').hexdigest())
            self.assertEqual(row['kind'], 'fileContent')
            self.assertTrue(row['prov']['hash_complete'])
            self.assertEqual(row['prov']['hash_algorithm'], 'sha256')
            self.assertNotIn('*', row['obj'])
            expected_serial = '1122334455667788' if source.startswith('C:') else '8877665544332211'
            self.assertEqual(row['prov']['volume_serial_full'], expected_serial)

    def test_filesystem_times_are_metadata_not_examination_or_execution(self):
        path = 'C:/Users/Other/AppData/Local/Microsoft/Outlook/any.pst'
        self.fs.add(path)
        row, = self.extract()
        self.assertEqual(row['time'], self.ctx['examined_at'])
        self.assertEqual(row['prov']['file_created_utc'], '1970-01-01T00:01:40Z')
        self.assertEqual(row['prov']['file_modified_utc'], '1970-01-01T00:03:20Z')
        self.assertEqual(row['prov']['timestamp_semantics'], 'examination_observation')
        self.assertIn('not an event', row['prov']['time_meaning'])
        self.assertEqual(row['prov']['profile_name'], 'Other')

    def test_missing_birth_time_does_not_fall_back_to_ctime(self):
        self.fs.add('C:/Users/Other/AppData/Local/Microsoft/Outlook/any.pst', birth=None)
        row, = self.extract()
        self.assertNotIn('file_created_utc', row['prov'])
        self.assertEqual(row['prov']['file_modified_utc'], '1970-01-01T00:03:20Z')

    def test_registered_nonstandard_home_is_found_and_standard_home_is_deduplicated(self):
        standard = 'C:/Users/Other'
        redirected = 'D:/Profiles/Elsewhere'
        for home in (standard, redirected):
            self.fs.add(home + '/AppData/Local/Microsoft/Outlook/mail.pst')
            self.homes.append(SimpleNamespace(home_path=self.fs.path(home)))
        self.assertEqual(len(self.extract()), 2)
        self.assertEqual(len(self.fs.opened), 2)

    def test_ancestor_junction_aliases_are_resolved_before_hashing_and_listing(self):
        actual = 'C:/Users/Other/AppData/Local/Microsoft/Outlook/mail.pst'
        alias = 'C:/Users/Other/Local Settings/Application Data/Microsoft/Outlook/mail.pst'
        self.fs.add(actual)
        self.fs.add(alias, resolves_to=actual)
        row, = self.extract()
        self.assertEqual(row['obj'], actual.replace('/', '\\'))
        self.assertEqual(self.fs.opened, [actual])

    def test_integer_nanoseconds_preserve_microseconds_without_float_rounding(self):
        stat = SimpleNamespace(st_birthtime=1.234568, st_birthtime_ns=1234567890)
        self.assertEqual(inventory._timestamp(stat, 'st_birthtime'), '1970-01-01T00:00:01.234567Z')
        self.assertEqual(inventory._win('/C:/Users/Other'), 'C:\\Users\\Other')

    def test_oversized_or_unreadable_files_remain_explicit_sightings_without_hashes(self):
        self.fs.add('C:/Users/Other/AppData/Local/Microsoft/Outlook/huge.pst', size=20)
        self.fs.add('C:/Users/Other/AppData/Local/Microsoft/Outlook/bad.ost', read_error=True)
        self.fs.add('C:/Users/Other/AppData/Local/Microsoft/Outlook/good.pst', data=b'ok')
        with patch.object(inventory, 'MAX_FILE_BYTES', 10):
            rows = self.extract()
        self.assertEqual(sum(r['kind'] == 'fileContent' for r in rows), 1)
        sightings = [r for r in rows if r['kind'] == 'fileSeen']
        self.assertEqual(len(sightings), 2)
        self.assertTrue(all(not r['prov']['hash_complete'] for r in sightings))
        self.assertTrue(all(r['time'] == self.ctx['examined_at'] for r in sightings))
        self.assertFalse(any(p.endswith('huge.pst') for p in self.fs.opened))
        self.assertEqual(len(self.ev.problems), 2)

    def test_short_and_long_reads_never_produce_complete_content_hash(self):
        self.fs.add('C:/Users/Other/AppData/Local/Microsoft/Outlook/short.pst', data=b'a', size=3)
        self.fs.add('C:/Users/Other/AppData/Local/Microsoft/Outlook/long.ost', data=b'longer', size=3)
        rows = self.extract()
        self.assertEqual([r['kind'] for r in rows], ['fileSeen', 'fileSeen'])
        self.assertEqual(len(self.ev.problems), 2)

    def test_total_budget_retains_unhashed_inventory(self):
        for name in ('one', 'two'):
            self.fs.add(f'C:/Users/Other/AppData/Local/Microsoft/Outlook/{name}.pst', data=b'abcd')
        with patch.object(inventory, 'MAX_TOTAL_BYTES', 5):
            rows = self.extract()
        self.assertEqual({r['kind'] for r in rows}, {'fileContent', 'fileSeen'})
        self.assertEqual(len(self.fs.opened), 1)
        self.assertEqual(len(self.ev.problems), 1)

    def test_bad_directory_does_not_stop_other_artifact_families(self):
        bad = 'C:/Users/Other/AppData/Local/Microsoft/Outlook'
        self.fs.add(bad + '/bad.pst')
        self.fs.failed_directories.add(bad)
        self.fs.add('C:/ProgramData/Microsoft/Search/Data/Applications/Windows/Windows.edb')
        row, = self.extract()
        self.assertEqual(row['prov']['inventory_category'], 'windows_search')
        self.assertEqual(len(self.ev.problems), 1)

    def test_links_wildcards_directories_and_absent_patterns_are_not_observations(self):
        top = 'C:/Users/Other/AppData/Local/Microsoft/Windows/Explorer/'
        self.fs.add(top + 'thumbcache_*.db')
        self.fs.add(top + 'thumbcache_link.db', symlink=True)
        self.fs.add(top + 'thumbcache_folder.db', data=None)
        rows = self.extract()
        self.assertEqual(rows, [])
        self.assertFalse(self.fs.opened)
        self.assertEqual(len(self.ev.problems), 1)

    def test_file_limit_is_explicit_and_input_order_does_not_affect_rows(self):
        for name in ('z', 'a'):
            self.fs.add(f'C:/Users/Other/AppData/Local/Microsoft/Outlook/{name}.pst')
        with patch.object(inventory, 'MAX_FILES', 1):
            row, = self.extract()
        self.assertTrue(row['obj'].endswith('a.pst'))
        self.assertIn('remaining files omitted', self.ev.problems[0])


if __name__ == '__main__':
    unittest.main()
