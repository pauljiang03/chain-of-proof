"""Reissue a saved run under the current checker, without rerunning an investigator.

Always use a new output directory. Historical runs and benchmark scores are untouched.
    python -m eval.recheck --run runs/investigator-1/run.json --out runs/dev/rechecked
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from agent.conclusions import Conclusions
from checker import export, report
from checker import claims
from checker.check import check
from checker.combine import _LockedSource, bound_to_source
from checker.facts import open_source
from verifier.verify import verify


def recheck(run_path, facts_path, out):
    run_path, facts_path, out = Path(run_path), Path(facts_path), Path(out)
    if out.exists():
        raise ValueError('use a new directory; refusing to overwrite an existing run')
    run = json.loads(run_path.read_text())
    source = _LockedSource(open_source(facts_path))
    out.mkdir(parents=True)

    def one(f):
        try:
            bound_to_source(f, source)
        except (ValueError, KeyError, claims.ClaimError) as error:
            raise ValueError(f"{f['finding_id']}: source evidence changed; "
                             f"recheck cannot remap fact IDs: {error}") from error
        result = check(f['claim'], f['finding_id'], source, f.get('question', ''), out,
                       proposer='recheck:' + str(run_path))
        if result['status'] != 'verified':
            raise ValueError(f"previous finding {f['finding_id']} no longer certifies: {result}")
        problems = verify(result, source)
        if problems:
            raise ValueError(f"reissued finding {f['finding_id']}: {problems}")
        return result

    with ThreadPoolExecutor(max_workers=4) as pool:
        findings = list(pool.map(one, run['findings']))
    # Preserve the original refusals as historical proposals, not fresh outcomes.
    proposals = findings + [dict(r, historical_rejection=True) for r in run.get('rejections', [])]
    (out / 'proposals.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in proposals))
    conclusions, review = Conclusions(out), []
    for c in run.get('conclusions', []):
        verdict = conclusions.add(c['text'], c['finding_ids'], findings,
                                  c.get('author', 'historical investigator'))
        review.append({'original_conclusion_id': c['conclusion_id'],
                       'original_text': c['text'], 'result': verdict})
    new = export.bundle(out, run['case']['name'])
    new['case']['reissued_from'] = str(run_path)
    new['case']['note'] = 'Same proposed claims, current checker; not a new AI run or blind score.'
    (out / 'run.json').write_text(json.dumps(new, indent=2) + '\n')
    (out / 'report.md').write_text(report.render(new))
    changed = [a['finding_id'] for a, b in zip(run['findings'], findings) if a['english'] != b['english']]
    result = {'source_run': str(run_path),
              'source_run_sha256': hashlib.sha256(run_path.read_bytes()).hexdigest(),
              'evidence_sha256': hashlib.sha256(facts_path.read_bytes()).hexdigest(),
              'reissued_and_reverified': len(findings), 'changed_english': changed,
              'conclusion_review': review,
              'note': 'Passing the conclusion checks is not verification of an inference. '
                      'No LLM marker was rerun and no historical benchmark score was changed.'}
    (out / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', required=True)
    ap.add_argument('--facts', default='evidence/case_facts.json')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    r = recheck(args.run, args.facts, args.out)
    print(f"{r['reissued_and_reverified']} reissued and reverified; "
          f"{len(r['changed_english'])} sentences changed; "
          f"{sum(c['result']['status'] == 'rejected' for c in r['conclusion_review'])} conclusions refused")


if __name__ == '__main__':
    main()
