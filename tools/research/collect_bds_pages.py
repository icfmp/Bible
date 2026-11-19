#!/usr/bin/env python3
"""Collect a Bible.com version into a resumable, local research ZIP (Python 3.10+).

Standard library only. No account, API key, browser, authentication workaround
or SWORD conversion. Up to ten transfers; globally spaced request starts. Source content
and the resulting archive must not be committed to the application repository.
"""
import argparse
from concurrent.futures import CancelledError, FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
import zipfile


INDEX = 'https://www.bible.com/fr/versions/21'
REF = re.compile(r'^/(?:[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)*/)?bible/([0-9]+)/([A-Z0-9]{3})\.([1-9][0-9]*|INTRO[0-9]+)\.([A-Za-z0-9_-]+)/?$')
MAX_BYTES = 12 * 1024 * 1024


def source_from_url(value):
    """Accept a chapter or version URL; never follow arbitrary hosts/credentials."""
    url = urlsplit(value.strip())
    if (url.scheme != 'https' or url.hostname not in {'www.bible.com', 'bible.com'}
            or url.username or url.password or url.port):
        raise ValueError('Use an https://www.bible.com/ chapter or version URL')
    parts = url.path.strip('/').split('/')
    locale = ''
    if parts[0] not in {'bible', 'versions'}:
        locale = parts.pop(0)
        if not re.fullmatch(r'[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)*', locale):
            raise ValueError('Unrecognized Bible.com language prefix')
    if len(parts) < 2 or parts[0] not in {'bible', 'versions'}:
        raise ValueError('Use a chapter or Bible version URL')
    version = re.fullmatch(r'([1-9][0-9]*)(?:-[A-Za-z0-9_-]+)?', parts[1])
    if not version or (parts[0] == 'versions' and len(parts) != 2):
        raise ValueError('Unrecognized Bible version identifier')
    if parts[0] == 'bible' and (len(parts) > 3 or (len(parts) == 3 and not REF.fullmatch(url.path))):
        raise ValueError('Unrecognized chapter URL')
    prefix = '/'+locale if locale else ''
    return int(version[1]), 'https://www.bible.com'+prefix+'/versions/'+version[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)


class IndexParser(HTMLParser):
    def __init__(self, index_url=INDEX):
        super().__init__(convert_charrefs=True)
        self.pages = {}
        self.abbreviations = set()
        self.version_id, self.index_url = source_from_url(index_url)

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        url = urlsplit(urljoin(self.index_url, dict(attrs).get('href', '')))
        if (url.scheme != 'https' or url.hostname not in {'www.bible.com', 'bible.com'}
                or url.username or url.password or url.port):
            return
        match = REF.fullmatch(url.path)
        if match and int(match[1]) == self.version_id:
            reference = match[2]+'.'+match[3]
            self.abbreviations.add(match[4])
            self.pages.setdefault(reference, 'https://www.bible.com'+url.path)


def discover(data, index_url=INDEX):
    parser = IndexParser(index_url)
    parser.feed(data.decode('utf-8', errors='strict'))
    books = {}
    for ref in parser.pages:
        book, chapter = ref.split('.')
        if chapter.isdigit():
            books.setdefault(book, []).append(int(chapter))
    # Other editions may be NT-only or have additional books. Check the actual
    # linked inventory instead of imposing BDS's canon on every translation.
    if not books or len(parser.abbreviations) != 1:
        raise ValueError('Missing or ambiguous chapter index; response may be an error page')
    if parser.version_id == 21 and (len(books) != 66 or sum(map(len, books.values())) < 1000):
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
        self.lock = threading.Lock()
        self.stop = threading.Event()

    def request_slot(self):
        # One GLOBAL limiter, not one independent rate limit per worker.
        with self.lock:
            pause = max(0, self.last+self.delay-time.monotonic())
            if self.stop.wait(pause):
                raise CancelledError('Collection stopped')
            self.last = time.monotonic()

    def fetch(self, url):
        for attempt in range(3):
            self.request_slot()
            try:
                request = Request(url, headers={
                    'User-Agent': 'Bible-HTML-Research/0.2 (local HTML collection)',
                    'Accept': 'text/html',
                })
                with urlopen(request, timeout=30) as response:
                    final = urlsplit(response.url)
                    if final.hostname != 'www.bible.com' or final.scheme != 'https':
                        raise ValueError('Unexpected redirect away from the public Bible site')
                    if source_from_url(url)[0] != source_from_url(response.url)[0]:
                        raise ValueError('Redirect to a different Bible version')
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
                    self.stop.set()
                    retry = error.headers.get('Retry-After')
                    raise RuntimeError(f'HTTP {error.code}; collection stopped. Retry-After: {retry or "not supplied"}') from error
                if error.code not in {500, 502, 503, 504} or attempt == 2:
                    raise
            except (URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise
            if self.stop.wait(2**(attempt+1)):
                raise CancelledError('Collection stopped')
        raise RuntimeError('Fetch failed')


def collect(directory, manifest, fetcher, workers, limit):
    todo = [(r, u) for r, u in manifest['index_pages'].items() if r not in manifest['pages']]
    if limit is not None:
        todo = todo[:limit]
    iterator = iter(todo)
    pool = ThreadPoolExecutor(max_workers=workers)
    pending = {}
    failed = False

    def download(ref, url):
        try:
            data, record = fetcher.fetch(url)
            check_page(data, ref)
            return data, record
        except Exception:
            fetcher.stop.set()
            raise

    def fill():
        while len(pending) < workers and not fetcher.stop.is_set():
            item = next(iterator, None)
            if item is None:
                break
            ref, url = item
            pending[pool.submit(download, ref, url)] = item

    def finish(future, ref, url):
        nonlocal failed
        try:
            data, record = future.result()
        except CancelledError:
            return
        except Exception as error:
            failed = True
            fetcher.stop.set()
            manifest['errors'].append(dict(reference=ref, url=url, at=now(), error=str(error)))
            print(f'Failed {ref}: {error}', file=sys.stderr, flush=True)
            return
        path = directory/'pages'/(ref+'.html')
        temporary = path.with_suffix('.html.tmp')
        temporary.write_bytes(data)
        temporary.replace(path)
        manifest['pages'][ref] = record
        save_json(directory/'manifest.json', manifest)
        print(f'[{len(manifest["pages"])}/{len(manifest["index_pages"])}] Saved {ref}', flush=True)

    try:
        fill()
        while pending:
            done, _ = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
            for future in done:
                ref, url = pending.pop(future)
                finish(future, ref, url)
            fill()
    except KeyboardInterrupt:
        failed = True
        fetcher.stop.set()
        print('\nStopping. Waiting for in-flight requests (up to 30 seconds)...', flush=True)
    finally:
        fetcher.stop.set()
        pool.shutdown(wait=True, cancel_futures=True)
        # Save successful in-flight responses even when the user interrupted.
        for future, (ref, url) in pending.items():
            try:
                finish(future, ref, url)
            except KeyboardInterrupt:
                failed = True
    return failed


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
    parser.add_argument('--url', default=INDEX, help='Bible.com chapter or version URL (default: BDS)')
    parser.add_argument('--output', type=Path, help='Separate output directory; automatic per version by default')
    parser.add_argument('--workers', type=int, default=4, help='Concurrent transfers, 1 to 10')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Minimum GLOBAL interval between request starts, seconds (>= 0.5)')
    parser.add_argument('--limit', type=int, help='Research smoke test only; omit for all indexed pages')
    args = parser.parse_args()
    if args.delay < 0.5 or not 1 <= args.workers <= 10 or (args.limit is not None and args.limit < 1):
        parser.error('Delay must be >= 0.5; workers 1..10; limit positive')
    version_id, index_url = source_from_url(args.url)
    default_directory = 'bds-pages' if version_id == 21 else f'bible-{version_id}-pages'
    directory = (args.output or Path(default_directory)).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'pages').mkdir(exist_ok=True)
    saved = directory/'manifest.json'
    manifest = json.loads(saved.read_text(encoding='utf-8')) if saved.exists() else {
        'schema': 1, 'version_id': version_id, 'index_url': index_url,
        'created_at': now(), 'pages': {}, 'errors': [],
    }
    if (manifest.get('schema'), manifest.get('version_id')) != (1, version_id):
        raise ValueError('Output directory belongs to another version/schema; choose a separate --output directory')
    fetcher = Fetcher(args.delay)
    index_path = directory/'index.html'
    receipt = manifest.get('index_receipt', {})
    if not index_path.exists() or sha(index_path.read_bytes()) != receipt.get('sha256'):
        print(f'Loading version {version_id} chapter/introduction index...', flush=True)
        data, receipt = fetcher.fetch(index_url)
        pages = discover(data, index_url)  # Validate BEFORE replacing the cached index.
        index_path.write_bytes(data)
        manifest['index_receipt'] = receipt
    else:
        pages = discover(index_path.read_bytes(), index_url)
    manifest['edition'] = REF.fullmatch(urlsplit(next(iter(pages.values()))).path)[4]
    manifest['index_url'] = index_url
    manifest['inventory_scope'] = 'All pages linked by the saved version index; not a proof of edition-wide text completeness'
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
    print(f'Up to {args.workers} simultaneous transfers; global request interval {args.delay}s.', flush=True)
    failed = False
    try:
        failed = collect(directory, manifest, fetcher, args.workers, args.limit)
    finally:
        destination = archive(directory, manifest)
        print(f'ZIP: {destination}\nVerified: {len(manifest["pages"])}/{len(pages)}; complete: {manifest["complete"]}', flush=True)
        if not manifest['complete']:
            print('Rerun the same command to resume.', flush=True)
    return 1 if failed or not manifest['complete'] else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
