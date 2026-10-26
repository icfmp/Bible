"""Isolated, cached local SWORD search; never mutate GTK's reading handle."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import os
import tempfile
from .search_terms import normalized,terms,UNSEGMENTED_LANGUAGES


def search(root,name,query,scope='all',book=None,offset=0,limit=100):
    query=query.strip()
    if not query or len(query)>200 or any(ord(c)<32 for c in query):raise ValueError('Enter a phrase of 1–200 characters')
    request=dict(scope=scope,book=book,offset=offset,limit=limit)
    result=subprocess.run([sys.executable,'-m','bible.text_search',str(root),name,query,json.dumps(request)],
                          capture_output=True,text=True,timeout=90,check=True)
    if len(result.stdout)>128*1024:raise ValueError('Text search response too large')
    value=json.loads(result.stdout)
    if not isinstance(value.get('references'),list) or len(value['references'])>500:raise ValueError('Invalid text search')
    return value


def index(root,name,reader):
    files=sorted((str(p.relative_to(reader.root)),p.stat().st_size,p.stat().st_mtime_ns)
                 for p in reader.root.rglob('*') if p.is_file())
    signature=hashlib.sha256(json.dumps([4,files]).encode()).hexdigest()
    cache=Path(root).parent/'search-indexes';cache.mkdir(exist_ok=True)
    path=cache/(name+'.sqlite3')
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            if db.execute('SELECT signature FROM metadata').fetchone()==(signature,):
                db.execute('SELECT reference,normalized FROM verses LIMIT 1').fetchone()
                if db.execute('PRAGMA quick_check').fetchone()[0]=='ok':return path
    except sqlite3.Error:pass
    language=reader.module.getConfigEntry('Lang') or 'und'
    with tempfile.TemporaryDirectory(prefix='.search-',dir=cache) as temp:
        candidate=Path(temp)/'index.sqlite3'
        with closing(sqlite3.connect(candidate)) as db,db:
            db.executescript('CREATE TABLE metadata(signature TEXT,language TEXT);'
                             'CREATE TABLE verses(position INTEGER PRIMARY KEY,reference TEXT,book TEXT,testament INTEGER,normalized TEXT);')
            db.execute('INSERT INTO metadata VALUES(?,?)',(signature,language))
            for book in reader.books:
                for chapter,verses in book.chapters.items():
                    if not verses:continue
                    for reference,text in reader.chapter(f'{book.code}.{chapter}.{verses[0]}').unique_verses():
                        key=reader.key(reference);testament=key.getTestament()
                        testament=ord(testament) if isinstance(testament,str) else int(testament)
                        db.execute('INSERT INTO verses VALUES(?,?,?,?,?)',(key.getIndex(),reference,book.code,testament,' '+normalized(text,language).strip()+' '))
        with candidate.open('rb') as stream:os.fsync(stream.fileno())
        os.replace(candidate,path)
    return path


def query_index(path,query,scope='all',book=None,offset=0,limit=100):
    if scope not in ('all','ot','nt','book') or type(offset) is not int or not 0<=offset<=100000 or type(limit) is not int or not 1<=limit<=500:
        raise ValueError('Invalid search scope or page')
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        language=db.execute('SELECT language FROM metadata').fetchone()[0]
        filters=[];parameters=[]
        for term in terms(query,language):
            filters.append('instr(normalized,?)>0')
            parameters.append(term if language.split('-')[0] in UNSEGMENTED_LANGUAGES else ' '+term+' ')
        if scope in ('ot','nt'):filters.append('testament=?');parameters.append(1 if scope=='ot' else 2)
        elif scope=='book':filters.append('book=?');parameters.append(book)
        where=' AND '.join(filters)
        total=db.execute('SELECT count(*) FROM verses WHERE '+where,parameters).fetchone()[0]
        refs=[r[0] for r in db.execute('SELECT reference FROM verses WHERE '+where+' ORDER BY position LIMIT ? OFFSET ?',parameters+[limit,offset])]
    return dict(total=total,references=refs,language=language)


def main():
    from .sword_provider import Reader
    root,name,query,request=sys.argv[1:]
    if Path(name).name!=name or name in ('.','..'):raise ValueError('Invalid module name')
    reader=Reader(Path(root)/name,name)
    value=query_index(index(root,name,reader),query,**json.loads(request))
    value['versification']=reader.versification
    print(json.dumps(value))


if __name__=='__main__':main()
