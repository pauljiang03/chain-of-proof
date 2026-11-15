"""Report display preserves the source instant and exact decimal precision."""
import unittest

from agent.answer_representation import render_timestamp


class AnswerRepresentation(unittest.TestCase):
    def test_explicit_report_display_roundtrip(self):
        source = '2004-08-27 15:46:33.109216Z'
        result = render_timestamp(source, 'America/Chicago')
        self.assertEqual(result.display_timestamp, '2004-08-27T10:46:33.109216-05:00')
        self.assertEqual(result.source_timestamp, source)
        self.assertEqual(result.interpretation, 'report_display_only')
        self.assertEqual(render_timestamp(result.display_timestamp, 'UTC').display_timestamp,
                         '2004-08-27T15:46:33.109216+00:00')

    def test_fraction_precision_is_exact(self):
        for fraction in ('', '.0', '.0000000', '.1234567', '.123456789012345678900'):
            with self.subTest(fraction=fraction):
                result = render_timestamp('2024-01-01T00:00:00' + fraction + '+05:45', 'UTC')
                self.assertEqual(result.source_utc, '2023-12-31T18:15:00' + fraction + 'Z')
                self.assertEqual(result.display_timestamp, '2023-12-31T18:15:00' + fraction + '+00:00')
                self.assertEqual(result.fraction_digits, len(fraction[1:]))

    def test_dst_spring_transition(self):
        self.assertEqual(render_timestamp('2024-03-10T06:59:59Z', 'America/New_York').display_timestamp,
                         '2024-03-10T01:59:59-05:00')
        self.assertEqual(render_timestamp('2024-03-10T07:00:00Z', 'America/New_York').display_timestamp,
                         '2024-03-10T03:00:00-04:00')

    def test_fold_instants_remain_distinct(self):
        first = render_timestamp('2024-11-03T05:30:00.1234567Z', 'America/New_York')
        second = render_timestamp('2024-11-03T06:30:00.1234567Z', 'America/New_York')
        self.assertEqual(first.display_timestamp, '2024-11-03T01:30:00.1234567-04:00')
        self.assertEqual(second.display_timestamp, '2024-11-03T01:30:00.1234567-05:00')
        for result in (first, second):
            self.assertEqual(render_timestamp(result.display_timestamp, 'UTC').source_utc, result.source_utc)

    def test_invalid_offsets_and_naive_inputs_fail(self):
        for value in ('2024-01-01T00:00:00', '2024-01-01', '2024-01-01T00:00:00-00:00',
                      '2024-01-01T00:00:00+24:00', '2024-01-01T00:00:00+01:60',
                      '2024-01-01T00:00:00+0500', '2024-01-01T00:00:60Z',
                      '2024-02-30T00:00:00Z', '2024-01-01T00:00:00.Z', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_timestamp(value, 'UTC')

    def test_zone_is_explicit_not_inferred_from_label(self):
        for zone in ('', None, 'Central Daylight Time (UTC-05:00)', '../UTC', 'Invalid/Zone'):
            with self.subTest(zone=zone), self.assertRaises(ValueError):
                render_timestamp('2024-01-01T00:00:00Z', zone)

    def test_numeric_offset_is_source_evidence_not_a_machine_zone_assertion(self):
        # An offset can differ from the chosen report zone; it defines the source
        # instant and is never replaced by guessing a machine's intended zone.
        result = render_timestamp('2024-01-01T12:00:00+09:00', 'America/New_York')
        self.assertEqual(result.source_utc, '2024-01-01T03:00:00Z')
        self.assertEqual(result.display_timestamp, '2023-12-31T22:00:00-05:00')


if __name__ == '__main__':
    unittest.main()
