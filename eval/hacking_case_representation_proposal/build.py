"""Prepare the reviewed public Hacking representation proposal; never activate it."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile

from agent.case import read_question_profile
from agent import answer_requirements
from agent.answer_projection import catalog
from eval import benchmark
from eval.benchmark import Matcher
from eval.representation_derivative import publish_prepared


CASE_ID = 'nist-cfreds-hacking-focused-recorded-representation-proposal-v1'
REVISION = 'focused-q2-q3-q4-q8-representation-proposal-v1-public-only'
QUESTION_IDS = ['Q2', 'Q3', 'Q4', 'Q8']
LOCAL_INSTRUCTION = ('For Q3 and Q8, this contract interprets the published local-time display in the '
    'contemporaneous time zone addressed by Q4. Submit a source-supported explicit offset; the public '
    'profile does not disclose that offset. This is a declared comparison convention, not proof of '
    'the original display configuration.')
UTC_INSTRUCTION = ('For Q3 and Q8, present source-supported explicit instants in UTC as a report display '
    'choice. Preserve every fractional digit and the exact instant. UTC presentation does not establish '
    'the original display configuration or the computer timezone addressed by Q4. '
    'Report display timezone is an explicit presentation convention; it does not establish the machine '
    'historical local timezone. Native source timestamp retained.')
PRODUCT_INSTRUCTION = ('For Q2, report the exact recorded ProductName configuration text. Do not strip '
    'vendor names, editions, versions, punctuation or Unicode, and do not introduce aliases. Only the '
    'retained legacy casefold_whitespace matching applies; this field does not establish actual OS use.')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _load(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate public JSON key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)


def prepare(public_path, output_dir):
    """Capture an ancestor once and prepare a fresh, held public-only proposal."""
    ancestor = Path(public_path).read_bytes()
    public = _load(ancestor)
    with tempfile.TemporaryDirectory(prefix='hacking-public-snapshot-') as directory:
        snapshot = Path(directory) / 'questions.json'
        snapshot.write_bytes(ancestor)
        if read_question_profile(snapshot) != public:
            raise ValueError('captured public validation mismatch')
    if public.get('case_id') == CASE_ID or public.get('contract_revision') == REVISION:
        raise ValueError('proposal is not an eligible ancestor')
    derivative = deepcopy(public)
    questions = {q['id']: q for q in derivative['questions']}
    if set(questions) != {f'Q{i}' for i in range(1, 32)}:
        raise ValueError('complete 31-question Hacking public contract required')
    for qid in QUESTION_IDS:
        report = answer_requirements.inspect(questions[qid]['answer_schema'], catalog()['forms'],
            require_claim_requirements=True, require_evidence_scope=True)
        if (not report['requirements'] or any(row['status'] != 'catalog_support'
                for row in report['requirements']) or any(
                not report[key] or any(row['status'] != 'valid' for row in report[key])
                for key in ('row_requirements', 'scope_requirements'))):
            raise ValueError('selected question requires valid reviewed leaf, row and evidence scope guards')
    instructions = derivative.get('instructions', [])
    if instructions.count(LOCAL_INSTRUCTION) != 1:
        raise ValueError('exact ancestor local-display instruction required')
    instructions[instructions.index(LOCAL_INSTRUCTION)] = UTC_INSTRUCTION
    instructions.append(PRODUCT_INSTRUCTION)
    for qid, field, role in [('Q2', 'operating_system', 'os_product_name'),
                             ('Q3', 'installed_at', 'os_install_time'),
                             ('Q4', 'time_zone_setting', 'os_effective_time_zone'),
                             ('Q8', 'shutdown_at', 'machine_last_shutdown')]:
        try:
            leaf = questions[qid]['answer_schema']['properties'][field]
            types = leaf['x-claim-requirement']['semantic_types']
        except (KeyError, TypeError) as error:
            raise ValueError('expected reviewed Hacking leaf missing') from error
        if leaf.get('type') != 'string' or types != ['recorded_attribute_' + role + '_string']:
            raise ValueError('expected exact reviewed Hacking role required')
        if 'x-claim-display' in leaf:
            raise ValueError('ancestor display policy must be absent')
        if qid == 'Q2':
            if questions[qid].get('match') != {'strings': 'casefold_whitespace', 'list_order': 'unordered'}:
                raise ValueError('Q2 legacy matching must be unchanged')
            leaf['description'] = ('Exact ProductName text recorded in operating-system configuration; '
                'preserve vendor, edition, version, punctuation and Unicode. This does not establish actual use.')
            leaf['x-claim-requirement']['meaning'] = (
                'Exact ProductName configuration text recorded by the source; not proof of actual operating-system use.')
        elif qid in ('Q3', 'Q8'):
            expected = {'strings': 'casefold_whitespace', 'list_order': 'unordered',
                        'timestamps': {'/' + field: {'tolerance_seconds': 0}}}
            if questions[qid].get('match') != expected:
                raise ValueError('zero-tolerance instant matching required')
            leaf.update(format='date-time', **{'x-claim-display': {
                'kind': 'report_timestamp_iso_v1', 'timezone': 'public_time_zone'}})
    zone = questions['Q4']
    if zone.get('match') != {'strings': 'casefold_whitespace', 'list_order': 'unordered'}:
        raise ValueError('unexpected Q4 ancestor match policy')
    zone['match'].update(normalization_profile={'id': 'typed-representation-v1', 'version': 1,
        'ancestor_public_sha256': _sha(ancestor), 'source_contexts': {}},
        normalization={'version': 1, 'fields': {'/time_zone_setting': {
            'kind': 'zone-label-offset-v1', 'label_mode': 'casefold_whitespace'}}})
    derivative['questions'] = [questions[qid] for qid in QUESTION_IDS]
    for question in derivative['questions']:
        Matcher(question.get('match'), 'UTC')
    derivative.update(case_id=CASE_ID, contract_revision=REVISION, time_zone='UTC',
                      title='Hacking focused Q2/Q3/Q4/Q8 representation development contract')
    encoded = (json.dumps(derivative, indent=2, ensure_ascii=False) + '\n').encode()
    manifest = {'schema_version': 1, 'status': 'prepared_public_only',
        'case_id': CASE_ID, 'contract_revision': REVISION,
        'question_ids': QUESTION_IDS, 'ancestor_question_count': 31, 'question_count': 4,
        'ancestor_public_sha256': _sha(ancestor), 'questions_sha256': _sha(encoded),
        'implementation_sha256': _sha(Path(__file__).read_bytes()),
        'publisher_implementation_sha256': _sha(Path(__file__).parents[1].joinpath('representation_derivative.py').read_bytes()),
        'normalization_implementation_sha256': _sha(Path(__file__).parents[1].joinpath('match_normalization.py').read_bytes()),
        'benchmark_implementation_sha256': _sha(Path(benchmark.__file__).read_bytes()),
        'observed_scorer_version': benchmark.VERSION,
        'reference_alignment_required': True, 'scorer_version_required': '2.2',
        'source_precision_alignment_required': True,
        'changes': ['Q2 exact recorded ProductName description and meaning; legacy matching retained',
                    'Q4 explicit same-label same-offset representation matching',
                    'Q3/Q8 UTC report display retaining native fractional precision and exact instant',
                    'UTC public presentation convention replaces prior local-display instruction'],
        'model_run_ready': False, 'private_reference_included': False,
        'model_invoked': False, 'scoring_performed': False}
    publish_prepared(output_dir, {'questions.json': encoded,
        'manifest.json': (json.dumps(manifest, indent=2) + '\n').encode()})
    return manifest
