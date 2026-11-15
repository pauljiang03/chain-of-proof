"""Synthetic PE/MUI bytes and retained language selectors; never load a DLL."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from extractor import registry_resources as rr, host_attributes as host, system
from extractor.store import Evidence


def pe(records):
    tree={}
    for kind,name,language,payload in records:
        tree.setdefault(kind,{}).setdefault(name,{})[language]=payload
    table=bytearray()
    def append(data,align=1):
        table.extend(b'\0'*(-len(table)%align));offset=len(table);table.extend(data);return offset
    def directory(nodes):
        at=append(bytes(16+8*len(nodes)),4)
        names=sorted(nodes,key=lambda n:(not isinstance(n,str),str(n)))
        struct.pack_into('<HH',table,at+12,sum(isinstance(n,str) for n in names),sum(isinstance(n,int) for n in names))
        for i,name in enumerate(names):
            encoded=name
            if isinstance(name,str):
                raw=name.encode('utf-16-le');encoded=0x80000000|append(struct.pack('<H',len(raw)//2)+raw,2)
            value=nodes[name]
            if isinstance(value,dict):child=directory(value)|0x80000000
            else:
                child=append(bytes(16),4);payload=append(value,4)
                struct.pack_into('<IIII',table,child,0x1000+payload,len(value),1200,0)
            struct.pack_into('<II',table,at+16+8*i,encoded,child)
        return at
    assert directory(tree)==0
    raw_size=(len(table)+511)&~511
    binary=bytearray(0x200+raw_size);binary[:2]=b'MZ';struct.pack_into('<I',binary,60,128)
    binary[128:132]=b'PE\0\0';struct.pack_into('<HHIIIHH',binary,132,0x14c,1,0,0,0,224,2)
    struct.pack_into('<H',binary,152,0x10b);struct.pack_into('<I',binary,212,512)
    struct.pack_into('<I',binary,244,16);struct.pack_into('<II',binary,264,0x1000,len(table))
    binary[376:384]=b'.rsrc\0\0\0';struct.pack_into('<IIII',binary,384,len(table),0x1000,raw_size,512)
    binary[512:512+len(table)]=table
    return binary


def strings(identifier=37,text='Arbitrary Daylight Label'):
    return b''.join(struct.pack('<H',len(value.encode('utf-16-le'))//2)+value.encode('utf-16-le')
                    for i in range(16) for value in [text if i==identifier%16 else ''])


def config(kind,language='zz-ZZ',checksum=bytes(range(1,17))):
    data=bytearray(132)
    struct.pack_into('<IIIIIII',data,0,0xfecdfecd,0,0x10000,0,kind,0,0)
    data[44:60]=checksum
    text=(language+'\0').encode('utf-16-le')
    pos=124 if kind&3==1 else 116
    struct.pack_into('<II',data,pos,len(data),len(text));data.extend(text)
    struct.pack_into('<I',data,4,len(data))
    return data


class ResourceBytes(unittest.TestCase):
    def test_sixteen_strings_and_physical_locator(self):
        data=pe([(6,3,1033,strings())])
        value,prov=rr.string_resource(data,37,1033)
        self.assertEqual(value,'Arbitrary Daylight Label')
        start=prov['string_byte_offset'];n=prov['string_byte_length']
        self.assertEqual(data[start:start+n].decode('utf-16-le'),value)
        self.assertEqual(prov['resource_name'],3)
        for identifier,language in ((38,1033),(37,1041),(4000,1033)):
            with self.assertRaises(ValueError):rr.string_resource(data,identifier,language)

    def test_truncated_block_bad_utf16_and_oversize_file_refuse(self):
        for payload in (strings()[:-1],strings()+b'\0\0',strings(text='bad\0value'),b'\xff\xff'):
            with self.assertRaises(ValueError):rr.string_resource(pe([(6,3,1033,payload)]),37,1033)
        with patch.object(rr,'MAX_PE_BYTES',20),self.assertRaises(ValueError):rr.resources(pe([(6,3,1033,strings())]),6)

    def test_mui_header_offsets_and_type_flags_not_zero_language_assumption(self):
        data=pe([('MUI',1,1033,config(0x12))])
        info=rr.mui_config(data)
        self.assertEqual(info['file_type'],2)
        self.assertEqual(info['raw_file_type'],0x12)
        self.assertEqual(info['resource_language'],1033)
        self.assertEqual(info['language'],'zz-ZZ')
        bad=config(2);struct.pack_into('<I',bad,116,4)
        with self.assertRaises(ValueError):rr.mui_config(pe([('MUI',1,1033,bad)]))
        with self.assertRaises(ValueError):rr.mui_config(pe([('MUI',1,1033,config(2)),('MUI',1,1041,config(2))]))

    def test_overlapping_sections_and_cycles_refuse(self):
        data=pe([(6,3,1033,strings())]);struct.pack_into('<H',data,134,2)
        data[416:456]=data[376:416]
        with self.assertRaises(ValueError):rr.resources(data,6)
        data=pe([(6,3,1033,strings())]);struct.pack_into('<I',data,532,0x80000000)
        with self.assertRaises(ValueError):rr.resources(data,6)


class SourceResolution(unittest.TestCase):
    def files(self,root,*,checksum=bytes(range(1,17)),language='zz-ZZ',resource_language=1033):
        (root/'tzres.dll').write_bytes(pe([('MUI',1,1033,config(0x11))]))
        localized=root/'zz-ZZ';localized.mkdir()
        (localized/'tzres.dll.mui').write_bytes(pe([('MUI',1,resource_language,config(0x12,language,checksum)),
                                                  (6,3,resource_language,strings())]))

    def test_bound_pair_without_host_locale_or_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.files(root)
            target=NS(resolve=lambda path: root)
            value,prov=rr.resolve_timezone_label(target,'@tzres.dll,-37','zz-ZZ',1033)
            self.assertEqual(value,'Arbitrary Daylight Label')
            self.assertEqual(prov['resources'][1]['sha256'],hashlib.sha256((root/'zz-ZZ/tzres.dll.mui').read_bytes()).hexdigest())
            self.assertEqual(prov['language_name'],'zz-ZZ')
            for indirect in ('@other.dll,-37','@../tzres.dll,-37','@tzres.dll,37','@tzres.dll,-37;v2'):
                with self.assertRaises(ValueError):rr.resolve_timezone_label(target,indirect,'zz-ZZ',1033)

    def test_wrong_checksum_language_missing_resource_and_symlink_refuse(self):
        for change in ({'checksum':b'x'*16},{'language':'yy-YY'},{'resource_language':1041}):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);self.files(root,**change)
                with self.assertRaises(ValueError):rr.resolve_timezone_label(NS(resolve=lambda _:root),'@tzres.dll,-37','zz-ZZ',1033)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.files(root)
            path=root/'zz-ZZ/tzres.dll.mui';moved=root/'elsewhere';path.rename(moved);path.symlink_to(moved)
            with self.assertRaises(ValueError):rr.resolve_timezone_label(NS(resolve=lambda _:root),'@tzres.dll,-37','zz-ZZ',1033)

    def test_reader_single_language_selection_preserves_indirect_input(self):
        hive=system.Hive('SYSTEM',None,r'C:\Windows\System32\config\SYSTEM',False,None,None)
        current='ControlSet003';path=current+r'\Control\MUI\UILanguages'
        child=NS(name='zz-ZZ',path=path+r'\zz-ZZ',values=lambda:[NS(name='LCID',value=1033)])
        key=NS(subkeys=lambda:[child])
        data={'Bias':300,'StandardBias':0,'DaylightBias':-60,'ActiveTimeBias':240,
              'StandardName':'Literal unused standard','DaylightName':'@tzres.dll,-37'}
        with patch.object(system,'_open',return_value=key),patch.object(host,'resolve_timezone_label',return_value=('Arbitrary Daylight Label',{'source':'fixture'})):
            value,prov=host.source_time_zone(Evidence(),object(),hive,current,data)
        self.assertEqual(value,'Arbitrary Daylight Label (UTC-04:00)')
        self.assertEqual(prov['time_zone_registry_inputs']['DaylightName'],'@tzres.dll,-37')
        self.assertEqual(prov['resolved_time_zone_labels']['DaylightName']['resolved_text'],'Arbitrary Daylight Label')
        for children in ([],[child,child]):
            with patch.object(system,'_open',return_value=NS(subkeys=lambda:children)),self.assertRaises(ValueError):
                host.source_time_zone(Evidence(),object(),hive,current,data)


if __name__=='__main__':unittest.main()
