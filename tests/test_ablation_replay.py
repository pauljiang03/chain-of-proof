"""Offline B keeps the A population intact and independently rechecks certificates."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from checker import check as checker
from comparison.ablation.capture import ReceiptWorkbench, seal_candidates
from comparison.ablation.replay import replay

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / 'fixtures/sample_facts.json'


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'A'
        self.out = self.root / 'B'
        self.wb = ReceiptWorkbench(FACTS, self.directory)
        self.addCleanup(self.wb._db.close)

    def seal(self):
        return seal_candidates(self.directory, facts_path=FACTS, metadata={'model_calls': 0})

    def run_replay(self, facts=FACTS):
        return replay(self.directory / 'seal.json', facts, self.out)

    def ledger(self):
        return [json.loads(line) for line in (self.out / 'replay.jsonl').read_text().splitlines()]

    def test_exact_whole_claim_population_real_lean_and_independent_replay(self):
        claims = [{'usbConnected': [4512]}, {'usbConnected': [4512]}, {'searched': [4512]},
                  {'both': [{'usbConnected': [4512]}, {'searched': [4512]}]},
                  ' {"usbConnected":[4512]} ', {'imaginaryRule': [4512]},
                  {'usbConnected': [999999]}, {'searched': []}]
        for index, claim in enumerate(claims):
            self.wb.check(f'question {index}', claim, 'unknown revision' if index == 1 else None)
        self.seal()
        before = {path.name: path.read_bytes() for path in self.directory.iterdir() if path.is_file()}
        with patch('comparison.ablation.replay.checker.check', wraps=checker.check) as check:
            summary = self.run_replay()
        self.assertEqual([call.args[0] for call in check.call_args_list], claims)
        self.assertEqual([call.args[1] for call in check.call_args_list], [f'P{n:06d}' for n in range(1, 9)])
        self.assertEqual(summary['counts'], {'verified': 2, 'rejected': 3, 'malformed': 2, 'unsupported': 1, 'error': 0})
        self.assertEqual(summary['independent_verification'], {'checked': 2, 'verified': 2, 'failed': 0})
        self.assertEqual(summary['accepted_candidate_ids'], ['P000001', 'P000002'])
        self.assertEqual(summary['model_calls'], 0)
        self.assertFalse(summary['candidate_repair'])
        self.assertFalse(summary['ground_truth_error_labels'])
        self.assertEqual([row['claim'] for row in self.ledger()], claims)
        self.assertEqual(self.ledger()[1]['revises'], 'unknown revision')
        self.assertIn('missing_record', self.ledger()[6]['reason_categories'])
        self.assertFalse((self.out / 'certificates/P000004.json').exists())
        self.assertEqual((self.out / 'candidates.jsonl').read_bytes(), before['candidates.jsonl'])
        self.assertEqual({path.name: path.read_bytes() for path in self.directory.iterdir() if path.is_file()}, before)
        self.assertEqual(json.loads((self.out / 'summary.json').read_text()), summary)

    def test_wrong_facts_and_mutated_log_fail_before_any_checker_or_output(self):
        self.wb.check('question', {'usbConnected': [4512]})
        self.seal()
        other = self.root / 'other.json'
        other.write_bytes(FACTS.read_bytes() + b'\n')
        with patch('comparison.ablation.replay.checker.check') as check:
            with self.assertRaises(ValueError):
                self.run_replay(other)
            self.assertFalse(self.out.exists())
            with (self.directory / 'candidates.jsonl').open('ab') as stream:
                stream.write(b'\n')
            with self.assertRaises(ValueError):
                self.run_replay()
            check.assert_not_called()
            self.assertFalse(self.out.exists())

    def test_fixed_manifest_paths_and_count_are_enforced(self):
        self.wb.check('question', {'usbConnected': [4512]})
        seal = self.seal()
        for modification in ({'file': '../../other.json'}, {'count': 5}, {'bytes': True}):
            altered = {**seal, 'candidates': {**seal['candidates'], **modification}}
            (self.directory / 'seal.json').write_text(json.dumps(altered))
            with patch('comparison.ablation.replay.checker.check') as check, self.assertRaises(ValueError):
                self.run_replay()
            check.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_invalid_order_is_not_fixed_even_with_updated_hash(self):
        self.wb.check('question', {'usbConnected': [4512]})
        seal = self.seal()
        entry = json.loads((self.directory / 'candidates.jsonl').read_text())
        entry['candidate_id'] = 'P000002'
        raw = (json.dumps(entry) + '\n').encode()
        (self.directory / 'candidates.jsonl').write_bytes(raw)
        seal['candidates'].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        (self.directory / 'seal.json').write_text(json.dumps(seal))
        with self.assertRaises(ValueError):
            self.run_replay()
        self.assertFalse(self.out.exists())

    def test_existing_output_and_source_nested_output_are_refused(self):
        self.seal()
        self.out.mkdir()
        (self.out / 'keep').write_text('keep')
        with self.assertRaises(FileExistsError):
            self.run_replay()
        self.assertEqual((self.out / 'keep').read_text(), 'keep')
        with self.assertRaises(ValueError):
            replay(self.directory / 'seal.json', FACTS, self.directory / 'nested-B')
        self.assertFalse((self.directory / 'nested-B').exists())

    def test_empty_sealed_run_yields_zero_counts_without_checker(self):
        self.seal()
        with patch('comparison.ablation.replay.checker.check') as check:
            result = self.run_replay()
        check.assert_not_called()
        self.assertEqual(result['total'], 0)
        self.assertEqual(sum(result['counts'].values()), 0)

    def test_checker_failure_is_safe_counted_and_does_not_drop_next_candidate(self):
        self.wb.check('first', [])
        self.wb.check('second', None)
        self.seal()
        result = {'status': 'rejected', 'proof_gap': {'requirements': [{'category': 'malformed_claim'}]}}
        with patch('comparison.ablation.replay.checker.check', side_effect=[RuntimeError('SECRET_PAYLOAD'), result]) as check:
            summary = self.run_replay()
        self.assertEqual(check.call_count, 2)
        self.assertEqual(summary['counts']['error'], 1)
        self.assertEqual(summary['counts']['malformed'], 1)
        self.assertEqual(self.ledger()[0]['error'], {'stage': 'checker', 'type': 'RuntimeError'})
        self.assertNotIn('SECRET_PAYLOAD', (self.out / 'replay.jsonl').read_text())

    def test_failed_independent_verification_never_counts_as_verified(self):
        self.wb.check('question', {'usbConnected': [4512]})
        self.seal()
        with patch('comparison.ablation.replay.verify', return_value=['Synthetic verifier failure']) as verify:
            summary = self.run_replay()
        verify.assert_called_once()
        self.assertEqual(summary['counts']['verified'], 0)
        self.assertEqual(summary['counts']['error'], 1)
        self.assertEqual(summary['independent_verification'], {'checked': 1, 'verified': 0, 'failed': 1})
        self.assertEqual(summary['accepted_candidate_ids'], [])
        self.assertEqual(self.ledger()[0]['error']['type'], 'CertificateVerificationError')

    def test_sealed_input_mutation_during_check_blocks_final_summary(self):
        self.wb.check('question', [])
        self.seal()
        def mutate(*_args, **_kwargs):
            with (self.directory / 'candidates.jsonl').open('ab') as stream:
                stream.write(b'\n')
            return {'status': 'rejected', 'proof_gap': {'requirements': [{'category': 'malformed_claim'}]}}
        with patch('comparison.ablation.replay.checker.check', side_effect=mutate), self.assertRaises(ValueError):
            self.run_replay()
        self.assertFalse((self.out / 'summary.json').exists())
        self.assertEqual(len(self.ledger()), 1)


if __name__ == '__main__':
    unittest.main()
