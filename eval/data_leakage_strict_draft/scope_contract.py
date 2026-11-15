"""Compile reviewed public source selections, without examining case answer values."""
from copy import deepcopy

from agent.answer_requirements import SCOPE_KEY, parse_scope


def unavailable(meaning):
    return {'mode': 'unavailable', 'meaning': meaning}


def records(origins, *, same_origin=False):
    policy = {'mode': 'source_records', 'origins': deepcopy(origins)}
    if same_origin:
        policy['same_origin'] = True
    return parse_scope(policy)


def nodes_at(schema, tokens):
    """Find every explicitly declared schema node for a public answer path."""
    if not tokens:
        yield schema
        return
    for branch in schema.get('anyOf', []):
        yield from nodes_at(branch, tokens)
    token, *rest = tokens
    child = schema.get('items') if token == '*' else schema.get('properties', {}).get(token)
    if isinstance(child, dict):
        yield from nodes_at(child, rest)


def declare(schema, path, policy):
    parse_scope(policy)
    tokens = [token for token in path.split('/') if token]
    nodes = list(nodes_at(schema, tokens))
    if not nodes:
        raise ValueError('reviewed scope path is absent from public schema: ' + path)
    for node in nodes:
        if SCOPE_KEY in node and node[SCOPE_KEY] != policy:
            raise ValueError('conflicting source policies at ' + path)
        node[SCOPE_KEY] = deepcopy(policy)


def mark_unselected_leaves(schema):
    pending = [(schema, False)]
    while pending:
        node, inherited = pending.pop()
        selected = inherited or SCOPE_KEY in node
        children = []
        children.extend((child, selected) for child in node.get('properties', {}).values())
        if isinstance(node.get('items'), dict):
            children.append((node['items'], selected))
        if isinstance(node.get('additionalProperties'), dict):
            raise ValueError('dynamic source selection needs explicit review')
        children.extend((branch, selected) for branch in node.get('anyOf', []))
        if not children and node.get('type') not in ('object', 'array') and not selected:
            node[SCOPE_KEY] = unavailable('No reviewed source-origin mapping exists for this requested field; select and review its evidence origin before binding it.')
        pending.extend(children)


def apply_data_leakage_scopes(questions, plan):
    profiles = plan['source_profiles']
    mapped = {row['question_id']: row for row in plan['questions']}
    resolutions = []
    for question in questions:
        qid, schema = question['id'], question['answer_schema']
        if qid == 'Q1':
            names = ('pc', 'rm1', 'rm2', 'rm3')
            origins = [profiles[name + suffix]['origin'] for name in names
                       for suffix in ('_logical_image', '_acquisition_container')]
            declare(schema, '', records(origins))
            resolutions.append({'question_id': qid, 'path': [], 'mode': 'source_records',
                                'reason': plan['compilation_review']['digest_comparison']})
        else:
            for selection in mapped[qid]['policies']:
                if qid == 'Q51' and 'source_profiles' in selection:
                    if (selection['object_path'] != '/records/*'
                            or selection['source_profiles'] != ['pc_primary', 'pc_unallocated_recovery']
                            or selection.get('same_origin') is not True):
                        raise ValueError('Q51 requires the reviewed per-row exact-origin alternatives')
                    policy = records([profiles[name]['origin'] for name in selection['source_profiles']],
                                     same_origin=True)
                else:
                    profile = profiles.get(selection.get('source_profile'), {})
                    origin = profile.get('origin')
                    if origin and all(value is not None for value in origin.values()):
                        policy = records([origin])
                    else:
                        policy = unavailable(selection.get('known_unavailable') or profile.get('meaning')
                                             or selection.get('reason') or 'Exact source selection is unavailable.')
                for path in selection['object_path'].split('|'):
                    declare(schema, path, policy)
                    resolutions.append({'question_id': qid, 'path': path, 'mode': policy['mode'],
                                        'reason': selection['reason'],
                                        **({'same_origin': True, 'origins': deepcopy(policy['origins'])}
                                           if qid == 'Q51' and policy.get('same_origin') else {})})
        mark_unselected_leaves(schema)
    return resolutions


def apply_hacking_scopes(questions, plan):
    mapping = plan['approved_exhibit_mapping']
    # This is an approved input label, not an answer inferred from evidence.
    if isinstance(mapping, dict) and 'image' in mapping:
        image, exhibit = mapping['image'], mapping['exhibit']
    else:
        rows = [(name, entry) for name, entry in mapping.items() if not name.startswith('_')]
        if len(rows) != 1:
            raise ValueError('reviewed Hacking exhibit mapping must identify one image')
        image, entry = rows[0]
        exhibit = entry['exhibit']
    base = {'image': image, 'exhibit': exhibit, 'source_snapshot': 'base-volume', 'source_variant': 'primary'}
    resolutions = []
    for question in questions:
        qid = question['id']
        if qid == 'Q1':
            origins = [dict(base, source_snapshot='evidence-image', source_variant=variant)
                       for variant in ('logical-image', 'acquisition-container')]
        elif qid == 'Q31':
            origins = [dict(base, source_snapshot='examination', source_variant='antivirus',
                            input_source={'source_snapshot': 'base-volume', 'source_variant': 'primary'})]
        else:
            origins = [base]
        declare(question['answer_schema'], '', records(origins))
        resolutions.append({'question_id': qid, 'path': [], 'mode': 'source_records',
                            'origins': origins, 'scope': 'Source origin only; stronger unsupported meanings stay unsupported.'})
    return resolutions
