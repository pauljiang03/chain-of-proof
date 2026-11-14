"""Decoders of extractor/system.py, on synthetic bytes. No disk image and no dissect needed."""
import struct
import unittest
from datetime import datetime, timezone

from extractor import system as s

FT_2015_03_25 = 130717152000000000          # FILETIME of 2015-03-25 00:00:00 UTC
US_2015_03_25 = 1427241600000000


def u16(text):
    return text.encode("utf-16-le")


class Times(unittest.TestCase):
    def test_filetime(self):
        self.assertEqual(s.filetime_us(FT_2015_03_25), US_2015_03_25)
        self.assertEqual(s.filetime_us(FT_2015_03_25 + 15), US_2015_03_25 + 1)   # 100 ns units, floored
        self.assertIsNone(s.filetime_us(0))                                      # unset
        self.assertIsNone(s.filetime_us(0x7FFFFFFFFFFFFFFF))                     # "never"
        self.assertIsNone(s.filetime_us(10_000_000))                             # year 1601: before 1970
        self.assertEqual(s.iso(US_2015_03_25 + 1), "2015-03-25 00:00:00.000001Z")

    def test_systemtime_is_local_and_converted_with_the_zone(self):
        raw = struct.pack("<8H", 2015, 3, 3, 25, 11, 16, 0, 336)
        naive = s.systemtime(raw)
        self.assertEqual(naive, datetime(2015, 3, 25, 11, 16, 0, 336000))
        self.assertIsNone(s.systemtime(bytes(16)))
        utc = datetime(2015, 3, 25, 15, 16, 0, 336000, tzinfo=timezone.utc)       # daylight time: UTC-4
        self.assertEqual(s.local_us(naive, "America/New_York"), s.us(utc))
        winter = datetime(2015, 1, 5, 9, 0, 0, tzinfo=timezone.utc)               # standard time: UTC-5
        self.assertEqual(s.local_us(datetime(2015, 1, 5, 4, 0, 0), "America/New_York"), s.us(winter))

    def test_install_date(self):
        self.assertEqual(s.parse_install_date("20150322"), datetime(2015, 3, 22))
        self.assertEqual(s.parse_install_date(20150322), datetime(2015, 3, 22))
        for bad in ("2015", "20151340", "", None, b"20150322", 1427034866):
            self.assertIsNone(s.parse_install_date(bad))


class Accounts(unittest.TestCase):
    def test_sam_f(self):
        raw = (bytes(8) + struct.pack("<5Q", FT_2015_03_25, 0, FT_2015_03_25 + 10, 0x7FFFFFFFFFFFFFFF, 0)
               + struct.pack("<3I", 1000, 513, 0x0214) + struct.pack("<4H", 0, 0, 2, 10))
        f = s.parse_sam_f(raw)
        self.assertEqual((f["rid"], f["logon_count"], f["failed_logons"]), (1000, 10, 2))
        self.assertEqual(f["last_logon"], US_2015_03_25)
        self.assertEqual(f["password_last_set"], US_2015_03_25 + 1)
        self.assertIsNone(f["account_expires"])
        self.assertIsNone(f["last_failed_logon"])
        self.assertEqual(s.acb_flags(f["flags"]),
                         ["password not required", "normal user account", "password does not expire"])
        with self.assertRaises(ValueError):
            s.parse_sam_f(raw[:40])

    def test_sam_v(self):
        head = bytearray(0xCC)
        struct.pack_into("<2I", head, 0x0C, 0, 6)           # user name
        struct.pack_into("<2I", head, 0x18, 8, 10)          # full name
        v = s.parse_sam_v(bytes(head) + u16("bob") + b"\x00\x00" + u16("Bob B"))
        self.assertEqual((v["name"], v["full_name"], v["comment"]), ("bob", "Bob B", ""))

    def test_sid_and_group_members(self):
        sid = bytes([1, 5]) + (5).to_bytes(6, "big") + struct.pack("<5I", 21, 1, 2, 3, 1000)
        self.assertEqual(s.sid_text(sid), "S-1-5-21-1-2-3-1000")
        head = bytearray(0x34)
        struct.pack_into("<2I", head, 0x10, 0, 10)
        struct.pack_into("<3I", head, 0x28, 12, len(sid), 1)
        name, members = s.parse_alias_c(bytes(head) + u16("Users") + b"\x00\x00" + sid)
        self.assertEqual((name, members), ("Users", ["S-1-5-21-1-2-3-1000"]))


class ProgramsRun(unittest.TestCase):
    def test_userassist(self):
        raw = struct.pack("<4I", 0, 3, 5, 1234) + bytes(44) + struct.pack("<Q", FT_2015_03_25) + bytes(4)
        self.assertEqual(s.parse_userassist(raw), {"run_count": 3, "focus_count": 5, "focus_time_ms": 1234,
                                                   "last_run": US_2015_03_25})
        never = struct.pack("<4I", 0, 0, 9, 50) + bytes(56)
        self.assertIsNone(s.parse_userassist(never)["last_run"])
        xp = s.parse_userassist(struct.pack("<IIQ", 1, 7, FT_2015_03_25))      # XP counts start at 5
        self.assertEqual((xp["run_count"], xp["last_run"]), (2, US_2015_03_25))
        self.assertIsNone(s.parse_userassist(b"\x00" * 9))
        self.assertIsNone(s.userassist_path("UEME_CTLSESSION"))
        self.assertEqual(s.userassist_path("UEME_RUNPATH:C:\\a\\b.exe"), "C:\\a\\b.exe")
        self.assertEqual(s.exe_name("{GUID}\\Folder\\App.exe"), "App.exe")
        self.assertEqual(s.exe_name('"C:\\Program Files\\x y.exe"'), "x y.exe")

    def prefetch(self, name, path_hash, files, last_run=FT_2015_03_25, runs=4):
        strings = u16("\x00".join(files) + "\x00")
        raw = bytearray(0x100) + strings
        struct.pack_into("<I", raw, 0, 23)
        raw[4:8] = b"SCCA"
        raw[16:16 + 2 * len(name)] = u16(name)
        struct.pack_into("<I", raw, 76, path_hash)
        struct.pack_into("<2I", raw, 0x64, 0x100, len(strings))
        struct.pack_into("<Q", raw, 0x80, last_run)
        struct.pack_into("<I", raw, 0x98, runs)
        return bytes(raw)

    def test_prefetch_hash(self):
        # h = h * 37 + byte, from 314159: (314159 * 37 + 0x41) * 37 + 0x00, worked by hand
        self.assertEqual(s.scca_hash_vista("A"), 430086076)
        self.assertEqual(s.scca_hash_2008("A"), 430086076)
        # the Windows 7 routine is the same sum unrolled eight bytes at a time
        # (442596621 = 37**7 and -803794207 = 37**8, modulo 2**32), so the two must agree
        self.assertEqual(pow(37, 7, 1 << 32), 442596621)
        self.assertEqual(pow(37, 8, 1 << 32), (1 << 32) - 803794207)
        long = "\\DEVICE\\HARDDISKVOLUME1\\DIR\\APP.EXE"
        self.assertEqual(s.scca_hash_2008(long), s.scca_hash_vista(long))
        self.assertNotEqual(s.scca_hash_xp(long), s.scca_hash_vista(long))

    def test_prefetch(self):
        good, other = "\\DEVICE\\HARDDISKVOLUME1\\DIR\\APP.EXE", "\\DEVICE\\HARDDISKVOLUME1\\OLD\\APP.EXE"
        dll = "\\DEVICE\\HARDDISKVOLUME1\\WINDOWS\\SYSTEM32\\NTDLL.DLL"
        pf = s.parse_prefetch(self.prefetch("APP.EXE", s.scca_hash_2008(good), [dll, other, good]))
        self.assertEqual((pf["version"], pf["name"], pf["run_count"]), (23, "APP.EXE", 4))
        self.assertEqual(pf["run_times"], [US_2015_03_25])
        self.assertEqual(pf["files"], [dll, other, good])
        self.assertEqual(s.prefetch_path(pf)[0], good)                 # picked by hash, not by order
        pf = s.parse_prefetch(self.prefetch("APP.EXE", 1, [dll, other, good]))
        self.assertEqual(s.prefetch_path(pf)[0], "")                   # two candidates, no hash match: no guess
        pf = s.parse_prefetch(self.prefetch("APP.EXE", 1, [dll, good]))
        self.assertEqual(s.prefetch_path(pf)[0], good)
        self.assertEqual(s.parse_prefetch(self.prefetch("APP.EXE", 1, [], last_run=0))["run_times"], [])
        with self.assertRaises(ValueError):
            s.parse_prefetch(b"MAM\x04" + bytes(0x200))

    def shimcache(self, wide):
        paths = ["\\??\\C:\\Windows\\a.exe", "\\??\\C:\\Temp\\b c.exe"]
        size = 48 if wide else 32
        table, blob, at = b"", b"", 0x80 + size * len(paths)
        for path, flags in zip(paths, (2, 0)):
            p = u16(path)
            if wide:
                table += struct.pack("<HHIQQIIQQ", len(p), len(p) + 2, 0, at + len(blob), FT_2015_03_25, flags, 0, 0, 0)
            else:
                table += struct.pack("<HHIQIIII", len(p), len(p) + 2, at + len(blob), FT_2015_03_25, flags, 0, 0, 0)
            blob += p + b"\x00\x00"
        return struct.pack("<II", 0xBADC0FEE, len(paths)) + bytes(0x78) + table + blob

    def test_shimcache_windows7(self):
        for wide in (True, False):
            entries = s.parse_shimcache_nt61(self.shimcache(wide))
            self.assertEqual([e["path"] for e in entries], ["\\??\\C:\\Windows\\a.exe", "\\??\\C:\\Temp\\b c.exe"])
            self.assertEqual([e["executed"] for e in entries], [True, False])
            self.assertEqual(entries[0]["modified"], US_2015_03_25)
        with self.assertRaises(ValueError):
            s.parse_shimcache_nt61(bytes(0x100))

    def test_generic_shimcache_unset_time_preserves_path_without_inventing_event_time(self):
        entry = s.shimcache_entry((datetime(1601, 1, 1, tzinfo=timezone.utc), r"C:\Tools\a.exe"))
        self.assertIsNone(entry["modified"])
        self.assertEqual(entry["path"], r"C:\Tools\a.exe")
        self.assertEqual(entry["raw_modified"], "1601-01-01T00:00:00+00:00")
        self.assertIsNone(entry["executed"])
        later = s.shimcache_entry((datetime(2015, 3, 25, tzinfo=timezone.utc), r"C:\Tools\b.exe"))
        self.assertEqual(later["modified"], US_2015_03_25)

    def test_recentfilecache(self):
        raw = struct.pack("<5I", 0xFFEEFFFE, 0x2211, 3, 1, 0)
        for path in ("c:\\a\\one.exe", "c:\\two.exe"):
            raw += struct.pack("<I", len(path)) + u16(path) + b"\x00\x00"
        self.assertEqual(s.parse_recentfilecache(raw), ["c:\\a\\one.exe", "c:\\two.exe"])
        with self.assertRaises(ValueError):
            s.parse_recentfilecache(bytes(40))

    def test_job_file(self):
        raw = bytearray(0x46)
        struct.pack_into("<H", raw, 0x14, 0x46)
        struct.pack_into("<8H", raw, 0x34, 2015, 3, 3, 25, 11, 16, 0, 336)
        for text in ("C:\\Tools\\run me.exe\x00", "/c\x00"):
            raw += struct.pack("<H", len(text)) + u16(text)
        job = s.parse_job(bytes(raw))
        self.assertEqual((job["application"], job["parameters"]), ("C:\\Tools\\run me.exe", "/c"))
        self.assertEqual(job["last_run"], datetime(2015, 3, 25, 11, 16, 0, 336000))

    def test_task_file_and_dialog_history(self):
        xml = ("\ufeff<Task><Actions><Exec><Command>\"C:\\A &amp; B\\x.exe\"</Command>"
               "<Arguments>/c</Arguments></Exec></Actions></Task>").encode("utf-16")
        self.assertEqual(s.task_commands(xml), ['"C:\\A & B\\x.exe"'])
        self.assertEqual(s.task_commands(b"<Task><Actions><ComHandler/></Actions></Task>"), [])
        self.assertEqual(s.mru_order(struct.pack("<4I", 2, 0, 1, 0xFFFFFFFF)), ["2", "0", "1"])
        self.assertEqual(s.utf16z(u16("WINWORD.EXE") + b"\x00\x00\x14\x00junk"), "WINWORD.EXE")


class Machine(unittest.TestCase):
    def test_partition_table(self):
        sector = bytearray(512)
        sector[446:462] = bytes([0x80, 0, 0, 0, 0x07, 0, 0, 0]) + struct.pack("<2I", 2048, 204800)
        sector[478:494] = bytes([0x00, 0, 0, 0, 0x0B, 0, 0, 0]) + struct.pack("<2I", 206848, 1000)
        sector[510:512] = b"\x55\xaa"
        self.assertEqual(s.parse_mbr(bytes(sector)), [
            {"number": 1, "type": 7, "bootable": True, "start": 2048, "sectors": 204800},
            {"number": 3, "type": 11, "bootable": False, "start": 206848, "sectors": 1000}])
        with self.assertRaises(ValueError):
            s.parse_mbr(bytes(512))

    def test_backup_copies_add_only_what_differs(self):
        class Ev:
            rows = []

            def add(self, kind, t, res, obj, aux="", **prov):
                self.rows.append((kind, t, obj, aux, prov))
        ev = Ev()
        out = s._Out(ev, {"image": "x.E01"})
        self.assertTrue(out.add("sessionEvent", 5, 1, "shutdown", "", artifact="live", empty=""))
        self.assertFalse(out.add("sessionEvent", 5, 1, "shutdown", "", _copy=True, artifact="backup"))
        self.assertTrue(out.add("sessionEvent", 4, 1, "shutdown", "", _copy=True, artifact="backup"))
        self.assertEqual([r[4]["artifact"] for r in ev.rows], ["live", "backup"])
        self.assertEqual(ev.rows[0][4], {"artifact": "live", "image": "x.E01"})    # empty values left out


if __name__ == "__main__":
    unittest.main()
