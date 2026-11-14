"""Read the disputed event IDs and their message definition from the seized image.

Requires extraction dependencies, python-evtx and pefile. These two additional
parsers are audit-only dependencies; they are not used by the production extractor.
    python -m eval.optical_audit --out runs/optical-review/raw-audit.json
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
from xml.etree import ElementTree as ET


def audit(image):
    from dissect.target import Target
    from dissect.eventlog.evtx import Evtx as DissectEvtx
    from Evtx.Evtx import Evtx as IndependentEvtx
    import pefile

    target = Target.open(image)
    log_path = 'C:/Windows/system32/winevt/logs/System.evtx'
    raw = target.fs.path(log_path).read_bytes()
    first = []
    for r in DissectEvtx(io.BytesIO(raw)):
        if str(r.get('Provider_Name', '')).lower() == 'cdrom':
            first.append({'record_id': int(str(r['EventRecordID'])), 'event_id': int(str(r['EventID'])),
                          'qualifiers': int(str(r.get('EventID_Qualifiers', 0))),
                          'utc': str(r['TimeCreated_SystemTime'])})
    ns = {'e': 'http://schemas.microsoft.com/win/2004/08/events/event'}
    second = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'System.evtx'
        path.write_bytes(raw)
        with IndependentEvtx(str(path)) as log:
            for r in log.records():
                xml = r.xml()
                root = ET.fromstring(xml)
                if root.find('e:System/e:Provider', ns).get('Name', '').lower() != 'cdrom':
                    continue
                event = root.find('e:System/e:EventID', ns)
                second.append({'record_id': r.record_num(), 'event_id': int(event.text),
                               'qualifiers': int(event.get('Qualifiers', 0)), 'xml': xml})
    key_path = r'HKLM\SYSTEM\CurrentControlSet\Services\EventLog\System\cdrom'
    key = target.registry.key(key_path)
    message_file = str(key.value('EventMessageFile').value)
    mui_path = 'C:/Windows/System32/en-US/IoLogMsg.dll.mui'
    mui = target.fs.path(mui_path).read_bytes()
    pe = pefile.PE(data=mui)
    wanted = {(r['qualifiers'] << 16) | r['event_id'] for r in first}
    messages = {}
    for typ in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if typ.id != 11:                   # RT_MESSAGETABLE
            continue
        for ent in typ.directory.entries:
            for lang in ent.directory.entries:
                st = lang.data.struct
                data = pe.get_data(st.OffsetToData, st.Size)
                for i in range(struct.unpack_from('<I', data)[0]):
                    low, high, at = struct.unpack_from('<III', data, 4 + i * 12)
                    for code in range(low, high + 1):
                        length, flags = struct.unpack_from('<HH', data, at)
                        if code in wanted:
                            messages[hex(code)] = data[at + 4:at + length].decode(
                                'utf-16-le' if flags & 1 else 'cp1252').strip('\x00\r\n')
                        at += length
    comparison = lambda rows: sorted((r['record_id'], r['event_id'], r['qualifiers']) for r in rows)
    if comparison(first) != comparison(second):
        raise ValueError('independent event parsers disagree')
    return {'image': str(image), 'log_path': log_path,
            'log_sha256': hashlib.sha256(raw).hexdigest(),
            'dissect_events': first, 'python_evtx_events': second, 'parsers_agree': True,
            'provider_registry_key': key_path, 'registered_message_file': message_file,
            'message_resource': mui_path, 'message_resource_sha256': hashlib.sha256(mui).hexdigest(),
            'messages': messages,
            'answer_key_event_id': 113,
            'disposition': 'Preserve the raw ID. An exclusive-access lock is not proof of a write '
                           'or of which physical disc was inserted. Keep the answer-key '
                           'discrepancy visible; do not silently amend the score.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--image', default='data/pc.E01')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    result = audit(args.image)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(result["dissect_events"])} cdrom records; independent parsers agree; {result["messages"]}')


if __name__ == '__main__':
    main()
