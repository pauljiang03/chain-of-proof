"""Reviewed attribute roles: fixed Lean kinds, native value types and narrow meanings.

Role names are claim syntax, not arbitrary text supplied by an investigator. Each
role has its own Lean Kind so a different role cannot reuse an accepted value row.
Counts are reader-recorded scoped counts; they do not imply evidence completeness.
"""
from dataclasses import dataclass
import json
import re


@dataclass(frozen=True)
class AttributeRole:
    name: str
    kind: str
    value_type: str
    meaning: str

    @property
    def value_kind(self):
        return {'string': 'attributeTextValue', 'integer': 'attributeIntegerValue',
                'boolean': 'attributeBooleanValue'}[self.value_type]

    @property
    def semantic_type(self):
        return 'recorded_attribute_' + self.name.replace('.', '_') + '_' + self.value_type

    @property
    def digest_algorithm(self):
        if self.name.startswith(('image.logical.', 'image.acquisition.')):
            return self.name.rsplit('.', 1)[1]
        return None


# Append new entries. Their order also extends the historical fact-kind order.
_SPECS = (
    ('image.logical.md5', 'string', 'MD5 recomputed over the logical image bytes'),
    ('image.logical.sha1', 'string', 'SHA-1 recomputed over the logical image bytes'),
    ('image.logical.sha256', 'string', 'SHA-256 recomputed over the logical image bytes'),
    ('image.acquisition.md5', 'string', 'MD5 declared by the retained acquisition container'),
    ('image.acquisition.sha1', 'string', 'SHA-1 declared by the retained acquisition container'),
    ('os.product_name', 'string', 'operating-system product name recorded in configuration'),
    ('os.install_time', 'string', 'installation timestamp recorded by the operating system'),
    ('os.time_zone_setting', 'string', 'recorded time-zone configuration, not proof of clock accuracy'),
    ('os.registered_owner', 'string', 'registered-owner text, not proof of ownership or user identity'),
    ('machine.account_name', 'string', 'configured computer account name'),
    ('machine.primary_domain', 'string', 'configured primary-domain name'),
    ('machine.last_shutdown', 'string', 'shutdown timestamp retained by the source'),
    ('account.name', 'string', 'account name recorded by the source'),
    ('account.count', 'integer', 'reader-reported account count under its stated enumeration scope'),
    ('account.logon_count', 'integer', 'logon counter retained for this account, not habitual-use attribution'),
    ('account.last_logon', 'string', 'last-logon timestamp retained for this account'),
    ('account.enabled', 'boolean', 'account enabled flag recorded by the source'),
    ('account.last_logon_name', 'string', 'last-logon account name retained by configuration'),
    ('network.description', 'string', 'network-interface description recorded by the source'),
    ('network.ip_address', 'string', 'IP address recorded by the source, not current assignment'),
    ('network.mac_address', 'string', 'MAC address recorded by the source, not physical-user attribution'),
    ('source.path', 'string', 'exact path of the examined source artifact'),
    ('app.name', 'string', 'application named by the source, not proof of installation or execution'),
    ('app.config.real_name', 'string', 'real-name field in application configuration, not verified identity'),
    ('app.config.nickname', 'string', 'nickname field in application configuration'),
    ('app.config.username', 'string', 'username field in application configuration'),
    ('app.config.email', 'string', 'email-address field in application configuration'),
    ('app.config.smtp_server', 'string', 'configured SMTP server'),
    ('app.config.nntp_server', 'string', 'configured NNTP server'),
    ('app.config.newsgroup', 'string', 'newsgroup subscription recorded by application configuration'),
    ('app.config.irc_server', 'string', 'IRC server recorded by application configuration'),
    ('app.config.irc_channel', 'string', 'IRC channel named in a source log or configuration'),
    ('app.config.field', 'string', 'uninterpreted configuration key/value text; no stronger role inferred'),
    ('traffic.user_agent', 'string', 'User-Agent text observed in captured traffic; it can be spoofed'),
    ('traffic.http_host', 'string', 'Host field observed in captured traffic, not attributed browsing'),
    ('traffic.url', 'string', 'URL observed in captured traffic, not attributed browsing'),
    ('traffic.file_name', 'string', 'name of the source containing captured traffic observations'),
    ('traffic.http_method', 'string', 'HTTP method observed in captured traffic'),
    ('browser.email_address', 'string', 'email-address text observed in a browser artifact, not ownership'),
    ('browser.cache_file_name', 'string', 'browser-cache source filename'),
    ('recycle.executable_count', 'integer', 'reader-reported executable count in its stated Recycle Bin scope'),
    ('recycle.file_present', 'boolean', 'whether the named retained file was present in the examined namespace'),
    ('recycle.original_path', 'string', 'original path retained in a Recycle Bin record'),
    ('recycle.stored_path', 'string', 'stored path of a Recycle Bin file'),
    ('filesystem.deleted_count', 'integer', 'reader-reported deleted-entry count in its stated filesystem scope'),
    ('filesystem.deleted_path', 'string', 'path of an entry marked deleted by filesystem metadata'),
    ('filesystem.allocated', 'boolean', 'allocation flag recorded by filesystem metadata; not recoverability'),
    ('scanner.version', 'string', 'scanner executable/version reported by the examination tool'),
    ('scanner.result', 'string', 'scanner result for the declared scope; not proof of historical infection or global absence'),
    ('scanner.scope', 'string', 'declared input and exclusions of this scanner examination'),
    ('scanner.signature', 'string', 'per-file detection/signature name reported by the scanner; may be a false positive and does not prove malware execution'),
    ('app.config.registered_owner', 'string', 'registered-owner text captured in application setup configuration'),
    ('app.config.is_admin', 'boolean', 'administrator flag captured by application setup, not present privilege or personal identity'),
    ('app.config.alternate_nickname', 'string', 'alternate nickname recorded in application configuration'),
    ('app.config.hostname', 'string', 'host name captured in application configuration'),
    ('scanner.detections_found', 'boolean', 'whether this scoped examination reported at least one signature match; false requires completed declared scope, not global virus absence or historical infection'),
    ('filesystem.deleted_flag', 'boolean', 'deleted-entry flag reported by filesystem metadata, not secure erasure or unrecoverability'),
    ('browser.url', 'string', 'URL text retained by a browser record; not proof of a visit or user attribution'),
    ('app.news.group_mailbox', 'string', 'name of a retained newsgroup mailbox file; current subscription is not established'),
    ('app.config.irc_log_file_name', 'string', 'retained IRC log basename whose Session Ident records a channel; not attributed to a person'),
)
ROLES = {name: AttributeRole(name, 'role' + ''.join(part.title().replace('_', '')
         for part in name.split('.')), value_type, meaning)
         for name, value_type, meaning in _SPECS}
ATTRIBUTE_KINDS = ('attributeSubject', 'attributeTextValue', 'attributeIntegerValue',
                   'attributeBooleanValue') + tuple(role.kind for role in ROLES.values())
DIGEST_ALGORITHMS = ('md5', 'sha1')


def roles_catalog():
    return {name: {'role_kind': role.kind, 'value_kind': role.value_kind,
                   'value_type': role.value_type, 'semantic_type': role.semantic_type,
                   'digest_algorithm': role.digest_algorithm,
                   'meaning': role.meaning}
            for name, role in ROLES.items()}


def decode_value(text, value_type):
    """Decode only a typed value's canonical representation, never infer a type."""
    if not isinstance(text, str):
        raise ValueError('attribute value encoding must be a string')
    if value_type == 'string':
        try:
            value = json.loads(text)
        except ValueError as error:
            raise ValueError('attribute text value must be a canonical JSON string') from error
        if type(value) is str and json.dumps(value, ensure_ascii=True) == text:
            return value
        raise ValueError('attribute text value must be a canonical JSON string')
    if value_type == 'integer' and re.fullmatch(r'0|[1-9][0-9]*', text):
        return int(text)
    if value_type == 'boolean' and text in ('true', 'false'):
        return text == 'true'
    raise ValueError('attribute value is not canonically encoded for its declared type')
