"""Optional, validated STEP lexical data; independent of notes and Bible modules."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from urllib.parse import quote
from .step_sources import COMMIT,FILES,SOURCE_URL,NOTICE,BOOKS,OSIS_BOOKS,CORPORA

ROW=re.compile(r'^([1-4]?[A-Za-z]{2,4})\.(\d+)\.(\d+)([^#]*)#([^=]+)=(\S+)$')
STRONG=re.compile(r'[GH]\d{4,5}[A-Z]?')
MAX_DATABASE=384*1024*1024
EXPECTED_COUNTS={'tagnt-na27':137992,'tahot-main':305465}


def checkpoint(cancelled):
    if cancelled and cancelled():raise InterruptedError('Study data operation cancelled')


def token_rows(path,corpus,cancelled=None):
    """Preserve raw identity/alternates; never concatenate edition alternatives."""
    with Path(path).open(encoding='utf-8-sig') as stream:
        for line in stream:
            checkpoint(cancelled)
            if len(line)>256*1024:raise ValueError('STEP row exceeds safe limits')
            fields=line.rstrip('\r\n').split('\t');match=ROW.fullmatch(fields[0])
            if not match:continue
            code,chapter,verse,alternates,word,reading=match.groups()
            if code not in BOOKS:raise ValueError('Unsupported STEP book code')
            if corpus=='tagnt-na27':
                if len(fields)<6 or 'NA27' not in fields[5].split('+'):continue
                form=fields[1];translit=''
                form_match=re.fullmatch(r'(.*?) \(([^()]*)\)',form)
                if form_match:form,translit=form_match.groups()
                tags=tuple(dict.fromkeys(STRONG.findall(fields[3].split('=')[0])))
                morphology=fields[3].split('=',1)[1] if '=' in fields[3] else ''
                lemma=fields[4].split('=',1)[0];gloss=fields[4].split('=',1)[1] if '=' in fields[4] else ''
                language='grc'
            else:
                if len(fields)<12 or reading[:1] not in ('L','Q'):continue
                form,translit,gloss=fields[1:4]
                tags=tuple(dict.fromkeys(STRONG.findall(fields[4])))
                morphology=fields[5];lemma=''
                language='arc' if morphology.startswith('A') else 'hbo'
            reference=f'{BOOKS[code]}.{int(chapter)}.{int(verse)}'
            if not 0<=int(verse)<=999 or not 1<=int(chapter)<=200:raise ValueError('Invalid STEP address')
            payload=dict(source_key=fields[0],reference=reference,alternates=alternates,
                         word=word,reading=reading,form=form,transliteration=translit,
                         morphology=morphology,lemma=lemma,gloss=gloss,language=language,tags=tags)
            if corpus=='tahot-main':
                payload['lexical']=[]
                for tag,form,gloss in re.findall(r'\{([GH]\d{4,5}[A-Z]?)=([^={}]+)=([^{}]*)\}',fields[11]):
                    payload['lexical'].append((tag,form,gloss))
            order=(OSIS_BOOKS.index(BOOKS[code])*1000000+int(chapter)*1000+int(verse))
            yield order,payload


def lexicon_rows(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        for line in stream:
            fields=line.rstrip('\r\n').split('\t')
            if len(fields)<8 or not re.fullmatch(r'G\d{4,5}',fields[0]):continue
            match=STRONG.match(fields[1])
            if not match:continue
            yield dict(id=match[0],basic=fields[0],lemma=fields[3],transliteration=fields[4],
                       category=fields[5],gloss=fields[6],definition=fields[7],language='grc')


class StepData:
    def __init__(self,root):
        self.root=Path(root);self.path=self.root/'step-word-study.sqlite3'

    @property
    def revision(self):
        try:info=self.path.stat();return info.st_ino,info.st_mtime_ns,info.st_size
        except FileNotFoundError:return None

    def connect(self):
        if not self.path.is_file() or self.path.stat().st_size>MAX_DATABASE:raise ValueError('Study data unavailable')
        connection=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)
        connection.execute('PRAGMA query_only=ON');return connection

    def metadata(self):
        try:
            with closing(self.connect()) as db:
                value=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
                if value['schema']!=1 or value['commit']!=COMMIT:raise ValueError('Unsupported study data version')
                db.execute('SELECT corpus,reference,payload FROM tokens LIMIT 1').fetchone()
                return value
        except (sqlite3.Error,TypeError,KeyError) as error:raise ValueError('Study data unavailable: '+str(error)) from error

    def install(self,progress=lambda done,total:None,installing=lambda:None,cancelled=None):
        from .library import download
        from .step_sources import DOWNLOAD_BYTES
        self.root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.step-download-',dir=self.root) as temporary:
            files={};completed=0
            for name,(path,digest,size) in FILES.items():
                checkpoint(cancelled);destination=Path(temporary)/name
                def report(done,total):checkpoint(cancelled);progress(completed+done,DOWNLOAD_BYTES)
                with destination.open('wb') as stream:
                    download('https://raw.githubusercontent.com/STEPBible/STEPBible-Data/'+COMMIT+'/'+quote(path),stream,report,limit=size+1024)
                completed+=destination.stat().st_size;files[name]=destination
            checkpoint(cancelled);installing()
            return self.install_files(files,cancelled)

    def install_files(self,files,cancelled=None):
        for name,(_,digest,size) in FILES.items():
            checkpoint(cancelled);path=Path(files[name])
            if path.stat().st_size!=size or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ValueError('STEP checksum mismatch; installed data preserved')
        self.root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.step-index-',dir=self.root) as temporary:
            candidate=Path(temporary)/'index.sqlite3';counts={}
            with closing(sqlite3.connect(candidate)) as db,db:
                db.executescript('''CREATE TABLE metadata(value TEXT NOT NULL);
                    CREATE TABLE tokens(corpus TEXT,source_key TEXT,reference TEXT,position INTEGER,payload TEXT,
                        PRIMARY KEY(corpus,source_key));
                    CREATE INDEX token_verse ON tokens(corpus,reference);
                    CREATE TABLE token_lemmas(corpus TEXT,source_key TEXT,lemma TEXT,PRIMARY KEY(corpus,source_key,lemma));
                    CREATE INDEX lemma_occurrences ON token_lemmas(corpus,lemma);
                    CREATE TABLE lexemes(id TEXT PRIMARY KEY,payload TEXT);
                    CREATE TABLE hebrew_glosses(id TEXT,form TEXT,gloss TEXT,PRIMARY KEY(id,form,gloss));''')
                for entry in lexicon_rows(files['greek-lexicon']):
                    checkpoint(cancelled)
                    db.execute('INSERT INTO lexemes VALUES(?,?)',(entry['id'],json.dumps(entry,ensure_ascii=False)))
                for name in FILES:
                    if name=='greek-lexicon':continue
                    corpus='tagnt-na27' if name.startswith('greek-') else 'tahot-main'
                    for position,token in token_rows(files[name],corpus,cancelled):
                        db.execute('INSERT INTO tokens VALUES(?,?,?,?,?)',(corpus,token['source_key'],token['reference'],position,json.dumps(token,ensure_ascii=False,separators=(',',':'))))
                        for tag in token['tags']:db.execute('INSERT INTO token_lemmas VALUES(?,?,?)',(corpus,token['source_key'],tag))
                        for tag,form,gloss in token.get('lexical',[]):db.execute('INSERT OR IGNORE INTO hebrew_glosses VALUES(?,?,?)',(tag,form,gloss))
                        counts[corpus]=counts.get(corpus,0)+1
                if counts!=EXPECTED_COUNTS:raise ValueError('Incomplete STEP corpus')
                metadata=dict(schema=1,commit=COMMIT,files=FILES,notice=NOTICE,counts=counts,corpora=CORPORA)
                db.execute('INSERT INTO metadata VALUES(?)',(json.dumps(metadata),))
                if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Invalid STEP index')
            checkpoint(cancelled)
            if candidate.stat().st_size>MAX_DATABASE:raise ValueError('STEP index exceeds safe limits')
            with candidate.open('rb') as stream:os.fsync(stream.fileno())
            os.replace(candidate,self.path)
        return metadata

    def verse(self,corpus,reference):
        if corpus not in CORPORA:raise ValueError('Unsupported source corpus')
        with closing(self.connect()) as db:
            rows=db.execute('SELECT payload FROM tokens WHERE corpus=? AND reference=? ORDER BY position,source_key LIMIT 1001',(corpus,reference)).fetchall()
            if len(rows)>1000:raise ValueError('Source verse exceeds safe limits')
            return [json.loads(row[0]) for row in rows]

    def lookup(self,identifier):
        if not STRONG.fullmatch(identifier):raise ValueError('Invalid lemma identifier')
        with closing(self.connect()) as db:
            row=db.execute('SELECT payload FROM lexemes WHERE id=?',(identifier,)).fetchone()
            if row:return json.loads(row[0])
            values=db.execute('SELECT form,gloss FROM hebrew_glosses WHERE id=? ORDER BY form,gloss',(identifier,)).fetchall()
            if values:
                return dict(id=identifier,basic=re.match(r'H\d{4,5}',identifier)[0],
                            lemma=' / '.join(dict.fromkeys(r[0] for r in values)),
                            gloss='; '.join(dict.fromkeys(r[1] for r in values)),definition='',
                            transliteration='',category='',language='hbo',source='TAHOT supplied brief glosses')
        return None

    def candidates(self,identifier):
        if not STRONG.fullmatch(identifier):raise ValueError('Invalid lemma identifier')
        # A basic Strong number is lexical evidence, not a disambiguated sense.
        # Return all explicit source IDs and let the user choose.
        basic=re.fullmatch(r'[GH]\d{4,5}',identifier)
        if not basic:return [entry] if (entry:=self.lookup(identifier)) else []
        with closing(self.connect()) as db:
            ids={r[0] for r in db.execute('SELECT id FROM lexemes WHERE json_extract(payload,?)=?',('$.basic',identifier))}
            ids.update(r[0] for r in db.execute('SELECT DISTINCT id FROM hebrew_glosses WHERE id=? OR (substr(id,1,?)=? AND length(id)=?)',
                       (identifier,len(identifier),identifier,len(identifier)+1)))
        return [entry for value in sorted(ids) if (entry:=self.lookup(value))]

    def occurrences(self,corpus,identifier,offset=0,limit=100):
        if corpus not in CORPORA or not STRONG.fullmatch(identifier) or not 0<=offset<=1000000 or not 1<=limit<=200:
            raise ValueError('Invalid occurrence query')
        with closing(self.connect()) as db:
            parameters=(corpus,identifier)
            total=db.execute('SELECT count(*) FROM token_lemmas WHERE corpus=? AND lemma=?',parameters).fetchone()[0]
            query='FROM tokens t JOIN token_lemmas l USING(corpus,source_key) WHERE t.corpus=? AND l.lemma=?'
            verses=db.execute('SELECT count(DISTINCT t.reference) '+query+' AND t.reference NOT LIKE ?',parameters+('%.0',)).fetchone()[0]
            rows=db.execute('SELECT t.reference,min(t.position) '+query+' GROUP BY t.reference ORDER BY min(t.position),t.reference LIMIT ? OFFSET ?',parameters+(limit,offset)).fetchall()
        return dict(tokens=total,verses=verses,references=[r[0] for r in rows],corpus=corpus,lemma=identifier)
