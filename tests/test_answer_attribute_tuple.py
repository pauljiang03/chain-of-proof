"""Typed tuple answers preserve atomic row identity and exact public choices."""
import hashlib
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from agent.answer_projection import claim_digest, project_answers, render_projection
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from tests.test_answer_requirements import need
from verifier.verify import verify

ORIGIN = {'image': 'synthetic.E01', 'exhibit': 'PC', 'source_snapshot': 'base-volume', 'source_variant': 'primary'}
VALUES = [('os.product_name', 'Fixture OS'), ('os.version', '6.1'), ('os.build_number', 1234),
          ('os.system_root', r'C:\Windows'), ('os.registered_owner', 'Fixture owner'),
          ('os.install_time', '2001-02-03T00:00:00Z')]


class AttributeTupleAnswers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        ev = Evidence()
        self.identities = {}
        for role, value in VALUES:
            self.identities[role] = emit_attribute(ev, 'PC:OS:CurrentVersion', role, value, 100,
                                                  artifact='synthetic registry', **ORIGIN)
        self.other = emit_attribute(ev, 'PC:other:CurrentVersion', 'os.version', '9.9', 100,
                                    artifact='synthetic other registry', **ORIGIN)
        self.boolean = emit_attribute(ev, 'PC:scanner', 'scanner.detections_found', True, 100,
                                      artifact='synthetic scanner', **ORIGIN)
        ev.write_json(self.root/'facts.json', {})
        self.source = JsonFacts(self.root/'facts.json')
        self.digest = hashlib.sha256((self.root/'facts.json').read_bytes()).hexdigest()
        self.entries = [self.entry(self.identities[role], role) for role, _ in VALUES]
        self.row = {'candidate_id': 'TUPLE', 'claim': {'attributeTuple': deepcopy(self.entries)}}

    def entry(self, identity, role):
        rows = {fact.kind: fact.id for fact in self.source.all() if self.source.string(fact.obj) == identity}
        spec = ROLES[role]
        return [rows['attributeSubject'], rows[spec.kind], rows[spec.value_kind], role]

    def public(self, count=6):
        from agent.answer_requirements import KEY, SCOPE_KEY
        return {'schema_version': 2, 'case_id': 'synthetic-tuple', 'questions': [{
            'id': 'Q', 'prompt': 'Record the same source OS row.', 'answer_schema': {
                'type': 'object', 'x-claim-row': {'mode': 'same_claim_part'},
                SCOPE_KEY: {'mode': 'source_records', 'origins': [ORIGIN]},
                'properties': {str(i): {'type': ROLES[role].value_type,
                    KEY: need(ROLES[role].semantic_type)} for i, (role, _) in enumerate(VALUES[:count])}}}]}

    def binding(self, row, index, field=None, part=0):
        return {'candidate_id': row.get('candidate_id', row.get('finding_id')),
                'claim_sha256': claim_digest(row['claim']), 'question_id': 'Q', 'path': [str(index)],
                'part': part, 'field': field or 'value_'+str(index)}

    def project(self, row=None, public=None, bindings=None):
        row = row or self.row
        return project_answers(public or self.public(), [row], bindings or [self.binding(row, i) for i in range(6)],
                               self.source, require_claim_requirements=True, require_evidence_scope=True,
                               evidence_facts_sha256=self.digest)

    def test_six_field_tuple_certifies_replays_and_preserves_typed_values(self):
        cert = check(self.row['claim'], 'CERT', self.source, out_dir=self.root)
        self.assertEqual(cert['status'], 'verified', cert)
        self.assertEqual(verify(cert, self.source), [])
        result = self.project()
        self.assertEqual(result['submission']['answers'][0]['answer'], {str(i): value for i, (_, value) in enumerate(VALUES)})
        all_ids = {fid for entry in self.entries for fid in entry[:3]}
        for i, leaf in enumerate(result['leaves']):
            self.assertEqual(set(leaf['record_ids']), all_ids)
            self.assertEqual(leaf['value_record_ids'], [self.entries[i][2]])
            self.assertEqual(leaf['semantic_type'], ROLES[VALUES[i][0]].semantic_type)

    def test_invalid_tuple_semantics_remain_literal_a_but_checker_filters_whole_candidate(self):
        mixed = deepcopy(self.entries)
        mixed[1] = self.entry(self.other, 'os.version')
        wrong = deepcopy(self.entries)
        wrong[1][3] = 'os.time_zone_setting'
        duplicate = deepcopy(self.entries)
        duplicate[1] = deepcopy(duplicate[0])
        for index, entries in enumerate((mixed, wrong, duplicate)):
            with self.subTest(index=index):
                row = {'candidate_id': 'BAD'+str(index), 'claim': {'attributeTuple': entries}}
                # Generic untyped schema exposes exact literal unchecked values;
                # role guards are tested separately rather than hiding A's claim.
                contract = self.public()
                contract['questions'][0]['answer_schema'] = {'type': 'object'}
                bindings = [self.binding(row, i) for i in range(6)]
                a = project_answers(contract, [row], bindings, self.source)
                self.assertEqual(len(a['leaves']), 6)
                cert = check(row['claim'], 'BAD'+str(index), self.source, out_dir=self.root)
                self.assertNotEqual(cert['status'], 'verified')
                b = render_projection(a['projection'], admitted_ids=[], authority='recorded_certificates')
                self.assertEqual(b['submission']['answers'][0]['status'], 'unknown')

    def test_tuple_inside_both_is_one_part_but_separate_parts_cannot_repair_row(self):
        row = {'candidate_id': 'BOTH', 'claim': {'both': [self.row['claim'], {'attributeRecorded': self.entries[0]}]}}
        self.assertEqual(len(self.project(row)['leaves']), 6)
        bindings = [self.binding(row, i) for i in range(6)]
        bindings[0] = self.binding(row, 0, field='value', part=1)
        result = self.project(row, bindings=bindings)
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertTrue(any(item['reason'] == 'row_fields_require_same_claim_part' for item in result['conflicts']))

    def test_missing_tuple_entry_field_is_not_filled(self):
        row = {'candidate_id': 'SHORT', 'claim': {'attributeTuple': self.entries[:2]}}
        result = self.project(row)
        self.assertEqual(len(result['leaves']), 2)
        self.assertEqual(len(result['unsupported']), 4)
        self.assertEqual(result['submission']['answers'][0]['answer'], {'0': VALUES[0][1], '1': VALUES[1][1]})

    def test_scope_checks_other_tuple_entry_even_when_binding_only_first_value(self):
        from checker.facts import Fact
        other_id = self.entries[5][2]
        original = self.source._facts[other_id]
        self.source._facts[other_id] = Fact(original.id, original.kind, original.t, original.res,
            original.obj, original.aux, dict(original.prov, source_snapshot='vss:other'))
        result = self.project(bindings=[self.binding(self.row, 0)])
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_records_do_not_meet_public_scope')

    def test_strict_enum_and_const_preserve_exact_json_types(self):
        for constraint, reason in (({'enum': ['different OS']}, 'value_not_in_public_schema_enum'),
                                   ({'const': 'different OS'}, 'value_does_not_match_public_schema_const')):
            contract = self.public()
            contract['questions'][0]['answer_schema']['properties']['0'].update(constraint)
            result = self.project(public=contract, bindings=[self.binding(self.row, 0)])
            self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
            self.assertEqual(result['unsupported'][0]['reason'], reason)
        boolean = self.entry(self.boolean, 'scanner.detections_found')
        row = {'candidate_id': 'BOOL', 'claim': {'attributeTuple': [boolean, self.entries[0]]}}
        for constraint, reason in (({'enum': [1]}, 'value_not_in_public_schema_enum'),
                                   ({'const': 1}, 'value_does_not_match_public_schema_const')):
            contract = self.public(1)
            schema = contract['questions'][0]['answer_schema']['properties']['0']
            schema.clear()
            from agent.answer_requirements import KEY
            schema.update({'type': 'boolean', KEY: need(ROLES['scanner.detections_found'].semantic_type), **constraint})
            result = project_answers(contract, [row], [self.binding(row, 0)], self.source,
                                     require_claim_requirements=True, require_evidence_scope=True, evidence_facts_sha256=self.digest)
            self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
            self.assertEqual(result['unsupported'][0]['reason'], reason)

    def test_positive_choices_and_legacy_enum_boundary_preserve_value(self):
        for choice in ({'enum': [VALUES[0][1]]}, {'const': VALUES[0][1]}):
            contract = self.public(1)
            contract['questions'][0]['answer_schema']['properties']['0'].update(choice)
            accepted = self.project(public=contract, bindings=[self.binding(self.row, 0)])
            self.assertEqual(accepted['submission']['answers'][0]['answer'], {'0': VALUES[0][1]})
            self.assertEqual(accepted['unsupported'], [])
        contract = self.public(1)
        contract['questions'][0]['answer_schema']['properties']['0']['enum'] = ['different OS']
        legacy = project_answers(contract, [self.row], [self.binding(self.row, 0)], self.source,
                                 require_claim_requirements=False, require_evidence_scope=True,
                                 evidence_facts_sha256=self.digest)
        self.assertEqual(legacy['submission']['answers'][0]['answer'], {'0': VALUES[0][1]})
        self.assertEqual(legacy['unsupported'], [])

    def test_legacy_attribute_recorded_projection_remains_unchanged(self):
        row = {'candidate_id': 'LEGACY', 'claim': {'attributeRecorded': self.entries[0]}}
        contract = self.public(1)
        result = project_answers(contract, [row], [self.binding(row, 0, field='value')], self.source,
                                 require_claim_requirements=True, require_evidence_scope=True,
                                 evidence_facts_sha256=self.digest)
        self.assertEqual(result['submission']['answers'][0]['answer'], {'0': VALUES[0][1]})


if __name__ == '__main__':
    unittest.main()
