"""The fixed false-claim regression remains independent of answer benchmarks."""
import unittest
from pathlib import Path

from checker.facts import open_source
from eval.gate import load_fixture, measure


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'fixtures' / 'nist_false_claims.json'


class GateTest(unittest.TestCase):
    def test_all_twenty_four_false_probes_are_still_refused(self):
        result = measure(FIXTURE, open_source(ROOT / 'evidence' / 'case_facts.json'),
                         case_id='nist-cfreds-data-leakage')
        self.assertEqual(result['false_claims'], 24)
        self.assertEqual(result['false_claims_rejected'], 24)
        self.assertTrue(result['all_as_expected'], result)

    def test_no_fixture_is_not_measured_and_wrong_case_is_rejected(self):
        self.assertFalse(measure(None, None)['measured'])
        with self.assertRaisesRegex(ValueError, 'case_id'):
            load_fixture(FIXTURE, case_id='another-case')


if __name__ == '__main__':
    unittest.main()
