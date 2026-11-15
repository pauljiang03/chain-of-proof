"""Origin labels follow the source view, including generated examination outputs."""
import json
import unittest
from unittest.mock import patch

from extractor import antivirus, content, image_integrity, system, windows
from extractor.source_scope import base_volume_scope, merge_scope, subject_scope, vss_snapshot
from extractor.store import Evidence


COPY_ID = '12345678-1234-5678-9ABC-0123456789AB'


class SourceOrigins(unittest.TestCase):
    def common(self, **updates):
        return dict(image='fixture.E01', exhibit='OTHER', **base_volume_scope(), **updates)

    def test_unknown_is_not_promoted_and_specific_scope_wins_without_mutation(self):
        original = {'image': 'a', 'exhibit': 'b'}
        self.assertEqual(subject_scope(original), ['a', 'b', 'unknown', 'unknown'])
        self.assertEqual(original, {'image': 'a', 'exhibit': 'b'})
        common = self.common()
        result = merge_scope(common, {'source_snapshot': 'vss:{' + COPY_ID + '}',
                                     'source_variant': 'registry-backup:retained'})
        self.assertEqual(result['source_snapshot'], 'vss:' + COPY_ID.lower())
        self.assertEqual(result['source_variant'], 'registry-backup:retained')
        self.assertEqual(common['source_snapshot'], 'base-volume')
        self.assertEqual(merge_scope(common, {'source_snapshot': None})['source_snapshot'], 'unknown')

    def test_vss_identity_is_explicit_and_canonical(self):
        self.assertEqual(vss_snapshot('{' + COPY_ID + '}'), 'vss:' + COPY_ID.lower())
        for invalid in ('not-a-copy', '', True, 123):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                vss_snapshot(invalid)
        self.assertEqual(merge_scope({'source_snapshot': 'vss:not-a-copy'})['source_snapshot'], 'unknown')

    def test_image_digest_sources_are_not_filesystem_views_but_compare_same_image(self):
        ev = Evidence()
        result = {'logical_bytes': 4, 'representation': 'ewf_logical_image', 'segments': ['fixture.E01'],
                  'computed': {'md5': 'a' * 32},
                  'recorded': [{'algorithm': 'md5', 'digest': 'a' * 32,
                                'segment': 'fixture.E01', 'section': 'hash', 'offset': 40}]}
        with patch.object(image_integrity, 'inspect', return_value=result):
            image_integrity.extract(ev, 'fixture.E01', {'common': self.common(), 'examined_at': 100})
        origins = {(json.loads(row[-1])['source_snapshot'], json.loads(row[-1])['source_variant'])
                   for row in ev.rows()}
        self.assertEqual(origins, {('evidence-image', 'logical-image'),
                                  ('evidence-image', 'acquisition-container')})
        subjects = {row[4] for row in ev.rows() if row[0] == 'attributeSubject'}
        self.assertEqual(len(subjects), 1, 'comparison relates two source observations of one image')

    def test_scanner_output_binds_the_exact_input_view(self):
        result = {'scanner_version': 'fixture scanner', 'files': [], 'transcript': '',
                  'complete_allocated_scope': True, 'detections': [], 'omitted': [], 'errors': [],
                  'scope': 'synthetic allocated-file scan'}
        subject_sets = []
        for origin in (base_volume_scope(), {'source_snapshot': vss_snapshot(COPY_ID), 'source_variant': 'primary'},
                       {'source_snapshot': 'unknown', 'source_variant': 'unknown'}):
            ev = Evidence()
            common = merge_scope(self.common(), origin)
            with patch.object(antivirus, 'scan', return_value=result):
                antivirus.extract(ev, object(), {'common': common, 'examined_at': 100})
            for row in ev.rows():
                provenance = json.loads(row[-1])
                self.assertEqual(provenance['source_snapshot'], 'examination')
                self.assertEqual(provenance['source_variant'], 'antivirus')
                self.assertEqual(provenance['input_source'], origin)
            subject_sets.append({row[4] for row in ev.rows() if row[0] == 'attributeSubject'})
        self.assertTrue(subject_sets[0].isdisjoint(subject_sets[1]))
        self.assertTrue(subject_sets[0].isdisjoint(subject_sets[2]))

    def test_recovered_content_does_not_inherit_primary_variant(self):
        ev = Evidence()
        content._row(ev, {'common': self.common(), 'examined_at': 100},
                     'old.txt', 'a' * 64, 1, b'x', 'unallocated', 'recovered sector',
                     recovered=True, source_variant='unallocated-recovery')
        provenance = json.loads(ev.rows()[0][-1])
        self.assertEqual(provenance['source_snapshot'], 'base-volume')
        self.assertEqual(provenance['source_variant'], 'unallocated-recovery')

    def test_derived_shortcut_volume_keeps_each_origin(self):
        ev = Evidence()
        for stamp, origin in enumerate((base_volume_scope(),
                {'source_snapshot': vss_snapshot(COPY_ID), 'source_variant': 'primary'},
                {'source_snapshot': 'unknown', 'source_variant': 'unknown'}), start=1):
            ev.add('lnkTarget', stamp, 1, 'target.txt', 'SERIAL',
                   volume_label='DATA', artifact='a.lnk', **merge_scope(self.common(), origin))
        self.assertEqual(windows._volumes_in_shortcuts(ev, self.common()), 3)
        values = [json.loads(row[-1]) for row in ev.rows() if row[0] == 'volumeSeen']
        self.assertEqual({p['source_snapshot'] for p in values},
                         {'base-volume', vss_snapshot(COPY_ID), 'unknown'})

    def test_unknown_currentness_does_not_collapse_distinct_control_sets(self):
        ev = Evidence()
        out = system._Out(ev, self.common())
        for control_set in ('ControlSet001', 'ControlSet002'):
            out.add('sessionEvent', 100, 1, 'shutdown', _copy=True,
                    hive='C:\\Windows\\System32\\config\\SYSTEM', control_set=control_set,
                    source_variant='unknown')
        self.assertEqual(len(ev.rows()), 2)
        self.assertEqual({json.loads(row[-1])['control_set'] for row in ev.rows()},
                         {'ControlSet001', 'ControlSet002'})


if __name__ == '__main__':
    unittest.main()
