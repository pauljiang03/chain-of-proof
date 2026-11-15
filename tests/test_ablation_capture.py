"""A receipts retain JSON submissions without invoking proof or repair paths."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent.audit import verify_audit
from agent.tools import Workbench
from comparison.ablation.capture import ReceiptWorkbench, seal_candidates

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / 'fixtures/sample_facts.json'


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'A'
        self.wb = ReceiptWorkbench(FACTS, self.directory)
        self.addCleanup(self.wb._db.close)

    def entries(self):
        return [json.loads(line) for line in (self.directory / 'candidates.jsonl').read_text().splitlines()]

    def test_no_checker_parser_revision_validation_or_dedup(self):
        raw = [({'searched': [4512]}, 'unknown'), ({'searched': [4512]}, 'P000002'),
               ('  {"searched": [4512]}  ', ['forward', 22]), (None, {'bad': True}),
               ({'both': [{'searched': []}, {'imaginary': [1]}]}, None)]
        with patch('checker.check.check', side_effect=AssertionError('checker called')), \
                patch('checker.claims.parse', side_effect=AssertionError('parser called')), \
                patch('agent.history.validate_revision', side_effect=AssertionError('revision checked')):
            for index, (claim, revises) in enumerate(raw, 1):
                receipt = self.wb.check({'raw question': index}, claim, revises)
                self.assertEqual(receipt, {'candidate_id': f'P{index:06d}', 'status': 'unverified', 'receipt': 'recorded'})
        rows = self.entries()
        self.assertEqual([row['claim'] for row in rows], [claim for claim, _ in raw])
        self.assertEqual(rows[0]['revises'], 'unknown')
        self.assertEqual(rows[1]['revises'], 'P000002')
        self.assertNotIn('revises', rows[-1])
        self.assertFalse((self.directory / 'proposals.jsonl').exists())
        self.assertFalse(list(self.directory.glob('*.lean')))
        self.assertTrue(verify_audit(self.directory / 'audit.jsonl')['passed'])

    def test_read_tools_match_workbench_and_conclusion_is_disabled(self):
        original = Workbench(FACTS, Path(self.temp.name) / 'C')
        self.addCleanup(original._db.close)
        self.assertEqual(self.wb.forms(), original.forms())
        self.assertEqual(self.wb.fact(4512), original.fact(4512))
        self.assertEqual(self.wb.sql('SELECT id FROM facts ORDER BY id LIMIT 3'),
                         original.sql('SELECT id FROM facts ORDER BY id LIMIT 3'))
        with self.assertRaises(RuntimeError):
            self.wb.conclude('unsupported judgment', [])
        self.assertFalse((self.directory / 'conclusions.jsonl').exists())

    def test_nonfinite_or_non_json_values_are_not_coerced(self):
        for value in (float('nan'), float('inf'), {'x': (1, 2)}, {1: 'integer key'}, object()):
            with self.subTest(kind=type(value).__name__), self.assertRaises((ValueError, TypeError)):
                self.wb.check('question', value)
        self.assertEqual(self.entries(), [])
        self.assertEqual(self.wb.check('question', {'value': -0.0})['candidate_id'], 'P000001')

    def test_reconstructed_and_concurrent_processes_keep_ids_and_audit(self):
        self.wb.check('first', {'usbConnected': [4512]})
        program = '''import sys
from comparison.ablation.capture import ReceiptWorkbench
wb=ReceiptWorkbench(sys.argv[1],sys.argv[2])
wb.fact(4512)
wb.check('same question',{'usbConnected':[4512]})
'''
        def submit(_):
            return subprocess.run([sys.executable, '-c', program, str(FACTS), str(self.directory)],
                                  cwd=ROOT, capture_output=True, text=True, timeout=20)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(submit, range(8)))
        self.assertEqual([result.returncode for result in outcomes], [0] * 8,
                         [result.stderr for result in outcomes if result.returncode])
        self.assertEqual([row['candidate_id'] for row in self.entries()], [f'P{n:06d}' for n in range(1, 10)])
        state = verify_audit(self.directory / 'audit.jsonl')
        self.assertTrue(state['passed'], state)
        self.assertEqual(state['count'], 17)

    def test_seal_exact_bytes_no_overwrite_and_blocks_future_receipts(self):
        self.wb.check(' q ', {'searched': [4512]}, 'not a real prior ID')
        before = (self.directory / 'candidates.jsonl').read_bytes()
        metadata = {'model': 'synthetic-only', 'ignored_path': '/does/not/exist'}
        seal = seal_candidates(self.directory, facts_path=FACTS, metadata=metadata)
        self.assertEqual(seal['candidates']['count'], 1)
        self.assertEqual(seal['candidates']['bytes'], len(before))
        self.assertEqual(seal['metadata'], metadata)
        self.assertEqual(json.loads((self.directory / 'seal.json').read_text()), seal)
        with self.assertRaises(FileExistsError):
            seal_candidates(self.directory, facts_path=FACTS)
        with self.assertRaises(ValueError):
            self.wb.check('late', {'searched': [3100]})
        with self.assertRaises(ValueError):
            ReceiptWorkbench(FACTS, self.directory)
        self.assertEqual((self.directory / 'candidates.jsonl').read_bytes(), before)

    def test_empty_startup_failure_can_be_sealed(self):
        empty = Path(self.temp.name) / 'failed-before-tools'
        empty.mkdir()
        seal = seal_candidates(empty, facts_path=FACTS)
        self.assertEqual(seal['candidates']['count'], 0)
        self.assertEqual((empty / 'candidates.jsonl').read_bytes(), b'')

    def test_damaged_log_is_never_repaired_or_sealed(self):
        path = self.directory / 'candidates.jsonl'
        for raw in (b'{"claim":', b'{"x":NaN}\n', b'{"x":1e999}\n', b'{"x":1,"x":2}\n', b'{}\n', b'\n'):
            path.write_bytes(raw)
            with self.assertRaises((ValueError, UnicodeError)):
                seal_candidates(self.directory, facts_path=FACTS)
            with self.assertRaises((ValueError, UnicodeError)):
                ReceiptWorkbench(FACTS, self.directory)
            self.assertEqual(path.read_bytes(), raw)
            self.assertFalse((self.directory / 'seal.json').exists())

    def test_symlink_and_fifo_logs_refused_without_reading(self):
        path = self.directory / 'candidates.jsonl'
        path.unlink()
        path.symlink_to(FACTS)
        with self.assertRaises((ValueError, OSError)):
            seal_candidates(self.directory, facts_path=FACTS)
        path.unlink()
        os.mkfifo(path)
        with self.assertRaises(ValueError):
            seal_candidates(self.directory, facts_path=FACTS)


if __name__ == '__main__':
    unittest.main()
