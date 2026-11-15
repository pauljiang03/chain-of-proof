"""Facts and where they come from.

A fact is one row of the evidence DB. Only the extractor writes facts; the agent
refers to them by id. The row layout mirrors `lean/ChainOfProof/Facts.lean` and
`extractor/schema.sql`: change all three together.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

from .catalog import ATTRIBUTE_KINDS


_ENTRY_KINDS = {name: index for index, name in enumerate((
    'ntfs_mft', 'fat_directory_entry', 'exfat_directory_entry',
    'udf_file_entry', 'iso9660_directory_record'), start=1)}
_OCCURRENCE_FIELDS = {'schema_version', 'disk_index', 'partition_offset_bytes',
                      'partition_size_bytes', 'entry_kind', 'entry_id'}


def file_occurrence(prov):
    """Return ten explicit identity dimensions, or None when evidence is absent.

    This is a strict source-to-formal-data adapter, not an identity equality
    checker. Lean compares every dimension. Text is encoded injectively as UTF-8
    bytes with a leading byte; no hash, path, volume serial, or unknown default
    supplies an occurrence. Native values are offset by one to reserve zero for
    absent identity. The full provenance remains covered by the source-row hash.
    """
    if type(prov) is not dict or type(prov.get('file_occurrence')) is not dict:
        return None
    raw = prov['file_occurrence']
    kind = raw.get('entry_kind')
    if type(kind) is not str or kind not in _ENTRY_KINDS:
        return None
    expected = _OCCURRENCE_FIELDS | ({'entry_sequence'} if kind == 'ntfs_mft' else set())
    if set(raw) != expected or type(raw.get('schema_version')) is not int or raw['schema_version'] != 1:
        return None
    scope = [prov.get(name) for name in ('image', 'exhibit', 'source_snapshot', 'source_variant')]
    if any(type(value) is not str or not value.strip() or value != value.strip()
           or value.lower() in {'unknown', 'none', '(none)'} or any(ord(char) < 32 for char in value)
           for value in scope):
        return None
    try:
        text_bytes = [value.encode('utf-8') for value in scope]
    except UnicodeError:
        return None
    if any(len(value) > 512 for value in text_bytes):
        return None
    values = [raw.get(name) for name in ('disk_index', 'partition_offset_bytes',
                                        'partition_size_bytes', 'entry_id')]
    if any(type(value) is not int or not 0 <= value < 2**64 for value in values):
        return None
    if raw['partition_size_bytes'] == 0 or (kind != 'ntfs_mft' and raw['entry_id'] >= raw['partition_size_bytes']):
        return None
    sequence = raw.get('entry_sequence', 0)
    if type(sequence) is not int or (kind == 'ntfs_mft' and not 1 <= sequence <= 65535):
        return None
    encoded = tuple(int.from_bytes(b'\x01' + value, 'big') for value in text_bytes)
    return encoded + (raw['disk_index'] + 1, raw['partition_offset_bytes'] + 1,
                      raw['partition_size_bytes'] + 1, _ENTRY_KINDS[kind],
                      raw['entry_id'] + 1, sequence + 1)

FILESYSTEM_SET_KINDS = ("filesystemSet", "filesystemMemberDeleted",
                        "filesystemMemberAllocated", "filesystemMemberUnknown")
# Preserve these new non-attribute ordinals when future attribute roles are appended.
_SET_KIND_BOUNDARY = ATTRIBUTE_KINDS.index("roleRecycleIndexDeletedAt") + 1

KINDS = (
    "usbInsert", "volumeMount", "lnkTarget",
    "fileCreated", "fileModified", "fileDeleted",
    "webSearch", "emailSent", "cdBurn",
    "tag",
    "volumeSeen", "volumeOnDevice",
    "unallocatedOnDevice",
    # the machine, its accounts and what ran on it
    "systemSetting", "accountSeen", "sessionEvent", "programInstalled", "programRun",
    # browsers, downloads, cloud clients, notes
    "webVisit", "fileDownloaded", "localSearch", "cloudFile", "noteText",
    # what the system remembers about folders and files
    "folderOpened", "fileRenamed", "fileSeen", "shadowCopy",
    # file contents
    "fileContent",
    # Recorded removal and optical volume timestamps; preserve the preceding kind order.
    "fileRemoved", "volumeRecorded",
    "fileCreationRecorded",
    "journalName", "journalParent", "journalRemoval",
    "journalPath",
) + ATTRIBUTE_KINDS[:_SET_KIND_BOUNDARY] + FILESYSTEM_SET_KINDS + ATTRIBUTE_KINDS[_SET_KIND_BOUNDARY:]


@dataclass(frozen=True)
class Fact:
    id: int
    kind: str
    t: int      # UTC microseconds since the Unix epoch
    res: int    # timestamp uncertainty in microseconds
    obj: int    # interned entity id
    aux: int    # interned entity id
    prov: dict = field(default_factory=dict, compare=False)

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"fact {self.id}: unknown kind {self.kind!r}")
        for name in ("id", "t", "res", "obj", "aux"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise ValueError(f"fact {self.id}: {name} must be a non-negative integer")

    def to_lean(self) -> str:
        occurrence = file_occurrence(self.prov) or (0,) * 10
        identity = '⟨' + ', '.join(str(value) for value in occurrence) + '⟩'
        return f"⟨{self.id}, .{self.kind}, {self.t}, {self.res}, {self.obj}, {self.aux}, {identity}⟩"

    def row_sha256(self) -> str:
        """Hash of everything a certificate relies on: the checked fields and provenance."""
        prov = json.dumps(self.prov, sort_keys=True, separators=(",", ":"))
        row = f"{self.id}|{self.kind}|{self.t}|{self.res}|{self.obj}|{self.aux}|{prov}"
        return hashlib.sha256(row.encode()).hexdigest()


class FactSource:
    """Read-only access to facts and interned strings."""

    metadata = None

    def get(self, ids: Iterable[int]) -> Dict[int, Fact]:
        raise NotImplementedError

    def string(self, sid: int) -> str:
        raise NotImplementedError

    def all(self) -> List[Fact]:
        """Every fact, ordered by id. For the miner and the scorer."""
        raise NotImplementedError


class JsonFacts(FactSource):
    """A JSON file: {"strings": {"<id>": "<text>"}, "facts": [{...}]}. For fixtures and tests."""

    def __init__(self, path):
        data = json.loads(Path(path).read_text())
        self._strings = {int(k): v for k, v in data.get("strings", {}).items()}
        self._facts = {}
        for row in data["facts"]:
            f = Fact(row["id"], row["kind"], row["t"], row["res"], row["obj"], row["aux"],
                     row.get("prov", {}))
            if f.id in self._facts:
                raise ValueError(f"duplicate fact id {f.id}")
            self._facts[f.id] = f
        meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
        self.metadata = {"facts": len(self._facts),
                         "by_kind": dict(Counter(f.kind for f in self._facts.values())),
                         "unparsed": meta.get("unparsed"),
                         "scope": "Counts describe this supplied fact store; parser omissions can remain unknown."}

    def get(self, ids):
        return {i: self._facts[i] for i in ids if i in self._facts}

    def string(self, sid):
        return self._strings.get(sid, f"#{sid}")

    def all(self):
        return [self._facts[i] for i in sorted(self._facts)]


class DuckFacts(FactSource):
    """The evidence DB, opened read-only. Schema: extractor/schema.sql."""

    def __init__(self, path):
        import duckdb  # imported here so fixtures and tests run without it
        self._db = duckdb.connect(str(path), read_only=True)

    def get(self, ids):
        ids = list(ids)
        if not ids:
            return {}
        marks = ",".join("?" * len(ids))
        rows = self._db.execute(
            f"SELECT id, kind, t, res, obj, aux, prov FROM facts WHERE id IN ({marks})", ids
        ).fetchall()
        return {r[0]: Fact(r[0], r[1], r[2], r[3], r[4], r[5], json.loads(r[6] or "{}"))
                for r in rows}

    def string(self, sid):
        row = self._db.execute("SELECT s FROM strings WHERE id = ?", [sid]).fetchone()
        return row[0] if row else f"#{sid}"

    def all(self):
        rows = self._db.execute(
            "SELECT id, kind, t, res, obj, aux, prov FROM facts ORDER BY id").fetchall()
        return [Fact(r[0], r[1], r[2], r[3], r[4], r[5], json.loads(r[6] or "{}")) for r in rows]


def open_source(path) -> FactSource:
    return JsonFacts(path) if str(path).endswith(".json") else DuckFacts(path)
