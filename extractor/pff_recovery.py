"""Opt-in, bounded libpff recovered-item observations from a captured PFF file.

The native scan runs in a separate process with its own read-only file handle.
Recovery is a parser operation, not proof of deletion, purging, or allocation.
"""
from __future__ import annotations

import argparse
import base64
import ctypes as C
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys

from .attributes import emit_attribute
from .source_scope import merge_scope, subject_scope
from .store import Evidence, us

# Reviewed installed binary and public C API. A different build needs an ABI review.
LIBRARY_VERSION = '20261030'
LIBRARY_SHA256 = '9d8f26e1e116d9aa727889aa8d2604a4a49fe1332e2ef73b404baea7a9fea266'
RECOVERY_FLAGS = 0
EMAIL_ITEM_TYPE = 11
UNICODE = 0x001F
ROLES = {0x0037: 'mail.recovered.subject_unicode', 0x1000: 'mail.recovered.body_unicode'}
FORMAT = 'conan-pff-recovery-v1'


class RecoveryError(ValueError):
    """No observations may be emitted from this failed scan."""


class ItemRejected(RecoveryError):
    """A recovered item has ambiguous or unsupported requested properties."""


@dataclass(frozen=True)
class Limits:
    input_bytes: int = 256 * 1024 * 1024
    items: int = 5000
    record_sets_per_item: int = 64
    record_sets: int = 100000
    entries_per_set: int = 4096
    entries: int = 2000000
    property_bytes: int = 1024 * 1024
    text_bytes: int = 8 * 1024 * 1024
    output_bytes: int = 32 * 1024 * 1024
    cpu_seconds: int = 30
    wall_seconds: int = 45
    memory_bytes: int = 1024 * 1024 * 1024

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in asdict(self).values()):
            raise ValueError('limits must be positive native integers')
        if self.output_bytes < 16384 or self.property_bytes > self.text_bytes:
            raise ValueError('output budget too small or property budget exceeds aggregate text budget')


def _json(data):
    return (json.dumps(data, sort_keys=True, ensure_ascii=True, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('ascii')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _integer(value, maximum, name):
    if type(value) is not int or not 0 <= value <= maximum:
        raise RecoveryError(name + ' is negative, invalid, or exceeds its budget')
    return value


def _unicode(raw):
    if len(raw) % 2:
        raise ItemRejected('PT_UNICODE has an odd byte length')
    try:
        value = raw.decode('utf-16-le', errors='strict')
    except UnicodeError as error:
        raise ItemRejected('PT_UNICODE has invalid UTF-16LE') from error
    # Preserve literal whitespace and empty values; remove only one storage NUL.
    if value.endswith('\0'):
        value = value[:-1]
    if '\0' in value:
        raise ItemRejected('PT_UNICODE has embedded or repeated terminal NULs')
    return value


def library_identity():
    spec = importlib.util.find_spec('pypff')
    if spec is None or not spec.origin:
        raise RecoveryError('pypff shared library is not installed')
    path = Path(spec.origin).resolve(strict=True)
    digest = _file_hash(path)
    if digest != LIBRARY_SHA256:
        raise RecoveryError('installed libpff binary is not the reviewed build')
    return {'path': str(path), 'sha256': digest, 'version': LIBRARY_VERSION}


class Native:
    """Explicit ABI for owned opaque C handles, never Python object addresses."""

    def __init__(self, identity):
        if (identity.get('version') != LIBRARY_VERSION or identity.get('sha256') != LIBRARY_SHA256
                or _file_hash(identity['path']) != LIBRARY_SHA256):
            raise RecoveryError('native library identity changed or is unsupported')
        self.lib = C.CDLL(identity['path'])
        p, pp = C.c_void_p, C.POINTER(C.c_void_p)
        integer, u32, byte, size = C.c_int, C.c_uint32, C.c_uint8, C.c_size_t
        # All error and handle outputs are pointers to opaque pointers.
        signatures = {
            'get_version': ([], C.c_char_p),
            'file_initialize': ([pp, pp], integer),
            'file_open': ([p, C.c_char_p, integer, pp], integer),
            'file_close': ([p, pp], integer),
            'file_free': ([pp, pp], integer),
            'file_recover_items': ([p, byte, pp], integer),
            'file_get_number_of_recovered_items': ([p, C.POINTER(integer), pp], integer),
            'file_get_recovered_item_by_index': ([p, integer, pp, pp], integer),
            'item_free': ([pp, pp], integer),
            'item_get_identifier': ([p, C.POINTER(u32), pp], integer),
            'item_get_type': ([p, C.POINTER(byte), pp], integer),
            'item_get_number_of_record_sets': ([p, C.POINTER(integer), pp], integer),
            'item_get_record_set_by_index': ([p, integer, pp, pp], integer),
            'record_set_free': ([pp, pp], integer),
            'record_set_get_number_of_entries': ([p, C.POINTER(integer), pp], integer),
            'record_set_get_entry_by_index': ([p, integer, pp, pp], integer),
            'record_entry_free': ([pp, pp], integer),
            'record_entry_get_entry_type': ([p, C.POINTER(u32), pp], integer),
            'record_entry_get_value_type': ([p, C.POINTER(u32), pp], integer),
            'record_entry_get_data_size': ([p, C.POINTER(size), pp], integer),
            'record_entry_get_data': ([p, C.POINTER(byte), size, pp], integer),
            'error_free': ([pp], None),
        }
        for name, (arguments, result) in signatures.items():
            try:
                fn = getattr(self.lib, 'libpff_' + name)
            except AttributeError as error:
                raise RecoveryError('reviewed libpff API symbol is missing: ' + name) from error
            fn.argtypes, fn.restype = arguments, result
        if self.lib.libpff_get_version() != LIBRARY_VERSION.encode('ascii'):
            raise RecoveryError('loaded libpff API version does not match the reviewed build')

    def call(self, name, *args, expected=1):
        error = C.c_void_p()
        try:
            result = getattr(self.lib, 'libpff_' + name)(*args, C.byref(error))
            if result != expected:
                raise RecoveryError('libpff ' + name + ' returned ' + str(result))
        finally:
            if error.value:
                self.lib.libpff_error_free(C.byref(error))

    def number(self, name, handle, ctype=C.c_int):
        value = ctype()
        self.call(name, handle, C.byref(value))
        return value.value

    def handle(self, name, *args):
        value = C.c_void_p()
        self.call(name, *args, C.byref(value))
        if not value.value:
            raise RecoveryError('libpff returned a null owned handle')
        return value

    def free(self, kind, value):
        if value is not None and value.value:
            self.call(kind + '_free', C.byref(value))


def _properties(native, item, limits, totals):
    result, seen, layout = [], set(), []
    count = _integer(native.number('item_get_number_of_record_sets', item),
                     limits.record_sets_per_item, 'item record-set count')
    totals['record_sets'] += count
    _integer(totals['record_sets'], limits.record_sets, 'aggregate record-set count')
    for set_index in range(count):
        record_set = native.handle('item_get_record_set_by_index', item, set_index)
        try:
            entries = _integer(native.number('record_set_get_number_of_entries', record_set),
                               limits.entries_per_set, 'record-set entry count')
            layout.append(entries)
            totals['entries'] += entries
            _integer(totals['entries'], limits.entries, 'aggregate entry count')
            for entry_index in range(entries):
                entry = native.handle('record_set_get_entry_by_index', record_set, entry_index)
                try:
                    tag = native.number('record_entry_get_entry_type', entry, C.c_uint32)
                    if tag not in ROLES:
                        continue
                    if tag in seen:
                        raise ItemRejected('duplicate requested property across recovered item record sets')
                    seen.add(tag)
                    value_type = native.number('record_entry_get_value_type', entry, C.c_uint32)
                    if value_type != UNICODE:
                        raise ItemRejected('requested property is not PT_UNICODE')
                    size = _integer(native.number('record_entry_get_data_size', entry, C.c_size_t),
                                    limits.property_bytes, 'property byte count')
                    totals['text_bytes'] += size
                    _integer(totals['text_bytes'], limits.text_bytes, 'aggregate property byte count')
                    buffer = (C.c_uint8 * max(1, size))()
                    if size:
                        native.call('record_entry_get_data', entry, buffer, size)
                    raw = bytes(buffer[:size])
                    _unicode(raw)
                    result.append({'record_set_index': set_index, 'entry_index': entry_index,
                                   'property_id': tag, 'value_type': value_type,
                                   'raw_bytes': size, 'raw_sha256': _sha(raw),
                                   'raw_base64': base64.b64encode(raw).decode('ascii')})
                finally:
                    native.free('record_entry', entry)
        finally:
            native.free('record_set', record_set)
    return result, layout


def _recover_native(source, identity, limits):
    native = Native(identity)
    file_handle, opened = None, False
    totals = {'record_sets': 0, 'entries': 0, 'text_bytes': 0}
    output = {'items': [], 'issues': [], 'skipped_item_types': {}, 'totals': totals}
    try:
        file_handle = native.handle('file_initialize')
        native.call('file_open', file_handle, os.fsencode(source), 1)
        opened = True
        native.call('file_recover_items', file_handle, RECOVERY_FLAGS)
        count = _integer(native.number('file_get_number_of_recovered_items', file_handle),
                         limits.items, 'recovered-item count')
        output['recovered_item_count'] = count
        for index in range(count):
            item = native.handle('file_get_recovered_item_by_index', file_handle, index)
            try:
                identifier = native.number('item_get_identifier', item, C.c_uint32)
                item_type = native.number('item_get_type', item, C.c_uint8)
                if item_type != EMAIL_ITEM_TYPE:
                    key = str(item_type)
                    output['skipped_item_types'][key] = output['skipped_item_types'].get(key, 0) + 1
                    continue
                locator = {'recovery_index': index, 'item_identifier': identifier, 'item_type': item_type}
                try:
                    properties, layout = _properties(native, item, limits, totals)
                except ItemRejected as error:
                    output['issues'].append(dict(locator, reason=str(error)))
                    continue
                output['items'].append(dict(locator, properties=properties, record_set_entry_counts=layout))
            finally:
                native.free('item', item)
    finally:
        try:
            if opened:
                native.call('file_close', file_handle, expected=0)
        finally:
            native.free('file', file_handle)
    return output


def _resource_limits(limits):
    applied, unavailable = {}, []
    try:
        import resource
    except ImportError:
        return {'applied': {}, 'unavailable': ['resource module']}
    for name, cap in [('RLIMIT_CPU', limits.cpu_seconds), ('RLIMIT_AS', limits.memory_bytes),
                      ('RLIMIT_DATA', limits.memory_bytes), ('RLIMIT_FSIZE', limits.output_bytes // 2),
                      ('RLIMIT_CORE', 0)]:
        key = getattr(resource, name, None)
        if key is None:
            unavailable.append(name)
            continue
        try:
            _, hard = resource.getrlimit(key)
            bound = cap if hard == resource.RLIM_INFINITY else min(cap, hard)
            resource.setrlimit(key, (bound, bound))
            applied[name] = bound
        except (OSError, ValueError):
            unavailable.append(name)
    return {'applied': applied, 'unavailable': unavailable}


def _worker(request_path):
    # The child only accepts a bounded request written by the parent API.
    if Path(request_path).stat().st_size > 16384:
        raise RecoveryError('worker request exceeds its byte budget')
    request = json.loads(Path(request_path).read_bytes())
    limits = Limits(**request['limits'])
    resources = _resource_limits(limits)
    source = Path(request['source'])
    if not source.is_file() or source.stat().st_size != request['input_bytes']:
        raise RecoveryError('captured input size changed')
    if source.stat().st_size > limits.input_bytes or _file_hash(source) != request['input_sha256']:
        raise RecoveryError('captured input hash changed or input exceeds its budget')
    output = _recover_native(source, request['library'], limits)
    if _file_hash(source) != request['input_sha256']:
        raise RecoveryError('captured input changed during recovery')
    output.update(format=FORMAT, input_sha256=request['input_sha256'], library=request['library'],
                  recovery_flags=RECOVERY_FLAGS, resource_limits=resources)
    encoded = _json(output)
    if len(encoded) > limits.output_bytes // 2:
        raise RecoveryError('worker output exceeds its byte budget')
    sys.stdout.buffer.write(encoded)


def _run_worker(request_path, output_dir, limits):
    stdout, stderr = output_dir / 'worker.json', output_dir / 'worker.stderr'
    with stdout.open('xb') as out, stderr.open('xb') as err:
        process = subprocess.Popen([sys.executable, '-m', 'extractor.pff_recovery', '--worker', str(request_path)],
                                   cwd=Path(__file__).resolve().parents[1], stdout=out, stderr=err,
                                   start_new_session=True)
        try:
            returncode = process.wait(timeout=limits.wall_seconds)
        except subprocess.TimeoutExpired as error:
            try:
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                pass  # The process exited between the timeout and termination.
            finally:
                process.wait()
            raise RecoveryError('native recovery exceeded the wall-clock budget') from error
    if returncode != 0:
        raise RecoveryError('native recovery subprocess failed with exit code ' + str(returncode))
    if stdout.stat().st_size > limits.output_bytes // 2 or stderr.stat().st_size > 4096:
        raise RecoveryError('native subprocess output exceeds its byte budget')
    return stdout.read_bytes()


def _validate_response(data, request, limits):
    """Verify the process boundary before creating any typed observations."""
    if len(data) > limits.output_bytes // 2:
        raise RecoveryError('worker response is too large')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RecoveryError('duplicate JSON key in worker response')
            result[key] = value
        return result
    try:
        response = json.loads(data, object_pairs_hook=unique)
        if (response['format'] != FORMAT or response['input_sha256'] != request['input_sha256']
                or response['library'] != request['library'] or type(response['recovery_flags']) is not int
                or response['recovery_flags'] != RECOVERY_FLAGS):
            raise RecoveryError('worker response has the wrong source or library identity')
        count = _integer(response['recovered_item_count'], limits.items, 'recovered-item count')
        totals = response['totals']
        for key, maximum in [('record_sets', limits.record_sets), ('entries', limits.entries),
                             ('text_bytes', limits.text_bytes)]:
            _integer(totals[key], maximum, 'worker aggregate ' + key)
        if type(response['items']) is not list or type(response['issues']) is not list:
            raise RecoveryError('worker item collections are invalid')
        indices, raw_total, set_total, entry_total = set(), 0, 0, 0
        for item in response['items'] + response['issues']:
            index = _integer(item['recovery_index'], count - 1, 'recovery index')
            if index in indices:
                raise RecoveryError('duplicate recovered enumeration index')
            indices.add(index)
            _integer(item['item_identifier'], 0xFFFFFFFF, 'item identifier')
            if type(item['item_type']) is not int or item['item_type'] != EMAIL_ITEM_TYPE:
                raise RecoveryError('worker returned a non-message item as message content')
        for issue in response['issues']:
            if type(issue['reason']) is not str or len(issue['reason']) > 512:
                raise RecoveryError('invalid worker issue')
        for item in response['items']:
            seen, positions = set(), set()
            layout = item['record_set_entry_counts']
            if type(layout) is not list:
                raise RecoveryError('worker record-set layout is invalid')
            _integer(len(layout), limits.record_sets_per_item, 'item record-set count')
            for entries in layout:
                _integer(entries, limits.entries_per_set, 'record-set entry count')
            set_total += len(layout)
            entry_total += sum(layout)
            if type(item['properties']) is not list or len(item['properties']) > len(ROLES):
                raise RecoveryError('worker requested-property count is invalid')
            for prop in item['properties']:
                tag = prop['property_id']
                if type(tag) is not int or tag not in ROLES or tag in seen or type(prop['value_type']) is not int or prop['value_type'] != UNICODE:
                    raise RecoveryError('worker property identity or encoding is ambiguous')
                seen.add(tag)
                set_index = _integer(prop['record_set_index'], len(layout) - 1, 'record-set index')
                entry_index = _integer(prop['entry_index'], layout[set_index] - 1, 'entry index')
                position = (set_index, entry_index)
                if position in positions:
                    raise RecoveryError('duplicate physical property locator within recovered item')
                positions.add(position)
                size = _integer(prop['raw_bytes'], limits.property_bytes, 'raw property byte count')
                raw = base64.b64decode(prop['raw_base64'], validate=True)
                if len(raw) != size or _sha(raw) != prop['raw_sha256']:
                    raise RecoveryError('worker raw property identity does not match its bytes')
                prop['value'] = _unicode(raw)
                raw_total += size
        skipped = 0
        for key, value in response['skipped_item_types'].items():
            if str(int(key)) != key or not 0 <= int(key) <= 255 or int(key) == EMAIL_ITEM_TYPE:
                raise RecoveryError('worker skipped-item type is invalid')
            skipped += _integer(value, count, 'skipped-item count')
        actual = {'record_sets': set_total, 'entries': entry_total, 'text_bytes': raw_total}
        if (len(indices) + skipped != count or any(actual[key] > totals[key] for key in actual)
                or (not response['issues'] and actual != totals)):
            raise RecoveryError('worker counts do not reconcile')
        if type(response['resource_limits']) is not dict:
            raise RecoveryError('worker resource receipt is missing')
        return response
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as error:
        if isinstance(error, RecoveryError):
            raise
        raise RecoveryError('malformed native worker response') from error


def _capture(source, destination, limit):
    # O_NOFOLLOW rejects input symlinks; the source can only be a regular file.
    fd = os.open(source, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise RecoveryError('selected PFF is not a bounded regular file')
        h, total, magic = hashlib.sha256(), 0, b''
        with os.fdopen(fd, 'rb', closefd=False) as handle, destination.open('xb') as out:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                if not magic:
                    magic = chunk[:4]
                total += len(chunk)
                if total > limit:
                    raise RecoveryError('selected PFF grew beyond the input byte budget')
                h.update(chunk)
                out.write(chunk)
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or total != before.st_size:
            raise RecoveryError('selected PFF changed during capture')
        if magic != b'!BDN':
            raise RecoveryError('selected input has no PFF signature')
        destination.chmod(0o400)
        return total, h.hexdigest()
    finally:
        os.close(fd)


def _evidence(response, common, source_path, source_hash, examined_at):
    ev = Evidence()
    provenance = merge_scope(common)
    input_variant = provenance['source_variant']
    provenance.update(source_variant='parser-recovery', input_source_variant=input_variant,
                      artifact=source_path, source_path=source_path, container_sha256=source_hash,
                      parser='libpff recovered-item enumeration', library=response['library'],
                      recovery_flags=RECOVERY_FLAGS,
                      observation='literal recovered property; no allocation, deletion, delivery, or authorship inference')
    for item in response['items']:
        locator = {key: item[key] for key in ('recovery_index', 'item_identifier', 'item_type')}
        for prop in item['properties']:
            subject = json.dumps(['pff-recovered-message', subject_scope(provenance), input_variant,
                                  source_path, source_hash, response['library']['sha256'], locator,
                                  prop['record_set_index']], sort_keys=True, separators=(',', ':'))
            field = {key: prop[key] for key in ('record_set_index', 'entry_index', 'property_id',
                                               'value_type', 'raw_bytes', 'raw_sha256')}
            emit_attribute(ev, subject, ROLES[prop['property_id']], prop['value'], examined_at,
                           **dict(provenance, recovered_item_locator=locator, property_locator=field))
    return ev


def recover_file(source, output_dir, common, examined_at, *, limits=None):
    """Read an explicitly selected captured PFF; create a new output directory.

    Returns a receipt. On any process/source/protocol failure, writes a failed
    receipt and raises RecoveryError; no facts file is written. Caller provenance
    must include image/exhibit and the original artifact path when known.
    """
    limits = limits or Limits()
    if type(examined_at) is not int or examined_at <= 0:
        raise ValueError('examination time must be positive UTC microseconds')
    if not isinstance(common, dict):
        raise ValueError('source provenance must be a dictionary')
    if len(_json(common)) > 16384:
        raise ValueError('source provenance exceeds its byte budget')
    for key in ('image', 'exhibit'):
        if type(common.get(key)) is not str or not common[key].strip():
            raise ValueError('source provenance must identify ' + key)
    source, output_dir = Path(source).absolute(), Path(output_dir).absolute()
    source_path = common.get('source_path') or common.get('artifact') or str(source)
    if type(source_path) is not str or len(source_path.encode('utf-8')) > 8192:
        raise ValueError('source artifact path must be a string')
    output_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
    receipt = {'format': FORMAT, 'status': 'failed', 'selected_input': str(source),
               'source': merge_scope(common), 'source_path': source_path, 'examined_at_us': examined_at,
               'limits': asdict(limits), 'reader_sha256': _file_hash(__file__),
               'source_variant': 'parser-recovery', 'recovery_flags': RECOVERY_FLAGS,
               'scope_of_result': 'parser recovery observations; no completeness or deletion claim'}
    try:
        size, digest = _capture(source, output_dir / 'source.pff', limits.input_bytes)
        receipt.update(input_bytes=size, input_sha256=digest)
        identity = library_identity()
        receipt['library'] = identity
        request = {'source': str(output_dir / 'source.pff'), 'input_sha256': digest,
                   'input_bytes': size, 'library': identity, 'limits': asdict(limits)}
        request_path = output_dir / 'request.json'
        request_path.write_bytes(_json(request))
        if request_path.stat().st_size > 16384:
            raise RecoveryError('worker request exceeds its byte budget')
        response = _validate_response(_run_worker(request_path, output_dir, limits), request, limits)
        if _file_hash(output_dir / 'source.pff') != digest:
            raise RecoveryError('captured source changed after native recovery')
        ev = _evidence(response, common, source_path, digest, examined_at)
        strings, facts = ev.finalize()
        receipt.update(status='completed', attributes=len(facts) // 3,
                       recovered_item_count=response['recovered_item_count'],
                       accepted_message_items=len(response['items']), issues=response['issues'],
                       skipped_item_types=response['skipped_item_types'], totals=response['totals'],
                       resource_limits=response['resource_limits'])
        facts_data = _json({'_meta': {'reader': FORMAT, 'source_variant': 'parser-recovery',
                                     'input_sha256': digest, 'facts': len(facts)},
                            'strings': {str(k): v for k, v in strings.items()}, 'facts': facts})
        receipt['facts_sha256'] = _sha(facts_data)
        other_bytes = sum(p.stat().st_size for p in output_dir.iterdir() if p.name != 'source.pff')
        if other_bytes + len(facts_data) + len(_json(receipt)) > limits.output_bytes:
            raise RecoveryError('aggregate output byte budget exceeded')
        (output_dir / 'facts.json').write_bytes(facts_data)
        (output_dir / 'receipt.json').write_bytes(_json(receipt))
        return receipt
    except Exception as error:
        # Do not retain unvalidated worker text after a failed native operation.
        for name in ('worker.json', 'worker.stderr', 'facts.json'):
            (output_dir / name).unlink(missing_ok=True)
        receipt.pop('facts_sha256', None)
        receipt.update(status='failed', attributes=0, error=type(error).__name__ + ': ' + str(error))
        (output_dir / 'receipt.json').write_bytes(_json(receipt))
        if isinstance(error, RecoveryError):
            raise
        raise RecoveryError('PFF recovery failed; see receipt.json') from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    parser.add_argument('--source')
    parser.add_argument('--output')
    parser.add_argument('--image')
    parser.add_argument('--exhibit')
    parser.add_argument('--artifact')
    parser.add_argument('--source-snapshot', default='unknown')
    parser.add_argument('--input-variant', default='unknown')
    args = parser.parse_args(argv)
    try:
        if args.worker:
            _worker(args.worker)
            return 0
        if not all((args.source, args.output, args.image, args.exhibit)):
            parser.error('--source, --output, --image and --exhibit are required')
        common = {'image': args.image, 'exhibit': args.exhibit,
                  'source_snapshot': args.source_snapshot, 'source_variant': args.input_variant}
        if args.artifact:
            common['artifact'] = args.artifact
        receipt = recover_file(args.source, args.output, common, us(datetime.now(timezone.utc)))
        print(json.dumps({k: receipt[k] for k in ('status', 'attributes', 'recovered_item_count')}))
        return 0
    except Exception as error:
        # Native diagnostics are not expanded into message contents.
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
