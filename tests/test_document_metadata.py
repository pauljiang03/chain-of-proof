import hashlib
import io
import json
import unittest
import warnings
import zipfile
from types import SimpleNamespace
from unittest.mock import patch

from extractor import document_metadata as reader
from extractor.store import Evidence
from tests.test_inventory import FS


def package_parts(core=None):
    if core is None:
        core = ('<cp:coreProperties xmlns:cp="' + reader.CORE_NS + '" xmlns:dc="' + reader.DC_NS +
                '" xmlns:dcterms="' + reader.DCTERMS_NS + '"><dc:title> Literal title </dc:title>'
                '<dc:creator>Recorded creator</dc:creator><dc:subject/>'
                '<dcterms:created>2015-03-25T01:02:03Z</dcterms:created></cp:coreProperties>')
    return {
        '[Content_Types].xml': ('<Types xmlns="' + reader.TYPE_NS + '">'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="' + reader.CORE_TYPE + '"/></Types>'),
        '_rels/.rels': ('<Relationships xmlns="' + reader.REL_NS + '">'
            '<Relationship Id="main" Type="' + reader.OFFICE_REL + '" Target="word/document.xml"/>'
            '<Relationship Id="core" Type="' + reader.CORE_REL + '" Target="docProps/core.xml"/></Relationships>'),
        'word/document.xml': '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>',
        'docProps/core.xml': core,
    }


def document(parts=None, extra=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as package:
        for name, value in (parts or package_parts()).items():
            package.writestr(name, value)
        if extra:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                package.writestr(*extra)
    return stream.getvalue()


class DocumentMetadata(unittest.TestCase):
    def test_literal_properties_and_empty_are_preserved_without_inventing_missing_values(self):
        result = reader.parse_ooxml(document())
        values = {role: value for role, value, _ in result['properties']}
        self.assertEqual(result['format'], 'WordprocessingML')
        self.assertEqual(values['document.core.title'], ' Literal title ')
        self.assertEqual(values['document.core.subject'], '')
        self.assertEqual(values['document.core.created'], '2015-03-25T01:02:03Z')
        self.assertNotIn('document.core.modified', values)

    def test_a_filename_or_core_xml_alone_does_not_establish_document_type(self):
        parts = package_parts()
        del parts['_rels/.rels']
        with self.assertRaises(KeyError):
            reader.parse_ooxml(document(parts))
        parts = package_parts()
        parts['word/document.xml'] = '<unrelated/>'
        with self.assertRaisesRegex(ValueError, 'main XML root'):
            reader.parse_ooxml(document(parts))

    def test_duplicate_nested_and_wrong_namespace_properties_are_not_promoted(self):
        for core in ('<cp:coreProperties xmlns:cp="' + reader.CORE_NS + '" xmlns:dc="' + reader.DC_NS + '">'
                     '<dc:creator>A</dc:creator><dc:creator>B</dc:creator></cp:coreProperties>',
                     '<cp:coreProperties xmlns:cp="' + reader.CORE_NS + '" xmlns:dc="' + reader.DC_NS + '">'
                     '<dc:creator><nested>A</nested></dc:creator></cp:coreProperties>'):
            with self.assertRaisesRegex(ValueError, 'duplicate or nested'):
                reader.parse_ooxml(document(package_parts(core)))
        core = '<cp:coreProperties xmlns:cp="' + reader.CORE_NS + '"><creator>Unrelated</creator></cp:coreProperties>'
        self.assertEqual(reader.parse_ooxml(document(package_parts(core)))['properties'], [])

    def test_external_traversing_and_ambiguous_relationships_are_refused(self):
        for change in ('Target="../outside.xml"', 'Target="https://example.test/core.xml"',
                       'Target="docProps/core.xml" TargetMode="External"'):
            parts = package_parts()
            parts['_rels/.rels'] = parts['_rels/.rels'].replace('Target="docProps/core.xml"', change)
            with self.assertRaises(ValueError):
                reader.parse_ooxml(document(parts))
        parts = package_parts()
        parts['_rels/.rels'] = parts['_rels/.rels'].replace('Id="core"', 'Id="main"')
        with self.assertRaisesRegex(ValueError, 'duplicate relationship'):
            reader.parse_ooxml(document(parts))

    def test_duplicate_zip_names_dtd_and_oversize_xml_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'duplicate package'):
            reader.parse_ooxml(document(extra=('docProps/core.xml', '<different/>')))
        for encoding in ('utf-8', 'utf-16'):
            parts = package_parts()
            parts['docProps/core.xml'] = ('<!DOCTYPE core [<!ENTITY x "expanded">]>' + parts['docProps/core.xml']).encode(encoding)
            with self.assertRaisesRegex(ValueError, 'DTD/entity'):
                reader.parse_ooxml(document(parts))
        with patch.object(reader, 'MAX_XML_BYTES', 32), self.assertRaisesRegex(ValueError, 'XML part exceeds'):
            reader.parse_ooxml(document())

    def test_no_core_relationship_yields_no_metadata_or_absence_claim(self):
        parts = package_parts()
        parts['_rels/.rels'] = ('<Relationships xmlns="' + reader.REL_NS + '"><Relationship Id="main" Type="' +
                               reader.OFFICE_REL + '" Target="word/document.xml"/></Relationships>')
        result = reader.parse_ooxml(document(parts))
        self.assertEqual(result['properties'], [])
        self.assertIsNone(result['core_part'])

    def test_reader_binds_full_bytes_scope_locator_and_examination_time(self):
        fs = FS()
        raw = document()
        fs.add('C:/Users/Other/Documents/evidence.docx', raw)
        target = SimpleNamespace(fs=fs)
        ev = Evidence()
        for snapshot in ('base-volume', 'vss:00000000-0000-0000-0000-000000000001'):
            ctx = {'examined_at': 1800000000000000, 'common': {
                'image': 'synthetic.E01', 'exhibit': 'OTHER', 'source_snapshot': snapshot, 'source_variant': 'primary'}}
            reader.extract(ev, target, ctx)
        self.assertEqual(ev.problems, [])
        subjects, roles = set(), set()
        for kind, timestamp, _, _, value, serialized in ev.rows():
            provenance = json.loads(serialized)
            self.assertEqual(timestamp, 1800000000000000)
            self.assertEqual(provenance['container_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(provenance['source_path'], r'C:\Users\Other\Documents\evidence.docx')
            if kind == 'attributeSubject':
                subjects.add(value)
            roles.add(provenance['attribute_role'])
        self.assertEqual(len(subjects), 2)
        self.assertIn('document.core.creator', roles)
        self.assertIn('document.container.path', roles)

    def test_bad_package_size_or_symlink_does_not_yield_typed_document(self):
        for metadata in ({'size': 1}, {'symlink': True}):
            fs = FS()
            fs.add('C:/Users/Other/Documents/evidence.docx', document(), **metadata)
            ev = Evidence()
            reader.extract(ev, SimpleNamespace(fs=fs), {'examined_at': 1, 'common': {}})
            self.assertEqual(ev.rows(), [])
            if 'size' in metadata:
                self.assertTrue(ev.problems)


if __name__ == '__main__':
    unittest.main()
