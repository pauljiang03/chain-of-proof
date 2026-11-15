"""Synthetic Search-row intervals constrain certified bindings, not native values."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, project_answers
from agent.answer_requirements import KEY, check as check_requirement, inspect, parse
from agent.answer_projection import catalog
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify


URL = 'search.index.item_url'
TIME = 'search.index.date_modified'
STORE = 'search.index.store'
START = '2012-04-05T00:00:00Z'
STOP = '2012-04-06T00:00:00Z'


def requirement():
    return {'semantic_types': [ROLES[URL].semantic_type],
            'meaning': 'Recorded Search item URL in the declared store and modification interval.',
            'evidence_needed': 'Same typed Search row, not an inference of a browser visit.',
            'selectors': [{'form': 'attributeTuple', 'field': 'value_0'}],
            'attribute_conditions': [{'role': STORE, 'values': ['SyntheticHistory']}],
            'attribute_timestamp_conditions': [{'mode': 'recorded_instant_half_open_v1',
                'role': TIME, 'start': START, 'stop': STOP}]}


class AnswerTimestampConditions(unittest.TestCase):
    def project_row(self, stamps, store='SyntheticHistory', mixed_subject=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ev = Evidence()
            identities = []
            values = [(URL, 'https://synthetic.invalid/item')] + stamps + [(STORE, store)]
            for index, (role, value) in enumerate(values):
                subject = 'synthetic:other-row' if mixed_subject and role == TIME else 'synthetic:row'
                identities.append(emit_attribute(ev, subject, role, value, 1800000000000000,
                    artifact=f'synthetic Search ESE field {index}', image='synthetic.E01'))
            path = root / 'facts.json'
            ev.write_json(path, {})
            source = JsonFacts(path)
            entries = []
            for identity, (role, _) in zip(identities, values):
                rows = {fact.kind: fact.id for fact in source.all() if source.string(fact.obj) == identity}
                entries.append([rows['attributeSubject'], rows[ROLES[role].kind],
                                rows[ROLES[role].value_kind], role])
            claim = {'attributeTuple': entries}
            certificate = check(claim, 'SyntheticInterval', source, out_dir=root)
            if mixed_subject:
                self.assertEqual(certificate['status'], 'rejected', certificate)
                return None
            self.assertEqual(certificate['status'], 'verified', certificate)
            self.assertEqual(certificate['trust_tier'], 'kernel')
            self.assertEqual(verify(certificate, source), [])
            public = {'schema_version': 2, 'case_id': 'synthetic-time-policy', 'questions': [
                {'id': 'Q', 'prompt': 'Recorded row URL?', 'answer_schema': {'type': 'object',
                    'properties': {'url': {'type': 'string', KEY: requirement()}},
                    'additionalProperties': False}}]}
            binding = {'candidate_id': certificate['finding_id'], 'claim_sha256': claim_digest(claim),
                       'question_id': 'Q', 'path': ['url'], 'part': 0, 'field': 'value_0'}
            return project_answers(public, [certificate], [binding], source,
                                   authority='recorded_certificates')

    def test_valid_half_open_bounds_preserve_native_precision_and_offset(self):
        for stamp in (START, '2012-04-05T23:59:59.9999999Z',
                      '2012-04-05T03:30:00.1234567+03:30'):
            with self.subTest(stamp=stamp):
                result = self.project_row([(TIME, stamp)])
                self.assertEqual(result['unsupported'], [])
                self.assertEqual(result['submission']['answers'][0]['answer'],
                                 {'url': 'https://synthetic.invalid/item'})
                # Qualification does not replace the recorded timestamp with a
                # rounded or timezone-shifted value, or bind an invented visit.
                fields = {'value_0': {'semantic_type': ROLES[URL].semantic_type, 'value': 'url'},
                          'value_1': {'semantic_type': ROLES[TIME].semantic_type, 'value': stamp},
                          'value_2': {'semantic_type': ROLES[STORE].semantic_type, 'value': 'SyntheticHistory'}}
                before = deepcopy(fields)
                diagnostic = check_requirement(requirement(), 'attributeTuple', 'value_0',
                                               ROLES[URL].semantic_type, part_fields=fields)
                self.assertEqual(diagnostic['status'], 'compatible')
                self.assertEqual(len(diagnostic['attribute_timestamp_condition_checks']), 1)
                self.assertEqual(fields, before)

    def test_certified_rows_without_unique_valid_in_range_role_are_not_answers(self):
        cases = [([], 'SyntheticHistory'),
                 ([('search.index.date_created', START)], 'SyntheticHistory'),
                 ([(TIME, '2012-04-04T23:59:59.9999999Z')], 'SyntheticHistory'),
                 ([(TIME, STOP)], 'SyntheticHistory'),
                 ([(TIME, '2012-04-05T12:00:00')], 'SyntheticHistory'),
                 ([(TIME, '2012-04-05T12:00:00-00:00')], 'SyntheticHistory'),
                 ([(TIME, '2012-04-05T12:00:00.12345678Z')], 'SyntheticHistory'),
                 ([(TIME, START)], 'OtherStore')]
        for stamps, store in cases:
            with self.subTest(stamps=stamps, store=store):
                result = self.project_row(stamps, store)
                self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
                self.assertEqual(result['unsupported'][0]['reason'],
                                 'claim_attributes_do_not_meet_public_requirement')

    def test_duplicate_typed_timestamp_fields_are_ambiguous_even_when_values_agree(self):
        # The tuple parser already forbids duplicate roles. The public boundary
        # must also refuse ambiguous fields supplied by any future claim form.
        fields = {'value_0': {'semantic_type': ROLES[URL].semantic_type, 'value': 'url'},
                  'value_1': {'semantic_type': ROLES[TIME].semantic_type, 'value': START},
                  'value_2': {'semantic_type': ROLES[TIME].semantic_type, 'value': START},
                  'value_3': {'semantic_type': ROLES[STORE].semantic_type, 'value': 'SyntheticHistory'}}
        result = check_requirement(requirement(), 'attributeTuple', 'value_0',
                                   ROLES[URL].semantic_type, part_fields=fields)
        self.assertEqual(result['status'], 'incompatible')
        self.assertEqual(result['reason'], 'claim_attributes_do_not_meet_public_requirement')
        self.assertEqual(result['attribute_timestamp_condition_checks'][0]['status'], 'ambiguous')

    def test_mixed_source_subject_is_kernel_rejected_before_policy_can_license_it(self):
        self.project_row([(TIME, START)], mixed_subject=True)

    def test_other_part_metadata_and_wrong_native_type_cannot_fill_timestamp(self):
        foreign = {'value_1': {'semantic_type': ROLES[TIME].semantic_type, 'value': START}}
        fields = {'value_0': {'semantic_type': ROLES[URL].semantic_type, 'value': 'url',
                              'provenance': foreign, 'other_part': foreign},
                  'value_2': {'semantic_type': ROLES[STORE].semantic_type, 'value': 'SyntheticHistory'}}
        for value in (None, 0, True, {}, []):
            with self.subTest(value=value):
                current = deepcopy(fields)
                if value is not None:
                    current['value_1'] = {'semantic_type': ROLES[TIME].semantic_type, 'value': value}
                result = check_requirement(requirement(), 'attributeTuple', 'value_0',
                                           ROLES[URL].semantic_type, part_fields=current)
                self.assertEqual(result['status'], 'incompatible')
                self.assertEqual(result['reason'], 'claim_attributes_do_not_meet_public_requirement')

    def test_policy_shape_roles_and_bounds_are_explicit_in_preflight(self):
        good = requirement()
        self.assertEqual(parse(good), good)
        bad = [[], [good['attribute_timestamp_conditions'][0]] * 2,
               [dict(good['attribute_timestamp_conditions'][0], role='search.index.date_created')],
               [dict(good['attribute_timestamp_conditions'][0], start=STOP)],
               [dict(good['attribute_timestamp_conditions'][0], stop='2012-04-06')],
               [dict(good['attribute_timestamp_conditions'][0], mode='truncate_to_day')],
               [dict(good['attribute_timestamp_conditions'][0], extra=True)]]
        for policies in bad:
            with self.subTest(policies=policies):
                raw = deepcopy(good)
                raw['attribute_timestamp_conditions'] = policies
                with self.assertRaises(ValueError):
                    parse(raw)
                self.assertEqual(inspect({'type': 'string', KEY: raw}, catalog()['forms'])
                                 ['requirements'][0]['status'], 'invalid')


if __name__ == '__main__':
    unittest.main()
