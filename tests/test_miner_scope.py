"""Local shortcut filtering follows image scope, not a hardcoded PC exhibit label."""
import unittest

from checker import claims
from checker.facts import Fact
from miner.mine import candidates


class Source:
    def __init__(self, facts):
        self.facts = facts

    def all(self):
        return self.facts

    def string(self, sid):
        return str(sid)


class MinerScope(unittest.TestCase):
    def opened(self, local_prov, shortcut_prov):
        rows = [Fact(1, "fileModified", 10, 1, 100, 42, local_prov),
                Fact(2, "lnkTarget", 20, 1, 200, 42, shortcut_prov)]
        return [claims.to_json(part) for _, candidate in candidates(Source(rows))
                for part in claims.parts(claims.parse(candidate)) if part[0] == "opened"]

    def test_custom_exhibit_local_volume_is_filtered(self):
        scope = {"image": "workstation.E01", "exhibit": "DESKTOP"}
        self.assertEqual(self.opened(scope, scope), [])

    def test_equal_volume_values_in_other_images_are_not_assumed_local(self):
        self.assertEqual(self.opened({"image": "first.E01", "exhibit": "PC"},
                                     {"image": "second.E01", "exhibit": "PC"}), [{"opened": [2]}])

    def test_missing_image_scope_does_not_suppress_a_candidate(self):
        self.assertEqual(self.opened({"exhibit": "PC"}, {"exhibit": "PC"}), [{"opened": [2]}])


if __name__ == "__main__":
    unittest.main()
