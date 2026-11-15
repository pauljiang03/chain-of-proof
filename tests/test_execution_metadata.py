"""Typed execution metadata from synthetic source bytes, without model calls."""
import codecs
from datetime import datetime, timezone
import hashlib
import json
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from checker.catalog import decode_value
from extractor import system as s
from extractor.store import Evidence
from tests.test_execution_attributes import File, prefetch


EXAMINED = 1800000000123456
FILETIME = 130717152000000000
EVENT_US = 1427241600000000
V3_GUID = '{75048700-EF1F-11D0-9888-006097DEACF9}'
V5_GUID = '{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}'
PREFIX = 'app.execution.'
UNSET = object()


def values(ev):
    subjects = {row[3]: row[4] for row in ev.rows() if row[0] == 'attributeSubject'}
    grouped = {}
    for row in ev.rows():
        if row[0] not in ('attributeTextValue', 'attributeIntegerValue'):
            continue
        provenance = json.loads(row[-1])
        name = provenance['attribute_role']
        if name.startswith(PREFIX):
            grouped.setdefault(subjects[row[3]], {})[name[len(PREFIX):]] = (
                decode_value(row[4], provenance['attribute_value_type']), provenance)
    return grouped


def userassist_raw(version, count=9, ft=FILETIME):
    if version == 3:
        return struct.pack('<IIQ', 1, count, ft)
    return struct.pack('<4I', 1, count, 2, 17) + bytes(44) + struct.pack('<Q', ft) + bytes(4)


class ExecutionMetadata(unittest.TestCase):
    def setUp(self):
        self.ev = Evidence()
        self.common = {'image': 'synthetic.E01', 'exhibit': 'OTHER-PC',
                       'source_snapshot': 'base-volume', 'source_variant': 'primary'}
        self.out = s._Out(self.ev, self.common, EXAMINED)

    def userassist(self, version=5, raw=None, hives=None, declared=UNSET, guid=None):
        raw = userassist_raw(version) if raw is None else raw
        guid = guid or (V3_GUID if version == 3 else V5_GUID)
        declared = version if declared is UNSET else declared
        root = r'Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist'
        path = r'D:\Other Tools\unrelated.exe'
        decoded = ('UEME_RUNPATH:' if version == 3 else '') + path
        node = SimpleNamespace(name=guid, path=root + '\\' + guid,
                               values=lambda: [SimpleNamespace(name='Version', value=declared)])
        count = SimpleNamespace(path=node.path + '\\Count',
                                values=lambda: [SimpleNamespace(name=codecs.encode(decoded, 'rot-13'), value=raw)])
        keys = {root: SimpleNamespace(subkeys=lambda: [node]), count.path: count}
        hives = hives or [s.Hive('SID-OTHER', None, r'D:\Users\Other\NTUSER.DAT', False, 'Other', 'SID-OTHER')]
        with patch.object(s, '_open', side_effect=lambda ev, hive, path: keys.get(path)):
            s._userassist(self.out, self.ev, hives)

    def read_prefetch(self, raw=None):
        raw = prefetch() if raw is None else raw
        path = File('D:/Windows/Prefetch/OTHER.pf', raw)
        with patch.object(s, '_path', return_value=SimpleNamespace(iterdir=lambda: [path])):
            s._prefetch(self.out, self.ev, None)
        return raw

    def security(self, **changes):
        record = dict(EventID=4688, Provider_Name=s.A, Channel='Security',
                      ts=datetime(2015, 3, 25, tzinfo=timezone.utc),
                      NewProcessName=r'D:\Other Tools\unrelated.exe', EventRecordID=42,
                      source='D:/Windows/System32/winevt/Logs/Security.evtx')
        record.update(changes)
        s._event(self.out, self.ev, record, 'Security.evtx record 42', {})

    def test_prefetch_metadata_has_same_occurrence_subject_and_literal_counter(self):
        raw = self.read_prefetch()
        records = values(self.ev)
        self.assertEqual(len(records), 2)
        for fields in records.values():
            self.assertEqual(set(fields), {'program', 'recorded_time', 'source_type', 'time_meaning',
                                           'run_count', 'raw_run_count'})
            self.assertEqual(fields['program'][0], 'DIFFERENT.EXE')
            self.assertEqual(fields['source_type'][0], 'Prefetch')
            self.assertEqual(fields['time_meaning'][0], 'execution')
            self.assertEqual(fields['run_count'][0], 2)
            self.assertEqual(fields['raw_run_count'][0], 2)
            source = fields['raw_run_count'][1]['attribute_value_source']
            self.assertEqual(struct.unpack_from('<I', raw, source['byte_offset'])[0], 2)
            self.assertEqual(source['byte_length'], 4)
            self.assertNotIn('byte_offset', fields['recorded_time'][1])
            self.assertEqual(fields['recorded_time'][1]['execution_identity_locator']['byte_offset'], 16)
            self.assertEqual(fields['recorded_time'][1]['recorded_time_resolution_us'], 1)
        self.assertEqual({fields['recorded_time'][0] for fields in records.values()},
                         {'2015-03-25T00:00:00.000000Z', '2015-03-24T23:59:59.000000Z'})
        self.assertTrue(all(row[1] == EXAMINED for row in self.ev.rows() if row[0].startswith(('attribute', 'roleAppExecution'))))
        self.assertEqual(self.ev.problems, [])

    def test_prefetch_time_locator_keeps_original_slot_after_unset_slot(self):
        raw = prefetch()
        struct.pack_into('<Q', raw, 0x88, 0)
        struct.pack_into('<Q', raw, 0x90, FILETIME + 19)
        self.read_prefetch(raw)
        fields = next(fields for fields in values(self.ev).values()
                      if fields['recorded_time'][0] == '2015-03-25T00:00:00.000001Z')
        locator = fields['recorded_time'][1]['attribute_value_source']
        self.assertEqual((locator['slot'], locator['byte_offset']), (2, 0x90))
        self.assertEqual(locator['raw_value'], FILETIME + 19)
        self.assertIn('// 10', locator['conversion'])

    def test_compressed_prefetch_offsets_are_not_claimed_as_original_file_offsets(self):
        from dissect.util.compression import lzxpress_huffman
        raw = prefetch()
        compressed = b'MAM\x04' + struct.pack('<I', len(raw)) + b'synthetic-compressed-body'
        with patch.object(lzxpress_huffman, 'decompress', return_value=raw):
            self.read_prefetch(compressed)
        for fields in values(self.ev).values():
            for name in ('recorded_time', 'run_count', 'raw_run_count'):
                provenance = fields[name][1]
                self.assertEqual(provenance['attribute_value_source']['byte_offset_basis'], 'decompressed Prefetch bytes')
                self.assertEqual(provenance['source_sha256'], hashlib.sha256(compressed).hexdigest())

    def test_userassist_v5_counter_and_time_are_source_fields(self):
        raw = userassist_raw(5, count=17, ft=FILETIME + 1234567)
        self.userassist(raw=raw)
        fields, = values(self.ev).values()
        self.assertEqual(set(fields), {'program', 'path', 'recorded_time', 'source_type', 'time_meaning',
                                      'run_count', 'raw_run_count'})
        self.assertEqual((fields['run_count'][0], fields['raw_run_count'][0]), (17, 17))
        self.assertEqual(fields['recorded_time'][0], '2015-03-25T00:00:00.123456Z')
        self.assertEqual(fields['source_type'][0], 'UserAssist')
        self.assertEqual(fields['time_meaning'][0], 'execution')
        locator = fields['recorded_time'][1]['attribute_value_source']
        self.assertEqual(locator['byte_offset'], 60)
        self.assertEqual(struct.unpack_from('<Q', raw, locator['byte_offset'])[0], locator['raw_value'])
        self.assertEqual(fields['run_count'][1]['attribute_value_source']['adjustment'], 0)

    def test_xp_raw_counter_and_minus_five_interpretation_are_distinct(self):
        raw = userassist_raw(3, count=12)
        self.userassist(version=3, raw=raw)
        fields, = values(self.ev).values()
        self.assertEqual((fields['raw_run_count'][0], fields['run_count'][0]), (12, 7))
        locator = fields['run_count'][1]['attribute_value_source']
        self.assertEqual((locator['raw_value'], locator['adjustment']), (12, 5))
        self.assertEqual(locator['derivation'], 'raw counter minus 5')
        self.assertEqual(fields['recorded_time'][1]['attribute_value_source']['byte_offset'], 8)
        old = next(row for row in self.ev.rows() if row[0] == 'programRun')
        self.assertEqual(json.loads(old[-1])['run_count'], 7)
        self.assertEqual(json.loads(old[-1])['raw_run_count'], 12)

    def test_xp_below_five_does_not_invent_zero_executions(self):
        self.userassist(version=3, raw=userassist_raw(3, count=4))
        fields, = values(self.ev).values()
        self.assertEqual(fields['raw_run_count'][0], 4)
        self.assertNotIn('run_count', fields)
        self.assertIn('interpreted count unavailable', fields['raw_run_count'][1]['run_count_status'])
        self.assertTrue(any('below 5' in problem for problem in self.ev.problems))
        # Frozen legacy row interpretation is unchanged and explicitly labelled.
        old = next(row for row in self.ev.rows() if row[0] == 'programRun')
        self.assertEqual(json.loads(old[-1])['run_count'], 0)
        self.assertIn('legacy display', json.loads(old[-1])['run_count_interpretation'])

    def test_recorded_zero_counters_are_not_absence(self):
        for version, count in ((3, 5), (5, 0)):
            with self.subTest(version=version):
                self.setUp()
                self.userassist(version=version, raw=userassist_raw(version, count=count))
                fields, = values(self.ev).values()
                self.assertEqual(fields['run_count'][0], 0)
                self.assertEqual(fields['raw_run_count'][0], count)
                self.assertEqual(self.ev.problems, [])

    def test_security_timestamp_is_not_examination_time_or_a_fabricated_count(self):
        self.security()
        fields, = values(self.ev).values()
        self.assertEqual(set(fields), {'program', 'path', 'recorded_time', 'source_type', 'time_meaning'})
        self.assertEqual(fields['recorded_time'][0], '2015-03-25T00:00:00.000000Z')
        self.assertEqual(fields['recorded_time'][1]['attribute_value_source']['retained_resolution_us'], 1000000)
        self.assertEqual(fields['source_type'][0], 'Security process creation')
        self.assertNotIn(fields['source_type'][0], {'Prefetch', 'UserAssist', 'Shimcache', 'MuiCache'})
        self.assertEqual(fields['time_meaning'][0], 'execution')

    def test_unavailable_times_and_wrong_source_layouts_emit_no_typed_metadata(self):
        for version, declared, raw, guid in ((3, 3, userassist_raw(3, ft=0), V3_GUID),
                                             (5, 5, userassist_raw(5, ft=0), V5_GUID),
                                             (5, None, userassist_raw(5), V5_GUID),
                                             (5, 4, userassist_raw(5), V5_GUID),
                                             (5, 5, userassist_raw(3), V5_GUID),
                                             (5, 5, userassist_raw(5), '{UNKNOWN-LIST}')):
            with self.subTest(version=version, declared=declared, length=len(raw), guid=guid):
                self.setUp()
                self.userassist(version=version, declared=declared, raw=raw, guid=guid)
                self.assertEqual(values(self.ev), {})
        self.setUp()
        raw = prefetch()
        raw[0x80:0xc0] = bytes(64)
        self.read_prefetch(raw)
        self.assertEqual(values(self.ev), {})
        for change in ({'ts': None}, {'Channel': 'Application'}, {'Provider_Name': 'OTHER'}):
            self.setUp()
            self.security(**change)
            self.assertEqual(values(self.ev), {})

    def test_timestamp_bounds_fail_without_falling_back_to_examination_time(self):
        for timestamp in (None, -1, True, 1.5, 10 ** 30):
            self.setUp()
            s._execution_attributes(self.out, 'A.EXE', None, timestamp, 'Prefetch header', 'A.pf', {'run_index': 1})
            self.assertEqual(values(self.ev), {})
        self.assertTrue(self.ev.problems)

    def test_recovered_registry_and_vss_subjects_do_not_merge_metadata(self):
        primary = s.Hive('SID', None, r'D:\Users\Other\NTUSER.DAT', False, 'Other', 'SID')
        backup = primary._replace(path=r'D:\RegBack\NTUSER.DAT', backup=True)
        self.userassist(hives=[primary, backup])
        self.out = s._Out(self.ev, dict(self.common, source_snapshot='vss:00000000-0000-0000-0000-000000000001'), EXAMINED)
        self.userassist(hives=[primary])
        records = values(self.ev)
        self.assertEqual(len(records), 3)
        scopes = set()
        for subject, fields in records.items():
            self.assertEqual(len(fields), 7)
            self.assertEqual({(p['source_snapshot'], p['source_variant']) for _, p in fields.values()},
                             {tuple(json.loads(subject)[2:4])})
            scopes.add(tuple(json.loads(subject)[2:4]))
        self.assertEqual(len(scopes), 3)


if __name__ == '__main__':
    unittest.main()
