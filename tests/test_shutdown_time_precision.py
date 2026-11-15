"""Native shutdown FILETIME precision and type survive source extraction."""
import json
import struct
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from extractor import host_attributes, system
from extractor.store import Evidence


class ShutdownTimePrecision(unittest.TestCase):
    def extract(self, entries):
        hive = system.Hive('SYSTEM', None, r'C:\Windows\System32\config\SYSTEM', False, None, None)
        path = r'ControlSet001\Control\Windows'
        ev = Evidence()
        with patch.object(system, '_hives', return_value=[hive]), \
                patch.object(system, '_control_sets', return_value=('ControlSet001', ['ControlSet001'])), \
                patch.object(system, '_open', side_effect=lambda ev, h, key:
                    NS(values=lambda: entries) if key == path else None):
            host_attributes.extract(ev, None, {'examined_at': 100, 'common': {
                'image': 'synthetic.E01', 'exhibit': 'PC', 'source_snapshot': 'base-volume',
                'source_variant': 'primary'}})
        rows = [(kind, stamp, json.loads(value), json.loads(prov))
                for kind, stamp, _, _, value, prov in ev.rows()
                if kind == 'attributeTextValue' and json.loads(prov).get('attribute_role') == 'machine.last_shutdown']
        return rows, ev

    def test_exact_native_hundred_nanosecond_digits_survive(self):
        for digit in range(10):
            raw = struct.pack('<Q', 127380951931092160 + digit)
            expected = f'2004-08-27T15:46:33.109216{digit}Z'
            self.assertEqual(host_attributes.shutdown_filetime_iso(raw), expected)
            rows, _ = self.extract([NS(name='ShutdownTime', value=raw, type=3)])
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1:3], (100, expected))
            self.assertEqual(rows[0][3]['native_filetime_le_hex'], raw.hex())
            self.assertEqual(rows[0][3]['native_filetime_ticks'], 127380951931092160 + digit)
            self.assertEqual(rows[0][3]['value_resolution'], '100ns')

    def test_wrong_types_missing_type_and_duplicate_names_emit_no_timestamp(self):
        raw = struct.pack('<Q', 127380951931092164)
        cases = [[NS(name='ShutdownTime', value=raw, type=kind)] for kind in (0, 4, 5, 11, '3')]
        cases += [[NS(name='ShutdownTime', value=raw)],
                  [NS(name='ShutdownTime', value=raw, type=3), NS(name='shutdowntime', value=raw, type=3)]]
        for entries in cases:
            with self.subTest(entries=entries):
                rows, ev = self.extract(entries)
                self.assertEqual(rows, [])
                self.assertTrue(ev.problems)

    def test_malformed_unset_pre_epoch_and_sentinel_values_are_refused(self):
        values = [b'', b'1234567', b'123456789', bytearray(8), 127380951931092164,
                  struct.pack('<Q', 0), struct.pack('<Q', 116444735999999999),
                  struct.pack('<Q', 2**63 - 1)]
        for raw in values:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                host_attributes.shutdown_filetime_iso(raw)
            rows, ev = self.extract([NS(name='ShutdownTime', value=raw, type=3)])
            self.assertEqual(rows, [])
            self.assertTrue(ev.problems)

    def test_epoch_second_rollover_and_native_case_are_preserved(self):
        self.assertEqual(host_attributes.shutdown_filetime_iso(struct.pack('<Q', 116444736000000000)),
                         '1970-01-01T00:00:00.0000000Z')
        self.assertEqual(host_attributes.shutdown_filetime_iso(struct.pack('<Q', 116445600000000000)),
                         '1970-01-02T00:00:00.0000000Z')
        rows, _ = self.extract([NS(name='shutdowntime', value=bytes.fromhex('c4fc00074d8cc401'), type=3)])
        self.assertEqual(rows[0][2], '2004-08-27T15:46:33.1092164Z')
        self.assertEqual(rows[0][3]['registry_value'], 'shutdowntime')


if __name__ == '__main__':
    unittest.main()
