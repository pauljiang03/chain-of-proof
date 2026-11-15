import struct
import unittest

from extractor.host_attributes import iso_seconds, policy_unicode
from extractor.system import parse_sam_v


class HostDecoders(unittest.TestCase):
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
