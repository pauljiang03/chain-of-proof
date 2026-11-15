"""Configured DHCP settings per network card, from the current hives."""
import json
from . import system
from .registry_fields import dword, interface_guid, text_value

CARDS = r'Microsoft\Windows NT\CurrentVersion\NetworkCards'
FIELDS = [('DhcpIPAddress', 'ip_address'), ('DhcpSubnetMask', 'subnet_mask'),
          ('DhcpNameServer', 'name_server'), ('DhcpDomain', 'domain'),
          ('DhcpDefaultGateway', 'default_gateway'), ('DhcpServer', 'server')]


def emit_dhcp(ev, hives, subject, emit):
    software = [h for h in hives if h.name == 'SOFTWARE']
    systems = [h for h in hives if h.name == 'SYSTEM']
    if not software or not systems:
        return
    if len(software) != 1 or len(systems) != 1:
        ev.problem('DHCP source join', ValueError('requires unique current SOFTWARE and SYSTEM hives'))
        return
    sh, hive = software[0], systems[0]
    current, _ = system._control_sets(ev, hive)
    if not current:
        return
    cards = {}
    key = system._open(ev, sh, CARDS)
    if key is not None:
        for card in system._subkeys(ev, sh, key):
            values = system._vals(ev, sh, card)
            try:
                guid = interface_guid(values.get('ServiceName'))
            except ValueError as error:
                ev.problem(system._art(sh, card.path), error)
                continue
            description = None
            try:
                description, _ = text_value(values.get('Description'), 'Description')
                if not description:
                    raise ValueError('NetworkCards Description is empty')
            except ValueError as error:
                ev.problem(system._art(sh, card.path), error)
            # A malformed duplicate still makes the ServiceName join ambiguous.
            cards.setdefault(guid, []).append((card, values, description))
    path = current + r'\Services\Tcpip\Parameters\Interfaces'
    key = system._open(ev, hive, path)
    if key is None:
        return
    for entry in system._subkeys(ev, hive, key):
        data = system._vals(ev, hive, entry)
        if not any(name in data for name, _ in FIELDS) and 'EnableDHCP' not in data:
            continue
        try:
            guid = interface_guid(entry.name)
            matches = cards.get(guid, [])
            if len(matches) != 1:
                raise ValueError('interface GUID has no unique current NetworkCards.ServiceName match')
            card, cv, description = matches[0]
            if not description:
                raise ValueError('matched NetworkCards description is unavailable')
            owner = subject + ':dhcp-interface:' + json.dumps([str(hive.path), entry.path,
                str(sh.path), card.path, guid], ensure_ascii=True, separators=(',', ':'))
            provenance = dict(adapter_guid=guid,
                joined_registry_sources=[{'artifact': system._art(hive, entry.path),
                    'source_hive': str(hive.path), 'registry_key': entry.path},
                    {'artifact': system._art(sh, card.path, 'ServiceName'),
                     'source_hive': str(sh.path), 'registry_key': card.path,
                     'registry_value': 'ServiceName', 'raw_value': cv['ServiceName']}],
                lease_registry_inputs={name: data[name] for name in
                    ('Lease', 'LeaseObtainedTime', 'LeaseTerminatesTime') if name in data},
                limitation='literal same-GUID current-hive DHCP configuration; not proof of lease assignment, current connectivity or actual use')
            emit(sh, card.path, 'Description', 'network.dhcp.device_name', description,
                 owner=owner, registry_native_value=cv['Description'], **provenance)
            for field, suffix in FIELDS:
                if field not in data:
                    continue
                try:
                    value, representation = text_value(data[field], field)
                    emit(hive, entry.path, field, 'network.dhcp.' + suffix, value, owner=owner,
                         registry_native_value=data[field], registry_representation=representation, **provenance)
                except ValueError as error:
                    ev.problem(system._art(hive, entry.path, field), error)
            if 'EnableDHCP' in data:
                enabled = dword(data['EnableDHCP'], 'EnableDHCP')
                if enabled not in (0, 1):
                    raise ValueError('EnableDHCP is not canonical 0 or 1')
                emit(hive, entry.path, 'EnableDHCP', 'network.dhcp.enabled', bool(enabled),
                     owner=owner, registry_native_value=data['EnableDHCP'], **provenance)
        except ValueError as error:
            ev.problem(system._art(hive, entry.path), error)
