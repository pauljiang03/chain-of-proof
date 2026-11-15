"""Real-kernel adversarial controls for file-occurrence and volume-serial scope."""
import copy
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from checker import check as checker
from checker.catalog import ROLES
from checker.facts import Fact, FactSource, JsonFacts, KINDS, file_occurrence
from verifier.verify import verify


def origin():
    return {'image': 'disk-A.E01', 'exhibit': 'A', 'source_snapshot': 'base-volume',
            'source_variant': 'primary', 'artifact': 'synthetic NTFS STANDARD_INFORMATION',
            'file_occurrence': {'schema_version': 1, 'disk_index': 0,
                'partition_offset_bytes': 1048576, 'partition_size_bytes': 536870912,
                'entry_kind': 'ntfs_mft', 'entry_id': 42, 'entry_sequence': 3}}


class Source(FactSource):
    def __init__(self, created=None, modified=None, modified_time=10_000_000):
        self.rows = [Fact(1, 'fileCreated', 30_000_000, 1, 1, 2,
                          origin() if created is None else created),
                     Fact(2, 'fileModified', modified_time, 1, 1, 2,
                          origin() if modified is None else modified)]

    def get(self, ids):
        return {row.id: row for row in self.rows if row.id in ids}

    def all(self):
        return self.rows

    def string(self, sid):
        return {1: r'\report.txt', 2: 'DEADBEEF', 3: 'ORIGINAL-A', 4: 'USB-B'}.get(sid, str(sid))


class FileOccurrenceSoundness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sequence = 0

    def certify(self, source, *, accepted=True, claim=None):
        self.sequence += 1
        with patch.object(checker, 'run_kernel', wraps=checker.run_kernel) as kernel:
            result = checker.check(claim or {'copiedHere': [1, 2]}, f'Occurrence{self.sequence}',
                                   source, out_dir=self.root)
        self.assertTrue(kernel.called, 'The actual formal kernel must enforce occurrence identity')
        self.assertEqual(result['status'], 'verified' if accepted else 'rejected', result)
        if accepted:
            self.assertEqual(result['axioms'], [])
            self.assertEqual(result['trust_tier'], 'kernel')
            self.assertEqual(verify(result, source), [])
        return result

    def test_same_native_occurrence_certifies_pattern_and_replays(self):
        cert = self.certify(Source())
        self.assertEqual(cert['strength'], 'heuristic')
        self.assertIn('same scoped native file occurrence', cert['english'])
        self.assertIn('does not establish a copying action', cert['english'])
        self.assertNotIn('was likely copied', cert['english'])
        lean = (self.root / cert['lean_file']).read_text()
        self.assertIn('Sets.copiedHere 1 2', lean)
        # Identity is formal data, not merely a diagnostic or answer guard.
        self.assertIn(str(file_occurrence(origin())[5]), lean)

    def test_cross_images_and_partitions_cannot_be_joined(self):
        changes = [('image', 'disk-B.E01'), ('exhibit', 'B'),
                   ('source_snapshot', 'vss:11111111-1111-1111-1111-111111111111'),
                   ('source_variant', 'unallocated-recovery'), ('disk_index', 1),
                   ('partition_offset_bytes', 2097152), ('partition_size_bytes', 1073741824),
                   ('entry_id', 43), ('entry_sequence', 4)]
        for name, value in changes:
            modified = origin()
            (modified if name in modified else modified['file_occurrence'])[name] = value
            with self.subTest(dimension=name):
                cert = self.certify(Source(modified=modified), accepted=False)
                self.assertIn('FAIL sameFileOccurrence 1 2', cert['parts'][0]['bricks'])

    def test_old_path_and_serial_only_counterexamples_fail_closed(self):
        first = {key: value for key, value in origin().items() if key != 'file_occurrence'}
        second = dict(first, image='disk-B.E01', exhibit='B')
        for modified in (first, second, dict(first, partition_offset=2097152)):
            with self.subTest(modified=modified):
                self.certify(Source(created=first, modified=modified), accepted=False)

    def test_missing_and_malformed_dimensions_fail_in_kernel(self):
        malformed = []
        for key in origin()['file_occurrence']:
            value = origin()
            del value['file_occurrence'][key]
            malformed.append(value)
        for key in ('image', 'exhibit', 'source_snapshot', 'source_variant'):
            value = origin()
            value[key] = 'unknown'
            malformed.append(value)
        for native in (True, '42', 42.0, -1, 2**64):
            value = origin()
            value['file_occurrence']['entry_id'] = native
            malformed.append(value)
        for value in malformed:
            with self.subTest(provenance=value):
                self.assertIsNone(file_occurrence(value))
        # One absent and one malformed actual claim exercise the kernel, not a
        # Python-only rejection; validation cases above cover the full adapter.
        self.certify(Source(created={}), accepted=False)
        self.certify(Source(modified=malformed[-1]), accepted=False)

    def test_native_offsets_are_partition_relative_and_bounded(self):
        for kind in ('fat_directory_entry', 'exfat_directory_entry', 'udf_file_entry', 'iso9660_directory_record'):
            valid = origin()
            valid['file_occurrence'].update(entry_kind=kind, entry_id=8192)
            del valid['file_occurrence']['entry_sequence']
            self.assertIsNotNone(file_occurrence(valid))
            wrong = copy.deepcopy(valid)
            wrong['file_occurrence']['entry_id'] = wrong['file_occurrence']['partition_size_bytes']
            self.assertIsNone(file_occurrence(wrong))
        self.certify(Source(created=valid, modified=valid))
        other = copy.deepcopy(valid)
        other['file_occurrence']['entry_kind'] = 'fat_directory_entry'
        self.certify(Source(created=valid, modified=other), accepted=False)

    def test_identity_does_not_bypass_existing_time_path_or_serial_checks(self):
        self.certify(Source(modified_time=29_999_999), accepted=False)
        source = Source()
        row = source.rows[1]
        source.rows[1] = Fact(row.id, row.kind, row.t, row.res, row.obj + 1, row.aux, row.prov)
        self.certify(source, accepted=False)
        source = Source()
        row = source.rows[1]
        source.rows[1] = Fact(row.id, row.kind, row.t, row.res, row.obj, row.aux + 1, row.prov)
        self.certify(source, accepted=False)

    def test_replay_binds_native_identity_and_provenance(self):
        source = Source()
        cert = self.certify(source)
        altered = copy.deepcopy(cert)
        altered['cited_facts'][0]['prov']['file_occurrence']['partition_offset_bytes'] += 4096
        self.assertTrue(verify(altered, source))
        altered_source = Source()
        altered_source.rows[0].prov['file_occurrence']['entry_sequence'] += 1
        self.assertTrue(verify(cert, altered_source))

    def test_diagnostics_separate_missing_metadata_from_conflicting_identity(self):
        missing = self.certify(Source(created={}), accepted=False)
        need = next(row for row in missing['proof_gap']['requirements']
                    if 'file-occurrence' in row['reason'])
        self.assertEqual(need['category'], 'missing_record')
        self.assertIn('Matching paths or volume serials do not supply this identity', need['action'])
        wrong = origin()
        wrong['file_occurrence']['partition_offset_bytes'] *= 2
        conflict = self.certify(Source(modified=wrong), accepted=False)
        need = next(row for row in conflict['proof_gap']['requirements']
                    if 'different encoded source file occurrences' in row['reason'])
        self.assertEqual(need['category'], 'contradictory_identity_or_value')
        self.assertIn('Preserve the conflicting', need['action'])

    def test_equal_serials_do_not_assert_volume_identity(self):
        source = Source()
        source.rows = [Fact(1, 'volumeSeen', 10_000_000, 1, 3, 2, dict(origin(), image='A.E01')),
                       Fact(2, 'volumeOnDevice', 40_000_000, 1, 4, 2, dict(origin(), image='B.E01'))]
        cert = self.certify(source, claim={'recordedOnDevice': [1, 2]})
        self.assertIn('same recorded volume serial DEADBEEF', cert['english'])
        self.assertIn('do not establish that these are the same volume or physical device', cert['english'])
        self.assertNotIn('is the volume on seized device', cert['english'])

    def test_usb_roles_are_append_only_and_sql_matches(self):
        roles = ['usb.device_instance_id', 'usb.device_id', 'usb.instance_id', 'usb.recorded_time',
                 'usb.record_time_meaning', 'usb.source_type']
        self.assertEqual(KINDS[236], 'roleMailRecoveredBodyUnicode')
        self.assertEqual(KINDS[237:], tuple(ROLES[role].kind for role in roles))
        root = Path(__file__).resolve().parent.parent
        sql = (root / 'extractor/schema.sql').read_text()
        kinds_sql = re.findall(r"'([A-Za-z][A-Za-z0-9]+)'", sql.split('kind IN (', 1)[1].split(')),', 1)[0])
        self.assertEqual(list(KINDS), kinds_sql)


if __name__ == '__main__':
    unittest.main()
