"""Literal claim-field projection, shared by unchecked and checked candidates.

This module does not decide whether claims hold. Selectors follow the proposed
form, even for a wrong record kind, identity join, count, or time order. B can
filter a frozen projection without opening the evidence again. Question placement
and relevance are supplied by the investigator, never proved by this projection.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from zoneinfo import ZoneInfo

from checker import claims
from checker.facts import KINDS
from checker.catalog import ROLES, DIGEST_ALGORITHMS, decode_value, roles_catalog
from agent import answer_requirements, answer_references

VERSION = 1
AUTHORITIES = frozenset({'unchecked', 'recorded_certificates', 'independently_replayed'})
FORMATS = frozenset({'identity', 'utc_iso', 'local_minute', 'local_date', 'integer'})
MAX_SCHEMA_NODES = 256
MAX_SCHEMA_DEPTH = 32
MAX_SCHEMA_ALTERNATIVES = 32
SCOPE = ('Projection preserves the proposed claim semantics; it does not check or repair them. '
         'Authority is supplied by the caller and is not a new certificate. Accepted semantic fields are '
         'relative to the cited facts and approved rules. Question placement, relevance, complete lists, '
         'answer accuracy and investigation completeness are not certified. Missing fields remain omitted.')


def _finite(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _finite(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _finite(item)
        return
    raise ValueError('projection inputs must contain finite JSON values only')


def _encoded(value):
    _finite(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def claim_digest(claim):
    """Hash the exact submitted JSON value, without claim normalization."""
    return hashlib.sha256(_encoded(claim)).hexdigest()


def _record(argument, slot, meaning):
    return {'argument': argument, 'slot': slot, 'semantic_type': meaning}


def _argument(index, meaning, decode=False):
    return {'literal_argument': index, 'semantic_type': meaning, 'decode_entity': decode}


def _assertion(meaning):
    return {'literal': True, 'semantic_type': meaning}


# Field roles follow the claim form, never the actual source row's kind. These
# select only formal core slots / literal claim arguments, not provenance fields.
_SINGLE = {
    'usbConnected': ('usbInsert', 'device_serial', 'connection_context'),
    'opened': ('lnkTarget', 'path', 'volume_or_share'),
    'searched': ('webSearch', 'query', 'browser'),
    'fileCreatedAt': ('fileCreated', 'path', 'volume_or_recovery_area'),
    'fileModifiedAt': ('fileModified', 'path', 'volume_or_recovery_area'),
    'fileDeletedAt': ('fileDeleted', 'path', 'volume'),
    'fileRemovedAt': ('fileRemoved', 'name_or_path', 'volume'),
    'fileCreationRecordedAt': ('fileCreationRecorded', 'name_or_path', 'volume'),
    'volumeRecordedAt': ('volumeRecorded', 'disc', 'volume'),
    'emailed': ('emailSent', 'subject', 'address_record'),
    'burnTrace': ('cdBurn', 'activity_record', 'record_source'),
    'settingRecorded': ('systemSetting', 'setting', 'value'),
    'accountRecorded': ('accountSeen', 'account', 'account_context'),
    'sessionRecorded': ('sessionEvent', 'event', 'account_or_machine'),
    'programInstalledAt': ('programInstalled', 'program', 'version'),
    'programRan': ('programRun', 'program', 'path'),
    'visited': ('webVisit', 'url', 'browser'),
    'downloaded': ('fileDownloaded', 'path', 'url'),
    'typedInSearchBox': ('localSearch', 'text', 'search_context'),
    'cloudEvent': ('cloudFile', 'path', 'service_event'),
    'noteFound': ('noteText', 'text', 'application'),
    'folderRecorded': ('folderOpened', 'path', 'record_source'),
    'renamed': ('fileRenamed', 'old_name_or_path', 'new_name_or_path'),
    'fileRecorded': ('fileSeen', 'path', 'record_source'),
    'shadowCopyMade': ('shadowCopy', 'shadow_copy', 'volume'),
    'contentHashed': ('fileContent', 'path', 'sha256'),
    'journalNamed': ('journalName', 'name_or_path', 'scoped_identity'),
    'journalParentRecorded': ('journalParent', 'child_identity', 'parent_identity'),
    'journalRemovalObserved': ('journalRemoval', 'name_or_path', 'scoped_identity'),
    'journalPathAt': ('journalPath', 'path_or_incomplete_suffix', 'scoped_identity'),
}
_FIELDS = {}
for _form, (_kind, _obj, _aux) in _SINGLE.items():
    _FIELDS[_form] = {_obj: _record(0, 'obj', _obj), _aux: _record(0, 'aux', _aux),
                     'recorded_time_us': _record(0, 't', 'recorded_timestamp_not_action_or_execution_guarantee_us'),
                     'uncertainty_us': _record(0, 'res', 'timestamp_uncertainty_us'),
                     'record_kind': {'literal': _kind, 'semantic_type': 'asserted_record_kind'}}


def _joined(form, slots, relation):
    _FIELDS[form] = {name: _record(index, slot, name) for name, index, slot in slots}
    _FIELDS[form][relation] = _assertion(relation)


_joined('before', [('earlier_recorded_time_us', 0, 't'), ('later_recorded_time_us', 1, 't')], 'precedes_beyond_uncertainty')
_joined('deviceHolds', [('device_serial', 0, 'obj'), ('volume', 1, 'aux'), ('connected_time_us', 0, 't')], 'same_device_holds_volume')
_joined('usbMountedAs', [('device_serial', 0, 'obj'), ('volume', 1, 'aux'), ('connected_time_us', 0, 't')], 'same_device_mounted_volume')
_joined('openedFromMount', [('path', 0, 'obj'), ('volume', 1, 'aux'), ('opened_time_us', 0, 't')], 'opened_from_mounted_volume')
_joined('openedFromDevice', [('path', 0, 'obj'), ('volume', 0, 'aux'), ('device_serial', 1, 'obj'), ('opened_time_us', 0, 't')], 'opened_from_device_volume')
_joined('openedFromRecorded', [('path', 0, 'obj'), ('volume', 0, 'aux'), ('volume_label', 1, 'obj'), ('opened_time_us', 0, 't')], 'same_recorded_volume')
# Legacy field keys remain stable, but their public roles describe only the
# shortcut/DestList target association established by these joins.
for _form, _relation, _meaning in (
        ('openedFromMount', 'opened_from_mounted_volume', 'shortcut_target_associated_with_mounted_volume'),
        ('openedFromDevice', 'opened_from_device_volume', 'shortcut_target_associated_with_device_volume'),
        ('openedFromRecorded', 'same_recorded_volume', 'shortcut_target_associated_with_recorded_volume')):
    _FIELDS[_form]['opened_time_us']['semantic_type'] = 'recorded_timestamp_not_action_or_execution_guarantee_us'
    _FIELDS[_form]['opened_time_us']['meaning'] = (
        'Timestamp retained by the shortcut/DestList target record; does not establish actual file opening or its time.')
    _FIELDS[_form][_relation]['semantic_type'] = _meaning
    _FIELDS[_form][_relation]['meaning'] = (
        'Shortcut/DestList target and volume association through the declared join; does not establish actual file opening.')

_joined('recordedOnDevice', [('volume', 0, 'aux'), ('volume_label', 0, 'obj'), ('device_serial', 1, 'obj')], 'same_device_volume')
_joined('sameLabel', [('first_volume', 0, 'aux'), ('second_volume', 1, 'aux'), ('label', 0, 'obj')], 'same_recorded_label_not_device_identity')
_joined('copiedHere', [('path', 0, 'obj'), ('volume_or_recovery_area', 0, 'aux'), ('creation_time_us', 0, 't'), ('modification_time_us', 1, 't')], 'likely_copied_heuristic')
_joined('deletedAfter', [('path', 0, 'obj'), ('deletion_recorded_time_us', 0, 't'), ('earlier_recorded_time_us', 1, 't')], 'deletion_record_after_other_record')
_joined('deviceExamined', [('device_serial', 0, 'obj'), ('connected_time_us', 0, 't')], 'same_device_has_unallocated_entries')
# USBSTOR key last-write timestamps do not establish connection onset.
for _form in ('deviceHolds', 'usbMountedAs', 'deviceExamined'):
    _FIELDS[_form]['connected_time_us']['semantic_type'] = 'recorded_timestamp_not_action_or_execution_guarantee_us'
    _FIELDS[_form]['connected_time_us']['meaning'] = (
        'Timestamp retained by the USB record (including USBSTOR key last-write); does not establish connection onset.')
_FIELDS['usbMountedAs']['same_device_mounted_volume']['semantic_type'] = 'same_recorded_device_volume_mapping'
_FIELDS['usbMountedAs']['same_device_mounted_volume']['meaning'] = (
    'USB record and volume mapping share the declared device serial; does not establish an actual mount event or time.')

_joined('recoveredOnDevice', [('path', 0, 'obj'), ('device_serial', 1, 'obj'), ('creation_time_us', 0, 't')], 'entry_recovered_from_device')
_joined('sameContent', [('first_path', 0, 'obj'), ('second_path', 1, 'obj'), ('sha256', 0, 'aux')], 'same_recorded_content_hash')
_joined('createdAfterVolumeRecord', [('path', 0, 'obj'), ('volume', 0, 'aux'), ('disc', 1, 'obj'), ('creation_time_us', 0, 't'), ('volume_recorded_time_us', 1, 't')], 'creation_timestamp_after_volume_record')
_joined('sameJournalFile', [('first_name_or_path', 0, 'obj'), ('second_name_or_path', 1, 'obj'), ('scoped_identity', 0, 'aux')], 'same_scoped_file_identity')
_joined('removedFilePreviouslyNamed', [('earlier_name_or_path', 0, 'obj'), ('removal_name_or_path', 1, 'obj'), ('scoped_identity', 1, 'aux'), ('removal_observed_time_us', 1, 't')], 'same_identity_later_removal_flag')
_joined('journalChildNamedDirectory', [('child_name_or_path', 0, 'obj'), ('child_identity', 0, 'aux'), ('parent_identity', 1, 'aux'), ('directory_name_or_path', 2, 'obj')], 'observations_join_through_scoped_parent_identity')
_joined('journalPathForFile', [('name_or_path', 0, 'obj'), ('path_or_incomplete_suffix', 1, 'obj'), ('scoped_identity', 0, 'aux')], 'same_scoped_path_observation_identity')
_FIELDS['tagged'] = {'entity': {'argument': 0, 'slot_argument': 1, 'semantic_type': 'tagged_entity'},
                     'tag': _argument(3, 'asserted_tag', True), 'tag_id': _argument(3, 'asserted_tag_entity_id')}
for _form in claims.CENSUS:
    _FIELDS[_form] = {'kind': _argument(0, 'counted_record_kind'), 'count': _argument(-1, 'asserted_extracted_record_count')}
    if _form != 'exactly':
        _FIELDS[_form]['slot'] = _argument(1, 'counted_record_slot')
    if _form == 'exactlyWith':
        _FIELDS[_form]['value'] = _argument(2, 'asserted_count_selector', True)

_FIELDS['filesystemSetDeleted'] = {
    'declared_set': _record(0, 'obj', 'declared_filesystem_set_identity'),
    'definition': _record(0, 'aux', 'declared_filesystem_set_extraction_definition'),
    'count': _argument(1, 'asserted_declared_filesystem_set_count'),
    'all_deleted': _argument(2, 'asserted_all_members_deleted_in_declared_filesystem_set'),
}

_FIELDS['attributeRecorded'] = {
    'subject': _record(0, 'aux', 'scoped_source_subject'),
    'role': _argument(3, 'asserted_attribute_role'),
    'algorithm': dict(_argument(3, 'asserted_digest_algorithm'), role_digest_algorithm=True,
                      allowed_roles=[name for name, role in ROLES.items() if role.digest_algorithm]),
    'value': dict(_record(2, 'aux', 'recorded_typed_attribute_value'), value_role_argument=3),
    'examined_at_us': _record(0, 't', 'examination_timestamp_not_event_time_us'),
}
for _form in ('attributesSameSubject', 'attributeValuesAgree'):
    _FIELDS[_form] = {
        'subject': _record(0, 'aux', 'scoped_source_subject'),
        'first_role': _argument(3, 'asserted_attribute_role'),
        'second_role': _argument(7, 'asserted_attribute_role'),
        'first_value': dict(_record(2, 'aux', 'recorded_typed_attribute_value'), value_role_argument=3),
        'second_value': dict(_record(6, 'aux', 'recorded_typed_attribute_value'), value_role_argument=7),
        'same_source_subject': _assertion('same_scoped_source_subject_not_personal_identity'),
    }
_FIELDS['attributeValuesAgree']['values_agree'] = _assertion('same_typed_recorded_values')
_FIELDS['imageDigestsAgree'] = {
    'subject': _record(0, 'aux', 'scoped_logical_image_subject'),
    'algorithm': _argument(6, 'asserted_digest_algorithm'),
    'logical_digest': dict(_record(2, 'aux', 'recomputed_logical_image_digest'), value_type='string'),
    'acquisition_digest': dict(_record(5, 'aux', 'retained_acquisition_digest'), value_type='string'),
    'digests_match': _assertion('same_algorithm_same_subject_digest_equality_not_authenticity'),
}
_FIELDS['attributeTuple'] = {
    'subject': dict(_record(0, 'aux', 'scoped_source_subject'), tuple_entry=0),
    'same_source_subject': _assertion('same_scoped_source_subject_not_personal_identity'),
}
for _index in range(8):
    _FIELDS['attributeTuple']['role_' + str(_index)] = dict(
        _argument(3, 'asserted_attribute_role'), tuple_entry=_index)
    _FIELDS['attributeTuple']['value_' + str(_index)] = dict(
        _record(2, 'aux', 'recorded_typed_attribute_value'),
        tuple_entry=_index, value_role_argument=3)
for _fields in _FIELDS.values():
    for _selector in _fields.values():
        if 'value_role_argument' in _selector:
            _selector['allowed_semantic_types'] = [role.semantic_type for role in ROLES.values()]


def catalog():
    """Public field schema only: no evidence queries, private reference or grading."""
    return {'schema_version': VERSION, 'forms': deepcopy(_FIELDS), 'formats': sorted(FORMATS),
            'attribute_roles': roles_catalog(),
            'part': 'zero-based index into flattened claim parts; a whole conjunction is one filter dependency',
            'example': {'candidate_id': 'A001', 'claim_sha256': '<hash of exact claim>', 'question_id': 'Q1',
                        'path': ['devices', 0, 'serial'], 'part': 0, 'field': 'device_serial'},
            'scope': SCOPE}


def tool_catalog():
    """Compact, self-contained tool view; the full internal catalog is unchanged."""
    result = catalog()
    shared_types = [role['semantic_type'] for role in result['attribute_roles'].values()]
    for fields in result['forms'].values():
        for selector in fields.values():
            if ('value_role_argument' in selector
                    and selector.get('allowed_semantic_types') == shared_types):
                del selector['allowed_semantic_types']
                selector['allowed_semantic_types_ref'] = '#/attribute_roles'
    result['view'] = 'compact_tool_catalog'
    result['attribute_type_lookup'] = (
        'For a selector with value_role_argument, take that indexed argument from the '
        'atomic claim. If tuple_entry is present, first select that zero-based tuple '
        'entry. The argument is an exact approved role key in attribute_roles; its '
        'semantic_type and value_type define the selected value. '
        'allowed_semantic_types_ref points to the shared attribute_roles map: its '
        'semantic_type values are the allowed types, not a type chosen by the model. '
        'All forms, selectors, role restrictions, formats and native types remain available.')
    return result


def _literal_parts(claim):
    """Parse shapes only; checker-only restrictions must not filter A's meaning.

    In particular, a sameContent claim citing one ID twice still asserts equal
    content, even though the checker refuses it. Whole-candidate refusal remains
    the gate's job. This parser neither checks records nor calls claims.parse.
    """
    pending, parts, count = [claim], [], 0
    while pending:
        node = pending.pop()
        count += 1
        if count > 2048:
            raise ValueError('projection_claim_shape_limit')
        if not isinstance(node, dict) or len(node) != 1:
            raise ValueError('claim_must_have_one_form')
        form, args = next(iter(node.items()))
        if form == 'both':
            if not isinstance(args, list) or len(args) < 2:
                raise ValueError('both_requires_at_least_two_claims')
            pending.extend(reversed(args))
            continue
        if form == 'attributeTuple':
            if not isinstance(args, list) or not 2 <= len(args) <= 8:
                raise ValueError('attribute_tuple_requires_two_to_eight_entries')
            if any(not isinstance(entry, list) or len(entry) != 4
                   or any(type(fid) is not int or fid < 0 for fid in entry[:3])
                   or not isinstance(entry[3], str) or entry[3] not in ROLES
                   for entry in args):
                raise ValueError('attribute_tuple_entry_shape_mismatch')
            # Kind, same-subject and unique-role conditions belong to the
            # checker. A retains the exact semantics of invalid proposals so
            # B can refuse them without repairing their frozen projection.
            parts.append((form, tuple(tuple(entry) for entry in args)))
            continue
        if form not in claims.SETS:
            raise ValueError('unrecognized_claim_form')
        params = claims.SETS[form].params
        if not isinstance(args, list) or len(args) != len(params):
            raise ValueError('claim_argument_shape_mismatch')
        for param, value in zip(params, args):
            valid = (isinstance(value, str) and value in ('obj', 'aux') if param == 'slot' else
                     isinstance(value, str) and value in KINDS if param == 'kind' else
                     isinstance(value, str) and value in ROLES if param == 'role' else
                     isinstance(value, str) and value in DIGEST_ALGORITHMS if param == 'algorithm' else
                     type(value) is bool if param == 'boolean' else
                     type(value) is int and value >= 0)
            if not valid:
                raise ValueError('claim_argument_type_mismatch')
        parts.append((form, tuple(args)))
    return parts


def claim_fields(claim, source):
    """Dereference declared argument roles only; never test kind, equality or order."""
    output = {'claim_sha256': claim_digest(claim), 'parts': [], 'unsupported': []}
    try:
        parts = _literal_parts(claim)
    except (ValueError, TypeError, RecursionError) as error:
        output['unsupported'].append({'reason': 'unsupported_or_malformed_claim', 'detail': str(error)})
        return output
    # Set support resolves only the exact declared membership. It never checks
    # or replaces the proposed count or Boolean, including invalid proposals.
    support = [claims.filesystem_set_support_ids(part[1][0], source)
               if part[0] == 'filesystemSetDeleted' else claims.fact_ids(part)
               for part in parts]
    ids = list(dict.fromkeys(fid for group in support for fid in group))
    found = source.get(ids)  # Legacy censuses still read only their asserted n.
    for index, part in enumerate(parts):
        form, args = part
        row = {'part': index, 'form': form, 'fields': {}, 'unsupported': []}
        for name, selector in _FIELDS.get(form, {}).items():
            try:
                value_ids = []
                if 'tuple_entry' in selector and selector['tuple_entry'] >= len(args):
                    raise ValueError('attribute_tuple_entry_missing')
                field_args = args[selector['tuple_entry']] if 'tuple_entry' in selector else args
                if 'literal' in selector:
                    value = selector['literal']
                elif 'literal_argument' in selector:
                    value = field_args[selector['literal_argument']]
                    if selector.get('decode_entity'):
                        value = source.string(value)
                    if selector.get('role_digest_algorithm'):
                        value = ROLES[value].digest_algorithm
                        if value is None:
                            raise ValueError('declared_role_has_no_digest_algorithm')
                else:
                    fid = field_args[selector['argument']]
                    fact = found.get(fid)
                    if fact is None:
                        raise ValueError('cited_record_missing')
                    value_ids.append(fid)
                    slot = field_args[selector['slot_argument']] if 'slot_argument' in selector else selector['slot']
                    value = getattr(fact, slot)
                    if slot in ('obj', 'aux'):
                        value = source.string(value)
                semantic_type = selector['semantic_type']
                if 'value_role_argument' in selector:
                    spec = ROLES[field_args[selector['value_role_argument']]]
                    value = decode_value(value, spec.value_type)
                    semantic_type = spec.semantic_type
                elif 'value_type' in selector:
                    value = decode_value(value, selector['value_type'])
                _finite(value)
                row['fields'][name] = {'value': value, 'selector': deepcopy(selector),
                    'semantic_type': semantic_type, 'record_ids': list(support[index]),
                    'value_record_ids': value_ids}
            except (ValueError, KeyError, IndexError, AttributeError) as error:
                row['unsupported'].append({'field': name, 'reason': str(error)})
        output['parts'].append(row)
    output['records'] = [{'id': fid, 'row_sha256': fact.row_sha256(),
                          'obj': fact.obj, 'obj_text': source.string(fact.obj),
                          'aux': fact.aux, 'aux_text': source.string(fact.aux)}
                         for fid, fact in sorted(found.items())]
    output['missing_record_ids'] = [fid for fid in ids if fid not in found]
    return output


def _public(public):
    allowed = {'schema_version', 'case_id', 'title', 'time_zone', 'instructions', 'questions', 'contract_revision'}
    if (not isinstance(public, dict) or public.get('schema_version') != 2 or set(public) - allowed
            or not isinstance(public.get('case_id'), str) or not public['case_id']
            or not isinstance(public.get('questions'), list)):
        raise ValueError('provide a public schema-v2 question contract without private fields')
    result = {}
    for question in public['questions']:
        if (not isinstance(question, dict) or set(question) - {'id', 'prompt', 'answer_schema', 'match'}
                or not isinstance(question.get('id'), str) or not question['id'] or question['id'] in result
                or not isinstance(question.get('answer_schema'), dict)):
            raise ValueError('public questions need unique IDs and explicit answer schemas')
        result[question['id']] = question
    return result


def _path(path):
    if not isinstance(path, list) or len(path) > 16 or any(
            not (type(token) is str and 0 < len(token) <= 200 or type(token) is int and 0 <= token <= 100000)
            for token in path):
        raise ValueError('path must have at most 16 object keys or nonnegative array indexes')
    return path


def _schema(schema, path):
    """Collect common-path leaf constraints without choosing an anyOf branch.

    This deliberately uses the intersection of branch path/type support, not
    general JSON Schema validation. A branch must explicitly declare the path;
    permissive additionalProperties cannot supply a branch-exclusive field.
    Required fields, enum values and other grading constraints remain outside
    this partial-field projector, as they are for schemas without alternatives.
    """
    pending, leaves, visited = [(schema, 0, 0, False)], [], 0
    while pending:
        schema, position, depth, common_path = pending.pop()
        visited += 1
        if visited > MAX_SCHEMA_NODES or depth > MAX_SCHEMA_DEPTH:
            raise ValueError('public_schema_traversal_limit')
        if not isinstance(schema, dict):
            raise ValueError('unsupported_public_schema_node')
        if answer_requirements.KEY in schema and position != len(path):
            raise ValueError('claim_requirement_must_annotate_exact_answer_value')
        if any(k in schema for k in ('$ref', '$dynamicRef', '$recursiveRef', 'oneOf', 'allOf')):
            raise ValueError('unsupported_schema_reference_or_union')
        if 'anyOf' in schema:
            alternatives = schema['anyOf']
            if (not isinstance(alternatives, list) or not alternatives
                    or len(alternatives) > MAX_SCHEMA_ALTERNATIVES):
                raise ValueError('unsupported_public_schema_anyof')
            # Sibling constraints still apply to every branch. They need not
            # redeclare the branch's paths, but cannot prohibit those paths.
            siblings = {key: value for key, value in schema.items() if key != 'anyOf'}
            pending.extend((branch, position, depth + 1, True) for branch in reversed(alternatives))
            if siblings:
                pending.append((siblings, position, depth + 1, False))
            continue
        if position == len(path):
            leaves.append(schema)
            continue
        token = path[position]
        kind = schema.get('type')
        allowed = kind if isinstance(kind, list) else [kind] if kind else []
        if type(token) is int:
            if allowed and 'array' not in allowed:
                raise ValueError('array_path_does_not_match_public_schema')
            if common_path and 'items' not in schema:
                raise ValueError('path_not_common_to_public_schema_anyof')
            child = schema.get('items', {})
        else:
            if allowed and 'object' not in allowed:
                raise ValueError('object_path_does_not_match_public_schema')
            properties = schema.get('properties', {})
            if not isinstance(properties, dict):
                raise ValueError('unsupported_public_schema_node')
            if token in properties:
                child = properties[token]
            elif common_path:
                raise ValueError('path_not_common_to_public_schema_anyof')
            elif schema.get('additionalProperties') is False:
                raise ValueError('field_not_in_public_schema')
            else:
                child = schema.get('additionalProperties', {})
                if child is True:
                    child = {}
        pending.append((child, position + 1, depth + 1, common_path))
    return leaves


def _strict_schema(schema, path):
    """Keep conjunctive constraints separate; require meaning in every alternative.

    No schema keyword is an internal marker. A branch cannot overwrite sibling
    constraints or their annotations, including additionalProperties and items.
    """
    pending, leaves, visited = [([schema], 0, 0)], [], 0
    while pending:
        nodes, position, depth = pending.pop()
        visited += len(nodes)
        if visited > MAX_SCHEMA_NODES or depth > MAX_SCHEMA_DEPTH:
            raise ValueError('public_schema_traversal_limit')
        expanded = False
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                raise ValueError('unsupported_public_schema_node')
            if any(k in node for k in ('$ref', '$dynamicRef', '$recursiveRef', 'oneOf', 'allOf')):
                raise ValueError('unsupported_schema_reference_or_union')
            if answer_requirements.KEY in node and position != len(path):
                raise ValueError('claim_requirement_must_annotate_exact_answer_value')
            if 'anyOf' in node:
                branches = node['anyOf']
                if not isinstance(branches, list) or not 1 <= len(branches) <= MAX_SCHEMA_ALTERNATIVES:
                    raise ValueError('unsupported_public_schema_anyof')
                siblings = {key: value for key, value in node.items() if key != 'anyOf'}
                for branch in reversed(branches):
                    pending.append((nodes[:index] + [siblings, branch] + nodes[index + 1:], position, depth + 1))
                expanded = True
                break
        if expanded:
            continue
        if position == len(path):
            for node in nodes:
                kind = node.get('type')
                if any(k in node for k in ('properties', 'items', 'additionalProperties', 'prefixItems')) or kind in ('object', 'array'):
                    raise ValueError('claim_requirement_must_annotate_exact_answer_value')
            if not any(answer_requirements.KEY in node for node in nodes):
                raise ValueError('missing_public_claim_requirement')
            leaves.extend(nodes)
            continue
        children = []
        for node in nodes:
            children.extend(_schema(node, [path[position]]))
        pending.append((children, position + 1, depth + 1))
    return leaves


def _typed(value, schema):
    if '$ref' in schema or any(k in schema for k in ('oneOf', 'anyOf', 'allOf')):
        raise ValueError('unsupported_schema_reference_or_union')
    kind = schema.get('type')
    allowed = kind if isinstance(kind, list) else [kind] if kind else []
    actual = ('null' if value is None else 'boolean' if type(value) is bool else 'integer' if type(value) is int
              else 'number' if type(value) is float else 'string' if type(value) is str
              else 'array' if type(value) is list else 'object')
    if allowed and actual not in allowed and not (actual == 'integer' and 'number' in allowed):
        raise ValueError('value_type_does_not_match_public_schema')


def _declared_choices(value, schema):
    """Enforce exact public literal choices without changing a proposed value."""
    if 'enum' in schema:
        options = schema['enum']
        if not isinstance(options, list) or not 1 <= len(options) <= 256:
            raise ValueError('invalid_public_schema_enum')
        if _encoded(value) not in [_encoded(option) for option in options]:
            raise ValueError('value_not_in_public_schema_enum')
    if 'const' in schema and _encoded(value) != _encoded(schema['const']):
        raise ValueError('value_does_not_match_public_schema_const')


def _format(value, format_name, zone, semantic_type):
    if format_name not in FORMATS:
        raise ValueError('unsupported_format')
    if format_name == 'identity':
        return value
    if semantic_type.startswith('recorded_attribute_') and not (
            format_name == 'integer' and semantic_type.endswith('_integer') and type(value) is int):
        raise ValueError('typed_attribute_format_cannot_change_its_declared_native_type')
    if format_name == 'integer':
        if type(value) is int:
            return value
        if not isinstance(value, str) or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)', value):
            raise ValueError('integer_format_requires_an_exact_decimal_literal')
        return int(value)
    if type(value) is not int or not semantic_type.endswith('_us') or 'uncertainty' in semantic_type:
        raise ValueError('time_format_requires_a_recorded_timestamp_field')
    try:
        stamp = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=value)
        if format_name == 'utc_iso':
            return stamp.isoformat().replace('+00:00', 'Z')
        if not isinstance(zone, str):
            raise ValueError('local_time_format_requires_public_timezone')
        local = stamp.astimezone(ZoneInfo(zone))
        return local.strftime('%Y-%m-%d %H:%M' if format_name == 'local_minute' else '%Y-%m-%d')
    except (OverflowError, KeyError) as error:
        raise ValueError('timestamp_or_public_timezone_is_not_displayable') from error


def _row_paths(requirements, path):
    """Instantiate object row paths without confusing different array rows."""
    output = []
    for row in requirements:
        pattern = row['path']
        if len(pattern) >= len(path):
            continue
        for expected, actual in zip(pattern, path):
            if expected == '*' and type(actual) is int:
                continue
            if isinstance(expected, dict) and expected.get('additional_property') is True:
                if type(actual) is str and actual not in expected.get('excluded_properties', []):
                    continue
            if expected != actual:
                break
        else:
            concrete = path[:len(pattern)]
            if concrete not in output:
                output.append(concrete)
    return output


def prepare_projection(public, candidates, bindings, source, *, require_claim_requirements=False, require_evidence_scope=False, evidence_facts_sha256=None):
    """Freeze literal values once; no candidate is accepted/refused by this function."""
    if type(require_claim_requirements) is not bool:
        raise ValueError('require_claim_requirements must be a boolean')
    if type(require_evidence_scope) is not bool:
        raise ValueError('require_evidence_scope must be a boolean')
    if evidence_facts_sha256 is not None and not answer_requirements.valid_facts_digest(evidence_facts_sha256):
        raise ValueError('invalid_evidence_facts_sha256')
    questions = _public(public)
    if answer_references.validate_public(public)['errors']:
        raise ValueError('invalid_public_claim_references')
    if not isinstance(candidates, list) or not isinstance(bindings, list) or len(bindings) > 20000:
        raise ValueError('candidates and at most 20000 bindings must be lists')
    _finite(candidates)
    _finite(bindings)
    indexed = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError('candidate must be an object')
        cid = candidate.get('candidate_id', candidate.get('finding_id'))
        if (not isinstance(cid, str) or not cid or len(cid) > 128 or cid in indexed
                or 'claim' not in candidate
                or candidate.get('candidate_id', cid) != candidate.get('finding_id', cid)):
            raise ValueError('candidate IDs must be unique and unambiguous')
        indexed[cid] = {'candidate_id': cid, 'claim': deepcopy(candidate['claim']),
                        **claim_fields(candidate['claim'], source)}
    row_policies = {qid: answer_requirements.row_requirements(question['answer_schema'], require_claim_requirements=require_claim_requirements)
                    for qid, question in questions.items()}
    scope_policies = {qid: answer_requirements.scope_requirements(question['answer_schema'], require_evidence_scope=require_evidence_scope)
                      for qid, question in questions.items()}
    prepared, unsupported = [], []
    for index, raw in enumerate(bindings):
        entry = {'binding_index': index, 'binding': deepcopy(raw)}
        try:
            if (not isinstance(raw, dict) or set(raw) - {'candidate_id', 'claim_sha256', 'question_id', 'path', 'part', 'field', 'format', 'value'}):
                raise ValueError('invalid_binding_fields')
            cid, qid = raw.get('candidate_id'), raw.get('question_id')
            if not isinstance(cid, str) or cid not in indexed:
                raise ValueError('candidate_not_found')
            candidate = indexed[cid]
            if raw.get('claim_sha256') != candidate['claim_sha256']:
                raise ValueError('claim_hash_mismatch')
            if not isinstance(qid, str) or qid not in questions:
                raise ValueError('question_not_in_public_contract')
            path = _path(raw.get('path'))
            policies, policy_errors = row_policies[qid]
            for error in policy_errors:
                if error['reason'] != 'missing_public_claim_row_requirement' or _row_paths([error], path):
                    raise ValueError(error['reason'])
            row_paths = _row_paths([policy for policy in policies if policy['mode'] == 'same_claim_part'], path)
            part = raw.get('part', 0)
            if type(part) is not int or not 0 <= part < len(candidate['parts']):
                raise ValueError('claim_part_unavailable')
            part_row = candidate['parts'][part]
            field = part_row['fields'].get(raw.get('field'))
            if field is None:
                raise ValueError('field_not_supported_or_cited_record_missing')
            scope_rows, scope_errors = scope_policies[qid]
            for error in scope_errors:
                if error['reason'] != 'missing_public_claim_scope_requirement':
                    raise ValueError(error['reason'])
            if require_evidence_scope or scope_rows:
                scopes = answer_requirements.applicable_scopes(questions[qid]['answer_schema'], path,
                                                               require_evidence_scope=require_evidence_scope)
                for scope in sorted(scopes, key=lambda item: item['mode'] != 'unavailable'):
                    scope_check = {'requirement': deepcopy(scope), 'status': 'compatible',
                                   'record_ids': list(field['record_ids']),
                                   'scope': 'Declared evidence origin compatibility; question relevance and completeness are not established.'}
                    entry.setdefault('scope_checks', []).append(scope_check)
                    if scope['mode'] == 'unavailable':
                        scope_check['status'] = 'unavailable'
                        raise ValueError('public_claim_scope_unavailable')
                    if scope['mode'] == 'unscoped_observation':
                        continue
                    if evidence_facts_sha256 is None:
                        scope_check['status'] = 'incompatible'
                        raise ValueError('evidence_facts_sha256_required')
                    if scope.get('evidence_facts_sha256', evidence_facts_sha256) != evidence_facts_sha256:
                        scope_check['status'] = 'incompatible'
                        raise ValueError('evidence_facts_sha256_mismatch')
                    ids = field['record_ids']
                    records = source.get(ids)
                    if not ids or any(fid not in records for fid in ids):
                        scope_check['status'] = 'incompatible'
                        raise ValueError('claim_scope_supporting_records_missing')
                    origins = [{key: (records[fid].prov if isinstance(records[fid].prov, dict) else {}).get(key) for key in answer_requirements.ORIGIN_KEYS}
                               for fid in ids]
                    for fid, origin in zip(ids, origins):
                        if origin['source_snapshot'] == 'examination':
                            origin['input_source'] = deepcopy((records[fid].prov if isinstance(records[fid].prov, dict) else {}).get('input_source'))
                    scope_check['record_origins'] = origins
                    if any(origin not in scope['origins'] for origin in origins):
                        scope_check['status'] = 'incompatible'
                        raise ValueError('claim_records_do_not_meet_public_scope')
                    if scope.get('same_origin') and any(origin != origins[0] for origin in origins[1:]):
                        scope_check['status'] = 'incompatible'
                        raise ValueError('claim_supporting_records_have_mixed_origins')
            value = _format(field['value'], raw.get('format', 'identity'), public.get('time_zone'), field['semantic_type'])
            if 'value' in raw and _encoded(raw['value']) != _encoded(value):
                raise ValueError('literal_value_mismatch_not_repaired')
            for schema in (_strict_schema if require_claim_requirements else _schema)(questions[qid]['answer_schema'], path):
                _typed(value, schema)
                if require_claim_requirements:
                    _declared_choices(value, schema)
                if answer_requirements.KEY in schema:
                    meaning = answer_requirements.check(schema[answer_requirements.KEY], part_row['form'],
                                                        raw['field'], field['semantic_type'], part_fields=part_row['fields'])
                    entry.setdefault('meaning_checks', []).append(meaning)
                    if meaning['status'] != 'compatible':
                        raise ValueError(meaning.get('reason', 'claim_role_does_not_meet_public_requirement'))
                if answer_references.KEY in schema:
                    reference = answer_references.parse(schema[answer_references.KEY])
                    if reference not in entry.setdefault('answer_references', []):
                        entry['answer_references'].append(reference)
            entry.update(candidate_id=cid, claim_sha256=candidate['claim_sha256'], question_id=qid,
                         path=deepcopy(path), part=part, form=part_row['form'], field=raw['field'],
                         semantic_type=field['semantic_type'], value=value, record_ids=field['record_ids'],
                         value_record_ids=field['value_record_ids'], selector=field['selector'])
            if row_paths:
                entry['row_paths'] = deepcopy(row_paths)
            prepared.append(entry)
        except (ValueError, TypeError, KeyError) as error:
            entry['reason'] = str(error)
            unsupported.append(entry)
    plan = {'schema_version': VERSION, 'kind': 'frozen_claim_field_projection', 'case_id': public['case_id'],
            'require_claim_requirements': require_claim_requirements,
            'require_evidence_scope': require_evidence_scope, 'evidence_facts_sha256': evidence_facts_sha256,
            'public_sha256': claim_digest(public), 'questions': [q['id'] for q in public['questions']],
            'candidates': indexed, 'bindings': prepared, 'unsupported': unsupported, 'scope': SCOPE}
    # Freeze omissions before any gate filtering. Removing a rejected candidate
    # must not reveal a conflicting value that was absent from A's answer. The
    # product can correct a collision by explicitly replacing its bindings.
    grouped = defaultdict(list)
    for entry in prepared:
        grouped[entry['question_id']].append(entry)
    plan['frozen_conflicts'] = [dict(conflict, question_id=qid)
        for qid in plan['questions'] for conflict in _assemble(grouped[qid])[3]]
    row_groups = defaultdict(list)
    for entry in prepared:
        for row_path in entry.get('row_paths', []):
            row_groups[(entry['question_id'], tuple(row_path))].append(entry)
    for (qid, row_path), entries in row_groups.items():
        if len({(entry['candidate_id'], entry['part']) for entry in entries}) > 1:
            plan['frozen_conflicts'].append({
                'reason': 'row_fields_require_same_claim_part', 'question_id': qid,
                'path': list(row_path), 'binding_indices': [entry['binding_index'] for entry in entries]})
    answer_references.freeze_references(plan)
    plan['conflict_policy'] = 'omit_all_conflicting_bindings_before_candidate_filtering'
    plan['projection_sha256'] = claim_digest(plan)
    return plan


def _assemble(entries):
    """Omit conflicts; compact arrays without inventing null values for absent rows."""
    tree = {'leaves': [], 'children': {}}
    for entry in entries:
        node = tree
        for token in entry['path']:
            node = node['children'].setdefault(token, {'leaves': [], 'children': {}})
        node['leaves'].append(entry)
    conflicts, leaves = [], []
    absent = object()
    def descendants(node):
        return node['leaves'] + [entry for child in node['children'].values() for entry in descendants(child)]
    def visit(node, output_path):
        records, children = node['leaves'], node['children']
        reason = ('ancestor_and_descendant_bindings_conflict' if records and children else
                  'object_and_array_paths_conflict' if len({type(token) for token in children}) > 1 else
                  'different_values_at_same_path' if len({_encoded(e['value']) for e in records}) > 1 else None)
        if reason:
            conflicts.append({'reason': reason, 'binding_indices': [e['binding_index'] for e in descendants(node)]})
            return absent
        if records:
            for entry in records:
                leaves.append(dict(entry, output_path=deepcopy(output_path)))
            return deepcopy(records[0]['value'])
        if not children:
            return absent
        array = type(next(iter(children))) is int
        value = [] if array else {}
        for token in sorted(children):
            next_token = len(value) if array else token
            child = visit(children[token], output_path + [next_token])
            if child is not absent:
                if array:
                    value.append(child)
                else:
                    value[token] = child
        return value if value else absent
    value = visit(tree, [])
    return value is not absent, None if value is absent else value, leaves, conflicts


def render_projection(plan, admitted_ids=None, authority='unchecked'):
    """Filter whole candidate dependencies and render frozen values without source access."""
    if authority not in AUTHORITIES:
        raise ValueError('unsupported authority label')
    if (not isinstance(plan, dict) or plan.get('schema_version') != VERSION
            or plan.get('kind') != 'frozen_claim_field_projection'
            or plan.get('projection_sha256') != claim_digest({k: v for k, v in plan.items() if k != 'projection_sha256'})):
        raise ValueError('projection content or digest changed')
    if admitted_ids is not None:
        if not isinstance(admitted_ids, (list, tuple, set)) or any(not isinstance(cid, str) for cid in admitted_ids):
            raise ValueError('admitted_ids must contain candidate IDs')
        admitted = set(admitted_ids)
        if admitted - plan['candidates'].keys():
            raise ValueError('admitted candidate was not in the frozen projection')
    else:
        admitted = set(plan['candidates'])
    frozen_conflicts = plan.get('frozen_conflicts', [])
    omitted = {index for collision in frozen_conflicts for index in collision['binding_indices']}
    grouped = defaultdict(list)
    dropped = []
    for entry in plan['bindings']:
        if entry['binding_index'] in omitted:
            dropped.append(dict(entry, reason='frozen_projection_conflict',
                                candidate_admitted=entry['candidate_id'] in admitted))
        elif entry['candidate_id'] not in admitted:
            dropped.append(dict(entry, reason='whole_candidate_not_admitted'))
        else:
            grouped[entry['question_id']].append(entry)
    answers, leaves, conflicts = [], [], deepcopy(frozen_conflicts)
    for qid in plan['questions']:
        present, value, used, collisions = _assemble(grouped[qid])
        answers.append({'question_id': qid, 'status': 'answered', 'answer': value} if present else
                       {'question_id': qid, 'status': 'unknown', 'reason': 'No unambiguous supported projection was retained.'})
        leaves.extend(dict(entry, authority=authority) for entry in used)
        conflicts.extend(dict(collision, question_id=qid) for collision in collisions)
    bound = {entry['candidate_id'] for entry in plan['bindings']}
    return {'schema_version': VERSION, 'projection_sha256': plan['projection_sha256'], 'authority': authority,
            'submission': {'schema_version': 2, 'case_id': plan['case_id'], 'answers': answers},
            'leaves': leaves, 'unsupported': deepcopy(plan['unsupported']), 'dropped': dropped, 'conflicts': conflicts,
            'unbound_candidate_ids': [cid for cid in plan['candidates'] if cid not in bound],
            'certification': 'not_performed_by_projector', 'question_completeness': 'not_established', 'scope': SCOPE}


def project_answers(public, candidates, bindings, source, admitted_ids=None, authority='unchecked', *, require_claim_requirements=False, require_evidence_scope=False, evidence_facts_sha256=None):
    plan = prepare_projection(public, candidates, bindings, source, require_claim_requirements=require_claim_requirements,
                              require_evidence_scope=require_evidence_scope, evidence_facts_sha256=evidence_facts_sha256)
    return dict(render_projection(plan, admitted_ids=admitted_ids, authority=authority), projection=plan)
