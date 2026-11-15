"""Public-only proposal controls; all schemas and timestamp examples are synthetic."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eval.benchmark import Matcher
from eval.hacking_case_representation_proposal.build import prepare, LOCAL_INSTRUCTION, CASE_ID
from eval.representation_derivative import publish_prepared


class HackingRepresentationContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path, self.output = self.root / 'public.json', self.root / 'proposal'
        self.public = {'schema_version': 2, 'case_id': 'synthetic-ancestor', 'contract_revision': 'old',
                       'time_zone': None, 'instructions': [LOCAL_INSTRUCTION], 'questions': []}
        for index in range(1, 32):
            self.public['questions'].append({'id': f'Q{index}', 'prompt': 'Synthetic recorded field?',
                'answer_schema': {'type': 'object', 'properties': {}},
                'match': {'strings': 'casefold_whitespace', 'list_order': 'unordered'}})
        for qid, field, role in [(2, 'operating_system', 'os_product_name'), (3, 'installed_at', 'os_install_time'),
                                 (4, 'time_zone_setting', 'os_effective_time_zone'), (8, 'shutdown_at', 'machine_last_shutdown')]:
            q = self.public['questions'][qid - 1]
            q['answer_schema'].update({'x-claim-row': {'mode': 'same_claim_part'},
                'x-claim-scope': {'mode': 'source_records', 'origins': [{
                    'image': 'synthetic.E01', 'exhibit': 'SYNTHETIC-PC',
                    'source_snapshot': 'base-volume', 'source_variant': 'primary'}]}})
            q['answer_schema']['properties'][field] = {'type': 'string', 'x-claim-requirement': {
                'semantic_types': ['recorded_attribute_' + role + '_string'], 'meaning': 'recorded text',
                'evidence_needed': 'Exact typed recorded source attribute from the declared exhibit.',
                'selectors': [{'form': 'attributeRecorded', 'field': 'value'}]}}
            if qid in (3, 8):
                q['match']['timestamps'] = {'/' + field: {'tolerance_seconds': 0}}
        self.path.write_text(json.dumps(self.public))

    def test_exact_changes_preserve_roles_shapes_scope_and_legacy_product_matching(self):
        original = self.path.read_bytes(); manifest = prepare(self.path, self.output)
        self.assertEqual(self.path.read_bytes(), original)
        derivative = json.loads((self.output / 'questions.json').read_text())
        self.assertEqual(derivative['case_id'], CASE_ID); self.assertEqual(derivative['time_zone'], 'UTC')
        self.assertEqual(manifest['ancestor_public_sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(manifest['questions_sha256'], hashlib.sha256((self.output / 'questions.json').read_bytes()).hexdigest())
        self.assertFalse(manifest['model_run_ready']); self.assertTrue(manifest['reference_alignment_required'])
        self.assertFalse(any('not ready for model execution' in instruction
                             for instruction in derivative['instructions']))
        self.assertNotIn('held', derivative['title'])
        self.assertEqual(manifest['scorer_version_required'], '2.2')
        from eval import benchmark
        self.assertEqual(manifest['observed_scorer_version'], benchmark.VERSION)
        self.assertEqual(manifest['benchmark_implementation_sha256'],
                         hashlib.sha256(Path(benchmark.__file__).read_bytes()).hexdigest())
        self.assertEqual([q['id'] for q in derivative['questions']], ['Q2', 'Q3', 'Q4', 'Q8'])
        self.assertEqual(manifest['question_ids'], ['Q2', 'Q3', 'Q4', 'Q8'])
        self.assertEqual(manifest['ancestor_question_count'], 31)
        self.assertEqual(manifest['question_count'], 4)
        self.assertTrue(manifest['source_precision_alignment_required'])
        self.assertTrue(any('Report display timezone is an explicit presentation convention; it does not '
                            'establish the machine historical local timezone. Native source timestamp retained.'
                            in instruction for instruction in derivative['instructions']))
        ancestors = {q['id']: q for q in self.public['questions']}
        for after in derivative['questions']:
            before = ancestors[after['id']]
            normalized = deepcopy(after)
            if before['id'] == 'Q2':
                del normalized['answer_schema']['properties']['operating_system']['description']
                normalized['answer_schema']['properties']['operating_system']['x-claim-requirement']['meaning'] = (
                    before['answer_schema']['properties']['operating_system']['x-claim-requirement']['meaning'])
            if before['id'] in ('Q3', 'Q8'):
                leaf = next(iter(normalized['answer_schema']['properties'].values()))
                del leaf['format']; del leaf['x-claim-display']
            if before['id'] == 'Q4':
                del normalized['match']['normalization']; del normalized['match']['normalization_profile']
            self.assertEqual(normalized, before)
        by_id = {q['id']: q for q in derivative['questions']}
        matcher = Matcher(by_id['Q4']['match'])
        a = {'time_zone_setting': 'Synthetic Zone (UTC+02:30)'}
        b = {'time_zone_setting': '(+0230) synthetic zone'}
        self.assertEqual([e['status'] for e in matcher.compare(a, b)], ['match'])
        self.assertNotEqual([e['status'] for e in matcher.compare(a, {'time_zone_setting': 'Synthetic Zone (UTC+03:30)'})], ['match'])
        product = Matcher(by_id['Q2']['match'])
        self.assertNotEqual([e['status'] for e in product.compare('Vendor Synthetic OS', 'Synthetic OS')], ['match'])
        self.assertEqual(set(p.name for p in self.output.iterdir()), {'questions.json', 'manifest.json'})

    def test_invalid_ancestor_leaves_no_output(self):
        self.public['instructions'] = ['different instruction']
        self.path.write_text(json.dumps(self.public))
        with self.assertRaises(ValueError): prepare(self.path, self.output)
        self.assertFalse(self.output.exists())

    def test_weakened_selected_source_guards_and_requirements_refuse(self):
        original = deepcopy(self.public)
        for mutation in ('missing_scope', 'empty_scope', 'missing_requirement', 'wrong_requirement', 'missing_row'):
            with self.subTest(mutation=mutation):
                public = deepcopy(original)
                schema = public['questions'][1]['answer_schema']
                leaf = schema['properties']['operating_system']
                if mutation == 'missing_scope': del schema['x-claim-scope']
                elif mutation == 'empty_scope': schema['x-claim-scope']['origins'] = []
                elif mutation == 'missing_requirement': del leaf['x-claim-requirement']
                elif mutation == 'wrong_requirement':
                    leaf['x-claim-requirement']['semantic_types'] = ['unreviewed_product_alias']
                else: del schema['x-claim-row']
                self.path.write_text(json.dumps(public))
                with self.assertRaises(ValueError): prepare(self.path, self.output)
                self.assertFalse(self.output.exists())

    def test_snapshot_input_swap_and_existing_destination_refusal(self):
        original = self.path.read_bytes(); real_read = Path.read_bytes; reads = []
        def swap(path):
            data = real_read(path)
            if path == self.path:
                reads.append(data); path.write_text('{"private_answer":"forbidden"}')
            return data
        with patch.object(Path, 'read_bytes', swap): manifest = prepare(self.path, self.output)
        self.assertEqual(reads, [original])
        self.assertEqual(manifest['ancestor_public_sha256'], hashlib.sha256(original).hexdigest())
        self.path.write_bytes(original)
        saved = (self.output / 'questions.json').read_bytes()
        with self.assertRaises(ValueError): prepare(self.path, self.output)
        self.assertEqual((self.output / 'questions.json').read_bytes(), saved)

    def test_shared_publisher_rejects_invalid_map_and_publishes_manifest_last(self):
        for files in ({}, {'manifest.json': 'text'}, {'manifest.json': b'{}', '../x': b'x'},
                      {'manifest.json': b'{}', 'a/b': b'x'}, {'manifest.json': b'{}', '.': b'x'}):
            with self.subTest(files=files), self.assertRaises(ValueError): publish_prepared(self.output, files)
            self.assertFalse(self.output.exists())
        import os
        actual = os.link; order = []
        def record(source, target):
            order.append(Path(target).name); return actual(source, target)
        with patch('eval.representation_derivative.os.link', side_effect=record):
            publish_prepared(self.output, {'manifest.json': b'{}', 'questions.json': b'{}'})
        self.assertEqual(order, ['questions.json', 'manifest.json'])


if __name__ == '__main__': unittest.main()
