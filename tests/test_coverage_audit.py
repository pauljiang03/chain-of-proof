"""Coverage diagnostics must not turn missing work into evidence or truth."""
from copy import deepcopy
from collections import Counter
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.answer_projection import catalog, claim_digest
from agent.coverage_audit import audit_coverage, main
from tests import test_completion_diagnostics


class CoverageAuditTests(unittest.TestCase):
    def fixture(self):
        public, document, projection = test_completion_diagnostics.CompletionDiagnostics().declaration_fixture()
        document['case_id'] = public['case_id']
        plan = {'case_id': public['case_id'], 'public_sha256': claim_digest(public)}
        plan['projection_sha256'] = claim_digest(plan)
        projection['projection_sha256'] = plan['projection_sha256']
        return [public, document, projection, catalog(), plan]

    def test_missing_work_catalog_and_scope_are_separate(self):
        args = self.fixture()
        before = deepcopy(args)
        result = audit_coverage(*args)
        self.assertEqual(args, before)
        rows = {r['question_id']: r for r in result['questions']}
        self.assertIn('catalog_or_mapping_gap', rows['UNSUPPORTED']['categories'])
        self.assertIn('declared_scope_unavailable', rows['UNAVAILABLE']['categories'])
        self.assertEqual(rows['UNBOUND']['categories'], ['no_authored_binding'])
        self.assertEqual(rows['SUPPORTED']['binding_outcomes']['authored'], 2)
        self.assertIn('recorded_output_conflict', rows['SUPPORTED']['categories'])
        self.assertTrue(all(r['source_presence'] == r['investigation_status'] == 'not_determined'
                            for r in rows.values()))
        self.assertEqual(result['accuracy'], 'not_measured')
        self.assertEqual(result['lineage']['catalog'], 'unverified')

    def test_scope_and_meaning_rejection_require_recorded_diagnostic(self):
        args = self.fixture()
        args[2]['unsupported'] = [
            {'binding': {'question_id': 'SUPPORTED'}, 'reason': 'claim_records_do_not_meet_public_scope'},
            {'binding': {'question_id': 'UNSUPPORTED'}, 'reason': 'claim_role_does_not_meet_public_requirement',
             'meaning_checks': [{'status': 'incompatible'}]}]
        rows = {r['question_id']: r for r in audit_coverage(*args)['questions']}
        self.assertIn('recorded_scope_rejection', rows['SUPPORTED']['categories'])
        self.assertIn('recorded_meaning_rejection', rows['UNSUPPORTED']['categories'])
        self.assertNotIn('recorded_scope_rejection', rows['UNBOUND']['categories'])

    def test_overlapping_rejection_categories_do_not_hide_other_refusals(self):
        args = self.fixture()
        args[2]['unsupported'] = [
            {'binding': {'question_id': 'SUPPORTED'}, 'reason': 'public_claim_scope_unavailable',
             'meaning_checks': [{'status': 'incompatible'}]},
            {'binding': {'question_id': 'SUPPORTED'}, 'reason': 'another_error'}]
        row = audit_coverage(*args)['questions'][0]
        self.assertIn('other_recorded_binding_rejection', row['categories'])
        self.assertEqual(row['binding_outcomes']['scope_rejected'], 1)
        self.assertEqual(row['binding_outcomes']['meaning_rejected'], 1)

    def test_cli_hashes_exactly_the_bytes_parsed_once_and_preserves_existing_output(self):
        args = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            files = {}
            argv = []
            for name, value in zip(('public', 'document', 'projection', 'catalog', 'plan'), args):
                path = Path(directory) / (name + '.json')
                files[path] = json.dumps(value, indent=1).encode() + b'\n'
                path.write_bytes(files[path])
                argv.extend(['--' + name, str(path)])
            output = Path(directory) / 'out.json'
            argv.extend(['--out', str(output)])
            reads = Counter()
            def read_once(path):
                reads[path] += 1
                if reads[path] != 1:
                    raise AssertionError('Input was reread after parsing')
                return files[path]
            with patch.object(Path, 'read_bytes', read_once):
                self.assertEqual(main(argv), 0)
            result = json.loads(output.read_text())
            self.assertEqual(result['input_file_sha256'], {
                path.stem: hashlib.sha256(data).hexdigest() for path, data in files.items()})
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                main(argv)
            self.assertEqual(output.read_bytes(), before)

    def test_retained_leaf_does_not_imply_complete_or_correct_answer(self):
        args = self.fixture()
        args[2]['leaves'] = [{'question_id': 'SUPPORTED', 'value': 'SECRET_ANSWER'}]
        args[2]['submission']['answers'][0] = {'question_id': 'SUPPORTED', 'status': 'answered',
                                             'answer': 'SECRET_ANSWER'}
        args[1]['bindings'][0]['value'] = 'SECRET_BINDING'
        args[2]['unsupported'][0]['reason'] = 'SECRET_ERROR_VALUE'
        result = audit_coverage(*args)
        text = json.dumps(result)
        for secret in ('SECRET_ANSWER', 'SECRET_BINDING', 'SECRET_ERROR_VALUE', 'Reviewed missing source fixture.'):
            self.assertNotIn(secret, text)
        row = result['questions'][0]
        self.assertEqual(row['binding_outcomes']['leaves'], 1)
        self.assertNotIn('no_retained_leaf', row['categories'])
        self.assertEqual(row['source_presence'], 'not_determined')

    def test_public_change_refused_or_explicitly_declarations_only(self):
        args = self.fixture()
        args[0]['questions'][0]['prompt'] = 'Changed question'
        with self.assertRaisesRegex(ValueError, 'public_revision_mismatch'):
            audit_coverage(*args)
        result = audit_coverage(*args, allow_cross_revision=True)
        self.assertEqual(result['lineage']['comparison'], 'cross_revision_declarations_only')
        self.assertTrue(all(r['binding_outcomes'] is None for r in result['questions']))
        self.assertNotIn('no_authored_binding', result['category_question_counts'])

    def test_catalog_change_refused_even_if_public_identical(self):
        args = self.fixture()
        expected = claim_digest(args[3])
        result = audit_coverage(*args, projection_catalog_sha256=expected)
        self.assertEqual(result['lineage']['catalog'], 'caller_hash_matched')
        args[3]['forms'] = {}
        with self.assertRaisesRegex(ValueError, 'catalog_revision_mismatch'):
            audit_coverage(*args, projection_catalog_sha256=expected)
        result = audit_coverage(*args, projection_catalog_sha256=expected, allow_cross_revision=True)
        self.assertTrue(all(r['binding_outcomes'] is None for r in result['questions']))

    def test_changed_plan_and_wrong_projection_fail_closed(self):
        args = self.fixture()
        args[4]['public_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'invalid_projection_plan_digest'):
            audit_coverage(*args)
        args = self.fixture()
        args[2]['projection_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'projection_plan_mismatch'):
            audit_coverage(*args)

    def test_saved_projection_can_supply_embedded_plan(self):
        args = self.fixture()
        args[2]['projection'] = args[4]
        explicit = audit_coverage(*args)
        embedded = audit_coverage(*args[:4])
        self.assertEqual(explicit, embedded)

    def test_wrong_case_and_duplicate_question_status_fail_closed(self):
        args = self.fixture()
        args[1]['case_id'] = 'OTHER'
        with self.assertRaisesRegex(ValueError, 'case_mismatch'):
            audit_coverage(*args)
        args = self.fixture()
        args[2]['submission']['answers'] *= 2
        with self.assertRaisesRegex(ValueError, 'invalid_submission_status_rows'):
            audit_coverage(*args)

    def test_malformed_and_foreign_rows_remain_visible(self):
        args = self.fixture()
        args[1]['bindings'] += [[], {'question_id': 'OTHER'}]
        args[2]['leaves'] = [{'question_id': 'OTHER', 'value': 'SECRET'}]
        result = audit_coverage(*args)
        self.assertEqual(result['unattributed_rows']['authored'], 2)
        self.assertEqual(result['unattributed_rows']['leaves'], 1)
        self.assertNotIn('SECRET', json.dumps(result))

    def test_every_input_change_changes_its_hash(self):
        args = self.fixture()
        result = audit_coverage(*args)
        for index, name in ((0, 'public'), (1, 'document'), (2, 'projection'), (3, 'catalog')):
            changed = deepcopy(args)
            changed[index]['audit_test_marker'] = True
            other = audit_coverage(*changed, allow_cross_revision=True)
            self.assertNotEqual(other['input_sha256'][name], result['input_sha256'][name])


if __name__ == '__main__':
    unittest.main()
