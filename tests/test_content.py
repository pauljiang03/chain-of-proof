"""extractor/content.py on synthetic bytes: the signature table, hashing, and the
arithmetic for reading a recovered FAT entry as one contiguous run. No image, no dissect."""
import hashlib
import io
import struct
import unittest
import zipfile

from extractor import content as c


def zipped(*names):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            z.writestr(name, "<x/>" * 20)
    return buf.getvalue()


class Signatures(unittest.TestCase):
    def test_office_containers(self):
        self.assertEqual(c.signature_of(zipped("[Content_Types].xml", "_rels/.rels", "word/document.xml")),
                         (c.ZIP_OFFICE, "word"))
        self.assertEqual(c.signature_of(zipped("[Content_Types].xml", "ppt/presentation.xml")),
                         (c.ZIP_OFFICE, "powerpoint"))
        self.assertEqual(c.signature_of(zipped("[Content_Types].xml", "xl/workbook.xml")),
                         (c.ZIP_OFFICE, "excel"))
        self.assertEqual(c.signature_of(zipped("[Content_Types].xml", "other.xml")),
                         (c.ZIP_OFFICE, "open packaging container"))
        self.assertEqual(c.signature_of(zipped("notes.txt")), ("zip", ""))
        self.assertEqual(c.signature_of(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + bytes(504)),
                         (c.OLE_OFFICE, ""))

    def test_common_types(self):
        cases = {
            b"%PDF-1.5\n": "pdf", b"\xFF\xD8\xFF\xE0\x00\x10JFIF": "jpeg",
            b"\x89PNG\r\n\x1a\n\x00\x00": "png", b"GIF89a\x01\x00": "gif", b"GIF87a\x01\x00": "gif",
            b"BM\x36\x10\x0e\x00\x00\x00\x00\x00\x36\x00": "bmp", b"MM\x00*\x00\x00": "tiff",
            b"II*\x00\x08\x00": "tiff", b"7z\xBC\xAF\x27\x1C\x00\x04": "7z",
            b"RIFF\x10\x00\x00\x00AVI LIST": "avi", b"RIFF\x10\x00\x00\x00WAVEfmt ": "wav",
            b"MZ\x90\x00\x03": "windows executable", b"#!AMR\n": "amr",
            b"L\x00\x00\x00\x01\x14\x02\x00\x00": "windows shortcut",
            b"SQLite format 3\x00": "sqlite", b"\x00\x00\x00\x18ftypmp42": "mp4",
        }
        for head, name in cases.items():
            self.assertEqual(c.signature_of(head)[0], name, head)

    def test_unknown(self):
        for head in (b"", b"[.ShellClassInfo]\r\n", b"BMW is not a bitmap", b"RIFF\x00\x00\x00\x00????",
                     bytes(16)):
            self.assertEqual(c.signature_of(head), ("unknown", ""), head)

    def test_zip_names_stop_where_sizes_are_unknown(self):
        head = (b"PK\x03\x04\x14\x00\x08\x00\x08\x00" + bytes(16) + struct.pack("<HH", 5, 0)
                + b"a.txt" + b"PK\x03\x04" + bytes(40))
        self.assertEqual(c.zip_names(head), ["a.txt"])

    def test_extension(self):
        self.assertEqual(c.extension_of("\\design\\winter_storm.AMR"), "amr")
        self.assertEqual(c.extension_of("\\[lost folder at cluster 7, older layout]\\a.b.JPG"), "jpg")
        self.assertEqual(c.extension_of("\\folder.d\\README"), "")
        self.assertEqual(c.extension_of("\\.hidden"), "")
        self.assertIn("docx", c.EXTENSIONS[c.ZIP_OFFICE])
        self.assertNotIn("amr", c.EXTENSIONS[c.OLE_OFFICE])


class Hashing(unittest.TestCase):
    def test_digest(self):
        data = bytes(range(256)) * 40
        digest, size, head = c.digest_of([data[:100], data[100:5000], data[5000:]])
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())
        self.assertEqual((size, head), (len(data), data[:c.HEAD]))
        self.assertEqual(c.digest_of([]), (hashlib.sha256(b"").hexdigest(), 0, b""))

    def test_stream_stops_at_size(self):
        fh = io.BytesIO(b"abcdefghij")
        fh.seek(2)
        self.assertEqual(b"".join(c._stream(fh, 5, step=2)), b"cdefg")
        self.assertEqual(b"".join(c._stream(io.BytesIO(b"xyz"))), b"xyz")

    def test_row(self):
        rows = []

        class Ev:
            def add(self, kind, t, res, obj, aux="", **prov):
                rows.append((kind, t, res, obj, aux, prov))

        ctx = {"common": {"image": "i.E01", "exhibit": "X", "tool": "t"}, "examined_at": 42}
        c._row(Ev(), ctx, "\\a\\holiday.jpg", "ab" * 32, 9, b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1!", "1234ABCD",
               "somewhere", recovered=True)
        kind, t, res, obj, aux, prov = rows[0]
        self.assertEqual((kind, t, res, obj, aux), ("fileContent", 42, 1, "\\a\\holiday.jpg", "sha256:" + "ab" * 32))
        self.assertEqual((prov["signature"], prov["extension"], prov["extension_fits_signature"]),
                         (c.OLE_OFFICE, "jpg", False))
        self.assertEqual((prov["location"], prov["size"], prov["exhibit"], prov["recovered"]),
                         ("1234ABCD", 9, "X", True))


class RecoveredRuns(unittest.TestCase):
    CS, START = 4096, 4194304
    END = START + 261120 * CS

    def test_contiguous_run(self):
        self.assertEqual(c.contiguous_run(5, 14547968, self.CS, self.START, self.END),
                         (self.START + 3 * self.CS, 3552))
        self.assertEqual(c.contiguous_run(2, 1, self.CS, self.START, self.END), (self.START, 1))
        self.assertEqual(c.contiguous_run(0, 0, self.CS, self.START, self.END), (self.START, 0))
        self.assertEqual(c.contiguous_run(261121, self.CS, self.CS, self.START, self.END)[1], 1)
        with self.assertRaises(ValueError):                      # one cluster too many
            c.contiguous_run(261121, self.CS + 1, self.CS, self.START, self.END)
        with self.assertRaises(ValueError):
            c.contiguous_run(0, 10, self.CS, self.START, self.END)

    def test_fat_in_use(self):
        fat = struct.pack("<5I", 0x0FFFFFF8, 0xFFFFFFFF, 0x0FFFFFFF, 0, 0xF0000000)
        self.assertEqual([c.fat_in_use(fat, i) for i in range(2, 5)], [True, False, False])

    def test_older_layout_is_derived_only_when_unique(self):
        old_size, old_start, own = 16384, 282624, 11492
        folder = old_start + (own - 2) * old_size
        files = [(11493, 921654), (11550, 6717692), (11961, 3352929)]     # back to back at 16 KiB
        self.assertEqual(c.older_layout(folder, own, files), (old_size, old_start))
        with self.assertRaises(ValueError):          # one tiny file: several sizes fit
            c.older_layout(1 << 20, 3, [(4, 100)])
        with self.assertRaises(ValueError):          # files overlap at every size that keeps the start >= 0
            c.older_layout(folder, own, [(11493, 921654), (11494, 5)])
        with self.assertRaises(ValueError):
            c.older_layout(folder, 1, files)

    def test_collide(self):
        self.assertFalse(c._collide([(10, 4096), (11, 4096), (12, 0)], 4096))
        self.assertTrue(c._collide([(10, 4097), (11, 4096)], 4096))
        self.assertFalse(c._collide([(10, 4097), (11, 4096)], 8192))


if __name__ == "__main__":
    unittest.main()
