"""Public-only derivative preparation with synthetic schemas and spellings."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eval.benchmark import Matcher
from eval.representation_derivative import prepare


class RepresentationDerivative(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = {'schema_version': 2, 'case_id': 'synthetic-original', 'contract_revision': 'original',
                       'questions': [{'id': 'Q', 'prompt': 'Recorded label and offset?',
                       'answer_schema': {'type': 'object', 'properties': {'zone': {'type': 'string'}},
                                         'additionalProperties': False},
                       'match': {'strings': 'casefold_whitespace', 'list_order': 'unordered'}}]}
        self.public_path = self.root / 'public.json'
        self.policy_path = self.root / 'policy.json'
        self.output = self.root / 'derivative'
        self.write_public()
        self.policy = {'version': 1, 'case_id': 'synthetic-prospective', 'contract_revision': 'prospective-v1',
                       'ancestor_public_sha256': hashlib.sha256(self.public_path.read_bytes()).hexdigest(),
                       'questions': {'Q': {'fields': {'/zone': {'kind': 'zone-label-offset-v1',
                                                              'label_mode': 'casefold_whitespace'}},
                                           'source_contexts': {}}}}

    def write_public(self):
        self.public_path.write_text(json.dumps(self.public, indent=3) + '\n')

    def run_prepare(self):
        self.policy_path.write_text(json.dumps(self.policy))
        return prepare(self.public_path, self.policy_path, self.output)

    def assert_refused(self):
        with self.assertRaises(ValueError):
            self.run_prepare()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.representation-*')))

    def test_failed_publication_preserves_foreign_file_and_has_no_manifest(self):
        import os
        real_link = os.link
        def inject_foreign_file(source, target):
            if Path(target).name == 'policy.json':
                (self.output / 'foreign.txt').write_text('concurrent actor')
                raise OSError('synthetic failure with concurrent content')
            return real_link(source, target)
        with patch('eval.representation_derivative.os.link', side_effect=inject_foreign_file), self.assertRaises(OSError):
            self.run_prepare()
        self.assertEqual((self.output / 'foreign.txt').read_text(), 'concurrent actor')
        self.assertEqual([path.name for path in self.output.iterdir()], ['foreign.txt'])
        self.assertFalse((self.output / 'manifest.json').exists())

    def test_zone_derivative_is_explicit_symmetric_and_original_bytes_unchanged(self):
        original = self.public_path.read_bytes()
        manifest = self.run_prepare()
        derivative = json.loads((self.output / 'questions.json').read_text())
        self.assertEqual(self.public_path.read_bytes(), original)
        self.assertEqual(derivative['questions'][0]['answer_schema'], self.public['questions'][0]['answer_schema'])
        self.assertEqual(manifest['ancestor_public_sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(manifest['questions_sha256'], hashlib.sha256((self.output / 'questions.json').read_bytes()).hexdigest())
        self.assertEqual(manifest['policy_sha256'], hashlib.sha256(self.policy_path.read_bytes()).hexdigest())
        self.assertTrue(manifest['separate_reference_alignment_required'])
        self.assertFalse(manifest['scoring_performed'])
        matcher = Matcher(derivative['questions'][0]['match'])
        left, right = 'Synthetic Zone (UTC+02:30)', '(+0230) synthetic zone'
        for first, second in ((left, right), (right, left)):
            self.assertEqual([event['status'] for event in matcher.compare({'zone': first}, {'zone': second})], ['match'])
        for other in ('Synthetic Zone (UTC+03:30)', 'Other Zone (UTC+02:30)'):
            self.assertNotEqual([event['status'] for event in matcher.compare({'zone': left}, {'zone': other})], ['match'])
        with self.assertRaises(ValueError):
            self.run_prepare()

    def test_bad_policy_and_schema_paths_leave_no_partial_output(self):
        baseline = deepcopy(self.policy)
        variants = []
        bad = deepcopy(baseline); bad['ancestor_public_sha256'] = '0' * 64; variants.append(bad)
        bad = deepcopy(baseline); bad['questions']['Q']['fields']['/zone'] = {'kind': 'os-vendor-alias-v1'}; variants.append(bad)
        bad = deepcopy(baseline); bad['questions']['UNKNOWN'] = bad['questions'].pop('Q'); variants.append(bad)
        bad = deepcopy(baseline); bad['questions']['Q']['fields'] = {'/absent': {'kind': 'guid-v1'}}; variants.append(bad)
        bad = deepcopy(baseline); bad['questions']['Q']['fields'] = {'': {'kind': 'guid-v1'}}; variants.append(bad)
        bad = deepcopy(baseline); bad['case_id'] = self.public['case_id']; variants.append(bad)
        for policy in variants:
            with self.subTest(policy=policy):
                self.policy = policy
                self.assert_refused()

    def test_legacy_rule_overlap_refuses_without_removing_rule(self):
        self.public['questions'][0]['match']['string_modes'] = {'/zone': 'casefold'}
        self.write_public()
        original = self.public_path.read_bytes()
        self.policy['ancestor_public_sha256'] = hashlib.sha256(original).hexdigest()
        self.assert_refused()
        self.assertEqual(self.public_path.read_bytes(), original)

    def test_input_swap_does_not_change_captured_validation_or_output(self):
        original = self.public_path.read_bytes()
        real_read = Path.read_bytes
        reads = []
        def swap_after_read(path):
            data = real_read(path)
            if path == self.public_path:
                reads.append(data)
                path.write_text(json.dumps(dict(self.public, private_answer='forbidden')))
            return data
        with patch.object(Path, 'read_bytes', swap_after_read):
            manifest = self.run_prepare()
        self.assertEqual(reads, [original])
        self.assertEqual(manifest['ancestor_public_sha256'], hashlib.sha256(original).hexdigest())
        derivative = json.loads((self.output / 'questions.json').read_text())
        self.assertNotIn('private_answer', derivative)
        self.assertEqual(derivative['questions'][0]['answer_schema'], self.public['questions'][0]['answer_schema'])

    def test_destination_race_and_publication_failure_never_overwrite(self):
        real_mkdir = Path.mkdir
        def race_mkdir(path, *args, **kwargs):
            if path == self.output:
                real_mkdir(path)
            return real_mkdir(path, *args, **kwargs)
        with patch.object(Path, 'mkdir', race_mkdir), self.assertRaises(FileExistsError):
            self.run_prepare()
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertFalse((self.output / 'manifest.json').exists())
        self.output.rmdir()
        import os
        real_link = os.link
        def fail_policy(source, target):
            if Path(target).name == 'policy.json':
                raise OSError('synthetic publication failure')
            return real_link(source, target)
        with patch('eval.representation_derivative.os.link', side_effect=fail_policy), self.assertRaises(OSError):
            self.run_prepare()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.representation-*')))

    def test_ambiguous_wildcards_and_union_schemas_refuse(self):
        schema = {'type': 'object', 'properties': {'a': {'type': 'object', 'properties': {
            'zone': {'type': 'string'}}, 'additionalProperties': False}}, 'additionalProperties': False}
        self.public['questions'][0]['answer_schema'] = schema
        self.write_public()
        self.policy['ancestor_public_sha256'] = hashlib.sha256(self.public_path.read_bytes()).hexdigest()
        self.policy['questions']['Q']['fields'] = {'/*/zone': {'kind': 'guid-v1'}, '/a/*': {'kind': 'guid-v1'}}
        self.assert_refused()
        self.policy['questions']['Q']['fields'] = {'/a/zone': {'kind': 'guid-v1'}}
        schema['properties']['a']['properties']['zone']['oneOf'] = [{'type': 'string'}]
        self.write_public()
        self.policy['ancestor_public_sha256'] = hashlib.sha256(self.public_path.read_bytes()).hexdigest()
        self.assert_refused()

    def test_guid_and_path_rules_require_explicit_complete_context(self):
        selection = self.policy['questions']['Q']
        selection['fields'] = {'/zone': {'kind': 'windows-volume-path-v1', 'context': 'volume',
                                        'case_sensitive': True, 'allow_volume_rooted': True}}
        self.assert_refused()
        context = {'origin': {'image': 'synthetic.E01', 'exhibit': 'SYNTHETIC',
                             'source_snapshot': 'base-volume', 'source_variant': 'primary'},
                   'volume': {'kind': 'ntfs-serial-64', 'value': '0123456789abcdef'},
                   'absolute_roots': ['C:'], 'mapping_receipt_sha256': 'a' * 64}
        selection['source_contexts'] = {'volume': context}
        del context['mapping_receipt_sha256']
        self.assert_refused()
        context['mapping_receipt_sha256'] = 'a' * 64
        self.run_prepare()
        derivative = json.loads((self.output / 'questions.json').read_text())
        matcher = Matcher(derivative['questions'][0]['match'])
        self.assertEqual([e['status'] for e in matcher.compare({'zone': r'C:\Folder\x'}, {'zone': r'\Folder\x'})], ['match'])
        # An independent fresh derivative can enable a GUID without source contexts.
        self.output = self.root / 'guid-derivative'
        selection.update(fields={'/zone': {'kind': 'guid-v1'}}, source_contexts={})
        self.run_prepare()
        derivative = json.loads((self.output / 'questions.json').read_text())
        matcher = Matcher(derivative['questions'][0]['match'])
        self.assertEqual([e['status'] for e in matcher.compare({'zone': 'a' * 32}, {'zone': '{' + 'A' * 32 + '}'})], ['match'])


if __name__ == '__main__':
    unittest.main()
