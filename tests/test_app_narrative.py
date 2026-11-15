"""The key findings are sentences about what verified findings' own records say. Synthetic bundles only."""
import unittest
import html
from datetime import datetime, timezone

from app import narrative
from app.report import render_html

NEW_YORK = 'local time, converted from America/New_York'
MEANING = 'time recorded by the source'


def micro(*parts):
    return int(datetime(*parts, tzinfo=timezone.utc).timestamp()) * 1000000


def row(number, kind, obj, aux=None, t=0, **prov):
    if t:
        prov.setdefault('time_meaning', MEANING)
    return {'id': number, 'kind': kind, 't': t, 'obj_text': obj, 'aux_text': aux, 'prov': prov}


def finding(name, rows, **updates):
    value = {'finding_id': name, 'status': 'verified', 'strength': 'strong', 'cited_facts': rows}
    value.update(updates)
    return value


def bundle(*findings):
    return {'case': {'name': 'Synthetic'}, 'findings': list(findings)}


def sentences(story, key):
    return next((point['sentences'] for point in story['points'] if point['key'] == key), None)


def case():
    """One record or more of every type the summary describes."""
    first, second = micro(2024, 5, 6, 14, 0), micro(2024, 5, 7, 15, 30)
    usb = dict(device='Disk&Ven_Acme&Prod_Pocket_Drive&Rev_1.0', exhibit='PC', time_zone=NEW_YORK)
    return bundle(
        finding('F1', [
            row(1, 'systemSetting', 'computer name', 'LAB-PC'), row(2, 'systemSetting', 'computer name', 'lab-pc'),
            row(3, 'systemSetting', 'operating system', 'Example OS 9'), row(4, 'systemSetting', 'image md5', 'ab' * 16),
            row(5, 'accountSeen', 'worker', 'windows local account'), row(6, 'accountSeen', 'Admin', 'windows local account'),
            row(7, 'accountSeen', 'worker@example.org', 'google drive'),
            row(8, 'usbInsert', 'SER-1', None, first, **usb), row(9, 'usbInsert', 'SER-1', None, second, **usb),
            row(10, 'volumeOnDevice', 'SER-1', 'aa11', exhibit='USB-1'), row(11, 'volumeSeen', 'TRAVEL', 'AA11', first),
        ]),
        finding('F2', [
            row(20, 'folderOpened', r'\\server\share\plans', 'shell bag', first, account='worker'),
            row(21, 'folderOpened', r'\\server\share\plans\old', 'shell bag', first, account='worker'),
            row(22, 'folderOpened', r'E:\copy', 'shell bag', first, account='worker'),
            row(23, 'folderOpened', r'C:\Users\worker', 'shell bag', first, account='worker'),
            row(24, 'tag', r'\plans\budget.xlsx', 'confidential', rule='marker', source='deterministic'),
            row(25, 'tag', r'\copy\budget.xlsx', 'same size and last-modified time as a file elsewhere: 10 bytes', source='deterministic'),
            row(26, 'fileRenamed', r'C:\work\notes.txt', r'C:\work\notes-old.txt', first),
            row(27, 'fileRenamed', r'C:\work\budget.xlsx', r'C:\work\holiday.jpg', second),
            row(28, 'fileCreated', r'\lost\a.doc', 'unallocated space of device SER-1', first, exhibit='USB-1'),
        ]),
        finding('F3', [
            row(30, 'webSearch', 'weather today', 'chrome', first), row(31, 'webSearch', 'how to hide a file', 'iexplore', second),
            row(32, 'tag', 'how to hide a file', 'watch-list-search', source='deterministic'),
            row(33, 'fileDownloaded', r'C:\Users\worker\Downloads\wiper.exe', 'http://example.org/wiper.exe', second, account='worker'),
            row(34, 'programRun', 'WIPER.EXE', r'C:\Users\worker\Downloads', second, source='prefetch'),
            row(35, 'emailSent', 'Plans', 'from worker to friend', first), row(36, 'emailSent', 'RE: Plans', 'from friend to worker', second),
            row(37, 'cloudFile', 'budget.xlsx', 'google drive: uploaded', second),
            row(38, 'fileDeleted', r'\Users\worker\old.txt', 'AA11', second, artifact='Recycle Bin index $I1'),
            row(39, 'cdBurn', 'cdrom driver event 133', 'System event log', second),
            row(40, 'localSearch', 'budget', 'Windows Explorer search box', first, account='worker'),
            row(41, 'noteText', 'Call  me\n\nlater', 'Sticky Notes', first),
        ]))


class Narrative(unittest.TestCase):
    def test_every_topic_states_what_its_records_say(self):
        story = narrative.build(case())
        self.assertEqual(story['zone'], 'America/New_York' if story['zone'] else None)
        local = story['zone'] is not None                       # this system may not know the zone; then times are UTC
        self.assertEqual(sentences(story, 'computer'), ['The cited records give the computer name LAB-PC.',
                                                        'The cited records name the operating system Example OS 9.',
                                                        'The cited records contain 2 distinct local-account names: Admin and worker.',
                                                        'The records show the Google Drive account worker@example.org.'])
        self.assertEqual(next(point for point in story['points'] if point['key'] == 'computer')['records'], 6)
        self.assertEqual(sentences(story, 'devices'), ['The cited records include 2 USB identifier records.',
            'The cited records include 2 volume records.',
            'Matching identifiers do not establish physical-device identity or connection times.'])
        self.assertEqual(len(story['devices']), 4)
        self.assertEqual([item['record'] for item in story['devices']],
                         ['usbInsert #8', 'usbInsert #9', 'volumeOnDevice #10', 'volumeSeen #11'])
        self.assertEqual([item['label'] for item in story['devices']], ['', '', '', 'TRAVEL'])
        self.assertIn('2024-05-06 10:00' if local else '2024-05-06 14:00', story['devices'][0]['recorded_time'])
        self.assertEqual(sentences(story, 'folders'), [
            '2 cited folder records name a path under \\\\server\\share.',
            'The cited records also contain 1 folder-path reference with drive letter E:.'])
        self.assertEqual(sentences(story, 'files'), [
            '1 cited tag record carries the confidential label.', 'One example is budget.xlsx.',
            '1 cited tag record carries a same-size-and-time label.',
            'The cited records include 2 file-rename records.', '1 record pairs file names with different extensions.',
            'One recorded name pair: budget.xlsx and holiday.jpg.',
            '1 cited file-creation record carries the recovery-area label "unallocated space of device SER-1".'])
        web = sentences(story, 'web')
        self.assertEqual(web[0], 'The cited records include 2 web-search records (Chrome and Internet Explorer).')
        self.assertTrue(web[1].startswith('The retained source timestamps fall from 2024-05-06 '))
        self.assertEqual(web[2:], ['1 search text matches the search watch list.', 'These are examples: "how to hide a file".'])
        downloads = sentences(story, 'downloads')
        self.assertEqual(downloads[0], 'The cited download records name 1 distinct file basename: wiper.exe.')
        self.assertTrue(downloads[1].startswith('The retained source timestamps fall on 2024-05-07 at '))
        self.assertNotIn('started programs', ' '.join(downloads))
        mail = sentences(story, 'mail')
        self.assertEqual(mail[0], 'The cited records include 2 e-mail records.')
        self.assertTrue(mail[1].startswith('The retained source timestamps fall from 2024-05-06 '))
        self.assertEqual(mail[2:], ['1 record carries the address text "from friend to worker".',
                                    '1 record carries the address text "from worker to friend".',
                                    'These are the subjects: "Plans" and "RE: Plans".'])
        cloud = sentences(story, 'cloud')
        self.assertEqual(cloud[0], 'The cited Google Drive client records contain 1 distinct file name.')
        self.assertTrue(cloud[1].startswith('The retained source timestamps fall on 2024-05-07 at '))
        self.assertEqual(cloud[2:], ['1 record carries an uploaded status label.', 'The file names are: budget.xlsx.'])
        self.assertEqual(sentences(story, 'deleted')[0], 'The Recycle Bin index shows 1 deletion record.')
        self.assertEqual(sentences(story, 'disc')[0], 'The cited records include 1 optical-drive record.')
        self.assertEqual(sentences(story, 'notes'), ['The Windows Explorer search box contains the search text "budget".',
                                                     'A Sticky Notes file contains this text: "Call me later".'])
        # short sentences, and a count of the records and findings each topic rests on
        self.assertEqual([point['key'] for point in story['points']],
                         ['devices', 'folders', 'files', 'disc', 'mail', 'web', 'downloads', 'cloud', 'deleted', 'notes', 'computer'])
        for point in story['points']:
            self.assertEqual(sorted(point), ['findings', 'key', 'records', 'sentences', 'title'])
            self.assertGreater(point['records'], 0)
            self.assertGreater(point['findings'], 0)
            for sentence in point['sentences']:
                self.assertLessEqual(len(sentence.split()), 25, sentence)
                self.assertTrue(sentence.endswith('.'), sentence)

    def test_only_verified_findings_are_read_and_a_selection_narrows_them(self):
        data = case()
        data['findings'].append(finding('F9', [row(90, 'emailSent', 'Unchecked', 'from x to y', micro(2024, 5, 8, 9, 0))], status='rejected'))
        data['findings'].append({'finding_id': 'F10', 'cited_facts': [row(91, 'cdBurn', 'unchecked', 'log', micro(2024, 5, 8, 9, 0))]})
        story = narrative.build(data)
        self.assertEqual(story['findings'], 3)
        self.assertNotIn('Unchecked', str(story))
        self.assertEqual(sentences(story, 'mail')[0], 'The cited records include 2 e-mail records.')
        chosen = narrative.build(data, ids=['F3'])
        self.assertEqual(chosen['findings'], 1)
        self.assertEqual([point['key'] for point in chosen['points']], ['disc', 'mail', 'web', 'downloads', 'cloud', 'deleted', 'notes'])
        self.assertIsNone(sentences(chosen, 'computer'))
        self.assertIsNone(sentences(chosen, 'files'))
        self.assertEqual(chosen['devices'], [])
        self.assertEqual(chosen['zone'], story['zone'])            # the case clock does not depend on the selection
        self.assertEqual(narrative.build(data, ids=[])['points'], [])

    def test_empty_and_malformed_bundles_say_nothing(self):
        empty = {'schema_version': 1, 'zone': None, 'findings': 0, 'points': [], 'devices': [],
                 'disclaimer': narrative.DISCLAIMER}
        for value in ({}, None, [], {'findings': 'x'}, {'findings': [None, 3, {'status': 'verified'}]}):
            story = narrative.build(value)
            self.assertEqual(story['points'], [])
            self.assertEqual(story['devices'], [])
        self.assertEqual(narrative.build({}), empty)
        odd = bundle(finding('F1', [None, 'text', {'kind': 5}, {'kind': 'webSearch'}, {'kind': 'emailSent', 'obj_text': 7, 'aux_text': None, 't': 'soon', 'prov': 'x'},
                                    row(1, 'systemSetting', 'computer name', None)]))
        story = narrative.build(odd)
        self.assertEqual(sentences(story, 'mail'), ['The cited records include 1 e-mail record.'])
        self.assertEqual(sentences(story, 'web'), ['The cited records include 1 web-search record.'])
        self.assertIsNone(sentences(story, 'computer'))

    def test_reused_identifiers_and_cloned_serials_never_join_source_records(self):
        at = micro(2024, 5, 6, 14, 0)
        data = bundle(finding('Scoped', [
            row(1, 'usbInsert', 'REUSED', t=at, image='host-a', exhibit='PC1',
                time_meaning='registry last-write timestamp, not connection onset'),
            row(2, 'usbInsert', 'REUSED', t=at, image='host-b', exhibit='PC2'),
            row(3, 'volumeOnDevice', 'REUSED', 'CLONED', at, image='device-image', exhibit='RM1',
                timestamp_semantics='examination_observation'),
            row(4, 'volumeSeen', 'OTHER-LABEL', 'CLONED', at, image='other-image', exhibit='PC3'),
        ]))
        story = narrative.build(data)
        self.assertEqual(len(story['devices']), 4)
        self.assertEqual([item['serial'] for item in story['devices']], ['REUSED', 'REUSED', '', ''])
        self.assertEqual([item['volume'] for item in story['devices']], ['', '', 'CLONED', 'CLONED'])
        self.assertNotIn('OTHER-LABEL', str(story['devices'][2]))
        self.assertIn('image: host-a', story['devices'][0]['item'])
        self.assertIn('image: host-b', story['devices'][1]['item'])
        self.assertIn('not connection onset', story['devices'][0]['recorded_time'])
        self.assertTrue(story['devices'][2]['recorded_time'].startswith('No displayed source time;'))
        self.assertEqual(sentences(story, 'devices')[0], 'The cited records include 2 USB identifier records.')

    def test_folder_and_download_names_do_not_prove_actions_or_application_identity(self):
        for source in ('MuiCache', 'Shimcache', 'Prefetch'):
            with self.subTest(source=source):
                data = bundle(finding('Observations', [
                    row(1, 'folderOpened', r'\\server\share\folder', 'ShellBag', account='worker'),
                    row(2, 'fileDownloaded', r'C:\Downloads\tool.exe', 'https://example.invalid/tool.exe',
                        account='worker', image='host-a'),
                    row(3, 'programRun', 'tool.exe', r'D:\Unrelated\tool.exe', source=source, image='host-b'),
                ]))
                story = narrative.build(data)
                text = ' '.join(sentence for point in story['points'] for sentence in point['sentences'])
                for forbidden in ('opened', 'downloaded', 'started', 'executed', 'The account'):
                    self.assertNotIn(forbidden, text)
                self.assertIn('folder record names a path', text)
                self.assertIn('download records name 1 distinct file basename', text)
                self.assertEqual(next(point['records'] for point in story['points'] if point['key'] == 'downloads'), 1)

    def test_recovery_area_labels_are_not_physical_source_attribution(self):
        story = narrative.build(bundle(finding('Recovery', [
            row(1, 'fileCreated', 'old.txt', 'unallocated space of device SAME', exhibit='DISPUTED'),
        ])))
        text = ' '.join(sentences(story, 'files'))
        self.assertIn('carries the recovery-area label "unallocated space of device SAME"', text)
        self.assertNotIn('space of DISPUTED contains', text)
        self.assertNotIn('reformatted', text)

    def test_html_summary_keeps_record_labels_and_exact_certificate_limitations(self):
        sentence = 'The records carry matching identifiers. This does not establish the same physical device.'
        data = bundle(finding('Qualified', [
            row(1, 'usbInsert', '<same-id>', t=micro(2024, 5, 6, 14, 0),
                image='<script>not markup</script>', time_meaning='key last write, not connection onset'),
        ], english=sentence))
        rendered = render_html(data)
        self.assertIn(html.escape(sentence), rendered)
        self.assertIn(html.escape(narrative.DISCLAIMER), rendered)
        self.assertIn('Record timestamp', rendered)
        self.assertIn('1 USB identifier record', rendered)
        self.assertNotIn('First connection', rendered)
        self.assertNotIn('Last connection', rendered)
        self.assertNotIn('<script>not markup</script>', rendered)
        self.assertIn('&lt;script&gt;not markup&lt;/script&gt;', rendered)

    def test_typed_usb_only_findings_remain_visible_without_legacy_summary_rows(self):
        sentence = 'The USB source tuple records identifier USBSTOR\\INSTANCE-A. This does not establish physical-device identity.'
        data = bundle(finding('TypedUsb', [
            row(1, 'attributeSubject', 'scoped-attribute', 'image-a:USBSTOR\\INSTANCE-A'),
            row(2, 'roleUsbDeviceInstanceId', 'scoped-attribute', 'usb.device_instance_id'),
            row(3, 'attributeTextValue', 'scoped-attribute', '"USBSTOR\\\\INSTANCE-A"'),
        ], english=sentence))
        story = narrative.build(data)
        self.assertEqual(story['points'], [])
        self.assertEqual(story['devices'], [])
        rendered = render_html(data)
        self.assertIn(html.escape(sentence), rendered)
        self.assertIn('This does not establish absence of evidence.', rendered)
        self.assertIn('usb.device_instance_id', rendered)


if __name__ == '__main__':
    unittest.main()
