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
    ('app.binary.product_name', 'string', 'literal ProductName in PE StringFileInfo for the examined registered application binary and resource language; not execution, use, or authenticity'),
    ('app.binary.product_version', 'string', 'literal ProductVersion in PE StringFileInfo for the examined registered application binary and resource language; not a derived version year, execution, use, or authenticity'),
    ('app.binary.file_description', 'string', 'literal FileDescription in PE StringFileInfo for the examined registered application binary and resource language; not execution, use, or authenticity'),
    ('app.binary.file_version', 'string', 'literal FileVersion in PE StringFileInfo for the examined registered application binary and resource language; not a derived version year, execution, use, or authenticity'),
    ('app.execution.program', 'string', 'program name explicitly identified by a reviewed execution artifact; records the artifact observation, not verified actual code execution, authenticity, purpose, or the physical user'),
    ('app.execution.path', 'string', 'literal executable path explicitly identified by a reviewed execution artifact; no inferred Prefetch path, shortcut target, shell identifier, verified actual code execution, authenticity, purpose, or physical user'),
    ('os.version', 'string', 'literal CurrentVersion in the selected operating-system configuration; not independently measured runtime or marketing version'),
    ('os.build_number', 'integer', 'canonical nonnegative decimal CurrentBuildNumber from the selected operating-system configuration'),
    ('os.system_root', 'string', 'literal SystemRoot path in the selected operating-system configuration'),
    ('app.execution.recorded_time', 'string', 'UTC timestamp retained by the reviewed execution artifact; not examination time or independent proof of actual execution'),
    ('app.execution.source_type', 'string', 'reviewed execution-artifact format label: Prefetch, UserAssist or Security process creation'),
    ('app.execution.time_meaning', 'string', 'classification of the timestamp field retained by the execution artifact; the execution label is not independent proof of actual execution'),
    ('app.execution.run_count', 'integer', 'source counter interpreted under the reviewed artifact-format rule; not a complete count of actual executions'),
    ('app.execution.raw_run_count', 'integer', 'literal unsigned run-counter field retained by the source artifact, before format-specific interpretation'),
    ('browser.history.browser', 'string', 'browser association from validated history format/schema and product profile layout; not exclusive producer, installation or browser use'),
    ('browser.history.path', 'string', 'exact path of the format-validated browser-history container'),
    ('mail.store.path', 'string', 'exact path of the parser-validated PST or OST mail-store container; not proof of sending or delivery'),
    ('thumbcache.container.path', 'string', 'exact path of the structurally validated thumbnail-cache database or index'),
    ('sticky_notes.container.path', 'string', 'exact path of the schema/content-validated Sticky Notes OLE or SQLite container'),
    ('mail.message.body_unicode', 'string', 'literal PR_BODY (0x1000/PT_UNICODE) message text, preserving empty versus absent; not delivery, reading or authorship'),
    ('mail.message.subject_unicode', 'string', 'literal PR_SUBJECT (0x0037/PT_UNICODE) message text, preserving empty versus absent; not delivery or authorship'),
    ('document.container.path', 'string', 'exact path of the validated OOXML document package'),
    ('document.container.format', 'string', 'format identified by the validated OOXML package structure; not application execution'),
    ('document.core.title', 'string', 'literal title text in the document core-properties XML'),
    ('document.core.subject', 'string', 'literal subject text in the document core-properties XML'),
    ('document.core.creator', 'string', 'literal creator text in the document core-properties XML; not verified authorship or identity'),
    ('document.core.last_modified_by', 'string', 'literal lastModifiedBy text in the document core-properties XML; not verified authorship or identity'),
    ('document.core.description', 'string', 'literal description text in the document core-properties XML'),
    ('document.core.keywords', 'string', 'literal keywords text in the document core-properties XML'),
    ('document.core.created', 'string', 'literal created text in the document core-properties XML; not independently verified creation or filesystem time'),
    ('document.core.modified', 'string', 'literal modified text in the document core-properties XML; not independently verified modification or filesystem time'),
    ('os.effective_time_zone', 'string', 'recorded time-zone name and UTC offset selected only by unambiguous registry bias agreement; not physical clock accuracy, actual daylight-saving state or transition correctness'),
    ('browser.yahoo_mail_cache_file_name', 'string', 'retained IE cache filename linked by an allocated index.dat entry to a validated Yahoo Mail message URL and matching message HTML headers/body; not authenticity, account ownership or user activity'),
    ('vss.copy_id', 'string', 'copy identifier observed in a base-volume VSS catalog entry; not examination of the snapshot contents'),
    ('vss.set_id', 'string', 'set identifier observed in a base-volume VSS catalog entry; not examination of the snapshot contents'),
    ('vss.storage_path', 'string', 'retained VSS store-file path resolved through its base-volume metadata reference; not a UUID-only constructed path or examination of snapshot contents'),
    ('vss.created_at', 'string', 'creation timestamp retained in a base-volume VSS catalog entry; not independently verified physical action time or examination of snapshot contents'),
    ('browser.search.url', 'string', 'literal URL in the exact browser history occurrence that records the search'),
    ('browser.search.query', 'string', 'query text parsed from that same recorded search URL under the reviewed search-provider grammar'),
    ('browser.search.browser', 'string', 'browser association of that same search history source; not physical user attribution'),
    ('browser.search.recorded_time', 'string', 'timestamp retained by that same search history occurrence; not independently verified human activity time'),
    ('recycle.index_file_name', 'string', 'literal filename of the examined Recycle Bin index entry'),
    ('recycle.index_deleted_at', 'string', 'moved-to-Recycle-Bin timestamp retained in that same index entry; not filesystem deallocation or secure erasure'),
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
