"""Strict binding transport preserves invalid attempts without inventing answers."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from agent.answer_projection import claim_digest
from comparison.ablation.bindings import extract_bindings, resolve_hashes


def public():
    return {'schema_version': 2, 'case_id': 'fixture', 'questions': [{'id': 'Q1'}, {'id': 'Q2'}]}


def document():
    return {'schema_version': 1, 'case_id': 'fixture',
            'bindings': [{'question_id': 'Q1', 'candidate_id': 'P1', 'field': 'path', 'path': ['name']}],
            'unanswered': [{'question_id': 'Q2', 'reason': 'Not established.'}]}


def summary(doc):
    return b'Public summary.\n```json\n' + json.dumps(doc).encode() + b'\n```\n'


class ExtractBindings(unittest.TestCase):
    def test_preserves_exact_block_bytes_and_invalid_binding_contents(self):
        raw = b'{"schema_version":1, "case_id":"fixture", "bindings":[null, 7, {"question_id":"Q1", "path":false, "value":null, "extension":1}], "unanswered":[{"question_id":"Q2","reason":"unknown"}]}\r\n'
        doc, block = extract_bindings(b'Summary\r\n```json\r\n' + raw + b'```\r\n', public())
        self.assertEqual(block, raw)
        self.assertEqual(doc['bindings'], [None, 7, {'question_id': 'Q1', 'path': False, 'value': None, 'extension': 1}])

    def test_strict_accounting_is_attempt_presence_not_selector_support(self):
        doc = document()
        doc['bindings'] += [{'question_id': 'foreign'}, {'question_id': 'Q1', 'field': 'invalid'}]
        parsed, _ = extract_bindings(summary(doc), public())
        self.assertEqual(parsed, doc)
        # Unknown IDs survive for unsupported diagnostics but do not cover Q1.
        doc['bindings'] = [{'question_id': 'foreign'}]
        with self.assertRaisesRegex(ValueError, 'every public question'):
            extract_bindings(summary(doc), public())

    def test_no_inference_from_prose_and_no_unanswered_overlap_duplicates_or_foreign_ids(self):
        for mutate in (lambda d: d.update(bindings=[]),
                       lambda d: d['unanswered'].append(deepcopy(d['unanswered'][0])),
                       lambda d: d['unanswered'].append({'question_id': 'Q1', 'reason': 'overlap'}),
                       lambda d: d['unanswered'][0].update(question_id='foreign'),
                       lambda d: d['unanswered'][0].update(reason='  ')):
            doc = document()
            mutate(doc)
            with self.assertRaises(ValueError):
                extract_bindings(b'Q1 answered in prose.\n' + summary(doc), public())

    def test_bad_outer_shape_case_or_version_is_refused(self):
        for mutate in (lambda d: d.update(answer='invented'), lambda d: d.update(case_id='other'),
                       lambda d: d.update(schema_version=True), lambda d: d.update(bindings={}),
                       lambda d: d.update(unanswered=None)):
            doc = document()
            mutate(doc)
            with self.assertRaises(ValueError):
                extract_bindings(summary(doc), public())

    def test_finite_unique_json_and_single_block_are_required(self):
        valid = summary(document())
        invalid = [valid + valid, valid + b'```json\nunfinished', b'No block',
                   b'```json\n{}\n```\n```json\n{}\n```',
                   valid.replace(b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1'),
                   valid.replace(b'"path": ["name"]', b'"path": ["name"], "value": NaN'),
                   valid.replace(b'"path": ["name"]', b'"path": ["name"], "value": 1e999'),
                   b'\xff' + valid]
        for raw in invalid:
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                extract_bindings(raw, public())

    def test_byte_binding_and_depth_bounds_are_explicit(self):
        with patch('comparison.ablation.bindings.MAX_BYTES', 20), self.assertRaises(ValueError):
            extract_bindings(summary(document()), public())
        doc = document()
        doc['bindings'] *= 2
        with patch('comparison.ablation.bindings.MAX_BINDINGS', 1), self.assertRaises(ValueError):
            extract_bindings(summary(doc), public())
        doc = document()
        nested = None
        for _ in range(70):
            nested = [nested]
        doc['bindings'][0]['value'] = nested
        with self.assertRaisesRegex(ValueError, 'depth'):
            extract_bindings(summary(doc), public())


class ResolveHashes(unittest.TestCase):
    def test_only_absent_hash_is_filled_without_selector_value_or_input_changes(self):
        candidates = [{'candidate_id': 'P1', 'claim': {'both': [{'exactly': ['fileSeen', 7]}, {'fileRecorded': [1]}]}},
                      {'finding_id': 'A001', 'claim': {'fileRecorded': [2]}}]
        bindings = [
            {'question_id': 'Q1', 'candidate_id': 'P1', 'part': 99, 'field': 'unsupported', 'value': False, 'path': []},
            {'candidate_id': 'P1', 'claim_sha256': None, 'value': 'wrong literal'},
            {'candidate_id': 'P1', 'claim_sha256': 'wrong'},
            {'candidate_id': 'A001'}, {'candidate_id': 'unknown'}, {'candidate_id': []}, None, 7]
        saved = deepcopy((bindings, candidates))
        resolved, provenance = resolve_hashes(bindings, candidates)
        self.assertEqual((bindings, candidates), saved)
        expected = deepcopy(bindings)
        expected[0]['claim_sha256'] = claim_digest(candidates[0]['claim'])
        expected[3]['claim_sha256'] = claim_digest(candidates[1]['claim'])
        self.assertEqual(resolved, expected)
        self.assertEqual(provenance, [
            {'binding_index': i, 'candidate_id': cid, 'claim_sha256': expected[i]['claim_sha256'],
             'hash_source': 'exact_candidate_claim'} for i, cid in [(0, 'P1'), (3, 'A001')]])
        resolved[0]['path'].append('changed')
        self.assertEqual(bindings[0]['path'], [])

    def test_duplicate_candidates_and_mismatched_aliases_are_setup_failures(self):
        row = {'candidate_id': 'P1', 'claim': {'exactly': ['fileSeen', 1]}}
        for candidates in ([row, deepcopy(row)], [row, dict(row, claim={})],
                           [dict(row, finding_id='other')], [dict(row, finding_id=None)],
                           [{'candidate_id': 'P1'}], [{'claim': {}}], [None]):
            with self.subTest(candidates=candidates), self.assertRaises(ValueError):
                resolve_hashes([], candidates)
        resolved, _ = resolve_hashes([{'candidate_id': 'P1'}], [dict(row, finding_id='P1')])
        self.assertEqual(resolved[0]['claim_sha256'], claim_digest(row['claim']))

    def test_exact_claim_types_and_order_are_not_normalized(self):
        rows = [{'candidate_id': 'P1', 'claim': {'x': [1, 2]}},
                {'candidate_id': 'P2', 'claim': {'x': [2, 1]}},
                {'candidate_id': 'P3', 'claim': '{"x":[1,2]}'}]
        resolved, _ = resolve_hashes([{'candidate_id': r['candidate_id']} for r in rows], rows)
        self.assertEqual(len({r['claim_sha256'] for r in resolved}), 3)

    def test_finite_and_node_bounds_apply_to_pure_inputs(self):
        for bindings, candidates in ([{'value': float('nan')}], []), ([], [{'candidate_id': 'P1', 'claim': float('inf')}]):
            with self.assertRaises(ValueError):
                resolve_hashes(bindings, candidates)
        with patch('comparison.ablation.bindings.MAX_NODES', 4), self.assertRaises(ValueError):
            resolve_hashes([{'candidate_id': 'P1', 'path': [1, 2, 3]}], [])


if __name__ == '__main__':
    unittest.main()
