"""Timestamp scoring on synthetic answer contracts, checked with independent integer ticks."""
from copy import deepcopy
from fractions import Fraction
import unittest

from eval.benchmark import score


def stamp(ticks):
    seconds, fraction = divmod(ticks, 10_000_000)
    # Small offsets from an arbitrary synthetic UTC epoch avoid datetime's
    # microsecond representation entirely when generating these test inputs.
    minute, second = divmod(seconds, 60)
    assert minute < 60
    return f'2001-02-03T04:{minute:02d}:{second:02d}.{fraction:07d}Z'


def measured(expected, actual, tolerance=0):
    reference = {'schema_version': 2, 'case_id': 'independent-precision', 'questions': [
        {'id': 'Q', 'prompt': 'Synthetic recorded instant?', 'expected': {'time': expected},
         'match': {'timestamps': {'/time': {'tolerance_seconds': tolerance, 'granularity': 'instant'}}}}]}
    submission = {'schema_version': 2, 'case_id': 'independent-precision', 'answers': [
        {'question_id': 'Q', 'status': 'answered', 'answer': {'time': actual}}]}
    before = deepcopy((reference, submission))
    result = score(reference, submission)
    assert (reference, submission) == before
    return result['atomic']['true_positive'] == 1


class IndependentTimestampPrecision(unittest.TestCase):
    def test_zero_tolerance_distinguishes_each_native_100ns_digit(self):
        for base in (0, 1, 9, 10, 1234560, 9999990, 9999999, 10_000_000):
            for difference in (1, 2, 7, 9):
                with self.subTest(base=base, difference=difference):
                    self.assertFalse(measured(stamp(base), stamp(base + difference)))

    def test_integer_oracle_checks_tolerance_in_both_directions(self):
        base = 1_234_560
        for tolerance in (0, 0.0000001, 0.0000002, 0.0000009, 0.000001):
            for delta in (-11, -10, -9, -2, -1, 0, 1, 2, 9, 10, 11):
                # The expected decision is exact rational arithmetic on native
                # ticks; no production timestamp parser supplies this oracle.
                expected = Fraction(abs(delta), 10_000_000) <= Fraction(str(tolerance))
                with self.subTest(tolerance=tolerance, delta=delta):
                    self.assertEqual(measured(stamp(base), stamp(base + delta), tolerance), expected)

    def test_exact_same_instant_survives_explicit_offset_and_precision_spelling(self):
        expected = '2001-02-03T04:00:00.1234567Z'
        for same in ('2001-02-03T04:00:00.1234567+00:00',
                     '2001-02-03T05:00:00.1234567+01:00',
                     '2001-02-02T23:00:00.1234567-05:00'):
            with self.subTest(same=same):
                self.assertTrue(measured(expected, same))
        self.assertTrue(measured('2001-02-03T04:00:00.1Z', '2001-02-03T04:00:00.1000000Z'))

    def test_same_whole_second_cannot_erase_native_fraction(self):
        for fraction in ('0000001', '1092164', '9999999'):
            with self.subTest(fraction=fraction):
                self.assertFalse(measured('2001-02-03T04:00:00.' + fraction + 'Z',
                                          '2001-02-03T04:00:00Z'))

    def test_one_microsecond_source_display_cannot_replace_a_more_precise_value(self):
        expected = '2001-02-03T04:00:00.1092164Z'
        for changed in ('2001-02-03T04:00:00.109216Z', '2001-02-03T04:00:00.109217Z'):
            with self.subTest(changed=changed):
                self.assertFalse(measured(expected, changed))

    def test_unordered_row_matching_preserves_native_timestamp_differences(self):
        expected = [{'name': 'same', 'time': stamp(1_234_560)},
                    {'name': 'same', 'time': stamp(1_234_567)}]
        actual = [{'name': 'same', 'time': stamp(1_234_567)},
                  {'name': 'same', 'time': stamp(1_234_561)}]
        reference = {'schema_version': 2, 'case_id': 'independent-rows', 'questions': [
            {'id': 'Q', 'prompt': 'Synthetic retained rows?', 'expected': expected,
             'match': {'list_order': 'unordered', 'timestamps': {'/*/time': {'tolerance_seconds': 0}}}}]}
        submission = {'schema_version': 2, 'case_id': 'independent-rows', 'answers': [
            {'question_id': 'Q', 'status': 'answered', 'answer': actual}]}
        result = score(reference, submission)
        self.assertEqual(result['atomic']['true_positive'], 3)
        self.assertEqual(result['atomic']['missing'], 1)
        self.assertEqual(result['atomic']['wrong'], 1)
        self.assertFalse(result['perfect_submission'])


if __name__ == '__main__':
    unittest.main()
