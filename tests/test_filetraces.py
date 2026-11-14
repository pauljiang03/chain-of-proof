"""Parsing helpers of extractor/filetraces.py, on synthetic bytes (no image, no dissect)."""
import struct
import unittest
import uuid

from extractor import filetraces as ft


def item(body: bytes) -> bytes:
    """Prefix a shell item body with its size word."""
    return struct.pack("<H", len(body) + 2) + body


def folder_item(short: str, long_name: str, date=0x4678, time=0x9DF8) -> bytes:
    """A directory file entry (class 0x31) with a version-8 0xBEEF0004 extension block."""
    name = short.encode("ascii") + b"\x00"
    if len(name) % 2:
        name += b"\x00"
    ext_body = (struct.pack("<HI", 8, 0xBEEF0004) + struct.pack("<HHHH", date, time, date, time)
                + struct.pack("<HH", 0x2A, 0) + b"\x00" * 16 + struct.pack("<HI", 0, 0)
                + long_name.encode("utf-16-le") + b"\x00\x00")
    ext = struct.pack("<H", len(ext_body) + 2) + ext_body
    head = b"\x31\x00" + struct.pack("<IHHH", 0, date, time, 0x10) + name
    return item(head + ext + struct.pack("<H", 2 + len(head)))


def drive_item(letter: str) -> bytes:
    return item(b"\x2f" + (letter + ":\\").encode("ascii") + b"\x00" * 19)


def root_item(guid: str) -> bytes:
    return item(b"\x1f\x50" + uuid.UUID(guid).bytes_le)


class ShellItems(unittest.TestCase):
    def test_folder_entry_uses_long_name_and_dos_times(self):
        it = ft.parse_shell_item(folder_item("LONGFO~1", "Long folder name"))
        self.assertEqual((it["type"], it["name"], it["short_name"]),
                         ("folder", "Long folder name", "LONGFO~1"))
        self.assertEqual(it["item_modified"], "2015-03-24 19:47:48")
        self.assertEqual(it["item_created"], "2015-03-24 19:47:48")

    def test_drive_path_keeps_the_letter(self):
        buf = (root_item("20d04fe0-3aea-1069-a2d8-08002b30309d") + drive_item("E")
               + folder_item("DATA", "Data") + folder_item("SUB", "Sub") + b"\x00\x00")
        path, items = ft.idlist_path(buf)
        self.assertEqual(path, "E:\\Data\\Sub")
        self.assertEqual([i["type"] for i in items], ["root folder", "drive", "folder", "folder"])
        self.assertEqual(items[0]["name"], "My Computer")

    def test_network_share_starts_the_path(self):
        share = item(b"\xc3\x01\xc5" + b"\\\\server\\share\x00Microsoft Network\x00A comment\x00\x02\x00")
        it = ft.parse_shell_item(share)
        self.assertEqual((it["type"], it["name"]), ("network location", "\\\\server\\share"))
        self.assertEqual((it["description"], it["comment"]), ("Microsoft Network", "A comment"))
        self.assertEqual(ft.compose_path("Network\\server", it), "\\\\server\\share")
        self.assertEqual(ft.compose_path("\\\\server\\share", ft.parse_shell_item(folder_item("A", "A"))),
                         "\\\\server\\share\\A")

    def test_file_entry_under_the_root_is_on_the_desktop(self):
        self.assertEqual(ft.compose_path(None, ft.parse_shell_item(folder_item("X", "X"))), "Desktop\\X")
        root = ft.parse_shell_item(root_item("031e4825-7b94-4dc3-b131-e946b44c8dd5"))
        self.assertEqual(ft.compose_path(None, root), "Libraries")

    def test_known_folder_and_property_view_names(self):
        known = item(b"\x00\x00" + struct.pack("<HIHH", 0x1A, 0x23FEBBEE, 0, 16)
                     + uuid.UUID("374de290-123f-4565-9164-39c4925e467b").bytes_le + b"\x00" * 4)
        it = ft.parse_shell_item(known)
        self.assertEqual((it["type"], it["name"]), ("known folder", "Downloads"))
        self.assertEqual(ft.parse_shell_item(known, {it["guid"]: "Other name"})["name"], "Other name")

        text = "Change settings".encode("utf-16-le") + b"\x00\x00"
        value = struct.pack("<IB", 10, 0) + struct.pack("<HHI", 0x1F, 0, len(text) // 2) + text
        value = struct.pack("<I", len(value) + 4) + value
        store = b"1SPS" + uuid.UUID(ft.ITEM_NAME_DISPLAY[0]).bytes_le + value + b"\x00" * 4
        store = struct.pack("<I", len(store) + 4) + store
        view = item(b"\x00\x00" + struct.pack("<HIHH", 0, 0xBEEBEE00, len(store), 4) + b"\x01\x00\x00\x00"
                    + store + b"\x00" * 4)
        self.assertEqual(ft.property_strings(view), [(ft.ITEM_NAME_DISPLAY[0], 10, "Change settings")])
        self.assertEqual(ft.parse_shell_item(view)["name"], "Change settings")

    def test_zip_entry_and_unknown_item(self):
        body = bytearray(0x5A) + struct.pack("<II", 6, 4)       # body starts at item offset 2
        body[0x52:0x5A] = struct.pack("<II", 6, 4)
        raw = item(bytes(body[:0x5A]) + "slides".encode("utf-16-le") + b"\x00\x00"
                   + "ppt/".encode("utf-16-le") + b"\x00\x00" + b"\x00" * 6)
        it = ft.parse_shell_item(raw)
        self.assertEqual((it["type"], it["name"], it["path_in_zip"]), ("zip folder entry", "slides", "ppt/"))
        self.assertEqual(ft.parse_shell_item(item(b"\x99" + b"\x00" * 9))["type"], "unknown")

    def test_split_idlist_stops_at_terminator_and_bad_sizes(self):
        a, b = drive_item("C"), folder_item("A", "A")
        self.assertEqual(ft.split_idlist(a + b + b"\x00\x00" + b"junk"), [a, b])
        self.assertEqual(ft.split_idlist(b"\xff\xff\x00"), [])


class Lists(unittest.TestCase):
    def test_office_mru_entry(self):
        self.assertEqual(ft.parse_office_mru("[F00000000][T01D0670FD56809C0][O00000000]*C:\\a\\b.docx"),
                         (0x01D0670FD56809C0, "C:\\a\\b.docx"))
        self.assertIsNone(ft.parse_office_mru("C:\\a\\b.docx"))
        self.assertEqual(ft.us_from_filetime(0x01D0670FD56809C0), 1427297089628000)

    def test_mru_orders_and_recentdocs_name(self):
        self.assertEqual(ft.mru_order_ex(struct.pack("<IIII", 2, 0, 1, 0xFFFFFFFF) + b"\x09\x00\x00\x00"),
                         [2, 0, 1])
        self.assertEqual(ft.mru_order_ex(None), [])
        value = "report.docx".encode("utf-16-le") + b"\x00\x00" + b"\x14\x00binary shell item"
        self.assertEqual(ft.recentdocs_name(value), "report.docx")

    def test_mount_point_and_dos_time(self):
        self.assertEqual(ft.mountpoint_to_unc("##10.0.0.1#share"), "\\\\10.0.0.1\\share")
        self.assertIsNone(ft.mountpoint_to_unc("{c9a1c044-d2d7-11e4-9dae-806e6f6e6963}"))
        self.assertIsNone(ft.dos_datetime(0, 0))

    def test_search_index_dates_and_thumbnail_ids(self):
        raw = bytes.fromhex("01d0659e73748a80")
        self.assertEqual(ft.search_filetime(raw, True), 0x01D0659E73748A80)
        self.assertEqual(ft.search_filetime(raw[::-1], False), 0x01D0659E73748A80)
        self.assertIsNone(ft.search_filetime(bytes.fromhex("0000000000000001"), True))
        self.assertIsNone(ft.search_filetime(b"\x01\x02", True))
        self.assertEqual(ft.thumbcache_id(bytes.fromhex("c51aeed6ad002c07")), "072c00add6ee1ac5")


class Renames(unittest.TestCase):
    OLD, NEW, CLOSE = ft.USN_RENAME_OLD, ft.USN_RENAME_NEW, 0x80000000

    def test_pairs_old_and_new_name_records(self):
        f, d1, d2 = (100, 1), (5, 5), (60, 2)
        records = [
            (10, 1000, f, d1, "a.tmp", self.OLD),
            (20, 1001, f, d2, "b.doc", self.NEW),
            (30, 1002, f, d2, "b.doc", self.NEW | self.CLOSE),      # same rename, on close
            (40, 2000, f, d2, "b.doc", self.NEW | self.OLD),        # renamed again before a close
            (50, 2001, f, d2, "c.doc", self.NEW),
            (60, 3000, (200, 1), d1, "left.tmp", self.OLD),         # journal ends before the new name
        ]
        renames, unpaired = ft.pair_renames(records)
        self.assertEqual(unpaired, 1)
        self.assertEqual([(r["old_name"], r["new_name"], r["filetime"], r["new_usn"]) for r in renames],
                         [("a.tmp", "b.doc", 1001, 20), ("b.doc", "c.doc", 2001, 50)])
        self.assertEqual((renames[0]["old_parent"], renames[0]["new_parent"]), (d1, d2))

    def test_folder_name_at_a_journal_position(self):
        root = (5, 5)
        history = [(100, "New folder", root), (200, "temp", root), (300, "x7Qp", (60, 2))]
        self.assertEqual(ft.name_at(history, 50), ("New folder", root))     # before its first record
        self.assertEqual(ft.name_at(history, 200), ("temp", root))
        self.assertEqual(ft.name_at(history, 250), ("temp", root))
        self.assertEqual(ft.name_at(history, 999), ("x7Qp", (60, 2)))


if __name__ == "__main__":
    unittest.main()
