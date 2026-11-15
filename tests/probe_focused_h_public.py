"""Check the prepared PUBLIC focused contract against retained native host facts.

No expected answers, scoring reference or model is loaded. A successful sample
does not activate the prepared endpoint or establish reference agreement.
"""
import argparse
from copy import deepcopy
import hashlib
import html
import json
from pathlib import Path
import subprocess

from agent.answer_projection import claim_digest, project_answers
from agent.answer_store import project_bundle, public_profile, report_projection
from agent.timestamp_predicates import instant_ticks
from app.report import render_html
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from verifier.verify import verify


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public', type=Path, required=True)
    parser.add_argument('--facts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    public_bytes, fact_bytes = args.public.read_bytes(), args.facts.read_bytes()
    assert sha(public_bytes) == '1de3c4fa1516f49e197568b55017a1d06ea98672b027a287e7357cd0e01acca7'
    public = json.loads(public_bytes)
    assert {q['id'] for q in public['questions']} == {'Q2', 'Q3', 'Q4', 'Q8'} and public['time_zone'] == 'UTC'
    (args.output / 'public.json').write_bytes(public_bytes)
    fact_copy = args.output / 'facts.json'
    fact_copy.write_bytes(fact_bytes)
    source = JsonFacts(fact_copy)
    digest = sha(fact_bytes)
    rows = source.all()

    def native(role):
        matches = [r for r in rows if r.kind == ROLES[role].value_kind and r.prov.get('attribute_role') == role]
        assert len(matches) == 1, (role, matches)
        row = matches[0]
        related = {r.kind: r.id for r in rows if r.obj == row.obj}
        return [related['attributeSubject'], related[ROLES[role].kind], row.id, role], json.loads(source.string(row.aux))

    specs = [('Q2', 'operating_system', 'os.product_name'), ('Q3', 'installed_at', 'os.install_time'),
             ('Q4', 'time_zone_setting', 'os.effective_time_zone'), ('Q8', 'shutdown_at', 'machine.last_shutdown')]
    candidates, certs, bindings, originals = [], [], [], {}
    for qid, field, role in specs:
        entry, value = native(role)
        candidate = {'candidate_id': 'Focused' + qid, 'claim': {'attributeRecorded': entry}}
        cert = check(candidate['claim'], candidate['candidate_id'], source, out_dir=args.output)
        assert cert['status'] == 'verified' and cert['axioms'] == [] and verify(cert, source) == []
        candidates.append(candidate)
        certs.append(cert)
        originals[qid] = value
        bindings.append({'candidate_id': candidate['candidate_id'], 'claim_sha256': claim_digest(candidate['claim']),
                         'question_id': qid, 'path': [field], 'field': 'value'})

    def project(offered, contract=public, supplied=candidates):
        return project_answers(contract, supplied, offered, source,
                               admitted_ids=[c['candidate_id'] for c in supplied],
                               require_claim_requirements=True, require_evidence_scope=True, evidence_facts_sha256=digest)

    result = project(bindings)
    assert len(result['leaves']) == 4 and not result['unsupported']
    for leaf in result['leaves']:
        qid = leaf['question_id']
        if qid in ('Q3', 'Q8'):
            assert leaf['source_value'] == originals[qid]
            assert instant_ticks(leaf['value']) == instant_ticks(originals[qid])
            assert leaf['display']['report_timezone'] == 'UTC'
        else:
            assert leaf['value'] == originals[qid] and 'display' not in leaf
    shutdown = next(leaf for leaf in result['leaves'] if leaf['question_id'] == 'Q8')
    assert shutdown['display']['fraction_digits'] == 7
    assert shutdown['value'].endswith('.1092164+00:00')
    controls = []

    def refused(name, offered, contract=public, supplied=candidates):
        response = project(offered, contract=contract, supplied=supplied)
        assert not response['leaves'] and response['unsupported'], response
        controls.append({'control': name, 'status': 'passed', 'reasons': [r['reason'] for r in response['unsupported']]})

    # Same JSON primitive type cannot make one semantic role supply another.
    wrong_role = dict(bindings[3], question_id='Q2', path=['operating_system'])
    refused('Q2_shutdown_string_is_not_product_name', [wrong_role])
    refused('Q3_examination_timestamp_is_not_installation', [dict(bindings[1], field='examined_at_us')])
    raw_entry, _ = native('os.time_zone_setting')
    raw_label = {'candidate_id': 'RawZone', 'claim': {'attributeRecorded': raw_entry}}
    cert = check(raw_label['claim'], 'RawZone', source, out_dir=args.output)
    assert cert['status'] == 'verified' and verify(cert, source) == []
    refused('Q4_raw_label_is_not_effective_label_and_offset', [dict(bindings[2], candidate_id='RawZone',
            claim_sha256=claim_digest(raw_label['claim']))], supplied=[raw_label])
    refused('Q8_truncated_display_value_not_repaired', [dict(bindings[3], value=shutdown['value'].replace('.1092164', '.109216'))])
    foreign = deepcopy(public)
    for question in foreign['questions']:
        question['answer_schema']['x-claim-scope']['origins'][0]['image'] = 'other.E01'
    refused('foreign_image_cannot_supply_any_focus_field', bindings, contract=foreign)
    unknown_zone = deepcopy(public)
    unknown_zone['time_zone'] = None
    refused('timestamp_display_requires_explicit_zone', [bindings[1], bindings[3]], contract=unknown_zone)
    run = {'case': {'name': 'Focused public host-field source diagnostic', 'facts_sha256': digest},
           'stats': {'verified': 4, 'rejected': 0}, 'findings': certs, 'rejections': [], 'conclusions': [],
           'investigation': dict(public, facts_sha256=digest),
           'answer_bindings': {'schema_version': 1, 'case_id': public['case_id'], 'facts_sha256': digest, 'bindings': bindings},
           'run_manifest': {'inputs': {'facts': {'sha256': digest}}}}
    run['answer_projection'] = project_bundle(run, public_profile(run['investigation']))
    assert report_projection(run)[1] is None
    report = render_html(run)
    assert all(html.escape(cert['english']) in report for cert in certs)
    (args.output / 'run.json').write_text(json.dumps(run, indent=2) + '\n')
    (args.output / 'report.html').write_text(report)
    receipt = {'status': 'passed', 'runtime': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
               'runner_sha256': sha(Path(__file__).read_bytes()), 'public_sha256': sha(public_bytes), 'facts_sha256': digest,
               'certificates_replayed': 4, 'retained_fields': 4, 'negative_controls': controls,
               'prepared_endpoint_activated': False, 'private_reference_read': False,
               'scope': 'actual native source fields through prepared public projection/display/report; no model or answer score'}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
