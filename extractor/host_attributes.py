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
            for field, role in (("ProductName", "os.product_name"), ("RegisteredOwner", "os.registered_owner")):
                if isinstance(data.get(field), str) and data[field]:
                    emit(hive, path, field, role, data[field])
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
