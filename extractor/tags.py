"""Deterministic tags. Each one is plain code over extracted rows, with its rule stated.

The authorized list and the confidential-path marker come from the case brief
(NIST scenario overview): RM#1 is the company's authorized USB, and confidential
files live under 'Secret Project Data' with 'secret_project' in their names.
"""
from __future__ import annotations

from .store import Evidence

AUTHORIZED_SERIALS = {"4C530012450531101593"}
CONFIDENTIAL_MARKERS = ("secret_project", "\\secret project data\\")
# A generic watch list for search terms: moving data out, or covering tracks. It was
# written before looking at this case's searches and is not tuned to them.
WATCH_WORDS = ("leak", "exfiltrat", "theft", "steal", "secret", "forensic", "delet", "eras",
               "wipe", "shred", "clean", "recover", "cover tracks", "dlp", "drm",
               "cloud storage", "cd burn", "external device", "investigat", "event log")


def add_tags(ev: Evidence, examined_at: int) -> int:
    devices, paths, terms = set(), set(), set()
    for kind, _t, _res, obj, _aux, _prov in ev.rows():
        if kind in ("usbInsert", "volumeOnDevice"):
            devices.add(obj)
        elif kind in ("lnkTarget", "fileCreated", "fileModified", "fileDeleted"):
            paths.add(obj)
        elif kind == "webSearch":
            terms.add(obj)
    n = 0
    for serial in sorted(devices):
        ok = serial in AUTHORIZED_SERIALS
        ev.add("tag", examined_at, 1, serial, "authorized-device" if ok else "unauthorized-device",
               source="deterministic",
               rule=("device serial is on the authorized list in the case brief" if ok else
                     "device serial is not on the authorized list in the case brief"))
        n += 1
    for path in sorted(paths):
        if any(m in path.lower() for m in CONFIDENTIAL_MARKERS):
            ev.add("tag", examined_at, 1, path, "confidential", source="deterministic",
                   rule="path carries the confidential-project marker named in the case brief")
            n += 1
    for term in sorted(terms):
        hit = next((w for w in WATCH_WORDS if w in term.lower()), None)
        if hit:
            ev.add("tag", examined_at, 1, term, "watch-list-search", source="deterministic",
                   rule=f'search term contains the watch-list word "{hit}"')
            n += 1
    return n
