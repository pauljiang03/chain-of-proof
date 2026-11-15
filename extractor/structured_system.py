"""Partition table entries and current-hive configuration fields."""
from __future__ import annotations

import hashlib
import json

from . import system
from .attributes import emit_attribute
from .source_scope import merge_scope, subject_scope

MAX_REGISTRY_VALUES = 4096
MAX_TEXT = 65536
MAX_PATTERNS = 4096
SEARCH_KEY = r'Microsoft\Windows Search'
EXCLUSION_KEY = r'Control\BackupRestore\FilesNotToSnapshot'
SERVICE_START_TYPES = {0: 'SERVICE_BOOT_START', 1: 'SERVICE_SYSTEM_START', 2: 'SERVICE_AUTO_START',
                       3: 'SERVICE_DEMAND_START', 4: 'SERVICE_DISABLED'}
SERVICE_SOURCE = 'https://learn.microsoft.com/en-us/windows/win32/api/winsvc/ns-winsvc-query_service_configa'
EXCLUSION_SOURCE = 'https://learn.microsoft.com/en-us/windows/win32/vss/excluding-files-from-shadow-copies'


def _uint(value, maximum=(1 << 64) - 1):
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
        raise ValueError('expected bounded native unsigned integer')
    return int(value)


def _text(value):
    if not isinstance(value, str) or len(value) > MAX_TEXT or '\0' in value:
        raise ValueError('expected bounded native text without embedded NUL')
    return str(value)


def _scope(provenance):
    scope = subject_scope(provenance)
    if not all(isinstance(value, str) and value.strip() and value != 'unknown' for value in scope):
        raise ValueError('explicit image, exhibit, source snapshot and variant are required')
    return scope


def _subject(provenance, *parts):
    return json.dumps(_scope(provenance) + list(parts), ensure_ascii=True, separators=(',', ':'))


def _emit(ev, subject, values, ctx, provenance):
    for role, value in values:
        emit_attribute(ev, subject, role, value, ctx['examined_at'], **provenance)


def partitions(ev, target, ctx):
    """Read raw primary MBR entries; filesystem joins require disk identity too."""
    _scope(merge_scope(ctx['common']))
    common = merge_scope(ctx['common'], {'source_snapshot': 'evidence-image', 'source_variant': 'logical-image'})
    seen = set()
    for disk_index, disk in enumerate(target.disks):
        if id(disk) in seen:
            continue
        seen.add(id(disk))
        where = f'logical disk {disk_index} MBR'
        try:
            # Use the disk's sector size from Dissect, not a filesystem boot sector.
            size = _uint(disk.size)
            sector_size = _uint(disk.vs._disk.sector_size, 65536)
            if sector_size not in (512, 4096):
                raise ValueError('unsupported or unavailable logical sector size for MBR offset conversion')
            position = disk.tell()
            try:
                disk.seek(0)
                sector = disk.read(512)
            finally:
                disk.seek(position)
            if len(sector) != 512:
                raise ValueError('incomplete MBR sector')
            parsed = system.parse_mbr(sector)
            digest = hashlib.sha256(sector).hexdigest()
            disk_identity = f'logical-disk:{disk_index}:mbr-sha256:{digest}'
            for part in parsed:
                entry_offset = 446 + 16 * (part['number'] - 1)
                raw = sector[entry_offset:entry_offset + 16]
                art = f'{where} entry {part["number"]}'
                try:
                    if raw[0] not in (0, 0x80):
                        raise ValueError('MBR boot indicator is neither inactive 0x00 nor active 0x80')
                    start, count = part['start'], part['sectors']
                    offset, length = start * sector_size, count * sector_size
                    if not start or not count or offset + length > size:
                        raise ValueError('MBR entry has zero or out-of-disk sector bounds')
                    if part['type'] == 0xee:
                        raise ValueError('protective MBR entry is not a decoded GPT partition')
                    provenance = dict(common, artifact=art, source_path=f'logical disk {disk_index}',
                        parser='extractor.structured_system.partitions', disk_index=disk_index,
                        disk_identity=disk_identity, logical_disk_bytes=size, mbr_sha256=digest,
                        mbr_entry_byte_offset=entry_offset, mbr_entry_hex=raw.hex(),
                        partition_type_code=part['type'], logical_sector_bytes=sector_size,
                        partition_byte_offset=offset, partition_bytes=length,
                        filesystem_join='same target disk object, exact byte offset and size; never partition-type guessing',
                        limitation='literal primary MBR entry; no GPT/extended-partition census, printed size or boot success claim')
                    values = [('partition.number', part['number']), ('partition.bootable', raw[0] == 0x80),
                              ('partition.start_sector', start), ('partition.total_sectors', count)]
                    matches, joined = [], set()
                    for volume in target.volumes:
                        if volume.disk is not disk or id(volume) in joined:
                            continue
                        joined.add(id(volume))
                        try:
                            if _uint(volume.offset) == offset and _uint(volume.size) == length:
                                matches.append(volume)
                        except (TypeError, ValueError):
                            continue
                    if len(matches) == 1:
                        volume = matches[0]
                        filesystem = getattr(volume, 'fs', None)
                        label = getattr(filesystem, '__type__', None)
                        if isinstance(label, str) and label and label not in ('unknown', 'virtual'):
                            values.append(('partition.filesystem', label.upper()))
                            provenance['filesystem_join_endpoint'] = {
                                'disk_identity': disk_identity, 'partition_byte_offset': offset,
                                'partition_bytes': length, 'volume_number': _uint(volume.number),
                                'filesystem_parser_type': label, 'same_disk_object': True}
                        else:
                            ev.problem(art, ValueError('matched partition has no recognized filesystem parser'))
                    else:
                        ev.problem(art, ValueError('filesystem join is missing or ambiguous for this exact disk and partition bounds'))
                    _emit(ev, _subject(provenance, 'mbr-partition', disk_identity, entry_offset), values, ctx, provenance)
                except Exception as error:
                    ev.problem(art, error)
        except Exception as error:
            ev.problem(where, error)


def _registry_values(ev, hive, path):
    key = system._open(ev, hive, path)
    if key is None:
        return None, {}
    values, ambiguous = {}, set()
    try:
        for index, value in enumerate(key.values()):
            if index >= MAX_REGISTRY_VALUES:
                raise ValueError('registry value enumeration bound exceeded')
            name = _text(value.name)
            folded = name.casefold()
            if folded in values or folded in ambiguous:
                values.pop(folded, None)
                ambiguous.add(folded)
                ev.problem(system._art(hive, path, name), ValueError('ambiguous duplicate registry value name'))
                continue
            values[folded] = value
    except Exception as error:
        ev.problem(system._art(hive, path), error)
    return key, values


def _registry_provenance(ctx, hive, key, value, *, control_set=None):
    where = system._where(hive, control_set, control_set)
    # A hive named like the primary one does not override the caller's origin.
    if where.get('source_variant') == 'primary':
        where.pop('source_variant')
    path = key.path
    return merge_scope(ctx['common'], dict(where, artifact=system._art(hive, path, value.name),
        source_path=str(hive.path), source_hive=str(hive.path), registry_key=system._art(hive, path),
        registry_value_name=value.name, registry_value_type=_uint(value.type, 0xffffffff),
        parser='extractor.structured_system.registry',
        limitation='recorded configuration only; no running service, actual omission or current physical-system state claim'))


def registry(ev, target, ctx):
    _scope(merge_scope(ctx['common']))
    for hive in system._hives(ev, target):
        if system._where(hive)['source_variant'] != 'primary':
            continue
        if hive.name == 'SOFTWARE':
            key, values = _registry_values(ev, hive, SEARCH_KEY)
            for field in ('DataDirectory', 'DefaultDataDirectory', 'SetupCompletedSuccessfully'):
                value = values.get(field.casefold())
                if value is None:
                    continue
                try:
                    provenance = _registry_provenance(ctx, hive, key, value)
                    raw, value_type = value.value, provenance['registry_value_type']
                    if field == 'SetupCompletedSuccessfully':
                        if value_type != 4:
                            raise ValueError('Search setup value is not REG_DWORD')
                        role, decoded = 'search.config.value_integer', _uint(raw, 0xffffffff)
                    else:
                        if value_type not in (1, 2):
                            raise ValueError('Search directory value is not REG_SZ or REG_EXPAND_SZ')
                        role, decoded = 'search.config.value_text', _text(raw)
                    provenance['registry_native_value'] = decoded
                    _emit(ev, _subject(provenance, 'registry-value', str(hive.path), key.path, value.name),
                          [('search.config.registry_key', provenance['registry_key']),
                           ('search.config.value_name', str(value.name)), (role, decoded)], ctx, provenance)
                except Exception as error:
                    ev.problem(system._art(hive, SEARCH_KEY, field), error)
        elif hive.name == 'SYSTEM':
            current, _ = system._control_sets(ev, hive)
            if not current:
                ev.problem(str(hive.path), ValueError('current control set unavailable; Search service and snapshot exclusions not inferred'))
                continue
            path = current + r'\Services\WSearch'
            key, values = _registry_values(ev, hive, path)
            value = values.get('start')
            if value is not None:
                try:
                    provenance = _registry_provenance(ctx, hive, key, value, control_set=current)
                    if provenance['registry_value_type'] != 4:
                        raise ValueError('WSearch Start is not REG_DWORD')
                    code = _uint(value.value, 0xffffffff)
                    provenance.update(registry_native_value=code, interpretation_source=SERVICE_SOURCE)
                    fields = [('search.service.registry_key', provenance['registry_key']),
                              ('search.service.start_code', code)]
                    if code in SERVICE_START_TYPES:
                        fields.append(('search.service.start_type', SERVICE_START_TYPES[code]))
                    else:
                        ev.problem(system._art(hive, path, 'Start'), ValueError('Start code has no reviewed service-start enum label'))
                    _emit(ev, _subject(provenance, 'registry-value', str(hive.path), key.path, value.name), fields, ctx, provenance)
                except Exception as error:
                    ev.problem(system._art(hive, path, 'Start'), error)
            path = current + '\\' + EXCLUSION_KEY
            key, values = _registry_values(ev, hive, path)
            for value in values.values():
                try:
                    provenance = _registry_provenance(ctx, hive, key, value, control_set=current)
                    raw = value.value
                    if provenance['registry_value_type'] != 7 or not isinstance(raw, list):
                        raise ValueError('FilesNotToSnapshot value is not native REG_MULTI_SZ')
                    if len(raw) > MAX_PATTERNS:
                        raise ValueError('snapshot exclusion pattern bound exceeded')
                    patterns = [_text(item) for item in raw]
                    for index, pattern in enumerate(patterns):
                        prov = dict(provenance, multi_string_index=index, multi_string_count=len(patterns),
                                    registry_native_value=patterns, interpretation_source=EXCLUSION_SOURCE,
                                    limitation='literal exclusion configuration; applications apply it on a best-effort basis; no proof of omission from any shadow copy')
                        _emit(ev, _subject(prov, 'registry-multi-string', str(hive.path), key.path, value.name, index),
                              [('snapshot.exclusion.registry_key', prov['registry_key']),
                               ('snapshot.exclusion.value_name', str(value.name)),
                               ('snapshot.exclusion.pattern', pattern)], ctx, prov)
                except Exception as error:
                    ev.problem(system._art(hive, path, value.name), error)


def extract(ev, target, ctx):
    for name, reader in (('MBR partition attributes', partitions), ('current-hive configuration attributes', registry)):
        try:
            reader(ev, target, ctx)
        except Exception as error:
            ev.problem(name, error)
