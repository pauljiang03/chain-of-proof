"""Synthetic current-hive records; no private cases or asserted user activity."""
import json
import struct
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from extractor import host_attributes as host, system
from extractor.registry_fields import dword, interface_guid, text_value
from extractor.store import Evidence

GUID = '{12345678-1234-5678-90AB-1234567890AB}'
OTHER = '{87654321-4321-8765-BA09-BA0987654321}'
CURRENT = 'ControlSet002'
IFACES = CURRENT + r'\Services\Tcpip\Parameters\Interfaces'
CARDS = r'Microsoft\Windows NT\CurrentVersion\NetworkCards'
USERS = r'SAM\Domains\Account\Users'
CONTEXT = {'examined_at': 1800000000000000, 'common': {'image': 'fixture.E01', 'exhibit': 'OTHER',
           'source_snapshot': 'base-volume', 'source_variant': 'primary'}}


def node(path, values=None, children=()):
    return NS(path=path, name=path.rsplit('\\', 1)[-1], subkeys=lambda: list(children),
              values=lambda: [NS(name=k, value=v) for k, v in (values or {}).items()])


def run(keys, names):
    hives = [system.Hive(name, None, rf'C:\Windows\System32\config\{name}', False, None, None)
             for name in names]
    ev = Evidence()
    with patch.object(system, '_hives', return_value=hives), \
         patch.object(system, '_open', side_effect=lambda ev,h,path: keys.get((h.name,path))), \
         patch.object(system, '_control_sets', return_value=(CURRENT, [CURRENT])):
        host.extract(ev, None, CONTEXT)
    return ev


def attributes(ev):
    return {json.loads(row[-1])['attribute_role']: (json.loads(row[4]), json.loads(row[-1]))
            for row in ev.rows() if row[0] in ('attributeTextValue','attributeIntegerValue',
                                              'attributeSignedIntegerValue','attributeBooleanValue')}


class NativeFields(unittest.TestCase):
    def test_native_subclasses_not_bool_or_coerced_numbers(self):
        from dissect.cstruct import cstruct
        cs = cstruct()
        value = cs.uint32(b'\x01\0\0\0')
        self.assertEqual(dword(value,'x'),1)
        for bad in (True, -1, 2**32, '1', 1.0):
            with self.subTest(bad=bad), self.assertRaises(ValueError): dword(bad,'x')
        self.assertEqual(interface_guid(GUID.lower()), GUID)
        for bad in (GUID.strip('{}'), GUID+' ', 'not-a-guid'):
            with self.assertRaises(ValueError): interface_guid(bad)

    def test_strings_preserve_empty_and_single_member_without_joining(self):
        self.assertEqual(text_value('', 'x')[0], '')
        self.assertEqual(text_value(['  exact  '], 'x')[0], '  exact  ')
        for bad in ([], ['a','b'], ['a\0'], 4, None):
            with self.assertRaises(ValueError): text_value(bad,'x')


class SamFields(unittest.TestCase):
    def read(self, key_rid=1007, value_rid=1007, name='Arbitrary Name'):
        f = bytearray(68)
        struct.pack_into('<I',f,0x30,value_rid)
        struct.pack_into('<H',f,0x42,19)
        encoded = name.encode('utf-16-le')
        v = bytearray(204)+encoded
        struct.pack_into('<II',v,12,0,len(encoded))
        child = node(USERS+'\\'+f'{key_rid:08X}', {'F':bytes(f),'V':bytes(v)})
        return run({('SAM',USERS):node(USERS,children=[child])},['SAM'])

    def test_rid_name_counter_share_exact_account_source(self):
        ev=self.read();rows=attributes(ev)
        self.assertEqual(ev.problems,[])
        self.assertEqual(rows['account.rid'][0],1007)
        self.assertEqual(rows['account.name'][0],'Arbitrary Name')
        self.assertEqual(rows['account.logon_count'][0],19)
        self.assertTrue(rows['account.enabled'][0])
        subjects=[row[4] for row in ev.rows() if row[0]=='attributeSubject' and
                  json.loads(row[-1])['attribute_role']!='account.count']
        self.assertEqual(len(set(subjects)),1)
        self.assertIn('000003EF',subjects[0])
        self.assertEqual(rows['account.rid'][1]['value_byte_offset'],48)

    def test_mismatch_or_empty_name_does_not_emit_account_row(self):
        for kwargs in ({'key_rid':1008},{'name':''}):
            ev=self.read(**kwargs)
            self.assertEqual(set(attributes(ev)),{'account.count'})
            self.assertTrue(ev.problems)

    def test_reader_does_not_hardcode_public_name_exclusions(self):
        for name in ('Administrator','Guest','different-user'):
            ev=self.read(name=name)
            self.assertEqual(attributes(ev)['account.name'][0],name)
            self.assertFalse(any('exclusion' in role for role in attributes(ev)))


class DhcpFields(unittest.TestCase):
    def read(self, updates=None, services=None, descriptions=None):
        data={'EnableDHCP':1,'DhcpIPAddress':'192.0.2.42','DhcpSubnetMask':'255.255.255.0',
              'DhcpNameServer':'192.0.2.53 192.0.2.54','DhcpDomain':'',
              'DhcpDefaultGateway':['192.0.2.1'],'DhcpServer':'192.0.2.2',
              'LeaseObtainedTime':1000,'LeaseTerminatesTime':2000,'Lease':1000}
        if updates is not None: data=updates
        cards=[node(CARDS+'\\'+str(i),{'ServiceName':service,'Description':descriptions[i] if descriptions else 'Literal NIC'})
               for i,service in enumerate(services or [GUID.lower()])]
        entry=node(IFACES+'\\'+GUID,data)
        # No timezone fields: its independent diagnostic must not suppress DHCP.
        keys={('SOFTWARE',CARDS):node(CARDS,children=cards),('SYSTEM',IFACES):node(IFACES,children=[entry])}
        return run(keys,['SOFTWARE','SYSTEM'])

    def test_exact_guid_join_all_eight_fields_one_subject(self):
        ev=self.read();rows={k:v for k,v in attributes(ev).items() if k.startswith('network.dhcp.')}
        self.assertEqual(len(rows),8)
        self.assertEqual(rows['network.dhcp.default_gateway'][0],'192.0.2.1')
        self.assertEqual(rows['network.dhcp.domain'][0],'')
        self.assertEqual(rows['network.dhcp.name_server'][0],'192.0.2.53 192.0.2.54')
        self.assertIs(rows['network.dhcp.enabled'][0],True)
        subjects=[row[4] for row in ev.rows() if row[0]=='attributeSubject' and
                  json.loads(row[-1])['attribute_role'].startswith('network.dhcp.')]
        self.assertEqual(len(set(subjects)),1)
        for value,prov in rows.values():
            self.assertEqual(prov['adapter_guid'],GUID)
            self.assertEqual(len(prov['joined_registry_sources']),2)
            self.assertIn('not proof of lease assignment',prov['limitation'])
            self.assertEqual(prov['source_variant'],'primary')

    def test_no_static_fallback_or_missing_value_invention(self):
        ev=self.read({'EnableDHCP':0,'IPAddress':'198.51.100.3','DefaultGateway':['198.51.100.1']})
        rows={k:v for k,v in attributes(ev).items() if k.startswith('network.dhcp.')}
        self.assertEqual(set(rows),{'network.dhcp.device_name','network.dhcp.enabled'})
        self.assertIs(rows['network.dhcp.enabled'][0],False)

    def test_guid_ambiguity_and_mismatch_never_join_arbitrarily(self):
        for services in ([OTHER],[GUID,GUID.lower()]):
            ev=self.read(services=services)
            self.assertFalse(any(k.startswith('network.dhcp.') for k in attributes(ev)))
            self.assertTrue(any('unique' in issue for issue in ev.problems))

    def test_malformed_duplicate_service_name_still_blocks_join(self):
        ev=self.read(services=[GUID,GUID],descriptions=['Literal NIC',None])
        self.assertFalse(any(k.startswith('network.dhcp.') for k in attributes(ev)))

    def test_invalid_boolean_and_multiple_gateway_are_omitted(self):
        for enabled in (True,2,'1'):
            ev=self.read({'EnableDHCP':enabled,'DhcpDefaultGateway':['192.0.2.1','192.0.2.2']})
            rows=attributes(ev)
            self.assertNotIn('network.dhcp.enabled',rows)
            self.assertNotIn('network.dhcp.default_gateway',rows)

    def test_raw_signed_bias_is_retained_without_effective_label(self):
        key=CURRENT+r'\Control\TimeZoneInformation'
        ev=run({('SYSTEM',key):node(key,{'Bias':300,'StandardBias':0,'DaylightBias':0xffffffc4,
                                       'ActiveTimeBias':240,'TimeZoneKeyName':'Raw setting'})},['SYSTEM'])
        rows=attributes(ev)
        self.assertEqual(rows['os.time_zone.daylight_bias_minutes'][0],-60)
        self.assertEqual(rows['os.time_zone.daylight_bias_minutes'][1]['registry_native_value'],0xffffffc4)
        self.assertNotIn('os.effective_time_zone',rows)
        self.assertEqual(rows['os.time_zone_setting'][0],'Raw setting')

    def test_resource_read_error_keeps_other_registry_observations(self):
        key=CURRENT+r'\Control\TimeZoneInformation'
        with patch.object(host,'source_time_zone',side_effect=OSError('unreadable source resource')):
            ev=run({('SYSTEM',key):node(key,{'Bias':300,'TimeZoneKeyName':'Recorded setting'})},['SYSTEM'])
        rows=attributes(ev)
        self.assertEqual(rows['os.time_zone.bias_minutes'][0],300)
        self.assertEqual(rows['os.time_zone_setting'][0],'Recorded setting')
        self.assertTrue(any('unreadable source resource' in issue for issue in ev.problems))


if __name__=='__main__': unittest.main()
