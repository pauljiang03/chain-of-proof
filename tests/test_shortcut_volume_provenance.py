"""Derived volume observations keep the shortcut's source scope and timestamp meaning."""
import json
import unittest

from extractor.store import Evidence
from extractor.windows import _volumes_in_shortcuts


class ShortcutVolumeProvenance(unittest.TestCase):
    def test_derivation_preserves_source_time_and_uncertainty_without_opening_claim(self):
        evidence = Evidence()
        common = {'image': 'pc.E01', 'exhibit': 'PC'}
        evidence.add('lnkTarget', 20_000, 1000, '\\file.txt', 'SERIAL',
                     volume_label='LABEL', artifact='Recent\\file.lnk',
                     time_meaning='shortcut file last-modified time',
                     timestamp_semantics='shortcut_file_modified', **common)
        self.assertEqual(_volumes_in_shortcuts(evidence, common), 1)
        row = next(row for row in evidence.rows() if row[0] == 'volumeSeen')
        self.assertEqual(row[1:3], (20_000, 1000))
        provenance = json.loads(row[5])
        self.assertEqual(provenance['time_meaning'], 'shortcut file last-modified time')
        self.assertEqual(provenance['timestamp_semantics'], 'shortcut_file_modified')
        self.assertNotIn('was opened', provenance['time_meaning'])

    def test_another_image_cannot_supply_the_earliest_record_or_its_label(self):
        evidence = Evidence()
        for image, exhibit, stamp, label in [('a.E01', 'A', 10, 'OTHER'), ('b.E01', 'B', 20, 'LOCAL')]:
            evidence.add('lnkTarget', stamp, 1, '\\file.txt', 'SHARED-SERIAL',
                         image=image, exhibit=exhibit, volume_label=label, artifact=image)
        self.assertEqual(_volumes_in_shortcuts(evidence, {'image': 'b.E01', 'exhibit': 'B'}), 1)
        rows = [row for row in evidence.rows() if row[0] == 'volumeSeen']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], 20)
        self.assertEqual(rows[0][3], 'LOCAL')
        self.assertEqual(json.loads(rows[0][5])['time_meaning'],
                         'unspecified originating shortcut record timestamp')
