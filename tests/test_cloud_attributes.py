"""Synthetic cloud containers and exact source-identity controls; no answer keys."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from checker.catalog import ROLES
from extractor import cloud_attributes as cloud
from extractor.store import Evidence

P = cloud.PREFIX


def line(message, module='common.cloud.cloud_watcher', second=0):
    return f'2020-07-01 12:00:{second:02},005 -0430 INFO pid=12 3:Worker {module}:42 {message}\r\n'


def entry(doc='DOC_A', filename='fixture.txt', modified='1593619100'):
    return (f'CloudEntry(doc_id={doc},filename={filename},modified={modified},created=1593619000,'
            'acl_role=owner,doc_type=DocType.BLOB)')


def deletion(doc='DOC_A', time='1593619300'):
    return f'WorkerDeleteCloudEvent(doc_id={doc}, server_mod_time={time}, version=None)'


def log(*messages):
    return (line('Config:', 'common.sync_app') + ''.join(messages)).encode('utf-8')


def sqlite_bytes(directory, *, missing=None):
    path = Path(directory) / 'fixture.sqlite'
    db = sqlite3.connect(path)
    for table, columns in cloud.SNAPSHOT_SCHEMA.items():
        if table == missing:
            continue
        db.execute('CREATE TABLE "' + table + '" (' + ','.join('"' + col + '" TEXT' for col in sorted(columns)) + ')')
    db.commit()
    db.close()
    return path.read_bytes()


class CloudLogParsing(unittest.TestCase):
    def test_exact_document_join_keeps_filename_and_both_server_times(self):
        data = log(line('Got: [' + entry() + ']'), line('Built: [' + deletion() + ']', second=1))
        rows, problems = cloud.parse_drive_log_bytes(data)
        joined, issues = cloud.deletion_relations(rows)
        self.assertEqual(problems + issues, [])
        record, = joined
        self.assertEqual(record['fields'], {P+'document_id': 'DOC_A', P+'file_name': 'fixture.txt',
            P+'server_modified_at': '2020-07-01T15:58:20.000000Z',
            P+'deletion_record_server_modified_at': '2020-07-01T16:01:40.000000Z'})
        self.assertEqual(record['locator']['log_recorded_at'], '2020-07-01T16:30:01.005000Z')
        self.assertNotEqual(record['fields'][P+'deletion_record_server_modified_at'], record['locator']['log_recorded_at'])

    def test_multiple_modified_versions_are_preserved_but_never_selected_for_join(self):
        data = log(line(entry()), line(entry(modified='1593619200'), second=1), line(deletion(), second=2))
        rows, _ = cloud.parse_drive_log_bytes(data)
        joined, issues = cloud.deletion_relations(rows)
        self.assertTrue(issues)
        self.assertEqual(joined, [])
        self.assertEqual(len([row for row in rows if row['kind']=='cloud_entry']), 2)

    def test_exact_repeats_keep_all_line_locators_without_inventing_new_version(self):
        rows, _ = cloud.parse_drive_log_bytes(log(line(entry()),line(entry(),second=1),line(deletion(),second=2)))
        joined, issues = cloud.deletion_relations(rows)
        self.assertEqual(issues, [])
        self.assertEqual(len(joined[0]['related_locators']),2)
        self.assertIn('one unchanged recorded modified value', joined[0]['identity_rule'])

    def test_no_join_for_name_conflicts_unknown_ids_future_versions_or_missing_modified(self):
        cases = [log(line(entry()), line(entry(filename='renamed.txt')), line(deletion())),
                 log(line(entry()), line(deletion(doc='DOC_B'))),
                 log(line(entry(modified='1593619999')), line(deletion())),
                 log(line(entry(modified='None')), line(deletion())),
                 log(line(deletion()), line(entry()))]
        for data in cases:
            with self.subTest(data=data[-80:]):
                rows, _ = cloud.parse_drive_log_bytes(data)
                joined, issues = cloud.deletion_relations(rows)
                self.assertEqual(joined, [])
                self.assertTrue(issues)
                self.assertTrue(any(row['kind']=='server_deletion' for row in rows))

    def test_record_order_within_same_line_does_not_join_future_entry(self):
        rows, _ = cloud.parse_drive_log_bytes(log(line('[' + deletion() + ', ' + entry() + ']')))
        self.assertEqual([row['kind'] for row in rows], ['server_deletion', 'cloud_entry'])
        self.assertEqual(cloud.deletion_relations(rows)[0], [])

    def test_exact_line_and_record_byte_locators_cover_utf8_and_crlf(self):
        data = log(line('Préfix [' + entry(filename='résumé.txt') + ']'))
        rows, _ = cloud.parse_drive_log_bytes(data)
        row, = rows
        where = row['locator']
        raw = data[where['byte_offset']:where['byte_offset'] + where['byte_length']]
        self.assertEqual(hashlib.sha256(raw).hexdigest(), where['line_sha256'])
        self.assertTrue(raw.endswith(b'\r\n'))
        span = data[where['record_byte_offset']:where['record_byte_offset'] + where['record_byte_length']]
        self.assertEqual(span.decode(), entry(filename='résumé.txt'))

    def test_credentials_are_initialization_not_logon_and_preserve_utc_offset(self):
        data = log(line('Initializing User instance with new credentials. fixture@example.test', 'common.service.user'))
        rows, issues = cloud.parse_drive_log_bytes(data)
        self.assertEqual(issues, [])
        row, = rows
        self.assertEqual(row['fields'], {P+'credentials_account': 'fixture@example.test',
                         P+'credentials_used_at': '2020-07-01T16:30:00.005000Z'})
        self.assertFalse(any('logon' in role for role in row['fields']))

    def test_worker_deletion_preserves_direction_stage_action_and_literal_name(self):
        change = "ImmutableChange(Direction.UPLOAD, Action.DELETE, name=u'a, b.txt', ino=9, path=u'C:\\\\Fixture')"
        data = log(line('Worker starting on ['+change+']', 'common.workers'),
                   line('Worker successfully completed ['+change+']', 'common.workers', second=1))
        rows, issues = cloud.parse_drive_log_bytes(data)
        self.assertEqual(issues, [])
        self.assertEqual([row['fields'][P+'worker_stage'] for row in rows], ['started', 'completed'])
        for row in rows:
            self.assertEqual(row['fields'][P+'worker_direction'], 'UPLOAD')
            self.assertEqual(row['fields'][P+'worker_action'], 'DELETE')
            self.assertEqual(row['fields'][P+'worker_file_name'], 'a, b.txt')
            self.assertNotIn('uploaded', row['fields'].values())

    def test_worker_does_not_fall_back_to_id_or_ambiguous_name(self):
        for tail in ('rid=DOC_A', 'name=a, b.txt, rid=DOC_A', "name='a.txt', name='b.txt'", "name='unterminated"):
            data = log(line(entry()), line('Worker successfully completed [ImmutableChange(Direction.UPLOAD, Action.CREATE, '+tail+')]', 'common.workers'))
            rows, issues = cloud.parse_drive_log_bytes(data)
            self.assertTrue(issues)
            self.assertFalse(any(row['kind']=='worker' for row in rows))
        data=log(line(entry()),line("Worker successfully completed [ImmutableChange(Direction.UPLOAD, Action.CREATE, name='x') garbage]",'common.workers'))
        rows,issues=cloud.parse_drive_log_bytes(data)
        self.assertTrue(issues)
        self.assertFalse(any(row['kind']=='worker' for row in rows))

    def test_strict_decode_invalid_time_and_unclosed_cloud_records_are_rejected(self):
        good = log(line(entry()))
        for data in (good+b'\xff', good.replace(b'-0430', b'-0460'), good.replace(b'12:00:00', b'99:00:00'),
                     log(line(entry()[:-1])), log(line(entry(filename='a,modified=1,created=2,acl_role=x')))):
            with self.subTest(data=data[-70:]), self.assertRaises((ValueError, UnicodeDecodeError)):
                cloud.parse_drive_log_bytes(data)

    def test_filename_and_generic_log_alone_do_not_establish_google_drive(self):
        for data in (b'Google Drive sync_log.log', line('unrelated message', 'other.logger').encode(),
                     line(entry(), 'other.logger').encode(), line(entry()).encode()):
            with self.assertRaises(ValueError):
                cloud.parse_drive_log_bytes(data)

    def test_bounds_are_enforced_before_observations(self):
        with patch.object(cloud, 'MAX_BYTES', 4), self.assertRaisesRegex(ValueError, 'byte bound'):
            cloud.parse_drive_log_bytes(log(line(entry())))
        with patch.object(cloud, 'MAX_LINES', 1), self.assertRaisesRegex(ValueError, 'line bound'):
            cloud.parse_drive_log_bytes(log(line(entry())))


class CloudContainerValidation(unittest.TestCase):
    def test_discovery_selects_content_without_turning_other_files_into_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            top=home/'AppData/Local/Google/Drive';top.mkdir(parents=True)
            (top/'different-name.bin').write_bytes(log(line(entry())))
            (top/'snapshot.data').write_bytes(b'SQLite format 3\0'+bytes(100))
            (top/'pid').write_text('1234')
            (top/'lock').write_bytes(b'')
            (top/'snapshot.data-wal').write_bytes(b'sidecar')
            ev=Evidence()
            with patch('extractor.webcloud._users',return_value=[('fixture',home)]),patch.object(cloud,'extract_paths') as extract:
                counts=cloud.extract(ev,NS(),{'common':{},'examined_at':1})
            self.assertEqual({path.name for path in extract.call_args.args[1]}, {'different-name.bin','snapshot.data'})
            self.assertEqual(counts['scanned_files'],4)
            self.assertEqual(counts['selected_files'],2)
            self.assertEqual(counts['unrecognized_files'],2)
            self.assertEqual(counts['skipped_sidecars'],1)
            self.assertEqual(ev.problems,[])

    def test_snapshot_is_classified_by_schema_even_under_different_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            result = cloud.classify_snapshot_sqlite(sqlite_bytes(directory))
        self.assertEqual(result['format'], 'Google Drive snapshot SQLite database')
        self.assertEqual(result['validated_tables'], sorted(cloud.SNAPSHOT_SCHEMA))

    def test_generic_sqlite_partial_schema_and_magic_only_are_not_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            data = sqlite_bytes(directory, missing='cloud_relations')
            with self.assertRaisesRegex(ValueError, 'table missing'):
                cloud.classify_snapshot_sqlite(data)
        for data in (b'SQLite format 3\0'+bytes(100), b'not SQLite'):
            with self.assertRaises((ValueError, sqlite3.DatabaseError)):
                cloud.classify_snapshot_sqlite(data)

    def test_allocation_flag_comes_from_matching_file_record(self):
        record = NS(segment=12, header=NS(Flags=1, SequenceNumber=3), is_file=lambda:True,
                    is_reparse_point=lambda:False, full_paths=lambda:[r'Cloud\log'])
        target = NS(fs=NS(mounts={'c:':NS(ntfs=NS(mft=NS(get=lambda path:record)))}))
        flag, locator = cloud._allocation(target, r'C:\Cloud\log')
        self.assertIs(flag, False)
        self.assertEqual(locator['mft_segment'], 12)
        record.header.Flags=0
        self.assertIs(cloud._allocation(target,r'C:\Cloud\log')[0], True)
        with self.assertRaisesRegex(ValueError, 'does not match'):
            cloud._allocation(target,r'C:\Other\log')
        self.assertIsNone(cloud._allocation(None,r'C:\Cloud\log'))


class CloudEmission(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'arbitrary-name.data'
        self.data=log(line(entry()),line(deletion(),second=1))
        self.path.write_bytes(self.data)
        self.ctx={'common':{'image':'fixture.E01','exhibit':'FIX','source_snapshot':'base-volume','source_variant':'primary'},'examined_at':999}

    def captured(self,ctx=None,paths=None):
        with patch.object(cloud,'emit_attribute') as emit:
            ev=Evidence();cloud.extract_paths(ev,paths or [self.path],ctx or self.ctx)
            return emit.call_args_list,ev

    def test_same_document_join_has_one_subject_hash_and_exam_time(self):
        calls,ev=self.captured()
        joined=[call for call in calls if call.kwargs.get('observation_kind')=='deleted_document']
        self.assertEqual(len(joined),4)
        self.assertEqual(len({call.args[1] for call in joined}),1)
        self.assertEqual({call.args[4] for call in calls},{999})
        self.assertEqual({call.kwargs['container_sha256'] for call in calls},{hashlib.sha256(self.data).hexdigest()})
        self.assertEqual(ev.problems,[])

    def test_changed_container_image_snapshot_or_variant_never_reuses_subject(self):
        original=self.captured()[0][0].args[1]
        for key,value in (('image','other.E01'),('exhibit','OTHER'),('source_snapshot','vss:11111111-1111-1111-1111-111111111111'),('source_variant','recovered')):
            ctx=dict(self.ctx,common=dict(self.ctx['common'],**{key:value}))
            self.assertNotEqual(self.captured(ctx=ctx)[0][0].args[1],original)
        self.path.write_bytes(self.data+b'continuation\n')
        self.assertNotEqual(self.captured()[0][0].args[1],original)
        ctx={'common':{'image':'fixture'},'examined_at':999}
        calls,_=self.captured(ctx=ctx)
        self.assertEqual(json.loads(calls[0].args[1])[2:4],['unknown','unknown'])

    def test_cross_container_document_id_cannot_supply_missing_name(self):
        other=self.path.parent/'other.log'
        self.path.write_bytes(log(line(entry())))
        other.write_bytes(log(line(deletion())))
        calls,ev=self.captured(paths=[self.path,other])
        self.assertFalse(any(call.kwargs.get('observation_kind')=='deleted_document' for call in calls))
        self.assertTrue(ev.problems)

    def test_adjacent_committed_wal_is_validated_and_both_hashes_bind_subject(self):
        dbpath=self.path.parent/'arbitrary.db'
        db=sqlite3.connect(dbpath)
        self.addCleanup(db.close)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA wal_autocheckpoint=0')
        for table,columns in cloud.SNAPSHOT_SCHEMA.items():
            db.execute('CREATE TABLE "'+table+'" ('+','.join('"'+col+'" TEXT' for col in sorted(columns))+')')
        db.commit()
        base=dbpath.read_bytes();wal=dbpath.with_name(dbpath.name+'-wal').read_bytes()
        calls,ev=self.captured(paths=[dbpath])
        self.assertEqual(ev.problems,[])
        self.assertEqual(len(calls),3)
        prov=calls[0].kwargs
        self.assertEqual(prov['sqlite_base_sha256'],hashlib.sha256(base).hexdigest())
        self.assertEqual(prov['sqlite_wal_sha256'],hashlib.sha256(wal).hexdigest())
        self.assertIn(prov['sqlite_wal_sha256'],json.loads(calls[0].args[1]))
        self.assertEqual(prov['sqlite_wal_source_scope']['source_snapshot'],'base-volume')

    def test_aggregate_budget_prevents_reading_extra_container(self):
        other=self.path.parent/'second.log';other.write_bytes(self.data)
        with patch.object(cloud,'MAX_TOTAL_BYTES',len(self.data)),patch.object(cloud,'_read',wraps=cloud._read) as read:
            calls,ev=self.captured(paths=[self.path,other])
        self.assertEqual(read.call_count,1)
        self.assertTrue(any('aggregate byte bound' in problem for problem in ev.problems))

    def test_real_fixed_roles_emit_native_triples(self):
        required={'cloud.container.service','cloud.container.type','cloud.container.path',P+'document_id',P+'file_name',P+'server_modified_at',P+'deletion_record_server_modified_at'}
        self.assertTrue(required<=ROLES.keys(),'central reviewed cloud roles must be integrated')
        ev=Evidence();cloud.extract_paths(ev,[self.path],self.ctx)
        self.assertEqual(ev.problems,[])
        self.assertEqual(len(ev.rows()),36)
        self.assertTrue(all(row[1]==999 for row in ev.rows()))


if __name__=='__main__':
    unittest.main()
