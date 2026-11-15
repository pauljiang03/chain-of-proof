"""Exact event fields from reviewed EVTX source occurrences, never inferred actors."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from checker import check as checker
from checker.catalog import ROLES
from checker.facts import JsonFacts
from extractor import system
from extractor.event_attributes import emit_event_attributes
from extractor.store import Evidence
from verifier.verify import verify

EXAMINED = 1800000000000000
SCOPE = {'image': 'fixture.E01', 'exhibit': 'DISK-A', 'source_snapshot': 'base-volume', 'source_variant': 'primary'}
STAMP = datetime(2025, 4, 3, 12, 1, 2, 123456, tzinfo=timezone(timedelta(hours=-4)))


def event(**updates):
    result = dict(Provider_Name='Microsoft-Windows-Security-Auditing', Channel='Security',
                  EventID=4624, EventRecordID=42, ts=STAMP,
                  source=r'C:\Windows\System32\winevt\Logs\Security.evtx',
                  TargetUserName=r'DOMAIN\Literal Name', TargetUserSid='S-1-5-21-100-200-300-1001')
    result.update(updates)
    return result


def values(ev):
    return {json.loads(row[-1])['attribute_role']: (json.loads(row[4]), json.loads(row[-1]))
            for row in ev.rows() if row[0] in ('attributeTextValue', 'attributeIntegerValue')
            and json.loads(row[-1]).get('attribute_role', '').startswith('event.')}


class EventAttributes(unittest.TestCase):
    def emit(self, record=None, common=None, examined=EXAMINED, adapter=False):
        ev = Evidence()
        out = system._Out(ev, dict(SCOPE if common is None else common), examined)
        ok = emit_event_attributes(out, ev, event() if record is None else record,
                                   parser_record_id_text=adapter)
        return ev, ok

    def test_literal_fields_one_source_and_exam_time_distinct(self):
        ev, ok = self.emit()
        self.assertTrue(ok)
        rows = values(ev)
        self.assertEqual(len(rows), 9)
        self.assertEqual(rows['event.account_name'][0], r'DOMAIN\Literal Name')
        self.assertEqual(rows['event.account_sid'][0], 'S-1-5-21-100-200-300-1001')
        self.assertEqual(rows['event.recorded_time'][0], '2025-04-03T16:01:02.123456Z')
        self.assertEqual(rows['event.record_id'][0], 42)
        self.assertIs(type(rows['event.record_id'][0]), int)
        self.assertTrue(rows['event.description'][0].startswith('The source event record reports:'))
        subjects = {row[4] for row in ev.rows() if row[0] == 'attributeSubject'}
        self.assertEqual(len(subjects), 1)
        for row in ev.rows():
            self.assertEqual(row[1], EXAMINED)
            provenance = json.loads(row[-1])
            self.assertEqual(provenance['timestamp_semantics'], 'examination_observation')
            self.assertEqual(provenance['parser_timestamp_resolution_us'], 1)
            self.assertIn('original finer XML precision is not retained', provenance['parser_timestamp_precision'])
            self.assertNotIn('raw_time_created', provenance)
            self.assertIn(provenance['source_field'], {'Provider_Name', 'Channel', 'EventID',
                'EventRecordID', 'TimeCreated_SystemTime (ts)', 'Provider_Name/Channel/EventID',
                'TargetUserName', 'TargetUserSid'})
            for key, value in SCOPE.items():
                self.assertEqual(provenance[key], value)

    def test_provider_channel_and_native_event_id_gate(self):
        changes = [dict(Provider_Name='Other'), dict(Channel='Application'), dict(Channel=' Security'),
                   dict(EventID=4624.0), dict(EventID=True), dict(EventID='4624'), dict(EventID=99999)]
        for update in changes:
            with self.subTest(update=update):
                ev, ok = self.emit(event(**update))
                self.assertFalse(ok)
                self.assertEqual(ev.rows(), [])

    def test_direct_helper_record_id_is_native_positive_uint64_only(self):
        for value in (None, True, False, 0, -1, 1.0, '42', 2**64):
            with self.subTest(value=value):
                ev, ok = self.emit(event(EventRecordID=value))
                self.assertFalse(ok)
                self.assertEqual(ev.rows(), [])
        ev, ok = self.emit(event(EventRecordID=2**64-1))
        self.assertTrue(ok)
        self.assertEqual(values(ev)['event.record_id'][0], 2**64-1)

    def test_reviewed_text_adapter_is_exact_and_preserves_raw_representation(self):
        ev, ok = self.emit(event(EventRecordID='42'), adapter=True)
        self.assertTrue(ok)
        value, prov = values(ev)['event.record_id']
        self.assertEqual(value, 42)
        self.assertEqual(prov['record_id_representation']['raw_value'], '42')
        self.assertIn('canonical decimal', prov['record_id_representation']['conversion'])
        for value in ('0', '042', '+42', '-42', '42 ', ' 42', '42.0', '4.2e1', str(2**64), True, 42.0):
            with self.subTest(value=value):
                ev, ok = self.emit(event(EventRecordID=value), adapter=True)
                self.assertFalse(ok)
                self.assertEqual(ev.rows(), [])

    def test_actual_dissect_field_shapes_work_through_events_adapter(self):
        from flow.record import RecordDescriptor
        descriptor = RecordDescriptor('fixture/evtx', [('string','Provider_Name'), ('string','Channel'),
            ('uint32','EventID'), ('string','EventRecordID'), ('datetime','ts'), ('path','source'),
            ('string','TargetUserName'), ('string','TargetUserSid')])
        record = descriptor(**event(EventRecordID='42'))
        target = NS(evtx=lambda: iter([record]))
        ev = Evidence()
        system._events(system._Out(ev, SCOPE, EXAMINED), ev, target, {'S-1-5-21-100-200-300-1001':'Guessed person'})
        self.assertEqual(values(ev)['event.record_id'][0], 42)
        self.assertEqual(values(ev)['event.account_name'][0], r'DOMAIN\Literal Name')
        self.assertEqual(values(ev)['event.record_id'][1]['parser_row_ordinal'], 1)
        self.assertEqual(len([row for row in ev.rows() if row[0]=='sessionEvent']), 1)

    def test_duplicate_parser_occurrences_have_distinct_ordinals(self):
        from flow.record import RecordDescriptor
        descriptor = RecordDescriptor('fixture/duplicate_evtx', [('string','Provider_Name'), ('string','Channel'),
            ('uint32','EventID'), ('string','EventRecordID'), ('datetime','ts'), ('path','source')])
        raw = {key:value for key,value in event(EventRecordID='42').items()
               if key not in ('TargetUserName','TargetUserSid')}
        record = descriptor(**raw)
        ev = Evidence()
        system._events(system._Out(ev,SCOPE,EXAMINED),ev,NS(evtx=lambda:iter([record,record])),{})
        subjects = {row[4] for row in ev.rows() if row[0]=='attributeSubject'}
        self.assertEqual(len(subjects),2)
        self.assertEqual({json.loads(row[-1])['parser_row_ordinal'] for row in ev.rows()
                          if row[0]=='attributeSubject'}, {1,2})

    def test_naive_or_missing_timestamp_scope_and_locator_never_emit(self):
        for update in (dict(ts=None), dict(ts=STAMP.replace(tzinfo=None)), dict(ts=STAMP.isoformat()),
                       dict(source=''), dict(source='Security.evtx'), dict(source=r'C:\config\SAM'),
                       dict(source=42), dict(source=r'C:\Logs\..\Security.evtx')):
            with self.subTest(update=update):
                ev, ok = self.emit(event(**update))
                self.assertFalse(ok)
                self.assertEqual(ev.rows(), [])
        for key in SCOPE:
            broken = dict(SCOPE, **{key:'unknown'})
            ev, ok = self.emit(common=broken)
            self.assertFalse(ok)
            self.assertEqual(ev.rows(), [])
        for examined in (None, 0, True, 1.5):
            ev, ok = self.emit(examined=examined)
            self.assertFalse(ok)
            self.assertEqual(ev.rows(), [])

    def test_service_and_unclean_restart_descriptions_do_not_invent_power_times(self):
        for eid in (6005, 6006):
            ev, ok = self.emit(event(Provider_Name='EventLog', Channel='System', EventID=eid))
            self.assertTrue(ok)
            description = values(ev)['event.description'][0]
            self.assertIn('service', description)
            self.assertIn('does not establish a machine power transition', description)
            self.assertNotIn('event.account_name', values(ev))
        ev, ok = self.emit(event(Provider_Name='Microsoft-Windows-Kernel-Power', Channel='System', EventID=41))
        self.assertTrue(ok)
        self.assertIn('not the prior crash or power-loss time', values(ev)['event.description'][0])

    def test_performance_keeps_timecreated_not_embedded_boot_time(self):
        ev, ok = self.emit(event(Provider_Name='Microsoft-Windows-Diagnostics-Performance',
            Channel='Microsoft-Windows-Diagnostics-Performance/Operational', EventID=100,
            BootStartTime=datetime(2001,1,1,tzinfo=timezone.utc)))
        self.assertTrue(ok)
        self.assertEqual(values(ev)['event.recorded_time'][0], '2025-04-03T16:01:02.123456Z')
        self.assertIn('not', values(ev)['event.time_meaning'][0])

    def test_sid_is_literal_and_never_looked_up_as_account_name(self):
        ev = Evidence()
        raw = event(Provider_Name='Microsoft-Windows-Winlogon', Channel='System', EventID=7001,
                    UserSid='S-1-5-18')
        system._event(system._Out(ev, SCOPE, EXAMINED), ev, raw, 'record42', {'S-1-5-18':'Guessed identity'})
        rows = values(ev)
        self.assertEqual(rows['event.account_sid'][0], 'S-1-5-18')
        self.assertNotIn('event.account_name', rows)
        ev, ok = self.emit(event(TargetUserName=42, TargetUserSid='not a SID'))
        self.assertTrue(ok)
        self.assertNotIn('event.account_name', values(ev))
        self.assertNotIn('event.account_sid', values(ev))
        self.assertTrue(ev.problems)

    def test_sam_or_registry_fields_do_not_become_events(self):
        for data in ({'account':'Alice','last_logon':STAMP,'logon_count':3,'source':r'C:\config\SAM'},
                     event(source=r'C:\Windows\System32\config\SAM')):
            ev, ok = self.emit(data)
            self.assertFalse(ok)
            self.assertEqual(ev.rows(), [])

    def test_occurrence_identity_separates_scopes_paths_and_records(self):
        subjects = set()
        fixtures = [(SCOPE,event())]
        fixtures += [(dict(SCOPE,**{key:value}),event()) for key,value in (
            ('image','another.E01'),('exhibit','OTHER'),('source_snapshot','vss:copy'),('source_variant','backup'))]
        fixtures += [(SCOPE,event(EventRecordID=43)),(SCOPE,event(source=r'D:\Logs\Security.evtx'))]
        for common, raw in fixtures:
            ev, ok = self.emit(raw, common=common)
            # The malformed VSS UUID is deliberately unknown and must not certify a source.
            if common['source_snapshot']=='vss:copy':
                self.assertFalse(ok)
                continue
            self.assertTrue(ok)
            subjects.update(row[4] for row in ev.rows() if row[0]=='attributeSubject')
        self.assertEqual(len(subjects), len(fixtures)-1)

    def test_actual_kernel_tuple_and_cross_record_refusal(self):
        ev = Evidence()
        out = system._Out(ev, SCOPE, EXAMINED)
        for rid in (42,43):
            self.assertTrue(emit_event_attributes(out,ev,event(EventRecordID=rid)))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ev.write_json(root/'facts.json',{})
            source = JsonFacts(root/'facts.json')
            def triple(rid, role):
                rows={f.kind:f.id for f in source.all() if f.prov.get('attribute_role')==role and f.prov.get('event_record_id')==rid}
                spec=ROLES[role]
                return [rows['attributeSubject'],rows[spec.kind],rows[spec.value_kind],role]
            chosen=['provider','channel','event_id','record_id','recorded_time','description','account_name','account_sid']
            rows=[triple(42,'event.'+name) for name in chosen]
            cert=checker.check({'attributeTuple':rows},'ActualEvent',source,out_dir=root)
            self.assertEqual(cert['status'],'verified',cert)
            self.assertEqual(cert['axioms'],[])
            self.assertEqual(verify(cert,source),[])
            rows[-1]=triple(43,'event.account_sid')
            rejected=checker.check({'attributeTuple':rows},'WrongEvent',source,out_dir=root)
            self.assertEqual(rejected['status'],'rejected')

    def test_same_id_time_but_different_literals_cannot_join_even_without_ordinal(self):
        ev=Evidence()
        out=system._Out(ev,SCOPE,EXAMINED)
        for account in ('First account','Second account'):
            self.assertTrue(emit_event_attributes(out,ev,event(TargetUserName=account)))
        subjects={row[4] for row in ev.rows() if row[0]=='attributeSubject'}
        self.assertEqual(len(subjects),2)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ev.write_json(root/'facts.json',{});source=JsonFacts(root/'facts.json')
            digests={json.loads(source.string(f.aux)):f.prov['selected_fields_sha256']
                     for f in source.all() if f.kind=='attributeTextValue'
                     and f.prov.get('attribute_role')=='event.account_name'}
            def triple(account, role):
                rows={f.kind:f.id for f in source.all() if f.prov.get('attribute_role')==role
                      and f.prov.get('selected_fields_sha256')==digests[account]}
                spec=ROLES[role]
                return [rows['attributeSubject'],rows[spec.kind],rows[spec.value_kind],role]
            mixed={'attributeTuple':[triple('First account','event.account_name'),
                                     triple('Second account','event.account_sid')]}
            rejected=checker.check(mixed,'SameIdConflict',source,out_dir=root)
            self.assertEqual(rejected['status'],'rejected')


if __name__=='__main__': unittest.main()
