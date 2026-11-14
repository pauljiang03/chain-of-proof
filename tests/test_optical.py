"""extractor/optical.py on synthetic bytes: descriptor parsing, serial, times, the E01
sections, and a small hand-built UDF disc with two states. No image, no dissect."""
import io
import struct
import tempfile
import unittest
import zlib
from datetime import datetime, timezone
from pathlib import Path

from extractor import optical as o

S = o.SECTOR


def us(*args):
    return int(datetime(*args, tzinfo=timezone.utc).timestamp()) * 1_000_000


def tag(ident, body, location=0):
    head = struct.pack("<HHBBHHHI", ident, 3, 0, 0, 0, o.crc_itu_t(body), len(body), location)
    checksum = (sum(head[:4]) + sum(head[5:])) & 0xFF
    return head[:4] + bytes([checksum]) + head[5:] + body


def sector(data):
    return data + bytes(S - len(data))


def dstr(text, size):
    raw = b"\x08" + text.encode("latin-1")
    return raw + bytes(size - len(raw) - 1) + bytes([len(raw)])


def stamp(y, mo, d, h, mi, s, micro=0, offset=-240, kind=1):
    return struct.pack("<HhBBBBBBBB", (kind << 12) | (offset & 0xFFF), y, mo, d, h, mi, s,
                       micro // 10000, micro // 100 % 100, micro % 100)


def long_ad(length, block, part, unique=0):
    return struct.pack("<IIH", length, block, part) + b"\x00\x00" + struct.pack("<I", unique)


CREATED = stamp(2015, 3, 24, 16, 55, 1, 21784)
MODIFIED = stamp(2015, 1, 16, 15, 10, 24)


def efe(location, file_type, size, unique, area, flags, created=CREATED, modified=MODIFIED):
    d = bytearray(216)
    d[27] = file_type
    struct.pack_into("<H", d, 34, flags)
    struct.pack_into("<H", d, 48, 1)
    struct.pack_into("<Q", d, 56, size)
    d[80:92], d[92:104], d[104:116], d[116:128] = modified, modified, created, modified
    struct.pack_into("<QII", d, 200, unique, 0, len(area))
    return sector(tag(o.TAG_EFE, bytes(d[16:]) + area, location))


def fe(location, file_type, unique, area, modified=MODIFIED):
    d = bytearray(176)
    d[27] = file_type
    struct.pack_into("<H", d, 34, 3)
    struct.pack_into("<Q", d, 56, len(area))
    d[84:96] = modified
    struct.pack_into("<QII", d, 160, unique, 0, len(area))
    return sector(tag(o.TAG_FE, bytes(d[16:]) + area, location))


def fid(name, chars, icb):
    ident = b"\x08" + name.encode("latin-1") if name else b""
    body = struct.pack("<HBB", 1, chars, len(ident)) + icb + struct.pack("<H", 0) + ident
    body += bytes(-(16 + len(body)) % 4)
    return tag(o.TAG_FID, body)


def vat(entries, previous=o.UNMAPPED, label="TESTDISC"):
    head = struct.pack("<HH", 152, 0) + dstr(label, 128) + struct.pack("<IIIHHHH", previous, 0, 0,
                                                                        0x201, 0x201, 0x201, 0)
    return head + struct.pack("<%dI" % len(entries), *entries)


class Pieces(unittest.TestCase):
    def test_crc_and_tag(self):
        self.assertEqual(o.crc_itu_t(b"123456789"), 0x31C3)
        raw = tag(o.TAG_FSD, b"body" * 10, location=7)
        t = o.parse_tag(raw)
        self.assertEqual((t.ident, t.location, t.crc_length), (o.TAG_FSD, 7, 40))
        self.assertIsNone(o.parse_tag(raw[:20] + b"X" + raw[21:]))              # CRC broken
        self.assertIsNotNone(o.parse_tag(raw[:20] + b"X" + raw[21:], check_crc=False))
        self.assertIsNone(o.parse_tag(raw[:8] + b"\x01" + raw[9:]))              # checksum broken
        self.assertIsNone(o.parse_tag(bytes(16)))

    def test_strings(self):
        self.assertEqual(o.dstring(dstr("IAMAN CD", 128)), "IAMAN CD")
        self.assertEqual(o.dstring(bytes(32)), "")
        self.assertEqual(o.cs0(b"\x10" + "né".encode("utf-16-be")), "né")
        self.assertEqual(o.cs0(b"\xfe" + b"gone"), "gone")                      # deleted, 8-bit
        with self.assertRaises(ValueError):
            o.cs0(b"\x07abc")

    def test_timestamp(self):
        t, note = o.stamp_utc(stamp(2015, 3, 24, 16, 53, 17, 880500))
        self.assertEqual(t, us(2015, 3, 24, 20, 53, 17) + 880500)                # local + 4 h
        self.assertIn("-240", note)
        self.assertEqual(o.stamp_utc(stamp(2015, 1, 23, 16, 47, 10, kind=0, offset=0))[0],
                         us(2015, 1, 23, 16, 47, 10))
        self.assertEqual(o.stamp_utc(stamp(2015, 1, 23, 9, 0, 0, offset=330))[0],
                         us(2015, 1, 23, 3, 30, 0))
        for bad in (bytes(12), stamp(2015, 13, 1, 0, 0, 0), stamp(2015, 1, 1, 0, 0, 0, kind=2),
                    stamp(2015, 1, 1, 0, 0, 0, offset=-2047)):
            with self.assertRaises(ValueError):
                o.stamp_utc(bad)

    def test_timestamp_without_offset_uses_named_zone(self):
        try:
            got = o.stamp_utc(stamp(2015, 1, 23, 16, 47, 10, offset=-2047), "America/New_York")
        except Exception as e:                                   # no tz database on this machine
            if type(e).__name__ == "ZoneInfoNotFoundError":
                self.skipTest("no time zone database")
            raise
        self.assertEqual(got[0], us(2015, 1, 23, 21, 47, 10))                    # EST in January
        self.assertIn("America/New_York", got[1])

    def test_serial(self):
        self.assertEqual(o.udf_serial32(bytes([1, 2, 3, 4])), 0x04030201)
        self.assertEqual(o.udf_serial32(bytes([1, 2, 3, 4, 0xFF, 0, 0, 0xFD])), 0x01030200)   # no carry
        self.assertEqual(o.udf_serial32(bytes(512)), 0)

    def test_allocation_descriptors(self):
        short = struct.pack("<II", 4096, 10) + struct.pack("<II", (2 << 30) | 100, 0) + bytes(8)
        self.assertEqual(o.parse_allocation_descriptors(short, 0),
                         [o.Extent(0, 4096, 10, None), o.Extent(2, 100, 0, None)])
        self.assertEqual(o.parse_allocation_descriptors(long_ad(5000, 39, 0), 1),
                         [o.Extent(0, 5000, 39, 0)])
        with self.assertRaises(ValueError):
            o.parse_allocation_descriptors(b"", 3)

    def test_file_entries(self):
        e = o.parse_file_entry(efe(6, o.FT_FILE, 5000, 20, long_ad(5000, 10, 0), 0x21))
        self.assertTrue(e.extended)
        self.assertEqual((e.file_type, e.size, e.unique_id, e.tag.location), (o.FT_FILE, 5000, 20, 6))
        self.assertEqual(e.extents, [o.Extent(0, 5000, 10, 0)])
        self.assertEqual(o.stamp_utc(e.created)[0], us(2015, 3, 24, 20, 55, 1) + 21784)
        self.assertEqual(o.stamp_utc(e.modified)[0], us(2015, 1, 16, 19, 10, 24))
        small = o.parse_file_entry(efe(7, o.FT_FILE, 3, 21, b"abc", 3))
        self.assertEqual((small.embedded, small.extents), (b"abc", []))
        plain = o.parse_file_entry(fe(31, o.FT_VAT, 16, b"x" * 8))
        self.assertEqual((plain.extended, plain.created, plain.embedded), (False, None, b"x" * 8))
        with self.assertRaises(ValueError):
            o.parse_file_entry(bytes(S))

    def test_fids(self):
        data = (fid("", 0x0A, long_ad(S, 1, 1)) + fid("old name", 0x06, bytes(16))
                + fid("report.docx", 0, long_ad(S, 5, 1, unique=33)))
        fids, stopped = o.parse_fids(data)
        self.assertIsNone(stopped)
        self.assertEqual([f.name for f in fids], ["", "old name", "report.docx"])
        self.assertTrue(fids[0].parent and fids[0].directory)
        self.assertTrue(fids[1].deleted and fids[1].icb.length == 0)
        self.assertEqual((fids[2].icb.block, fids[2].icb.partition, fids[2].unique_id), (5, 1, 33))
        fids, stopped = o.parse_fids(data[:40] + b"\xff" * 40)
        self.assertEqual(len(fids), 1)
        self.assertIn("byte 40", stopped)

    def test_vat(self):
        v = o.parse_vat(vat([7, 8, o.UNMAPPED], previous=31), o.FT_VAT)
        self.assertEqual((v.entries, v.previous, v.label), ((7, 8, o.UNMAPPED), 31, "TESTDISC"))
        self.assertIsNone(o.parse_vat(vat([1]), o.FT_VAT).previous)
        old = struct.pack("<2I", 4, 5) + b"\x00" + o.VAT150_ID.ljust(31, b"\x00") + struct.pack("<I", 9)
        v = o.parse_vat(old, 0)
        self.assertEqual((v.entries, v.previous, v.label), ((4, 5), 9, None))
        with self.assertRaises(ValueError):
            o.parse_vat(b"\x00" * 40, 0)

    def test_logical_volume(self):
        lvd = o.parse_lvd(make_lvd())
        self.assertEqual((lvd.label, lvd.block_size, lvd.revision), ("TESTDISC", S, "2.01"))
        self.assertEqual(lvd.fsd, o.Extent(0, S, 0, 1))
        self.assertEqual(lvd.maps, (o.PartitionMap("physical", 0), o.PartitionMap("virtual", 0)))


def make_lvd():
    d = bytearray(440)
    struct.pack_into("<I", d, 16, 3)
    d[84:212] = dstr("TESTDISC", 128)
    struct.pack_into("<I", d, 212, S)
    d[217:236] = b"*OSTA UDF Compliant"
    struct.pack_into("<H", d, 240, 0x0201)
    d[248:264] = long_ad(S, 0, 1)
    maps = bytes([1, 6]) + struct.pack("<HH", 1, 0)
    maps += bytes([2, 64, 0, 0, 0]) + b"*UDF Virtual Partition".ljust(31, b"\x00") + struct.pack("<HH", 1, 0)
    maps += bytes(70 - len(maps))
    struct.pack_into("<II", d, 264, len(maps), 2)
    return sector(tag(o.TAG_LVD, bytes(d[16:]) + maps, 34))


class Container(unittest.TestCase):
    def segment(self):
        def checked(data):
            return data + struct.pack("<I", zlib.adler32(data))
        md5, sha1 = bytes(range(16)), bytes(range(100, 120))
        header = zlib.compress("1\nmain\nc\tn\tm\tav\tov\ncase\tev\t1427383810\t7.09\tWindows 7\n\n"
                               .encode("utf-16"))
        parts = [("header2", header),
                 ("session", checked(struct.pack("<I", 1) + bytes(28)) + checked(struct.pack("<II", 0, 16) + bytes(24))),
                 ("error2", checked(struct.pack("<I", 2) + bytes(512)) + checked(struct.pack("<IIII", 321, 1, 900, 3))),
                 ("digest", checked(md5 + sha1 + bytes(40))),
                 ("hash", checked(md5 + bytes(16))),
                 ("done", b"")]
        out = bytearray(o.EWF_MAGIC[0] + b"\x01\x01\x00\x00\x00")
        for kind, data in parts:
            here = len(out)
            following = here if kind == "done" else here + 76 + len(data)
            size = 0 if kind == "done" else 76 + len(data)
            d = kind.encode().ljust(16, b"\x00") + struct.pack("<QQ", following, size) + bytes(40)
            out += d + struct.pack("<I", zlib.adler32(d)) + data
        return bytes(out), md5.hex(), sha1.hex()

    def test_sections(self):
        raw, md5, sha1 = self.segment()
        fh = io.BytesIO(raw)
        self.assertEqual([k for k, _o, _s in o.ewf_sections(fh)],
                         ["header2", "session", "error2", "digest", "hash", "done"])
        self.assertEqual([(a, v, s) for a, v, s, _off in o.ewf_digests(fh)],
                         [("md5", md5, "digest"), ("sha1", sha1, "digest"), ("md5", md5, "hash")])
        self.assertEqual(o.ewf_sessions(fh), [(0, 16)])
        self.assertEqual(o.ewf_unreadable(fh), [(321, 1), (900, 3)])
        self.assertEqual(o.ewf_header(fh)["m"], "1427383810")

    def test_damage_is_refused(self):
        raw, _md5, _sha1 = self.segment()
        at = raw.index(bytes(range(16)))
        with self.assertRaises(ValueError):
            o.ewf_digests(io.BytesIO(raw[:at] + b"\xff" + raw[at + 1:]))
        with self.assertRaises(ValueError):
            o.ewf_sections(io.BytesIO(b"not an image at all"))

    def test_digest_rows(self):
        raw, md5, sha1 = self.segment()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "disc.E01"
            path.write_bytes(raw)
            ev = Collector()
            n = o.emit_image_digests(ev, path, CTX)
        self.assertEqual(n, 2)
        self.assertEqual([(k, obj, aux) for k, _t, obj, aux, _p in ev.rows],
                         [("systemSetting", "image md5", md5), ("systemSetting", "image sha1", sha1)])
        self.assertEqual(ev.rows[0][4]["acquired_as_recorded"], "1427383810")


class Collector:
    def __init__(self):
        self.rows, self.problems = [], []

    def add(self, kind, t, res, obj, aux="", **prov):
        assert isinstance(t, int) and t >= 0 and res >= 1 and "artifact" in prov
        self.rows.append((kind, t, obj, aux, prov))

    def problem(self, where, error):
        self.problems.append(f"{where}: {error}")


CTX = {"common": {"image": "disc.img", "exhibit": "T#1", "tool": "test"},
       "examined_at": 1794614400000000, "pc_time_zone": "UTC"}
PAYLOAD = bytes(range(256)) * 20            # 5120 bytes: 2.5 sectors


def make_disc():
    """A write-once disc written twice. First state: \\a.txt and \\sub\\b.bin. Second
    state: a.txt deleted (its entry keeps the name, drops the address), \\c.txt added."""
    start = 288
    disc = {16: b"\x00BEA01\x01", 17: b"\x00NSR03\x01", 18: b"\x00TEA01\x01"}
    pvd = bytearray(512)
    struct.pack_into("<I", pvd, 16, 1)
    pvd[72:200] = dstr("TEST SET", 128)
    disc[32] = tag(o.TAG_PVD, bytes(pvd[16:]), 32)
    pd = bytearray(512)
    struct.pack_into("<IHH", pd, 16, 2, 1, 0)
    struct.pack_into("<II", pd, 188, start, 1000)
    disc[33] = tag(o.TAG_PD, bytes(pd[16:]), 33)
    disc[34] = make_lvd()
    disc[35] = tag(o.TAG_TD, bytes(496), 35)
    disc[256] = tag(o.TAG_AVDP, struct.pack("<IIII", 4 * S, 32, 4 * S, 32) + bytes(480), 256)
    fsd = bytearray(512)
    fsd[16:28] = stamp(2015, 3, 24, 16, 53, 17, 880500)
    fsd[112:240] = dstr("TESTDISC", 128)
    fsd[304:336] = dstr("SET", 32)
    fsd[400:416] = long_ad(S, 1, 1)
    disc[start] = tag(o.TAG_FSD, bytes(fsd[16:]), 0)
    parent = fid("", 0x0A, long_ad(S, 1, 1))
    root1 = parent + fid("a.txt", 0, long_ad(S, 2, 1, 17)) + fid("sub", 2, long_ad(S, 3, 1, 18))
    disc[start + 1] = efe(1, o.FT_DIRECTORY, len(root1), 0, root1, 3)
    disc[start + 2] = efe(2, o.FT_FILE, len(PAYLOAD), 17, long_ad(len(PAYLOAD), 10, 0), 0x21)
    sub = parent + fid("b.bin", 0, long_ad(S, 4, 1, 19))
    disc[start + 3] = efe(3, o.FT_DIRECTORY, len(sub), 18, sub, 3)
    disc[start + 4] = efe(4, o.FT_FILE, 3, 19, b"bbb", 3)
    disc[start + 5] = fe(5, o.FT_VAT, 20, vat([0, 1, 2, 3, 4]), stamp(2015, 3, 24, 16, 55, 47))
    for i in range(3):
        disc[start + 10 + i] = PAYLOAD[i * S:(i + 1) * S]
    root2 = (parent + fid("a.txt", 0x04, bytes(16)) + fid("sub", 2, long_ad(S, 3, 1, 18))
             + fid("c.txt", 0, long_ad(S, 5, 1, 21)))
    disc[start + 13] = efe(1, o.FT_DIRECTORY, len(root2), 0, root2, 3)
    disc[start + 14] = efe(5, o.FT_FILE, 2, 21, b"cc", 3, created=stamp(2015, 3, 24, 16, 57, 0))
    disc[start + 15] = fe(15, o.FT_VAT, 22, vat([0, 13, 2, 3, 4, 14], previous=5),
                          stamp(2015, 3, 24, 16, 58, 15))
    total = start + 16
    return b"".join(sector(disc.get(i, b"")) for i in range(total)), bytes(sector(disc[start])[:512])


class Disc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "disc.img"
        image, self.fsd = make_disc()
        self.path.write_bytes(image)

    def test_states(self):
        s = o.survey(self.path)
        self.assertTrue(o.is_optical(self.path))
        self.assertEqual(s.udf.problems, [])
        self.assertEqual([v.vat_sector for v in s.udf.versions], [293, 303])
        self.assertEqual({v.serial for v in s.udf.versions}, {o.udf_serial32(self.fsd)})
        self.assertEqual(sorted(f.path for f in s.current), ["\\c.txt", "\\sub\\b.bin"])
        self.assertEqual([f.path for f, _extra in s.recovered], ["\\a.txt"])
        gone, extra = s.recovered[0]
        self.assertEqual(extra["listed_by_allocation_tables_at_sectors"], [293])
        self.assertEqual(extra["last_listed_utc"], "2015-03-24T20:55:47.000000Z")
        self.assertEqual(b"".join(s.content(gone)), PAYLOAD)
        self.assertEqual(s.udf.versions[1].nameless, ["\\a.txt"])
        self.assertEqual(s.udf.uncovered(), [])
        s.close()

    def test_rows(self):
        ev = Collector()
        o.extract(ev, self.path, CTX)
        self.assertEqual(ev.problems, [])
        serial = "%08X" % o.udf_serial32(self.fsd)
        area = "unallocated space of device disc T#1"
        got = sorted((k, obj, aux) for k, _t, obj, aux, _p in ev.rows)
        self.assertEqual(got, sorted(
            [("volumeOnDevice", "disc T#1", serial), ("unallocatedOnDevice", "disc T#1", area)]
            + [(k, p, serial) for k in ("fileCreated", "fileModified") for p in ("\\c.txt", "\\sub\\b.bin")]
            + [(k, "\\a.txt", area) for k in ("fileCreated", "fileModified")]))
        rows = {(k, obj): (t, p) for k, t, obj, _aux, p in ev.rows}
        self.assertEqual(rows[("fileCreated", "\\a.txt")][0], us(2015, 3, 24, 20, 55, 1) + 21784)
        self.assertEqual(rows[("fileModified", "\\a.txt")][0], us(2015, 1, 16, 19, 10, 24))
        self.assertTrue(rows[("fileCreated", "\\a.txt")][1]["recovered"])
        self.assertEqual(rows[("fileCreated", "\\a.txt")][1]["size"], len(PAYLOAD))
        self.assertEqual(rows[("fileCreated", "\\c.txt")][0], us(2015, 3, 24, 20, 57, 0))
        self.assertEqual(rows[("volumeOnDevice", "disc T#1")][1]["volume_label"], "TESTDISC")

    def test_unreadable_sector_blocks_content(self):
        s = o.survey(self.path)
        gone = s.recovered[0][0]
        s.unreadable = frozenset([299])
        with self.assertRaises(ValueError):
            list(s.content(gone))
        s.close()

    def test_not_a_disc(self):
        self.path.write_bytes(bytes(40 * S))
        self.assertFalse(o.is_optical(self.path))
        ev = Collector()
        o.extract(ev, self.path, CTX)
        self.assertEqual(ev.rows, [])
        self.assertEqual(len(ev.problems), 1)


if __name__ == "__main__":
    unittest.main()
