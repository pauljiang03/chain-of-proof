"""Deterministic tags with explicit, shared public policy for case-specific labels.

No case-specific serial, path marker, or authorization policy is built in. Generic
artifact comparisons and the stated search watch list do not depend on case policy.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .store import Evidence

SAME_FILE_SLACK_US = 2_000_000      # FAT keeps modified times to 2 seconds

# A generic watch list for search terms: moving data out, or covering tracks. It was
# written before looking at this case's searches and is not tuned to them.
WATCH_WORDS = ("leak", "exfiltrat", "theft", "steal", "secret", "forensic", "delet", "eras",
               "wipe", "shred", "clean", "recover", "cover tracks", "dlp", "drm",
               "cloud storage", "cd burn", "external device", "investigat", "event log")


def public_policy(value=None) -> dict:
    """Validate the optional ``_policy`` in a public acquisition manifest.

    A nonmember is unauthorized only when the supplied allowlist is explicitly
    complete; an incomplete or absent list leaves nonmembers unclassified.
    """
    if value is None:
        return {}
    allowed = {"source", "authorized_device_serials", "authorized_device_serials_complete",
               "confidential_path_markers"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("public _policy must contain only source, authorized_device_serials, "
                         "authorized_device_serials_complete, and confidential_path_markers")
    out = dict(value)
    if "source" in out and not isinstance(out["source"], str):
        raise ValueError("public policy source must be text")
    for key in ("authorized_device_serials", "confidential_path_markers"):
        if key in out:
            entries = out[key]
            if not isinstance(entries, list) or any(not isinstance(v, str) or not v.strip() for v in entries):
                raise ValueError(f"public policy {key} must be a list of nonempty strings")
            out[key] = sorted({v.strip() for v in entries})
    if "authorized_device_serials_complete" in out:
        if type(out["authorized_device_serials_complete"]) is not bool:
            raise ValueError("authorized_device_serials_complete must be a boolean")
        if "authorized_device_serials" not in out:
            raise ValueError("a complete public allowlist requires authorized_device_serials")
    return out


def add_tags(ev: Evidence, examined_at: int, *, policy=None) -> int:
    policy = public_policy(policy)
    authorized = set(policy.get("authorized_device_serials", ()))
    complete = policy.get("authorized_device_serials_complete", False)
    confidential = tuple(m.lower() for m in policy.get("confidential_path_markers", ()))
    devices, paths, terms = set(), set(), set()
    for kind, _t, _res, obj, _aux, prov in ev.rows():
        if kind in ("usbInsert", "volumeOnDevice", "unallocatedOnDevice"):
            info = json.loads(prov)
            if not obj.startswith("image-scoped device ") and (
                    kind == "usbInsert" or info.get("device_identity_kind") == "hardware_serial"):
                devices.add(obj)
        elif kind in ("lnkTarget", "fileCreated", "fileModified", "fileDeleted"):
            paths.add(obj)
        elif kind == "webSearch":
            terms.add(obj)
    n = 0
    for serial in sorted(devices):
        ok = serial in authorized
        if not ok and not complete:
            continue
        ev.add("tag", examined_at, 1, serial, "authorized-device" if ok else "unauthorized-device",
               source="deterministic", policy_source=policy.get("source", "explicit public manifest policy"),
               rule=("device serial is on the explicitly supplied public authorized list" if ok else
                     "device serial is not on the explicitly supplied complete public authorized list"))
        n += 1
    for path in sorted(paths):
        if any(m in path.lower() for m in confidential):
            ev.add("tag", examined_at, 1, path, "confidential", source="deterministic",
                   policy_source=policy.get("source", "explicit public manifest policy"),
                   rule="path carries a confidential-path marker in the explicitly supplied public policy")
            n += 1
    n += _same_size_and_time(ev, examined_at)
    n += _deleted_mail(ev, examined_at)
    for term in sorted(terms):
        hit = next((w for w in WATCH_WORDS if w in term.lower()), None)
        if hit:
            ev.add("tag", examined_at, 1, term, "watch-list-search", source="deterministic",
                   rule=f'search term contains the watch-list word "{hit}"')
            n += 1
    return n


def _same_size_and_time(ev: Evidence, examined_at: int) -> int:
    """Tag file records that sit in different places (volumes, or a device's unallocated
    space) with the same size and the same last-modified time. A copy keeps both, so
    this is how a renamed copy shows up. Contents are not compared, and the tag says so."""
    by_size = defaultdict(list)
    for kind, t, _res, obj, aux, prov in ev.rows():
        if kind == "fileModified":
            size = json.loads(prov).get("size")
            if isinstance(size, int) and size > 0:
                by_size[size].append((t, obj, aux))
    n = 0
    for size in sorted(by_size):
        rows = sorted(by_size[size])
        group = [rows[0]]
        for row in rows[1:] + [None]:
            if row is not None and row[0] - group[0][0] <= SAME_FILE_SLACK_US:
                group.append(row)
                continue
            if len({aux for _t, _obj, aux in group}) > 1:      # in more than one place
                when = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=group[0][0])
                name = (f"same size and last-modified time as a file elsewhere: {size} bytes, "
                        f"{when.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                for path in sorted({obj for _t, obj, _aux in group}):
                    ev.add("tag", examined_at, 1, path, name, source="deterministic",
                           rule=("another file record, in a different volume or in a device's "
                                 "unallocated space, has this size and this last-modified "
                                 "time (within 2 s); contents were not compared"))
                    n += 1
            group = [row] if row is not None else []
    return n


def _deleted_mail(ev: Evidence, examined_at: int) -> int:
    """Tag an e-mail subject when every message with that subject is in Deleted Items."""
    folders = defaultdict(set)
    for kind, _t, _res, obj, _aux, prov in ev.rows():
        if kind == "emailSent":
            folders[obj].add(json.loads(prov).get("folder"))
    n = 0
    for subject in sorted(folders):
        if folders[subject] == {"Deleted Items"}:
            ev.add("tag", examined_at, 1, subject, "e-mail in the Deleted Items folder",
                   source="deterministic",
                   rule="the mailbox file lists this message in its Deleted Items folder")
            n += 1
    return n
