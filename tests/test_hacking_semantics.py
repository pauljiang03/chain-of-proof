"""Source-bound attribute roles, typed values and exact image comparisons use Lean.

All fixtures are synthetic. No case image, private reference or expected case answer
is consulted. These tests exercise the actual kernel and independent certificate replay.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.answer_projection import catalog, claim_digest, project_answers
from agent import answer_requirements
from checker import check, claims
from checker.catalog import ATTRIBUTE_KINDS, ROLES
from checker.facts import JsonFacts
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify


class HackingSemantics(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ev = Evidence()
        self.identities = {}
        values = (
            ('os', 'image-A:machine', 'os.product_name', 'Fixture OS'),
            ('owner', 'image-A:machine', 'os.registered_owner', 'Fixture name'),
            ('count', 'image-A:machine', 'account.count', 3),
            ('enabled', 'image-A:account:1001', 'account.enabled', False),
            ('logical', 'image-A:logical', 'image.logical.md5', 'a' * 32),
            ('acquired', 'image-A:logical', 'image.acquisition.md5', 'a' * 32),
            ('different', 'image-A:logical', 'image.acquisition.md5', 'b' * 32),
            ('other_image', 'image-B:logical', 'image.acquisition.md5', 'a' * 32),
            ('sha1', 'image-A:logical', 'image.logical.sha1', 'c' * 40),
            ('scan', 'image-A:scan:1', 'scanner.detections_found', False),
            ('scope', 'image-A:scan:1', 'scanner.scope', 'allocated regular files only; archive recursion disabled'),
        )
        self.roles = {}
        for key, subject, role, value in values:
            self.roles[key] = role
            self.identities[key] = emit_attribute(self.ev, subject, role, value, 1_000_000,
                artifact='synthetic source', image='fixture-image', source_path='/fixture/config', field=key)
        self.path = self.root / 'facts.json'
        self.ev.write_json(self.path, {})
        self.source = JsonFacts(self.path)
        self.sequence = 0

    def triple(self, key):
        rows = {f.kind: f.id for f in self.source.all()
                if self.source.string(f.obj) == self.identities[key]}
        spec = ROLES[self.roles[key]]
        return [rows['attributeSubject'], rows[spec.kind], rows[spec.value_kind]]

    def attribute(self, key):
        return {'attributeRecorded': self.triple(key) + [self.roles[key]]}

    def certify(self, claim, accepted=True):
        self.sequence += 1
        result = check.check(claim, f'T{self.sequence}', self.source, out_dir=self.root / 'certs')
        self.assertEqual(result['status'], 'verified' if accepted else 'rejected', result)
        if accepted:
            self.assertEqual(result['trust_tier'], 'kernel')
            self.assertEqual(result['axioms'], [])
            self.assertEqual(verify(result, self.source), [])
        else:
            self.assertFalse((self.root / 'certs' / f'T{self.sequence}.json').exists())
        return result

    def test_actual_lean_certifies_source_role_and_native_integer_boolean_values(self):
        certs = [self.certify(self.attribute(key)) for key in ('os', 'count', 'enabled')]
        contract = {'schema_version': 2, 'case_id': 'arbitrary-fixture', 'questions': [
            {'id': 'Q', 'prompt': 'Recorded fields?', 'answer_schema': {'type': 'object', 'properties': {
                'os': {'type': 'string'}, 'count': {'type': 'integer'}, 'enabled': {'type': 'boolean'}}}}]}
        bindings = [{'candidate_id': cert['finding_id'], 'claim_sha256': claim_digest(cert['claim']),
                     'question_id': 'Q', 'path': [field], 'field': 'value', 'part': 0}
                    for cert, field in zip(certs, ('os', 'count', 'enabled'))]
        output = project_answers(contract, certs, bindings, self.source, authority='recorded_certificates')
        self.assertEqual(output['submission']['answers'][0]['answer'],
                         {'os': 'Fixture OS', 'count': 3, 'enabled': False})
        self.assertIn('examined', certs[0]['english'])
        self.assertIn('not personal attribution', certs[0]['english'])
        self.assertEqual(output['question_completeness'], 'not_established')

    def test_wrong_role_wrong_triple_and_wrong_value_kind_are_kernel_refused(self):
        self.certify({'attributeRecorded': self.triple('os') + ['os.registered_owner']}, False)
        mixed = self.triple('os')[:1] + self.triple('owner')[1:]
        self.certify({'attributeRecorded': mixed + ['os.registered_owner']}, False)
        data = json.loads(self.path.read_text())
        value_id = self.triple('count')[2]
        next(row for row in data['facts'] if row['id'] == value_id)['kind'] = 'attributeTextValue'
        self.path.write_text(json.dumps(data))
        self.source = JsonFacts(self.path)
        self.certify({'attributeRecorded': self.triple('os')[:2] + [value_id, 'os.product_name']}, False)
        # Correct identity and role cannot turn generic text into a numeric value.
        rows = {f.kind: f.id for f in self.source.all()
                if self.source.string(f.obj) == self.identities['count']}
        self.certify({'attributeRecorded': [rows['attributeSubject'], rows[ROLES['account.count'].kind],
                                           value_id, 'account.count']}, False)

    def test_digest_equality_requires_same_subject_exact_roles_algorithm_and_value(self):
        self.certify({'imageDigestsAgree': self.triple('logical') + self.triple('acquired') + ['md5']})
        for key, algorithm in (('different', 'md5'), ('other_image', 'md5'), ('acquired', 'sha1')):
            with self.subTest(key=key, algorithm=algorithm):
                self.certify({'imageDigestsAgree': self.triple('logical') + self.triple(key) + [algorithm]}, False)
        self.certify({'imageDigestsAgree': self.triple('sha1') + self.triple('acquired') + ['md5']}, False)
        self.certify({'imageDigestsAgree': self.triple('logical') + [99998, 99999, 100000, 'md5']}, False)

    def test_same_subject_preserves_scope_without_personal_or_historical_conclusions(self):
        claim = {'attributesSameSubject': self.triple('scan') + ['scanner.detections_found']
                 + self.triple('scope') + ['scanner.scope']}
        result = self.certify(claim)
        self.assertIn('scoped examination', result['english'])
        self.assertIn('false requires completed declared scope', result['english'])
        self.assertIn('not global virus absence or historical infection', result['english'])
        self.assertIn('archive recursion disabled', result['english'])
        self.certify({'attributesSameSubject': self.triple('os') + ['os.product_name']
                      + self.triple('other_image') + ['image.acquisition.md5']}, False)
        self.certify({'attributeValuesAgree': self.triple('count') + ['account.count']
                      + self.triple('os') + ['os.product_name']}, False)
        for unsupported in ('mostlyUses', 'suspectOwnsComputer', 'neverHadVirus', 'securelyErased'):
            with self.subTest(form=unsupported), self.assertRaises(claims.ClaimError):
                claims.parse({unsupported: []})

    def test_unchecked_projection_preserves_wrong_role_and_asserted_digest_equality(self):
        proposals = [{'candidate_id': 'A', 'claim': {'attributeRecorded': self.triple('os') + ['os.registered_owner']}},
                     {'candidate_id': 'B', 'claim': {'imageDigestsAgree': self.triple('logical') + self.triple('different') + ['md5']}}]
        public = {'schema_version': 2, 'case_id': 'new-case', 'questions': [
            {'id': 'Q', 'prompt': 'Assertions?', 'answer_schema': {}}]}
        bindings = [{'candidate_id': row['candidate_id'], 'claim_sha256': claim_digest(row['claim']),
                     'question_id': 'Q', 'path': [field], 'part': 0, 'field': field}
                    for row, field in zip(proposals, ('value', 'digests_match'))]
        with patch('checker.check.run_kernel', side_effect=AssertionError('no online gate for A')):
            projected = project_answers(public, proposals, bindings, self.source)
        self.assertEqual(projected['submission']['answers'][0]['answer'], {'value': 'Fixture OS', 'digests_match': True})

    def test_reader_rejects_coercions_unknown_roles_and_noncanonical_digests(self):
        cases = [('account.count', '3'), ('account.count', True), ('account.count', -1),
                 ('account.enabled', 'false'), ('new.unreviewed.role', 'value'),
                 ('image.logical.md5', 'ABCDEF')]
        for role, value in cases:
            with self.subTest(role=role, value=value), self.assertRaises(ValueError):
                emit_attribute(Evidence(), 'fixture:subject', role, value, 100, artifact='fixture')
        with self.assertRaises(ValueError):
            emit_attribute(Evidence(), 'fixture:subject', 'account.count', 3, 0, artifact='fixture')

    def test_malformed_numeric_encoding_refused_before_kernel(self):
        claim = self.attribute('count')
        data = json.loads(self.path.read_text())
        value_row = next(row for row in data['facts'] if row['id'] == self.triple('count')[2])
        data['strings'][str(value_row['aux'])] = '03'
        self.path.write_text(json.dumps(data))
        self.source = JsonFacts(self.path)
        with patch('checker.check.run_kernel', side_effect=AssertionError('malformed typed evidence')):
            self.certify(claim, False)

    def test_kind_contract_and_public_catalog_cover_every_reviewed_role(self):
        root = Path(__file__).resolve().parents[1]
        lean = (root / 'lean/ChainOfProof/Facts.lean').read_text()
        sql = (root / 'extractor/schema.sql').read_text()
        for kind in ATTRIBUTE_KINDS:
            self.assertIn('| ' + kind + '\n', lean)
            self.assertIn("'" + kind + "'", sql)
        self.assertEqual(set(catalog()['attribute_roles']), set(ROLES))
        self.certify({'exactly': [ROLES['os.product_name'].kind, 1]})

    def test_public_requirements_expand_exact_roles_without_accepting_other_role(self):
        requirement = {'semantic_types': [ROLES['os.product_name'].semantic_type],
                       'selectors': [{'form': 'attributeRecorded', 'field': 'value'}],
                       'meaning': 'Source-recorded OS product name.',
                       'evidence_needed': 'A typed OS product-name source attribute.'}
        schema = {'type': 'string', 'x-claim-requirement': requirement}
        preflight = answer_requirements.inspect(schema, catalog()['forms'])
        self.assertEqual(preflight['requirements'][0]['available_fields'], [
            {'form': 'attributeRecorded', 'field': 'value',
             'semantic_type': ROLES['os.product_name'].semantic_type}])
        contract = {'schema_version': 2, 'case_id': 'fixture', 'questions': [
            {'id': 'Q', 'prompt': 'Recorded OS?', 'answer_schema': schema}]}
        row = {'candidate_id': 'A', 'claim': self.attribute('owner')}
        binding = {'candidate_id': 'A', 'claim_sha256': claim_digest(row['claim']),
                   'question_id': 'Q', 'path': [], 'part': 0, 'field': 'value'}
        result = project_answers(contract, [row], [binding], self.source)
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertTrue(result['unsupported'])
        generic = dict(requirement, semantic_types=['recorded_typed_attribute_value'])
        self.assertEqual(answer_requirements.inspect({'x-claim-requirement': generic}, catalog()['forms'])
                         ['requirements'][0]['status'], 'no_catalog_support')

    def test_text_encoding_preserves_empty_unicode_and_does_not_cast_text_to_number(self):
        for text in ('', '雪\n"quoted"', '123'):
            ev = Evidence()
            identity = emit_attribute(ev, 'fixture:subject', 'app.config.email', text, 100,
                                      artifact='configuration source')
            path = self.root / 'text.json'
            ev.write_json(path, {})
            source = JsonFacts(path)
            rows = {f.kind: f.id for f in source.all() if source.string(f.obj) == identity}
            claim = {'attributeRecorded': [rows['attributeSubject'], rows[ROLES['app.config.email'].kind],
                                           rows['attributeTextValue'], 'app.config.email']}
            row = {'candidate_id': 'A', 'claim': claim}
            binding = {'candidate_id': 'A', 'claim_sha256': claim_digest(claim),
                       'question_id': 'Q', 'path': [], 'field': 'value'}
            contract = {'schema_version': 2, 'case_id': 'fixture', 'questions': [
                {'id': 'Q', 'prompt': 'Observed text?', 'answer_schema': {}}]}
            result = project_answers(contract, [row], [binding], source)
            self.assertEqual(result['submission']['answers'][0]['answer'], text)
            binding['format'] = 'integer'
            result = project_answers(contract, [row], [binding], source)
            self.assertEqual(result['unsupported'][0]['reason'],
                             'typed_attribute_format_cannot_change_its_declared_native_type')

    def test_partial_image_hash_exports_algorithm_without_an_acquisition_digest(self):
        data = json.loads(self.path.read_text())
        ids = set(self.triple('logical'))
        data['facts'] = [row for row in data['facts'] if row['id'] in ids]
        self.path.write_text(json.dumps(data))
        self.source = JsonFacts(self.path)
        cert = self.certify(self.attribute('logical'))
        public = {'schema_version': 2, 'case_id': 'raw-image-fixture', 'questions': [
            {'id': 'Q', 'prompt': 'Image hash and optional comparison?', 'answer_schema': {}}]}
        bindings = [{'candidate_id': cert['finding_id'], 'claim_sha256': claim_digest(cert['claim']),
                     'question_id': 'Q', 'path': ['image_hash', target], 'field': field}
                    for target, field in (('algorithm', 'algorithm'), ('digest', 'value'))]
        result = project_answers(public, [cert], bindings, self.source, authority='recorded_certificates')
        self.assertEqual(result['submission']['answers'][0]['answer'],
                         {'image_hash': {'algorithm': 'md5', 'digest': 'a' * 32}})
        self.assertFalse(result['unsupported'])
        self.assertNotIn('acquisition_verification_match', result['submission']['answers'][0]['answer'])

    def test_algorithm_selector_is_not_available_for_unrelated_roles(self):
        row = {'candidate_id': 'A', 'claim': self.attribute('os')}
        public = {'schema_version': 2, 'case_id': 'fixture', 'questions': [
            {'id': 'Q', 'prompt': 'Declared algorithm?', 'answer_schema': {}}]}
        binding = {'candidate_id': 'A', 'claim_sha256': claim_digest(row['claim']),
                   'question_id': 'Q', 'path': [], 'field': 'algorithm'}
        result = project_answers(public, [row], [binding], self.source)
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertTrue(result['unsupported'])


if __name__ == '__main__':
    unittest.main()
