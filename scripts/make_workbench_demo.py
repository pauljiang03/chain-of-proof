"""Build a broad, explicitly synthetic workbench demo using the real proof checker.

    python scripts/make_workbench_demo.py --out /tmp/conan-demo-new

The output directory must be new. No model, case evidence, or benchmark is used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.tools import Workbench
from checker.export import bundle
from checker.facts import JsonFacts
from verifier.verify import verify


def build(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    strings, rows, proposals = {"0": "(none)"}, [], []
    def sid(value):
        if value in (None, "", "(none)"):
            return 0
        for key, known in strings.items():
            if known == value:
                return int(key)
        key = len(strings)
        strings[str(key)] = value
        return key
    def stamp(clock):
        return int(datetime.fromisoformat('2026-06-09T' + clock).replace(tzinfo=ZoneInfo('America/New_York')).timestamp()) * 1000000
    def row(kind, obj, aux=None, clock='09:00:00', exhibit='Laptop', artifact='Synthetic fixture', meaning='source record timestamp', **prov):
        ident = len(rows) + 1
        image = {'Laptop': 'demo-laptop.E01', 'Project USB': 'demo-project-usb.E01', 'Backup USB': 'demo-backup-usb.E01'}[exhibit]
        rows.append(dict(id=ident, kind=kind, t=stamp(clock), res=1000, obj=sid(obj), aux=sid(aux), prov=dict(
            image=image, exhibit=exhibit, artifact=artifact, tool='Synthetic demo generator v1',
            time_meaning=meaning, time_zone='local time, converted from America/New_York', synthetic=True, **prov)))
        return ident
    def claim(question, name, *ids, expected='verified'):
        proposals.append((question, {name: list(ids)}, expected))
    for label, value in [('computer name', 'HARBOR-LAPTOP'), ('operating system', 'Windows 11 Pro'), ('registered owner', 'Maya Chen')]:
        claim('Which computer was examined?', 'settingRecorded', row('systemSetting', label, value, meaning='registry key last-write time'))
    for exhibit in ['Laptop', 'Project USB', 'Backup USB']:
        digest = hashlib.sha256(('SYNTHETIC PLACEHOLDER ' + exhibit).encode()).hexdigest()
        claim('What evidence items are in this demo?', 'settingRecorded', row('systemSetting', 'image sha256', digest,
            exhibit=exhibit, meaning='when the image was examined, not source activity',
            timestamp_semantics='examination_observation', stored_by='synthetic placeholder; no disk image exists'))
    account = row('accountSeen', 'maya', 'local account', clock='08:45:00', artifact='SAM account record',
                  meaning='account registry key last-write time', user='maya', profile_path=r'C:\Users\maya',
                  groups=['Design team'], sid='S-1-5-21-101-202-303-1001', logon_count=8,
                  last_logon='2026-06-09T12:55:00Z')
    claim('Which account is recorded?', 'accountRecorded', account)
    claim('When was a sign-in recorded?', 'sessionRecorded', row('sessionEvent', 'interactive logon', 'maya',
        clock='08:55:00', artifact='Security event 4624', meaning='time the sign-in event was logged', user='maya', event_id=4624))
    usb = row('usbInsert', 'DEMO-PROJECT-042', clock='09:10:00', artifact='SetupAPI device install log',
              meaning='device install section start (first connection)', device='Disk&Ven_Atlas&Prod_Pocket_Drive&Rev_1.0')
    backup = row('usbInsert', 'DEMO-BACKUP-007', clock='08:58:00', artifact='SetupAPI device install log',
                 meaning='device install section start (first connection)', device='Disk&Ven_Atlas&Prod_Archive_Drive&Rev_1.0')
    mount = row('volumeMount', 'DEMO-PROJECT-042', 'DEMO-VOL-PROJECT', clock='09:10:01', artifact='Volume mount record',
                meaning='recorded mount time', volume_label='HARBOR PROJECT', drive_letter='E:')
    wrong = row('volumeMount', 'DEMO-BACKUP-007', 'DEMO-VOL-BACKUP', clock='08:58:01', artifact='Volume mount record',
                meaning='recorded mount time', volume_label='TEAM BACKUP', drive_letter='F:')
    claim('Which removable devices were connected?', 'usbMountedAs', usb, mount)
    claim('Which removable devices were connected?', 'usbMountedAs', backup, wrong)
    for serial, vol, exhibit, label in [('DEMO-PROJECT-042','DEMO-VOL-PROJECT','Project USB','HARBOR PROJECT'),
                                       ('DEMO-BACKUP-007','DEMO-VOL-BACKUP','Backup USB','TEAM BACKUP')]:
        volume = row('volumeOnDevice', serial, vol, exhibit=exhibit, artifact='Volume boot record',
                     meaning='when the image was examined, not source activity', timestamp_semantics='examination_observation',
                     volume_label=label, filesystem='exFAT')
        claim('Which volume belongs to each examined device?', 'deviceHolds', usb if exhibit == 'Project USB' else backup, volume)
    file_path = r'E:\Harbor\launch-plan.pptx'
    opened = row('lnkTarget', file_path, 'DEMO-VOL-PROJECT', clock='09:18:00', artifact='Recent Items / launch-plan.lnk',
                 meaning='shortcut file last-modified time (last open via the shell)', user='maya', drive_letter='E:', volume_label='HARBOR PROJECT')
    proposals.append(('How do the device connection and project file relate?',
                      {'both': [{'usbMountedAs': [usb, mount]}, {'openedFromMount': [opened, mount]}, {'before': [usb, opened]}]}, 'verified'))
    proposals.append(('Was the project file opened from the backup device?', {'openedFromMount': [opened, wrong]}, 'rejected'))
    for name, size, minute in [('launch-plan.pptx', 5242880, 12), ('budget.xlsx', 98304, 14), ('brand-guide.pdf', 2097152, 16)]:
        path = 'E:\\Harbor\\' + name
        modified = row('fileModified', path, 'DEMO-VOL-PROJECT', clock='08:10:00', exhibit='Project USB',
                       artifact='exFAT directory entry', meaning='filesystem last-modified time', size=size)
        created = row('fileCreated', path, 'DEMO-VOL-PROJECT', clock=f'09:{minute}:00', exhibit='Project USB',
                      artifact='exFAT directory entry', meaning='filesystem creation time', size=size)
        claim('Which project files are recorded on the USB?', 'both', {'fileModifiedAt': [modified]}, {'fileCreatedAt': [created]})
    claim('Which names changed?', 'renamed', row('fileRenamed', r'C:\Users\maya\Desktop\Harbor-draft.zip',
        r'C:\Users\maya\Desktop\Harbor-review.zip', clock='09:35:00', artifact='NTFS change journal', meaning='time of the new-name journal record',
        user='maya', old_name='Harbor-draft.zip', new_name='Harbor-review.zip'))
    claim('Was a file sent to the Recycle Bin?', 'fileDeletedAt', row('fileDeleted', r'C:\Users\maya\Downloads\old-mockup.png',
        'DEMO-SYSTEM-VOL', clock='10:05:00', artifact='Recycle Bin $I record', meaning='deletion time stored in the Recycle Bin record', size=204800, user='maya'))
    for name, path in [('budget.xlsx', r'F:\Backup\budget.xlsx'), ('readme.txt', r'F:\Backup\readme.txt')]:
        claim('What is recorded on the backup USB?', 'fileRecorded', row('fileSeen', path, 'DEMO-VOL-BACKUP', exhibit='Backup USB',
            artifact='File inventory', meaning='when the image was examined, not source activity', timestamp_semantics='examination_observation', size=4096))
    for query, clock in [('how to encrypt a USB drive', '09:02:00'), ('Harbor project presentation template', '09:04:00')]:
        claim('Which searches are recorded?', 'searched', row('webSearch', query, 'Chrome', clock=clock,
            artifact='Chrome History', meaning='browser history visit time', user='maya', url='https://search.example.test/?q=' + query.replace(' ', '+')))
    for url, clock in [('https://docs.example.test/harbor/brief','09:06:00'), ('https://docs.example.test/harbor/assets','09:07:00')]:
        claim('Which websites were visited?', 'visited', row('webVisit', url, 'Chrome', clock=clock,
            artifact='Chrome History', meaning='browser history visit time', user='maya'))
    claim('Which download is recorded?', 'downloaded', row('fileDownloaded', r'C:\Users\maya\Downloads\harbor-template.pptx',
        'https://templates.example.test/harbor-template.pptx', clock='09:08:00', artifact='Chrome downloads',
        meaning='download start time', user='maya', size=1048576))
    claim('Which message is recorded?', 'emailed', row('emailSent', 'Harbor review — draft attached', 'from maya to dana',
        clock='09:40:00', artifact='Outlook Sent Items', meaning='client submit time stored in the message',
        sender_address='maya@example.test', recipient_address='dana@example.test', attachments=1,
        attachment_names=['launch-plan.pptx'], mailbox_user='maya', message_id='<demo-harbor-1@example.test>'))
    claim('What cloud activity is recorded?', 'cloudEvent', row('cloudFile', 'Harbor/launch-plan.pptx', 'sync completed',
        clock='09:42:00', artifact='Synthetic cloud client log', meaning='time written in the sync log', user='maya', service='Demo Drive'))
    for app, clock, count in [('POWERPNT.EXE','09:17:00',3), ('7ZFM.EXE','09:30:00',1)]:
        claim('Which application artifacts are recorded?', 'programRan', row('programRun', app, 'C:\\Program Files\\' + app,
            clock=clock, artifact='Prefetch / ' + app + '.pf', meaning='last run time in the prefetch header', source='prefetch', run_count=count, user='maya'))
    claim('Which software registration is recorded?', 'programInstalledAt', row('programInstalled', '7-Zip', '24.09',
        clock='08:30:00', artifact='Uninstall registry key', meaning='registry key last-write time', publisher='Igor Pavlov'))
    claim('Which optical-disc trace is recorded?', 'burnTrace', row('cdBurn', 'optical drive lock', 'DVD RW Drive',
        clock='10:00:00', artifact='Synthetic optical service event', meaning='time the optical event was logged', event_id=1001))
    claim('What note was found?', 'noteFound', row('noteText',
        'Bring the Harbor deck and budget to the design review.', 'UTF-8 text file',
        artifact=r'C:\Users\maya\Desktop\review-note.txt',
        meaning='when the image was examined, not source activity', timestamp_semantics='examination_observation', user='maya'))
    facts = {'_note': 'Entirely synthetic Harbor case. All people, devices, messages and artifacts are fictional. No image exists.', 'strings': strings, 'facts': rows}
    (output / 'facts.json').write_text(json.dumps(facts, indent=2) + '\n')
    workbench = Workbench(output / 'facts.json', output, proposer='synthetic demo script; no model')
    for item in rows:
        workbench.fact(item['id'])
    for question, value, expected in proposals:
        result = workbench.check(question, value)
        print(result['finding_id'], result['status'], question, flush=True)
        if result['status'] != expected:
            raise RuntimeError(json.dumps(result, indent=2))
    data = bundle(output, 'Harbor design review — synthetic demo', case_metadata={
        'sample': True, 'case_id': 'synthetic-harbor-review', 'backend': 'offline-fixture', 'model': 'none',
        'ended': 'success', 'is_error': False, 'facts_sha256': hashlib.sha256((output / 'facts.json').read_bytes()).hexdigest(),
        'note': 'Fictional demonstration, generated through the real checker. No model, real disk images or benchmark score.'})
    source = JsonFacts(output / 'facts.json')
    for finding in data['findings']:
        errors = verify(finding, source)
        if errors:
            raise RuntimeError(str(errors))
    (output / 'run.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    verification_sources = [ROOT / 'checker/check.py', ROOT / 'checker/claims.py',
                            ROOT / 'verifier/verify.py', ROOT / 'lean/ChainOfProof.lean']
    verification_sources += sorted((ROOT / 'lean/ChainOfProof').rglob('*.lean'))
    receipt = {'synthetic': True, 'checked': len(data['findings']), 'passed': True,
               'facts_sha256': hashlib.sha256((output / 'facts.json').read_bytes()).hexdigest(),
               'run_sha256': hashlib.sha256((output / 'run.json').read_bytes()).hexdigest(),
               'verification_sources_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                               for path in verification_sources}}
    (output / 'demo-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Verified demo:', len(rows), 'records;', len(data['findings']), 'findings;', len(data['rejections']), 'refusal(s).')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    build(parser.parse_args().out)
