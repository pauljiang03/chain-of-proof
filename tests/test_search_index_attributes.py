"""Exact ESE row field bindings using a synthetic parser adapter, no gold data."""
import hashlib
import io
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from extractor import filetraces as reader
from extractor.store import Evidence, FILETIME_EPOCH_100NS

COMMON={'image':'other.raw','exhibit':'WORKSTATION','source_snapshot':'base-volume','source_variant':'primary'}
EXAMINED=1800000000000000
MODIFIED=1700000000123456
CREATED=1600000000654321


class SourcePath:
    data=b'immutable synthetic ESE parser input'
    declared_size=None
    def __str__(self): return reader.SEARCH_DB
    def exists(self): return True
    def stat(self): return NS(st_size=len(self.data) if self.declared_size is None else self.declared_size)
    def open(self,mode): return io.BytesIO(self.data)


class Table:
    def __init__(self,name,records,columns=None):
        self.name=name;self._rows=records
        self.column_names=columns if columns is not None else list(dict.fromkeys(k for row in records for k in row))
    def records(self): yield from self._rows


def source_row(doc=17,big=True):
    return {'DocID':doc,'1-System_ItemUrl':'iehistory://{S-1-5-21-1}/https://example.test/a',
      '2-System_ItemPathDisplay':r'D:\Users\Other\Desktop\note.txt',
      '3-System_DateModified':(MODIFIED*10+FILETIME_EPOCH_100NS).to_bytes(8,'big' if big else 'little'),
      '4-System_DateCreated':(CREATED*10+FILETIME_EPOCH_100NS).to_bytes(8,'big' if big else 'little'),
      '5-System_Search_Store':'iehistory','6-System_ItemType':'.url','7-System_Kind':['link','document'],
      '8-System_ThumbnailCacheId':(999).to_bytes(8,'big' if big else 'little')}


def run(tables,*,examined=EXAMINED,common=COMMON,state=3,path=None,on_parse=None):
    path=path or SourcePath()
    by_name={table.name:table for table in tables}
    captured=[]
    def parser(stream):
        captured.append(stream.read());stream.seek(0)
        if on_parse: on_parse(path)
        return NS(header=NS(dbstate=state),table=lambda name:by_name[name])
    target=NS(fs=NS(path=lambda name:path))
    ev=Evidence()
    with patch('dissect.database.ese.ESE',side_effect=parser),patch.object(reader,'_sid_names',return_value={}):
        thumbs=reader._search_index(ev,target,common,examined_at=examined)
    return ev,thumbs,captured


def attrs(ev,role=None):
    subject_by_id={row[3]:row[4] for row in ev.rows() if row[0]=='attributeSubject'}
    result=[]
    for kind,observed,_,identity,value,raw in ev.rows():
        if kind not in ('attributeTextValue','attributeIntegerValue','attributeBooleanValue'): continue
        prov=json.loads(raw)
        if role is None or prov['attribute_role']==role:
            result.append((prov['attribute_role'],json.loads(value),subject_by_id[identity],prov,observed))
    return result


class SearchAttributes(unittest.TestCase):
    def test_exact_fields_share_container_table_docid_and_distinct_timestamp_roles(self):
        ev,thumbs,captured=run([Table('SystemIndex_0A',[source_row()])])
        self.assertEqual(ev.problems,[])
        self.assertEqual(len({row[2] for row in attrs(ev)}),1)
        values={role:value for role,value,_,_,_ in attrs(ev)}
        self.assertEqual(values['search.index.item_url'],source_row()['1-System_ItemUrl'])
        self.assertEqual(values['search.index.item_path'],source_row()['2-System_ItemPathDisplay'])
        self.assertEqual(values['search.index.date_modified'],'2023-11-14T22:13:20.1234560Z')
        self.assertEqual(values['search.index.date_created'],'2020-09-13T12:26:40.6543210Z')
        self.assertEqual(values['search.index.store'],'iehistory')
        self.assertEqual(values['search.index.document_id'],17)
        self.assertEqual({row[1] for row in attrs(ev,'search.index.kind')},{'link','document'})
        for _,_,_,prov,observed in attrs(ev):
            self.assertEqual(prov['source_sha256'],hashlib.sha256(captured[0]).hexdigest())
            self.assertEqual(prov['source_snapshot'],'base-volume')
            self.assertEqual(observed,EXAMINED)
        self.assertEqual(thumbs['00000000000003e7'],[(source_row()['2-System_ItemPathDisplay'],17)])
        self.assertFalse(any(row[0] in ('webVisit','fileCreated') for row in ev.rows()))

    def test_table_byte_order_and_work_id_remain_explicit(self):
        row=source_row(big=False);row['WorkID']=row.pop('DocID')
        ev,_,_=run([Table('SystemIndex_PropertyStore',[row])])
        self.assertEqual(ev.problems,[])
        self.assertEqual(attrs(ev,'search.index.identifier_column')[0][1],'WorkID')
        self.assertEqual(attrs(ev,'search.index.date_modified')[0][1],'2023-11-14T22:13:20.1234560Z')
        self.assertEqual(attrs(ev,'search.index.date_modified')[0][3]['byte_order'],'little')

    def test_all_seven_filetime_fraction_digits_survive_both_byte_orders(self):
        for big,table_name in ((True,'SystemIndex_0A'),(False,'SystemIndex_PropertyStore')):
            row=source_row(big=big)
            row['3-System_DateModified']=(MODIFIED*10+FILETIME_EPOCH_100NS+7).to_bytes(8,'big' if big else 'little')
            row['4-System_DateCreated']=(CREATED*10+FILETIME_EPOCH_100NS+9).to_bytes(8,'big' if big else 'little')
            ev,_,_=run([Table(table_name,[row])])
            self.assertEqual(attrs(ev,'search.index.date_modified')[0][1],'2023-11-14T22:13:20.1234567Z')
            self.assertEqual(attrs(ev,'search.index.date_created')[0][1],'2020-09-13T12:26:40.6543219Z')
            self.assertEqual(attrs(ev,'search.index.date_modified')[0][3]['value_precision'],'100ns')
            # The generic fileSeen row keeps microsecond time.
            self.assertIn(MODIFIED,{record[1] for record in ev.rows() if record[0]=='fileSeen'})

    def test_same_docid_in_distinct_rows_tables_or_source_snapshots_does_not_join(self):
        row=source_row();other=source_row();other['2-System_ItemPathDisplay']=r'D:\Different\file.txt'
        ev,_,_=run([Table('SystemIndex_0A',[row,other]),Table('SystemIndex_PropertyStore',[source_row(big=False)])])
        self.assertEqual(len({row[2] for row in attrs(ev)}),3)
        second,_,_=run([Table('SystemIndex_0A',[row])],common=dict(COMMON,source_variant='recovered'))
        self.assertTrue({row[2] for row in attrs(ev)}.isdisjoint({row[2] for row in attrs(second)}))

    def test_url_never_fills_missing_native_path_and_unset_dates_are_not_exam_time(self):
        row=source_row();row.pop('2-System_ItemPathDisplay');row['3-System_DateModified']=b'\0'*8
        row['4-System_DateCreated']=(1).to_bytes(8,'big')
        ev,_,_=run([Table('SystemIndex_0A',[row])])
        self.assertEqual(attrs(ev,'search.index.item_path'),[])
        self.assertEqual(attrs(ev,'search.index.date_modified'),[])
        self.assertEqual(attrs(ev,'search.index.date_created'),[])
        self.assertTrue(attrs(ev,'search.index.item_url'))

    def test_bad_identifier_or_unknown_source_cannot_make_typed_row(self):
        for doc in (None,True,-1,'17',b'17'):
            ev,_,_=run([Table('SystemIndex_0A',[source_row(doc)])])
            self.assertEqual(attrs(ev),[])
            self.assertTrue(ev.problems)
        ev,_,_=run([Table('SystemIndex_0A',[source_row()])],common=dict(COMMON,source_snapshot='unknown'))
        self.assertEqual(attrs(ev),[])
        self.assertTrue(ev.problems)
        ev,_,_=run([Table('SystemIndex_0A',[source_row()])],examined=None)
        self.assertEqual(attrs(ev),[])
        self.assertTrue(any(row[0]=='fileSeen' for row in ev.rows()))

    def test_native_integer_subclass_and_literal_empty_field_are_preserved(self):
        class DWORD(int): pass
        row=source_row(DWORD(0));row['2-System_ItemPathDisplay']=''
        ev,_,_=run([Table('SystemIndex_0A',[row])])
        self.assertEqual(ev.problems,[])
        self.assertEqual(attrs(ev,'search.index.document_id')[0][1],0)
        self.assertEqual(attrs(ev,'search.index.item_path')[0][1],'')

    def test_malformed_dates_categories_and_columns_are_not_repaired(self):
        row=source_row();row['3-System_DateModified']='2023-11-14';row['7-System_Kind']=b'IE history'
        ev,_,_=run([Table('SystemIndex_0A',[row])])
        self.assertEqual(attrs(ev,'search.index.date_modified'),[])
        self.assertEqual(attrs(ev,'search.index.kind'),[])
        self.assertTrue(attrs(ev,'search.index.date_created'))
        self.assertEqual(len(ev.problems),2)
        for columns in (['DocID','1-System_ItemUrl','2-System_ItemUrl'],['DocID','evil-System_ItemUrl']):
            ev,_,_=run([Table('SystemIndex_0A',[row],columns=columns)])
            self.assertEqual(attrs(ev),[])
            self.assertTrue(ev.problems)

    def test_record_and_byte_bounds_report_partial_work_without_completeness(self):
        with patch.object(reader,'MAX_SEARCH_RECORDS',1):
            ev,_,_=run([Table('SystemIndex_0A',[source_row(1),source_row(2)])])
        self.assertEqual(len(attrs(ev,'search.index.document_id')),1)
        self.assertTrue(any('bound' in problem for problem in ev.problems))
        self.assertFalse(any(row[0]=='filesystemSet' for row in ev.rows()))
        with patch.object(reader,'MAX_SEARCH_DATABASE_BYTES',1):
            ev,_,captured=run([Table('SystemIndex_0A',[source_row()])])
        self.assertEqual(attrs(ev),[]);self.assertEqual(captured,[])
        self.assertTrue(ev.problems)

    def test_parsed_bytes_are_frozen_hash_bound_and_dirty_state_is_visible(self):
        path=SourcePath();original=path.data
        ev,_,captured=run([Table('SystemIndex_0A',[source_row()])],state=2,path=path,
                         on_parse=lambda p:setattr(p,'data',b'different subsequent source bytes'))
        self.assertEqual(captured,[original])
        self.assertEqual(attrs(ev,'search.index.document_id')[0][3]['source_sha256'],hashlib.sha256(original).hexdigest())
        self.assertTrue(any('transaction logs were not replayed' in problem for problem in ev.problems))
        self.assertTrue(all(row[3]['ese_database_state']==2 for row in attrs(ev)))

    def test_truncated_or_oversized_container_never_reaches_parser(self):
        for delta in (-1,1):
            path=SourcePath();path.declared_size=len(path.data)+delta
            with self.assertRaisesRegex(ValueError,'advertised'):
                run([Table('SystemIndex_0A',[source_row()])],path=path)


if __name__=='__main__': unittest.main()
