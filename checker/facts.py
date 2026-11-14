"""Facts and where they come from.

A fact is one row of the evidence DB. Only the extractor writes facts; the agent
refers to them by id. The row layout mirrors `lean/ChainOfProof/Facts.lean` and
`extractor/schema.sql`: change all three together.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

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
)


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
        return f"⟨{self.id}, .{self.kind}, {self.t}, {self.res}, {self.obj}, {self.aux}⟩"

    def row_sha256(self) -> str:
        """Hash of everything a certificate relies on: the checked fields and provenance."""
        prov = json.dumps(self.prov, sort_keys=True, separators=(",", ":"))
        row = f"{self.id}|{self.kind}|{self.t}|{self.res}|{self.obj}|{self.aux}|{prov}"
        return hashlib.sha256(row.encode()).hexdigest()


class FactSource:
    """Read-only access to facts and interned strings."""

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
