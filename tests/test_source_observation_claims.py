"""Retained records certify observations, never an invented stronger event.

Synthetic fixtures in the readers' provenance shapes, checked by the real Lean kernel and replay.
"""
import copy
from pathlib import Path
import tempfile
import unittest

from checker import claims
from checker.check import check
from checker.catalog import ROLES
from checker.facts import Fact, FactSource, JsonFacts, KINDS
from extractor.attributes import emit_attribute
from extractor.store import Evidence
from verifier.verify import verify


class ObservationSource(FactSource):
    def __init__(self):
        self.strings = {0: '(none)', 1: r'\documents\plan.txt', 2: 'VOL-A',
                        3: 'Fixture editor', 4: '1.2', 5: 'Message subject',
                        6: 'from Display A to Display B', 7: 'DEVICE-A',
                        8: 'Volume label', 9: 'VOL-B', 10: 'DEVICE-B', 11: 'recovery area'}
        self.rows = [
            Fact(1, 'lnkTarget', 10_000_000, 1, 1, 2, {
                'artifact': r'C:\Users\Fixture\Recent\plan.lnk',
                'time_meaning': 'shortcut file last-modified time (last open via the shell)'}),
            Fact(2, 'lnkTarget', 20_000_000, 1, 1, 0, {}),
            Fact(3, 'programInstalled', 30_000_000, 1, 3, 4, {
                'artifact': r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Fixture',
                'time_meaning': 'last-write time of the uninstall entry'}),
            Fact(4, 'emailSent', 40_000_000, 1, 5, 6, {
                'artifact': r'Fixture.ost folder Inbox', 'folder': 'Inbox',
                'sender_address': None, 'sender_address_status': 'missing',
                'time_meaning': 'client submit time stored in the message'}),
            Fact(5, 'volumeMount', 1_000_000, 1, 7, 2),
            Fact(6, 'volumeOnDevice', 50_000_000, 1, 7, 2),
            Fact(7, 'volumeSeen', 9_000_000, 1, 8, 2, {
                'artifact': r'SYSTEM\ControlSet001\Control\EMDMgmt',
                'time_meaning': 'registry key last-write time'}),
            Fact(8, 'volumeMount', 1_000_000, 1, 7, 9),
            Fact(9, 'programInstalled', 60_000_000, 1, 3, 4, {
                'artifact': 'Application.evtx event 11707',
                'time_meaning': 'time the Windows Installer logged the completed installation'}),
            Fact(10, 'programInstalled', 70_000_000, 86_400_000_000, 3, 4, {
                'artifact': 'SOFTWARE Installer product record',
                'time_meaning': 'InstallDate value: a date with no time of day'}),
            Fact(11, 'usbInsert', 80_000_000, 1, 7, 0, {
                'artifact': r'HKLM\SYSTEM\CurrentControlSet\Enum\USBSTOR\Fixture\DEVICE-A',
                'device': 'Fixture', 'time_meaning': 'registry key last-write time'}),
            Fact(12, 'usbInsert', 90_000_000, 1, 7, 0, {}),
            Fact(13, 'unallocatedOnDevice', 100_000_000, 1, 7, 11),
            Fact(14, 'volumeMount', 1_000_000, 1, 10, 2),
            Fact(15, 'usbInsert', 110_000_000, 1000, 7, 0, {
                'artifact': r'C:\Windows\inf\setupapi.dev.log line 1',
                'time_meaning': 'device install section start (first connection)'}),
            Fact(16, 'volumeOnDevice', 50_000_000, 1, 10, 2),
        ]

    def get(self, ids):
        return {row.id: row for row in self.rows if row.id in ids}

    def all(self):
        return self.rows

    def string(self, sid):
        return self.strings[sid]


class SourceObservationClaims(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.source = ObservationSource()
        self.sequence = 0

    def certify(self, claim, accepted=True):
        self.sequence += 1
        cert = check(claim, f'Observation{self.sequence}', self.source, out_dir=self.path)
        self.assertEqual(cert['status'], 'verified' if accepted else 'rejected', cert)
        if accepted:
            self.assertEqual(cert['trust_tier'], 'kernel')
            self.assertEqual(cert['axioms'], [])
            self.assertEqual(cert['strength'], 'strong')  # strong about the cited record
            self.assertEqual(verify(cert, self.source), [])
        return cert

    def test_registration_times_retain_each_source_meaning(self):
        for fid in (3, 9, 10):
            with self.subTest(fid=fid):
                text = self.certify({'programInstalledAt': [fid]})['english']
                self.assertIn(self.source.get([fid])[fid].prov['time_meaning'], text)
                self.assertIn('source artifact:', text)
                self.assertIn('software-registration or installer record naming Fixture editor 1.2', text)
                self.assertIn('does not by itself establish the actual installation time', text)
                self.assertNotIn('is recorded as installed (', text)

    def test_message_metadata_does_not_claim_sending_or_delivery(self):
        text = self.certify({'emailed': [4]})['english']
        self.assertIn('retained message record', text)
        self.assertIn('from Display A to Display B', text)
        self.assertIn('client submit time stored in the message', text)
        self.assertIn('Fixture.ost folder Inbox', text)
        self.assertIn('does not establish successful transmission, delivery, reading, or authorship', text)
        self.assertNotIn('was sent', text)

    def test_every_shortcut_form_preserves_target_volume_join_without_opening_event(self):
        for claim in ({'opened': [1]}, {'openedFromMount': [1, 5]},
                      {'openedFromDevice': [1, 6]}, {'openedFromRecorded': [1, 7]}):
            with self.subTest(claim=claim):
                text = self.certify(claim)['english']
                self.assertIn('shortcut target record naming', text)
                self.assertIn('on recorded volume VOL-A', text)
                self.assertIn('shortcut file last-modified time', text)
                self.assertIn('not that the target was opened at this time', text)
                self.assertNotIn(r'\documents\plan.txt was opened', text)
        unknown = self.certify({'opened': [2]})['english']
        self.assertIn('with no volume recorded', unknown)
        self.assertIn('unspecified record timestamp', unknown)
        self.assertIn('source artifact: not supplied', unknown)

    def test_usb_record_timestamps_are_not_promoted_to_connection_onset(self):
        for claim in ({'usbConnected': [11]}, {'usbMountedAs': [11, 5]},
                      {'deviceHolds': [11, 6]}, {'deviceExamined': [11, 13]}):
            with self.subTest(claim=claim):
                text = self.certify(claim)['english']
                self.assertIn('matching recorded device identifier DEVICE-A' if 'deviceExamined' in claim
                              else 'USB device record naming serial DEVICE-A', text)
                self.assertIn('registry key last-write time', text)
                self.assertIn(r'Enum\USBSTOR\Fixture\DEVICE-A', text)
                self.assertIn('does not by itself establish exact connection onset', text)
                self.assertNotIn('was connected', text)
        missing = self.certify({'usbConnected': [12]})['english']
        self.assertIn('unspecified record timestamp', missing)
        self.assertIn('source artifact: not supplied', missing)
        self.assertNotIn('was connected', missing)
        setup = self.certify({'usbConnected': [15]})['english']
        self.assertIn('device install section start (first connection)', setup)
        self.assertIn('setupapi.dev.log line 1', setup)

    def test_usb_serial_joins_and_temporal_census_boundaries(self):
        self.certify({'usbMountedAs': [11, 14]}, accepted=False)
        self.certify({'deviceHolds': [11, 16]}, accepted=False)
        self.certify({'usbConnected': [1]}, accepted=False)
        ordered = self.certify({'before': [11, 15]})['english']
        self.assertIn('registry key last-write time', ordered)
        self.assertIn('orders recorded timestamps', ordered)
        self.assertNotIn('the connection of', ordered)
        census = self.certify({'exactly': ['usbInsert', 3]})['english']
        self.assertIn('3 USB device records', census)
        self.assertNotIn('USB connection', census)
        self.assertNotIn('was connected', census)
        mappings = self.certify({'exactly': ['volumeMount', 3]})['english']
        self.assertIn('3 device-volume mapping records', mappings)
        self.assertNotIn('the mounting of', mappings)

    def test_temporal_and_census_forms_do_not_bypass_observation_meaning(self):
        ordered = self.certify({'before': [3, 4]})['english']
        self.assertIn('orders recorded timestamps, not necessarily the underlying actions', ordered)
        self.assertNotIn('happened before', ordered)
        self.assertNotIn('the sending of', ordered)
        for kind, count, noun in [('lnkTarget', 2, 'shortcut-target'),
                                  ('emailSent', 1, 'retained-message'),
                                  ('programInstalled', 3, 'software-registration or installer')]:
            text = self.certify({'exactly': [kind, count]})['english']
            self.assertIn(noun, text)
            self.assertIn('counts records in the evidence file', text)
            self.assertNotIn('the opening of', text)
            self.assertNotIn('the sending of', text)

    def test_wrong_kind_wrong_volume_and_stronger_unsupported_forms_are_refused(self):
        for claim in ({'opened': [3]}, {'emailed': [1]}, {'programInstalledAt': [4]},
                      {'openedFromMount': [1, 8]}):
            self.certify(claim, accepted=False)
        for form in ('messageDelivered', 'fileActuallyOpened', 'installedAtExactTime'):
            with self.assertRaises(claims.ClaimError):
                claims.parse({form: [1]})

    def test_replay_rejects_promoted_english_or_changed_timestamp_provenance(self):
        cert = self.certify({'emailed': [4]})
        changed = copy.deepcopy(cert)
        changed['english'] = 'The message was successfully delivered.'
        self.assertTrue(verify(changed, self.source))
        self.source.get([4])[4].prov['time_meaning'] = 'delivery confirmed by server'
        self.assertTrue(verify(cert, self.source))


class BinaryAttributeSemantics(unittest.TestCase):
    def test_literal_version_fields_are_typed_source_observations_with_translation_scope(self):
        roles = ['app.binary.product_name', 'app.binary.product_version',
                 'app.binary.file_description', 'app.binary.file_version']
        values = ['Fixture Mail', '11, 0, 0001 beta', 'Fixture Mail Client', '11.0.1.2']
        start = KINDS.index('roleAppConfigIrcLogFileName') + 1
        self.assertEqual(tuple(ROLES[r].kind for r in roles), KINDS[start:start + 4])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ev = Evidence()
            identities = {}
            for role, value in zip(roles, values):
                identities[role] = emit_attribute(ev, 'image-A:app.exe:040904B0', role, value,
                    1_000_000, artifact='app.exe VERSIONINFO StringFileInfo 040904B0',
                    image='image-A', source_path='app.exe', resource_language=1033)
            other = emit_attribute(ev, 'image-A:app.exe:040C04B0', roles[1], values[1],
                1_000_000, artifact='app.exe VERSIONINFO StringFileInfo 040C04B0', resource_language=1036)
            path = root / 'facts.json'
            ev.write_json(path, {})
            source = JsonFacts(path)

            def triple(identity, role):
                rows = {f.kind: f.id for f in source.all() if source.string(f.obj) == identity}
                return [rows['attributeSubject'], rows[ROLES[role].kind], rows['attributeTextValue']]

            for index, (role, value) in enumerate(zip(roles, values)):
                cert = check({'attributeRecorded': triple(identities[role], role) + [role]},
                             f'Binary{index}', source, out_dir=root)
                self.assertEqual(cert['status'], 'verified', cert)
                self.assertEqual(verify(cert, source), [])
                self.assertIn(value, cert['english'])
                self.assertIn('literal', cert['english'])
                self.assertIn('not', cert['english'])
                self.assertNotIn('Fixture Mail 2020', cert['english'])
            wrong_role = check({'attributeRecorded': triple(identities[roles[1]], roles[1]) + [roles[3]]},
                               'WrongVersionField', source, out_dir=root)
            self.assertEqual(wrong_role['status'], 'rejected')
            joined = {'attributesSameSubject': triple(identities[roles[0]], roles[0]) + [roles[0]]
                      + triple(other, roles[1]) + [roles[1]]}
            self.assertEqual(check(joined, 'WrongTranslation', source, out_dir=root)['status'], 'rejected')


if __name__ == '__main__':
    unittest.main()
