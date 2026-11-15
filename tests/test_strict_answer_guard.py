"""Counterexamples for the explicit claim-to-answer policy (no model calls)."""
import unittest
from copy import deepcopy
from agent.answer_projection import project_answers, claim_digest, catalog
from agent.answer_requirements import inspect, KEY
from tests.test_answer_requirements import Source, need


class StrictGuard(unittest.TestCase):
    def run_projection(self, schema, bindings=None, **policy):
        candidate = {'candidate_id': 'C', 'claim': {'programRan': [1]}}
        binding = {'candidate_id': 'C', 'claim_sha256': claim_digest(candidate['claim']),
                   'question_id': 'Q', 'field': 'program', 'path': ['executable']}
        public = {'schema_version': 2, 'case_id': 'case', 'questions': [
            {'id': 'Q', 'prompt': 'Email product and version?', 'answer_schema': schema}]}
        return project_answers(public, [candidate], bindings or [binding], Source(), **policy)

    def test_strict_unannotated_promotion_is_removed_and_policy_frozen(self):
        schema = {'type': 'object', 'properties': {'executable': {'type': 'string'}}}
        self.assertIn('answer', self.run_projection(schema)['submission']['answers'][0])
        result = self.run_projection(schema, require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(result['unsupported'][0]['reason'], 'missing_public_claim_requirement')
        self.assertIs(result['projection']['require_claim_requirements'], True)

    def test_anyof_common_annotated_field_survives_structural_siblings(self):
        schema = {'type': 'object', 'properties': {'executable': {'type': 'string', KEY: need('program')}},
                  'anyOf': [{'type': 'object'}, {'type': 'object'}]}
        result = self.run_projection(schema, require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['answer'], {'executable': 'POSTBOX.EXE'})

    def test_anyof_one_missing_meaning_does_not_sneak_through(self):
        schema = {'anyOf': [
            {'type': 'object', 'properties': {'executable': {'type': 'string', KEY: need('program')}}},
            {'type': 'object', 'properties': {'executable': {'type': 'string'}}}]}
        self.assertEqual(self.run_projection(schema, require_claim_requirements=True)['unsupported'][0]['reason'],
                         'missing_public_claim_requirement')

    def test_stronger_field_removed_while_observation_survives(self):
        schema = {'type': 'object', 'x-claim-row': {'mode': 'same_claim_part'}, 'properties': {
            'product_version': {'type': 'string', KEY: need('email_application_product_with_version')},
            'executable': {'type': 'string', KEY: need('program')}}}
        result = self.run_projection(schema, require_claim_requirements=True)
        binding = deepcopy(result['projection']['bindings'][0]['binding'])
        binding['path'] = ['product_version']
        result = self.run_projection(schema, [result['projection']['bindings'][0]['binding'], binding],
                                     require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['answer'], {'executable': 'POSTBOX.EXE'})
        self.assertEqual(len(result['unsupported']), 1)

    def test_hash_and_literal_are_never_repaired(self):
        schema = {'type': 'object', 'properties': {'executable': {'type': 'string', KEY: need('program')}}}
        base = self.run_projection(schema)['projection']['bindings'][0]['binding']
        for changes, expected in [({'claim_sha256': '0'*64}, 'claim_hash_mismatch'),
                                  ({'value': 'Email Client 7.2'}, 'literal_value_mismatch_not_repaired')]:
            result = self.run_projection(schema, [dict(base, **changes)], require_claim_requirements=True)
            self.assertEqual(result['unsupported'][0]['reason'], expected)

    def test_bad_policy_types_and_strict_preflight(self):
        for policy in (None, 0, 1, 'true', []):
            with self.assertRaises(ValueError):
                self.run_projection({}, require_claim_requirements=policy)
            with self.assertRaises(ValueError):
                inspect({}, catalog()['forms'], require_claim_requirements=policy)
        view = inspect({'type': 'string'}, catalog()['forms'], require_claim_requirements=True)
        self.assertEqual(view['requirements'][0]['status'], 'missing_annotation')

    def test_incomplete_path_and_removal_observation_do_not_become_complete_copy_or_wipe(self):
        cases = [({'journalPathAt': [2]}, 'path_or_incomplete_suffix', 'complete_copy_destination_path'),
                 ({'fileRemovedAt': [3]}, 'record_kind', 'anti_forensic_action'),
                 ({'fileRemovedAt': [3]}, 'recorded_time_us', 'anti_forensic_action_time_us')]
        for claim, field, stronger in cases:
            candidate = {'candidate_id': 'C', 'claim': claim}
            binding = {'candidate_id': 'C', 'claim_sha256': claim_digest(claim), 'question_id': 'Q',
                       'field': field, 'path': []}
            contract = {'schema_version': 2, 'case_id': 'case', 'questions': [
                {'id': 'Q', 'prompt': 'Requested stronger meaning', 'answer_schema': {KEY: need(stronger)}}]}
            result = project_answers(contract, [candidate], [binding], Source(), require_claim_requirements=True)
            self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
            self.assertEqual(result['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')

    def test_container_annotation_never_covers_a_descendant_or_scalar_container_binding(self):
        for schema in [
            {'type': 'object', KEY: need('program'), 'properties': {'executable': {'type': 'string'}}},
            {'type': 'object', 'properties': {'executable': {'type': 'object', KEY: need('program'),
                                                             'properties': {'nested': {'type': 'string'}}}}}]:
            result = self.run_projection(schema, require_claim_requirements=True)
            self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
            self.assertEqual(result['unsupported'][0]['reason'], 'claim_requirement_must_annotate_exact_answer_value')

    def test_shortcut_join_time_and_relationship_cannot_answer_actual_opening(self):
        from checker.facts import Fact
        source = Source()
        source.rows[6] = Fact(6, 'lnkTarget', 128000000, 1, 2, 6)
        source.rows[7] = Fact(7, 'volumeOnDevice', 128000000, 1, 7, 6)
        source.rows[8] = Fact(8, 'volumeRecorded', 128000000, 1, 8, 6)
        for form, args, old_field, old_meaning in [
                ('openedFromMount', [6, 7], 'opened_from_mounted_volume', 'shortcut_target_associated_with_mounted_volume'),
                ('openedFromDevice', [6, 7], 'opened_from_device_volume', 'shortcut_target_associated_with_device_volume'),
                ('openedFromRecorded', [6, 8], 'same_recorded_volume', 'shortcut_target_associated_with_recorded_volume')]:
            candidate = {'candidate_id': 'C', 'claim': {form: args}}
            field, narrow = 'matching_recorded_volume_serials', 'matching_recorded_volume_serials'
            def run(field_name, meaning):
                contract = {'schema_version': 2, 'case_id': 'case', 'questions': [
                    {'id': 'Q', 'prompt': 'Actual opening?', 'answer_schema': {KEY: need(meaning)}}]}
                binding = {'candidate_id': 'C', 'claim_sha256': claim_digest(candidate['claim']),
                           'question_id': 'Q', 'field': field_name, 'path': []}
                return project_answers(contract, [candidate], [binding], source, require_claim_requirements=True)
            for stronger in ('actual_open_time_us', 'action_time_us', 'opened_time_us'):
                result = run('opened_time_us', stronger)
                self.assertEqual(result['submission']['answers'][0]['status'], 'unknown', form)
                self.assertEqual(result['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')
            for stronger in ('actual_file_opened', old_field, old_meaning):
                result = run(field, stronger)
                self.assertEqual(result['submission']['answers'][0]['status'], 'unknown', form)
            self.assertEqual(run(old_field, narrow)['submission']['answers'][0]['status'], 'unknown', form)
            self.assertIs(run(field, narrow)['submission']['answers'][0]['answer'], True)
            self.assertEqual(run('opened_time_us', 'recorded_timestamp_not_action_or_execution_guarantee_us')
                             ['submission']['answers'][0]['answer'], 128000000)
            self.assertIn('actual file opening', catalog()['forms'][form][field]['meaning'])

    def test_anyof_cannot_relax_additional_properties_or_item_requirements(self):
        schema = {'type': 'object', 'additionalProperties': False, 'anyOf': [
            {'type': 'object', 'additionalProperties': True,
             'properties': {'executable': {'type': 'string', KEY: need('program')}}}]}
        result = self.run_projection(schema, require_claim_requirements=True)
        self.assertEqual(result['unsupported'][0]['reason'], 'field_not_in_public_schema')
        # A branch's looser item must not replace the sibling's stronger role.
        schema = {'type': 'object', 'properties': {'executable': {
            'type': 'string', KEY: need('email_application_product_with_version')}},
            'anyOf': [{'properties': {'executable': {'type': 'string', KEY: need('program'),
                                                    '_extra_requirements': []}}}]}
        result = self.run_projection(schema, require_claim_requirements=True)
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')

    def test_anyof_item_schema_remains_conjunctive(self):
        candidate = {'candidate_id': 'C', 'claim': {'programRan': [1]}}
        contract = {'schema_version': 2, 'case_id': 'case', 'questions': [
            {'id': 'Q', 'prompt': 'Email products?', 'answer_schema': {
                'type': 'array', 'items': {'type': 'string', KEY: need('email_application_product_with_version')},
                'anyOf': [{'items': {'type': 'string', KEY: need('program'), '_extra_requirements': []}}]}}]}
        binding = {'candidate_id': 'C', 'claim_sha256': claim_digest(candidate['claim']),
                   'question_id': 'Q', 'path': [0], 'field': 'program'}
        result = project_answers(contract, [candidate], [binding], Source(), require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(result['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')

    def test_conjunctive_compatible_type_union_and_wildcard_preflight(self):
        schema = {'type': ['object', 'null'], 'properties': {
            'executable': {'type': ['string', 'null'], KEY: need('program')}},
            'anyOf': [{'type': 'object', 'properties': {'executable': {'type': 'string'}}}]}
        result = self.run_projection(schema, require_claim_requirements=True)
        self.assertEqual(result['submission']['answers'][0]['answer'], {'executable': 'POSTBOX.EXE'})
        for schema in [
                {'type': 'array', 'items': {'type': 'string', KEY: need('program')},
                 'anyOf': [{'items': {'type': 'string'}}]},
                {'type': 'object', 'additionalProperties': {'type': 'string', KEY: need('program')},
                 'anyOf': [{'additionalProperties': {'type': 'string'}}]}]:
            view = inspect(schema, catalog()['forms'], require_claim_requirements=True)
            self.assertFalse(any(row['status'] == 'missing_annotation' for row in view['requirements']), view)
            self.assertIn('blocked', view['unannotated_fields'])

    def test_usbstor_record_time_is_not_connection_onset_and_mapping_is_not_mount_event(self):
        from checker.facts import Fact
        source = Source()
        source.rows[6] = Fact(6, 'volumeOnDevice', 128000000, 1, 7, 6)
        for form in ('deviceHolds', 'usbMountedAs', 'deviceExamined'):
            candidate = {'candidate_id': 'C', 'claim': {form: [4, 6]}}
            def run(field, meaning):
                contract = {'schema_version': 2, 'case_id': 'case', 'questions': [
                    {'id': 'Q', 'prompt': 'When was the device connected?', 'answer_schema': {KEY: need(meaning)}}]}
                binding = {'candidate_id': 'C', 'claim_sha256': claim_digest(candidate['claim']),
                           'question_id': 'Q', 'field': field, 'path': []}
                return project_answers(contract, [candidate], [binding], source, require_claim_requirements=True)
            for stronger in ('connected_time_us', 'actual_connection_time_us', 'connection_onset_us'):
                result = run('connected_time_us', stronger)
                self.assertEqual(result['submission']['answers'][0]['status'], 'unknown', form)
                self.assertEqual(result['unsupported'][0]['reason'], 'claim_role_does_not_meet_public_requirement')
            self.assertEqual(run('connected_time_us', 'recorded_timestamp_not_action_or_execution_guarantee_us')
                             ['submission']['answers'][0]['answer'], 126000000)
            if form == 'usbMountedAs':
                for stronger in ('same_device_mounted_volume', 'actual_mount_event'):
                    self.assertEqual(run('same_device_mounted_volume', stronger)
                                     ['submission']['answers'][0]['status'], 'unknown')
                self.assertEqual(run('matching_recorded_device_identifiers', 'same_recorded_device_volume_mapping')
                                 ['submission']['answers'][0]['status'], 'unknown')
            self.assertIs(run('matching_recorded_device_identifiers', 'matching_recorded_device_identifiers')
                          ['submission']['answers'][0]['answer'], True)
