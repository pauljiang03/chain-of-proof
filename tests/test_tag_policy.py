"""Case policy must be explicit, shared and sufficient for a negative classification."""
import json
import unittest

from extractor.acquisition import fallback, provenance
from extractor.store import Evidence
from extractor.tags import add_tags, public_policy


def facts():
    ev = Evidence()
    ev.add("usbInsert", 1, 1, "ALLOWED-USB")
    ev.add("usbInsert", 2, 1, "OTHER-USB")
    unknown = fallback("rm1.E01", "Other case exhibit")
    ev.add("volumeOnDevice", 3, 1, unknown["device_identity"], "VOLUME", **provenance(unknown))
    ev.add("fileCreated", 4, 1, r"C:\secret project data\secret_project.txt", "VOLUME")
    ev.add("fileCreated", 5, 1, r"C:\public\report.txt", "VOLUME")
    return ev, unknown["device_identity"]


def tags(ev):
    return {(r[3], r[4]): json.loads(r[5]) for r in ev.rows() if r[0] == "tag"}


class TagPolicy(unittest.TestCase):
    def test_another_case_receives_no_builtin_authorization_or_confidential_tags(self):
        ev, _ = facts()
        self.assertEqual(add_tags(ev, 10), 0)
        self.assertEqual(tags(ev), {})

    def test_shared_explicit_policy_labels_known_serials_and_selected_path_marker(self):
        ev, unknown = facts()
        policy = {"source": "public case brief", "authorized_device_serials": ["ALLOWED-USB"],
                  "authorized_device_serials_complete": True, "confidential_path_markers": ["\\public\\"]}
        self.assertEqual(add_tags(ev, 10, policy=policy), 3)
        result = tags(ev)
        self.assertIn(("ALLOWED-USB", "authorized-device"), result)
        self.assertIn(("OTHER-USB", "unauthorized-device"), result)
        self.assertIn((r"C:\public\report.txt", "confidential"), result)
        self.assertFalse(any(obj == unknown for obj, _ in result))
        self.assertTrue(all(p["policy_source"] == "public case brief" for p in result.values()))

    def test_partial_allowlist_does_not_classify_unlisted_or_unknown_devices(self):
        ev, _ = facts()
        add_tags(ev, 10, policy={"authorized_device_serials": ["ALLOWED-USB"]})
        self.assertEqual(set(tags(ev)), {("ALLOWED-USB", "authorized-device")})

    def test_ambiguous_or_invalid_policy_fails_before_applying_tags(self):
        for policy in ({"authorized_device_serials": "SERIAL"}, {"confidential_path_markers": [""]},
                       {"authorized_device_serials_complete": True},
                       {"authorized_device_serials": [], "authorized_device_serials_complete": "true"},
                       {"answer_key": "not public policy"}):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                public_policy(policy)


if __name__ == "__main__":
    unittest.main()
