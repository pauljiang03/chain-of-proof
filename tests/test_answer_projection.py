"""Literal values follow proposed semantics, not actual kind or truth repairs."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from agent.answer_projection import catalog, claim_digest, claim_fields, prepare_projection, project_answers, render_projection
from checker.facts import Fact, FactSource


class Source(FactSource):
    def __init__(self):
        self.strings = {1: 'DEVICE-A', 2: 'DEVICE-B', 3: 'PC', 4: 'VOLUME-V', 5: 'query text',
                        6: 'Browser', 7: 'folder/file.txt', 8: 'real-tag', 9: 'wrong-proposed-tag',
                        10: 'Setting', 11: '123', 12: 'opaque-sha256'}
        self.rows = {f.id: f for f in (
            Fact(1, 'usbInsert', 100000000, 1, 1, 3),
            Fact(2, 'volumeOnDevice', 200000000, 1, 2, 4),
            Fact(3, 'webSearch', 200000000, 1, 5, 6),
            Fact(4, 'fileCreated', 300000000, 1, 7, 4),
            Fact(5, 'fileModified', 500000000, 1, 7, 4),
            Fact(6, 'tag', 100000000, 1, 1, 8),
            Fact(7, 'systemSetting', 100000000, 1, 10, 11),
            Fact(8, 'fileContent', 100000000, 1, 7, 12))}

    def get(self, ids):
        return {i: self.rows[i] for i in ids if i in self.rows}

    def string(self, sid):
        return self.strings.get(sid, f'#{sid}')

    def all(self):
        raise AssertionError('Projection must not scan/count facts to repair an asserted count')


def public():
    return {'schema_version': 2, 'case_id': 'arbitrary-case', 'time_zone': 'America/Los_Angeles',
            'questions': [{'id': 'devices', 'prompt': 'Which relationships?', 'answer_schema': {
                'type': 'object', 'properties': {'devices': {'type': 'array', 'items': {
                    'type': 'object', 'properties': {'serial': {'type': 'string'}, 'volume': {'type': 'string'},
                        'linked': {'type': 'boolean'}, 'time': {'type': 'string'}}, 'additionalProperties': False}}},
                'additionalProperties': False}},
                {'id': 'count', 'prompt': 'How many extracted rows?', 'answer_schema': {'type': 'integer'}},
                {'id': 'order', 'prompt': 'Does the declared order hold?', 'answer_schema': {'type': 'boolean'}},
                {'id': 'tag', 'prompt': 'Which tag is asserted?', 'answer_schema': {'type': 'string'}},
                {'id': 'untouched', 'prompt': 'Still unknown?', 'answer_schema': {'type': 'object'}}]}


def candidate(cid, claim, **extra):
    return {'candidate_id': cid, 'claim': claim, **extra}


def bind(row, qid, path, field, part=0, **extra):
    return {'candidate_id': row.get('candidate_id', row.get('finding_id')), 'claim_sha256': claim_digest(row['claim']),
            'question_id': qid, 'path': path, 'part': part, 'field': field, **extra}


class AnswerProjection(unittest.TestCase):
    def setUp(self):
        self.source = Source()

    def test_wrong_counts_tag_constants_and_reversed_order_are_not_recomputed(self):
        rows = [candidate('COUNT', {'exactly': ['usbInsert', 99]}),
                candidate('BEFORE', {'before': [5, 4]}),
                candidate('TAG', {'tagged': [1, 'obj', 6, 9]})]
        bindings = [bind(rows[0], 'count', [], 'count'), bind(rows[1], 'order', [], 'precedes_beyond_uncertainty'),
                    bind(rows[2], 'tag', [], 'tag')]
        with patch('checker.check.run_kernel', side_effect=AssertionError('no kernel')), \
             patch('checker.check.explain', side_effect=AssertionError('no semantic feedback')):
            result = project_answers(public(), rows, bindings, self.source)
        values = {r['question_id']: r.get('answer') for r in result['submission']['answers']}
        self.assertEqual(values['count'], 99)
        self.assertIs(values['order'], True)
        self.assertEqual(values['tag'], 'wrong-proposed-tag')
        self.assertEqual(result['authority'], 'unchecked')
        self.assertNotIn('verified', [entry['authority'] for entry in result['leaves']])
        self.assertEqual(result['certification'], 'not_performed_by_projector')

    def test_wrong_identity_join_and_wrong_kind_keep_the_proposed_roles(self):
        joined = candidate('JOIN', {'deviceHolds': [1, 2]})
        kind = candidate('KIND', {'usbConnected': [3]})
        bindings = [bind(joined, 'devices', ['devices', 0, 'serial'], 'device_serial'),
                    bind(joined, 'devices', ['devices', 0, 'volume'], 'volume'),
                    bind(joined, 'devices', ['devices', 0, 'linked'], 'same_device_holds_volume'),
                    bind(kind, 'devices', ['devices', 1, 'serial'], 'device_serial')]
        result = project_answers(public(), [joined, kind], bindings, self.source)
        values = result['submission']['answers'][0]['answer']['devices']
        self.assertEqual(values, [{'serial': 'DEVICE-A', 'volume': 'VOLUME-V', 'linked': True}, {'serial': 'query text'}])
        self.assertEqual(claim_fields(kind['claim'], self.source)['parts'][0]['fields']['record_kind']['value'], 'usbInsert')
        serial = next(entry for entry in result['leaves'] if entry['candidate_id'] == 'JOIN' and entry['field'] == 'device_serial')
        self.assertEqual(serial['record_ids'], [1, 2])
        self.assertEqual(serial['value_record_ids'], [1])
        self.assertEqual(result['projection']['candidates']['JOIN']['records'][1]['obj_text'], 'DEVICE-B')

    def test_whole_conjunction_dependency_prevents_salvaging_its_good_part(self):
        row = candidate('BOTH', {'both': [{'usbConnected': [1]}, {'before': [5, 4]}]})
        plan = prepare_projection(public(), [row], [bind(row, 'devices', ['devices', 0, 'serial'], 'device_serial')], self.source)
        filtered = render_projection(plan, admitted_ids=[], authority='recorded_certificates')
        self.assertEqual(filtered['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(filtered['dropped'][0]['reason'], 'whole_candidate_not_admitted')
        self.assertEqual(filtered['dropped'][0]['candidate_id'], 'BOTH')

    def test_partial_objects_arrays_and_zero_values_never_get_null_fillers(self):
        one, two, count = candidate('ONE', {'usbConnected': [1]}), candidate('TWO', {'usbConnected': [3]}), candidate('ZERO', {'exactly': ['usbInsert', 0]})
        plan = prepare_projection(public(), [one, two, count], [
            bind(one, 'devices', ['devices', 0, 'serial'], 'device_serial'),
            bind(two, 'devices', ['devices', 8, 'serial'], 'device_serial'), bind(count, 'count', [], 'count')], self.source)
        result = render_projection(plan, admitted_ids=['TWO', 'ZERO'], authority='recorded_certificates')
        self.assertEqual(result['submission']['answers'][0]['answer'], {'devices': [{'serial': 'query text'}]})
        self.assertEqual(result['leaves'][0]['path'], ['devices', 8, 'serial'])
        self.assertEqual(result['leaves'][0]['output_path'], ['devices', 0, 'serial'])
        self.assertEqual(result['submission']['answers'][1]['answer'], 0)
        self.assertEqual(result['submission']['answers'][-1]['status'], 'unknown')

    def test_conflicting_leaves_are_omitted_not_overwritten_identical_ones_keep_all_links(self):
        first, second = candidate('A', {'usbConnected': [1]}), candidate('B', {'usbConnected': [3]})
        path = ['devices', 0, 'serial']
        conflict = project_answers(public(), [first, second], [bind(first, 'devices', path, 'device_serial'),
                                   bind(second, 'devices', path, 'device_serial')], self.source)
        self.assertEqual(conflict['submission']['answers'][0]['status'], 'unknown')
        self.assertEqual(conflict['conflicts'][0]['binding_indices'], [0, 1])
        self.assertEqual(conflict['leaves'], [])
        twin = candidate('TWIN', first['claim'])
        same = project_answers(public(), [first, twin], [bind(first, 'devices', path, 'device_serial'),
                               bind(twin, 'devices', path, 'device_serial')], self.source)
        self.assertEqual(len(same['leaves']), 2)
        self.assertFalse(same['conflicts'])

    def test_hash_value_and_plan_tampering_fail_without_repair(self):
        row = candidate('A', {'usbConnected': [1]})
        good = bind(row, 'devices', ['devices', 0, 'serial'], 'device_serial')
        bad_hash = dict(good, claim_sha256='0' * 64)
        bad_value = dict(good, value='DEVICE-B')
        result = project_answers(public(), [row], [bad_hash, bad_value], self.source)
        self.assertEqual([e['reason'] for e in result['unsupported']], ['claim_hash_mismatch', 'literal_value_mismatch_not_repaired'])
        self.assertEqual(result['unsupported'][1]['binding']['value'], 'DEVICE-B')
        plan = prepare_projection(public(), [row], [good], self.source)
        plan['bindings'][0]['value'] = 'ALTERED'
        with self.assertRaisesRegex(ValueError, 'digest changed'):
            render_projection(plan)

    def test_missing_records_provenance_fields_and_unknown_forms_explain_limits(self):
        missing = candidate('MISSING', {'usbConnected': [999]})
        unsupported = candidate('INTENT', {'intentionalLeak': [1]})
        valid = candidate('OK', {'programRan': [1]})
        result = project_answers(public(), [missing, unsupported, valid], [
            bind(missing, 'devices', ['devices', 0, 'serial'], 'device_serial'),
            bind(unsupported, 'order', [], 'intent'),
            bind(valid, 'count', [], 'execution_count')], self.source)
        self.assertEqual(len(result['unsupported']), 3)
        self.assertEqual(result['projection']['candidates']['MISSING']['missing_record_ids'], [999])
        self.assertTrue(result['projection']['candidates']['INTENT']['unsupported'])
        self.assertNotIn('execution_time', catalog()['forms']['programRan'])
        self.assertEqual(result['unbound_candidate_ids'], ['MISSING', 'INTENT', 'OK'])

    def test_explicit_time_formats_preserve_semantics_and_use_public_zone(self):
        row = candidate('A', {'usbConnected': [1]})
        bindings = [bind(row, 'devices', ['devices', 0, 'time'], 'recorded_time_us', format='utc_iso'),
                    bind(row, 'devices', ['devices', 1, 'time'], 'recorded_time_us', format='local_minute')]
        result = project_answers(public(), [row], bindings, self.source)
        self.assertEqual(result['submission']['answers'][0]['answer']['devices'],
                         [{'time': '1970-01-01T00:01:40Z'}, {'time': '1969-12-31 16:01'}])
        self.assertEqual(result['leaves'][0]['semantic_type'], 'recorded_timestamp_not_action_or_execution_guarantee_us')

    def test_general_public_schema_and_recorded_certificate_alias_work_without_mutation(self):
        contract = {'schema_version': 2, 'case_id': 'new-case', 'questions': [
            {'id': 'size', 'prompt': 'Recorded numeric setting?', 'answer_schema': {'type': 'integer'}}]}
        row = {'finding_id': 'F1', 'claim': {'settingRecorded': [7]}, 'status': 'verified'}
        binding = bind(row, 'size', [], 'value', format='integer')
        before = deepcopy((contract, row, binding))
        result = project_answers(contract, [row], [binding], self.source, authority='recorded_certificates')
        self.assertEqual(result['submission']['answers'][0]['answer'], 123)
        self.assertEqual((contract, row, binding), before)
        self.assertEqual(result['certification'], 'not_performed_by_projector')
        contract['expected'] = 'private'
        with self.assertRaises(ValueError):
            project_answers(contract, [row], [binding], self.source)

    def test_bad_structural_path_or_value_type_stays_unsupported(self):
        row = candidate('A', {'usbConnected': [1]})
        result = project_answers(public(), [row], [bind(row, 'devices', ['not_in_schema'], 'device_serial'),
                                  bind(row, 'count', [], 'device_serial')], self.source)
        self.assertEqual([e['reason'] for e in result['unsupported']], ['field_not_in_public_schema', 'value_type_does_not_match_public_schema'])

    def test_checker_only_same_record_restriction_does_not_filter_unchecked_meaning(self):
        row = candidate('SELF', {'sameContent': [8, 8]})
        with patch('checker.claims.parse', side_effect=AssertionError('no semantic gate in projection')):
            result = project_answers(public(), [row], [bind(row, 'order', [], 'same_recorded_content_hash')], self.source)
        self.assertIs(result['submission']['answers'][2]['answer'], True)
        self.assertEqual(result['unsupported'], [])

    def test_missing_rows_do_not_rewrite_an_asserted_literal_relation(self):
        row = candidate('MISSING', {'before': [999, 1000]})
        result = project_answers(public(), [row], [bind(row, 'order', [], 'precedes_beyond_uncertainty')], self.source)
        self.assertIs(result['submission']['answers'][2]['answer'], True)
        self.assertEqual(result['leaves'][0]['record_ids'], [999, 1000])
        self.assertEqual(result['projection']['candidates']['MISSING']['missing_record_ids'], [999, 1000])

    def test_prefix_and_container_conflicts_are_explicit_and_partial_siblings_survive(self):
        contract = {'schema_version': 2, 'case_id': 'flexible', 'questions': [{'id': 'Q', 'prompt': 'Public', 'answer_schema': {}}]}
        row = candidate('A', {'usbConnected': [1]})
        for paths, reason in (([['x'], ['x', 'child']], 'ancestor_and_descendant_bindings_conflict'),
                              ([['x', 0], ['x', 'field']], 'object_and_array_paths_conflict')):
            bindings = [bind(row, 'Q', path, 'device_serial') for path in paths]
            bindings.append(bind(row, 'Q', ['retained'], 'device_serial'))
            result = project_answers(contract, [row], bindings, self.source)
            self.assertEqual(result['submission']['answers'][0]['answer'], {'retained': 'DEVICE-A'})
            self.assertEqual(result['conflicts'][0]['reason'], reason)


if __name__ == '__main__':
    unittest.main()
