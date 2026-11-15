"""Source-declared MAPI encodings, without locale guesses or HTML rendering."""
import struct
import json
import unittest
from types import SimpleNamespace as NS

from extractor import mail_content as mc
from extractor import artifact_containers as ac
from extractor.store import Evidence
from checker.catalog import ROLES
from tests.test_artifact_containers import message, prop


def cp(value, field=0x3FDE):
    return prop(field, struct.pack('<I', value), 0x0003)


class MailContent(unittest.TestCase):
    def test_string8_subject_and_body_use_their_own_recorded_code_pages(self):
        msg = message([prop(0x0037, b'caf\xe9\0', 0x001E), cp(1252, 0x3FFD),
                       prop(0x1000, '日本語\n'.encode('cp932'), 0x001E), cp(932)])
        subject = mc.text_property(msg, 0x0037)
        body = mc.text_property(msg, 0x1000)
        self.assertEqual((subject['role'], subject['value']), ('mail.message.subject_string8', 'café'))
        self.assertEqual(body['value'], '日本語\n')
        self.assertEqual(subject['provenance']['codepage_locator']['property_id'], 0x3FFD)
        self.assertEqual(body['provenance']['codepage_locator']['property_id'], 0x3FDE)
        self.assertEqual(body['provenance']['property_byte_length'], len('日本語\n'.encode('cp932')))

    def test_unicode_needs_no_codepage_and_preserves_empty_newlines(self):
        for value in ('', 'Space \r\nΩ '):
            found = mc.text_property(message([prop(0x1000, (value + '\0').encode('utf-16-le'))]), 0x1000)
            self.assertEqual(found['value'], value)
            self.assertEqual(found['role'], 'mail.message.body_unicode')

    def test_html_is_literal_markup_with_declared_encoding_and_matching_bom(self):
        value = '<p>café &amp; text</p><script>ignored_as_code()</script>'
        for codepage, encoding, bom in ((65001, 'utf-8', b'\xef\xbb\xbf'),
                                         (1200, 'utf-16-le', b'\xff\xfe'),
                                         (1252, 'cp1252', b'')):
            found = mc.text_property(message([prop(0x1013, bom + value.encode(encoding), 0x0102), cp(codepage)]), 0x1013)
            self.assertEqual(found['value'], value)
            self.assertEqual(found['role'], 'mail.message.body_html')
            self.assertIn('no rendering', found['provenance']['html_policy'])

    def test_zero_message_codepage_uses_only_explicit_containing_folder(self):
        msg = message([prop(0x0037, b'caf\xe9', 0x001E), cp(0, 0x3FFD)])
        folder = message([cp(1252, 0x3FFD)])
        found = mc.text_property(msg, 0x0037, folder=folder)
        self.assertEqual(found['value'], 'café')
        self.assertEqual(found['provenance']['codepage_scope'], 'containing folder')
        with self.assertRaises(ValueError):
            mc.text_property(msg, 0x0037, folder=NS())

    def test_missing_wrong_duplicate_or_unsupported_encoding_stays_unavailable(self):
        bad_sets = [[], [cp(0)], [cp(999999)], [cp(1252), cp(1252)],
                    [prop(0x3FDE, b'1252', 0x001E)], [prop(0x3FDE, b'\0', 0x0003)],
                    [cp(1200)], [cp(65001)]]
        for extras in bad_sets:
            with self.subTest(extras=extras), self.assertRaises((ValueError, UnicodeError)):
                mc.text_property(message([prop(0x1000, b'\xff', 0x001E), *extras]), 0x1000)
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            mc.text_property(message([prop(0x1013, b'\xef\xbb\xbf<p>x</p>', 0x0102), cp(1252)]), 0x1013)

    def test_property_identity_types_and_bounds_are_checked(self):
        for entries in ([prop(0x1000, b'x', 0x001F)],
                        [prop(0x1000, b'\x00\xd8', 0x001F)],
                        [prop(0x1000, b'a\0b', 0x001E), cp(1252)],
                        [prop(0x1000, b'x', 0x0102)],
                        [prop(0x1000, b'\0\0'), prop(0x1000, b'\0\0')]):
            with self.subTest(entries=entries), self.assertRaises((ValueError, UnicodeError)):
                mc.text_property(message(entries), 0x1000)
        self.assertIsNone(mc.text_property(message([]), 0x1000))
        bad = message([])
        bad.number_of_record_sets = 65
        with self.assertRaises(ValueError):
            mc.text_property(bad, 0x1000)

    def test_duplicate_properties_are_rejected_before_reading_more_bytes(self):
        class UnreadDuplicate:
            entry_type = 0x1000
            @property
            def data(self):
                raise AssertionError('duplicate property bytes must not be materialized')
        first = prop(0x1000, 'first'.encode('utf-16-le'))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            mc.text_property(message([first, UnreadDuplicate(), UnreadDuplicate()]), 0x1000)

    def test_real_typed_emission_keeps_same_message_and_examination_time(self):
        msg = message([prop(0x0037, b'subject', 0x001E), cp(1252, 0x3FFD),
                       prop(0x1000, b'body', 0x001E), cp(65001),
                       prop(0x1013, b'<p>body</p>', 0x0102)])
        folder = NS(identifier=7, number_of_sub_messages=1, number_of_sub_folders=0,
                    get_sub_message=lambda index: msg)
        box = NS(get_root_folder=lambda: folder)
        ev = Evidence()
        provenance = dict(artifact='C:\\mail.pst', source_path='C:\\mail.pst', container_sha256='a' * 64,
                          image='synthetic.E01', exhibit='PC', source_snapshot='base-volume', source_variant='primary')
        ac.mail_fields(ev, box, 'scoped-container-subject', provenance, 12345)
        self.assertEqual(ev.problems, [])
        rows = list(ev.rows())
        self.assertEqual(len(rows), 9)
        self.assertEqual({row[1] for row in rows}, {12345})
        subjects = {row[4] for row in rows if row[0] == 'attributeSubject'}
        self.assertEqual(len(subjects), 1)
        roles = {json.loads(row[5])['attribute_role'] for row in rows}
        self.assertEqual(roles, {'mail.message.subject_string8', 'mail.message.body_string8', 'mail.message.body_html'})
        self.assertTrue(all(role in ROLES for role in roles))


if __name__ == '__main__':
    unittest.main()
