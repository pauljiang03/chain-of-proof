"""Collect rows and assign ids in sorted order, so the same images always give the same ids."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from checker.facts import KINDS

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
FILETIME_EPOCH_100NS = 116444736000000000


def us(dt: datetime) -> int:
    """Aware datetime -> UTC microseconds, exactly."""
    return (dt - EPOCH) // timedelta(microseconds=1)


def us_from_unix(seconds: float) -> int:
    return round(seconds * 1_000_000)


def us_from_filetime(ft: int) -> int:
    return (ft - FILETIME_EPOCH_100NS) // 10


class Evidence:
    def __init__(self):
        self._rows: List[Tuple] = []
        self.problems: List[str] = []

    def problem(self, where: str, error: Exception) -> None:
        """An artifact that could not be parsed. Reported, never silently dropped."""
        self.problems.append(f"{where}: {type(error).__name__}: {error}")

    def add(self, kind: str, t: int, res: int, obj: str, aux: str = "", **prov) -> None:
        assert kind in KINDS, kind
        assert isinstance(t, int) and t >= 0 and isinstance(res, int) and res >= 1, (kind, t, res)
        self._rows.append((kind, t, res, obj, aux, json.dumps(prov, sort_keys=True)))

    def rows(self) -> List[Tuple]:
        return sorted(set(self._rows), key=lambda r: (KINDS.index(r[0]),) + r[1:])

    def finalize(self) -> Tuple[Dict[int, str], List[dict]]:
        strings: Dict[str, int] = {"": 0}
        facts = []
        for i, (kind, t, res, obj, aux, prov) in enumerate(self.rows(), start=1):
            for s in (obj, aux):
                strings.setdefault(s, len(strings))
            facts.append({"id": i, "kind": kind, "t": t, "res": res,
                          "obj": strings[obj], "aux": strings[aux], "prov": json.loads(prov)})
        table = {i: (s or "(none)") for s, i in strings.items()}
        return table, facts

    def write_json(self, path, meta: dict) -> dict:
        strings, facts = self.finalize()
        counts: Dict[str, int] = {}
        for f in facts:
            counts[f["kind"]] = counts.get(f["kind"], 0) + 1
        meta = dict(meta, facts=len(facts), by_kind=counts, unparsed=sorted(self.problems))
        data = {"_meta": meta, "strings": {str(i): s for i, s in strings.items()}, "facts": facts}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        return meta

    def write_duckdb(self, path, schema_sql: str) -> None:
        import duckdb
        strings, facts = self.finalize()
        Path(path).unlink(missing_ok=True)
        db = duckdb.connect(str(path))
        db.execute(schema_sql)
        db.executemany("INSERT INTO strings VALUES (?, ?)", sorted(strings.items()))
        db.executemany("INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?)",
                       [(f["id"], f["kind"], f["t"], f["res"], f["obj"], f["aux"],
                         json.dumps(f["prov"], sort_keys=True)) for f in facts])
        db.close()
