"""Deterministic native-Pango pagination with canonical character anchors.

Offsets count non-whitespace Unicode characters inside a source verse/entry.
Pango byte offsets are converted before slicing Python text; pages partition the
entire display document exactly, including paragraph separators and headings.
"""
from dataclasses import dataclass, field
import unicodedata
import gi

gi.require_version('Pango','1.0')
from gi.repository import Pango
from .reading_style import SPACING


@dataclass(frozen=True)
class Anchor:
    reference: str
    offset: int = 0
    at_body: bool = False
    spacing: int = 0


@dataclass(frozen=True)
class PassageSpan:
    reference: str
    start: int
    body: int
    end: int


@dataclass(frozen=True)
class StyleSpan:
    kind: str
    start: int
    end: int


@dataclass
class Document:
    key: object
    text: str
    spans: tuple[PassageSpan,...]
    styles: tuple[StyleSpan,...] = ()

    def anchor(self,offset):
        if not self.spans:return Anchor('',0)
        candidates=[span for span in self.spans if span.start<=offset]
        span=candidates[-1] if candidates else self.spans[0]
        body=self.text[span.body:min(span.end,max(span.body,offset))]
        anchor=Anchor(span.reference,sum(not c.isspace() for c in body),offset>=span.body)
        if anchor.at_body:
            from dataclasses import replace
            anchor=replace(anchor,spacing=min(span.end,offset)-self.locate(anchor))
        else:
            # Heading/number selections have no body-character offset. Keep
            # their distinct positions in the presentation prefix as well.
            from dataclasses import replace
            anchor=replace(anchor,spacing=max(0,offset-span.start))
        return anchor

    def locate(self,anchor):
        span=next((s for s in self.spans if s.reference==anchor.reference),self.spans[0])
        if anchor.offset==0 and not anchor.at_body:return min(span.body,span.start+anchor.spacing)
        remaining=anchor.offset
        for pos in range(span.body,span.end):
            if not self.text[pos].isspace():
                if remaining<=0:return max(span.body,min(span.end,pos+anchor.spacing))
                remaining-=1
        return max(span.body,min(span.end,span.end+anchor.spacing))

    def selected_passage(self,start,end):
        spans=[s for s in self.spans if s.body<end and s.end>start]
        return (spans[0].reference,spans[-1].reference) if spans else None


@dataclass(frozen=True)
class Page:
    start: int
    end: int


@dataclass
class PagePlan:
    document: Document
    pages: tuple[Page,...]

    def containing(self,offset):
        return next((i for i,p in enumerate(self.pages) if p.start<=offset<p.end),max(0,len(self.pages)-1))


def attributes(document,start=0,end=None):
    end=len(document.text) if end is None else end
    values=Pango.AttrList()
    for span in document.styles:
        left,right=max(start,span.start),min(end,span.end)
        if right<=left:continue
        if span.kind in ('heading','chapter'):
            attrs=[Pango.attr_weight_new(Pango.Weight.BOLD),Pango.attr_scale_new(1.35 if span.kind=='chapter' else 1.12)]
        elif span.kind=='number':attrs=[Pango.attr_scale_new(.65),Pango.attr_rise_new(6000)]
        else:continue
        for attr in attrs:
            attr.start_index=len(document.text[start:left].encode())
            attr.end_index=len(document.text[start:right].encode())
            values.insert(attr)
    return values


def paginate(widget,document,preferences,width,height,anchor=None):
    """Measure real shaped lines. No verse/chapter-length estimates or columns."""
    split=document.locate(anchor) if anchor else 0
    while split and split<len(document.text) and unicodedata.combining(document.text[split]):split-=1
    boundaries=[(0,split),(split,len(document.text))] if split else [(0,len(document.text))]
    pages=[]
    for first,last in boundaries:
        if first==last:continue
        text=document.text[first:last]
        layout=widget.create_pango_layout(text)
        layout.set_font_description(Pango.FontDescription(f'{preferences.font} {preferences.size}'))
        layout.set_width(max(20,int(width))*Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_spacing(SPACING[preferences.line_spacing]*Pango.SCALE)
        layout.set_attributes(attributes(document,first,last))
        raw=text.encode();byte_to_char={0:0};n=0
        for i,char in enumerate(text):n+=len(char.encode());byte_to_char[n]=i+1
        iterator=layout.get_iter();lines=[]
        while True:
            line=iterator.get_line_readonly();_,logical=iterator.get_line_extents()
            lines.append((byte_to_char[line.start_index],logical.y/Pango.SCALE,logical.height/Pango.SCALE))
            if not iterator.next_line():break
        # A trailing newline creates an additional GTK paragraph line in a page
        # buffer. Reserve a shaped font line, including paragraph spacing, so
        # separators remain copied verbatim without clipping the last glyph.
        metrics=widget.get_pango_context().get_metrics(layout.get_font_description(),None)
        reserve=metrics.get_height()/Pango.SCALE+2*SPACING[preferences.line_spacing]
        page_start=first;top=lines[0][1]
        for offset,y,line_height in lines:
            absolute=first+offset
            if y+line_height-top>max(1,height-reserve-2) and absolute>page_start:
                pages.append(Page(page_start,absolute));page_start=absolute;top=y
        if page_start<last:pages.append(Page(page_start,last))
    if not pages:pages=[Page(0,0)]
    assert ''.join(document.text[p.start:p.end] for p in pages)==document.text
    return PagePlan(document,tuple(pages))
