"""Strict native registry field representations used by typed host observations."""
import re


def dword(value, field):
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xffffffff:
        raise ValueError(field + ' is not a native unsigned DWORD')
    return int(value)


def interface_guid(value):
    if not isinstance(value, str) or not re.fullmatch(
            r'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}', value):
        raise ValueError('interface identity is not a literal braced GUID')
    return str(value).upper()


def text_value(value, field):
    """Literal REG_SZ, or exactly one REG_MULTI_SZ member; never join a list."""
    representation = 'literal registry string'
    if isinstance(value, list):
        if len(value) != 1:
            raise ValueError(field + ' has no single string representation')
        value = value[0]
        representation = 'single retained REG_MULTI_SZ member'
    if not isinstance(value, str) or len(value) > 32768 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(field + ' is not bounded literal registry text')
    return str(value), representation
