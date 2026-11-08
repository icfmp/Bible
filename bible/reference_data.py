"""Pinned OpenBible relationships: bounded parsing and atomic offline indexing."""
from dataclasses import dataclass
from contextlib import closing
from datetime import date,datetime, timezone
from functools import lru_cache
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
import time
import zipfile

SOURCE_URL = 'https://www.openbible.info/labs/cross-references/'
DOWNLOAD_URL = 'https://a.openbible.info/data/cross-references.zip'
LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'
from .study_catalogue import StudyCatalogue,BUNDLED,parse as parse_catalogue
_DEFAULT = parse_catalogue(BUNDLED.read_bytes())['openbible-cross-references']
ARCHIVE_SHA256 = _DEFAULT.sha256
SOURCE_DATE = _DEFAULT.generation
MAX_ARCHIVE = 8 * 1024 * 1024
MAX_TEXT = 16 * 1024 * 1024
MAX_DATABASE = 128 * 1024 * 1024
MAX_ROWS = 1000000
NUMBERING = 'OpenBible ESV-style (3 John has 15 verses)'
TRANSFORMATIONS = ('Reference relationships and community scores only; no Scripture quotations. '
                   'Validated and indexed in SQLite; directed links retained. Range results '
                   'deduplicate identical destination ranges, ranked by maximum community '
                   'score, then canonical destination order. No reciprocal links added.')


class ReferenceDataError(ValueError):
    pass


def generation_date(value,prefix,suffix=''):
    if not value.startswith(prefix) or suffix and not value.endswith(suffix):raise ReferenceDataError('Unsupported dataset generation header')
    text=value[len(prefix):len(value)-len(suffix) if suffix else None]
    try:
        if date.fromisoformat(text).isoformat()!=text:raise ValueError('Invalid generation date')
    except ValueError as error:raise ReferenceDataError('Invalid dataset generation date') from error
    return text


def archive_generation(path,filename,header_parser):
    try:
        with zipfile.ZipFile(path) as archive,archive.open(filename) as source:
            line=source.readline(1024).decode('utf-8-sig').rstrip('\r\n')
        return header_parser(line.split('\t'))
    except (KeyError,UnicodeError,zipfile.BadZipFile) as error:raise ReferenceDataError('Unsupported dataset archive') from error


def reference_header(header):
    if len(header)!=4 or header[:3]!=['From Verse','To Verse','Votes']:raise ReferenceDataError('Unsupported reference data header')
    return generation_date(header[3],'#www.openbible.info CC-BY ')


@lru_cache(maxsize=1)
def canon():
    # Publisher's pinned parser default agrees with KJV chapter sizes except
    # 3 John. See source audit; these counts validate addresses, not quotations.
    result = json.loads(Path(__file__).with_name('versification_data').joinpath('KJV.json').read_text())['canon']
    result['3John'] = [15]
    return result


def reference_key(reference):
    if not isinstance(reference, str) or not re.fullmatch(r'[1-3]?[A-Za-z]+\.[1-9][0-9]{0,2}\.[1-9][0-9]{0,2}', reference):
        raise ReferenceDataError('Invalid relationship reference')
    book, chapter, verse = reference.split('.')
    chapter, verse = int(chapter), int(verse)
    books = canon()
    if book not in books or chapter > len(books[book]) or verse > books[book][chapter-1]:
        raise ReferenceDataError('Relationship reference outside the verified source canon: '+reference)
    return list(books).index(book)*1000000 + chapter*1000 + verse


def reference_span(start,end):
    """Enumerate the verified dataset canon, including its split 3 John ending."""
    if reference_key(start)>reference_key(end):raise ReferenceDataError('Reversed relationship range')
    first_book,first_chapter,first_verse=start.split('.')
    last_book,last_chapter,last_verse=end.split('.')
    books=list(canon());left,right=books.index(first_book),books.index(last_book)
    for book in books[left:right+1]:
        chapters=canon()[book]
        low=int(first_chapter) if book==first_book else 1
        high=int(last_chapter) if book==last_book else len(chapters)
        for chapter in range(low,high+1):
            first=int(first_verse) if book==first_book and chapter==int(first_chapter) else 1
            last=int(last_verse) if book==last_book and chapter==int(last_chapter) else chapters[chapter-1]
            for verse in range(first,last+1):yield f'{book}.{chapter}.{verse}'


def parse_archive(path):
    """Yield strictly validated rows without extracting archive paths."""
    path = Path(path)
    if path.stat().st_size > MAX_ARCHIVE:raise ReferenceDataError('Reference archive is too large')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) != 1:raise ReferenceDataError('Expected one reference data file')
        entry = entries[0]
        if (entry.filename != 'cross_references.txt' or entry.is_dir()
                or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1
                or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                or entry.file_size > MAX_TEXT):
            raise ReferenceDataError('Unsupported reference archive layout')
        with archive.open(entry) as source:
            raw = source.read(MAX_TEXT+1)
        if len(raw) > MAX_TEXT:raise ReferenceDataError('Expanded reference data is too large')
    source = io.StringIO(raw.decode('utf-8-sig'))
    header = source.readline().rstrip('\r\n').split('\t')
    reference_header(header)
    count = 0
    for line in source:
        count += 1
        if count > MAX_ROWS or len(line) > 256:raise ReferenceDataError('Reference data exceeds safe limits')
        fields = line.rstrip('\r\n').split('\t')
        if len(fields) != 3:raise ReferenceDataError('Invalid reference data row')
        origin, destination, votes = fields
        reference_key(origin)
        targets = destination.split('-')
        if len(targets) not in (1,2):raise ReferenceDataError('Invalid relationship range')
        start, end = targets[0], targets[-1]
        first, last = reference_key(start), reference_key(end)
        if first > last:raise ReferenceDataError('Reversed relationship range')
        if not re.fullmatch(r'-?[0-9]{1,7}', votes):raise ReferenceDataError('Invalid community score')
        yield origin, start, end, int(votes), first
    if not count:raise ReferenceDataError('Empty reference dataset')


@dataclass(frozen=True)
class Relationship:
    start: str
    end: str
    score: int
    source_count: int


class ReferenceData:
    def __init__(self, root):
        self.root = Path(root)
        self.catalogue=StudyCatalogue(root)
        self.path = self.root / 'openbible-cross-references.sqlite3'
        self._metadata_revision=None;self._metadata=None

    @property
    def revision(self):
        try:
            info = self.path.stat()
            return info.st_ino, info.st_mtime_ns, info.st_size
        except FileNotFoundError:return None

    def connect(self):
        if not self.path.is_file():raise ReferenceDataError('Reference data is not installed')
        if self.path.stat().st_size > MAX_DATABASE:raise ReferenceDataError('Reference index is too large')
        connection = sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro', uri=True)
        connection.execute('PRAGMA query_only=ON')
        return connection

    def metadata(self):
        try:
            revision=self.revision
            if revision is not None and revision==self._metadata_revision:return dict(self._metadata)
            with closing(self.connect()) as connection:
                metadata = json.loads(connection.execute('SELECT value FROM metadata WHERE key=?',('source',)).fetchone()[0])
                connection.execute('SELECT origin,start,end,score,ordering FROM relationships LIMIT 1').fetchone()
                if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                    raise ReferenceDataError('Damaged reference index')
            if (metadata['schema'] != 1 or metadata['source_url'] != SOURCE_URL
                    or metadata['license_url'] != LICENSE_URL or metadata['numbering'] != NUMBERING):
                raise ReferenceDataError('Unsupported reference index')
            self._metadata,self._metadata_revision=metadata,revision
            return dict(metadata)
        except (sqlite3.Error, TypeError, KeyError, ValueError) as error:
            raise ReferenceDataError(str(error)) from error

    def install(self, progress=lambda done,total:None, installing=lambda:None):
        fresh=True
        try:revisions=self.catalogue.refresh(include_context=False)
        except OSError:fresh=False;revisions=self.catalogue.load()
        except ValueError as error:raise ReferenceDataError(str(error)) from error
        revision=revisions['openbible-cross-references']
        if not fresh:
            try:installed=self.metadata()
            except (OSError,ValueError):installed=None
            if installed and installed['archive_sha256']!=revision.sha256:
                raise ReferenceDataError('The study catalogue could not be refreshed; the installed index was preserved. Retry when metadata is available.')
        self.root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.reference-download-',dir=self.root) as temporary:
            archive=Path(temporary)/'references.zip'
            try:self.catalogue.download('openbible-cross-references',archive,progress,revision=revision)
            except ValueError as error:raise ReferenceDataError(str(error)) from error
            installing()
            return self.install_archive(archive,revision=revision)

    def install_archive(self, archive,*,revision=None):
        """Verify even local test/integration input; never accept an unpinned update."""
        archive = Path(archive)
        expected=revision.sha256 if revision else ARCHIVE_SHA256
        if archive.stat().st_size > MAX_ARCHIVE or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise ReferenceDataError('Reference archive checksum mismatch; installed data was preserved')
        if revision:revision.verify(archive)
        generation=archive_generation(archive,'cross_references.txt',reference_header)
        if revision and generation!=revision.generation:raise ReferenceDataError('Reference generation does not match the checked catalogue')
        self.root.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='.reference-index-',dir=self.root) as temporary:
            candidate = Path(temporary)/'index.sqlite3'
            with closing(sqlite3.connect(candidate)) as connection, connection:
                connection.execute('CREATE TABLE relationships(origin TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL, score INTEGER NOT NULL, ordering INTEGER NOT NULL)')
                connection.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
                connection.executemany('INSERT INTO relationships VALUES(?,?,?,?,?)',parse_archive(archive))
                connection.execute('CREATE INDEX relationships_origin ON relationships(origin)')
                count = connection.execute('SELECT count(*) FROM relationships').fetchone()[0]
                metadata = dict(schema=1,source='OpenBible.info',source_url=SOURCE_URL,download_url=revision.url if revision else DOWNLOAD_URL,
                    source_date=generation,archive_sha256=expected,license='CC BY 4.0',license_url=LICENSE_URL,
                    numbering=NUMBERING,transformations=TRANSFORMATIONS,relationships=count,
                    installed_at=datetime.now(timezone.utc).isoformat(),index_seconds=round(time.monotonic()-started,3))
                connection.execute('INSERT INTO metadata VALUES(?,?)',('source',json.dumps(metadata)))
                if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ReferenceDataError('Invalid reference index')
            if candidate.stat().st_size > MAX_DATABASE:raise ReferenceDataError('Reference index is too large')
            with candidate.open('rb') as source:os.fsync(source.fileno())
            os.replace(candidate,self.path)
        return metadata

    def query(self, origins):
        origins = sorted(set(origins))
        if len(origins)>1000:raise ReferenceDataError('Select at most 1000 verses')
        for reference in origins:reference_key(reference)
        self.metadata()
        if not origins:return []
        parameters = ','.join('?' for _ in origins)
        with closing(self.connect()) as connection:
            rows = connection.execute('SELECT start,end,max(score),count(DISTINCT origin) FROM relationships '
                f'WHERE origin IN ({parameters}) GROUP BY start,end ORDER BY max(score) DESC,min(ordering),start,end',origins).fetchall()
        return [Relationship(*row) for row in rows]
