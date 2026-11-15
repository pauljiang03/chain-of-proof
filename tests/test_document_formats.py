"""Synthetic format fixtures exercise real readers without answer/benchmark data."""
import hashlib
import importlib.util
import io
import json
import struct
import subprocess
import unittest
import zlib
from types import SimpleNamespace
from unittest.mock import patch

from extractor import document_formats as formats
from extractor import document_metadata as reader
from extractor.store import Evidence
from tests.test_inventory import FS


def available(module):
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:
        return False


def summary(properties=None, codepage=1252):
    """MS-OLEPS PropertySetStream, including its mandatory typed CodePage."""
    if properties is None:
        properties = [(2, 'Résumé\0'), (4, 'Recorded Author'), (18, 'Recorded Application'),
                      (12, 132537600000000001), (13, 0)]
    encoded = [(1, struct.pack('<IHH', 2, codepage, 0))]
    for pid, value in properties:
        if isinstance(value, bytes):
            blob = value
        elif isinstance(value, int):
            blob = struct.pack('<IQ', 0x40, value)
        else:
            codec = 'utf-16-le' if codepage == 1200 else 'cp' + str(codepage)
            raw = (value + '\0').encode(codec)
            blob = struct.pack('<II', 0x1e, len(raw)) + raw
            blob += bytes(-len(blob) % 4)
        encoded.append((pid, blob))
    offset, table, values = 8 + len(encoded) * 8, [], []
    for pid, blob in encoded:
        table.append(struct.pack('<II', pid, offset))
        values.append(blob)
        offset += len(blob)
    section = struct.pack('<II', offset, len(encoded)) + b''.join(table + values)
    return struct.pack('<HHI16sI16sI', 0xfffe, 0, 0, bytes(16), 1,
                       formats.SUMMARY_FMTID.bytes_le, 48) + section


def office_streams(kind='doc', metadata=None):
    if kind == 'doc':
        fib = bytearray(32)
        struct.pack_into('<HH', fib, 0, 0xa5ec, 0xc1)
        streams = [('WordDocument', bytes(fib)), ('0Table', b'\0' * 8)]
    elif kind == 'xls':
        streams = [('Workbook', struct.pack('<4H12s', 0x809, 16, 0x600, 5, bytes(12)))]
    else:
        main = struct.pack('<HHI28s', 0, 0xff5, 28, bytes(28))
        current = struct.pack('<HHIIIIHHBBHI', 0, 0xff6, 24, 20, 0xe391c05f, 0,
                              0, 0x3f4, 3, 0, 0, 8)
        streams = [('PowerPoint Document', main), ('Current User', current)]
    if metadata is not False:
        streams.append((formats.SUMMARY_STREAM, summary() if metadata is None else metadata))
    return streams


def compound(streams, version=3):
    """Build valid small CFB allocations, using real mini and regular streams."""
    sector_size = 512 if version == 3 else 4096
    entries_per_sector = sector_size // 128
    directory_sectors = (len(streams) + 1 + entries_per_sector - 1) // entries_per_sector
    sectors = [bytes(sector_size)] * (1 + directory_sectors)
    allocation = [formats.FAT] + [i + 2 for i in range(directory_sectors)]
    allocation[-1] = formats.END

    def allocate(blob):
        if not blob:
            return formats.END
        start = len(sectors)
        padded = blob + bytes(-len(blob) % sector_size)
        count = len(padded) // sector_size
        for offset in range(count):
            sectors.append(padded[offset * sector_size:(offset + 1) * sector_size])
            allocation.append(start + offset + 1 if offset < count - 1 else formats.END)
        return start

    mini_blob, minifat, locations = b'', [], []
    for name, data in streams:
        if len(data) >= 4096:
            locations.append(allocate(data))
        elif data:
            start = len(minifat)
            padded = data + bytes(-len(data) % 64)
            count = len(padded) // 64
            mini_blob += padded
            minifat.extend(start + i + 1 if i < count - 1 else formats.END for i in range(count))
            locations.append(start)
        else:
            locations.append(formats.END)
    mini_start = allocate(mini_blob)
    mini_table = b''.join(struct.pack('<I', value) for value in minifat)
    mini_table += b'\xff' * (-len(mini_table) % sector_size)
    mini_fat_start = allocate(mini_table)

    def directory_entry(name, kind, start, size, child=formats.FREE, right=formats.FREE):
        entry = bytearray(128)
        raw = (name + '\0').encode('utf-16-le')
        entry[:len(raw)] = raw
        struct.pack_into('<HBBIII', entry, 64, len(raw), kind, 1, formats.FREE, right, child)
        struct.pack_into('<IQ', entry, 116, start, size)
        return bytes(entry)

    directory = directory_entry('Root Entry', 5, mini_start, len(mini_blob), child=1 if streams else formats.FREE)
    for index, ((name, data), location) in enumerate(zip(streams, locations), 1):
        directory += directory_entry(name, 2, location, len(data), right=index + 1 if index < len(streams) else formats.FREE)
    directory += bytes(directory_sectors * sector_size - len(directory))
    for index in range(directory_sectors):
        sectors[index + 1] = directory[index * sector_size:(index + 1) * sector_size]
    assert len(allocation) <= sector_size // 4
    sectors[0] = b''.join(struct.pack('<I', value) for value in allocation)
    sectors[0] += b'\xff' * (sector_size - len(sectors[0]))
    header = bytearray(sector_size)
    header[:8] = formats.OLE_SIGNATURE
    struct.pack_into('<5H', header, 24, 0x3e, version, 0xfffe, 9 if version == 3 else 12, 6)
    struct.pack_into('<9I', header, 40, 0 if version == 3 else directory_sectors, 1, 1, 0,
                     4096, mini_fat_start, len(mini_table) // sector_size, formats.END, 0)
    struct.pack_into('<109I', header, 76, 0, *([formats.FREE] * 108))
    return bytes(header) + b''.join(sectors)


def pdf(info=None, version='1.7', extra_objects=(), trailer_extra=b'', catalog_extra=b''):
    """A minimal standards-shaped PDF with real offsets and a classic xref."""
    if info is None:
        info = b'<< /Title (Literal title) /Author (Recorded Author) /CreationDate (D:20200101) >>'
    objects = [b'<< /Type /Catalog /Pages 2 0 R ' + catalog_extra + b' >>', b'<< /Type /Pages /Kids [] /Count 0 >>', info]
    objects.extend(extra_objects)
    data = ('%PDF-' + version + '\n').encode('ascii') + b'%\xe2\xe3\xcf\xd3\n'
    offsets = []
    for index, blob in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(index).encode() + b' 0 obj\n' + blob + b'\nendobj\n'
    start = len(data)
    data += b'xref\n0 ' + str(len(objects) + 1).encode() + b'\n0000000000 65535 f \n'
    data += b''.join(('%010d 00000 n \n' % offset).encode() for offset in offsets)
    data += (b'trailer\n<< /Size ' + str(len(objects) + 1).encode() + b' /Root 1 0 R /Info 3 0 R ' + trailer_extra +
             b' >>\nstartxref\n' + str(start).encode() + b'\n%%EOF\n')
    return data


def compressed_pdf(padding=0):
    """ISO 32000 object and cross-reference streams, including compressed Info."""
    objects = [(1, b'<< /Type /Catalog /Pages 2 0 R >>'), (2, b'<< /Type /Pages /Kids [] /Count 0 >>')]
    compressed = zlib.compress(b'3 0 << /Title (Compressed Info) >>' + b' ' * padding)
    objects.append((4, b'<< /Type /ObjStm /N 1 /First 4 /Length ' + str(len(compressed)).encode() +
                    b' /Filter /FlateDecode >>\nstream\n' + compressed + b'\nendstream'))
    raw, offsets = b'%PDF-1.7\n', {}
    for number, blob in objects:
        offsets[number] = len(raw)
        raw += str(number).encode() + b' 0 obj\n' + blob + b'\nendobj\n'
    offsets[5] = len(raw)
    entries = [(0, 0, 65535), (1, offsets[1], 0), (1, offsets[2], 0), (2, 4, 0),
               (1, offsets[4], 0), (1, offsets[5], 0)]
    xref = b''.join(struct.pack('>BIH', *entry) for entry in entries)
    raw += (b'5 0 obj\n<< /Type /XRef /Size 6 /Root 1 0 R /Info 3 0 R /W [1 4 2] /Length ' +
            str(len(xref)).encode() + b' >>\nstream\n' + xref + b'\nendstream\nendobj\nstartxref\n' +
            str(offsets[5]).encode() + b'\n%%EOF\n')
    return raw


def values(parsed):
    return {role: value for role, value, _ in parsed['properties']}


class OleMetadata(unittest.TestCase):
    def test_legacy_root_document_folders_are_bounded_candidates_without_owner_inference(self):
        fs, ev = FS(), Evidence()
        fs.add('C:/My Documents/old.DOC', compound(office_streams()))
        fs.add('D:/My Documents/slides.PPS', compound(office_streams('ppt')))
        fs.add('C:/Other/not-selected.doc', compound(office_streams()))
        selected = list(reader.candidates(ev, SimpleNamespace(fs=fs)))
        self.assertEqual({str(path) for path in selected}, {'C:/My Documents/old.DOC', 'D:/My Documents/slides.PPS'})
        self.assertEqual(ev.problems, [])

    def test_real_cfb_mini_streams_identify_office_and_preserve_literal_metadata(self):
        for kind, expected in [('doc', 'Word Binary (OLE)'), ('xls', 'Excel BIFF8 (OLE)'),
                               ('ppt', 'PowerPoint Binary (OLE)')]:
            for version in (3, 4):
                with self.subTest(kind=kind, version=version):
                    result = formats.parse_ole(compound(office_streams(kind), version))
                    self.assertEqual(result['format'], expected)
                    observed = values(result)
                    self.assertEqual(observed['document.ole.title'], 'Résumé\0')
                    self.assertEqual(observed['document.ole.author'], 'Recorded Author')
                    self.assertEqual(observed['document.ole.created_filetime'], 132537600000000001)
                    self.assertEqual(observed['document.ole.last_saved_filetime'], 0)
                    self.assertIs(type(observed['document.ole.created_filetime']), int)
                    self.assertEqual(result['properties'][0][2]['property_id'], 2)
                    self.assertEqual(result['provenance']['property_part_sha256'], hashlib.sha256(summary()).hexdigest())

    @unittest.skipUnless(available('dissect.ole'), 'optional dissect reader not installed')
    def test_fixture_is_readable_by_the_independent_installed_cfb_parser(self):
        from dissect.ole.ole import OLE
        raw = compound(office_streams())
        parsed = OLE(io.BytesIO(raw))
        self.assertEqual(parsed.get(formats.SUMMARY_STREAM).open().read(), summary())

    def test_regular_stream_and_exact_unicode_codepages(self):
        for codepage, text in [(1200, ' 日本語 \0Ω'), (1251, 'Кириллица'), (65001, 'UTF-8 🧪')]:
            metadata = summary([(2, text), (4, '')], codepage)
            streams = office_streams(metadata=metadata)
            streams[-1] = (formats.SUMMARY_STREAM, metadata + bytes(4096 - len(metadata)))
            result = formats.parse_ole(compound(streams))
            self.assertEqual(values(result)['document.ole.title'], text)
            self.assertEqual(values(result)['document.ole.author'], '')

    def test_valid_difat_extension_and_a_cyclic_extension(self):
        base = compound(office_streams())
        header = bytearray(base[:512])
        sectors = [base[i:i + 512] for i in range(512, len(base), 512)]
        initial_count = len(sectors)
        fat_ids = [0] + list(range(initial_count, initial_count + 109))
        difat_id = initial_count + 109
        sectors.extend([bytes(512)] * 110)
        fat = list(struct.unpack('<128I', sectors[0]))[:initial_count] + [formats.FAT] * 109 + [formats.DIFAT]
        fat.extend([formats.FREE] * (110 * 128 - len(fat)))
        for index, sid in enumerate(fat_ids):
            sectors[sid] = struct.pack('<128I', *fat[index * 128:(index + 1) * 128])
        sectors[difat_id] = struct.pack('<128I', fat_ids[-1], *([formats.FREE] * 126), formats.END)
        struct.pack_into('<I', header, 44, 110)
        struct.pack_into('<II', header, 68, difat_id, 1)
        struct.pack_into('<109I', header, 76, *fat_ids[:109])
        raw = bytes(header) + b''.join(sectors)
        self.assertEqual(values(formats.parse_ole(raw))['document.ole.author'], 'Recorded Author')
        malformed = bytearray(raw)
        struct.pack_into('<I', malformed, 72, 2)
        struct.pack_into('<I', malformed, (difat_id + 2) * 512 - 4, difat_id)
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            formats.parse_ole(bytes(malformed))

    def test_absent_metadata_does_not_invent_properties(self):
        result = formats.parse_ole(compound(office_streams(metadata=False)))
        self.assertEqual(result['properties'], [])
        self.assertNotIn('property_part_sha256', result['provenance'])

    def test_stored_stream_name_case_and_byte_signature_are_retained(self):
        streams = [(name.lower(), raw) for name, raw in office_streams()]
        result = reader.parse_document(compound(streams))
        self.assertEqual(result['provenance']['main_part'], 'worddocument')
        self.assertEqual(result['properties'][0][2]['property_part'], formats.SUMMARY_STREAM.lower())

    def test_signature_stream_names_and_embedded_summary_do_not_establish_office(self):
        invalid = [compound([(formats.SUMMARY_STREAM, summary())]),
                   compound([('WordDocument', b'fake'), ('0Table', b'x'), (formats.SUMMARY_STREAM, summary())]),
                   compound(office_streams() + [('Workbook', b'other')])]
        for raw in invalid:
            with self.assertRaises(ValueError):
                formats.parse_ole(raw)
        # Root child 3 is a storage containing the metadata at SID 4; that nested
        # metadata cannot be attributed to the parent document.
        raw = bytearray(compound(office_streams(metadata=False) + [('ObjectPool', b''), (formats.SUMMARY_STREAM, summary())]))
        entry = 1024 + 3 * 128
        raw[entry + 66] = 1
        struct.pack_into('<II', raw, entry + 72, formats.FREE, 4)
        self.assertEqual(formats.parse_ole(bytes(raw))['properties'], [])

    def test_cyclic_overlapping_truncated_and_duplicate_containers_are_rejected(self):
        baseline = compound(office_streams())
        variants = []
        raw = bytearray(baseline)
        struct.pack_into('<I', raw, 512 + 4, 1)  # directory FAT self-cycle
        variants.append(bytes(raw))
        raw = bytearray(baseline)
        struct.pack_into('<I', raw, 1024 + 128 + 72, 1)  # directory sibling self-cycle
        variants.append(bytes(raw))
        raw = bytearray(baseline)
        first = struct.unpack_from('<I', raw, 1024 + 128 + 116)[0]
        struct.pack_into('<I', raw, 1024 + 2 * 128 + 116, first)  # table aliases main mini stream
        variants.append(bytes(raw))
        variants.extend([baseline[:-1], compound(office_streams() + [('worddocument', b'alias')])])
        for raw in variants:
            with self.assertRaises(ValueError):
                formats.parse_ole(raw)

    def test_property_type_duplicate_fmtid_and_invalid_unicode_are_rejected(self):
        invalid = [summary([(2, struct.pack('<II', 3, 42))]),
                   summary([(12, struct.pack('<II', 3, 42))]),
                   summary([(2, 'one'), (2, 'two')]),
                   summary([(2, struct.pack('<II', 0x1e, 4) + b'\x00\xd8\0\0')], 1200)]
        raw = bytearray(summary())
        raw[28] ^= 1
        invalid.append(bytes(raw))
        raw = bytearray(summary())
        struct.pack_into('<I', raw, 56, 0)  # CodePage PID is mandatory
        invalid.append(bytes(raw))
        for metadata in invalid:
            with self.assertRaises((ValueError, UnicodeError)):
                formats.parse_ole(compound(office_streams(metadata=metadata)))

    def test_file_property_and_directory_bounds_are_enforced(self):
        raw = compound(office_streams())
        for key, limit in [('MAX_FILE_BYTES', 1), ('MAX_PROPERTY_BYTES', 3), ('MAX_PROPERTIES', 1), ('MAX_CFB_ENTRIES', 2)]:
            with patch.object(formats, key, limit), self.assertRaises(ValueError):
                formats.parse_ole(raw)


@unittest.skipUnless(available('pypdf'), 'optional pypdf reader not installed')
class PdfMetadata(unittest.TestCase):
    def test_real_pdf_literal_strings_escapes_unicode_empty_and_dates(self):
        title = b'\xfe\xff' + ' 東京 Ω '.encode('utf-16-be')
        raw = pdf(b'<< /Title <' + title.hex().encode() + b'> /Author ( A\\(B\\)\\n ) /Subject () '
                  b'/Creator (Source app) /Producer (PDF producer) /CreationDate (not a date) >>')
        result = formats.parse_pdf(raw)
        observed = values(result)
        self.assertEqual(observed['document.pdf.title'], ' 東京 Ω ')
        self.assertEqual(observed['document.pdf.author'], ' A(B)\n ')
        self.assertEqual(observed['document.pdf.subject'], '')
        self.assertEqual(observed['document.pdf.created'], 'not a date')
        self.assertNotIn('document.pdf.modified', observed)
        self.assertEqual(result['properties'][0][2]['pdf_string_encoding'], 'UTF-16BE')
        self.assertEqual(result['properties'][0][2]['pdf_info_object'], '3 0 R')

    def test_pdf20_utf8_and_indirect_strings_have_precise_locators(self):
        encoded = b'\xef\xbb\xbf' + 'UTF-8 日本語'.encode('utf-8')
        raw = pdf(b'<< /Title 4 0 R >>', version='2.0', extra_objects=[b'<' + encoded.hex().encode() + b'>'])
        result = formats.parse_pdf(raw)
        self.assertEqual(values(result)['document.pdf.title'], 'UTF-8 日本語')
        locator = result['properties'][0][2]
        self.assertEqual(locator['pdf_field_object'], '4 0 R')
        self.assertEqual(locator['pdf_string_bytes_sha256'], hashlib.sha256(encoded).hexdigest())
        upgraded = pdf(b'<< /Title <' + encoded.hex().encode() + b'> >>', catalog_extra=b'/Version /2.0')
        self.assertEqual(values(formats.parse_pdf(upgraded))['document.pdf.title'], 'UTF-8 日本語')

    def test_real_compressed_object_and_xref_streams_obey_decoding_budget(self):
        self.assertEqual(values(formats.parse_pdf(compressed_pdf()))['document.pdf.title'], 'Compressed Info')
        with self.assertRaisesRegex(ValueError, 'LimitReachedError'):
            formats.parse_pdf(compressed_pdf(formats.MAX_METADATA_BYTES + 1))
        oversized = b'<< ' + b' '.join(b'/K' + str(i).encode() + b' (value)' for i in range(formats.MAX_PROPERTIES + 1)) + b' >>'
        with self.assertRaisesRegex(ValueError, 'maximum number of dictionary entries'):
            formats.parse_pdf(pdf(oversized))

    def test_pypdf_writer_fixture_is_accepted_without_execution_or_rendering(self):
        from pypdf import PdfWriter
        from pypdf.actions import JavaScript
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_metadata({'/Title': 'Writer fixture', '/ModDate': 'D:20200101000000+05\'30\''})
        writer.add_open_action(JavaScript('throw new Error("this must never execute")'))
        stream = io.BytesIO()
        writer.write(stream)
        result = formats.parse_pdf(stream.getvalue())
        self.assertEqual(values(result)['document.pdf.title'], 'Writer fixture')
        self.assertEqual(values(result)['document.pdf.modified'], 'D:20200101000000+05\'30\'')

    def test_wrong_native_types_duplicated_and_undecodable_values_are_rejected(self):
        for value in [b'42', b'true', b'/Name', b'null', b'[]', b'<<>>', b'<FEFFD800>', b'<FFFE4100>', b'<0041>']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                formats.parse_pdf(pdf(b'<< /Author ' + value + b' >>'))
        with self.assertRaises(ValueError):
            formats.parse_pdf(pdf(b'<< /Author (one) /Author (two) >>'))

    def test_absent_info_does_not_invent_absence_claims_or_xmp_values(self):
        raw = pdf().replace(b'/Info 3 0 R', b'           ')
        self.assertEqual(formats.parse_pdf(raw)['properties'], [])

    def test_encryption_invalid_structure_and_bounds_are_rejected(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt('password')
        stream = io.BytesIO()
        writer.write(stream)
        for raw in [stream.getvalue(), b'%PDF-1.7\nnot a PDF', pdf(b'42'), pdf().replace(b'/Catalog', b'/Unknown'), pdf()[:-15]]:
            with self.assertRaises(ValueError):
                formats.parse_pdf(raw)
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            formats.parse_pdf(pdf(b'<< /Title (' + b'A' * (formats.MAX_PROPERTY_BYTES + 1) + b') >>'))
        with patch.object(formats, 'MAX_FILE_BYTES', 1), self.assertRaises(ValueError):
            formats.parse_pdf(pdf())
        with patch.object(formats.subprocess, 'run', side_effect=subprocess.TimeoutExpired('reader', 10)):
            with self.assertRaisesRegex(ValueError, 'time limit'):
                formats.parse_pdf(pdf())

    def test_extraction_binds_full_hash_native_types_field_locators_and_origins(self):
        fs = FS()
        fixtures = {'old.doc': compound(office_streams()), 'print.pdf': pdf()}
        for filename, raw in fixtures.items():
            fs.add('C:/Users/Other/Documents/' + filename, raw)
        ev = Evidence()
        for snapshot, variant in [('base-volume', 'primary'), ('base-volume', 'historical'),
                                   ('vss:00000000-0000-0000-0000-000000000001', 'primary')]:
            context = {'examined_at': 1800000000000000, 'common': {'image': 'synthetic.E01', 'exhibit': 'OTHER',
                       'source_snapshot': snapshot, 'source_variant': variant}}
            reader.extract(ev, SimpleNamespace(fs=fs), context)
        self.assertEqual(ev.problems, [])
        subjects, roles, filetimes = set(), set(), []
        for kind, timestamp, _, _, value, serialized in ev.rows():
            provenance = json.loads(serialized)
            self.assertEqual(timestamp, 1800000000000000)
            self.assertEqual(provenance['timestamp_semantics'], 'examination_observation')
            filename = provenance['source_path'].rsplit('\\', 1)[1]
            self.assertEqual(provenance['container_sha256'], hashlib.sha256(fixtures[filename]).hexdigest())
            role = provenance['attribute_role']
            roles.add(role)
            if kind == 'attributeSubject':
                subjects.add(value)
            if role == 'document.ole.created_filetime':
                self.assertEqual(provenance['attribute_value_type'], 'integer')
                self.assertEqual(provenance['property_id'], 12)
                self.assertIn('stream_byte_offset', provenance)
                filetimes.append(provenance)
            if role == 'document.pdf.author':
                self.assertEqual(provenance['pdf_field'], '/Author')
        self.assertEqual(len(subjects), 6)
        self.assertTrue(filetimes)
        self.assertIn('document.source.path', roles)
        self.assertIn('document.source.format', roles)
        self.assertFalse(any(role.startswith('document.core.') or role.startswith('document.container.') for role in roles))

    def test_reader_rejects_mismatched_size_and_does_not_trust_extensions(self):
        fs = FS()
        fs.add('C:/Users/Other/Documents/not-real.pdf', b'arbitrary bytes')
        fs.add('C:/Users/Other/Documents/wrong-size.doc', compound(office_streams()), size=1)
        ev = Evidence()
        reader.extract(ev, SimpleNamespace(fs=fs), {'examined_at': 1, 'common': {}})
        self.assertEqual(ev.rows(), [])
        self.assertEqual(len(ev.problems), 2)


if __name__ == '__main__':
    unittest.main()
