"""Reviewed, deliberately partial FR/EN topic names; identifiers are source facts."""
import locale
import json
import hashlib
from datetime import date
from pathlib import Path
import re
import unicodedata
from .i18n import LANGUAGE

BUNDLED=Path(__file__).with_name('study_data')/'topic-vocabulary.json'
MAX_BYTES=1024*1024


def parse(data):
    if len(data)>MAX_BYTES:raise ValueError('Topic vocabulary is too large')
    try:value=json.loads(data)
    except (ValueError,UnicodeError,RecursionError) as error:raise ValueError('Invalid topic vocabulary JSON') from error
    if (not isinstance(value,dict) or type(value.get('schema')) is not int or value.get('schema')!=1
            or value.get('source_url')!='https://www.openbible.info/topics/'
            or value.get('license')!='GPL-2.0-only' or not isinstance(value.get('attribution'),str) or not 0<len(value['attribution'])<=1024
            or not isinstance(value.get('revision'),str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\.[1-9][0-9]{0,8}',value['revision'])
            or not isinstance(value.get('entries'),list) or not 0<len(value['entries'])<=10000):
        raise ValueError('Unsupported topic vocabulary')
    date.fromisoformat(value['revision'][:10])
    entries=[];seen=set()
    def text(item,empty=False):
        return isinstance(item,str) and (empty or bool(item.strip())) and len(item)<=200 and not any(ord(c)<32 for c in item)
    for entry in value['entries']:
        if not isinstance(entry,dict) or set(entry)!={'id','names','synonyms'}:raise ValueError('Invalid topic vocabulary entry')
        identifier=entry['id'];names=entry['names'];synonyms=entry['synonyms']
        if not text(identifier) or len(identifier)>120 or identifier!=identifier.strip() or identifier in seen:
            raise ValueError('Invalid or duplicate topic identifier')
        if (not isinstance(names,dict) or set(names)!={'fr','en'} or not text(names['en']) or not text(names['fr'],True)
                or not isinstance(synonyms,list) or len(synonyms)>32 or not all(text(s) for s in synonyms)):
            raise ValueError('Invalid topic names or synonyms')
        seen.add(identifier);entries.append((identifier,names['fr'],'; '.join(synonyms),names['en']))
    return value,tuple(entries)


class TopicVocabulary:
    def __init__(self,root):self.path=Path(root)/'topic-vocabulary.json'

    def read(self):
        try:
            if self.path.is_symlink() or self.path.stat().st_size>MAX_BYTES:raise ValueError('Invalid saved topic vocabulary')
            data=self.path.read_bytes();value,entries=parse(data)
        except (OSError,ValueError,TypeError,KeyError):
            data=BUNDLED.read_bytes();value,entries=parse(data)
        return value,entries,hashlib.sha256(data).hexdigest()

    def current(self,revision):return self.read()[2]==revision.sha256

    def install_file(self,path,revision):
        from .study_catalogue import atomic_write
        revision.verify(path);data=Path(path).read_bytes();value,entries=parse(data)
        if value['revision']!=revision.revision:raise ValueError('Topic vocabulary revision mismatch')
        atomic_write(self.path,data)
        return value


# Backward-compatible read-only default for existing callers; content lives in
# a separately versioned resource, while each profile may install a newer one.
VOCABULARY=parse(BUNDLED.read_bytes())[1]

def normalized(value):
    return ' '.join(re.findall(r'\w+', ''.join(c for c in unicodedata.normalize('NFKD',value.casefold())
                                            if not unicodedata.combining(c)),re.UNICODE))


def title(entry,language=None):
    base=(language or LANGUAGE).split(':')[0].replace('_','-').casefold().split('-')[0]
    return entry[1] if base=='fr' and entry[1] else entry[3] if len(entry)>3 else entry[0].capitalize()


def suggestions(query,language=None,limit=50,*,entries=None):
    words=normalized(query).split();ranked=[]
    for entry in VOCABULARY if entries is None else entries:
        terms=[normalized(t) for t in (entry[0],entry[1],title(entry,'en'),*entry[2].split(';'))]
        if all(any(word==token or token.startswith(word) for term in terms for token in term.split()) for word in words):
            exact=normalized(query) in terms
            ranked.append((not exact,locale.strxfrm(normalized(title(entry,language))),entry))
    return [entry for _,_,entry in sorted(ranked)[:limit]]
