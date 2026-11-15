"""Identifier collisions certify matching record values, never physical identity."""
import copy
from pathlib import Path
import tempfile
import unittest

from checker.check import check
from checker.facts import Fact, FactSource
from verifier.verify import verify


class CollisionSource(FactSource):
    def __init__(self):
        self.strings = {0: '(none)', 1: 'SHARED-IDENTIFIER', 2: 'SHARED-RECOVERY-LABEL',
                        3: r'\file.txt', 4: 'DEADBEEF', 5: 'disc B', 6: 'OTHER-ID', 7: 'OTHER-LABEL'}
        def record(fid, kind, stamp, obj, aux):
            return Fact(fid, kind, stamp, 1, obj, aux, {
                'image': f'DIFFERENT-IMAGE-{fid}.E01', 'exhibit': f'EXHIBIT-{fid}',
                'source_snapshot': 'base-volume', 'source_variant': 'primary',
                'partition_offset': fid * 1048576,
                'artifact': f'synthetic independent source {fid}',
                'time_meaning': 'recorded source field; not independently verified action time'})
        self.rows = [record(1, 'usbInsert', 10_000_000, 1, 0),
                     record(2, 'unallocatedOnDevice', 50_000_000, 1, 2),
                     record(3, 'fileCreated', 30_000_000, 3, 2),
                     record(4, 'fileCreated', 30_000_000, 3, 4),
                     record(5, 'volumeRecorded', 10_000_000, 5, 4),
                     record(6, 'volumeMount', 20_000_000, 1, 4),
                     record(7, 'volumeOnDevice', 50_000_000, 1, 4),
                     record(8, 'unallocatedOnDevice', 50_000_000, 6, 7),
                     record(9, 'volumeRecorded', 10_000_000, 5, 7)]

    def get(self, ids):
        return {row.id: row for row in self.rows if row.id in ids}

    def all(self):
        return self.rows

    def string(self, sid):
        return self.strings[sid]


class IdentifierJoinClaims(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.source = CollisionSource()
        self.sequence = 0

    def certify(self, claim, accepted=True):
        self.sequence += 1
        cert = check(claim, f'Collision{self.sequence}', self.source, out_dir=self.path)
        self.assertEqual(cert['status'], 'verified' if accepted else 'rejected', cert)
        if accepted:
            self.assertEqual(cert['axioms'], [])
            self.assertEqual(cert['trust_tier'], 'kernel')
            self.assertEqual(verify(cert, self.source), [])
        return cert

    def test_device_examination_identifies_only_matching_recorded_identifiers(self):
        cert = self.certify({'deviceExamined': [1, 2]})
        text = cert['english']
        self.assertIn('matching recorded device identifier SHARED-IDENTIFIER', text)
        self.assertIn('do not establish that the records refer to the same physical device', text)
        self.assertIn('synthetic independent source 1', text)
        self.assertIn('synthetic independent source 2', text)
        self.assertNotIn('recovered directory entries on device', text)
        self.certify({'deviceExamined': [1, 8]}, accepted=False)

    def test_recovery_area_collision_never_assigns_the_file_to_a_physical_device(self):
        cert = self.certify({'recoveredOnDevice': [3, 2]})
        text = cert['english']
        self.assertIn('same recorded recovery-area label SHARED-RECOVERY-LABEL', text)
        self.assertIn('do not establish that the entry came from that physical device', text)
        self.assertIn('or from the same source area', text)
        self.assertIn('synthetic independent source 3', text)
        self.assertIn('synthetic independent source 2', text)
        self.assertNotIn('was recovered from', text)
        self.certify({'recoveredOnDevice': [3, 8]}, accepted=False)

    def test_optical_timeline_qualifies_nonunique_volume_serial(self):
        cert = self.certify({'createdAfterVolumeRecord': [4, 5]})
        text = cert['english']
        self.assertIn('matching recorded volume serial DEADBEEF', text)
        self.assertIn('Different volumes can share this serial; their volume identity is not established', text)
        self.assertIn('more than the combined timestamp uncertainty', text)
        self.assertIn('does not establish that a burn or copy completed', text)
        self.assertNotIn('the same volume (', text)
        self.certify({'createdAfterVolumeRecord': [4, 9]}, accepted=False)

    def test_other_usb_joins_keep_nonunique_identifier_qualification(self):
        for claim in ({'usbMountedAs': [1, 6]}, {'deviceHolds': [1, 7]}):
            with self.subTest(claim=claim):
                text = self.certify(claim)['english']
                self.assertIn('Recorded identifiers are not guaranteed unique', text)
                self.assertIn('do not by themselves establish physical-device identity', text)

    def test_replay_refuses_promoted_physical_identity_wording(self):
        for claim in ({'deviceExamined': [1, 2]}, {'recoveredOnDevice': [3, 2]},
                      {'createdAfterVolumeRecord': [4, 5]}):
            with self.subTest(claim=claim):
                cert = self.certify(claim)
                promoted = copy.deepcopy(cert)
                promoted['english'] = 'This is the same physical device and volume.'
                self.assertTrue(verify(promoted, self.source))

    def test_content_hash_match_never_promotes_hash_equality_to_byte_identity(self):
        self.source.strings.update({8: 'sha256:' + 'ab' * 32, 9: 'sha256:' + 'cd' * 32,
                                    10: r'\other.txt'})
        self.source.rows = [Fact(1, 'fileContent', 10_000_000, 1, 3, 8, {'exhibit': 'A'}),
                            Fact(2, 'fileContent', 10_000_000, 1, 10, 8, {'exhibit': 'B'}),
                            Fact(3, 'fileContent', 10_000_000, 1, 10, 9, {'exhibit': 'C'})]
        cert = self.certify({'sameContent': [1, 2]})
        self.assertIn('same recorded content hash sha256:' + 'ab' * 32, cert['english'])
        self.assertIn('does not independently prove byte-for-byte identity or source authenticity', cert['english'])
        self.assertNotIn('identical content', cert['english'])
        self.certify({'sameContent': [1, 3]}, accepted=False)
        promoted = copy.deepcopy(cert)
        promoted['english'] = 'These files have identical authentic content.'
        self.assertTrue(verify(promoted, self.source))


if __name__ == '__main__':
    unittest.main()
