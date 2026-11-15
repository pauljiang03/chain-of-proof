"""The key findings are sentences about what verified findings' own records say. Synthetic bundles only."""
import unittest
from datetime import datetime, timezone

from app import narrative

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
        self.assertEqual(sentences(story, 'computer'), ['The computer name is LAB-PC.', 'The operating system is Example OS 9.',
                                                        'The computer has 2 local accounts: Admin and worker.',
                                                        'The records show the Google Drive account worker@example.org.'])
        self.assertEqual(next(point for point in story['points'] if point['key'] == 'computer')['records'], 6)
        self.assertEqual(sentences(story, 'devices'), ['The computer records show connections of 1 USB storage device.'])
        self.assertEqual(story['devices'], [{
            'item': 'USB-1', 'device': 'Acme Pocket Drive', 'serial': 'SER-1', 'label': 'TRAVEL', 'volume': 'AA11',
            'first': '2024-05-06 10:00' if local else '2024-05-06 14:00', 'last': '2024-05-07 11:30' if local else '2024-05-07 15:30'}])
        self.assertEqual(sentences(story, 'folders'), [
            'The account "worker" opened 2 folders on the network location \\\\server\\share.',
            'The records also show 1 opened folder on drive E:.'])
        self.assertEqual(sentences(story, 'files'), [
            '1 path contains the confidential-project marker.', 'One example is budget.xlsx.',
            '1 file entry has the same size and last-modified time as a file in a different location.',
            'The file system journal shows 2 file renames.', '1 rename changed the file name extension.',
            'One example: budget.xlsx became holiday.jpg.', 'The unallocated space of USB-1 contains 1 recovered file entry.'])
        web = sentences(story, 'web')
        self.assertTrue(web[0].startswith('The browser history contains 2 web searches (Chrome and Internet Explorer) from 2024-05-06 '))
        self.assertEqual(web[1:], ['1 search text matches the search watch list.', 'These are examples: "how to hide a file".'])
        downloads = sentences(story, 'downloads')
        self.assertTrue(downloads[0].startswith('The account "worker" downloaded 1 file on 2024-05-07 at '))
        self.assertTrue(downloads[0].endswith(': wiper.exe.'))
        self.assertEqual(downloads[1], '1 of these files appears in the records of started programs.')
        mail = sentences(story, 'mail')
        self.assertTrue(mail[0].startswith('The mailbox contains 2 e-mail messages from 2024-05-06 '))
        self.assertEqual(mail[1:], ['1 message is from friend to worker.', '1 message is from worker to friend.',
                                    'These are the subjects: "Plans".'])
        cloud = sentences(story, 'cloud')
        self.assertTrue(cloud[0].startswith('The Google Drive client log shows 1 file event for 1 file on 2024-05-07 at '))
        self.assertEqual(cloud[1:], ['1 event is an upload.', 'The file names are: budget.xlsx.'])
        self.assertTrue(sentences(story, 'deleted')[0].startswith('The Recycle Bin index shows 1 deleted item on 2024-05-07 at '))
        self.assertTrue(sentences(story, 'disc')[0].startswith('The records show 1 trace of disc writing on 2024-05-07 at '))
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
        self.assertTrue(sentences(story, 'mail')[0].startswith('The mailbox contains 2 e-mail messages'))
        chosen = narrative.build(data, ids=['F3'])
        self.assertEqual(chosen['findings'], 1)
        self.assertEqual([point['key'] for point in chosen['points']], ['disc', 'mail', 'web', 'downloads', 'cloud', 'deleted', 'notes'])
        self.assertIsNone(sentences(chosen, 'computer'))
        self.assertIsNone(sentences(chosen, 'files'))
        self.assertEqual(chosen['devices'], [])
        self.assertEqual(chosen['zone'], story['zone'])            # the case clock does not depend on the selection
        self.assertEqual(narrative.build(data, ids=[])['points'], [])

    def test_lead_tells_what_happened_in_date_order(self):
        lead = narrative.build(case())['lead']
        self.assertEqual(lead[0], 'The computer is LAB-PC.')
        mail = lead.index('From 2024-05-06 to 2024-05-07, "friend" and "worker" exchanged 2 e-mails.')
        folders = lead.index('By 2024-05-06, the account "worker" had opened 2 folders on the network location \\\\server\\share.')
        self.assertLess(mail, folders)
        self.assertIn('On 2024-05-07, 1 file went to the Recycle Bin.', lead)
        self.assertFalse(any('downloaded' in sentence for sentence in lead))   # installers are for the report
        detail = narrative.build(case())['lead_detail']
        self.assertIn('On 2024-05-07 at 11:30, the account "worker" downloaded wiper.exe.', detail)
        self.assertIn('From 2024-05-06 10:00 to 2024-05-07 11:30, "friend" and "worker" exchanged 2 e-mails. '
                      'The first subject is "Plans" and the last subject is "RE: Plans".', detail)
        self.assertGreater(len(' '.join(detail)), len(' '.join(lead)))
        self.assertEqual(narrative.build({})['lead'], [])
        data = case()
        data['findings'].append(finding('F9', [
            row(90, 'programRun', 'Wiper.exe', 'C:\\Tools\\Wiper.exe', t=micro(2024, 5, 8, 9), account='worker',
                time_meaning='last run time stored in the UserAssist entry'),
            row(91, 'sessionEvent', 'shutdown', None, t=micro(2024, 5, 8, 10), time_meaning='time the event was logged'),
            row(92, 'tag', 'wiper', 'watch-list-search')]))
        lead = narrative.build(data)['lead']
        self.assertIn('On 2024-05-08, the account "worker" started Wiper.', lead)
        self.assertIn('On 2024-05-08, the computer shut down for the last time in the records.', lead)

    def test_uploads_name_the_confidential_files_they_were_renamed_from(self):
        data = bundle(finding('F1', [
            row(1, 'tag', '\\USB1\\[topsecret]_plan.docx', 'confidential'),
            row(2, 'tag', '\\[topsecret]_prices.xlsx', 'confidential'),
            row(3, 'fileRenamed', 'C:\\x\\[topsecret]_prices.xlsx', 'C:\\x\\holiday.jpg', t=micro(2024, 5, 6, 10)),
            row(4, 'fileRenamed', 'C:\\x\\notes.txt', 'C:\\x\\notes.md', t=micro(2024, 5, 6, 10, 1)),
            row(5, 'cloudFile', 'holiday.jpg', 'google drive: uploaded', t=micro(2024, 5, 6, 10, 5)),
            row(6, 'usbInsert', 'SER1', None, t=micro(2024, 5, 6, 9), exhibit='PC'),
            row(7, 'fileCreated', 'x', 'unallocated space of device SER1', exhibit='USB1')]))
        lead = narrative.build(data)['lead']
        self.assertIn('On 2024-05-06, 1 confidential file got a new name with a different file type, '
                      'for example [topsecret]_prices.xlsx became holiday.jpg.', lead)
        self.assertIn('On 2024-05-06, Google Drive uploaded holiday.jpg. Before a rename, this file had the name [topsecret]_prices.xlsx.', lead)
        self.assertFalse(any('notes.md' in sentence for sentence in lead))     # a rename without the marker is not news
        self.assertIn('2 file paths carry the confidential-project marker, 1 on USB1.', lead)
        cloud = sentences(narrative.build(data), 'cloud')
        self.assertIn('Before a rename, holiday.jpg had the name [topsecret]_prices.xlsx.', cloud)

    def test_investigator_summary_leads_the_whole_case_only(self):
        data = case()
        computed = narrative.build(data)
        self.assertEqual(computed['lead_by'], 'records')
        self.assertTrue(computed['lead'])
        data['case'] = {'name': 'x', 'case_summary': '  The USB device   was connected.\n'}
        story = narrative.build(data)
        self.assertEqual((story['lead'], story['lead_by']), (['The USB device was connected.'], 'investigator'))
        self.assertEqual(narrative.build(data, ids=['F3'])['lead_by'], 'records')   # a selection gets the computed text
        for value in (None, 7, '', '   ', ['x']):
            data['case']['case_summary'] = value
            self.assertEqual(narrative.build(data)['lead_by'], 'records')

    def test_empty_and_malformed_bundles_say_nothing(self):
        empty = {'schema_version': 1, 'zone': None, 'findings': 0, 'lead': [], 'lead_by': 'records', 'lead_detail': [],
                 'points': [], 'devices': []}
        for value in ({}, None, [], {'findings': 'x'}, {'findings': [None, 3, {'status': 'verified'}]}):
            story = narrative.build(value)
            self.assertEqual(story['points'], [])
            self.assertEqual(story['devices'], [])
        self.assertEqual(narrative.build({}), empty)
        odd = bundle(finding('F1', [None, 'text', {'kind': 5}, {'kind': 'webSearch'}, {'kind': 'emailSent', 'obj_text': 7, 'aux_text': None, 't': 'soon', 'prov': 'x'},
                                    row(1, 'systemSetting', 'computer name', None)]))
        story = narrative.build(odd)
        self.assertEqual(sentences(story, 'mail'), ['The mailbox contains 1 e-mail message.'])
        self.assertEqual(sentences(story, 'web'), ['The browser history contains 1 web search.'])
        self.assertIsNone(sentences(story, 'computer'))


if __name__ == '__main__':
    unittest.main()
