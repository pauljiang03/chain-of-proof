"""Synthetic registry product text stays literal through certified projection."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent.answer_projection import claim_digest, project_answers
from checker import claims
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from extractor import host_attributes, system
from extractor.store import Evidence
from verifier.verify import verify


ROOT = Path(__file__).resolve().parents[1]


class RecordedProductLiteral(unittest.TestCase):
    def test_reader_typed_certificate_and_public_q2_preserve_product_text(self):
        public = json.loads((ROOT / 'tests/fixtures/contracts/hacking/questions.json').read_text())
        question = deepcopy(next(q for q in public['questions'] if q['id'] == 'Q2'))
        requirement = question['answer_schema']['properties']['operating_system']['x-claim-requirement']
        self.assertEqual(requirement['semantic_types'], [ROLES['os.product_name'].semantic_type])
        origin = dict(image='synthetic.E01', exhibit='SYNTHETIC-PC',
                      source_snapshot='base-volume', source_variant='primary')
        question['answer_schema']['x-claim-scope']['origins'] = [origin]
        # Arbitrary names and deliberate near-neighbors: no vendor, edition,
        # version, punctuation, Unicode or whitespace may disappear in projection.
        products = ('Aster OS', 'Vendor Aster OS', 'Vendor Aster OS Professional',
                    'Vendor Aster OS Professional 4.2', 'Vendor Aster OS Professional 4.3',
                    'Vendor Aster OS (Lab)+!', '雪社 Aster Ω e\u0301', '  Aster  OS\tLab  ')
        projected_values = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, product in enumerate(products):
                with self.subTest(product=product):
                    hive = system.Hive('SOFTWARE', None, r'C:\Windows\System32\config\SOFTWARE', False, None, None)
                    key = SimpleNamespace(values=lambda: [SimpleNamespace(name='ProductName', value=product)])
                    ev = Evidence()
                    with patch.object(system, '_hives', return_value=[hive]), patch.object(
                            system, '_open', side_effect=lambda ev, h, path:
                            key if path == r'Microsoft\Windows NT\CurrentVersion' else None):
                        host_attributes.extract(ev, None, {'examined_at': 1800000000000000,
                                                          'common': deepcopy(origin)})
                    self.assertEqual(ev.problems, [])
                    path = root / 'facts.json'
                    ev.write_json(path, {})
                    source = JsonFacts(path)
                    rows = {fact.kind: fact for fact in source.all()}
                    spec = ROLES['os.product_name']
                    self.assertEqual(set(rows), {'attributeSubject', spec.kind, spec.value_kind})
                    value = rows[spec.value_kind]
                    self.assertEqual(source.string(value.aux), json.dumps(product, ensure_ascii=True))
                    self.assertEqual(value.t, 1800000000000000)
                    claim = {'attributeRecorded': [rows['attributeSubject'].id, rows[spec.kind].id,
                                                   value.id, 'os.product_name']}
                    certificate = check(claim, f'Literal{index}', source, out_dir=root)
                    self.assertEqual(certificate['status'], 'verified', certificate)
                    self.assertEqual(certificate['trust_tier'], 'kernel')
                    self.assertEqual(certificate['axioms'], [])
                    self.assertEqual(verify(certificate, source), [])
                    self.assertIn('recorded in configuration', certificate['english'])
                    self.assertIn('not personal attribution, habitual use, intent or completeness',
                                  certificate['english'])
                    binding = {'candidate_id': certificate['finding_id'], 'claim_sha256': claim_digest(claim),
                               'question_id': 'Q2', 'path': ['operating_system'], 'part': 0, 'field': 'value'}
                    contract = dict(schema_version=2, case_id='synthetic-product-literals', questions=[question])
                    result = project_answers(contract, [certificate], [binding], source,
                                             authority='recorded_certificates',
                                             require_claim_requirements=True, require_evidence_scope=True,
                                             evidence_facts_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                    self.assertEqual(result['unsupported'], [])
                    answer = result['submission']['answers'][0]
                    self.assertEqual(answer['status'], 'answered')
                    self.assertEqual(answer['answer'], {'operating_system': product})
                    self.assertEqual(result['question_completeness'], 'not_established')
                    projected_values.append(answer['answer']['operating_system'])
        self.assertEqual(projected_values, list(products))
        self.assertEqual(len(set(projected_values)), len(products))

    def test_configuration_does_not_supply_an_actual_use_claim_form(self):
        for unsupported in ('operatingSystemUsed', 'mostlyUses'):
            with self.subTest(form=unsupported), self.assertRaises(claims.ClaimError):
                claims.parse({unsupported: []})


if __name__ == '__main__':
    unittest.main()
