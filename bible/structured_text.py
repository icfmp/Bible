"""Conservative SWORD markup extraction; no HTML execution or invented headings."""
from dataclasses import dataclass
from html.parser import HTMLParser
import re


@dataclass(frozen=True)
class Segment:
    text: str
    kind: str = 'text'
    styles: tuple[str,...] = ()


class SourceParser(HTMLParser):
    # OSIS/ThML titles contain inline XML. Recent HTMLParser releases give
    # HTML title/textarea RCDATA semantics, which would expose those tags.
    CDATA_CONTENT_ELEMENTS=('script','style')
    RCDATA_CONTENT_ELEMENTS=()

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.segments = []
        self.hidden = 0
        self.heading = 0
        self.heading_kinds = []
        self.divisions = []
        self.paragraph_ids = set()
        self.inline = []

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        # HTMLParser normalizes attribute names, including OSIS sID/eID.
        # A closing milestone is a boundary, never a new enclosing block.
        if attrs.get('eid'):
            if tag=='l':self.segments.append(Segment('\n','poetry',('poetry',)))
            elif tag=='lg' or tag=='div' and (attrs.get('type') in {'paragraph','x-p'} or attrs['eid'] in self.paragraph_ids):
                self.segments.append(Segment('\n\n','break'))
                self.paragraph_ids.discard(attrs['eid'])
            return
        if tag in {'script','style','note'}:self.hidden += 1
        if self.hidden:return
        styles=[]
        if tag=='hi':
            styles={'italic':['italic'],'emphasis':['italic'],'bold':['bold'],'bolditalic':['bold','italic'],'x-bold-italic':['bold','italic'],
                    'small-caps':['small-caps'],'super':['superscript']}.get(attrs.get('type'),[])
        elif tag=='transchange' and attrs.get('type')=='added':styles=['italic']
        elif tag=='divinename':styles=['small-caps']
        if tag in ('hi','transchange','divinename'):self.inline.append((tag,tuple(styles)))
        if tag in {'title','h1','h2','h3','h4'}:
            self.heading += 1
            self.heading_kinds.append('editorial' if tag=='title' and attrs.get('type')=='parallel' else 'heading')
        if tag == 'div':
            paragraph = attrs.get('type') in {'paragraph', 'x-p'}
            if paragraph and attrs.get('sid'):self.paragraph_ids.add(attrs['sid'])
            if not attrs.get('sid'):self.divisions.append(paragraph)
        else:
            paragraph = tag in {'p', 'lg'}
        if paragraph or (tag=='milestone' and attrs.get('type') in {'x-p','paragraph'}):
            self.segments.append(Segment('\n\n','break'))
        elif tag in {'l','lb','br'}:self.segments.append(Segment('\n','poetry',('poetry',)))

    def handle_endtag(self,tag):
        if tag in {'script','style','note'}:self.hidden=max(0,self.hidden-1);return
        if self.hidden:return
        if tag in ('hi','transchange','divinename'):
            for index in range(len(self.inline)-1,-1,-1):
                if self.inline[index][0]==tag:del self.inline[index:];break
        if tag in {'title','h1','h2','h3','h4'}:
            self.heading=max(0,self.heading-1);self.segments.append(Segment('\n','break'))
            if self.heading_kinds:self.heading_kinds.pop()
        paragraph = self.divisions.pop() if tag == 'div' and self.divisions else tag in {'p','lg'}
        if paragraph:self.segments.append(Segment('\n\n','break'))

    def handle_startendtag(self,tag,attrs):
        # Empty ThML p and OSIS start/end milestones each mark a boundary.
        # Do not synthesize a second end event, or retain an empty title/note.
        self.handle_starttag(tag,attrs)
        if not dict(attrs).get('sid') and not dict(attrs).get('eid') and tag in {'note','script','style','title','h1','h2','h3','h4','div'}:
            self.handle_endtag(tag)

    def handle_data(self,text):
        if not self.hidden:self.segments.append(Segment(text,self.heading_kinds[-1] if self.heading_kinds else 'text',
            tuple(dict.fromkeys(style for _,styles in self.inline for style in styles))))


def extract(raw,plain,source_type):
    """Use structure only when its body words agree with SWORD's own plain text.

    A mismatch falls back to exact plain text: unknown markup cannot rewrite the
    resource or leak notes/commands into a purported faithful Bible rendering.
    """
    if source_type not in {'OSIS','ThML'}:return (Segment(plain),)
    parser=SourceParser()
    try:parser.feed(raw);parser.close()
    except Exception:return (Segment(plain),)
    return checked_segments(parser.segments,plain)


def checked_segments(segments,plain):
    body=''.join(s.text for s in segments if s.kind=='text')
    normalize=lambda v: re.sub(r'\s+','',v)
    if normalize(body)!=normalize(plain):
        # Some StripText filters retain editorial titles. Do not guess which
        # words belong to verses; use the original plain output in that case.
        return (Segment(plain),)
    result = [];pending=[]
    def flush(next_segment=None):
        if not pending:return next_segment
        boundaries=[s for s in pending if s.kind in {'break','poetry'}]
        if boundaries:
            # Formatting whitespace between paired milestones is not an extra
            # paragraph. Retain the strongest authored boundary exactly once.
            kind='break' if any(s.kind=='break' for s in boundaries) else 'poetry'
            if result:
                previous=result[-1]
                result[-1]=Segment(previous.text.rstrip(),previous.kind,previous.styles)
            result.append(Segment('\n\n' if kind=='break' else '\n',kind,('poetry',) if kind=='poetry' else ()))
            if next_segment is not None:next_segment=Segment(next_segment.text.lstrip(),next_segment.kind,next_segment.styles)
        else:
            for item in pending:
                if result and (result[-1].kind,result[-1].styles)==(item.kind,item.styles):
                    previous=result.pop();item=Segment(previous.text+item.text,item.kind,item.styles)
                result.append(item)
        pending.clear()
        return next_segment
    for segment in segments:
        if segment.kind in {'break','poetry'} or segment.text.isspace():pending.append(segment);continue
        segment=flush(segment)
        if result and (result[-1].kind,result[-1].styles)==(segment.kind,segment.styles):
            previous=result.pop();segment=Segment(previous.text+segment.text,segment.kind,segment.styles)
        result.append(segment)
    flush()
    return tuple(s for s in result if s.text) or (Segment(plain),)
