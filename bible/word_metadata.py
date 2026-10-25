"""Conservative OSIS lexical evidence; no inferred STEP token alignment."""
from html.parser import HTMLParser
import re


class WordParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.characters=[];self.words=[];self.current=[];self.hidden=0

    def handle_starttag(self,tag,attrs):
        if tag in ('note','title','script','style'):self.hidden+=1
        if not self.hidden and tag=='w':self.current.append((len(self.characters),dict(attrs)))

    def handle_endtag(self,tag):
        if tag in ('note','title','script','style'):self.hidden=max(0,self.hidden-1);return
        if not self.hidden and tag=='w' and self.current:
            start,attrs=self.current.pop();self.words.append((start,len(self.characters),attrs))

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs);self.handle_endtag(tag)

    def handle_data(self,text):
        if not self.hidden:self.characters.extend(c for c in text if not c.isspace())


def aligned_identifiers(raw,source_body,prefix,selected):
    parser=WordParser()
    try:parser.feed(raw);parser.close()
    except Exception:return None
    plain=lambda value:''.join(c for c in value if not c.isspace())
    if ''.join(parser.characters)!=plain(source_body):return None
    start=len(plain(prefix));end=start+len(plain(selected))
    matches=[attrs for a,b,attrs in parser.words if a==start and b==end and b>a]
    if len(matches)!=1:return None
    attrs=matches[0];ids=[]
    for language,number,suffix in re.findall(r'\bstrong:([GH])(\d{1,5})([A-Z]?)(?!\w)',attrs.get('lemma','')):
        value=language+f'{int(number):04d}'+suffix
        if value not in ids:ids.append(value)
    if not ids:return None
    return dict(identifiers=tuple(ids),source_lemma=attrs.get('lemma',''),source_morphology=attrs.get('morph',''))


def selected_metadata(target):
    if not target.native_selection or len(target.references)!=1:return None
    source=target.source;reader=source.reader;document=source.document
    if reader.module.getConfigEntry('SourceType')!='OSIS':return None
    reference=target.references[0]
    span=next((s for s in document.spans if s.reference==reference),None)
    bounds=target.view.get_buffer().get_selection_bounds()
    if not span or not bounds:return None
    first,last=(source.base+i.get_offset() for i in bounds)
    if first<span.body or last>span.end:return None
    reader.module.setKey(reader.key(reference));raw=reader.module.getRawEntry()
    raw=raw if isinstance(raw,str) else raw.c_str()
    return aligned_identifiers(raw,document.copy(span.body,span.end),document.copy(span.body,first),document.copy(first,last))


def source_verse_references(reference,reader):
    """Keep Psalm superscriptions separate from a source verse's body words.

    Prefer existing pinned verse-part mappings. Native SWORD can collapse a
    numbered title onto a body verse; require unambiguous reciprocal coverage
    when the pinned bridge is unavailable. No introduction becomes verse one.
    """
    from .reference_targets import Canon
    from .reference_resolution import resolve,_span,VersificationMismatch
    from .versification_mapping import to_base,from_base
    source=Canon(reader.versification);target=Canon('NRSV')
    source.key(reference)
    parts=to_base(reference,reader.versification)
    if parts is not None:
        refs=set()
        for part in parts:
            # JSword's !pv is a Psalm title; !v denotes the verse body.
            # A whole-verse fallback must never erase that distinction.
            if '!pv' in part or part.startswith('?'):
                raise VersificationMismatch('No source-body alignment for heading: '+reference)
            mapped=from_base(part,'NRSV')
            if not mapped:raise VersificationMismatch('No source-verse alignment: '+reference)
            refs.update(mapped)
        if not refs:raise VersificationMismatch('No source-verse alignment: '+reference)
        ordered=sorted(refs,key=lambda ref:target.key(ref).getIndex())
        if _span(ordered[0],ordered[-1],'NRSV')!=ordered:
            raise VersificationMismatch('Non-contiguous source-verse alignment: '+reference)
        return tuple(ordered)
    mapped=resolve(reference,reader.versification,target,require_entry=False)
    refs=_span(mapped.start,mapped.end,'NRSV')
    key=source.key(reference);index=key.getIndex();verse=key.getVerse()
    for ref in refs:
        reverse=resolve(ref,'NRSV',source,require_entry=False)
        if not source.key(reverse.start).getIndex()<=index<=source.key(reverse.end).getIndex():
            raise VersificationMismatch('No reciprocal source-verse alignment: '+reference)
    for neighbour in (verse-1,verse+1):
        if not 1<=neighbour<=key.getVerseMax():continue
        key.setVerse(neighbour)
        other=resolve(key.getOSISRef(),reader.versification,target,require_entry=False)
        if set(refs).intersection(_span(other.start,other.end,'NRSV')):
            raise VersificationMismatch('Ambiguous source-verse alignment: '+reference)
    return tuple(refs)
