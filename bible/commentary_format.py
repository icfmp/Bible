"""Verified OSIS styling without changing legacy plain-body character offsets."""
from bisect import bisect_left
from html.parser import HTMLParser
import re
from collections import defaultdict


class PreverseParts(HTMLParser):
    """Keep SWORD's preverse region separate from its stripped verse body."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.body=[];self.prefix=[];self.region=None;self.hidden=0

    def append(self,text):
        (self.prefix if self.region else self.body).append(text)

    def start(self,tag,attrs,raw,empty):
        values=dict(attrs)
        if not self.hidden and tag=='div':
            if values.get('subtype')=='x-preverse' and values.get('sid'):self.region=values['sid']
            if self.region and values.get('eid')==self.region:
                self.append(raw);self.region=None;return
        self.append(raw)
        if not empty and tag in {'script','style','note'}:self.hidden+=1

    def handle_starttag(self,tag,attrs):self.start(tag,attrs,self.get_starttag_text(),False)
    def handle_startendtag(self,tag,attrs):self.start(tag,attrs,self.get_starttag_text(),True)
    def handle_endtag(self,tag):
        self.append('</'+tag+'>')
        if tag in {'script','style','note'}:self.hidden=max(0,self.hidden-1)
    def handle_data(self,text):self.append(text)
    def handle_entityref(self,name):self.append('&'+name+';')
    def handle_charref(self,name):self.append('&#'+name+';')


def split_preverse(raw):
    parser=PreverseParts();parser.feed(raw);parser.close()
    return ''.join(parser.body),''.join(parser.prefix)


def preverse_layout(raw):
    """Real preverse prose/headings, outside legacy native body offsets."""
    if len(raw)>2*1024*1024:return '',(),0
    from .structured_text import SourceParser,checked_segments
    _,prefix=split_preverse(raw)
    parser=SourceParser();parser.feed(prefix);parser.close()
    native=''.join(s.text for s in parser.segments if s.kind=='text')
    parts=[];styles=[];offset=0;focus=0
    for segment in checked_segments(parser.segments,native):
        text=segment.text
        if segment.kind in ('heading','editorial'):
            # Same escaped-inline-title handling as InlineOSIS below.
            from .resource_details import PlainMetadata
            clean=PlainMetadata();clean.feed(text);text=''.join(clean.parts)
            if text.strip():
                styles.append((segment.kind,offset,offset+len(text)));focus=offset
        styles.extend((kind,offset,offset+len(text)) for kind in segment.styles if kind!='poetry')
        parts.append(text);offset+=len(text)
    return ''.join(parts),tuple(styles),focus


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

    SWORD OSISPlain inserts stars around hi elements. Validate source characters,
    literal stars and bounded generated markers before hiding decorations.
    Unknown conversions fall back to native text.
    """
    if source_type!='OSIS' or len(raw)>2*1024*1024:return plain,(),()
    parser=InlineOSIS()
    try:
        raw,_=split_preverse(raw)
        parser.feed(raw);parser.close()
    except Exception:return plain,(),()
    expected=''.join(parser.parts)
    generated={marker for _,first,_,_,last in parser.emphasis for marker in (first,last)}
    # Native OSISPlain has one suspension buffer for nested hi elements, so
    # their generated stars can collect at a different emphasis boundary.
    # Verify every source character and literal star; permit only the exact
    # number of generated decorations, at actual source emphasis boundaries.
    left=[i for i,c in enumerate(expected) if not c.isspace() and c!='*']
    right=[i for i,c in enumerate(plain) if not c.isspace() and c!='*']
    if ''.join(expected[i] for i in left)!=''.join(plain[i] for i in right):return plain,(),()
    literals=defaultdict(list);actual=defaultdict(list);boundaries=set();position=0
    for index,char in enumerate(expected):
        if char.isspace():continue
        if char=='*':
            if index in generated:boundaries.add(position)
            else:literals[position].append(index)
        else:position+=1
    position=0
    for index,char in enumerate(plain):
        if char.isspace():continue
        if char=='*':actual[position].append(index)
        else:position+=1
    if sum(map(len,actual.values()))!=sum(map(len,literals.values()))+len(generated):return plain,(),()
    mapping=dict(zip(left,right));hidden=[]
    for slot in actual.keys()|literals.keys():
        authored=literals[slot];native=actual[slot]
        if len(native)<len(authored) or len(native)>len(authored) and slot not in boundaries:return plain,(),()
        mapping.update(zip(authored,native))
        hidden.extend(native[len(authored):])
    left=sorted(mapping);right=[mapping[i] for i in left]
    styles=[('hidden',i,i+1) for i in hidden];display=list(plain)
    for kind,first,body,end,last in parser.emphasis:
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
        # Keep native visible-byte indices aligned with the buffer. GTK 4.20
        # can abort in pixel-to-iterator conversion with invisible inline tags.
        # Zero-scale source decorations have no ink/advance; Document.copy()
        # still omits precisely these verified generated markers.
        if kind=='hidden':tag.props.scale=0
        elif kind=='italic':tag.props.style=Pango.Style.ITALIC
        elif kind=='bold':tag.props.weight=700
        elif kind=='small-caps':tag.props.variant=Pango.Variant.SMALL_CAPS
        elif kind=='number':configure(tag,view,preferences,palette)
        elif kind=='superscript':configure(tag,view,preferences,palette)
        elif kind=='editorial':tag.props.scale=.9
        elif kind=='heading':tag.props.weight=700;tag.props.scale=1.12
        buffer.apply_tag(tag,buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(last))
