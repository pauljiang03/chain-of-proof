"""Exercise source readers with synthetic records, never models or answer keys."""
import codecs
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from checker.catalog import decode_value
from extractor import system as s
from extractor.store import Evidence

EXAMINED = 1800000000123456
FILETIME = 130717152000000000
EVENT_US = 1427241600000000


class File:
    def __init__(self, path, data):
        self.path, self.data = path, data
        self.name = path.rsplit('/', 1)[-1]

    def __str__(self):
        return self.path

    def open(self, mode):
        return io.BytesIO(self.data)

    def lstat(self):
        return SimpleNamespace(st_birthtime=1427241000, st_mtime=1427242000)


def prefetch():
    path = r'\DEVICE\HARDDISKVOLUME7\TOOLS\DIFFERENT.EXE'
    strings = (path + '\0').encode('utf-16-le')
    raw = bytearray(0x200) + strings
    struct.pack_into('<I', raw, 0, 26)
    raw[4:8] = b'SCCA'
    name = 'DIFFERENT.EXE'.encode('utf-16-le')
    raw[16:16 + len(name)] = name
    struct.pack_into('<I', raw, 76, s.scca_hash_2008(path))
    struct.pack_into('<II', raw, 0x64, 0x200, len(strings))
    struct.pack_into('<QQ', raw, 0x80, FILETIME, FILETIME - 10000000)
    struct.pack_into('<I', raw, 0xd0, 2)
    return raw


def userassist_value():
    return struct.pack('<4I', 0, 3, 5, 1234) + bytes(44) + struct.pack('<Q', FILETIME) + bytes(4)


def attrs(ev):
    # Only the program/path identity roles; metadata roles are tested elsewhere.
    return [(json.loads(row[-1])['attribute_role'], decode_value(row[4], 'string'), json.loads(row[-1]))
            for row in ev.rows() if row[0] == 'attributeTextValue'
            and json.loads(row[-1])['attribute_role'] in ('app.execution.program', 'app.execution.path')]


class ExecutionReaders(unittest.TestCase):
    def setUp(self):
        self.ev = Evidence()
        self.common = {'image': 'synthetic.E01', 'exhibit': 'OTHER-PC'}
        self.out = s._Out(self.ev, self.common, EXAMINED)

    def event(self, **changes):
        data = dict(EventID=4688, Provider_Name=s.A, Channel='Security',
                    ts=datetime(2015, 3, 25, tzinfo=timezone.utc),
                    NewProcessName=r'D:\Unrelated Tools\literal.exe', EventRecordID=42,
                    source='D:/Windows/System32/winevt/Logs/Security.evtx', SubjectUserName='OtherUser')
        data.update(changes)
        return data

    def test_security_process_creation_preserves_literal_path_and_time_scope(self):
        record = self.event()
        s._event(self.out, self.ev, record, 'Security.evtx record 42', {})
        values = attrs(self.ev)
        self.assertEqual({(role, value) for role, value, _ in values},
                         {('app.execution.program', 'literal.exe'),
                          ('app.execution.path', r'D:\Unrelated Tools\literal.exe')})
        for _, _, prov in values:
            self.assertEqual(prov['source_value'], record['NewProcessName'])
            self.assertEqual(prov['source_entry']['event_record_id'], '42')
            self.assertEqual(prov['recorded_time_us'], EVENT_US)
            self.assertEqual(prov['recorded_time_resolution_us'], 1000000)
            self.assertEqual(prov['timestamp_semantics'], 'examination_observation')
        typed = [row for row in self.ev.rows() if row[0].startswith(('attribute', 'roleAppExecution'))]
        self.assertTrue(all(row[1] == EXAMINED for row in typed))
        old = [row for row in self.ev.rows() if row[0] == 'programRun']
        self.assertEqual(old[0][1], EVENT_US)

    def test_security_requires_provider_channel_locator_and_explicit_unmodified_path(self):
        cases = [dict(Provider_Name='Other'), dict(Channel='Application'), dict(EventID=4689),
                 dict(EventRecordID=None), dict(source=''), dict(source=' '), dict(NewProcessName=''),
                 dict(NewProcessName='"D:\\Tools\\a.exe"'), dict(NewProcessName=' D:\\Tools\\a.exe'),
                 dict(NewProcessName='D:\\Tools\\a.exe --flag'), dict(NewProcessName=42)]
        for changes in cases:
            with self.subTest(changes=changes):
                ev = Evidence()
                s._event(s._Out(ev, self.common, EXAMINED), ev, self.event(**changes), 'record 42', {})
                self.assertEqual(attrs(ev), [])
        ev = Evidence()
        s._event(s._Out(ev, self.common, EXAMINED), ev, self.event(Channel='Application'), 'record 42', {})
        self.assertEqual(len([r for r in ev.rows() if r[0] == 'programRun']), 1)

    def test_missing_examined_time_or_image_scope_preserves_old_rows_only(self):
        for examined, common in [(None, self.common), (0, self.common), (EXAMINED, {'image': 'x'}),
                                 (EXAMINED, {'exhibit': 'PC'}),
                                 (EXAMINED, {'image': ' ', 'exhibit': 'PC'})]:
            ev = Evidence()
            s._event(s._Out(ev, common, examined), ev, self.event(), 'record 42', {})
            self.assertEqual(attrs(ev), [])
            self.assertEqual(len(ev.rows()), 1)

    def test_source_subject_distinguishes_image_exhibit_and_event_record(self):
        for image, exhibit, number in [('a', 'PC', 42), ('b', 'PC', 42), ('a', 'OTHER', 42), ('a', 'PC', 43)]:
            out = s._Out(self.ev, {'image': image, 'exhibit': exhibit}, EXAMINED)
            s._event(out, self.ev, self.event(EventRecordID=number), f'Security.evtx record {number}', {})
        subjects = {row[4] for row in self.ev.rows() if row[0] == 'attributeSubject'}
        self.assertEqual(len(subjects), 4)

    def test_prefetch_emits_only_literal_header_name_per_run(self):
        raw = prefetch()
        file = File('C:/Windows/Prefetch/ARBITRARY-FILENAME.pf', raw)
        with patch.object(s, '_path', return_value=SimpleNamespace(iterdir=lambda: [file])):
            s._prefetch(self.out, self.ev, None)
        self.assertEqual(self.ev.problems, [])
        values = attrs(self.ev)
        self.assertEqual([(r, v) for r, v, _ in values],
                         [('app.execution.program', 'DIFFERENT.EXE')] * 2)
        self.assertEqual({p['recorded_time_us'] for _, _, p in values}, {EVENT_US, EVENT_US - 1000000})
        for _, _, p in values:
            self.assertEqual(raw[p['byte_offset']:p['byte_offset'] + p['byte_length']].hex(), p['raw_value_hex'])
            self.assertEqual(p['byte_offset_basis'], 'source file bytes')
            self.assertNotIn('path_source', p)
        self.assertEqual(len({row[4] for row in self.ev.rows() if row[0] == 'attributeSubject'}), 2)
        old = [r for r in self.ev.rows() if r[0] == 'programRun']
        self.assertEqual(len(old), 2)
        self.assertTrue(all(r[4].endswith('DIFFERENT.EXE') for r in old))

    def test_prefetch_damaged_header_is_not_repaired_into_typed_text(self):
        raw = prefetch()
        raw[16:18] = b'\x00\xd8'
        file = File('C:/Windows/Prefetch/DAMAGED.pf', raw)
        with patch.object(s, '_path', return_value=SimpleNamespace(iterdir=lambda: [file])):
            s._prefetch(self.out, self.ev, None)
        self.assertEqual(attrs(self.ev), [])
        self.assertEqual(len([r for r in self.ev.rows() if r[0] == 'programRun']), 2)

    def userassist(self, entries, hives=None, version=5, list_id='{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}'):
        root = 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist'
        guid = SimpleNamespace(name=list_id, path=root + '\\' + list_id,
                               values=lambda: [] if version is None else [SimpleNamespace(name='Version', value=version)])
        count = SimpleNamespace(path=guid.path + '\\Count',
                                values=lambda: [SimpleNamespace(name=codecs.encode(name, 'rot-13'), value=raw)
                                                for name, raw in entries])
        keys = {root: SimpleNamespace(subkeys=lambda: [guid]), count.path: count}
        if hives is None:
            hives = [s.Hive('SID-OTHER', None, 'D:\\Users\\Other\\NTUSER.DAT', False, 'Other', 'SID-OTHER')]
        with patch.object(s, '_open', side_effect=lambda ev, h, path: keys.get(path)):
            s._userassist(self.out, self.ev, hives)

    def test_userassist_only_explicit_executable_paths_and_exact_registry_locator(self):
        names = [r'D:\Tools\Run Here.exe', r'D:\Tools\Other.exe',
                 r'UEME_RUNPIDL:D:\Tools\PidL.exe', r'UEME_RUNCPL:D:\Tools\Control.exe',
                 r'{01234567-0123-0123-0123-0123456789AB}\Other.exe',
                 r'D:\Links\Target.lnk', r'D:\Panel\Control.cpl', r'%APPDATA%\Other.exe',
                 r'UEME_RUNPATH:"D:\Tools\Quoted.exe"', r'D:\Tools\Other.exe -arg',
                 r'D:\{01234567-0123-0123-0123-0123456789AB}\Other.exe']
        self.userassist([(name, userassist_value()) for name in names])
        self.assertEqual(self.ev.problems, [])
        values = attrs(self.ev)
        self.assertEqual({value for role, value, _ in values if role == 'app.execution.path'},
                         {r'D:\Tools\Run Here.exe', r'D:\Tools\Other.exe'})
        self.assertEqual(len(values), 4)
        for _, _, p in values:
            self.assertEqual(codecs.decode(p['source_value'], 'rot-13'), p['decoded_value_name'])
            self.assertEqual(p['raw_value_hex'], userassist_value().hex())
            self.assertEqual(p['source_entry']['hive'], 'D:\\Users\\Other\\NTUSER.DAT')
            self.assertEqual(p['recorded_time_us'], EVENT_US)
        self.assertGreater(len([r for r in self.ev.rows() if r[0] == 'programRun']), 2)

    def test_userassist_declared_version_guid_and_record_layout_must_match(self):
        xp = struct.pack('<IIQ', 1, 7, FILETIME)
        self.userassist([(r'UEME_RUNPATH:D:\Tools\XP.exe', xp)], version=3,
                        list_id='{75048700-EF1F-11D0-9888-006097DEACF9}')
        self.assertEqual({(r, v) for r, v, _ in attrs(self.ev)},
                         {('app.execution.program', 'XP.exe'), ('app.execution.path', r'D:\Tools\XP.exe')})
        negatives = [
            (None, '{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}', userassist_value(), r'D:\Tools\Other.exe'),
            (4, '{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}', userassist_value(), r'D:\Tools\Other.exe'),
            ('5', '{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}', userassist_value(), r'D:\Tools\Other.exe'),
            (5.0, '{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}', userassist_value(), r'D:\Tools\Other.exe'),
            (True, '{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}', userassist_value(), r'D:\Tools\Other.exe'),
            (5, '{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}', xp, r'D:\Tools\Other.exe'),
            (5, '{F4E57C4B-2036-45F0-A9AB-443BCFE33D9F}', userassist_value(), r'D:\Tools\Other.exe'),
            (5, '{UNKNOWN-LIST}', userassist_value(), r'D:\Tools\Other.exe'),
            (5, '{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}', userassist_value(), r'UEME_RUNPATH:D:\Tools\Other.exe'),
            (3, '{75048700-EF1F-11D0-9888-006097DEACF9}', userassist_value(), r'UEME_RUNPATH:D:\Tools\Other.exe'),
            (3, '{75048700-EF1F-11D0-9888-006097DEACF9}', xp, r'D:\Tools\Other.exe'),
            (3, '{UNKNOWN-LIST}', xp, r'UEME_RUNPATH:D:\Tools\Other.exe'),
        ]
        for version, list_id, raw, name in negatives:
            with self.subTest(version=version, list_id=list_id, length=len(raw), name=name):
                self.ev = Evidence()
                self.out = s._Out(self.ev, self.common, EXAMINED)
                self.userassist([(name, raw)], version=version, list_id=list_id)
                self.assertEqual(attrs(self.ev), [])
                self.assertEqual(len([r for r in self.ev.rows() if r[0] == 'programRun']), 1)

    def test_userassist_accepts_actual_dissect_reg_dword_version_subclass(self):
        try:
            from dissect.regf.regf import parse_value, REG_DWORD
        except ImportError:
            self.skipTest('optional dissect registry parser is unavailable')
        fixtures = [(5, '{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}', userassist_value(), r'D:\Tools\Modern.exe'),
                    (3, '{75048700-EF1F-11D0-9888-006097DEACF9}', struct.pack('<IIQ', 1, 7, FILETIME),
                     r'UEME_RUNPATH:D:\Tools\Legacy.exe')]
        for declared, guid, raw, name in fixtures:
            with self.subTest(declared=declared):
                version = parse_value(REG_DWORD, struct.pack('<I', declared))
                self.assertIsInstance(version, int)
                self.ev = Evidence()
                self.out = s._Out(self.ev, self.common, EXAMINED)
                self.userassist([(name, raw)], version=version, list_id=guid)
                values = attrs(self.ev)
                self.assertEqual(len(values), 2)
                self.assertEqual({p['userassist_version'] for _, _, p in values}, {declared})
                self.assertEqual({p['userassist_record_bytes'] for _, _, p in values}, {len(raw)})

    def test_userassist_no_run_time_and_different_hives_do_not_merge(self):
        self.userassist([(r'D:\Tools\Never.exe', bytes(72))])
        self.assertEqual(attrs(self.ev), [])
        hives = [s.Hive('SID-OTHER', None, name, backup, 'Other', 'SID-OTHER')
                 for name, backup in [('live.dat', False), ('backup.dat', True)]]
        self.userassist([(r'D:\Tools\Same.exe', userassist_value())], hives)
        self.assertEqual(len({r[4] for r in self.ev.rows() if r[0] == 'attributeSubject'}), 2)
        ev, out = self.ev, self.out
        self.ev = Evidence()
        self.out = s._Out(self.ev, self.common, EXAMINED)
        self.userassist([(r'D:\Tools\Same.exe', userassist_value())],
                        [s.Hive('SID-OTHER', None, ' ', False, 'Other', 'SID-OTHER')])
        self.assertEqual(attrs(self.ev), [])
        self.assertEqual(len(self.ev.rows()), 1)
        self.ev, self.out = ev, out

    def test_other_observation_readers_do_not_emit_execution_roles(self):
        timestamp = datetime(2015, 3, 25, tzinfo=timezone.utc)
        hive = s.Hive('SYSTEM', None, 'SYSTEM', False, None, None)
        path = r'\??\D:\Tools\Cache.exe'.encode('utf-16-le')
        raw = bytearray(0x80 + 48) + path + b'\0\0'
        struct.pack_into('<II', raw, 0, 0xBADC0FEE, 1)
        struct.pack_into('<HHIQQII', raw, 0x80, len(path), len(path) + 2, 0, 0x80 + 48, FILETIME, 2, 0)
        key = SimpleNamespace(timestamp=timestamp, values=lambda: [SimpleNamespace(name='AppCompatCache', value=bytes(raw))])
        with patch.object(s, '_control_sets', return_value=('ControlSet001', ['ControlSet001'])), patch.object(s, '_open', return_value=key):
            s._shimcache(self.out, self.ev, None, [hive])
        user = s.Hive('SID', None, 'NTUSER.DAT', False, 'Other', 'SID')
        mui = SimpleNamespace(timestamp=timestamp, values=lambda: [SimpleNamespace(name=r'D:\Tools\Mui.exe', value='description')])
        dialog = SimpleNamespace(timestamp=timestamp, values=lambda: [SimpleNamespace(name='0', value='Dialog.exe\0'.encode('utf-16-le'))])
        with patch.object(s, '_open', side_effect=lambda ev, h, path: dialog if path in s.DIALOG_MRU else mui):
            s._user_lists(self.out, self.ev, [user])
        job = bytearray(0x46)
        struct.pack_into('<H', job, 0x14, 0x46)
        struct.pack_into('<8H', job, 0x34, 2015, 3, 3, 25, 0, 0, 0, 0)
        for text in ('D:\\Tools\\Task.exe\0', '\0'):
            job += struct.pack('<H', len(text)) + text.encode('utf-16-le')
        with patch.object(s, '_path', return_value=SimpleNamespace(iterdir=lambda: [File('C:/Windows/Tasks/Test.job', job)])):
            s._jobs(self.out, self.ev, None, 'UTC')
        self.assertEqual(self.ev.problems, [])
        sources = {json.loads(r[-1])['source'] for r in self.ev.rows() if r[0] == 'programRun'}
        self.assertTrue({'application compatibility cache', 'MUICache', 'open/save dialog history',
                         'scheduled task file (.job)'} <= sources)
        self.assertEqual(attrs(self.ev), [])
        self.assertFalse(any(row[0].startswith('attribute') for row in self.ev.rows()))

    def test_sql_accepts_new_roles_without_changing_older_kind_contract(self):
        try:
            import duckdb
        except ImportError:
            self.skipTest('duckdb unavailable')
        db = duckdb.connect(':memory:')
        self.addCleanup(db.close)
        db.execute((Path(__file__).resolve().parents[1] / 'extractor/schema.sql').read_text())
        for number, kind in enumerate(('roleAppExecutionProgram', 'roleAppExecutionPath'), 1):
            db.execute('INSERT INTO facts VALUES (?, ?, 1, 1, 0, 0, ?)', [number, kind, '{}'])
        self.assertEqual(db.execute('SELECT count(*) FROM facts').fetchone()[0], 2)


if __name__ == '__main__':
    unittest.main()
