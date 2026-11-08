"""Optional, pinned OpenBible topic relationships; no imported Bible quotations."""
from contextlib import closing
from datetime import datetime,timezone
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
from .reference_data import ReferenceData,ReferenceDataError,Relationship,reference_key,LICENSE_URL,NUMBERING,archive_generation,generation_date
from .topic_vocabulary import TopicVocabulary

SOURCE_URL='https://www.openbible.info/topics/'
DOWNLOAD_URL='https://a.openbible.info/data/topic-scores.zip'
from .study_catalogue import BUNDLED,parse as parse_catalogue
_DEFAULT=parse_catalogue(BUNDLED.read_bytes())['openbible-topics']
SOURCE_DATE=_DEFAULT.generation
ARCHIVE_SHA256=_DEFAULT.sha256
MAX_ARCHIVE=4*1024*1024
MAX_TEXT=8*1024*1024
TRANSFORMATIONS=('Topic identifiers, reference relationships and supplied quality scores only; no Scripture quotations. '
                'Validated local SQLite index; exact ranges deduplicated by maximum score, then canonical order. '
                'The complete source index is retained; separately maintained reviewed names control UI coverage. Community suggestions are not doctrinal conclusions.')


def topic_header(header):
    if len(header)!=4 or header[:3]!=['Topic','OSIS','Quality Score (based on percentage of votes for the passage)']:
        raise ReferenceDataError('Unsupported topic data header')
    return generation_date(header[3],'# Generated ','. CC-BY License: www.openbible.info/topics')


def parse_archive(path):
    path=Path(path)
    if path.stat().st_size>MAX_ARCHIVE:raise ReferenceDataError('Topic archive too large')
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist()
        if len(entries)!=1:raise ReferenceDataError('Expected one topic data file')
        entry=entries[0]
        if (entry.filename!='topic-scores.txt' or entry.is_dir() or stat.S_ISLNK(entry.external_attr>>16)
                or entry.flag_bits&1 or entry.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
                or entry.file_size>MAX_TEXT):raise ReferenceDataError('Unsupported topic archive')
        with archive.open(entry) as source:raw=source.read(MAX_TEXT+1)
        if len(raw)>MAX_TEXT:raise ReferenceDataError('Topic expansion exceeds limit')
    source=io.StringIO(raw.decode('utf-8-sig'))
    topic_header(source.readline().rstrip('\r\n').split('\t'))
    count=0
    for count,line in enumerate(source,1):
        if count>200000 or len(line)>512:raise ReferenceDataError('Topic data exceeds limits')
        fields=line.rstrip('\r\n').split('\t')
        if len(fields)!=3:raise ReferenceDataError('Invalid topic row')
        topic,span,score=fields
        if not topic.strip() or len(topic)>120 or not topic.isprintable():raise ReferenceDataError('Invalid topic identifier')
        targets=span.split('-')
        if len(targets) not in (1,2):raise ReferenceDataError('Invalid topic range')
        start,end=targets[0],targets[-1];first,last=reference_key(start),reference_key(end)
        if first>last or not re.fullmatch(r'[0-9]{1,3}',score) or not 0<=int(score)<=100:
            raise ReferenceDataError('Invalid topic score or range')
        yield topic,start,end,int(score),first
    if not count:raise ReferenceDataError('Empty topic data')


class TopicData(ReferenceData):
    def __init__(self,root):
        super().__init__(root);self.path=self.root/'openbible-topics.sqlite3'

    def metadata(self):
        try:
            revision=self.revision
            if revision and revision==self._metadata_revision:return dict(self._metadata)
            with closing(self.connect()) as connection:
                value=json.loads(connection.execute('SELECT value FROM metadata WHERE key=?',('source',)).fetchone()[0])
                connection.execute('SELECT topic,start,end,score,ordering FROM topics LIMIT 1').fetchone()
                if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ReferenceDataError('Damaged topic data')
            if value['schema']!=1 or value['source_url']!=SOURCE_URL or value['numbering']!=NUMBERING:
                raise ReferenceDataError('Unsupported topic data')
            self._metadata_revision,self._metadata=revision,value;return dict(value)
        except (sqlite3.Error,TypeError,KeyError,ValueError) as error:raise ReferenceDataError(str(error)) from error

    def install(self,progress=lambda done,total:None,installing=lambda:None):
        from .topic_vocabulary import parse as parse_vocabulary
        from .study_catalogue import atomic_write
        fresh=True
        try:revisions=self.catalogue.refresh(include_context=False)
        except OSError:fresh=False;revisions=self.catalogue.load()
        except ValueError as error:raise ReferenceDataError(str(error)) from error
        index=revisions['openbible-topics'];words=revisions['topic-vocabulary']
        vocabulary=TopicVocabulary(self.root)
        installed=None
        try:installed=self.metadata();current=installed['archive_sha256']==index.sha256
        except (OSError,ValueError,KeyError):current=False
        if not fresh and installed is not None and (not current or not vocabulary.current(words)):
            raise ReferenceDataError('The study catalogue could not be refreshed; installed topics and vocabulary were preserved. Retry when metadata is available.')
        self.root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.topic-download-',dir=self.root) as temporary:
            temporary=Path(temporary);vocabulary_path=None;candidate=None
            try:
                if not vocabulary.current(words):
                    vocabulary_path=temporary/'vocabulary.json'
                    self.catalogue.download('topic-vocabulary',vocabulary_path,progress,revision=words)
                    value,_=parse_vocabulary(vocabulary_path.read_bytes())
                    if value['revision']!=words.revision:raise ReferenceDataError('Topic vocabulary revision mismatch')
                if not current:
                    archive=temporary/'topics.zip'
                    self.catalogue.download('openbible-topics',archive,progress,revision=index)
                    installing();candidate=TopicData(temporary/'prepared')
                    candidate.install_archive(archive,revision=index)
                # Both payloads are checked before replacing either file. Index
                # and vocabulary stay independently versioned and atomically
                # replaced; their exact-ID intersection tolerates interruption.
                previous=vocabulary.path.read_bytes() if vocabulary.path.is_file() else None
                replaced=False
                try:
                    if vocabulary_path:vocabulary.install_file(vocabulary_path,words);replaced=True
                    if candidate:os.replace(candidate.path,self.path)
                except OSError:
                    if replaced:
                        if previous is None:vocabulary.path.unlink(missing_ok=True)
                        else:atomic_write(vocabulary.path,previous)
                    raise
            except ValueError as error:raise ReferenceDataError(str(error)) from error
        return self.metadata()

    def install_archive(self,path,*,revision=None):
        path=Path(path)
        expected=revision.sha256 if revision else ARCHIVE_SHA256
        if path.stat().st_size>MAX_ARCHIVE or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ReferenceDataError('Topic checksum mismatch; installed data was preserved')
        if revision:revision.verify(path)
        generation=archive_generation(path,'topic-scores.txt',topic_header)
        if revision and generation!=revision.generation:raise ReferenceDataError('Topic generation does not match the checked catalogue')
        self.root.mkdir(parents=True,exist_ok=True);started=time.monotonic()
        with tempfile.TemporaryDirectory(prefix='.topic-index-',dir=self.root) as temporary:
            candidate=Path(temporary)/'index.sqlite3'
            with closing(sqlite3.connect(candidate)) as connection,connection:
                connection.executescript('''CREATE TABLE topics(topic TEXT NOT NULL,start TEXT NOT NULL,end TEXT NOT NULL,
                    score INTEGER NOT NULL,ordering INTEGER NOT NULL);
                    CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')
                connection.executemany('INSERT INTO topics VALUES(?,?,?,?,?)',parse_archive(path))
                connection.execute('CREATE INDEX topic_names ON topics(topic)')
                names={r[0] for r in connection.execute('SELECT DISTINCT topic FROM topics')}
                value=dict(schema=1,source='OpenBible.info',source_url=SOURCE_URL,download_url=revision.url if revision else DOWNLOAD_URL,
                    source_date=generation,archive_sha256=expected,license='CC BY 4.0',license_url=LICENSE_URL,
                    numbering=NUMBERING,transformations=TRANSFORMATIONS,topics=len(names),
                    relationships=connection.execute('SELECT count(*) FROM topics').fetchone()[0],
                    installed_at=datetime.now(timezone.utc).isoformat(),
                    index_seconds=round(time.monotonic()-started,3))
                connection.execute('INSERT INTO metadata VALUES(?,?)',('source',json.dumps(value)))
                if connection.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ReferenceDataError('Invalid topic index')
            if candidate.stat().st_size>128*1024*1024:raise ReferenceDataError('Topic index too large')
            with candidate.open('rb') as source:os.fsync(source.fileno())
            os.replace(candidate,self.path)
        return value

    def query(self,topic):
        if not isinstance(topic,str) or not topic.strip() or len(topic)>120 or not topic.isprintable():raise ReferenceDataError('Invalid topic identifier')
        self.metadata()
        with closing(self.connect()) as connection:
            rows=connection.execute('SELECT start,end,max(score),1 FROM topics WHERE topic=? GROUP BY start,end '
                'ORDER BY max(score) DESC,min(ordering),start,end LIMIT 1000',(topic,)).fetchall()
        return [Relationship(*row) for row in rows]

    def identifiers(self):
        self.metadata()
        with closing(self.connect()) as connection:
            return frozenset(row[0] for row in connection.execute('SELECT DISTINCT topic FROM topics'))
