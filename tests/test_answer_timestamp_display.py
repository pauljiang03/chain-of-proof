"""Prospective public report displays freeze identically before gate filtering."""
from copy import deepcopy
import json
import unittest

from agent.answer_projection import claim_digest, prepare_projection, render_projection
from checker.catalog import ROLES
from checker.facts import Fact, FactSource


POLICY = {'kind': 'report_timestamp_iso_v1', 'timezone': 'public_time_zone'}
STAMP = '2024-11-03T06:30:00.123456700Z'
DISPLAY = '2024-11-03T01:30:00.123456700-05:00'


class Source(FactSource):
    def __init__(self, stamp=STAMP, role='machine.last_shutdown'):
        self.strings = {1: 'identity', 2: 'synthetic-host', 3: role, 4: json.dumps(stamp)}
        self.rows = {f.id: f for f in (
            Fact(1, 'attributeSubject', 123, 1, 1, 2),
            Fact(2, ROLES[role].kind, 123, 1, 1, 3),
            Fact(3, 'attributeTextValue', 123, 1, 1, 4))}

    def get(self, ids):
        return {i: self.rows[i] for i in ids if i in self.rows}

    def string(self, sid):
        return self.strings[sid]

    def all(self):
        raise AssertionError('projection must not scan source')


def fixture():
    leaf = {'type': 'string', 'format': 'date-time', 'x-claim-display': deepcopy(POLICY),
            'x-claim-requirement': {
                'semantic_types': [ROLES['machine.last_shutdown'].semantic_type],
                'meaning': 'Recorded synthetic shutdown instant.',
                'evidence_needed': 'Source retained typed shutdown instant.'}}
    public = {'schema_version': 2, 'case_id': 'synthetic-report-display',
              'time_zone': 'America/New_York', 'questions': [
                  {'id': 'Q', 'prompt': 'When?', 'answer_schema': leaf}]}
    candidate = {'candidate_id': 'C', 'claim': {'attributeRecorded': [1, 2, 3, 'machine.last_shutdown']}}
    binding = {'candidate_id': 'C', 'claim_sha256': claim_digest(candidate['claim']),
               'question_id': 'Q', 'path': [], 'field': 'value'}
    return public, candidate, binding


class AnswerTimestampDisplay(unittest.TestCase):
    def plan(self, public=None, candidate=None, binding=None, source=None):
        p, c, b = fixture()
        return prepare_projection(public or p, [candidate or c], [binding or b], source or Source(),
                                  require_claim_requirements=True)

    def rejected(self, public=None, candidate=None, binding=None, source=None):
        plan = self.plan(public, candidate, binding, source)
        self.assertEqual(plan['bindings'], [])
        self.assertEqual(len(plan['unsupported']), 1)
        return plan['unsupported'][0]['reason']

    def test_a_b_c_share_exact_frozen_display_and_source(self):
        p, c, b = fixture()
        before = deepcopy((p, c, b))
        plan = self.plan(p, c, b)
        self.assertEqual((p, c, b), before)
        self.assertEqual(plan['unsupported'], [])
        leaf = plan['bindings'][0]
        self.assertEqual(leaf['source_value'], STAMP)
        self.assertEqual(leaf['value'], DISPLAY)
        self.assertEqual(leaf['display']['source_utc'], STAMP)
        self.assertEqual(leaf['display']['fraction_digits'], 9)
        self.assertEqual(leaf['display']['interpretation'], 'report_display_only')
        submissions = [render_projection(plan, admitted_ids=ids, authority=authority)['submission']
                       for ids, authority in [(None, 'unchecked'), (['C'], 'recorded_certificates'),
                                              (['C'], 'independently_replayed')]]
        self.assertEqual(submissions[0], submissions[1])
        self.assertEqual(submissions[1], submissions[2])
        self.assertEqual(submissions[0]['answers'][0]['answer'], DISPLAY)
        self.assertEqual(render_projection(plan, admitted_ids=[])['submission']['answers'][0]['status'], 'unknown')

    def test_manual_value_must_be_exact_display(self):
        p, c, b = fixture()
        b['value'] = DISPLAY
        self.assertTrue(self.plan(p, c, b)['bindings'])
        b['value'] = STAMP
        self.assertEqual(self.rejected(p, c, b), 'literal_value_mismatch_not_repaired')
        b['value'] = DISPLAY.replace('123456700', '1234567')
        self.rejected(p, c, b)

    def test_without_annotation_identity_remains_literal(self):
        p, c, b = fixture()
        del p['questions'][0]['answer_schema']['x-claim-display']
        plan = self.plan(p, c, b)
        self.assertEqual(plan['bindings'][0]['value'], STAMP)
        self.assertNotIn('source_value', plan['bindings'][0])
        self.assertNotIn('display', plan['bindings'][0])
        b['value'] = DISPLAY
        self.rejected(p, c, b)

    def test_invalid_policy_field_type_and_format(self):
        for change in ({'type': 'integer'}, {'type': ['string', 'null']}, {'format': 'date'},
                       {'x-claim-display': {'kind': 'other', 'timezone': 'public_time_zone'}},
                       {'x-claim-display': dict(POLICY, extra=True)}):
            p, c, b = fixture()
            p['questions'][0]['answer_schema'].update(change)
            self.rejected(p, c, b)
        for missing in ('type', 'format'):
            p, c, b = fixture()
            del p['questions'][0]['answer_schema'][missing]
            self.rejected(p, c, b)

    def test_no_naive_invalid_zone_or_combined_binding_conversion(self):
        for zone in (None, '', 'Invalid/Zone', 'Central Daylight Time'):
            p, c, b = fixture()
            p['time_zone'] = zone
            self.rejected(p, c, b)
        self.rejected(source=Source('2024-01-01T00:00:00'))
        p, c, b = fixture()
        b['format'] = 'utc_iso'
        self.assertEqual(self.rejected(p, c, b), 'display_policy_requires_identity_binding_format')

    def test_wrong_role_is_not_repaired_by_display(self):
        p, c, b = fixture()
        c['claim']['attributeRecorded'][3] = 'os.install_time'
        b['claim_sha256'] = claim_digest(c['claim'])
        self.rejected(p, c, b, Source(role='os.install_time'))

    def test_aligned_iso_shaped_non_temporal_and_unreviewed_roles_cannot_convert(self):
        for role in ('os.product_name', 'account.last_logon', 'search.index.date_created',
                     'event.recorded_time'):
            with self.subTest(role=role):
                p, c, b = fixture()
                c['claim']['attributeRecorded'][3] = role
                b['claim_sha256'] = claim_digest(c['claim'])
                p['questions'][0]['answer_schema']['x-claim-requirement']['semantic_types'] = [ROLES[role].semantic_type]
                self.assertEqual(self.rejected(p, c, b, Source(role=role)),
                                 'claim_role_has_no_reviewed_timestamp_display_capability')
                # The same reviewed role remains a perfectly ordinary literal
                # when no display conversion was requested.
                del p['questions'][0]['answer_schema']['x-claim-display']
                self.assertEqual(self.plan(p, c, b, Source(role=role))['bindings'][0]['value'], STAMP)

    def test_reviewed_install_instant_can_convert(self):
        p, c, b = fixture()
        role = 'os.install_time'
        c['claim']['attributeRecorded'][3] = role
        b['claim_sha256'] = claim_digest(c['claim'])
        p['questions'][0]['answer_schema']['x-claim-requirement']['semantic_types'] = [ROLES[role].semantic_type]
        self.assertEqual(self.plan(p, c, b, Source(role=role))['bindings'][0]['value'], DISPLAY)

    def test_anyof_requires_unambiguous_policy_and_all_role_requirements(self):
        p, c, b = fixture()
        leaf = p['questions'][0]['answer_schema']
        p['questions'][0]['answer_schema'] = {'anyOf': [deepcopy(leaf), deepcopy(leaf)]}
        self.assertTrue(self.plan(p, c, b)['bindings'])
        del p['questions'][0]['answer_schema']['anyOf'][1]['x-claim-display']
        self.assertEqual(self.rejected(p, c, b), 'ambiguous_public_display_policy')
        p['questions'][0]['answer_schema']['anyOf'][1] = deepcopy(leaf)
        p['questions'][0]['answer_schema']['anyOf'][1]['x-claim-requirement']['semantic_types'] = [ROLES['os.install_time'].semantic_type]
        self.rejected(p, c, b)

    def test_policy_and_report_zone_bound_by_plan_digest(self):
        plan = self.plan()
        altered = deepcopy(plan)
        altered['bindings'][0]['display']['report_timezone'] = 'UTC'
        with self.assertRaises(ValueError):
            render_projection(altered)
        p, c, b = fixture()
        p['time_zone'] = 'UTC'
        utc_plan = self.plan(p, c, b)
        self.assertNotEqual(plan['public_sha256'], utc_plan['public_sha256'])
        self.assertNotEqual(plan['projection_sha256'], utc_plan['projection_sha256'])

    def test_nested_policy_and_conjunctive_anyof_sibling(self):
        p, c, b = fixture()
        leaf = p['questions'][0]['answer_schema']
        requirement = leaf.pop('x-claim-requirement')
        leaf['anyOf'] = [{'x-claim-requirement': deepcopy(requirement)},
                         {'x-claim-requirement': deepcopy(requirement)}]
        p['questions'][0]['answer_schema'] = {'type': 'object', 'properties': {'at': leaf}}
        b['path'] = ['at']
        self.assertEqual(self.plan(p, c, b)['bindings'][0]['value'], DISPLAY)
        leaf['anyOf'][1]['type'] = 'integer'
        self.rejected(p, c, b)


if __name__ == '__main__':
    unittest.main()
