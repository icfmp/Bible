"""Reproduce Original reference-only data from pinned SIL and JSword tables.

SIL English->Original rules cover the OT. The NT uses the existing JSword
German UBS/GNT rules, whose complete NT canon matches SIL Original exactly.
Unsupported SIL verse-part comments are deliberately left unmapped.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
from bible.youversion_osis import BOOKS

ROOT=Path(__file__).resolve().parents[2]


def canon(text):
    result={}
    for line in text.splitlines():
        line=line.split('#',1)[0].strip()
        if not line or '=' in line:continue
        code,*counts=line.split()
        if code not in BOOKS:continue
        chapters=[tuple(map(int,count.split(':'))) for count in counts]
        if [n for n,_ in chapters]!=list(range(1,len(chapters)+1)):raise ValueError('Unsupported canon')
        result[BOOKS[code]]=[maximum for _,maximum in chapters]
    return result


def valid(ref,inventory):
    book,ch,v=ref.split('.');ch,v=int(ch),int(v)
    return book in inventory and 1<=ch<=len(inventory[book]) and 0<=v<=inventory[book][ch-1]


def refs(value):
    code,span=value.strip().split()
    match=re.fullmatch(r'([0-9]+):([0-9]+)(?:-([0-9]+))?',span)
    if not match:raise ValueError('Unsupported mapping range')
    return [f'{BOOKS[code]}.{int(match[1])}.{v}' for v in range(int(match[2]),int(match[3] or match[2])+1)]


def build():
    directory=ROOT/'third_party/libpalaso'
    provenance=json.loads((directory/'provenance.json').read_text())
    for filename,notice in provenance['files'].items():
        assert hashlib.sha256((directory/filename).read_bytes()).hexdigest()==notice['sha256']
    original=canon((directory/'org.vrs.txt').read_text())
    english_text=(directory/'eng.vrs.txt').read_text();english=canon(english_text)
    german=json.loads((ROOT/'bible/versification_data/German.json').read_text())
    base=json.loads((ROOT/'bible/versification_data/KJVA.json').read_text())['canon']
    ot=list(original)[:list(original).index('Matt')]
    # Canon inventory is serialized in Bible order, not SIL's Hebrew book order.
    ot=[code for code in german['canon'] if code in ot]
    nt=[code for code in german['canon'] if code not in ot]
    assert all(original[book]==german['canon'][book] for book in nt)
    rules=defaultdict(list)
    for line in english_text.splitlines():
        line=line.split('#',1)[0].strip()
        if '=' not in line:continue
        left,right=line.split('=')
        if left.split()[0] not in BOOKS or right.split()[0] not in BOOKS:continue
        a,b=refs(left),refs(right)
        if a[0].split('.')[0] not in ot:continue
        if len(a)==len(b):pairs=zip(a,b)
        elif len(a)==1 or len(b)==1:pairs=((x,y) for x in a for y in b)
        else:raise ValueError('Ambiguous mapping')
        for x,y in pairs:rules[x].append(y)
    inverse=defaultdict(list)
    for book in ot:
        assert english[book]==base[book],book
        for ch,maximum in enumerate(english[book],1):
            for verse in range(0,maximum+1):
                ref=f'{book}.{ch}.{verse}'
                for target in rules.get(ref,[ref]):
                    if valid(target,original):inverse[target].append(ref)
    forward={};reverse=defaultdict(list)
    # Source comments explicitly mark these split mappings unsupported. Whole
    # verse labels cannot establish their exact boundaries.
    uncertain={'Num.25.19','Num.26.1','1Kgs.18.33','1Kgs.18.34',
               '1Kgs.22.43','1Kgs.22.44','1Chr.12.4','1Chr.12.5'}
    for book in german['canon']:
        for ch,maximum in enumerate(original[book],1):
            for verse in range(1,maximum+1):
                ref=f'{book}.{ch}.{verse}'
                values=(inverse.get(ref,[]) if book in ot else german['forward'].get(ref,[ref]))
                values=list(dict.fromkeys(values))
                if ref in uncertain or any(value.rsplit('.',1)[-1]=='0' for value in values):values=[]
                forward[ref]=values
                for value in values:reverse[value].append(ref)
    # Store exceptions only; explicit empty results preserve every unsupported
    # source verse. Reverse gaps inside the source canon also remain explicit.
    for book in german['canon']:
        for ch,maximum in enumerate(base[book],1):
            for verse in range(1,maximum+1):
                ref=f'{book}.{ch}.{verse}'
                if valid(ref,original) and ref not in reverse:reverse[ref]=[]
    return dict(canon={book:original[book] for book in german['canon']},
                forward={k:v for k,v in forward.items() if v!=[k]},
                reverse={k:v for k,v in reverse.items() if v!=[k]},absent=[])


if __name__=='__main__':
    path=ROOT/'bible/versification_data/Original.json'
    value=json.dumps(build(),ensure_ascii=False,separators=(',',':'))+'\n'
    import sys
    if '--check' in sys.argv:assert path.read_text()==value
    else:path.write_text(value)
