"""Recovery of FAT directory entries, on bytes built here (no disk image needed)."""
import struct
import unittest
from datetime import datetime

from extractor.fatcarve import Directory, _checksum, carve_fat32, folder_paths, parse_directory

DATE = (2015 - 1980) << 9 | 3 << 5 | 24          # 2015-03-24
TIME = 9 << 11 | 59 << 5 | 13                    # 09:59:26


def short(name11: bytes, attr: int, cluster: int, size: int, ntres: int = 0, tenths: int = 112):
    return (name11 + bytes([attr, ntres, tenths])
            + struct.pack("<HHHHHHHI", TIME, DATE, DATE, cluster >> 16, TIME, DATE,
                          cluster & 0xFFFF, size))


def long_name(text: str, short11: bytes) -> bytes:
    raw = (text + "\x00").encode("utf-16-le")
    raw += b"\xff" * (-len(raw) % 26)
    parts = [raw[i:i + 26] for i in range(0, len(raw), 26)]
    out = b""
    for n in range(len(parts), 0, -1):
        p = parts[n - 1]
        seq = n | (0x40 if n == len(parts) else 0)
        out += (bytes([seq]) + p[0:10] + bytes([0x0F, 0, _checksum(short11)]) + p[10:22]
                + b"\x00\x00" + p[22:26])
    return out


def folder(own: int, parent: int, body: bytes, size: int = 4096) -> bytes:
    head = short(b".          ", 0x10, own, 0) + short(b"..         ", 0x10, parent, 0)
    return (head + body).ljust(size, b"\x00")


class Volume:
    """Just enough of a volume for carve_fat32: seek and read over bytes."""
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def seek(self, pos):
        self.pos = pos

    def read(self, n):
        out = self.data[self.pos:self.pos + n]
        self.pos += len(out)
        return out


class Carve(unittest.TestCase):
    def test_names_sizes_and_times_come_from_the_entry(self):
        body = (long_name("winter_whether_advisory.zip", b"WINTER~1ZIP")
                + short(b"WINTER~1ZIP", 0x20, 3557, 16381123)
                + short(b"DESIGN     ", 0x10, 9, 0, ntres=0x08)
                + short(b"\xe5OTES   TXT", 0x20, 50, 12)
                + long_name("not_this_file.txt", b"OTHER~1 TXT")
                + short(b"REAL~1  TXT", 0x20, 60, 5))
        d = parse_directory(folder(7, 3, body))
        self.assertEqual((d.own, d.parent, d.complete), (7, 3, True))
        zip_, design, removed, real = d.entries
        self.assertEqual((zip_.name, zip_.short_name, zip_.size, zip_.first_cluster),
                         ("winter_whether_advisory.zip", "WINTER~1.ZIP", 16381123, 3557))
        self.assertEqual(zip_.created, datetime(2015, 3, 24, 9, 59, 27, 120000))   # +1.12 s
        self.assertEqual(zip_.modified, datetime(2015, 3, 24, 9, 59, 26))
        self.assertEqual((design.name, design.is_dir), ("design", True))    # lower-case flag
        self.assertEqual((removed.name, removed.deleted), ("?OTES.TXT", True))
        self.assertEqual(real.name, "REAL~1.TXT")   # a long name for another file is not used

    def test_only_free_clusters_are_recovered_and_lost_names_stay_lost(self):
        cluster = 512
        reserved, fat_sectors = 2, 1
        data = bytearray(512 * (reserved + fat_sectors) + cluster * 8)
        fat_at, data_at = 512 * reserved, 512 * (reserved + fat_sectors)
        struct.pack_into("<I", data, fat_at + 4 * 5, 0x0FFFFFFF)       # cluster 5 is in use
        def put(n, content):
            data[data_at + (n - 2) * cluster: data_at + (n - 1) * cluster] = content
        put(3, folder(3, 0, short(b"DESIGN     ", 0x10, 4, 0), cluster))
        put(4, folder(4, 3, short(b"A       TXT", 0x20, 6, 10), cluster))
        put(5, folder(5, 0, short(b"LIVE    TXT", 0x20, 7, 10), cluster))   # allocated
        put(8, folder(77, 0, short(b"OLD     TXT", 0x20, 9, 10), cluster))  # wrong place
        found = carve_fat32(Volume(bytes(data)), 512, 1, reserved, 1, fat_sectors,
                            len(data) // 512)
        self.assertEqual(sorted(found), [3, 4, 8])
        self.assertEqual(folder_paths(found), {
            3: "\\[lost folder 3]", 4: "\\[lost folder 3]\\DESIGN",
            8: "\\[lost folder at cluster 8, older layout]"})

    def test_fat_modified_time_takes_the_offset_in_force_when_it_was_written(self):
        from zoneinfo import ZoneInfo
        from extractor.fatcarve import fat_times_utc
        from extractor.store import us
        from datetime import timezone
        tz = ZoneInfo("America/New_York")
        utc = lambda *a: us(datetime(*a, tzinfo=timezone.utc))
        # copied on 2015-03-24 (UTC-4); the file was last modified in December (UTC-5 then)
        c, m, note = fat_times_utc(datetime(2015, 3, 24, 9, 59, 37), datetime(2014, 12, 16, 12, 10, 26), tz)
        self.assertEqual(c, utc(2015, 3, 24, 13, 59, 37))
        self.assertEqual(m, utc(2014, 12, 16, 16, 10, 26))     # +4 h, not +5 h
        self.assertIn("-0400", note)
        # modified after it was created: the stamp was written on its own date
        c, m, _ = fat_times_utc(datetime(2014, 12, 1, 8, 0, 0), datetime(2014, 12, 16, 12, 10, 26), tz)
        self.assertEqual(m, utc(2014, 12, 16, 17, 10, 26))

    def test_a_cluster_that_is_not_a_directory_is_ignored(self):
        self.assertIsNone(parse_directory(b"\x00" * 4096))
        self.assertEqual(folder_paths({9: Directory(own=9, parent=0)}), {9: "\\[lost folder 9]"})


if __name__ == "__main__":
    unittest.main()
