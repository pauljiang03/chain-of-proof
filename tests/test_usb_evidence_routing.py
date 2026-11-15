"""Exact USB source-role gaps route only through configured Windows readers."""
from unittest.mock import patch

from agent.evidence_requests import bind_config, catalog, recommendations, KINDS
from checker.catalog import ROLES
from checker.facts import KINDS as FACT_KINDS
from tests.test_intake import IntakeFixture

USB_ROLES = ('usb.device_instance_id', 'usb.device_id', 'usb.instance_id',
             'usb.recorded_time', 'usb.record_time_meaning', 'usb.source_type')


def gap(kind, category='missing_record'):
    return {'status': 'diagnostic', 'requirements': [{'category': category,
        'reason': 'Synthetic exact typed source-record gap.',
        'action': 'Consider the configured source reader.', 'required': {'kind': kind}}]}


class UsbEvidenceRouting(IntakeFixture):
    def setUp(self):
        super().setUp()
        self.initial = self.make()
        self.run = self.root/'run'
        self.run.mkdir()
        bind_config(self.run, self.initial['config'], self.initial['facts'])

    def test_capabilities_add_only_six_reviewed_role_kinds_and_shared_text_triple_rows(self):
        original = {'usbInsert', 'volumeSeen', 'lnkTarget', 'webSearch', 'fileCreated',
                    'fileModified', 'fileDeleted', 'emailSent', 'cdBurn'}
        added = {ROLES[role].kind for role in USB_ROLES} | {'attributeSubject', 'attributeTextValue'}
        self.assertEqual(KINDS['windows'], original | added)
        windows = [row for row in catalog(self.run) if row['reader'] == 'windows']
        self.assertEqual([(row['reader'], row['exhibit']) for row in windows], [('windows', 'Computer A')])
        self.assertEqual(set(windows[0]['supported_record_kinds']), original | added)
        self.assertFalse(windows[0]['already_collected'])
        self.assertTrue(all(ROLES[role].value_type == 'string' for role in USB_ROLES))

    def test_exact_missing_and_wrong_typed_kinds_recommend_configured_windows(self):
        kinds = [ROLES[role].kind for role in USB_ROLES] + ['attributeSubject', 'attributeTextValue']
        for kind in kinds:
            for category in ('missing_record', 'wrong_record_type'):
                with self.subTest(kind=kind, category=category):
                    result = recommendations(self.run, gap(kind, category))
                    self.assertEqual([(row['reader'], row['exhibit']) for row in result['recommendations']],
                                     [('windows', 'Computer A')])
                    self.assertEqual(result['evidence_needs'][0]['candidate_readers'], ['windows'])
                    self.assertFalse(result['evidence_needs'][0]['requires_review'])
                    self.assertIn('does not establish', result['note'])
        self.assertEqual(self.calls, [('inventory', 'Computer A')])

    def test_unknown_role_or_prefix_does_not_trigger_a_family_guess(self):
        for kind in ('usb.not_reviewed', 'roleUsbInvented', ROLES[USB_ROLES[0]].kind+'NotReviewed'):
            result = recommendations(self.run, gap(kind))
            self.assertEqual(result['recommendations'], [])
            self.assertEqual(result['evidence_needs'][0]['candidate_readers'], [])

    def test_identity_and_count_gaps_are_not_promoted_into_collection_guarantees(self):
        for category in ('contradictory_identity_or_value', 'cardinality_mismatch'):
            result = recommendations(self.run, gap(ROLES[USB_ROLES[0]].kind, category))
            self.assertEqual(result['recommendations'], [])
            self.assertTrue(result['evidence_needs'][0]['requires_review'])

    def test_existing_collected_and_pending_snapshot_constraints_are_preserved(self):
        windows = next(row for row in catalog(self.run) if row['reader'] == 'windows')
        with patch('agent.evidence_requests.catalog', return_value=[dict(windows, already_collected=True)]):
            self.assertEqual(recommendations(self.run, gap(ROLES[USB_ROLES[0]].kind))['recommendations'], [])
        pending = {'reader': 'windows', 'exhibit': 'Computer A', 'status': 'completed'}
        with patch('agent.evidence_requests._pending', return_value=pending):
            result = recommendations(self.run, gap(ROLES[USB_ROLES[0]].kind))
            self.assertTrue(result['continuation_required'])
            self.assertEqual(result['recommendations'], [])
        (self.run/'intake-config.json').unlink()
        result = recommendations(self.run, gap(ROLES[USB_ROLES[0]].kind))
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['recommendations'], [])

    def test_typed_rows_are_queryable_and_forms_expose_roles_without_usb_insert(self):
        from extractor.attributes import emit_attribute
        from extractor.store import Evidence
        from agent.tools import Workbench
        evidence = Evidence()
        for role in USB_ROLES:
            emit_attribute(evidence, 'synthetic:USBSTOR:literal-instance', role, 'fixture source text', 100,
                           artifact='synthetic USB source', image='machine.img', exhibit='Computer A',
                           source_snapshot='base-volume', source_variant='primary')
        facts = self.root/'typed-facts.json'
        evidence.write_json(facts, {})
        typed_run = self.root/'typed-run'
        typed_run.mkdir()
        bench = Workbench(facts, typed_run)
        try:
            rows = bench.sql('SELECT kind, COUNT(*) AS n FROM facts GROUP BY kind ORDER BY kind')['rows']
            counts = dict(rows)
            self.assertEqual(counts['attributeSubject'], 6)
            self.assertEqual(counts['attributeTextValue'], 6)
            self.assertNotIn('usbInsert', counts)
            for role in USB_ROLES:
                self.assertEqual(counts[ROLES[role].kind], 1)
            forms = bench.forms()
            self.assertTrue(all(role in forms['attribute_roles'] for role in USB_ROLES))
            self.assertIn('attributeTuple', forms['forms'])
            self.assertIn('attributeRecorded', forms['forms'])
        finally:
            bench._db.close()

    def test_catalog_fact_and_generic_attribute_form_reachability_without_identity_promotion(self):
        from agent.tools import FORMS
        from agent.answer_projection import catalog as projection_catalog
        self.assertIn('attributeRecorded', FORMS)
        self.assertIn('attributeTuple', FORMS)
        fields = projection_catalog()['forms']
        for role in USB_ROLES:
            self.assertIn(ROLES[role].kind, FACT_KINDS)
            self.assertIn(ROLES[role].semantic_type, fields['attributeRecorded']['value']['allowed_semantic_types'])
            self.assertIn(ROLES[role].semantic_type, fields['attributeTuple']['value_0']['allowed_semantic_types'])
        self.assertFalse(any('usb.device_count' == role or 'usb.hardware_serial' == role for role in USB_ROLES))


if __name__ == '__main__':
    import unittest
    unittest.main()
