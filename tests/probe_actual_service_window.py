"""One bounded native Q42 and retained-index Q44 integration sample.

This manual audit uses an actual image and a previously bound selected ESE
snapshot. It never runs a model or scores answers. All outputs go to a new path.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace as NS
from unittest.mock import patch

from agent.answer_projection import claim_digest, project_answers
from agent.answer_store import project_bundle, public_profile, report_projection
from agent.timestamp_predicates import instant_ticks, recorded_in_interval
from app import brief, narrative
from app.report import render_html, report_options
from checker.catalog import ROLES
from checker.check import check
from checker.facts import JsonFacts
from checker.report import render as render_markdown
from eval.data_leakage_strict_draft.assemble import build
from extractor import structured_system, system
from extractor.store import Evidence, us
from verifier.verify import verify


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def capture(path):
    raw = path.read_bytes()
    return json.loads(raw), sha(raw), raw


def groups(source):
    by_obj = defaultdict(dict)
    rows = source.all()
    subjects = {row.obj: source.string(row.aux) for row in rows if row.kind == 'attributeSubject'}
    for row in rows:
        by_obj[row.obj][row.kind] = row.id
    result = defaultdict(dict)
    for row in rows:
        role = row.prov.get('attribute_role')
        if role in ROLES and row.kind == ROLES[role].value_kind:
            identity = subjects[row.obj]
            result[identity][role] = {'value': json.loads(source.string(row.aux)), 'prov': row.prov,
                                     'entry': [by_obj[row.obj]['attributeSubject'], by_obj[row.obj][ROLES[role].kind], row.id, role]}
    return list(result.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--ese-facts', type=Path, required=True)
    parser.add_argument('--ese-readback', type=Path, required=True)
    parser.add_argument('--service-readback', type=Path, required=True)
    parser.add_argument('--exclusion-readback', type=Path, required=True)
    parser.add_argument('--native-system-facts', type=Path,
                        help='Reuse the fresh registry facts from a retained preflight attempt; no second extraction')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    runtime = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    inputs = {}
    ese_raw, inputs['ese_readback'], _ = capture(args.ese_readback)
    service_raw, inputs['service_readback'], _ = capture(args.service_readback)
    exclusion_raw, inputs['exclusion_readback'], _ = capture(args.exclusion_readback)
    _, inputs['ese_facts'], ese_bytes = capture(args.ese_facts)
    frozen_ese = args.output / 'retained-ese-facts.json'
    frozen_ese.write_bytes(ese_bytes)
    assert ese_raw['status'] == 'passed' and ese_raw['native_store'] == 'iehistory'
    from dissect.target import Target
    target = Target.open(args.image)
    evidence = Evidence()
    ctx = {'examined_at': us(datetime.now(timezone.utc)), 'common': {
        'image': 'pc.E01', 'exhibit': 'PC', 'source_snapshot': 'base-volume', 'source_variant': 'primary'}}
    service_facts = args.output / 'native-system-facts.json'
    if args.native_system_facts:
        _, inputs['native_system_facts'], native_bytes = capture(args.native_system_facts)
        service_facts.write_bytes(native_bytes)
    else:
        structured_system.registry(evidence, target, ctx)
        assert not evidence.problems, evidence.problems
        evidence.write_json(service_facts, {'scope': 'fresh native registry reader only'})
    service_source = JsonFacts(service_facts)
    service_digest = sha(service_facts.read_bytes())
    service_roles = ['search.service.registry_key', 'search.service.start_code', 'search.service.start_type']
    service_group = next(g for g in groups(service_source) if set(service_roles) <= g.keys())
    assert type(service_group[service_roles[1]]['value']) is int
    assert service_group[service_roles[1]]['value'] == service_raw['start_native_value'] == 2
    assert service_group[service_roles[2]]['value'] == 'SERVICE_AUTO_START'
    h = next(h for h in system._hives(Evidence(), target) if h.name == 'SYSTEM' and not h.backup)
    with target.fs.path(h.path).open('rb') as stream:
        assert sha(stream.read()) == service_raw['source_hive_sha256']
    selected, _ = system._control_sets(Evidence(), h)
    assert selected == service_raw['selected']
    service_key = system._open(Evidence(), h, service_raw['service_key'])
    # The receipt names the requested lookup; the native key preserves actual
    # source casing ("services" in this hive). Compare that literal path.
    assert service_key.path.casefold() == service_raw['service_key'].casefold()
    assert service_group[service_roles[0]]['value'] == 'HKLM\\SYSTEM\\' + service_key.path
    # Correcting the common selector must also preserve the real exclusion value.
    exclusion = next(g for g in groups(service_source) if g.get('snapshot.exclusion.value_name', {}).get('value') == 'OutlookOST')
    assert exclusion['snapshot.exclusion.pattern']['value'] in exclusion_raw['registry']['literal_multi_string']
    assert exclusion['snapshot.exclusion.pattern']['prov']['control_set'] == selected
    results = []
    original_open = system._open
    for label, kind, duplicate in [('wrong_type_qword', 11, False), ('wrong_type_big_endian', 5, False), ('duplicate_current', 4, True)]:
        changed = Evidence()
        def open_key(ev, hive, path):
            key = original_open(ev, hive, path)
            if hive.name != 'SYSTEM' or path != 'Select' or key is None:
                return key
            values = [NS(name=v.name, value=v.value, type=kind if v.name.casefold() == 'current' else v.type) for v in key.values()]
            if duplicate:
                values.append(NS(name='CURRENT', value=service_raw['value'], type=4))
            return NS(path=key.path, values=lambda: iter(values))
        with patch.object(system, '_open', side_effect=open_key):
            structured_system.registry(changed, target, ctx)
        assert not any(json.loads(prov).get('attribute_role', '').startswith('search.service.') for *_, prov in changed.rows())
        assert changed.problems
        results.append({'control': 'Q42_' + label, 'status': 'passed', 'service_roles_emitted': 0})

    ese_source = JsonFacts(frozen_ese)
    ese_groups = groups(ese_source)
    ie_roles = ['search.index.' + name for name in ('item_url', 'date_modified', 'store', 'container_path', 'table', 'document_id')]
    ie = next(g for g in ese_groups if set(ie_roles) <= g.keys() and g[ie_roles[-1]]['value'] == ese_raw['DocID']
              and g[ie_roles[4]]['value'] == ese_raw['table'])
    assert ie[ie_roles[2]]['value'] == ese_raw['native_store']
    assert ie[ie_roles[1]]['prov']['native_filetime_bytes'] == ese_raw['native_filetime_big_endian_hex']
    assert ie[ie_roles[1]]['prov']['source_sha256'] == ese_raw['container_sha256']
    assert instant_ticks(ie[ie_roles[1]]['value']) == int.from_bytes(bytes.fromhex(ese_raw['native_filetime_big_endian_hex']), 'big') - 116444736000000000
    public = build()['questions.json']
    public['questions'] = [q for q in public['questions'] if q['id'] in ('Q42', 'Q44')]
    controls = results

    def make(name, group, roles):
        return {'candidate_id': name, 'claim': {'attributeTuple': [group[role]['entry'] for role in roles]}}

    def bound(candidate, qid, paths):
        return [{'candidate_id': candidate['candidate_id'], 'claim_sha256': claim_digest(candidate['claim']),
                 'question_id': qid, 'part': 0, 'path': path, 'field': field} for path, field in paths]

    def run_case(label, candidate, qid, paths, source, digest, *, expected=True, kernel=True, contract=public):
        cert = check(candidate['claim'], candidate['candidate_id'], source, out_dir=args.output)
        assert (cert['status'] == 'verified') == kernel, cert
        if kernel:
            assert cert['axioms'] == [] and verify(cert, source) == []
        bindings = bound(candidate, qid, paths)
        result = project_answers(contract, [candidate], bindings, source,
                                 admitted_ids=[candidate['candidate_id']] if kernel else [],
                                 require_claim_requirements=True, require_evidence_scope=True, evidence_facts_sha256=digest)
        assert bool(result['leaves']) == expected, (label, result['leaves'], result['unsupported'])
        controls.append({'control': label, 'status': 'passed', 'kernel_accepted': kernel,
                         'retained': len(result['leaves']), 'reasons': sorted({r['reason'] for r in result['unsupported']})})
        (args.output / (label + '-projection.json')).write_text(json.dumps(result, indent=2) + '\n')
        return cert, bindings, result

    def report_case(qid, cert, bindings, result, digest):
        run = {'case': {'name': 'Actual selected ' + qid + ' source control', 'facts_sha256': digest},
               'stats': {'verified': 1, 'rejected': 0}, 'findings': [cert], 'rejections': [], 'conclusions': [],
               'investigation': dict(public, facts_sha256=digest),
               'answer_bindings': {'schema_version': 1, 'case_id': public['case_id'], 'facts_sha256': digest, 'bindings': bindings},
               'run_manifest': {'inputs': {'facts': {'sha256': digest}}}}
        run['answer_projection'] = project_bundle(run, public_profile(run['investigation']))
        assert report_projection(run)[1] is None
        assert [leaf['value'] for leaf in run['answer_projection']['leaves']] == [leaf['value'] for leaf in result['leaves']]
        full, short, md = render_html(run), render_html(run, report_options(brief=True, sections=[])), render_markdown(run)
        assert html.escape(cert['english']) in full
        assert 'Structured answers from claim fields' in full and 'Structured answers from claim fields' in md
        assert brief.build(run)['counts']['dated'] == 0 and narrative.build(run)['points'] == []
        for name, text in [('report.html', full), ('short.html', short), ('report.md', md), ('run.json', json.dumps(run, indent=2))]:
            (args.output / (qid + '-' + name)).write_text(text)

    service = make('ActualService', service_group, service_roles)
    service_paths = [(['identification', 'service_registry_key'], 'value_0'), (['identification', 'startup'], 'value_2')]
    cert, bindings, result = run_case('Q42_positive', service, 'Q42', service_paths, service_source, service_digest)
    assert [leaf['value'] for leaf in result['leaves']] == [service_group[service_roles[i]]['value'] for i in (0, 2)]
    report_case('Q42', cert, bindings, result, service_digest)
    wrong_scope = deepcopy(public)
    next(q for q in wrong_scope['questions'] if q['id'] == 'Q42')['answer_schema']['x-claim-scope']['origins'][0]['source_variant'] = 'registry-backup:fixture'
    run_case('Q42_wrong_scope', make('BackupService', service_group, service_roles), 'Q42', service_paths,
             service_source, service_digest, expected=False, contract=wrong_scope)

    ie_paths = [(['records', 0, 'url'], 'value_0'), (['records', 0, 'date_modified'], 'value_1')]
    cert, bindings, result = run_case('Q44_positive', make('ActualIE', ie, ie_roles), 'Q44', ie_paths, ese_source, inputs['ese_facts'])
    assert {leaf['path'][-1]: leaf['value'] for leaf in result['leaves']} == {
        'url': ie[ie_roles[0]]['value'], 'date_modified': ie[ie_roles[1]]['value']}
    report_case('Q44', cert, bindings, result, inputs['ese_facts'])
    schema = next(q for q in public['questions'] if q['id'] == 'Q44')['answer_schema']
    properties = schema['properties']['records']['items']['properties']
    policy = properties['date_modified']['x-claim-requirement']['attribute_timestamp_conditions'][0]
    other_store = next(g for g in ese_groups if set(ie_roles) <= g.keys() and g[ie_roles[2]]['value'] != 'iehistory'
                       and recorded_in_interval(g[ie_roles[1]]['value'], role=ie_roles[1], policy=policy))
    run_case('Q44_other_store', make('OtherStore', other_store, ie_roles), 'Q44', ie_paths, ese_source, inputs['ese_facts'], expected=False)
    # This actual IE row has no DateCreated. Use its real ItemPathDisplay as
    # a same-row, same-native-type substitution; do not invent a date field.
    changed = make('PathNotModified', ie, ie_roles)
    changed['claim']['attributeTuple'][1] = ie['search.index.item_path']['entry']
    run_case('Q44_wrong_time_role', changed, 'Q44', ie_paths, ese_source, inputs['ese_facts'], expected=False)
    outside = deepcopy(public)
    for leaf in next(q for q in outside['questions'] if q['id'] == 'Q44')['answer_schema']['properties']['records']['items']['properties'].values():
        leaf['x-claim-requirement']['attribute_timestamp_conditions'][0]['stop'] = ie[ie_roles[1]]['value']
    run_case('Q44_exclusive_stop', make('AtExclusiveStop', ie, ie_roles), 'Q44', ie_paths, ese_source, inputs['ese_facts'], expected=False, contract=outside)
    mixed = make('MixedIERow', ie, ie_roles)
    alternate = next(g for g in ese_groups if set(ie_roles) <= g.keys() and g is not ie)
    mixed['claim']['attributeTuple'][-1] = alternate[ie_roles[-1]]['entry']
    run_case('Q44_mixed_row', mixed, 'Q44', ie_paths, ese_source, inputs['ese_facts'], expected=False, kernel=False)
    wrong_scope = deepcopy(public)
    next(q for q in wrong_scope['questions'] if q['id'] == 'Q44')['answer_schema']['x-claim-scope']['origins'][0]['source_snapshot'] = 'vss:other'
    run_case('Q44_wrong_scope', make('WrongIESnapshot', ie, ie_roles), 'Q44', ie_paths, ese_source, inputs['ese_facts'], expected=False, contract=wrong_scope)
    assert sha(args.ese_facts.read_bytes()) == inputs['ese_facts']
    receipt = {'status': 'passed', 'runtime': runtime, 'runner_sha256': sha(Path(__file__).read_bytes()),
               'inputs_captured_once_sha256': inputs, 'fresh_registry_facts_sha256': service_digest,
               'controls': controls, 'positive_certificates_replayed': 2, 'positive_fields': 4,
               'native_Current_type': service_raw['registry_type'], 'native_Current_python_type': service_raw['value_python_type'],
               'registry_facts_reused_from': str(args.native_system_facts) if args.native_system_facts else None,
               'selected_control_set': selected, 'Q50_source_retained': True,
               'db_state': ese_raw['db_state'], 'logs_replayed': False, 'whole_image_rehashed': False,
               'endpoint': 'Q44 revised indexed-record endpoint; no browser visit or actor claim',
               'scope': 'one selected actual-source sample per question, no model run or accuracy score'}
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == runtime
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
