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
from .reference_data import ReferenceData,ReferenceDataError,Relationship,reference_key,LICENSE_URL,NUMBERING
from .topic_vocabulary import VOCABULARY

SOURCE_URL='https://www.openbible.info/topics/'
DOWNLOAD_URL='https://a.openbible.info/data/topic-scores.zip'
SOURCE_DATE='2026-10-19'
ARCHIVE_SHA256='47bc1cb1defe5b8f0f65ca9966cd99ff151b7f22cab18ef9c99eda6a244df7cc'
MAX_ARCHIVE=4*1024*1024
MAX_TEXT=8*1024*1024
TRANSFORMATIONS=('Topic identifiers, reference relationships and supplied quality scores only; no Scripture quotations. '
                'Validated local SQLite index; exact ranges deduplicated by maximum score, then canonical order. '
                'Only the explicit curated bilingual vocabulary is exposed; community suggestions are not doctrinal conclusions.')


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
    if source.readline().rstrip('\r\n').split('\t')!=['Topic','OSIS','Quality Score (based on percentage of votes for the passage)',
            '# Generated '+SOURCE_DATE+'. CC-BY License: www.openbible.info/topics']:
        raise ReferenceDataError('Unsupported topic data header')
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
        from .library import download
        self.root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.topic-download-',dir=self.root) as temporary:
            path=Path(temporary)/'topics.zip'
            with path.open('wb') as output:download(DOWNLOAD_URL,output,progress,limit=MAX_ARCHIVE)
            installing();return self.install_archive(path)

    def install_archive(self,path):
        path=Path(path)
        if path.stat().st_size>MAX_ARCHIVE or hashlib.sha256(path.read_bytes()).hexdigest()!=ARCHIVE_SHA256:
            raise ReferenceDataError('Topic checksum mismatch; installed data was preserved')
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
                if any(entry[0] not in names for entry in VOCABULARY):raise ReferenceDataError('Curated topic missing from source')
                value=dict(schema=1,source='OpenBible.info',source_url=SOURCE_URL,download_url=DOWNLOAD_URL,
                    source_date=SOURCE_DATE,archive_sha256=ARCHIVE_SHA256,license='CC BY 4.0',license_url=LICENSE_URL,
                    numbering=NUMBERING,transformations=TRANSFORMATIONS,topics=len(names),
                    relationships=connection.execute('SELECT count(*) FROM topics').fetchone()[0],
                    supported_topics=len(VOCABULARY),installed_at=datetime.now(timezone.utc).isoformat(),
                    index_seconds=round(time.monotonic()-started,3))
                connection.execute('INSERT INTO metadata VALUES(?,?)',('source',json.dumps(value)))
                if connection.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ReferenceDataError('Invalid topic index')
            if candidate.stat().st_size>128*1024*1024:raise ReferenceDataError('Topic index too large')
            with candidate.open('rb') as source:os.fsync(source.fileno())
            os.replace(candidate,self.path)
        return value

    def query(self,topic):
        if topic not in {entry[0] for entry in VOCABULARY}:raise ReferenceDataError('Unsupported topic')
        self.metadata()
        with closing(self.connect()) as connection:
            rows=connection.execute('SELECT start,end,max(score),1 FROM topics WHERE topic=? GROUP BY start,end '
                'ORDER BY max(score) DESC,min(ordering),start,end LIMIT 1000',(topic,)).fetchall()
        return [Relationship(*row) for row in rows]
