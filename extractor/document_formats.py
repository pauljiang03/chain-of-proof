"""Literal metadata from OLE Office files and PDF Info dictionaries; nothing is rendered or run."""
from __future__ import annotations

import codecs
import hashlib
import io
import json
import logging
import re
import struct
import subprocess
import sys
from pathlib import Path
from uuid import UUID

MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_PROPERTY_BYTES = 64 * 1024
MAX_CFB_ENTRIES = 4096
MAX_PROPERTIES = 256
MAX_PDF_OBJECTS = 100000
PDF_TIMEOUT_SECONDS = 10
OLE_SIGNATURE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
SUMMARY_STREAM = '\x05SummaryInformation'
SUMMARY_FMTID = UUID('f29f85e0-4ff9-1068-ab91-08002b27b3d9')
FREE, END, FAT, DIFAT = 0xffffffff, 0xfffffffe, 0xfffffffd, 0xfffffffc
OLE_STRINGS = {
    2: 'title', 3: 'subject', 4: 'author', 5: 'keywords', 6: 'comments',
    7: 'template', 8: 'last_author', 9: 'revision', 18: 'application',
}
OLE_TIMES = {12: 'created_filetime', 13: 'last_saved_filetime'}
PDF_FIELDS = {
    '/Title': 'title', '/Author': 'author', '/Subject': 'subject',
    '/Keywords': 'keywords', '/Creator': 'creator', '/Producer': 'producer',
    '/CreationDate': 'created', '/ModDate': 'modified',
}


def _bounded(data):
    if type(data) is not bytes or len(data) > MAX_FILE_BYTES:
        raise ValueError('document exceeds the byte limit or is not bytes')


def _uint(data, offset, size=4):
    if offset < 0 or offset + size > len(data):
        raise ValueError('truncated binary field')
    return int.from_bytes(data[offset:offset + size], 'little')


class _CompoundFile:
    """Read selected streams; every chain is finite, in range and nonoverlapping."""

    def __init__(self, data):
        _bounded(data)
        if len(data) < 1536 or data[:8] != OLE_SIGNATURE:
            raise ValueError('invalid compound-file signature or length')
        version, order, shift, mini_shift = struct.unpack_from('<4H', data, 26)
        if ((version, shift) not in ((3, 9), (4, 12)) or order != 0xfffe or mini_shift != 6
                or any(data[8:24]) or any(data[34:40]) or _uint(data, 56) != 4096):
            raise ValueError('unsupported compound-file header')
        self.data, self.version, self.sector_size = data, version, 1 << shift
        if len(data) % self.sector_size or len(data) < 3 * self.sector_size:
            raise ValueError('truncated compound-file sectors')
        if version == 4 and any(data[512:self.sector_size]):
            raise ValueError('nonzero compound-file header padding')
        self.sectors = len(data) // self.sector_size - 1
        directory_count, fat_count = _uint(data, 40), _uint(data, 44)
        if (version == 3 and directory_count) or not 1 <= fat_count <= self.sectors:
            raise ValueError('invalid compound-file sector count')
        self.claimed, self.mini_claimed = {}, {}
        fat_ids = list(struct.unpack_from('<109I', data, 76))
        difat_start, difat_count = _uint(data, 68), _uint(data, 72)
        if difat_count > self.sectors:
            raise ValueError('DIFAT sector limit exceeded')
        difat_ids = []
        for _ in range(difat_count):
            self._claim(difat_start, 'DIFAT', self.claimed, self.sectors)
            difat_ids.append(difat_start)
            values = struct.unpack('<' + 'I' * (self.sector_size // 4), self._sector(difat_start))
            fat_ids.extend(values[:-1])
            difat_start = values[-1]
        if difat_start != END:
            raise ValueError('invalid DIFAT chain termination')
        if len(fat_ids) < fat_count or any(value != FREE for value in fat_ids[fat_count:]):
            raise ValueError('invalid FAT sector list')
        fat_ids = fat_ids[:fat_count]
        fat_data = []
        for sector in fat_ids:
            self._claim(sector, 'FAT', self.claimed, self.sectors)
            fat_data.append(self._sector(sector))
        fat_blob = b''.join(fat_data)
        self.fat = struct.unpack('<' + 'I' * (len(fat_blob) // 4), fat_blob)
        if len(self.fat) < self.sectors or any(self.fat[s] != FAT for s in fat_ids):
            raise ValueError('invalid FAT allocation')
        if any(self.fat[s] != DIFAT for s in difat_ids):
            raise ValueError('invalid DIFAT allocation')
        directory = self._regular(_uint(data, 48), None, 'directory', MAX_CFB_ENTRIES * 128)
        if version == 4 and len(directory) != directory_count * self.sector_size:
            raise ValueError('directory sector count mismatch')
        self.directory = directory
        root = self._entry(0)
        if root['type'] != 5 or root['name'] != 'Root Entry' or root['left'] != FREE or root['right'] != FREE:
            raise ValueError('invalid compound-file root')
        self.ministream = self._regular(root['start'], root['size'], 'mini stream', MAX_FILE_BYTES)
        mini_count = _uint(data, 64)
        if mini_count > self.sectors:
            raise ValueError('mini FAT sector limit exceeded')
        mini_blob = self._regular(_uint(data, 60), mini_count * self.sector_size, 'mini FAT', MAX_FILE_BYTES)
        self.minifat = struct.unpack('<' + 'I' * (len(mini_blob) // 4), mini_blob)
        # Root-level entries only: embedded documents must not supply the parent's properties.
        self.entries, seen, pending = {}, {0}, [root['child']]
        while pending:
            sid = pending.pop()
            if sid == FREE:
                continue
            if sid in seen or len(seen) >= MAX_CFB_ENTRIES:
                raise ValueError('cyclic or oversized compound-file directory')
            seen.add(sid)
            entry = self._entry(sid)
            if entry['type'] not in (1, 2):
                raise ValueError('invalid root child type')
            folded = entry['name'].casefold()
            if folded in self.entries:
                raise ValueError('duplicate compound-file root name')
            self.entries[folded] = entry
            pending.extend((entry['left'], entry['right']))

    @staticmethod
    def _claim(sector, owner, claimed, count):
        if not 0 <= sector < count or sector in claimed:
            raise ValueError('cyclic, overlapping or out-of-range ' + owner + ' sector')
        claimed[sector] = owner

    def _sector(self, sector):
        if not 0 <= sector < self.sectors:
            raise ValueError('compound-file sector out of range')
        offset = (sector + 1) * self.sector_size
        return self.data[offset:offset + self.sector_size]

    def _regular(self, start, size, owner, limit):
        if size is not None and size > limit:
            raise ValueError(owner + ' exceeds the byte limit')
        pieces, length = [], 0
        while start != END:
            if size == 0 and start == FREE:
                break
            self._claim(start, owner, self.claimed, self.sectors)
            length += self.sector_size
            if length > limit or (size is not None and length > ((size + self.sector_size - 1) // self.sector_size) * self.sector_size):
                raise ValueError(owner + ' chain exceeds declared size or byte limit')
            pieces.append(self._sector(start))
            start = self.fat[start]
        if size is not None and length < size:
            raise ValueError('truncated ' + owner + ' chain')
        return b''.join(pieces)[:size]

    def _entry(self, sid):
        if sid >= MAX_CFB_ENTRIES or sid * 128 + 128 > len(self.directory):
            raise ValueError('compound-file directory ID out of range')
        raw = self.directory[sid * 128:(sid + 1) * 128]
        length = _uint(raw, 64, 2)
        if not 2 <= length <= 64 or length % 2 or raw[length - 2:length] != b'\0\0':
            raise ValueError('invalid compound-file directory name length')
        name = raw[:length - 2].decode('utf-16-le', errors='strict')
        if not name or '\0' in name:
            raise ValueError('invalid compound-file directory name')
        return {'name': name, 'type': raw[66], 'left': _uint(raw, 68), 'right': _uint(raw, 72),
                'child': _uint(raw, 76), 'start': _uint(raw, 116),
                'size': _uint(raw, 120, 4 if self.version == 3 else 8), 'sid': sid}

    def has(self, name):
        return name.casefold() in self.entries

    def read(self, name, limit=MAX_FILE_BYTES):
        entry = self.entries[name.casefold()]
        size = entry['size']
        if entry['type'] != 2 or entry['child'] != FREE or size > limit:
            raise ValueError('invalid or oversized compound-file stream: ' + name)
        if size >= 4096:
            return self._regular(entry['start'], size, name, limit)
        sector, chunks, length = entry['start'], [], 0
        while sector != END:
            if size == 0 and sector == FREE:
                break
            self._claim(sector, name, self.mini_claimed, len(self.ministream) // 64)
            if sector >= len(self.minifat):
                raise ValueError('mini FAT index out of range')
            length += 64
            if length > ((size + 63) // 64) * 64:
                raise ValueError('mini stream exceeds declared size')
            chunks.append(self.ministream[sector * 64:(sector + 1) * 64])
            sector = self.minifat[sector]
        if length < size:
            raise ValueError('truncated mini stream')
        return b''.join(chunks)[:size]


def _summary_properties(data, stream_name=SUMMARY_STREAM):
    if len(data) < 48 or len(data) > MAX_METADATA_BYTES:
        raise ValueError('invalid SummaryInformation size')
    if (_uint(data, 0, 2) != 0xfffe or _uint(data, 2, 2) not in (0, 1)
            or _uint(data, 24) != 1 or data[28:44] != SUMMARY_FMTID.bytes_le):
        raise ValueError('invalid SummaryInformation property-set header')
    offset = _uint(data, 44)
    if offset < 48 or offset % 4:
        raise ValueError('invalid property-set offset')
    size, count = _uint(data, offset), _uint(data, offset + 4)
    if (size < 8 or size % 4 or offset + size > len(data) or count > MAX_PROPERTIES
            or 8 + count * 8 > size or any(data[offset + size:])):
        raise ValueError('invalid property-set size or count')
    table, offsets = {}, set()
    for index in range(count):
        pid, relative = struct.unpack_from('<II', data, offset + 8 + index * 8)
        if pid in table or relative in offsets or relative % 4 or not 8 + 8 * count <= relative < size:
            raise ValueError('duplicate or invalid property identifier/offset')
        table[pid] = relative
        offsets.add(relative)
    boundaries = {start: end for start, end in zip(sorted(offsets), sorted(offsets)[1:] + [size])}

    def value_blob(pid):
        start = table[pid]
        blob = data[offset + start:offset + boundaries[start]]
        if len(blob) < 4 or blob[2:4] != b'\0\0':
            raise ValueError('invalid typed property header')
        return _uint(blob, 0, 2), blob[4:], offset + start

    if 1 not in table:
        raise ValueError('missing SummaryInformation code page')
    kind, raw, _ = value_blob(1)
    if kind != 2 or len(raw) != 4 or any(raw[2:]):
        raise ValueError('invalid SummaryInformation code-page type')
    codepage = _uint(raw, 0, 2)
    if codepage == 0:
        raise ValueError('unspecified SummaryInformation code page')
    encoding = 'utf-16-le' if codepage == 1200 else 'cp' + str(codepage)
    try:
        codecs.lookup(encoding)
    except LookupError as error:
        raise ValueError('unsupported SummaryInformation code page') from error
    properties = []
    for pid in sorted(table):
        if pid not in OLE_STRINGS and pid not in OLE_TIMES:
            continue
        kind, raw, position = value_blob(pid)
        locator = {'property_part': stream_name, 'property_set_fmtid': str(SUMMARY_FMTID),
                   'property_id': pid, 'property_type': kind, 'stream_byte_offset': position,
                   'property_codepage': codepage}
        if pid in OLE_STRINGS:
            if kind != 0x1e or len(raw) < 4:
                raise ValueError('SummaryInformation string has unexpected type')
            length = _uint(raw, 0)
            if length > MAX_PROPERTY_BYTES or 4 + ((length + 3) // 4) * 4 != len(raw):
                raise ValueError('SummaryInformation string exceeds bounds')
            encoded = raw[4:4 + length]
            if any(raw[4 + length:]):
                raise ValueError('nonzero SummaryInformation string padding')
            terminator = b'\0\0' if codepage == 1200 else b'\0'
            if length and (not encoded.endswith(terminator) or (codepage == 1200 and length % 2)):
                raise ValueError('unterminated SummaryInformation string')
            # Strip only the declared terminator, not other NULs.
            text = (encoded[:-len(terminator)] if length else b'').decode(encoding, errors='strict')
            if len(text.encode('utf-8')) > MAX_PROPERTY_BYTES:
                raise ValueError('decoded SummaryInformation string exceeds bounds')
            properties.append(('document.ole.' + OLE_STRINGS[pid], text, locator))
        else:
            if kind != 0x40 or len(raw) != 8:
                raise ValueError('SummaryInformation FILETIME has unexpected type or size')
            properties.append(('document.ole.' + OLE_TIMES[pid], _uint(raw, 0, 8), locator))
    return properties


def parse_ole(data):
    """Identify Office headers and retain only root SummaryInformation values."""
    compound = _CompoundFile(data)
    variants = [name for name in ('WordDocument', 'Workbook', 'Book', 'PowerPoint Document') if compound.has(name)]
    if len(variants) != 1:
        raise ValueError('missing or ambiguous OLE Office main stream')
    main_name = variants[0]
    main = compound.read(main_name)
    if main_name == 'WordDocument':
        if (len(main) < 32 or _uint(main, 0, 2) != 0xa5ec
                or _uint(main, 2, 2) not in (0xc1, 0xd9, 0x101, 0x10c, 0x112)):
            raise ValueError('invalid supported Word FibBase header')
        flags = _uint(main, 10, 2)
        if flags & 0x8100:
            raise ValueError('encrypted Word documents are unsupported')
        table = '1Table' if flags & 0x0200 else '0Table'
        if not compound.has(table) or not compound.read(table):
            raise ValueError('missing Word table stream')
        format_name = 'Word Binary (OLE)'
    elif main_name in ('Workbook', 'Book'):
        if len(main) < 20 or struct.unpack_from('<4H', main) != (0x0809, 16, 0x0600, 0x0005):
            raise ValueError('invalid supported Excel BIFF8 BOF header')
        format_name = 'Excel BIFF8 (OLE)'
    else:
        if not compound.has('Current User'):
            raise ValueError('missing PowerPoint Current User stream')
        current = compound.read('Current User', MAX_METADATA_BYTES)
        if (len(current) < 32 or struct.unpack_from('<HH', current) != (0, 0x0ff6)
                or _uint(current, 8) != 20 or _uint(current, 12) != 0xe391c05f
                or _uint(current, 22, 2) != 0x03f4 or current[24:26] != b'\x03\0'):
            raise ValueError('invalid or encrypted PowerPoint CurrentUserAtom header')
        length, edit = _uint(current, 20, 2), _uint(current, 16)
        if (length > 255 or len(current) not in (32 + length, 32 + length * 3)
                or _uint(current, 4) != len(current) - 8 or _uint(current, 28 + length) not in (8, 9)
                or edit + 8 > len(main) or struct.unpack_from('<HH', main, edit) != (0, 0x0ff5)
                or _uint(main, edit + 4) not in (28, 32) or edit + 8 + _uint(main, edit + 4) > len(main)):
            raise ValueError('invalid PowerPoint current-edit record')
        format_name = 'PowerPoint Binary (OLE)'
    result = {'format': format_name, 'properties': [], 'provenance': {
        'validation': 'bounded CFB allocation and root directory; Office identification headers; typed SummaryInformation',
        'main_part': compound.entries[main_name.casefold()]['name'], 'main_part_sha256': hashlib.sha256(main).hexdigest(),
        'limitation': 'literal OLE metadata; Office content not fully validated; not verified authorship or event/filesystem times',
    }}
    if compound.has(SUMMARY_STREAM):
        summary = compound.read(SUMMARY_STREAM, MAX_METADATA_BYTES)
        entry = compound.entries[SUMMARY_STREAM.casefold()]
        result['properties'] = _summary_properties(summary, entry['name'])
        result['provenance'].update(property_part=entry['name'], property_directory_id=entry['sid'],
                                    property_part_sha256=hashlib.sha256(summary).hexdigest())
    return result


def parse_pdf(data):
    """Read PDF metadata in a child process with time and output limits."""
    _bounded(data)
    if not re.match(br'%PDF-(?:1\.[0-7]|2\.0)(?:\r\n|\r|\n)', data):
        raise ValueError('invalid supported PDF header')
    try:
        run = subprocess.run([sys.executable, '-m', 'extractor.document_formats', '--pdf-metadata'],
                             input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             cwd=str(Path(__file__).resolve().parent.parent), timeout=PDF_TIMEOUT_SECONDS,
                             check=False)
    except subprocess.TimeoutExpired as error:
        raise ValueError('PDF metadata parser time limit exceeded') from error
    if run.returncode != 0 or len(run.stdout) > MAX_METADATA_BYTES:
        raise ValueError('PDF metadata parser failed or exceeded its resource limit')
    result = json.loads(run.stdout)
    if 'error' in result:
        raise ValueError(result['error'])
    return result


def _parse_pdf(data):
    from pypdf import apply_configuration

    # Tight limits: only the catalog and Info dictionary are read.
    with apply_configuration(
            maximum_declared_stream_length=MAX_METADATA_BYTES,
            array_based_stream_maximum_output_length=MAX_METADATA_BYTES,
            array_maximum_element_count=MAX_PDF_OBJECTS,
            dictionary_maximum_element_count=MAX_PROPERTIES,
            lzw_maximum_output_length=MAX_METADATA_BYTES,
            run_length_maximum_output_length=MAX_METADATA_BYTES,
            zlib_maximum_output_length=MAX_METADATA_BYTES,
            brotli_maximum_output_length=MAX_METADATA_BYTES,
            stream_decoding_work_maximum_length=4 * MAX_METADATA_BYTES,
            stream_parsing_work_maximum_count=MAX_PDF_OBJECTS,
            stream_filters_maximum_length=4,
            image_maximum_buffer_size=MAX_METADATA_BYTES,
            jbig2dec_binary=None):
        return _read_pdf(data)


def _read_pdf(data):
    from pypdf import PdfReader
    from pypdf.generic import (ByteStringObject, DictionaryObject, IndirectObject,
                               NameObject, TextStringObject, decode_pdfdocencoding)

    _bounded(data)
    reader = PdfReader(io.BytesIO(data), strict=True, xref_stream_maximum_entries=MAX_PDF_OBJECTS)
    if reader.is_encrypted:
        raise ValueError('encrypted PDF documents are unsupported')
    if sum(len(entries) for entries in reader.xref.values()) + len(reader.xref_objStm) > MAX_PDF_OBJECTS:
        raise ValueError('PDF cross-reference object limit exceeded')
    root = reader.root_object
    if type(root) is not DictionaryObject or root.get('/Type') != NameObject('/Catalog'):
        raise ValueError('invalid PDF catalog')
    version = reader.pdf_header[5:]
    if '/Version' in root:
        override = root.raw_get('/Version')
        if type(override) is not NameObject or not re.fullmatch(r'/(?:1\.[0-7]|2\.0)', str(override)):
            raise ValueError('unsupported PDF catalog version')
        version = max(version, str(override)[1:])
    result = {'format': 'PDF', 'properties': [], 'provenance': {
        'validation': 'strict pypdf cross-reference parsing and catalog/Info dictionary types',
        'pdf_version': reader.pdf_header, 'pdf_effective_version': version,
        'limitation': 'literal PDF Info strings only; no XMP; not verified authorship or event/filesystem times',
    }}
    if '/Info' not in reader.trailer:
        return result
    reference = reader.trailer.raw_get('/Info')
    if type(reference) is not IndirectObject:
        raise ValueError('PDF Info must be an indirect dictionary')
    info = reference.get_object()
    if type(info) is not DictionaryObject or len(info) > MAX_PROPERTIES:
        raise ValueError('invalid or oversized PDF Info dictionary')
    object_id = str(reference.idnum) + ' ' + str(reference.generation) + ' R'
    result['provenance']['pdf_info_object'] = object_id
    for key, suffix in PDF_FIELDS.items():
        if key not in info:
            continue
        value = info.raw_get(key)
        field_object = None
        if type(value) is IndirectObject:
            field_object = str(value.idnum) + ' ' + str(value.generation) + ' R'
            value = value.get_object()
        if type(value) not in (TextStringObject, ByteStringObject):
            raise ValueError('PDF Info field is not an exactly decoded text string: ' + key)
        raw = value.original_bytes if type(value) is TextStringObject else bytes(value)
        if len(raw) > MAX_PROPERTY_BYTES:
            raise ValueError('PDF Info encoded string exceeds the byte limit')
        # Decode by the encoding the file signals (ISO 32000), not pypdf's UTF-16 guess.
        # PDF 2.0 also allows UTF-8 with a BOM. Dates stay literal.
        if raw.startswith(b'\xfe\xff'):
            literal, encoding = raw[2:].decode('utf-16-be', errors='strict'), 'UTF-16BE'
        elif raw.startswith(b'\xff\xfe'):
            raise ValueError('PDF text string has unsupported UTF-16LE byte order')
        elif raw.startswith(b'\xef\xbb\xbf') and version == '2.0':
            literal, encoding = raw[3:].decode('utf-8', errors='strict'), 'UTF-8'
        else:
            literal, encoding = decode_pdfdocencoding(raw), 'PDFDocEncoding'
        if len(literal.encode('utf-8', errors='strict')) > MAX_PROPERTY_BYTES:
            raise ValueError('PDF Info string exceeds the byte limit')
        result['properties'].append(('document.pdf.' + suffix, literal, {
            'pdf_dictionary': 'trailer/Info', 'pdf_field': key, 'pdf_info_object': object_id,
            'pdf_field_object': field_object,
            'pdf_string_encoding': encoding, 'pdf_string_bytes_sha256': hashlib.sha256(raw).hexdigest(),
        }))
    return result


def _pdf_worker():
    try:
        if sys.platform != 'win32':
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
            if sys.platform != 'darwin':
                resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))

        class RejectRecovery(logging.Handler):
            def emit(self, record):
                if record.levelno >= logging.WARNING:
                    raise ValueError('PDF parser warning: ' + record.getMessage()[:200])

        logging.getLogger('pypdf').addHandler(RejectRecovery())
        data = sys.stdin.buffer.read(MAX_FILE_BYTES + 1)
        result = _parse_pdf(data)
        output = json.dumps(result, ensure_ascii=True, allow_nan=False).encode('ascii')
        if len(output) > MAX_METADATA_BYTES:
            raise ValueError('PDF metadata output exceeds the byte limit')
    except Exception as error:
        output = json.dumps({'error': type(error).__name__ + ': ' + str(error)[:300]}, ensure_ascii=True).encode('ascii')
    sys.stdout.buffer.write(output)


if __name__ == '__main__' and sys.argv[1:] == ['--pdf-metadata']:
    _pdf_worker()
