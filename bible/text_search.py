"""Isolated, cached local SWORD search; never mutate GTK's reading handle."""
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import os
import tempfile
from .search_terms import normalized,terms,UNSEGMENTED_LANGUAGES
from .languages import canonical_language


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
    signature=hashlib.sha256(json.dumps([5,files]).encode()).hexdigest()
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


# Ranking only: these words still participate in the strict query and excerpt.
_COMMON={
 'fr':frozenset('le la les de des du un une et a au aux en dans pour que qui ce ces cette il elle ils elles son sa ses sur est sont avec car oui se qu l d c j y on vous nous tu je'.split()),
 'en':frozenset('the a an and of to in for with that this it is are was as he she they you we be by from so his her their your our'.split())}
_NEGATION={'fr':frozenset('ne pas non jamais sans ni aucun aucune'.split()),
           'en':frozenset('not no never without neither nor'.split())}
CLOSE_LIMIT=20
CANDIDATE_LIMIT=256


@dataclass(frozen=True)
class TextMatch:
    start: str
    end: str
    kind: str = 'strict'


def _close_matches(db,query,language,scope_filters,scope_parameters,strict_where,strict_parameters):
    base=canonical_language(language).split('-')[0]
    if base not in _COMMON or '"' in query:return [],0
    words=normalized(query,language).split()
    core=tuple(dict.fromkeys(w for w in words if w not in _COMMON[base]))
    if not 3<=len(core)<=12 or len(set(core)-_NEGATION[base])<2:return [],0
    minimum=max(2,len(core)-1)
    clauses=['CASE WHEN instr(normalized,?)>0 THEN 1 ELSE 0 END' for _ in core]
    overlap='('+'+'.join(clauses)+')'
    needles=[' '+w+' ' for w in core]
    filters=[*scope_filters,'NOT ('+strict_where+')',overlap+'>=?']
    candidates=db.execute('SELECT reference,normalized,position,'+overlap+' AS overlap FROM verses WHERE '+
        ' AND '.join(filters)+' ORDER BY overlap DESC,position LIMIT ?',
        needles+scope_parameters+strict_parameters+needles+[minimum,CANDIDATE_LIMIT]).fetchall()
    ranked=[];required_negations=set(words)&_NEGATION[base]
    for ref,text,position,_ in candidates:
        tokens=text.split();hits=[(i,w) for i,w in enumerate(tokens) if w in core]
        matched={w for _,w in hits}
        if len(matched)<minimum:continue
        # Smallest source window containing every matched content word.
        counts={};left=0;best=None
        for right,(last,word) in enumerate(hits):
            counts[word]=counts.get(word,0)+1
            while len(counts)==len(matched):
                first=hits[left][0]
                if best is None or last-first<best[1]-best[0]:best=(first,last)
                old=hits[left][1];counts[old]-=1
                if counts[old]==0:del counts[old]
                left+=1
        if best is None or best[1]-best[0]+1>min(32,max(12,len(words)*2+4)):continue
        observed_negations=set(tokens[best[0]:best[1]+1])&_NEGATION[base]
        if observed_negations!=required_negations:continue
        ranked.append((-len(matched)/len(core),best[1]-best[0],best[0],position,ref))
    return [row[-1] for row in sorted(ranked)[:CLOSE_LIMIT]],len(candidates)


def query_index(path,query,scope='all',book=None,offset=0,limit=100):
    if scope not in ('all','ot','nt','book') or type(offset) is not int or not 0<=offset<=100000 or type(limit) is not int or not 1<=limit<=500:
        raise ValueError('Invalid search scope or page')
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        language=db.execute('SELECT language FROM metadata').fetchone()[0]
        filters=[];parameters=[]
        for term in terms(query,language):
            filters.append('instr(normalized,?)>0')
            parameters.append(term if canonical_language(language).split('-')[0] in UNSEGMENTED_LANGUAGES else ' '+term+' ')
        strict_where=' AND '.join(filters);strict_parameters=list(parameters)
        scope_filters=[];scope_parameters=[]
        if scope in ('ot','nt'):scope_filters.append('testament=?');scope_parameters.append(1 if scope=='ot' else 2)
        elif scope=='book':scope_filters.append('book=?');scope_parameters.append(book)
        where=' AND '.join(filters+scope_filters);parameters+=scope_parameters
        strict_total=db.execute('SELECT count(*) FROM verses WHERE '+where,parameters).fetchone()[0]
        refs=[r[0] for r in db.execute('SELECT reference FROM verses WHERE '+where+' ORDER BY position LIMIT ? OFFSET ?',parameters+[limit,offset])]
        close,candidates=_close_matches(db,query,language,scope_filters,scope_parameters,strict_where,strict_parameters) if strict_total<CLOSE_LIMIT else ([],0)
        matches=[dict(reference=ref,kind='strict') for ref in refs]
        if len(matches)<limit:
            first=max(0,offset-strict_total)
            matches.extend(dict(reference=ref,kind='close') for ref in close[first:first+limit-len(matches)])
    return dict(total=strict_total+len(close),strict_total=strict_total,close_total=len(close),
                references=[r['reference'] for r in matches],matches=matches,language=language,
                approximate_candidates=candidates,candidate_limit=CANDIDATE_LIMIT)


def main():
    from .sword_provider import Reader
    root,name,query,request=sys.argv[1:]
    if Path(name).name!=name or name in ('.','..'):raise ValueError('Invalid module name')
    reader=Reader(Path(root)/name,name)
    value=query_index(index(root,name,reader),query,**json.loads(request))
    value['versification']=reader.versification
    print(json.dumps(value))


if __name__=='__main__':main()
