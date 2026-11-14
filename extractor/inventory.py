"""Inventory concrete Windows artifact containers without interpreting their contents.

Standard per-profile layouts and registered home directories are searched on every
mounted drive. Only existing regular files are emitted; patterns select directory
entries and are never emitted as observed paths. This is a bounded inventory, not
an absence claim or an assertion that an application executed. Files outside the
listed layouts, redirected application data, and alternate streams are not covered.

A complete readable file yields fileContent; skipped/failed hashes yield fileSeen.
Both are examination observations. Filesystem birth/modified times remain distinct
provenance fields and are never substituted for examination time or application use.
"""
from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timedelta, timezone

from .content import HEAD, _row
from .acquisition import provenance

MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_FILES = 4096
MAX_DIRECTORY_ENTRIES = 20000
CHUNK_BYTES = 1024 * 1024

# Folder layouts, not case-specific users, names, or expected benchmark answers.
USER_LAYOUTS = (
    ("AppData/Local/Microsoft/Outlook", "outlook_mailbox", (".pst", ".ost")),
    ("Local Settings/Application Data/Microsoft/Outlook", "outlook_mailbox", (".pst", ".ost")),
    ("Documents/Outlook Files", "outlook_mailbox", (".pst", ".ost")),
    ("My Documents/Outlook Files", "outlook_mailbox", (".pst", ".ost")),
    ("AppData/Local/Microsoft/Windows/Explorer", "thumbnail_cache", ("thumbcache_",)),
    ("Local Settings/Application Data/Microsoft/Windows/Explorer", "thumbnail_cache", ("thumbcache_",)),
    ("AppData/Roaming/Microsoft/Sticky Notes", "sticky_notes", ("stickynotes.snt",)),
    ("Application Data/Microsoft/Sticky Notes", "sticky_notes", ("stickynotes.snt",)),
)
SEARCH_LAYOUTS = (
    "ProgramData/Microsoft/Search/Data/Applications/Windows",
    "Documents and Settings/All Users/Application Data/Microsoft/Search/Data/Applications/Windows",
)


def _win(path):
    name = str(path).replace("/", "\\")
    # Dissect's resolved absolute drive paths carry a virtual leading slash.
    return name[1:] if re.match(r"^\\[A-Za-z]:\\", name) else name


def _children(ev, directory):
    """Bound directory listing and log read failures without stopping other paths."""
    try:
        if not directory.exists() or directory.is_symlink() or not directory.is_dir():
            return []
        rows = []
        for entry in directory.iterdir():
            if len(rows) >= MAX_DIRECTORY_ENTRIES:
                raise ValueError(f"directory exceeds {MAX_DIRECTORY_ENTRIES} entries; inventory omitted")
            rows.append(entry)
        return sorted(rows, key=lambda p: (_win(p).casefold(), _win(p)))
    except Exception as error:
        ev.problem(f"artifact inventory directory {_win(directory)}", error)
        return []


def _matches(name, category, names):
    name = name.casefold()
    if category == "outlook_mailbox":
        return name.endswith(names)
    if category == "thumbnail_cache":
        return name.startswith("thumbcache_") and name.endswith(".db")
    return name in names


def _homes(ev, target, drives):
    homes = {}
    for drive in drives:
        for root in ("Users", "Documents and Settings"):
            for path in _children(ev, target.fs.path(drive + "/" + root)):
                try:
                    if path.is_dir() and not path.is_symlink():
                        homes[_win(path).casefold()] = path
                except Exception as error:
                    ev.problem(f"artifact inventory profile {_win(path)}", error)
    # Registered user homes can be on nonstandard paths or another mounted volume.
    try:
        for details in target.user_details.all_with_home():
            path = details.home_path
            if path.is_dir() and not path.is_symlink():
                homes.setdefault(_win(path).casefold(), path)
    except Exception as error:
        ev.problem("artifact inventory registered user homes", error)
    return sorted(homes.values(), key=lambda path: (_win(path).casefold(), _win(path)))


def candidates(ev, target):
    """Yield concrete (path, category, profile) from standard artifact containers."""
    drives = sorted({str(m).upper() for m in target.fs.mounts
                     if re.fullmatch(r"[A-Za-z]:", str(m))})
    if not drives:
        ev.problem("artifact inventory", ValueError("no mounted drive-letter roots; inventory not attempted"))
        return
    for home in _homes(ev, target, drives):
        for relative, category, names in USER_LAYOUTS:
            for path in _children(ev, home.joinpath(relative)):
                if _matches(path.name, category, names):
                    yield path, category, home
        packages = home.joinpath("AppData/Local/Packages")
        for package in _children(ev, packages):
            if package.name.casefold().startswith("microsoft.microsoftstickynotes_"):
                for path in _children(ev, package.joinpath("LocalState")):
                    if path.name.casefold() == "plum.sqlite":
                        yield path, "sticky_notes", home
    for drive in drives:
        for relative in SEARCH_LAYOUTS:
            for path in _children(ev, target.fs.path(drive + "/" + relative)):
                if path.name.casefold().endswith((".edb", ".db")):
                    yield path, "windows_search", None


def _timestamp(stat, field):
    nanoseconds = getattr(stat, field + "_ns", None)
    if nanoseconds is not None:
        if isinstance(nanoseconds, bool) or not isinstance(nanoseconds, int):
            raise ValueError(f"{field}_ns is not an integer timestamp")
        micros = nanoseconds // 1000
        if micros < 0:
            raise ValueError(f"{field}_ns precedes 1970; not emitted")
        return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=micros)).isoformat().replace("+00:00", "Z")
    value = getattr(stat, field, None)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field} is not a finite timestamp")
    micros = round(value * 1_000_000)
    if micros < 0:
        raise ValueError(f"{field} precedes 1970; not emitted")
    return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=micros)).isoformat().replace("+00:00", "Z")


def _metadata(ev, target, path, profile, stat, category):
    source = _win(path)
    extra = {"inventory_category": category, "source_path": source,
             "timestamp_semantics": "examination_observation",
             "classification_basis": "filename and artifact-directory layout; container contents not interpreted",
             "stat_source": "filesystem lstat; birth time and modification time are distinct from examination time"}
    if profile is not None:
        extra.update(profile_name=profile.name, profile_path=_win(profile))
    for field, key in (("st_birthtime", "file_created_utc"), ("st_mtime", "file_modified_utc")):
        try:
            value = _timestamp(stat, field)
            if value is not None:
                extra[key] = value
        except Exception as error:
            ev.problem(f"artifact inventory timestamp {source}", error)
    drive = source[:2].lower()
    if re.match(r"^[A-Za-z]:\\", source):
        extra["filesystem_root"] = source[:2] + "\\"
    location = ""
    try:
        mounts = {str(k).lower(): v for k, v in target.fs.mounts.items()}
        serial = int(mounts[drive].ntfs.serial)
        extra["volume_serial_full"] = f"{serial:016X}"
        location = f"{serial & 0xFFFFFFFF:08X}"
    except (AttributeError, KeyError, TypeError, ValueError):
        pass  # Never invent a serial for another filesystem or an unresolved mount.
    return location, extra


def _digest(fh, recorded_size, budget):
    digest, size, head = hashlib.sha256(), 0, b""
    while True:
        # One extra byte detects a length mismatch without an unbounded stream read.
        chunk = fh.read(min(CHUNK_BYTES, recorded_size - size + 1))
        if not chunk:
            break
        budget[0] += len(chunk)
        if budget[0] > MAX_TOTAL_BYTES:
            raise ValueError("total inventory hashing budget exceeded")
        size += len(chunk)
        if size > recorded_size:
            raise ValueError("content is longer than the recorded file size")
        digest.update(chunk)
        if len(head) < HEAD:
            head += chunk[:HEAD - len(head)]
    if size != recorded_size:
        raise ValueError(f"read {size} bytes; file record says {recorded_size}")
    return digest.hexdigest(), size, head


def extract(ev, target, ctx):
    seen, budget = set(), [0]
    for path, category, profile in candidates(ev, target):
        discovered = _win(path)
        if any(c in discovered for c in "*?\x00"):
            ev.problem(f"artifact inventory {discovered}", ValueError("non-concrete path was not emitted"))
            continue
        try:
            if path.is_symlink() or not path.is_file():
                continue
            # Resolve ancestor junctions such as Local Settings -> AppData/Local,
            # so one physical file is not reported again under a compatibility alias.
            path = path.resolve(strict=True)
            source = _win(path)
            key = source.casefold()
            if key in seen:
                continue
            stat = path.lstat()
            size = stat.st_size
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise ValueError("invalid recorded file size")
        except Exception as error:
            ev.problem(f"artifact inventory {discovered}", error)
            continue
        if len(seen) >= MAX_FILES:
            ev.problem("artifact inventory", ValueError(f"file limit {MAX_FILES} reached; remaining files omitted"))
            break
        seen.add(key)
        location, extra = _metadata(ev, target, path, profile, stat, category)
        if source != discovered:
            extra["discovered_path"] = discovered
            extra["path_resolution"] = "resolved filesystem ancestor links/junctions"
        artifact = f"filesystem artifact container {source}"
        try:
            if size > MAX_FILE_BYTES:
                raise ValueError(f"size {size} exceeds per-file hashing limit {MAX_FILE_BYTES}")
            if size > MAX_TOTAL_BYTES - budget[0]:
                raise ValueError("file exceeds remaining total inventory hashing budget")
            with path.open("rb") as stream:
                digest, read_size, head = _digest(stream, size, budget)
            _row(ev, ctx, source, digest, read_size, head, location, artifact,
                 hash_complete=True, hash_algorithm="sha256", **extra)
        except Exception as error:
            ev.problem(f"artifact inventory content {source}", error)
            details = dict(extra, artifact=artifact, size=size, location=location,
                           hash_complete=False, hash_status=str(error),
                           time_meaning="file observed when the image was examined; not application execution",
                           **ctx["common"])
            if ctx.get("acquisition"):
                details.update(provenance(ctx["acquisition"]))
            ev.add("fileSeen", ctx["examined_at"], 1, source, "artifact inventory: " + category,
                   **details)
