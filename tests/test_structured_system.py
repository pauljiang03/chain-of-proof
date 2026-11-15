"""Source-only synthetic partition and registry joins; no case answer key."""
import io
import json
import struct
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from extractor import structured_system as reader, system
from extractor.store import Evidence

CTX = {'examined_at': 1800000000000000, 'common': {'image': 'fixture.raw', 'exhibit': 'DISK',
       'source_snapshot': 'base-volume', 'source_variant': 'primary'}}


def mbr(*entries):
    data = bytearray(512)
    data[510:] = b'\x55\xaa'
    for index, (boot, ptype, start, count) in enumerate(entries):
        offset = 446 + 16 * index
        data[offset], data[offset + 4] = boot, ptype
        struct.pack_into('<II', data, offset + 8, start, count)
    return bytes(data)


class Disk(io.BytesIO):
    def __init__(self, data, *, sector_size=512):
        super().__init__(data)
        self.size = 512 * 512
        self.vs = NS(_disk=NS(sector_size=sector_size))


def volume(disk, filesystem='ntfs', *, offset=512, size=5120):
    return NS(disk=disk, offset=offset, size=size, number=1, fs=NS(__type__=filesystem))


def attrs(ev, role=None):
    result=[]
    for kind, _, _, identity, value, raw in ev.rows():
        if kind not in ('attributeTextValue','attributeIntegerValue','attributeBooleanValue'):
            continue
        prov=json.loads(raw)
        if role is None or prov['attribute_role']==role:
            result.append((prov['attribute_role'],json.loads(value),identity,prov))
    return result


def value(name, data, vtype):
    return NS(name=name,value=data,type=vtype)


def hive(name, backup=False):
    return system.Hive(name,None,r'C:\Windows\System32\config'+'\\'+('RegBack\\' if backup else '')+name,
                       backup,None,None)


def registry_run(software=None, service=None, exclusions=None, *, current='ControlSet002', hives=None, ctx=CTX):
    paths={}
    if software is not None: paths[('SOFTWARE',reader.SEARCH_KEY)]=software
    if service is not None: paths[('SYSTEM',r'ControlSet002\Services\WSearch')]=service
    if exclusions is not None: paths[('SYSTEM','ControlSet002\\'+reader.EXCLUSION_KEY)]=exclusions
    opened=[]
    def open_key(ev,h,path):
        opened.append((h.name,path))
        items=paths.get((h.name,path))
        return NS(path=path,values=lambda:iter(items)) if items is not None else None
    ev=Evidence()
    with patch.object(system,'_hives',return_value=hives or [hive('SOFTWARE'),hive('SYSTEM')]), \
         patch.object(system,'_open',side_effect=open_key), \
         patch.object(system,'_control_sets',return_value=(current,['ControlSet001','ControlSet002'])):
        reader.registry(ev,None,ctx)
    return ev,opened


class StructuredSystem(unittest.TestCase):
    def test_partition_join_is_disk_and_bounds_not_offset_only(self):
        first,second=Disk(mbr((0x80,7,1,10))),Disk(mbr((0,7,1,10)))
        first.seek(17)
        ev=Evidence()
        reader.partitions(ev,NS(disks=[first,second],volumes=[volume(second,'fat'),volume(first,'ntfs')]),CTX)
        self.assertEqual(first.tell(),17)
        self.assertEqual(ev.problems,[])
        labels=attrs(ev,'partition.filesystem')
        self.assertEqual({row[1] for row in labels},{'FAT','NTFS'})
        self.assertEqual({row[3]['disk_index']:row[1] for row in labels},{0:'NTFS',1:'FAT'})
        self.assertEqual(len({row[2] for row in labels}),2)
        for _,_,_,prov in attrs(ev):
            self.assertEqual((prov['source_snapshot'],prov['source_variant']),('evidence-image','logical-image'))
            self.assertEqual(prov['mbr_entry_byte_offset'],446)
            self.assertEqual(prov['partition_byte_offset'],512)
        self.assertFalse(any(row[0]=='filesystemSet' for row in ev.rows()))

    def test_mbr_type_never_substitutes_for_filesystem_or_ambiguous_join(self):
        disk,foreign=Disk(mbr((0,7,1,10))),Disk(mbr((0,7,1,10)))
        for volumes in ([volume(foreign)],[volume(disk),volume(disk,'exfat')],
                        [volume(disk,size=5121)],[volume(disk,'virtual')]):
            ev=Evidence();reader.partitions(ev,NS(disks=[disk],volumes=volumes),CTX)
            self.assertEqual(attrs(ev,'partition.filesystem'),[])
            self.assertEqual(attrs(ev,'partition.bootable')[0][1],False)
            self.assertTrue(ev.problems)

    def test_invalid_boot_byte_bounds_and_protective_gpt_not_invented(self):
        for entry in ((1,7,1,10),(0,7,1,10000),(0,7,0,10),(0,0xee,1,10)):
            ev=Evidence();disk=Disk(mbr(entry))
            reader.partitions(ev,NS(disks=[disk],volumes=[]),CTX)
            self.assertEqual(attrs(ev),[])
            self.assertTrue(ev.problems)

    def test_sector_size_is_explicit_and_disk_aliases_deduplicate(self):
        disk=Disk(mbr((0,7,1,10)),sector_size=4096)
        ev=Evidence();reader.partitions(ev,NS(disks=[disk,disk],volumes=[volume(disk,offset=4096,size=40960)]),CTX)
        self.assertEqual(len(attrs(ev,'partition.number')),1)
        self.assertEqual(attrs(ev,'partition.filesystem')[0][3]['partition_byte_offset'],4096)
        disk.vs._disk.sector_size=True
        ev=Evidence();reader.partitions(ev,NS(disks=[disk],volumes=[]),CTX)
        self.assertEqual(attrs(ev),[])
        self.assertTrue(ev.problems)

    def test_search_values_and_service_start_are_literal_current_configuration(self):
        class DWORD(int): pass
        ev,opened=registry_run(software=[value('DataDirectory',r'%ProgramData%\Search\Data'+'\\',2),
                                value('SetupCompletedSuccessfully',DWORD(0),4)],
                              service=[value('Start',DWORD(2),4)])
        self.assertEqual(ev.problems,[])
        self.assertEqual(attrs(ev,'search.config.value_text')[0][1],r'%ProgramData%\Search\Data'+'\\')
        self.assertEqual(attrs(ev,'search.config.value_integer')[0][1],0)
        self.assertEqual(attrs(ev,'search.service.start_code')[0][1],2)
        self.assertEqual(attrs(ev,'search.service.start_type')[0][1],'SERVICE_AUTO_START')
        key=attrs(ev,'search.service.registry_key')[0]
        self.assertEqual(key[1],r'HKLM\SYSTEM\ControlSet002\Services\WSearch')
        self.assertEqual(key[3]['control_set'],'ControlSet002')
        self.assertEqual(key[3]['current_control_set'],'ControlSet002')
        self.assertFalse(any('ControlSet001\\Services' in path for _,path in opened))
        self.assertFalse(any('running' in role or 'enabled' in role for role,_,_,_ in attrs(ev)))

    def test_exclusion_tuple_is_per_actual_value_and_multi_string_element(self):
        patterns=[r'$UserProfile$\mail\*.ost',r'$AllVolumes$\cache\*.tmp /s']
        ev,_=registry_run(exclusions=[value('OutlookOST',patterns,7),value('OtherApplication',[''],7)])
        self.assertEqual(ev.problems,[])
        emitted=attrs(ev,'snapshot.exclusion.pattern')
        self.assertEqual({row[1] for row in emitted},set(patterns+['']))
        self.assertEqual({row[3]['multi_string_index'] for row in emitted},{0,1})
        self.assertEqual(len({row[2] for row in emitted}),3)
        for _,_,identity,prov in emitted:
            roles={role for role,_,other_id,_ in attrs(ev) if other_id==identity}
            # Each attribute has its own triple ID; shared source subject is tested below.
            self.assertTrue(roles)
            self.assertIn('best-effort',prov['limitation'])
        subjects={row[4] for row in ev.rows() if row[0]=='attributeSubject'}
        self.assertEqual(len(subjects),3)
        self.assertFalse(any('excluded' in role for role,_,_,_ in attrs(ev)))

    def test_missing_current_control_set_backup_and_bad_native_types_remain_unknown(self):
        ev,opened=registry_run(service=[value('Start',2,4)],exclusions=[value('OutlookOST',['*.ost'],7)],current=None)
        self.assertEqual(attrs(ev),[])
        self.assertTrue(ev.problems)
        self.assertFalse(any('Services' in path for _,path in opened))
        ev,_=registry_run(software=[value('DataDirectory','value',1)],hives=[hive('SOFTWARE',backup=True)])
        self.assertEqual(attrs(ev),[])
        ev,_=registry_run(software=[value('DataDirectory',b'bytes',3),value('SetupCompletedSuccessfully',True,4)],
                          service=[value('Start','2',1)],exclusions=[value('OutlookOST','*.ost',1)])
        self.assertEqual(attrs(ev),[])
        self.assertEqual(len(ev.problems),4)

    def test_source_axes_and_duplicate_names_do_not_silently_merge(self):
        ev,_=registry_run(software=[value('DataDirectory','first',1),value('DATADIRECTORY','second',1)])
        self.assertEqual(attrs(ev),[])
        self.assertTrue(ev.problems)
        ctx=dict(CTX,common=dict(CTX['common'],source_variant='recovered'))
        ev,_=registry_run(service=[value('Start',3,4)],ctx=ctx)
        self.assertTrue(attrs(ev))
        self.assertTrue(all(row[3]['source_variant']=='recovered' for row in attrs(ev)))
        ctx=dict(CTX,common=dict(CTX['common'],source_snapshot='unknown'))
        with self.assertRaisesRegex(ValueError,'source snapshot'):
            registry_run(service=[value('Start',3,4)],ctx=ctx)


if __name__=='__main__': unittest.main()
