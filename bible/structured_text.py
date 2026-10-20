"""Conservative SWORD markup extraction; no HTML execution or invented headings."""
from dataclasses import dataclass
from html.parser import HTMLParser
import re


@dataclass(frozen=True)
class Segment:
    text: str
    kind: str = 'text'


class SourceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.segments = []
        self.hidden = 0
        self.heading = 0
        self.divisions = []

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in {'script','style','note'}:self.hidden += 1
        if self.hidden:return
        if tag in {'title','h1','h2','h3','h4'}:
            self.heading += 1
        if tag == 'div':
            paragraph = attrs.get('type') in {'paragraph', 'x-p'}
            self.divisions.append(paragraph)
        else:
            paragraph = tag in {'p', 'lg'}
        if paragraph or (tag=='milestone' and attrs.get('type') in {'x-p','paragraph'}):
            self.segments.append(Segment('\n\n','break'))
        elif tag in {'l','lb','br'}:self.segments.append(Segment('\n','poetry'))

    def handle_endtag(self,tag):
        if tag in {'script','style','note'}:self.hidden=max(0,self.hidden-1);return
        if self.hidden:return
        if tag in {'title','h1','h2','h3','h4'}:
            self.heading=max(0,self.heading-1);self.segments.append(Segment('\n','break'))
        paragraph = self.divisions.pop() if tag == 'div' and self.divisions else tag in {'p','lg'}
        if paragraph:self.segments.append(Segment('\n\n','break'))

    def handle_startendtag(self,tag,attrs):
        # Empty ThML p and OSIS start/end milestones each mark a boundary.
        # Do not synthesize a second end event, or retain an empty title/note.
        self.handle_starttag(tag,attrs)
        if tag in {'note','script','style','title','h1','h2','h3','h4','div'}:
            self.handle_endtag(tag)

    def handle_data(self,text):
        if not self.hidden:self.segments.append(Segment(text,'heading' if self.heading else 'text'))


def extract(raw,plain,source_type):
    """Use structure only when its body words agree with SWORD's own plain text.

    A mismatch falls back to exact plain text: unknown markup cannot rewrite the
    resource or leak notes/commands into a purported faithful Bible rendering.
    """
    if source_type not in {'OSIS','ThML'}:return (Segment(plain),)
    parser=SourceParser()
    try:parser.feed(raw);parser.close()
    except Exception:return (Segment(plain),)
    body=''.join(s.text for s in parser.segments if s.kind=='text')
    normalize=lambda v: re.sub(r'\s+','',v)
    if normalize(body)!=normalize(plain):
        # Some StripText filters retain editorial titles. Do not guess which
        # words belong to verses; use the original plain output in that case.
        return (Segment(plain),)
    result = []
    for segment in parser.segments:
        if segment.kind in {'break','poetry'} and result and result[-1].kind in {'break','poetry'}:
            previous = result.pop()
            segment = Segment('\n\n' if 'break' in {previous.kind,segment.kind} else '\n',
                              'break' if 'break' in {previous.kind,segment.kind} else 'poetry')
        result.append(segment)
    return tuple(result) or (Segment(plain),)
