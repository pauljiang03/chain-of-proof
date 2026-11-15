"""Typed Windows configuration and account observations, independent of case names.

The existing system reader also retains historical copies and activity records.
These attributes identify exact current-hive fields for public answer contracts.
They do not infer personal identity, habitual use, or successful authentication
from a configuration value or a SAM counter.
"""
from __future__ import annotations

import re
import struct
import json
from datetime import datetime, timezone

from .attributes import emit_attribute
from .source_scope import merge_scope, subject_scope
from . import system


def iso_seconds(seconds):
    if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds < 0:
        raise ValueError("expected nonnegative Unix seconds")
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def build_number(value):
    """Decode only a canonical unsigned decimal/DWORD registry build value.

    Preserve the original value in provenance. Versions, whitespace, leading
    zeroes, signs and floating-point values are not silently repaired.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        number = int(value)
    elif isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]{0,9}", value):
        number = int(value)
    else:
        raise ValueError("CurrentBuildNumber is not a canonical unsigned decimal value")
    if not 0 <= number <= 0xffffffff:
        raise ValueError("CurrentBuildNumber is outside the unsigned DWORD range")
    return number


TIME_ZONE_FIELDS = ('Bias', 'StandardBias', 'DaylightBias', 'ActiveTimeBias')
TIME_ZONE_DISABLE_FIELDS = ('DynamicDaylightTimeDisabled', 'DisableAutoDaylightTimeSet')
TIME_ZONE_SOURCES = (
    'https://learn.microsoft.com/en-us/windows/win32/api/timezoneapi/ns-timezoneapi-time_zone_information',
    'https://learn.microsoft.com/en-us/windows/win32/api/timezoneapi/ns-timezoneapi-dynamic_time_zone_information',
)


def _signed_bias(value, field):
    """Accept native LONG or DWORD representations, never text/float/bool casts."""
    if not isinstance(value, int) or isinstance(value, bool) or not -(1 << 31) <= value <= 0xffffffff:
        raise ValueError(f'{field} is not a signed LONG or unsigned DWORD integer')
    value = int(value)
    return value - (1 << 32) if value >= (1 << 31) else value


def effective_time_zone(data):
    """Display only an unambiguous correspondence in the recorded bias fields.

    Microsoft defines UTC = local time + bias, with StandardBias/DaylightBias
    added to Bias. Those adjustments depend on transition dates at runtime; we
    do not evaluate dates or claim an actual operating-system DST state here.
    ActiveTimeBias is compared with the stored sums, not inferred from a clock.
    A dynamic-DST disable flag alone can still allow fixed transition dates, so
    the conservative flag check below does not resolve an ambiguous label.
    """
    raw, decoded = {}, {}
    for field in TIME_ZONE_FIELDS:
        if field not in data:
            raise ValueError(f'effective recorded time zone needs {field}')
        raw[field] = data[field]
        decoded[field] = _signed_bias(data[field], field)
    disabled = {}
    for field in TIME_ZONE_DISABLE_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if not isinstance(value, int) or isinstance(value, bool) or value not in (0, 1):
            raise ValueError(f'{field} must be a canonical DWORD 0 or 1')
        raw[field] = value
        disabled[field] = int(value)
    if len(set(disabled.values())) > 1:
        raise ValueError('recorded daylight-control settings differ; this rule does not resolve their combination')
    totals = {field: decoded['Bias'] + decoded[field] for field in ('StandardBias', 'DaylightBias')}
    active = decoded['ActiveTimeBias']
    if any(abs(value) >= 24 * 60 for value in (active, *totals.values())):
        raise ValueError('recorded bias exceeds the supported UTC offset range (less than 24 hours)')
    matched = [field for field, total in totals.items() if total == active]
    if not matched:
        raise ValueError('ActiveTimeBias matches neither recorded standard nor daylight total')
    if any(disabled.values()) and 'StandardBias' not in matched:
        raise ValueError('daylight-only bias correspondence with a daylight-disable setting is unsupported by this rule')
    labels = {}
    for field in matched:
        name_field = field.replace('Bias', 'Name')
        name = data.get(name_field)
        if (not isinstance(name, str) or not name.strip() or name != name.strip()
                or any(ord(char) < 32 or ord(char) == 127 for char in name)
                or name.startswith('@')):
            raise ValueError(f'{name_field} is missing, malformed, or an unresolved resource label')
        raw[name_field] = name
        labels[name_field] = name
    if len(set(labels.values())) != 1:
        raise ValueError('active bias matches different standard/daylight labels; effective display is ambiguous')
    label = next(iter(labels.values()))
    offset = -active
    hours, minutes = divmod(abs(offset), 60)
    rendered = f'{label} (UTC{"+" if offset >= 0 else "-"}{hours:02d}:{minutes:02d})'
    return rendered, {
        'time_zone_registry_inputs': raw,
        'decoded_bias_minutes': decoded,
        'standard_total_bias_minutes': totals['StandardBias'],
        'daylight_total_bias_minutes': totals['DaylightBias'],
        'matched_bias_fields': matched,
        'matched_name_fields': list(labels),
        'daylight_disable_settings': disabled,
        'utc_offset_minutes': offset,
        'value_conversion': 'match recorded ActiveTimeBias to Bias + StandardBias/DaylightBias; UTC offset is -ActiveTimeBias',
        'display_convention': '<literal matched name> (UTC+HH:MM or UTC-HH:MM); zero uses UTC+00:00',
        'interpretation_sources': list(TIME_ZONE_SOURCES),
        'limitation': 'recorded active-bias correspondence only; no physical-clock accuracy, actual DST-state, '
                      'or transition-date correctness claim; no examination-date or calendar inference',
    }


def extract(ev, target, ctx):
    hives = [h for h in system._hives(ev, target) if system._where(h)['source_variant'] == 'primary']
    subject = f"{ctx['common']['exhibit']}:{ctx['common']['image']}:windows-system"

    def emit(hive, path, field, role, value, *, owner=subject, **extra):
        provenance = merge_scope(ctx["common"], dict(system._where(hive), reader="host_attributes",
                                 artifact=system._art(hive, path, field), source_hive=str(hive.path),
                                 registry_key=path, registry_value=field, **extra))
        scoped_owner = json.dumps(subject_scope(provenance) + [owner], ensure_ascii=True, separators=(',', ':'))
        emit_attribute(ev, scoped_owner, role, value, ctx["examined_at"], **provenance)

    def values(hive, path):
        key = system._open(ev, hive, path)
        return system._vals(ev, hive, key) if key is not None else {}

    for hive in hives:
        if hive.name == "SOFTWARE":
            path = r"Microsoft\Windows NT\CurrentVersion"
            data = values(hive, path)
            for field, role in (("ProductName", "os.product_name"),
                                ("RegisteredOwner", "os.registered_owner"),
                                ("CurrentVersion", "os.version"),
                                ("SystemRoot", "os.system_root")):
                if isinstance(data.get(field), str) and data[field]:
                    emit(hive, path, field, role, data[field])
            if "CurrentBuildNumber" in data:
                try:
                    raw_build = data["CurrentBuildNumber"]
                    emit(hive, path, "CurrentBuildNumber", "os.build_number", build_number(raw_build),
                         registry_native_value=raw_build,
                         value_conversion="canonical unsigned decimal or DWORD to integer")
                except ValueError as error:
                    ev.problem(system._art(hive, path, "CurrentBuildNumber"), error)
            if isinstance(data.get("InstallDate"), int) and not isinstance(data["InstallDate"], bool) and data["InstallDate"] > 0:
                emit(hive, path, "InstallDate", "os.install_time", iso_seconds(data["InstallDate"]),
                     value_time_meaning="recorded installation time; Unix seconds UTC")
            path = r"Microsoft\Windows NT\CurrentVersion\Winlogon"
            data = values(hive, path)
            if isinstance(data.get("DefaultUserName"), str) and data["DefaultUserName"]:
                emit(hive, path, "DefaultUserName", "account.last_logon_name", data["DefaultUserName"],
                     limitation="retained default/last-logon setting; does not prove a successful logon event")
            # NetworkCards is an inventory, independent of DHCP configuration.
            path = r"Microsoft\Windows NT\CurrentVersion\NetworkCards"
            key = system._open(ev, hive, path)
            if key is not None:
                for card in system._subkeys(ev, hive, key):
                    data = system._vals(ev, hive, card)
                    if isinstance(data.get("Description"), str) and data["Description"]:
                        emit(hive, card.path, "Description", "network.description", data["Description"],
                             owner=subject + ":network-card:" + card.name)
        elif hive.name == "SYSTEM":
            current, _sets = system._control_sets(ev, hive)
            if not current:
                ev.problem("host attributes current control set", ValueError(
                    "Select\\Current missing; no fallback control set labeled current"))
                continue
            path = current + r"\Control\ComputerName\ComputerName"
            data = values(hive, path)
            if isinstance(data.get("ComputerName"), str) and data["ComputerName"]:
                emit(hive, path, "ComputerName", "machine.account_name", data["ComputerName"])
            path = current + r"\Control\TimeZoneInformation"
            data = values(hive, path)
            field = "TimeZoneKeyName" if data.get("TimeZoneKeyName") else "StandardName"
            if isinstance(data.get(field), str) and data[field]:
                emit(hive, path, field, "os.time_zone_setting", data[field],
                     bias=data.get("Bias"), daylight_bias=data.get("DaylightBias"))
            try:
                display, provenance = effective_time_zone(data)
                locators = {name: {'artifact': system._art(hive, path, name),
                                   'source_hive': str(hive.path), 'registry_key': path,
                                   'registry_value': name}
                            for name in provenance['time_zone_registry_inputs']}
                emit(hive, path, 'ActiveTimeBias', 'os.effective_time_zone', display,
                     registry_input_locators=locators, current_control_set=current,
                     control_set_selection_artifact=system._art(hive, 'Select', 'Current'),
                     **provenance)
            except ValueError as error:
                ev.problem(system._art(hive, path) + ' effective recorded time zone', error)
            path = current + r"\Control\Windows"
            data = values(hive, path)
            raw = data.get("ShutdownTime")
            if isinstance(raw, bytes) and len(raw) == 8:
                stamp = system.filetime_us(struct.unpack("<Q", raw)[0])
                if stamp is not None:
                    emit(hive, path, "ShutdownTime", "machine.last_shutdown", system.iso(stamp),
                         value_time_meaning="recorded shutdown FILETIME in UTC")
        elif hive.name == "SECURITY":
            # LSA primary domain name is a counted Unicode string. A DNS suffix or
            # default-logon domain is not silently relabeled as this field.
            path = r"Policy\PolPrDmN"
            data = values(hive, path)
            raw = data.get("") or data.get("(Default)")
            if isinstance(raw, bytes):
                try:
                    name = policy_unicode(raw)
                    if name:
                        emit(hive, path, "(Default)", "machine.primary_domain", name)
                except ValueError as error:
                    ev.problem(system._art(hive, path), error)
        elif hive.name == "SAM":
            path = r"SAM\Domains\Account\Users"
            key = system._open(ev, hive, path)
            if key is None:
                continue
            before = len(ev.problems)
            entries = [entry for entry in system._subkeys(ev, hive, key)
                       if re.fullmatch(r"[0-9A-Fa-f]{8}", entry.name)]
            if len(ev.problems) == before:
                emit(hive, path, "subkeys", "account.count", len(entries),
                     scope="all RID-named user records in the current SAM, including built-in accounts",
                     member_keys=[entry.name for entry in entries])
            for entry in entries:
                try:
                    data = system._vals(ev, hive, entry)
                    fixed = system.parse_sam_f(data["F"])
                    names = system.parse_sam_v(data["V"])
                    owner = subject + ":sam-rid:" + entry.name.upper()
                    emit(hive, entry.path, "V", "account.name", names["name"], owner=owner)
                    emit(hive, entry.path, "F", "account.logon_count", fixed["logon_count"], owner=owner,
                         limitation="retained SAM counter; not a complete login history or habitual-use proof")
                    emit(hive, entry.path, "F", "account.enabled", not bool(fixed["flags"] & 1), owner=owner)
                    if fixed["last_logon"] is not None:
                        emit(hive, entry.path, "F", "account.last_logon", system.iso(fixed["last_logon"]), owner=owner)
                except Exception as error:
                    ev.problem(system._art(hive, entry.path), error)


def policy_unicode(raw):
    """Decode the relative Unicode string layout of LSA PolPrDmN/PolAcDmN."""
    if len(raw) < 12:
        raise ValueError("truncated LSA domain-name record")
    length, maximum, offset = struct.unpack_from("<HHI", raw)
    if length % 2 or maximum < length or offset < 8 or offset + length > len(raw):
        raise ValueError("invalid LSA domain-name string bounds")
    try:
        return raw[offset:offset + length].decode("utf-16-le").rstrip("\x00")
    except UnicodeDecodeError as error:
        raise ValueError("invalid LSA domain-name Unicode") from error
