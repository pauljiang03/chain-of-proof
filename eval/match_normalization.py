"""Opt-in, versioned representation parsers; never infer answer meaning or source."""
from copy import deepcopy
import ntpath
import re

PROFILE_ID = 'typed-representation-v1'
VERSION = 1
KINDS = frozenset(('guid-v1', 'zone-label-offset-v1', 'windows-volume-path-v1'))
_HEX64 = re.compile(r'[0-9a-f]{64}')
_ORIGIN = ('image', 'exhibit', 'source_snapshot', 'source_variant')
_OFFSET = r'(?:(?:UTC|GMT) ?[+-][0-9]{1,2}:[0-9]{2}|[+-](?:[0-9]{2}:[0-9]{2}|[0-9]{4}))'


def _fail(reason):
    raise ValueError(reason)


def _string(value, maximum=2000):
    if type(value) is not str or not 0 < len(value) <= maximum or not value.strip():
        return False
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        return False
    return not any(ord(c) < 32 or ord(c) == 127 for c in value)


def _digest(value):
    return type(value) is str and _HEX64.fullmatch(value) is not None


def _origin(raw):
    keys = set(_ORIGIN) | ({'input_source'} if isinstance(raw, dict) and raw.get('source_snapshot') == 'examination' else set())
    if not isinstance(raw, dict) or set(raw) != keys or any(
            not _string(raw.get(key)) or raw[key].strip().lower() == 'unknown' or '*' in raw[key] for key in _ORIGIN):
        _fail('invalid_normalization_source_origin')
    if 'input_source' in raw:
        nested = raw['input_source']
        if not isinstance(nested, dict) or set(nested) != {'source_snapshot', 'source_variant'} or any(
                not _string(value) or value.strip().lower() == 'unknown' or '*' in value for value in nested.values()):
            _fail('invalid_normalization_source_origin')
    return tuple((key, tuple(sorted(value.items())) if isinstance(value, dict) else value) for key, value in sorted(raw.items()))


def _root(value):
    if not _string(value, 512):
        _fail('invalid_normalization_absolute_root')
    if re.fullmatch(r'[A-Za-z]:', value):
        return value.upper()
    if value.startswith('\\\\'):
        components = value[2:].split('\\')
        if len(components) == 2 and all(component and component not in ('.', '..') and
                not any(c in component for c in '/:*?"<>|') and not component.endswith((' ', '.')) for component in components):
            # UNC spelling case is ASCII-only here. Unicode casefold can
            # invent root aliases (for example sharp-s versus ss).
            return value.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))
    _fail('invalid_normalization_absolute_root')


def validate_profile(profile):
    if (not isinstance(profile, dict) or set(profile) != {'id', 'version', 'ancestor_public_sha256', 'source_contexts'}
            or profile['id'] != PROFILE_ID or type(profile['version']) is not int or profile['version'] != VERSION
            or not _digest(profile['ancestor_public_sha256'])):
        _fail('invalid_matching_normalization_profile')
    contexts = profile['source_contexts']
    if not isinstance(contexts, dict) or len(contexts) > 64:
        _fail('invalid_matching_normalization_contexts')
    for name, context in contexts.items():
        if not _string(name, 128) or not isinstance(context, dict) or set(context) != {'origin', 'volume', 'absolute_roots', 'mapping_receipt_sha256'}:
            _fail('invalid_matching_normalization_context')
        _origin(context['origin'])
        volume = context['volume']
        if not isinstance(volume, dict) or set(volume) != {'kind', 'value'} or volume['kind'] != 'ntfs-serial-64' or not isinstance(volume['value'], str) or not re.fullmatch('[0-9a-f]{16}', volume['value']):
            _fail('invalid_normalization_volume_identity')
        roots = context['absolute_roots']
        if not isinstance(roots, list) or not 1 <= len(roots) <= 32 or not _digest(context['mapping_receipt_sha256']):
            _fail('invalid_normalization_root_mapping')
        canonical = [_root(root) for root in roots]
        if len(set(canonical)) != len(canonical):
            _fail('duplicate_normalization_absolute_root')
    return deepcopy(profile)


def validate_rule(rule, *, profile=None):
    if not isinstance(rule, dict) or not isinstance(rule.get('kind'), str) or rule['kind'] not in KINDS:
        _fail('invalid_matching_normalization_rule')
    kind = rule['kind']
    if kind == 'guid-v1':
        if set(rule) != {'kind'}:
            _fail('invalid_matching_normalization_rule')
    elif kind == 'zone-label-offset-v1':
        if set(rule) - {'kind', 'label_mode'} or rule.get('label_mode', 'exact') not in ('exact', 'casefold', 'casefold_whitespace'):
            _fail('invalid_matching_normalization_rule')
    else:
        if set(rule) != {'kind', 'context', 'case_sensitive', 'allow_volume_rooted'} or type(rule['case_sensitive']) is not bool or type(rule['allow_volume_rooted']) is not bool:
            _fail('invalid_matching_normalization_rule')
        validated = validate_profile(profile)
        if not isinstance(rule['context'], str) or rule['context'] not in validated['source_contexts']:
            _fail('unknown_matching_normalization_context')
    return deepcopy(rule)


def _pointer(value):
    return isinstance(value, str) and (not value or value.startswith('/')) and len(value) <= 4096 and len(value.split('/')) <= 17 and not re.search(r'~(?![01])', value)


def validate_config(config, *, profile=None):
    validate_profile(profile)  # A new rule never silently upgrades a legacy profile.
    if not isinstance(config, dict) or set(config) != {'version', 'fields'} or type(config['version']) is not int or config['version'] != VERSION:
        _fail('invalid_matching_normalization_config')
    fields = config['fields']
    if not isinstance(fields, dict) or not 1 <= len(fields) <= 256:
        _fail('invalid_matching_normalization_fields')
    for pointer, rule in fields.items():
        if not _pointer(pointer):
            _fail('invalid_matching_normalization_pointer')
        validate_rule(rule, profile=profile)
    return deepcopy(fields)


def _guid(value):
    body = value
    if body.startswith('{') or body.endswith('}'):
        if not (body.startswith('{') and body.endswith('}')):
            _fail('invalid_guid_representation')
        body = body[1:-1]
    if not re.fullmatch(r'(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', body):
        _fail('invalid_guid_representation')
    return ('guid-v1', bytes.fromhex(body.replace('-', '')))


def _zone(value, rule):
    patterns = (rf'(.+) \(({_OFFSET})\)', rf'(.+) ({_OFFSET})', rf'\(({_OFFSET})\) (.+)')
    parsed = []
    for index, pattern in enumerate(patterns):
        match = re.fullmatch(pattern, value)
        if not match:
            continue
        label, offset = (match[2], match[1]) if index == 2 else (match[1], match[2])
        if not _string(label, 512) or label != label.strip() or re.search(_OFFSET, label):
            continue
        digits = re.fullmatch(r'(?:(?:UTC|GMT) ?)?([+-])([0-9]{1,2}):([0-9]{2})', offset)
        if digits is None:
            digits = re.fullmatch(r'([+-])([0-9]{2})([0-9]{2})', offset)
        sign, hours, minutes = digits[1], int(digits[2]), int(digits[3])
        if hours > 14 or minutes > 59 or hours == 14 and minutes or sign == '-' and hours == minutes == 0:
            continue
        total = (hours * 60 + minutes) * (-1 if sign == '-' else 1)
        if rule.get('label_mode') == 'casefold':
            label = label.casefold()
        elif rule.get('label_mode') == 'casefold_whitespace':
            label = ' '.join(label.casefold().split())
        parsed.append(('zone-label-offset-v1', label, total))
    if len(parsed) != 1:
        _fail('invalid_zone_label_offset_representation')
    return parsed[0]


def _reserved_device_component(component):
    # Microsoft reserves these names even with extensions, in every directory.
    # Also refuse spaces around the basename conservatively: never collapse a
    # potentially special Win32 name with a literal extended-namespace file.
    basename = component.split('.', 1)[0].strip(' ')
    basename = basename.translate(str.maketrans('abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
    return re.fullmatch(r'(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])', basename) is not None


def _path(value, rule, profile):
    context = profile['source_contexts'][rule['context']]
    roots = {_root(root) for root in context['absolute_roots']}
    path = value.replace('/', '\\')
    if path.startswith('\\\\?\\') and (not value.startswith('\\\\?\\') or '/' in value):
        _fail('invalid_extended_windows_path_representation')
    if path[:8].casefold() == '\\\\?\\unc\\':
        path = '\\\\' + path[8:]
    elif path.startswith('\\\\?\\'):
        path = path[4:]
    if path.casefold().startswith(('\\\\.\\', '\\device\\', '\\??\\', '\\systemroot\\')) or any(c in path for c in '*?"<>|'):
        _fail('invalid_windows_volume_path_representation')
    drive, tail = ntpath.splitdrive(path)
    if drive:
        if not tail.startswith('\\') or _root(drive) not in roots:
            _fail('path_root_or_volume_mismatch')
    elif not path.startswith('\\') or not rule['allow_volume_rooted']:
        _fail('path_requires_explicit_volume_root')
    trailing = tail.endswith('\\')
    body = tail[1:] if tail.startswith('\\') else tail
    if body.startswith('\\'):
        _fail('invalid_windows_volume_path_component')
    if trailing:
        body = body[:-1]
    components = body.split('\\') if body else []
    if any(not component or component in ('.', '..') or component.endswith((' ', '.')) or ':' in component for component in components):
        _fail('invalid_windows_volume_path_component')
    if any(_reserved_device_component(component) for component in components):
        _fail('reserved_windows_device_component')
    if not rule['case_sensitive']:
        components = [component.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))
                      for component in components]
    return ('windows-volume-path-v1', _origin(context['origin']),
            context['volume']['kind'], context['volume']['value'], tuple(components), trailing)


def normalize(value, rule, *, profile=None):
    validate_rule(rule, profile=profile)
    if not _string(value, 32768):
        _fail('invalid_matching_normalization_value')
    try:
        if len(value.encode('utf-8')) > 262144:
            _fail('matching_normalization_value_limit')
    except UnicodeEncodeError:
        _fail('invalid_matching_normalization_value')
    if rule['kind'] == 'guid-v1':
        return _guid(value)
    if rule['kind'] == 'zone-label-offset-v1':
        return _zone(value, rule)
    return _path(value, rule, profile)
