"""Verified OSIS styling without changing legacy plain-body character offsets."""
from bisect import bisect_left
from html.parser import HTMLParser
import re


class InlineOSIS(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[];self.length=0;self.emphasis=[];self.stack=[];self.paragraphs=[]
        self.title=0;self.title_parts=[];self.titles=[];self.hidden=0

    def append(self,text):self.parts.append(text);self.length+=len(text)

    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag in {'script','style','note'}:self.hidden+=1;return
        if self.hidden:return
        if tag=='title':self.title+=1;return
        if self.title:return
        if tag=='hi':
            start=self.length;self.append('* ')
            self.stack.append((values.get('type',''),start,self.length))
        if tag in {'p','l','lb','br'} or (tag=='div' and values.get('type') in {'paragraph','x-p'}):
            self.paragraphs.append(self.length);self.append('\n\n')

    def handle_endtag(self,tag):
        if tag in {'script','style','note'}:self.hidden=max(0,self.hidden-1);return
        if self.hidden:return
        if tag=='title':
            self.title=max(0,self.title-1)
            if not self.title:
                value=''.join(self.title_parts).strip();self.title_parts=[]
                # Some SWORD OSIS titles contain entity-escaped inline tags.
                # Keep their words, never display or execute that markup.
                from .resource_details import PlainMetadata
                parser=PlainMetadata();parser.feed(value)
                value=''.join(parser.parts).strip()
                if value:self.titles.append(value)
            return
        if self.title:return
        if tag=='hi' and self.stack:
            kind,first,body=self.stack.pop();end=self.length;self.append(' *')
            self.emphasis.append((kind,first,body,end,self.length-1))

    def handle_data(self,text):
        if self.hidden:return
        if self.title:self.title_parts.append(text)
        else:self.append(text)


def format_entry(raw,plain,source_type):
    """Return same-length body, typed ranges and real source headings.

    SWORD OSISPlain inserts stars around hi elements. Validate the complete
    non-whitespace character sequence, including every generated/literal star,
    before hiding only verified decorations. Unknown conversions fall back.
    """
    if source_type!='OSIS' or len(raw)>2*1024*1024:return plain,(),()
    parser=InlineOSIS()
    try:parser.feed(raw);parser.close()
    except Exception:return plain,(),()
    expected=''.join(parser.parts)
    left=[i for i,c in enumerate(expected) if not c.isspace()]
    right=[i for i,c in enumerate(plain) if not c.isspace()]
    if ''.join(expected[i] for i in left)!=''.join(plain[i] for i in right):return plain,(),()
    mapping=dict(zip(left,right));styles=[];display=list(plain)
    for kind,first,body,end,last in parser.emphasis:
        for marker in [first,last]:
            actual=mapping[marker];styles.append(('hidden',actual,actual+1))
        content=right[bisect_left(left,body):bisect_left(left,end)]
        style={'italic':'italic','bold':'bold','super':'number','small-caps':'small-caps'}.get(kind)
        if content and style:styles.append((style,content[0],content[-1]+1))
    for boundary in parser.paragraphs:
        position=bisect_left(left,boundary)
        if not 0<position<len(right):continue
        first=right[position-1]+1 if position else 0
        last=right[position] if position<len(right) else len(plain)
        for index in range(first,min(last,first+2)):
            if display[index].isspace():display[index]='\n'
    return ''.join(display),tuple(styles),tuple(parser.titles)


def apply(view,styles,preferences,palette):
    from gi.repository import Pango
    from .verse_typography import configure
    buffer=view.get_buffer();table=buffer.get_tag_table()
    for kind,first,last in styles:
        name='source-'+kind;tag=table.lookup(name) or buffer.create_tag(name)
        if kind=='hidden':tag.props.invisible=True
        elif kind=='italic':tag.props.style=Pango.Style.ITALIC
        elif kind=='bold':tag.props.weight=700
        elif kind=='small-caps':tag.props.variant=Pango.Variant.SMALL_CAPS
        elif kind=='number':configure(tag,view,preferences,palette)
        elif kind=='heading':tag.props.weight=700;tag.props.scale=1.12
        buffer.apply_tag(tag,buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(last))
