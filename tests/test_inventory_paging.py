"""Bounded inventory traversal and explicit SQL clipping diagnostics."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest
from pathlib import Path

from agent.inventory_pages import render_rows, page, inventory_progress
from agent.tools import Workbench, CELL_LIMIT, ROW_LIMIT

ROOT = Path(__file__).resolve().parents[1]


class Rendering(unittest.TestCase):
    def test_clipping_locations_preserve_column_identity_and_length(self):
        result = render_rows(['same', 'same', 'n'], [('abcde', 'longer', 4), ('ok', None, 5)], 4)
        self.assertEqual(result['rows'], [['abcd…', 'long…', 4], ['ok', None, 5]])
        self.assertEqual(result['cell_truncations'], [
            {'row_index': 0, 'column_index': 0, 'column': 'same', 'original_chars': 5},
            {'row_index': 0, 'column_index': 1, 'column': 'same', 'original_chars': 6}])
        self.assertTrue(result['cells_truncated'])

    def test_sql_reports_row_and_cell_truncation_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            bench = Workbench(ROOT / 'evidence/case_facts.json', Path(directory))
            result = bench.sql("SELECT id, printf('%0300d', id) AS expanded FROM facts ORDER BY id")
            self.assertEqual(len(result['rows']), ROW_LIMIT)
            self.assertIn('truncated', result)
            self.assertEqual(len(result['cell_truncations']), ROW_LIMIT)
            self.assertEqual(len(result['rows'][0][1]), CELL_LIMIT + 1)
            self.assertEqual(result['cell_truncations'][0]['original_chars'], 300)
            small = bench.sql('SELECT 1 AS n')
            self.assertFalse(small['cells_truncated'])
            self.assertEqual(small['cell_truncations'], [])


class Paging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = sqlite3.connect(':memory:', check_same_thread=False)
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE facts (id INTEGER PRIMARY KEY, kind TEXT, exhibit TEXT, obj TEXT)')
        self.db.executemany('INSERT INTO facts VALUES (?, ?, ?, ?)', [
            (0, 'a', 'one', 'z' * 300), (4, 'a', 'one', 'b'),
            (8, 'a', 'two', 'c'), (11, 'b', 'one', 'd'), (20, 'a', 'one', 'e')])

    def call(self, **kwargs):
        return page(self.db, self.root, 'a' * 64, 'Q1', **kwargs)

    def test_sequential_exact_filters_cover_sparse_ids_once_and_persist(self):
        first = self.call(kinds=['a'], exhibits=['one'], page_size=1)
        self.assertEqual(first['rows'][0][0], 0)
        self.assertTrue(first['cells_truncated'])
        self.assertFalse(first['exhausted'])
        ids = [0]
        result = first
        while not result['exhausted']:
            result = self.call(kinds=['a'], exhibits=['one'], page_size=1, cursor=result['next_cursor'])
            ids.extend(row[0] for row in result['rows'])
        self.assertEqual(ids, [0, 4, 20])
        progress = inventory_progress(self.root, 'a' * 64)['traversals'][0]
        self.assertEqual(progress['rows_returned'], 3)
        self.assertEqual(progress['pages_returned'], 3)
        self.assertTrue(progress['exhausted'])
        self.assertIn('question completeness', result['limitation'])
        with self.assertRaises(ValueError):
            self.call(kinds=['a'], exhibits=['one'], page_size=1)

    def test_empty_scope_is_exhausted_without_claiming_absence(self):
        result = self.call(kinds=['missing'])
        self.assertEqual(result['rows'], [])
        self.assertTrue(result['exhausted'])
        self.assertEqual(result['progress']['rows_returned'], 0)

    def test_stale_tampered_foreign_request_and_evidence_rejected(self):
        first = self.call(page_size=1)
        token = first['next_cursor']
        for kwargs in ({'cursor': token + 'x'}, {'cursor': token, 'kinds': ['a']},
                       {'cursor': token, 'page_size': 2}):
            with self.assertRaises(ValueError):
                self.call(**kwargs)
        self.call(page_size=1, cursor=token)
        with self.assertRaises(ValueError):
            self.call(page_size=1, cursor=token)
        with self.assertRaises(ValueError):
            page(self.db, self.root, 'b' * 64, 'Q1', page_size=1)

    def test_bounds_and_symlinks_rejected(self):
        for kwargs in ({'page_size': True}, {'page_size': 251}, {'kinds': []},
                       {'exhibits': ['x'] * 33}, {'kinds': ['x' * 257]}):
            with self.assertRaises(ValueError):
                self.call(**kwargs)
        target = self.root / 'target.json'
        target.write_text('{}')
        (self.root / 'inventory-progress.json').symlink_to(target)
        with self.assertRaises(ValueError):
            self.call()
        with self.assertRaises(ValueError):
            inventory_progress(self.root)
        self.assertEqual(target.read_text(), '{}')

    def test_parallel_consumption_of_same_cursor_advances_only_once(self):
        first = self.call(page_size=1)
        def advance(_):
            try:
                return self.call(page_size=1, cursor=first['next_cursor'])['rows'][0][0]
            except ValueError:
                return 'stale'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(advance, range(2)))
        self.assertCountEqual(results, [4, 'stale'])

    def test_corrupt_persisted_state_is_rejected_before_continuation(self):
        from copy import deepcopy
        first = self.call(page_size=1)
        path = self.root / 'inventory-progress.json'
        original = json.loads(path.read_text())
        key = first['progress']['traversal_id']
        mutations = [
            lambda s: s.pop('evidence_sha256'),
            lambda s: s.update(evidence_sha256='not-a-digest'),
            lambda s: s.update(schema_version=True),
            lambda s: s['traversals'][key].pop('last_id'),
            lambda s: s['traversals'][key].update(question_id='different'),
            lambda s: s['traversals'][key].update(kinds=['z', 'a']),
            lambda s: s['traversals'][key].update(kinds=['a', 'a']),
            lambda s: s['traversals'][key].update(last_id=True),
            lambda s: s['traversals'][key].update(last_id=-2),
            lambda s: s['traversals'][key].update(rows_returned=-1),
            lambda s: s['traversals'][key].update(rows_returned=0),
            lambda s: s['traversals'][key].update(pages_returned=0),
            lambda s: s['traversals'][key].update(pages_returned=10001),
            lambda s: s['traversals'][key].update(exhausted=1),
            lambda s: s['traversals'][key].update(next_cursor=None),
            lambda s: s['traversals'][key].update(next_cursor='x' * 97),
            lambda s: s['traversals'][key].update(exhausted=True),
        ]
        for mutate in mutations:
            state = deepcopy(original)
            mutate(state)
            path.write_text(json.dumps(state))
            with self.subTest(state=state), self.assertRaises(ValueError):
                inventory_progress(self.root)
            with self.assertRaises(ValueError):
                self.call(page_size=1, cursor=first['next_cursor'])
        path.write_text(json.dumps(original))
        self.assertEqual(inventory_progress(self.root)['status'], 'recorded')

    def test_duplicate_nonfinite_oversize_and_nonregular_state_rejected(self):
        from agent.inventory_pages import MAX_BYTES
        path = self.root / 'inventory-progress.json'
        for raw in ('{"schema_version":1,"schema_version":1}', '{"x":NaN}',
                    '{"x":Infinity}', '{"x":-Infinity}', ' ' * (MAX_BYTES + 1),
                    '"' + 'é' * (MAX_BYTES // 2) + '"'):
            path.write_text(raw)
            with self.subTest(raw=raw[:50]), self.assertRaises(ValueError):
                inventory_progress(self.root)
        path.unlink()
        import os
        os.mkfifo(path)
        with self.assertRaises(ValueError):
            inventory_progress(self.root)
        path.unlink()
        path.mkdir()
        with self.assertRaises(ValueError):
            inventory_progress(self.root)

    def test_direct_run_directory_symlink_rejected(self):
        alias = self.root / 'alias'
        real = self.root / 'real'
        real.mkdir()
        alias.symlink_to(real, target_is_directory=True)
        with self.assertRaises(ValueError):
            inventory_progress(alias)
        with self.assertRaises(ValueError):
            page(self.db, alias, 'a' * 64, 'Q1')

    def test_workbench_requires_public_question_and_unchanged_evidence(self):
        from agent.investigation import Investigation
        from agent.case import CaseProfile
        import shutil
        facts = self.root / 'facts.json'
        shutil.copyfile(ROOT / 'evidence/case_facts.json', facts)
        bench = Workbench(facts, self.root)
        Investigation(self.root).initialize(CaseProfile('case', 'brief', ('Which?',)))
        # Audit integration is owned by the coordinator. Exercise the real method,
        # without manufacturing audit records for an unadvertised tool.
        call = Workbench.inventory_page.__wrapped__
        with self.assertRaises(ValueError):
            call(bench, 'wrong')
        result = call(bench, 'Q1', page_size=1)
        self.assertEqual(result['progress']['question_id'], 'Q1')
        facts.write_text(facts.read_text() + ' ')
        with self.assertRaises(ValueError):
            call(bench, 'Q1', page_size=1, cursor=result['next_cursor'])


if __name__ == '__main__':
    unittest.main()
