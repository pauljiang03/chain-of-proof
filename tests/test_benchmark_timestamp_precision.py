"""Prospective scorer exact timestamp arithmetic; synthetic values only."""
import unittest

from eval.benchmark import Matcher, VERSION


class BenchmarkTimestampPrecision(unittest.TestCase):
    def matches(self, expected, actual, tolerance=0, zone=None, granularity='instant'):
        matcher = Matcher({'timestamps': {'': {'tolerance_seconds': tolerance,
                                               'granularity': granularity}}}, time_zone=zone)
        return all(event['status'] == 'match' for event in matcher.compare(expected, actual))

    def test_version_is_prospective(self):
        self.assertEqual(VERSION, '2.2')

    def test_100ns_neighbors_do_not_match(self):
        self.assertFalse(self.matches('2024-01-01T00:00:00.1234567Z', '2024-01-01T00:00:00.1234568Z'))
        self.assertFalse(self.matches('2024-01-01T00:00:00.0000001Z', '2024-01-01T00:00:00Z'))

    def test_arbitrary_precision_and_trailing_zero_equivalence(self):
        self.assertTrue(self.matches('2024-01-01T00:00:00.123456789012345678900Z',
                                     '2024-01-01T00:00:00.1234567890123456789+00:00'))
        self.assertFalse(self.matches('2024-01-01T00:00:00.123456789012345678901Z',
                                      '2024-01-01T00:00:00.123456789012345678902Z'))
        prefix = '2024-01-01T00:00:00.'
        self.assertTrue(self.matches(prefix + '1' * 256 + 'Z', prefix + '1' * 256 + '+00:00'))
        with self.assertRaisesRegex(ValueError, 'exceeds supported 256 digits'):
            self.matches(prefix + '1' * 257 + 'Z', prefix + '1' * 257 + 'Z')

    def test_offsets_rollovers_and_before_epoch(self):
        for expected, actual in [
                ('2024-01-01T00:00:00.1234567Z', '2023-12-31T19:00:00.1234567-05:00'),
                ('2023-12-31T18:15:00.123456789Z', '2024-01-01T00:00:00.123456789+05:45'),
                ('1969-12-31T23:59:59.9999999Z', '1970-01-01T00:59:59.9999999+01:00'),
                ('2024-01-01T00:00:00.1Z', '2024-01-01T00:00:30.1+00:00:30')]:
            self.assertTrue(self.matches(expected, actual))

    def test_exact_fractional_tolerance_boundaries(self):
        base = '2024-01-01T00:00:00Z'
        self.assertTrue(self.matches(base, '2024-01-01T00:00:00.0000001Z', 1e-7))
        self.assertFalse(self.matches(base, '2024-01-01T00:00:00.0000001000000001Z', 1e-7))
        self.assertTrue(self.matches(base, '2023-12-31T23:59:59.9Z', 0.1))
        self.assertFalse(self.matches(base, '2023-12-31T23:59:59.899999999999Z', 0.1))
        self.assertTrue(self.matches(base, '2024-01-01T00:00:02Z', 2))
        self.assertFalse(self.matches(base, '2024-01-01T00:00:02.0000000001Z', 2))

    def test_tolerance_validation_does_not_float_convert_large_integers(self):
        self.assertTrue(self.matches('2024-01-01T00:00:00Z', '2025-01-01T00:00:00Z', 10 ** 400))
        for invalid in (True, -1, float('inf'), float('nan')):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.matches('2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', invalid)

    def test_naive_zone_and_dst_controls(self):
        with self.assertRaisesRegex(ValueError, 'declared time_zone'):
            self.matches('2024-01-01T00:00:00.1234567', '2024-01-01T00:00:00.1234567Z')
        self.assertTrue(self.matches('2024-01-01T00:00:00.1234567',
                                     '2024-01-01T05:00:00.1234567Z', zone='America/New_York'))
        for stamp in ('2024-11-03T01:30:00.1234567', '2024-03-10T02:30:00.1234567'):
            with self.assertRaisesRegex(ValueError, 'ambiguous|nonexistent'):
                self.matches(stamp, '2024-01-01T00:00:00Z', zone='America/New_York')
        self.assertFalse(self.matches('2024-11-03T01:30:00-04:00', '2024-11-03T01:30:00-05:00'))

    def test_local_day_keeps_declared_zone_and_fine_precision(self):
        self.assertTrue(self.matches('2024-03-10', '2024-03-11T03:59:59.9999999999Z',
                                     zone='America/New_York', granularity='local_day'))
        self.assertFalse(self.matches('2024-03-10', '2024-03-11T04:00:00Z',
                                      zone='America/New_York', granularity='local_day'))
        self.assertFalse(self.matches('2024-03-10', '2024-03-11T04:00:00+00:00:00.0000001',
                                      zone='America/New_York', granularity='local_day'))

    def test_existing_standard_forms_and_decimal_comma(self):
        for stamp in ('2024-01-01 00:00:00Z', '2024-01-01T00:00Z', '2024-01-01T00Z',
                      '2024-01-01T05:30:00+0530', '2024-01-01T01:00:00+01'):
            self.assertTrue(self.matches('2024-01-01T00:00:00Z', stamp))
        self.assertTrue(self.matches('2024-01-01T00:00:00.1234567Z', '2024-01-01T00:00:00,1234567Z'))

    def test_unsupported_or_invalid_actual_never_silently_truncates(self):
        for actual in ('2024-01-01T00:00:00+00:00:00.1', '2024-01-01T00:00:00+00:00:00.00000001',
                       '2024-01-01T00:00:00+01:0203', '2024-01-01T00:00:00+0102:03',
                       '2024-01-01T00:00.1Z', '2024-01-01T00.1Z', '2024-01-01T00:00:00-00:00',
                       '2024-01-01T00:00:00+00:60', '2024-01-01T00:00:00+24:00',
                       '2024-01-01T00:00:60Z', '2024-02-30T00:00:00Z', None):
            with self.subTest(actual=actual):
                self.assertFalse(self.matches('2024-01-01T00:00:00Z', actual))
        with self.assertRaises(ValueError):
            self.matches('2024-01-01T00:00:00+00:00:00.1', '2024-01-01T00:00:00Z')


if __name__ == '__main__':
    unittest.main()
