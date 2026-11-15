#!/usr/bin/env python3
"""Download the public NIST CFReDS Hacking Case images, never the answer key.

SHA-256 values are of the downloaded files, not the image's published acquisition
hash. Complete files are kept; interrupted .part files resume.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

SOURCE_PAGE = 'https://cfreds-archive.nist.gov/Hacking_Case.html'
FILES = (
    ('4Dell Latitude CPi.E01', 'https://cfreds-archive.nist.gov/images/4Dell%20Latitude%20CPi.E01'),
    ('4Dell Latitude CPi.E02', 'https://cfreds-archive.nist.gov/images/4Dell%20Latitude%20CPi.E02'),
    ('SCHARDT.LOG', 'https://cfreds-archive.nist.gov/images/hacking-dd/SCHARDT.LOG'),
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def fetch(destination, name, url):
    final = destination / name
    headers = {}
    if final.exists():
        if not final.is_file() or final.is_symlink():
            raise ValueError(f'not a regular downloaded file: {final}')
        print(f'Preserving existing {name}; hashing its bytes.', flush=True)
        status = 'existing_file_not_redownloaded'
    else:
        partial = destination / (name + '.part')
        if partial.is_symlink():
            raise ValueError(f'refusing symlink: {partial}')
        receipt = destination / (name + '.part.json')
        if receipt.is_symlink():
            raise ValueError(f'refusing symlink: {receipt}')
        prior = json.loads(receipt.read_text()) if receipt.exists() else {}
        # Only resume a prefix bound to this URL and a strong ETag. A loose
        # partial file is restarted; otherwise two server versions could mix.
        validator = prior.get('etag') if prior.get('url') == url else None
        if not isinstance(validator, str) or validator.startswith('W/'):
            validator = None
        offset = partial.stat().st_size if partial.exists() and validator else 0
        request = Request(url, headers={'User-Agent': 'CFReDS-evidence-fetch/1',
                                       **({'Range': f'bytes={offset}-', 'If-Range': validator} if offset else {})})
        with urlopen(request, timeout=120) as response:
            resumed = offset > 0 and response.status == 206
            remaining = None
            if response.status == 206:
                match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                if not resumed or not match:
                    raise ValueError('server returned an unexpected partial response')
                first, last, total = map(int, match.groups())
                if first != offset or last < first or last + 1 != total or response.headers.get('ETag') != validator:
                    raise ValueError('server returned an unexpected resume range or object version')
                remaining = total - offset
            elif response.status != 200:
                raise ValueError(f'unexpected download status: {response.status}')
            if not resumed:
                offset = 0
            headers = {key: response.headers.get(key) for key in ('Content-Length', 'Content-Range', 'ETag', 'Last-Modified')}
            receipt.write_text(json.dumps({'url': url, 'etag': headers['ETag']}))
            received, next_notice = 0, 64 << 20
            print(f'Downloading {name} from byte {offset}.', flush=True)
            with partial.open('ab' if resumed else 'wb') as output:
                for block in iter(lambda: response.read(1 << 20), b''):
                    output.write(block)
                    received += len(block)
                    if received >= next_notice:
                        print(f'{name}: {(offset + received) / (1 << 20):.0f} MiB downloaded', flush=True)
                        next_notice += 64 << 20
            if headers['Content-Length'] is not None and received != int(headers['Content-Length']):
                raise ValueError(f'incomplete download of {name}: {received} bytes')
            if remaining is not None and received != remaining:
                raise ValueError(f'incomplete resumed download of {name}: {received} bytes')
        os.link(partial, final)  # publish without overwriting another complete file
        partial.unlink()
        receipt.unlink(missing_ok=True)
        status = 'downloaded'
    result = {'file': name, 'url': url, 'bytes': final.stat().st_size,
              'sha256': sha256(final), 'status': status, 'response_headers': headers}
    print(f'{name}: {result["bytes"]} bytes; SHA-256 {result["sha256"]}', flush=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--manifest', default='download-manifest.json')
    args = parser.parse_args(argv)
    args.destination.mkdir(parents=True, exist_ok=True)
    manifest = args.destination / args.manifest
    if manifest.exists():
        parser.error('manifest already exists; choose a new --manifest name')
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(lambda item: fetch(args.destination, *item), FILES))
    receipt = {'schema_version': 1, 'source_page': SOURCE_PAGE,
               'retrieved_at': datetime.now(timezone.utc).isoformat(), 'files': records,
               'scope': 'Downloaded container hashes only; logical image verification is separate.'}
    with manifest.open('x') as output:
        json.dump(receipt, output, indent=2)
        output.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
