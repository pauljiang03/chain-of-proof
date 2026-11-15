"""Parsing and time-conversion helpers of extractor/webcloud.py, on synthetic values."""
import struct
import unittest
import uuid
from datetime import datetime, timezone
import json
from types import SimpleNamespace
from unittest.mock import patch

from extractor import webcloud as w
from extractor.store import Evidence


def utc_us(*parts):
    return w.us(datetime(*parts, tzinfo=timezone.utc))


def pb_varint(n):
    out = bytearray()
    while True:
        b, n = n & 0x7F, n >> 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def pb_field(number, value):
    if isinstance(value, int):
        return pb_varint(number << 3) + pb_varint(value)
    return pb_varint(number << 3 | 2) + pb_varint(len(value)) + value


class Times(unittest.TestCase):
    def test_filetime(self):
        self.assertEqual(w.filetime_us(116444736000000000), 0)
        self.assertEqual(w.filetime_us(116444736000000000 + 10_000_005), 1_000_000)   # 100 ns floor

    def test_webkit(self):
        self.assertEqual(w.webkit_us(11_644_473_600_000_000), 0)
        self.assertEqual(w.webkit_us(11_644_473_600_000_000 + 1_500_000), 1_500_000)

    def test_local_filetime_follows_daylight_saving(self):
        def as_filetime(*parts):                # the wall-clock reading, stored as if it were UTC
            return (utc_us(*parts) + w.FILETIME_EPOCH_US) * 10
        self.assertEqual(w.local_filetime_us(as_filetime(2020, 7, 1, 12, 0, 0), "America/New_York"),
                         utc_us(2020, 7, 1, 16, 0, 0))
        self.assertEqual(w.local_filetime_us(as_filetime(2020, 1, 15, 12, 0, 0), "America/New_York"),
                         utc_us(2020, 1, 15, 17, 0, 0))

    def test_uuid1_time(self):
        u = uuid.uuid1()
        self.assertEqual(w.uuid1_us("{%s}" % str(u).upper()), u.time // 10 - w.UUID_EPOCH_US)
        self.assertIsNone(w.uuid1_us(str(uuid.uuid4())))
        self.assertIsNone(w.uuid1_us("not a guid"))

    def test_decimal_seconds_keeps_the_printed_precision(self):
        self.assertEqual(w.decimal_seconds("1500000000.24"), (1_500_000_000_240_000, 10_000))
        self.assertEqual(w.decimal_seconds("1500000000.056"), (1_500_000_000_056_000, 1_000))
        self.assertEqual(w.decimal_seconds("1500000000"), (1_500_000_000_000_000, 1_000_000))
        self.assertEqual(w.decimal_seconds("1500000000.1234567"), (1_500_000_000_123_456, 1))


class InternetExplorer(unittest.TestCase):
    def test_split_history_url(self):
        self.assertEqual(w.split_history_url("Visited: alice@http://example.com/a?b=c@d\x00"),
                         ("Visited:", "alice", "http://example.com/a?b=c@d"))
        self.assertEqual(w.split_history_url(":2020010120200102: alice@file:///C:/x.txt"),
                         (":2020010120200102:", "alice", "file:///C:/x.txt"))
        self.assertIsNone(w.split_history_url("http://example.com/"))

    def test_mshist_days(self):
        self.assertEqual(w.mshist_days("MSHist012020010120200102"), 1)
        self.assertEqual(w.mshist_days("MSHist012019123020200106"), 7)
        self.assertIsNone(w.mshist_days("History"))
        self.assertIsNone(w.mshist_days("MSHist012020139920200102"))

    def test_parse_iedownload(self):
        strings = ["Signer", "http://example.com/page", "application/octet-stream",
                   "C:\\Users\\alice\\AppData\\Local\\Temp\\a[1].exe", "http://example.com/a.exe",
                   "C:\\Users\\alice\\Desktop\\a.exe"]
        blob = b"\x01\x02" * 40 + b"".join(s.encode("utf-16-le") + b"\x00\x00" for s in strings)
        got = w.parse_iedownload(blob)
        self.assertEqual(got["url"], "http://example.com/a.exe")
        self.assertEqual(got["path"], "C:\\Users\\alice\\Desktop\\a.exe")
        self.assertEqual(got["referrer"], "http://example.com/page")
        self.assertEqual(got["mime_type"], "application/octet-stream")
        with self.assertRaises(ValueError):
            w.parse_iedownload("no url here\x00neither\x00".encode("utf-16-le"))


class ChromeCache(unittest.TestCase):
    def test_history_reader_records_source_file_separately_from_row_locator(self):
        source = r"E:\Profiles\Another Person\Profile 7\History"
        rows = {"urls": [SimpleNamespace(id=1, url="https://different.test/", title="Page", last_visit_time=0),
                         SimpleNamespace(id=2, url="https://unvisited.test/", title="Cached", last_visit_time=13_000_000_000_000_001)],
                "visits": [SimpleNamespace(id=37, url=1, transition=1, from_visit=0, visit_time=13_000_000_000_000_000)]}
        evidence = Evidence()
        with patch.object(w, "_rows", side_effect=lambda db, name: rows.get(name, [])):
            w._chrome_history(evidence, object(), source, "Another Person", {"image": "different.E01"})
        self.assertFalse(evidence.problems)
        self.assertEqual(len(evidence.rows()), 2)
        metadata = [json.loads(row[-1]) for row in evidence.rows()]
        self.assertTrue(all(p["source_file"] == source for p in metadata))
        self.assertTrue(all(p["account"] == "Another Person" for p in metadata))
        self.assertEqual({p["artifact"] for p in metadata},
                         {source + " table visits id 37", source + " table urls id 2"})

    def test_history_provider_cache(self):
        visit = pb_field(1, 13_000_000_000_000_000) + pb_field(2, 805306368)
        entry = (pb_field(1, 7) + pb_field(2, 3) + pb_field(3, 1) + pb_field(4, 13_000_000_000_000_001)
                 + pb_field(5, b"http://example.com/") + pb_field(6, b"Example") + pb_field(7, visit))
        cache = (pb_field(1, 13_000_000_000_000_002) + pb_field(2, 5) + pb_field(3, 1)
                 + pb_field(4, pb_field(1, 1) + pb_field(2, b"word"))
                 + pb_field(8, pb_field(1, 1) + pb_field(2, entry)))
        rows = list(w.parse_history_provider_cache(cache))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], "http://example.com/")
        self.assertEqual(rows[0]["title"], "Example")
        self.assertEqual(rows[0]["history_id"], 7)
        self.assertEqual(rows[0]["visits"], [(13_000_000_000_000_000, 805306368)])

    def test_truncated_message_is_an_error(self):
        with self.assertRaises((ValueError, IndexError)):
            list(w.pb_fields(pb_varint(8 << 3 | 2) + pb_varint(50) + b"short"))


HEAD = "2020-07-01 12:00:0%d,%03d -0400 INFO pid=1 2:Thread      %s:10 "
DRIVE_LOG = "\n".join([
    HEAD % (0, 0, "common.sync_app") + "Config:",
    "Email: alice@example.com",
    "Sync root: \\\\?\\C:\\Users\\alice\\Cloud Folder",
    HEAD % (1, 5, "common.service.user") + "Initializing User instance with new credentials. alice@example.com",
    HEAD % (2, 0, "common.aggregator") + "--------> Received event RawEvent(CREATE, path=u'\\\\\\\\?\\\\C:\\\\Users"
    "\\\\alice\\\\Cloud Folder\\\\sub\\\\a.txt', time=1593619202.05, is_dir=False, ino=5L)",
    HEAD % (2, 1, "common.change_buffer") + "Adding event to change buffer: RawEvent(CREATE, path=u'\\\\\\\\?\\\\C:"
    "\\\\Users\\\\alice\\\\Cloud Folder\\\\sub\\\\a.txt', time=1593619202.05, is_dir=False, ino=5L)",
    HEAD % (3, 250, "common.workers") + "Worker successfully completed [ImmutableChange(Direction.UPLOAD, "
    "Action.CREATE, ino=5, path=u'\\\\\\\\?\\\\C:\\\\Users\\\\alice\\\\Cloud Folder\\\\sub', name=u'a.txt', "
    "parent_ino=4, is_folder=False), ImmutableChange(Direction.DOWNLOAD, Action.DELETE, name=b, c.txt, "
    "rid=D2, parent_ino=4)]",
    HEAD % (4, 0, "common.cloud.cloud_watcher") + "Got: [CloudEntry(doc_id=D1,filename=a.txt,modified=1593619100,"
    "created=1593619204,acl_role=owner,doc_type=DocType.BLOB)]",
    HEAD % (5, 0, "common.cloud.cloud_watcher") + "Built: {u'D1': [WorkerDeleteCloudEvent(doc_id=D1, "
    "server_mod_time=1593619300, version=None)]}",
    HEAD % (6, 0, "common.persistence.snapshot_sqlite") + "Updating local entry inode=5, filename=a.txt, "
    "modified=1593619100.5, checksum=abc123, size=10",
    HEAD % (7, 0, "common.aggregator") + "--------> Received event RawEvent(TELEPORT, path=u'x', time=1.0)",
])


class DriveLog(unittest.TestCase):
    def setUp(self):
        self.events, self.problems = w.parse_drive_log(DRIVE_LOG)

    def pick(self, **want):
        return [e for e in self.events if all(e.get(k) == v for k, v in want.items())]

    def test_account_uses_the_offset_printed_on_the_line(self):
        (e,) = self.pick(kind="accountSeen")
        self.assertEqual((e["obj"], e["line"]), ("alice@example.com", 4))
        self.assertEqual(e["t"], utc_us(2020, 7, 1, 16, 0, 1, 5000))

    def test_file_system_event_is_reported_once_with_its_own_time(self):
        (e,) = self.pick(event="created", log_event="RawEvent CREATE")
        self.assertEqual(e["obj"], "sub\\a.txt")
        self.assertEqual(e["local_path"], "C:\\Users\\alice\\Cloud Folder\\sub\\a.txt")
        self.assertEqual((e["t"], e["res"], e["line"]), (1_593_619_202_050_000, 10_000, 5))

    def test_worker_changes(self):
        (up,) = self.pick(event="uploaded")
        self.assertEqual((up["obj"], up["t"]), ("sub\\a.txt", utc_us(2020, 7, 1, 16, 0, 3, 250000)))
        (down,) = self.pick(log_event="Direction.DOWNLOAD, Action.DELETE")
        self.assertEqual((down["obj"], down["event"]), ("b, c.txt", "deleted"))

    def test_cloud_entry_times_and_cloud_deletion(self):
        (created,) = self.pick(event="created", doc_id="D1")
        self.assertEqual((created["obj"], created["t"], created["res"]),
                         ("a.txt", 1_593_619_204_000_000, 1_000_000))
        (gone,) = self.pick(event="deleted", doc_id="D1")
        self.assertEqual((gone["obj"], gone["t"]), ("a.txt", 1_593_619_300_000_000))

    def test_local_entry(self):
        (e,) = self.pick(md5="abc123")
        self.assertEqual((e["obj"], e["event"], e["t"], e["res"], e["size"]),
                         ("a.txt", "modified", 1_593_619_100_500_000, 100_000, 10))

    def test_unknown_event_type_is_reported_not_dropped(self):
        self.assertEqual(len(self.problems), 1)
        self.assertIn("TELEPORT", self.problems[0])
        self.assertIn("line 11", self.problems[0])


class SmallDecoders(unittest.TestCase):
    def test_reg_text(self):
        self.assertEqual(w.reg_text("a@example.com".encode("utf-16-le") + b"\x00\x00"), "a@example.com")
        self.assertEqual(w.reg_text("plain"), "plain")
        self.assertEqual(w.reg_text(None), "")

    def test_mru_order(self):
        self.assertEqual(w.mru_order(struct.pack("<4I", 2, 0, 1, 0xFFFFFFFF)), [2, 0, 1])
        self.assertEqual(w.mru_order(b""), [])

    def test_note_text(self):
        self.assertEqual(w.note_text("one\r\n\r\ntwo\r\n\x00".encode("utf-16-le")), "one\n\ntwo")

    def test_oeaccount(self):
        xml = ('<?xml version="1.0" encoding="utf-16" ?>\r\n<MessageAccount>\r\n'
               '    <Account_Name type="SZ">Mail</Account_Name>\r\n'
               '    <SMTP_Email_Address type="SZ">a@example.com</SMTP_Email_Address>\r\n</MessageAccount>')
        got = w.parse_oeaccount(b"\xff\xfe" + xml.encode("utf-16-le"))
        self.assertEqual(got, {"Account_Name": "Mail", "SMTP_Email_Address": "a@example.com"})


if __name__ == "__main__":
    unittest.main()
