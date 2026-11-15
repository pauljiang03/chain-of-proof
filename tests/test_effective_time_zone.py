"""Recorded registry bias correspondence, never a live-clock or DST-date test."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from checker.catalog import decode_value
from extractor import host_attributes as host, system
from extractor.store import Evidence


def zone(**changes):
    values = {'Bias': 300, 'StandardBias': 0, 'DaylightBias': -60,
              'ActiveTimeBias': 300, 'StandardName': 'Example Standard',
              'DaylightName': 'Example Daylight', 'TimeZoneKeyName': 'Example Registry Key'}
    values.update(changes)
    return values


def typed(ev):
    return [(json.loads(row[-1])['attribute_role'], decode_value(row[4], 'string'), json.loads(row[-1]), row[1])
            for row in ev.rows() if row[0] == 'attributeTextValue']


class EffectiveTimeZone(unittest.TestCase):
    def test_standard_and_daylight_are_selected_by_stored_bias_only(self):
        text, provenance = host.effective_time_zone(zone())
        self.assertEqual(text, 'Example Standard (UTC-05:00)')
        self.assertEqual(provenance['matched_name_fields'], ['StandardName'])
        self.assertEqual(provenance['utc_offset_minutes'], -300)
        text, provenance = host.effective_time_zone(zone(ActiveTimeBias=240))
        self.assertEqual(text, 'Example Daylight (UTC-04:00)')
        self.assertEqual(provenance['matched_name_fields'], ['DaylightName'])
        self.assertEqual(provenance['standard_total_bias_minutes'], 300)
        self.assertEqual(provenance['daylight_total_bias_minutes'], 240)
        self.assertIn('no examination-date', provenance['limitation'])
        self.assertNotIn('dst_state', provenance)

    def test_signed_long_unsigned_dword_and_fractional_offsets(self):
        for encoded in (-345, (-345) & 0xffffffff):
            text, provenance = host.effective_time_zone(zone(Bias=encoded, ActiveTimeBias=encoded,
                                                             DaylightBias=(-60) & 0xffffffff))
            self.assertEqual(text, 'Example Standard (UTC+05:45)')
            self.assertEqual(provenance['decoded_bias_minutes']['Bias'], -345)
            self.assertEqual(provenance['time_zone_registry_inputs']['Bias'], encoded)
        self.assertEqual(host.effective_time_zone(zone(Bias=0, ActiveTimeBias=0))[0],
                         'Example Standard (UTC+00:00)')

    def test_nonzero_standard_adjustment_is_not_ignored(self):
        text, provenance = host.effective_time_zone(zone(Bias=330, StandardBias=15, ActiveTimeBias=345))
        self.assertEqual(text, 'Example Standard (UTC-05:45)')
        self.assertEqual(provenance['decoded_bias_minutes']['StandardBias'], 15)

    def test_actual_dissect_dword_subclasses_are_accepted(self):
        try:
            import struct
            from dissect.regf.regf import parse_value, REG_DWORD
        except ImportError:
            self.skipTest('optional Dissect registry decoder unavailable')
        value = parse_value(REG_DWORD, struct.pack('<I', (-345) & 0xffffffff))
        self.assertIsInstance(value, int)
        self.assertEqual(host.effective_time_zone(zone(Bias=value, ActiveTimeBias=value))[0],
                         'Example Standard (UTC+05:45)')

    def test_missing_malformed_and_out_of_range_bias_fields_refuse(self):
        for field in host.TIME_ZONE_FIELDS:
            values = zone()
            del values[field]
            with self.subTest(field=field, kind='missing'), self.assertRaisesRegex(ValueError, field):
                host.effective_time_zone(values)
            for invalid in (None, '300', 300.0, True, b'\x00\x00\x00\x00', 1 << 32, -(1 << 31) - 1):
                with self.subTest(field=field, invalid=invalid), self.assertRaisesRegex(ValueError, field):
                    host.effective_time_zone(zone(**{field: invalid}))
        with self.assertRaisesRegex(ValueError, 'supported UTC offset range'):
            host.effective_time_zone(zone(Bias=1440, ActiveTimeBias=1440))

    def test_mismatched_and_ambiguous_biases_do_not_choose_a_name(self):
        with self.assertRaisesRegex(ValueError, 'matches neither'):
            host.effective_time_zone(zone(ActiveTimeBias=270))
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            host.effective_time_zone(zone(DaylightBias=0))
        text, provenance = host.effective_time_zone(zone(DaylightBias=0, DaylightName='Example Standard'))
        self.assertEqual(text, 'Example Standard (UTC-05:00)')
        self.assertEqual(provenance['matched_name_fields'], ['StandardName', 'DaylightName'])
        self.assertIn('no physical-clock accuracy, actual DST-state', provenance['limitation'])

    def test_only_matching_literal_labels_are_used_and_never_resource_lookup(self):
        values = zone()
        del values['DaylightName']  # Its bias does not match, so its label is not an input.
        self.assertEqual(host.effective_time_zone(values)[0], 'Example Standard (UTC-05:00)')
        for invalid in (None, '', ' ', ' Example Standard', 'Example\nStandard', '@tzres.dll,-42', 7):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'StandardName'):
                host.effective_time_zone(zone(StandardName=invalid))
        values = zone(DaylightBias=0)
        del values['DaylightName']
        with self.assertRaisesRegex(ValueError, 'DaylightName'):
            host.effective_time_zone(values)

    def test_daylight_disable_flags_are_explicit_and_canonical(self):
        for field in host.TIME_ZONE_DISABLE_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(host.effective_time_zone(zone(**{field: 1}))[0],
                                 'Example Standard (UTC-05:00)')
                self.assertEqual(host.effective_time_zone(zone(ActiveTimeBias=240, **{field: 0}))[0],
                                 'Example Daylight (UTC-04:00)')
                with self.assertRaisesRegex(ValueError, 'daylight-only'):
                    host.effective_time_zone(zone(ActiveTimeBias=240, **{field: 1}))
                for invalid in (None, True, '1', 1.0, -1, 2, 0xffffffff):
                    with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'DWORD 0 or 1'):
                        host.effective_time_zone(zone(**{field: invalid}))
        with self.assertRaisesRegex(ValueError, 'settings differ'):
            host.effective_time_zone(zone(DynamicDaylightTimeDisabled=1, DisableAutoDaylightTimeSet=0))

    def test_dynamic_disable_does_not_resolve_equal_bias_different_name_ambiguity(self):
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            host.effective_time_zone(zone(DaylightBias=0, DynamicDaylightTimeDisabled=1))
        self.assertEqual(host.effective_time_zone(zone(DaylightBias=0, DaylightName='Example Standard',
                                                       DynamicDaylightTimeDisabled=1))[0],
                         'Example Standard (UTC-05:00)')

    def test_transition_dates_are_not_used_as_a_calendar_selector(self):
        ordinary = host.effective_time_zone(zone(ActiveTimeBias=240))[0]
        with_dates = zone(ActiveTimeBias=240, StandardStart=bytes(16), DaylightStart=bytes(16),
                          StandardDate='future', DaylightDate='past')
        self.assertEqual(host.effective_time_zone(with_dates)[0], ordinary)


class TimeZoneReader(unittest.TestCase):
    def run_reader(self, data, examined_at=1800000000000000, selector=2, snapshot='base-volume'):
        path = r'C:\Windows\System32\config\SYSTEM'
        root = SimpleNamespace(subkeys=lambda: [SimpleNamespace(name='ControlSet001'),
                                                SimpleNamespace(name='ControlSet002')])
        hive = system.Hive('SYSTEM', SimpleNamespace(root=lambda: root), path, False, None, None)
        backup = hive._replace(path=r'C:\Windows\System32\config\RegBack\SYSTEM', backup=True)
        def node(fields):
            return SimpleNamespace(values=lambda: [SimpleNamespace(name=name, value=value,
                type=4 if type(value) is int else 1) for name, value in fields.items()])
        keys = {'Select': node({} if selector is None else {'Current': selector}),
                r'ControlSet001\Control\TimeZoneInformation': node(zone(StandardName='Wrong control set')),
                r'ControlSet002\Control\TimeZoneInformation': node(data)}
        visited = []
        def open_key(ev, selected_hive, key):
            visited.append((selected_hive.path, key))
            return keys.get(key)
        ev = Evidence()
        with patch.object(system, '_hives', return_value=[hive, backup]), patch.object(system, '_open', side_effect=open_key):
            host.extract(ev, None, {'examined_at': examined_at, 'common': {
                'image': 'synthetic.E01', 'exhibit': 'OTHER-PC',
                'source_snapshot': snapshot, 'source_variant': 'primary'}})
        self.assertFalse(any(source == backup.path for source, _ in visited))
        return ev

    def test_reader_preserves_generic_setting_and_binds_every_input_locator(self):
        ev = self.run_reader(zone(ActiveTimeBias=240, DynamicDaylightTimeDisabled=0))
        self.assertEqual(ev.problems, [])
        rows = {role: (text, provenance, stamp) for role, text, provenance, stamp in typed(ev)}
        self.assertEqual(rows['os.time_zone_setting'][0], 'Example Registry Key')
        text, provenance, stamp = rows['os.effective_time_zone']
        self.assertEqual(text, 'Example Daylight (UTC-04:00)')
        self.assertEqual(stamp, 1800000000000000)
        self.assertEqual(provenance['current_control_set'], 'ControlSet002')
        self.assertEqual(provenance['source_snapshot'], 'base-volume')
        self.assertEqual(provenance['source_variant'], 'primary')
        self.assertTrue(provenance['control_set_selection_artifact'].endswith(r'Select value Current'))
        raw = provenance['time_zone_registry_inputs']
        locators = provenance['registry_input_locators']
        self.assertEqual(set(raw), set(locators))
        for name, locator in locators.items():
            self.assertEqual(locator['registry_value'], name)
            self.assertEqual(locator['registry_key'], r'ControlSet002\Control\TimeZoneInformation')
            self.assertEqual(locator['source_hive'], r'C:\Windows\System32\config\SYSTEM')
            self.assertTrue(locator['artifact'].endswith('value ' + name))

    def test_missing_or_ambiguous_effective_inputs_leave_generic_role_and_diagnostic(self):
        for data in (zone(DaylightBias=0), zone(ActiveTimeBias=None), zone(StandardName='@tzres.dll,-1')):
            ev = self.run_reader(data)
            self.assertEqual([role for role, *_ in typed(ev)], ['os.time_zone_setting'])
            self.assertTrue(any('effective recorded time zone' in error for error in ev.problems))

    def test_missing_selected_control_set_never_uses_first_fallback(self):
        ev = self.run_reader(zone(), selector=None)
        self.assertEqual(typed(ev), [])
        self.assertTrue(any('Select\\Current missing' in error for error in ev.problems))

    def test_examination_date_does_not_select_bias_and_snapshot_is_retained(self):
        values = []
        for stamp in (1704067200000000, 1719792000000000):  # January and July; only observation time changes.
            ev = self.run_reader(zone(ActiveTimeBias=240), examined_at=stamp,
                                 snapshot='vss:00000000-0000-0000-0000-000000000001')
            row = next(row for row in typed(ev) if row[0] == 'os.effective_time_zone')
            values.append(row[1])
            self.assertEqual(row[3], stamp)
            self.assertTrue(row[2]['source_snapshot'].startswith('vss:'))
        self.assertEqual(values, ['Example Daylight (UTC-04:00)'] * 2)


if __name__ == '__main__':
    unittest.main()
