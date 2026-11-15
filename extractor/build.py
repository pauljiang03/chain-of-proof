"""Reusable extraction dispatch over an explicitly supplied exhibit manifest.

The legacy --out command and versioned intake share ``extract``. No case-specific
image names, identities, policies, timezone or observation date are selected here.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from extractor.acquisition import resolve
from extractor.store import Evidence, us
from extractor.tags import add_tags, public_policy


def extract_media(*args, **kwargs):
    from extractor.media import extract_media as reader
    return reader(*args, **kwargs)


def extract_pc(*args, **kwargs):
    from extractor.windows import extract_pc as reader
    return reader(*args, **kwargs)

READERS = {"pc": ("system", "webcloud", "filetraces", "inventory", "content"),
           "removable": ("content",), "optical": ("optical", "content")}
OPEN_TARGET = ("system", "webcloud", "filetraces", "inventory")
READER_ROLES = {"windows": ("pc",), "media": ("removable",),
                **{reader: tuple(role for role, readers in READERS.items() if reader in readers)
                   for reader in sorted({r for readers in READERS.values() for r in readers})}}
READER_ORDER = ("windows", "media", "system", "webcloud", "filetraces", "inventory", "optical", "content")


def selection(exhibits, readers=None):
    """Expand a caller-approved reader allowlist into explicit exhibit pairs."""
    chosen = list(READER_ORDER) if readers is None else list(readers)
    if not chosen or any(not isinstance(r, str) or r not in READER_ROLES for r in chosen):
        raise ValueError("readers must be a nonempty list of supported reader IDs")
    if len(chosen) != len(set(chosen)):
        raise ValueError("reader IDs must be unique")
    return [{"reader": r, "exhibit": e["exhibit"]} for r in READER_ORDER if r in chosen
            for name, e in sorted(exhibits.items()) if not name.startswith("_")
            and e["role"] in READER_ROLES[r]]


def extract(images, exhibits, *, case, examined_at, selected=None, evidence=None,
            previous_meta=None, manifest_source="explicit acquisition manifest"):
    """Run approved reader/exhibit pairs into a new or caller-owned Evidence object.

    Individual reader failures remain visible in health and do not erase partial
    records. A missing FAT timezone is a failure, never an invented UTC setting.
    This function does not write files or modify a previous snapshot.
    """
    images = Path(images)
    ev = evidence if evidence is not None else Evidence()
    previous_meta = previous_meta or {}
    stamp = datetime.fromisoformat(examined_at)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("examined_at must include a timezone")
    observation = us(stamp.astimezone(timezone.utc))
    if observation < 0:
        raise ValueError("examined_at must not precede the Unix epoch")
    tool = f"dissect.target {version('dissect.target')}"
    policy = public_policy(exhibits.get("_policy"))
    by_id = {e["exhibit"]: (name, e) for name, e in exhibits.items() if not name.startswith("_")}
    selected = selection(exhibits) if selected is None else selected
    for item in selected:
        reader, exhibit = item.get("reader"), item.get("exhibit")
        if reader not in READER_ROLES or exhibit not in by_id:
            raise ValueError("unknown selected reader or exhibit")
        if by_id[exhibit][1]["role"] not in READER_ROLES[reader]:
            raise ValueError("selected reader does not support this exhibit role")
    selected = sorted(selected, key=lambda p: (READER_ORDER.index(p["reader"]), p["exhibit"]))
    acquisition = dict(previous_meta.get("acquisition", {}))
    for exhibit in sorted({item["exhibit"] for item in selected}):
        name, entry = by_id[exhibit]
        acquisition[name] = resolve(images / name, entry, manifest_source)
    pcs = dict(previous_meta.get("pc_by_exhibit", {}))
    fat_tz = exhibits.get("_time_zone") or previous_meta.get("fat_time_zone")
    log, attempts = [], []
    for item in selected:
        reader, exhibit_id = item["reader"], item["exhibit"]
        name, exhibit = by_id[exhibit_id]
        before, problems_before = len(ev.rows()), len(ev.problems)
        failure = None
        try:
            if reader == "windows":
                info, lines = extract_pc(ev, images / name, tool, exhibit_id)
                pcs[exhibit_id] = info
                log.extend(lines)
                zones = {p.get("time_zone") for p in pcs.values() if p.get("time_zone")}
                if "_time_zone" not in exhibits:
                    fat_tz = next(iter(zones)) if len(zones) == 1 else None
            else:
                if reader == "media" and not fat_tz:
                    ev.problem(f"{name}: reader media", ValueError(
                        "FAT timezone unavailable; supply manifest _time_zone or collect Windows timezone evidence. "
                        "FAT wall-clock conversions are unavailable; offset-bearing exFAT times may still be read."))
                if fat_tz:
                    ZoneInfo(fat_tz)
                if reader == "media":
                    log.extend(extract_media(ev, images / name, exhibit, fat_tz, observation, tool,
                                             acquisition=acquisition[name]))
                else:
                    ctx = {"common": {"image": name, "exhibit": exhibit_id, "tool": tool},
                           "examined_at": observation, "pc_time_zone": fat_tz,
                           "acquisition": acquisition[name]}
                    module = import_module(f"extractor.{reader}")
                    if reader in OPEN_TARGET:
                        from dissect.target import Target
                        module.extract(ev, Target.open(images / name), ctx)
                    else:
                        module.extract(ev, images / name, ctx)
        except Exception as error:
            failure = type(error).__name__
            ev.problem(f"{name}: reader {reader}", error)
        delta = len(ev.rows()) - before
        issues = ev.problems[problems_before:]
        attempts.append({"reader": reader, "exhibit": exhibit_id, "new_records": delta,
                         "status": "failed" if failure else "partial" if issues else "completed",
                         "error_type": failure, "issues": list(issues)})
        log.append(f"{name}: reader {reader}: {delta} new rows")
    tags = add_tags(ev, observation, policy=policy)
    info = next(iter(pcs.values())) if len(pcs) == 1 else {}
    meta = {"case": case, "images": sorted(name for name in exhibits if not name.startswith("_")),
            "pc": info, "pc_by_exhibit": pcs, "fat_time_zone": fat_tz,
            "examined_at": examined_at, "tool": tool, "acquisition": acquisition,
            "public_policy": policy,
            "reader_attempts": previous_meta.get("reader_attempts", []) + attempts,
            "current_reader_attempts": attempts,
            "note": "Extracted from explicitly configured images; reader failures are retained."}
    log.append(f"{tags} tags")
    return ev, meta, log


def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract facts from explicitly configured case images.")
    ap.add_argument("images", help="directory holding the images named in the manifest")
    ap.add_argument("--out", required=True, help="new JSON fact file; existing files are refused")
    ap.add_argument("--duckdb", help="also write a new DuckDB evidence database")
    ap.add_argument("--exhibits", required=True, help="explicit image/exhibit/role manifest")
    ap.add_argument("--case", default="Supplied case")
    ap.add_argument("--examined-at", default=None)
    ap.add_argument("--readers", nargs="+", choices=READER_ORDER)
    args = ap.parse_args(argv)
    from extractor.intake import validated_manifest, observation_time
    images, exhibits = validated_manifest(args.images, args.exhibits)
    if Path(args.out).exists() or (args.duckdb and Path(args.duckdb).exists()):
        ap.error("output already exists; choose a new evidence path")
    selected = selection(exhibits, args.readers)
    if not selected:
        ap.error("no configured exhibit supports the requested readers")
    ev, metadata, log = extract(images, exhibits, case=args.case,
                                examined_at=observation_time(args.examined_at), selected=selected,
                                manifest_source=f"acquisition manifest {Path(args.exhibits).name}")
    # Reserve the destinations before the legacy writers, which otherwise overwrite.
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.out).open("x"):
        pass
    meta = ev.write_json(args.out, metadata)
    if args.duckdb:
        Path(args.duckdb).parent.mkdir(parents=True, exist_ok=True)
        with Path(args.duckdb).open("x"):
            pass
        ev.write_duckdb(args.duckdb, (ROOT / "extractor" / "schema.sql").read_text())
    for line in log:
        print(line)
    for line in meta["unparsed"]:
        print("could not parse:", line)
    print(f"{args.out}: {meta['facts']} facts {meta['by_kind']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
