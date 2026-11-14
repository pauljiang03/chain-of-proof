"""Reissue the union of certified claims from saved runs, without an answer key.

    python -m checker.combine --facts evidence/case_facts.json \
        --run /path/miner/run.json /path/agent/run.json --out runs/dev/combined

Claims are canonicalized, deduplicated and sorted before new certificate IDs are
assigned. Every claim is checked again against the supplied evidence. Source rows
must match their saved certificate hashes, including exact census membership.
Rejected proposals and free-form conclusions do not enter the certified report.
This composes existing searches; it is neither a new AI run nor new extraction.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from threading import Lock

from . import claims, export, report
from .check import check
from .facts import FactSource, open_source


class _LockedSource(FactSource):
    """DuckDB cursors share a connection; serialize reads while Lean runs in parallel."""

    def __init__(self, source):
        self.source = source
        self.lock = Lock()

    def get(self, ids):
        with self.lock:
            return self.source.get(ids)

    def string(self, sid):
        with self.lock:
            return self.source.string(sid)

    def all(self):
        with self.lock:
            return self.source.all()


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(2 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_claim(raw):
    """Canonical syntax, preserving the stated order of conjunction parts."""
    value = claims.to_json(claims.parse(raw))
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def bound_to_source(finding, source):
    """Refuse stale fact IDs before they can accidentally denote different records."""
    claim = claims.parse(finding['claim'])
    ids, found = claims.cited_facts(claim, source)
    cited = finding.get('cited_facts', [])
    saved = {r['id']: r for r in cited}
    if len(saved) != len(cited):
        raise ValueError('duplicate cited fact IDs in source certificate')
    if set(saved) != set(ids):
        raise ValueError('source certificate cites different evidence membership '
                         '(including census membership)')
    for fact_id in ids:
        if saved[fact_id].get('row_sha256') != found[fact_id].row_sha256():
            raise ValueError(f'source certificate fact {fact_id} does not match --facts')
        for slot in ('obj', 'aux'):
            if saved[fact_id].get(f'{slot}_text') != source.string(getattr(found[fact_id], slot)):
                raise ValueError(f'source certificate fact {fact_id} {slot} text does not match --facts')


def combine(run_paths, facts_path, out_dir, workers=4):
    if not run_paths:
        raise ValueError('provide at least one source run')
    if workers < 1:
        raise ValueError('workers must be positive')
    out = Path(out_dir)
    if out.exists():
        raise ValueError('use a new output directory; refusing to overwrite an existing run')
    source = _LockedSource(open_source(facts_path))
    # One input file is one source even if it was passed through multiple aliases.
    paths = {}
    for raw in run_paths:
        path = Path(raw)
        key = str(path.resolve())
        if key not in paths or str(path) < str(paths[key]):
            paths[key] = path
    groups, sources, names = {}, [], set()
    for path in sorted(paths.values(), key=str):
        run = json.loads(path.read_text())
        run_hash = file_sha256(path)
        name = run.get('case', {}).get('name')
        if name:
            names.add(name)
        info = {'run': str(path), 'sha256': run_hash,
                'certified_findings': 0, 'nonverified_findings_ignored': 0,
                'source_rejected_proposals': len(run.get('rejections', [])),
                'source_declared_rejections': run.get('stats', {}).get('rejected'),
                'excluded_unverified_conclusions': len(run.get('conclusions', []))}
        local_ids = {}
        for finding in run.get('findings', []):
            if finding.get('status') != 'verified':
                info['nonverified_findings_ignored'] += 1
                continue
            fid = finding.get('finding_id')
            if not isinstance(fid, str) or not fid:
                raise ValueError(f'{path}: source finding has no ID')
            try:
                key = canonical_claim(finding['claim'])
                bound_to_source(finding, source)
            except (KeyError, claims.ClaimError, ValueError) as error:
                raise ValueError(f'{path}: {fid}: {error}') from error
            if fid in local_ids and local_ids[fid] != key:
                raise ValueError(f'{path}: finding ID {fid} denotes different claims')
            local_ids[fid] = key
            origin = {'run': str(path), 'run_sha256': run_hash, 'finding_id': fid,
                      'question': finding.get('question', '')}
            group = groups.setdefault(key, [])
            if origin not in group:
                group.append(origin)
            info['certified_findings'] += 1
        sources.append(info)
    out.mkdir(parents=True, exist_ok=False)
    plan = [(f'F{n:06d}', key, sorted(groups[key], key=lambda x: (x['run'], x['finding_id'])))
            for n, key in enumerate(sorted(groups), 1)]

    def issue(item):
        fid, key, origins = item
        certificate = check(json.loads(key), fid, source, 'Combined certified findings',
                            out, proposer='combined saved claims')
        if certificate['status'] != 'verified':
            raise ValueError(f'{fid}: merged claim no longer certifies: {certificate.get("reason")}')
        certificate['source_findings'] = origins
        (out / f'{fid}.json').write_text(json.dumps(certificate, indent=2, ensure_ascii=False) + '\n')
        return certificate

    # Warm the Lean build before concurrent checks; output IDs follow plan order.
    results = [issue(plan[0])] if plan else []
    if len(plan) > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results.extend(pool.map(issue, plan[1:]))
    (out / 'proposals.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in results))
    case_name = next(iter(names)) if len(names) == 1 else 'Combined certified investigation'
    combined = export.bundle(out, case_name)
    combined['case'].update(
        composition='Canonical union of existing certified claims, checked again against the same evidence',
        new_ai_run=False, new_facts=False,
        evidence_path=str(facts_path), evidence_sha256=file_sha256(facts_path))
    combined['sources'] = sources
    combined['composition'] = {
        'input_certified_findings': sum(s['certified_findings'] for s in sources),
        'unique_certified_claims': len(results),
        'duplicate_claims_removed': sum(s['certified_findings'] for s in sources) - len(results),
        'source_rejected_proposals': sum(s['source_rejected_proposals'] for s in sources),
        'excluded_unverified_conclusions': sum(s['excluded_unverified_conclusions'] for s in sources),
        'selection': 'All source findings marked verified, with matching evidence; no reference or answer key used',
    }
    (out / 'run.json').write_text(json.dumps(combined, indent=2, ensure_ascii=False) + '\n')
    rendered = report.render(combined)
    title, body = rendered.split('\n', 1)
    provenance = ('This report combines existing certified claims from saved runs. Every claim '
                  'was checked again against the supplied evidence; no answer key or reference '
                  'was used to select claims. It is not a new AI investigation and adds no new '
                  'facts. Rejected proposals and unverified conclusions are excluded.\n')
    (out / 'report.md').write_text(title + '\n\n' + provenance + body)
    (out / 'source_map.json').write_text(json.dumps({
        'sources': sources,
        'findings': {r['finding_id']: r['source_findings'] for r in results},
        'composition': combined['composition'],
    }, indent=2, ensure_ascii=False) + '\n')
    return combined


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', required=True)
    parser.add_argument('--run', action='append', nargs='+', required=True,
                        help='source run files; may be given repeatedly')
    parser.add_argument('--out', required=True, help='new directory for certificates and report')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args(argv)
    data = combine([p for group in args.run for p in group], args.facts, args.out, args.workers)
    counts = data['composition']
    print(f"{counts['unique_certified_claims']} certified claims; "
          f"{counts['duplicate_claims_removed']} duplicate claims removed; "
          f"{counts['excluded_unverified_conclusions']} unverified conclusions excluded")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
