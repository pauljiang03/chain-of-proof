"""Large complete censuses still need kernel proofs and exact source binding."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from checker import check as checker, claims
from checker.facts import Fact, FactSource
from verifier.verify import verify


class Source(FactSource):
    def __init__(self, size, *, distinct=31):
        self.rows = [Fact(i, 'webVisit', 1_800_000_000_000_000 + i, 1, (i - 1) % distinct + 1, i % 2,
                          {'image': 'synthetic-only', 'artifact': f'History row {i}', 'time_meaning': 'synthetic visit'})
                     for i in range(1, size + 1)]
        # A different kind is not part of a webVisit census.
        self.rows.append(Fact(size + 1, 'usbInsert', 10, 1, 1, 0, {'image': 'synthetic-only'}))

    def all(self):
        return list(self.rows)

    def get(self, ids):
        wanted = set(ids)
        return {row.id: row for row in self.rows if row.id in wanted}

    def string(self, sid):
        return f'synthetic entity {sid}'


class CensusScaling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.sources, cls.certificates = {}, {}
        for size in (518, 747, 1025, claims.MAX_CENSUS):
            source = Source(size)
            result = checker.check({'exactly': ['webVisit', size]}, f'C{size}', source, out_dir=cls.folder.name)
            if result['status'] != 'verified':
                raise AssertionError(result)
            cls.sources[size], cls.certificates[size] = source, result

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_representative_and_over_one_thousand_counts_are_kernel_verified_and_complete(self):
        self.assertGreater(claims.MAX_CENSUS, 1000)
        for size, cert in self.certificates.items():
            with self.subTest(size=size):
                self.assertEqual(cert['axioms'], [])
                self.assertEqual(cert['trust_tier'], 'kernel')
                self.assertEqual(len(cert['cited_facts']), size)
                self.assertEqual({row['id'] for row in cert['cited_facts']}, set(range(1, size + 1)))
                self.assertEqual(verify(cert, self.sources[size]), [])
                proof = (Path(self.folder.name) / cert['lean_file']).read_text()
                self.assertIn('List.flatten', proof)
                self.assertIn('counts cited census = true := by decide +kernel', proof)
                self.assertNotIn('native_decide', proof)
                self.assertIn(f'maxHeartbeats {checker.CENSUS_MAX_HEARTBEATS}', proof)
                self.assertIn('is not counted', cert['english'])

    def test_distinct_and_filtered_forms_above_one_thousand_use_real_kernel(self):
        source = self.sources[1025]
        for name, args in [('exactlyDistinct', ['webVisit', 'obj', 31]),
                           ('exactlyWith', ['webVisit', 'aux', 1, 513])]:
            with self.subTest(name=name):
                cert = checker.check({name: args}, name, source, out_dir=self.folder.name)
                self.assertEqual(cert['status'], 'verified', cert)
                self.assertEqual(cert['axioms'], [])
                self.assertEqual(len(cert['cited_facts']), 1025)
                self.assertEqual(verify(cert, source), [])

    def test_off_by_one_count_is_refused_by_real_kernel(self):
        result = checker.check({'exactly': ['webVisit', 748]}, 'Wrong747', self.sources[747], out_dir=self.folder.name)
        self.assertEqual(result['status'], 'rejected')
        self.assertIn('holds 747, not 748', result['parts'][0]['bricks'][0])
        self.assertFalse((Path(self.folder.name) / 'Wrong747.json').exists())

    def test_omitted_duplicate_copied_rows_and_tampering_fail_independent_verification(self):
        original, source = self.certificates[747], self.sources[747]
        for mutate, expected in (
            (lambda cert: cert['cited_facts'].pop(), 'differ'),
            (lambda cert: cert['cited_facts'].append(deepcopy(cert['cited_facts'][0])), 'duplicate'),
            (lambda cert: cert['cited_facts'][0].update(t=1234), 'copied fields differ'),
            (lambda cert: cert['cited_facts'][0].update(row_sha256='0' * 64), 'no longer matches')):
            with self.subTest(expected=expected):
                cert = deepcopy(original)
                mutate(cert)
                with patch('verifier.verify.run_kernel') as kernel:
                    problems = verify(cert, source)
                kernel.assert_not_called()
                self.assertTrue(any(expected in problem for problem in problems), problems)
        grown = Source(748)
        self.assertTrue(any('differ' in problem for problem in verify(original, grown)))

    def test_duplicate_source_ids_are_refused_before_kernel_or_dict_collapse(self):
        source = Source(518)
        source.rows.append(source.rows[0])
        with patch.object(checker, 'run_kernel') as kernel:
            result = checker.check({'exactly': ['webVisit', 519]}, 'DuplicateSource', source, out_dir=self.folder.name)
        self.assertEqual(result['status'], 'rejected')
        self.assertIn('unique source fact IDs', result['reason'])
        kernel.assert_not_called()

    def test_above_capacity_is_explicit_not_a_partial_census(self):
        source = Source(claims.MAX_CENSUS + 1)
        with patch.object(checker, 'run_kernel') as kernel:
            result = checker.check({'exactly': ['webVisit', claims.MAX_CENSUS + 1]}, 'TooLarge', source, out_dir=self.folder.name)
        kernel.assert_not_called()
        self.assertEqual(result['status'], 'rejected')
        self.assertIn(f'a census can cover at most {claims.MAX_CENSUS}', result['reason'])
        self.assertEqual(result['proof_gap']['requirements'][0]['category'], 'execution_or_unclassified')
        self.assertNotIn('cited_facts', result)

    def test_resource_failures_do_not_claim_that_a_correct_count_is_wrong(self):
        source = self.sources[518]
        failures = [subprocess.TimeoutExpired('lean', 120),
                    {'ok': False, 'output': 'maximum recursion depth has been reached'}]
        for index, failure in enumerate(failures):
            kwargs = {'side_effect': failure} if isinstance(failure, Exception) else {'return_value': failure}
            with self.subTest(index=index), patch.object(checker, 'run_kernel', **kwargs):
                result = checker.check({'exactly': ['webVisit', 518]}, f'Resource{index}', source, out_dir=self.folder.name)
            self.assertEqual(result['status'], 'rejected')
            self.assertIn('no certificate was issued', result['reason'])
            self.assertEqual(result['parts'], [])
            self.assertNotIn('holds 518, not 518', json.dumps(result))
            self.assertFalse((Path(self.folder.name) / f'Resource{index}.json').exists())


if __name__ == '__main__':
    unittest.main()
