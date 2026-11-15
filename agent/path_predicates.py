"""Versioned lexical path predicates; never resolve files or infer volume identity."""
import re

POLICY = 'windows-volume-relative-directory-v1'


def components(value, *, directory=False):
    """Accept an unambiguous rooted Windows path, retaining no canonicalized output."""
    if not isinstance(value, str) or not 1 <= len(value) <= 32768:
        return None
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or '/' in value:
        return None
    if value.startswith('\\\\'):
        return None  # UNC and device namespaces have different root semantics.
    if re.match(r'^[A-Za-z]:\\', value):
        if directory:
            return None  # The policy directory itself must be volume-relative.
        value = value[2:]
    if not value.startswith('\\') or ':' in value:
        return None
    # A single terminal separator denotes a directory; keep the source value unchanged.
    if value.endswith('\\'):
        value = value[:-1]
    parts = value[1:].split('\\')
    if not parts or any(not p or p in ('.', '..') or p[-1:] in (' ', '.')
                        or any(c in p for c in '<>"|?*') for p in parts):
        return None
    # DOS device names remain ambiguous even when given extensions.
    if any(re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])', p.split('.')[0], re.I)
           for p in parts):
        return None
    return parts


def validate_condition(condition):
    keys = {'role', 'policy', 'directory', 'include_directory', 'case_sensitive'}
    return (isinstance(condition, dict) and set(condition) == keys
            and condition['policy'] == POLICY
            and type(condition['include_directory']) is bool
            and type(condition['case_sensitive']) is bool
            and components(condition['directory'], directory=True) is not None)


def matches_directory(value, condition):
    """Compare components only. A drive prefix is irrelevant to this lexical policy."""
    if not validate_condition(condition):
        return False
    offered = components(value)
    target = components(condition['directory'], directory=True)
    if offered is None:
        return False
    if not condition['case_sensitive']:
        # Only ASCII A-Z aliases are reviewed. Do not approximate filesystem Unicode folding.
        translation = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')
        offered = [p.translate(translation) for p in offered]
        target = [p.translate(translation) for p in target]
    return (offered[:len(target)] == target and
            (len(offered) > len(target) or condition['include_directory']))
