import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from extractor.profiles import user_profiles, ntfs_volume_serial


class ProfileLayouts(unittest.TestCase):
    def test_legacy_and_modern_profiles_on_multiple_drives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "C:/Documents and Settings/Analyst").mkdir(parents=True)
            (root / "D:/Users/Second").mkdir(parents=True)
            target = SimpleNamespace(fs=SimpleNamespace(
                mounts={"c:": SimpleNamespace(ntfs=SimpleNamespace(serial=1)),
                        "d:": SimpleNamespace(ntfs=SimpleNamespace(serial=2))},
                path=lambda value: root / value))
            self.assertEqual([path.name for path in user_profiles(target)], ["Analyst", "Second"])
            self.assertEqual(ntfs_volume_serial(target, "d:/Users/Second"), "00000002")
            self.assertEqual(ntfs_volume_serial(target, "/c:/Documents and Settings/Analyst"), "00000001")

    def test_absent_layout_and_symlink_profile_do_not_fail_or_duplicate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "C:/Documents and Settings"
            (folder / "Analyst").mkdir(parents=True)
            (folder / "Alias").symlink_to(folder / "Analyst", target_is_directory=True)
            target = SimpleNamespace(fs=SimpleNamespace(mounts={"c:": None}, path=lambda value: root / value))
            self.assertEqual([path.name for path in user_profiles(target)], ["Analyst"])


if __name__ == "__main__":
    unittest.main()
