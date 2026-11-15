"""Boundary and counterexample controls for an opt-in recorded-time predicate."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest

from agent.timestamp_predicates import instant_ticks, local_day_interval, parse_interval, recorded_in_interval


ROLE = 'search.index.date_modified'


class TimestampPredicateTests(unittest.TestCase):
    def policy(self):
        return local_day_interval(first_day='2015-03-22', stop_day_exclusive='2015-03-24',
                                  zone_name='America/New_York', role=ROLE)

    def test_public_local_days_have_explicit_UTC_bounds(self):
        policy = self.policy()
        self.assertEqual((policy['start'], policy['stop']), ('2015-03-22T04:00:00Z', '2015-03-24T04:00:00Z'))
        for stamp, included in [
                ('2015-03-22T03:59:59.9999999Z', False),
                ('2015-03-22T04:00:00.0000000Z', True),
                ('2015-03-24T03:59:59.9999999Z', True),
                ('2015-03-24T04:00:00.0000000Z', False)]:
            self.assertEqual(recorded_in_interval(stamp, role=ROLE, policy=policy), included)

    def test_100ns_difference_at_each_boundary_is_not_truncated(self):
        policy = {'mode': 'recorded_instant_half_open_v1', 'role': ROLE,
                  'start': '2026-01-01T00:00:00.0000001Z', 'stop': '2026-01-01T00:00:00.0000002Z'}
        self.assertFalse(recorded_in_interval('2026-01-01T00:00:00Z', role=ROLE, policy=policy))
        self.assertTrue(recorded_in_interval(policy['start'], role=ROLE, policy=policy))
        self.assertFalse(recorded_in_interval(policy['stop'], role=ROLE, policy=policy))
        self.assertEqual(instant_ticks(policy['stop']) - instant_ticks(policy['start']), 1)

    def test_equivalent_offsets_and_fraction_lengths_have_identical_instants(self):
        stamps = ['2026-01-01T00:00:00.1Z', '2026-01-01T00:00:00.1000000+00:00',
                  '2025-12-31T19:00:00.1000000-05:00', '2026-01-01T05:30:00.1+05:30']
        self.assertEqual(len({instant_ticks(stamp) for stamp in stamps}), 1)

    def test_folded_local_time_requires_explicit_offset_and_can_reverse_order(self):
        first = instant_ticks('2026-11-01T01:30:00-04:00')
        second = instant_ticks('2026-11-01T01:30:00-05:00')
        boundary = instant_ticks('2026-11-01T06:00:00Z')
        self.assertLess(first, boundary)
        self.assertGreater(second, boundary)
        with self.assertRaises(ValueError):
            instant_ticks('2026-11-01T01:30:00')

    def test_local_day_policy_handles_DST_day_lengths(self):
        for start, stop, hours in [('2026-03-08', '2026-03-09', 23), ('2026-11-01', '2026-11-02', 25)]:
            policy = local_day_interval(first_day=start, stop_day_exclusive=stop,
                                       zone_name='America/New_York', role=ROLE)
            self.assertEqual(instant_ticks(policy['stop']) - instant_ticks(policy['start']), hours * 3600 * 10_000_000)

    def test_invalid_or_unknown_timestamps_fail_closed(self):
        for stamp in [None, 0, True, '2026-01-01', '2026-01-01 00:00:00Z',
                      '2026-01-01T00:00:00', '2026-01-01T00:00:00-00:00',
                      '2026-01-01T00:00:00.12345678Z', '2026-02-29T00:00:00Z',
                      '2026-01-01T24:00:00Z', '2026-01-01T00:00:60Z',
                      '2026-01-01T00:00:00+24:00', '2026-01-01T00:00:00+01:60',
                      '0001-01-01T00:00:00+01:00', '9999-12-31T23:59:59-01:00']:
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                recorded_in_interval(stamp, role=ROLE, policy=self.policy())

    def test_wrong_role_bounds_policy_and_zone_fail_closed(self):
        policy = self.policy()
        with self.assertRaisesRegex(ValueError, 'timestamp_role_mismatch'):
            recorded_in_interval(policy['start'], role='file.creation_time', policy=policy)
        for bad in [dict(policy, role='search.index.date_created'), dict(policy, stop=policy['start']),
                    dict(policy, start=policy['stop']), dict(policy, extra=True), dict(policy, mode='inclusive')]:
            with self.assertRaises(ValueError):
                parse_interval(bad)
        for zone in [None, '', 'Not/A_Zone', '/etc/passwd', '../UTC']:
            with self.assertRaises(ValueError):
                local_day_interval(first_day='2015-03-22', stop_day_exclusive='2015-03-24', zone_name=zone, role=ROLE)

    def test_ambiguous_or_nonexistent_midnight_is_refused(self):
        for zone, first, stop in [('America/Havana', '2020-11-01', '2020-11-02'),
                                   ('Pacific/Apia', '2011-12-30', '2011-12-31')]:
            with self.assertRaisesRegex(ValueError, 'ambiguous_or_nonexistent'):
                local_day_interval(first_day=first, stop_day_exclusive=stop, zone_name=zone, role=ROLE)

    def test_integer_parser_matches_independent_datetime_controls(self):
        # Whole-second controls use datetime's independent calendar conversion;
        # fine-grained precision controls above do not use datetime microseconds.
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        for year in (1900, 1969, 1970, 2000, 2026):
            for minutes in (-720, -330, 0, 345, 840):
                stamp = datetime(year, 3, 1, 12, 34, 56, tzinfo=timezone(timedelta(minutes=minutes)))
                difference = stamp.astimezone(timezone.utc) - epoch
                expected = (difference.days * 86400 + difference.seconds) * 10_000_000
                self.assertEqual(instant_ticks(stamp.isoformat()), expected)

    def test_policy_and_literal_values_are_not_mutated(self):
        policy = self.policy()
        before = deepcopy(policy)
        value = '2015-03-22T00:00:00.0000001-04:00'
        self.assertTrue(recorded_in_interval(value, role=ROLE, policy=policy))
        self.assertEqual(policy, before)
        self.assertEqual(value, '2015-03-22T00:00:00.0000001-04:00')


if __name__ == '__main__':
    unittest.main()
