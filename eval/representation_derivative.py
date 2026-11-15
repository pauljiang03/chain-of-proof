"""Prepare a public-only prospective representation derivative; never score."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from agent.case import read_question_profile
from eval.benchmark import Matcher
from eval.match_normalization import PROFILE_ID, VERSION, validate_config, validate_profile


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _load(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _schema_paths(schema, pointer):
    """Resolve explicit public schema paths, refusing unions and opaque schemas."""
    if not isinstance(pointer, str) or (pointer and not pointer.startswith('/')) or re.search(r'~(?![01])', pointer):
        raise ValueError('invalid public schema pointer')
    nodes = [schema]
    for raw in pointer.split('/')[1:] if pointer else []:
        token = raw.replace('~1', '/').replace('~0', '~')
        following = []
        for node in nodes:
            if not isinstance(node, dict) or any(key in node for key in (
                    '$ref', '$dynamicRef', '$recursiveRef', 'oneOf', 'anyOf', 'allOf')):
                raise ValueError('ambiguous public schema path')
            if node.get('type') == 'object':
                properties = node.get('properties', {})
                if token == '*':
                    if not properties or node.get('additionalProperties', True) is not False:
                        raise ValueError('opaque wildcard object path')
                    following.extend(properties.values())
                elif token in properties:
                    following.append(properties[token])
                else:
                    raise ValueError('unknown public schema property')
            elif node.get('type') == 'array' and (token == '*' or re.fullmatch(r'0|[1-9][0-9]*', token)):
                if not isinstance(node.get('items'), dict):
                    raise ValueError('opaque public array path')
                if token != '*' and isinstance(node.get('maxItems'), int) and int(token) >= node['maxItems']:
                    raise ValueError('array pointer exceeds public schema bounds')
                following.append(node['items'])
            else:
                raise ValueError('incompatible public schema path')
        nodes = following
    if not nodes or any(not isinstance(node, dict) or node.get('type') != 'string' or any(
            key in node for key in ('$ref', '$dynamicRef', '$recursiveRef', 'oneOf', 'anyOf', 'allOf')) for node in nodes):
        raise ValueError('representation rules require unambiguous string leaves')


def _ambiguous(fields):
    items = list(fields)
    for index, first in enumerate(items):
        left = first.split('/')
        for second in items[index + 1:]:
            right = second.split('/')
            if len(left) == len(right) and all(a == b or a == '*' or b == '*' for a, b in zip(left, right)):
                if sum(x != '*' for x in left) == sum(x != '*' for x in right):
                    raise ValueError('ambiguous representation pointers')


def prepare(public_path, policy_path, output_dir):
    """Write a fresh questions.json and manifest after all public validation succeeds.

    Policy keys are exactly version, case_id, contract_revision,
    ancestor_public_sha256, and questions. Each question maps to exactly fields
    (pointer -> existing typed rule) and source_contexts (explicit profile contexts).
    """
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise ValueError('output must be fresh')
    ancestor_bytes = Path(public_path).read_bytes()
    policy_bytes = Path(policy_path).read_bytes()
    public = _load(ancestor_bytes)
    # The shared validator accepts a path. Give it a private immutable snapshot
    # of the captured bytes, never a second read of the caller's mutable path.
    with tempfile.TemporaryDirectory(prefix='public-contract-snapshot-') as snapshot_dir:
        snapshot = Path(snapshot_dir) / 'questions.json'
        snapshot.write_bytes(ancestor_bytes)
        if read_question_profile(snapshot) != public:
            raise ValueError('captured public snapshot validation mismatch')
    policy = _load(policy_bytes)
    if not isinstance(policy, dict) or set(policy) != {
            'version', 'case_id', 'contract_revision', 'ancestor_public_sha256', 'questions'}:
        raise ValueError('invalid derivative policy keys')
    if type(policy['version']) is not int or policy['version'] != 1:
        raise ValueError('unsupported derivative policy version')
    if policy['ancestor_public_sha256'] != _sha(ancestor_bytes):
        raise ValueError('ancestor public hash mismatch')
    for field in ('case_id', 'contract_revision'):
        if not _text(policy[field]) or policy[field] == public.get(field):
            raise ValueError('derivative needs a new case_id and contract_revision')
    selections = policy['questions']
    if not isinstance(selections, dict) or not selections:
        raise ValueError('explicit question policies required')
    derivative = deepcopy(public)
    questions = {question['id']: question for question in derivative['questions']}
    for qid, selection in selections.items():
        if qid not in questions:
            raise ValueError('unknown public question')
        if not isinstance(selection, dict) or set(selection) != {'fields', 'source_contexts'}:
            raise ValueError('invalid question policy keys')
        question = questions[qid]
        config = deepcopy(question.get('match', {}))
        if 'normalization' in config or 'normalization_profile' in config:
            raise ValueError('ancestor already declares representation rules')
        profile = {'id': PROFILE_ID, 'version': VERSION,
                   'ancestor_public_sha256': policy['ancestor_public_sha256'],
                   'source_contexts': selection['source_contexts']}
        normalization = {'version': VERSION, 'fields': selection['fields']}
        validate_profile(profile)
        fields = validate_config(normalization, profile=profile)
        _ambiguous(fields)
        for pointer in fields:
            _schema_paths(question['answer_schema'], pointer)
        used = {rule['context'] for rule in fields.values() if rule['kind'] == 'windows-volume-path-v1'}
        if used != set(profile['source_contexts']):
            raise ValueError('source contexts must be exactly those used by path rules')
        config.update(normalization_profile=profile, normalization=normalization)
        Matcher(config, public.get('time_zone'))  # Includes legacy-rule overlap rejection.
        question['match'] = config
    derivative.update(case_id=policy['case_id'], contract_revision=policy['contract_revision'])
    derivative.setdefault('instructions', []).append(
        'Prospective public representation derivative. Raw answers and evidence remain unchanged. '
        'Separate independent reference alignment and review are required before comparison; preparation is not execution authorization.')
    questions_bytes = (json.dumps(derivative, indent=2, ensure_ascii=False) + '\n').encode()
    manifest = {'schema_version': 1, 'status': 'prepared_public_only_not_run',
                'case_id': derivative['case_id'], 'contract_revision': derivative['contract_revision'],
                'ancestor_public_sha256': _sha(ancestor_bytes), 'policy_sha256': _sha(policy_bytes),
                'implementation_sha256': _sha(Path(__file__).read_bytes()),
                'normalization_implementation_sha256': _sha(Path(__file__).with_name('match_normalization.py').read_bytes()),
                'questions_sha256': _sha(questions_bytes), 'question_ids': sorted(selections),
                'separate_reference_alignment_required': True, 'private_reference_included': False,
                'model_invoked': False, 'scoring_performed': False}
    publish_prepared(destination, {'questions.json': questions_bytes, 'policy.json': policy_bytes,
        'manifest.json': (json.dumps(manifest, indent=2) + '\n').encode()})
    return manifest


def publish_prepared(output_dir, files):
    """Publish immutable file bytes exclusively; manifest.json is the completion marker."""
    destination = Path(output_dir)
    if (not isinstance(files, dict) or 'manifest.json' not in files or any(
            not isinstance(name, str) or name in ('', '.', '..') or '/' in name or '\\' in name
            or '\0' in name or type(data) is not bytes for name, data in files.items())):
        raise ValueError('immutable basename files and manifest.json required')
    if destination.exists() or destination.is_symlink():
        raise ValueError('output must be fresh')
    # Validate and stage everything before exclusively claiming the output name.
    # Exclusive hard links publish complete files without replacing race winners.
    # The manifest is linked last and is the atomic completion marker.
    staging = Path(tempfile.mkdtemp(prefix='.representation-', dir=destination.parent))
    owned_directory, published = None, []
    try:
        for name, data in files.items():
            (staging / name).write_bytes(data)
        destination.mkdir()  # Exclusive: never replace a concurrently created directory.
        owned_directory = destination.stat()
        for name in [name for name in files if name != 'manifest.json'] + ['manifest.json']:
            target = destination / name
            os.link(staging / name, target)  # Exclusive creation; no partial file visibility.
            published.append((target, (staging / name).stat()))
    except BaseException:
        for target, owned in reversed(published):
            try:
                current = target.lstat()
                if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                    target.unlink()
            except FileNotFoundError:
                pass
        if owned_directory:
            try:
                current = destination.lstat()
                if (current.st_dev, current.st_ino) == (owned_directory.st_dev, owned_directory.st_ino):
                    destination.rmdir()
            except OSError:
                pass  # Never remove files placed there by another actor.
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
