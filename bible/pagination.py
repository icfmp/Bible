"""Deterministic native-Pango pagination with canonical character anchors.

Offsets count non-whitespace Unicode characters inside a source verse/entry.
Pango byte offsets are converted before slicing Python text; pages partition the
entire display document exactly, including paragraph separators and headings.
"""
from dataclasses import dataclass
from bisect import bisect_right
import unicodedata
import gi

gi.require_version('Pango','1.0')
from gi.repository import Pango
from .reading_metrics import SPACING
from .preparation import checkpoint


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
    copy_text: str | None = None

    def copy(self, start, end):
        text=self.copy_text if self.copy_text is not None else self.text
        hidden=sorted((max(start,s.start),min(end,s.end)) for s in self.styles
                      if s.kind=='hidden' and s.end>start and s.start<end)
        if not hidden:return text[start:end]
        pieces=[];position=start
        for first,last in hidden:
            if first>position:pieces.append(text[position:first])
            position=max(position,last)
        pieces.append(text[position:end]);return ''.join(pieces)

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


def attributes(document,start=0,end=None,*,context=None,preferences=None,cancelled=None):
    end=len(document.text) if end is None else end
    values=Pango.AttrList()
    # Encode each intervening slice once, rather than the entire prefix twice
    # for every style in a whole book (quadratic in the book's length).
    positions={start,end}
    for span in document.styles:
        if span.end>start and span.start<end and span.kind!='verse-start':
            positions.update((max(start,span.start),min(end,span.end)))
    byte_offsets={};previous=start;offset=0
    for position in sorted(positions):
        checkpoint(cancelled)
        offset+=len(document.text[previous:position].encode())
        byte_offsets[position]=offset;previous=position
    rise=None
    for span in document.styles:
        checkpoint(cancelled)
        left,right=max(start,span.start),min(end,span.end)
        if right<=left:continue
        if span.kind in ('heading','chapter'):
            attrs=[Pango.attr_weight_new(Pango.Weight.BOLD),Pango.attr_scale_new(1.35 if span.kind=='chapter' else 1.12)]
        elif span.kind=='number':
            from .verse_typography import NUMBER_SCALE, number_rise
            if rise is None:rise=number_rise(context,preferences) if context and preferences else 0
            attrs=[Pango.attr_scale_new(NUMBER_SCALE),Pango.attr_rise_new(rise)]
        # Nonbreaking presentation spaces already bind marker and first word.
        # Thousands of ALLOW_BREAKS ranges make whole-book Pango shaping
        # disproportionately slow; retain these spans for partition boundaries.
        elif span.kind=='verse-start':continue
        elif span.kind=='italic':attrs=[Pango.attr_style_new(Pango.Style.ITALIC)]
        elif span.kind=='bold':attrs=[Pango.attr_weight_new(Pango.Weight.BOLD)]
        elif span.kind=='small-caps':attrs=[Pango.attr_variant_new(Pango.Variant.SMALL_CAPS)]
        elif span.kind=='hidden':
            rectangle=Pango.Rectangle()
            attrs=[Pango.attr_shape_new(rectangle,rectangle)]
        else:continue
        for attr in attrs:
            attr.start_index=byte_offsets[left]
            attr.end_index=byte_offsets[right]
            values.insert(attr)
    return values


def heading_groups(document):
    """Keep consecutive source/chapter headings with the next body character.

    Offsets are metadata only: source text, copy text and canonical spans stay
    untouched. Include all intervening blank lines and consecutive headings.
    """
    groups=[]
    for style in sorted(document.styles,key=lambda s:s.start):
        if style.kind not in {'heading','chapter'}:continue
        start,end=style.start,style.end
        if groups and not document.text[groups[-1][1]:start].strip():
            start=groups.pop()[0]
        groups.append((start,end))
    result=[]
    for start,end in groups:
        while end<len(document.text) and document.text[end].isspace():end+=1
        if end<len(document.text):result.append((start,end+1))
    return result


def paginate(widget,document,preferences,width,height,anchor=None,*,cancelled=None):
    """Measure real shaped lines. No verse/chapter-length estimates or columns."""
    checkpoint(cancelled)
    groups=heading_groups(document)
    split=document.locate(anchor) if anchor else 0
    for start,end in groups:
        if start<split<end:split=start
    for style in document.styles:
        if style.kind=='verse-start' and style.start<split<style.end:split=style.start
    for start,end in groups:
        if start<split<end:split=start
    while split and split<len(document.text) and unicodedata.combining(document.text[split]):split-=1
    boundaries=[(0,split),(split,len(document.text))] if split else [(0,len(document.text))]
    pages=[]
    for first,last in boundaries:
        checkpoint(cancelled)
        if first==last:continue
        text=document.text[first:last]
        layout=widget.create_pango_layout(text)
        layout.set_font_description(Pango.FontDescription(f'{preferences.font} {preferences.size}'))
        layout.set_width(max(20,int(width))*Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_spacing(SPACING[preferences.line_spacing]*Pango.SCALE)
        layout.set_attributes(attributes(document,first,last,context=widget.get_pango_context(),preferences=preferences,
                                         cancelled=cancelled))
        byte_to_char={0:0};n=0
        for i,char in enumerate(text):
            if i%2048==0:checkpoint(cancelled)
            n+=len(char.encode());byte_to_char[n]=i+1
        checkpoint(cancelled)
        iterator=layout.get_iter();lines=[]
        while True:
            checkpoint(cancelled)
            line=iterator.get_line_readonly();_,logical=iterator.get_line_extents()
            lines.append((byte_to_char[line.start_index],logical.y/Pango.SCALE,logical.height/Pango.SCALE))
            if not iterator.next_line():break
        # A trailing newline creates an additional GTK paragraph line in a page
        # buffer. Reserve a shaped font line, including paragraph spacing, so
        # separators remain copied verbatim without clipping the last glyph.
        metrics=widget.get_pango_context().get_metrics(layout.get_font_description(),None)
        reserve=metrics.get_height()/Pango.SCALE+2*SPACING[preferences.line_spacing]
        capacity=max(1,height-reserve-2)
        starts=[first+line[0] for line in lines]
        # Treat a heading and the first shaped body line as one block when it
        # fits. Oversized titles still make progress one line at a time.
        protected=list(groups)+[(s.start,s.end) for s in document.styles if s.kind=='verse-start']
        intervals=[]
        for start,end in protected:
            if start<first or end>last:continue
            begin=bisect_right(starts,start)-1;finish=bisect_right(starts,end-1)-1
            if lines[finish][1]+lines[finish][2]-lines[begin][1]<=capacity:
                # Ranges may share the heading's first body line. Merge them
                # only if the combined group can still fit on an empty page.
                overlaps=[(a,b) for a,b in intervals if a<=finish and b>=begin]
                left=min([begin]+[a for a,b in overlaps]);right=max([finish]+[b for a,b in overlaps])
                if lines[right][1]+lines[right][2]-lines[left][1]>capacity:continue
                intervals=[item for item in intervals if item not in overlaps]
                intervals.append((left,right))
        blocks=dict(intervals)
        page_start=first;top=lines[0][1];index=0
        while index<len(lines):
            checkpoint(cancelled)
            finish=blocks.get(index,index)
            offset,y,_=lines[index];bottom=lines[finish][1]+lines[finish][2]
            absolute=first+offset
            if bottom-top>capacity and absolute>page_start:
                pages.append(Page(page_start,absolute));page_start=absolute;top=y
            index=finish+1
        if page_start<last:pages.append(Page(page_start,last))
    if not pages:pages=[Page(0,0)]
    checkpoint(cancelled)
    assert pages[0].start==0 and pages[-1].end==len(document.text)
    assert all(a.end==b.start for a,b in zip(pages,pages[1:]))
    return PagePlan(document,tuple(pages))
