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
