import struct
import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

from extractor import host_attributes, system
from extractor.host_attributes import build_number, iso_seconds, policy_unicode
from extractor.store import Evidence
from extractor.system import parse_sam_v


class HostDecoders(unittest.TestCase):
    def test_build_number_keeps_exact_decimal_meaning(self):
        class RegistryUint32(int):
            pass
        for value in ("7601", 7601, RegistryUint32(7601)):
            self.assertEqual(build_number(value), 7601)
        self.assertEqual(build_number("0"), 0)
        self.assertEqual(build_number("4294967295"), 4294967295)
        for invalid in (True, -1, "07601", "7601 ", " 7601", "+7601", "6.1.7601",
                        "7601.0", "", 7601.0, "4294967296", 2**32, "９９９", None):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                build_number(invalid)

    def test_os_fields_keep_one_scoped_subject_and_native_build_value(self):
        primary = system.Hive('SOFTWARE', None, r'C:\Windows\System32\config\SOFTWARE', False, None, None)
        backup = primary._replace(path=r'C:\Windows\System32\config\RegBack\SOFTWARE')
        fields = {'ProductName': 'Fixture OS', 'RegisteredOwner': 'Recorded owner',
                  'CurrentVersion': '6.1', 'CurrentBuildNumber': '7601',
                  'SystemRoot': r'C:\Windows', 'InstallDate': 1427245200}
        key = SimpleNamespace(values=lambda: [SimpleNamespace(name=k, value=v) for k, v in fields.items()])
        ev = Evidence()
        with patch.object(system, '_hives', return_value=[primary, backup]), \
                patch.object(system, '_open', side_effect=lambda ev, h, path:
                             key if path == r'Microsoft\Windows NT\CurrentVersion' else None):
            host_attributes.extract(ev, None, {'examined_at': 1800000000000000, 'common': {
                'image': 'fixture.E01', 'exhibit': 'OTHER-PC', 'source_snapshot': 'base-volume', 'source_variant': 'primary'}})
        self.assertEqual(ev.problems, [])
        subjects, values = set(), {}
        for kind, timestamp, _, _, value, raw in ev.rows():
            prov = json.loads(raw)
            self.assertEqual(timestamp, 1800000000000000)
            self.assertEqual(prov['source_hive'], primary.path)
            self.assertEqual(prov['source_variant'], 'primary')
            if kind == 'attributeSubject':
                subjects.add(value)
            if kind in ('attributeTextValue', 'attributeIntegerValue'):
                values[prov['attribute_role']] = json.loads(value)
                if prov['attribute_role'] == 'os.build_number':
                    self.assertEqual(prov['registry_native_value'], '7601')
        self.assertEqual(len(subjects), 1)
        self.assertEqual(values, {'os.product_name': 'Fixture OS', 'os.registered_owner': 'Recorded owner',
                                 'os.version': '6.1', 'os.build_number': 7601, 'os.system_root': r'C:\Windows',
                                 'os.install_time': '2015-03-25T01:00:00Z'})

    def test_native_registry_integer_subclass_is_accepted_but_boolean_is_not(self):
        class RegistryUint32(int):
            pass
        self.assertEqual(iso_seconds(RegistryUint32(1)), "1970-01-01T00:00:01Z")
        for invalid in (True, -1, "1", 1.5):
            with self.assertRaises(ValueError):
                iso_seconds(invalid)

    def test_domain_name_is_counted_unicode_not_dns_or_default_login_guess(self):
        data = "LAB".encode("utf-16-le")
        self.assertEqual(policy_unicode(struct.pack("<HHI", len(data), len(data) + 2, 8) + data + b"\0\0"), "LAB")
        for bad in (b"short", struct.pack("<HHI", 40, 40, 8) + data,
                    struct.pack("<HHI", 3, 4, 8) + data,
                    struct.pack("<HHI", 6, 2, 8) + data):
            with self.assertRaises(ValueError):
                policy_unicode(bad)

    def test_bad_sam_name_is_not_an_empty_certifiable_account(self):
        data = bytearray(204)
        struct.pack_into("<II", data, 12, 999999, 20)
        with self.assertRaises(ValueError):
            parse_sam_v(data)
        struct.pack_into("<II", data, 12, 0, 1)
        with self.assertRaises(ValueError):
            parse_sam_v(data + b"x")


if __name__ == "__main__":
    unittest.main()
