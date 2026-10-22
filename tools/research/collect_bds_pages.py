#!/usr/bin/env python3
"""Collect public BDS pages into a resumable, local research ZIP (Python 3.10+).

Standard library only. No account, API key, browser, authentication workaround
or SWORD conversion. Defaults to one request every two seconds. Source content
and the resulting archive must not be committed to the application repository.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
import zipfile


INDEX = 'https://www.bible.com/fr/versions/21'
REF = re.compile(r'^/fr/bible/21/([A-Z0-9]{3})\.([1-9][0-9]*|INTRO[0-9]+)\.BDS/?$')
MAX_BYTES = 12 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)


class IndexParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pages = {}

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        url = urlsplit(urljoin(INDEX, dict(attrs).get('href', '')))
        if url.scheme != 'https' or url.hostname != 'www.bible.com':
            return
        match = REF.fullmatch(url.path)
        if match:
            reference = match[1]+'.'+match[2]
            self.pages.setdefault(reference, 'https://www.bible.com'+url.path)


def discover(data):
    parser = IndexParser()
    parser.feed(data.decode('utf-8', errors='strict'))
    books = {}
    for ref in parser.pages:
        book, chapter = ref.split('.')
        if chapter.isdigit():
            books.setdefault(book, []).append(int(chapter))
    # Guard against a blocked/promotional/truncated response mistaken for an index.
    if len(books) != 66 or sum(map(len, books.values())) < 1000:
        raise ValueError('Incomplete BDS index: expected 66 books and over 1000 chapter links')
    for book, chapters in books.items():
        if sorted(chapters) != list(range(1, max(chapters)+1)):
            raise ValueError(f'Non-contiguous chapter index for {book}')
    return parser.pages


class ChapterParser(HTMLParser):
    def __init__(self, reference):
        super().__init__(convert_charrefs=True)
        self.reference, self.matches = reference, 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if (tag == 'div' and attrs.get('data-usfm') == self.reference
                and any(c.rsplit('_', 1)[-1] == 'chapter' for c in attrs.get('class', '').split())):
            self.matches += 1


def check_page(data, reference):
    parser = ChapterParser(reference)
    parser.feed(data.decode('utf-8', errors='strict'))
    if parser.matches != 1:
        raise ValueError(f'Expected chapter container {reference}; response may be an error page')


class Fetcher:
    def __init__(self, delay):
        self.delay, self.last = delay, 0.0

    def fetch(self, url):
        for attempt in range(3):
            time.sleep(max(0, self.last+self.delay-time.monotonic()))
            self.last = time.monotonic()
            try:
                request = Request(url, headers={
                    'User-Agent': 'Bible-BDS-Research/0.1 (local HTML collection)',
                    'Accept': 'text/html', 'Accept-Language': 'fr',
                })
                with urlopen(request, timeout=30) as response:
                    final = urlsplit(response.url)
                    if final.hostname != 'www.bible.com' or final.scheme != 'https':
                        raise ValueError('Unexpected redirect away from the public Bible site')
                    if response.status != 200 or 'text/html' not in response.headers.get('Content-Type', ''):
                        raise ValueError('Unexpected response status or content type')
                    data = response.read(MAX_BYTES+1)
                    if len(data) > MAX_BYTES:
                        raise ValueError('Response exceeds the research size limit')
                    return data, dict(url=url, final_url=response.url, retrieved_at=now(),
                                      http_status=200, bytes=len(data), sha256=sha(data),
                                      etag=response.headers.get('ETag'),
                                      last_modified=response.headers.get('Last-Modified'))
            except HTTPError as error:
                # No bypass or repeated requests after an access/rate-limit refusal.
                if error.code in {401, 403, 429}:
                    retry = error.headers.get('Retry-After')
                    raise RuntimeError(f'HTTP {error.code}; collection stopped. Retry-After: {retry or "not supplied"}') from error
                if error.code not in {500, 502, 503, 504} or attempt == 2:
                    raise
            except (URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise
            time.sleep(2**(attempt+1))
        raise RuntimeError('Fetch failed')


def archive(directory, manifest):
    """ZIP only verified receipts; an interruption never labels partial data complete."""
    manifest['updated_at'] = now()
    manifest['missing'] = [ref for ref in manifest['index_pages'] if ref not in manifest['pages']]
    manifest['complete'] = not manifest['missing']
    save_json(directory/'manifest.json', manifest)
    destination = directory.with_name(directory.name+'.zip')
    temporary = destination.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        for filename in ['manifest.json', 'index.html']:
            if (directory/filename).is_file():
                output.write(directory/filename, filename)
        for ref in manifest['pages']:
            output.write(directory/'pages'/(ref+'.html'), 'pages/'+ref+'.html')
    temporary.replace(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('bds-pages'))
    parser.add_argument('--delay', type=float, default=2.0, help='Seconds between requests, minimum 1')
    parser.add_argument('--limit', type=int, help='Research smoke test only; omit for all indexed pages')
    args = parser.parse_args()
    if args.delay < 1 or (args.limit is not None and args.limit < 1):
        parser.error('Delay must be >= 1; limit must be positive')
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'pages').mkdir(exist_ok=True)
    saved = directory/'manifest.json'
    manifest = json.loads(saved.read_text(encoding='utf-8')) if saved.exists() else {
        'schema': 1, 'version_id': 21, 'edition': 'BDS', 'index_url': INDEX,
        'created_at': now(), 'pages': {}, 'errors': [],
    }
    if (manifest.get('schema'), manifest.get('version_id'), manifest.get('edition')) != (1, 21, 'BDS'):
        raise ValueError('Output directory belongs to another collection/schema')
    fetcher = Fetcher(args.delay)
    index_path = directory/'index.html'
    receipt = manifest.get('index_receipt', {})
    if not index_path.exists() or sha(index_path.read_bytes()) != receipt.get('sha256'):
        print('Loading BDS chapter/introduction index...', flush=True)
        data, receipt = fetcher.fetch(INDEX)
        pages = discover(data)  # Validate BEFORE replacing the cached index.
        index_path.write_bytes(data)
        manifest['index_receipt'] = receipt
    else:
        pages = discover(index_path.read_bytes())
    manifest['index_pages'] = pages
    # Verify saved files; never trust an old Installed-like receipt blindly.
    valid = {}
    for ref, url in pages.items():
        path = directory/'pages'/(ref+'.html')
        record = manifest['pages'].get(ref)
        if record and record.get('url') == url and path.is_file():
            data = path.read_bytes()
            if sha(data) == record.get('sha256'):
                check_page(data, ref)
                valid[ref] = record
    manifest['pages'] = valid
    save_json(saved, manifest)
    print(f'{len(pages)} indexed pages (chapters + introductions); {len(valid)} already verified.', flush=True)
    downloaded, failed = 0, False
    try:
        for ref, url in pages.items():
            if ref in valid:
                continue
            if args.limit is not None and downloaded >= args.limit:
                break
            print(f'[{len(manifest["pages"])+1}/{len(pages)}] {ref}', flush=True)
            data, record = fetcher.fetch(url)
            check_page(data, ref)
            path = directory/'pages'/(ref+'.html')
            temporary = path.with_suffix('.html.tmp')
            temporary.write_bytes(data)
            temporary.replace(path)
            manifest['pages'][ref] = record
            downloaded += 1
            save_json(saved, manifest)
    except KeyboardInterrupt:
        failed = True
        print('\nInterrupted. Verified pages saved; rerun the same command to resume.', flush=True)
    except Exception as error:
        failed = True
        manifest['errors'].append(dict(reference=ref, url=url, at=now(), error=str(error)))
        print(f'\nStopped at {ref}: {error}\nRerun the same command after resolving the error.', file=sys.stderr)
    finally:
        destination = archive(directory, manifest)
        print(f'ZIP: {destination}\nVerified: {len(manifest["pages"])}/{len(pages)}; complete: {manifest["complete"]}', flush=True)
    return 1 if failed or not manifest['complete'] else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
