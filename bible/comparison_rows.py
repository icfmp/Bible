"""Native two-text-view layout with one adjustment and shared wrapped rows."""
from gi.repository import Gtk
from .comparison_layout import correspondences, row_document
from .paged_sources import BiblePages
from .bible_render import render
from .i18n import tr
from .reference_resolution import resolve,_span
from .pagination import Document
from dataclasses import replace


class ComparisonRows:
    def __init__(self,tab):
        self.tab=tab;self.signature=None;self.tags=[[],[]];self.bounds=[(),()]
        self.bodies=[(),()];self.bottom_tags=[None,None]
        self.geometry=None;self.settling=0;self.padding=[[],[]]

    def build(self,chapter):
        tab=self.tab;left=tab.reader;right=tab._comparison_reader
        signature=(id(left),id(right),tab.current.reference,chapter.reference,tuple(vars(tab.preferences).items()))
        if signature==self.signature:return
        primary=BiblePages(left,None).document(tab.current.reference,tab.preferences)
        chapters={chapter.reference}
        for span in primary.spans:
            for reference in span.members:
                mapped=resolve(reference,left.versification,right,require_entry=False)
                chapters.update(ref.rsplit('.',1)[0] for ref in _span(mapped.start,mapped.end,right.versification))
        key=left.key(tab.current.reference+'.1')
        low=key.getIndex();key.setVerse(key.getVerseMax());high=key.getIndex()
        pieces=[];copies=[];spans=[];styles=[];offset=0
        for name in sorted(chapters,key=lambda ref:right.key(ref+'.1').getIndex()):
            document=BiblePages(right,None).document(name,tab.preferences)
            for index,span in enumerate(document.spans):
                mapped=[resolve(ref,right.versification,left,require_entry=False) for ref in span.members]
                if not any(left.key(m.end).getIndex()>=low and left.key(m.start).getIndex()<=high for m in mapped):continue
                end=document.spans[index+1].start if index+1<len(document.spans) else len(document.text)
                pieces.append(document.text[span.start:end]);copies.append((document.copy_text or document.text)[span.start:end])
                spans.append(replace(span,start=offset,body=offset+span.body-span.start,end=offset+span.end-span.start))
                for style in document.styles:
                    a,b=max(span.start,style.start),min(end,style.end)
                    if b>a:styles.append(replace(style,start=offset+a-span.start,end=offset+b-span.start))
                offset+=end-span.start
        secondary=Document(tuple(chapters),''.join(pieces),tuple(spans),tuple(styles),''.join(copies))
        documents=(primary,secondary)
        rows=correspondences(left,right,*(tuple(ref for s in doc.spans for ref in s.members) for doc in documents),
                             linked=tuple(tuple(s.members for s in doc.spans if s.aliases) for doc in documents))
        self.rows=rows
        tab.comparison_text.set_top_margin(tab.text.get_top_margin())
        tab.comparison_text.set_bottom_margin(tab.text.get_bottom_margin())
        for side,view,reader,source in ((0,tab.text,left,primary),(1,tab.comparison_text,right,secondary)):
            buffer=view.get_buffer()
            anchors=[getattr(view,'_bible_copy_source',(source,0))[0].anchor(i.get_offset()) for i in buffer.get_selection_bounds()]
            doc,self.bounds[side]=row_document(source,rows,side,tr('No verse in this edition.'))
            values=render(view,reader,tab.current if side==0 else chapter,tab.preferences,doc)
            if hasattr(values[0],'source_shift'):
                shift=values[0].source_shift
                self.bounds[side]=tuple((shift(a),shift(b)) for a,b in self.bounds[side])
            if side==0:tab._document,tab._verse_offsets,tab._verse_ranges,tab._marker_ends=values
            else:tab._comparison_document,tab._comparison_offsets,tab._comparison_ranges,tab._comparison_markers=values
            for tag in self.tags[side]:buffer.get_tag_table().remove(tag)
            if self.bottom_tags[side]:buffer.get_tag_table().remove(self.bottom_tags[side])
            self.tags[side]=[];self.padding[side]=[0]*len(rows)
            markers=values[3]
            self.bodies[side]=tuple(next((markers[ref] for ref in (row.primary if side==0 else row.secondary)
                                         if ref in markers),start) for row,(start,end) in zip(rows,self.bounds[side]))
            for body in self.bodies[side]:
                tag=buffer.create_tag(None,pixels_above_lines=0)
                # Align the verse body, preserving any preceding source titles.
                # GTK paragraph padding never changes text or copy offsets.
                first=buffer.get_iter_at_offset(body);first.set_line_offset(0)
                end=first.copy();end.forward_line()
                buffer.apply_tag(tag,first,end)
                self.tags[side].append(tag)
            self.bottom_tags[side]=buffer.create_tag(None,pixels_below_lines=0)
            last=buffer.get_iter_at_offset(max(0,buffer.get_char_count()-1));last.set_line_offset(0)
            buffer.apply_tag(self.bottom_tags[side],last,buffer.get_end_iter())
            if anchors and all(any(a.reference in s.members for s in doc.spans) for a in anchors):
                buffer.select_range(*(buffer.get_iter_at_offset(doc.locate(a)) for a in anchors))
        self.signature=signature;self.geometry=None;self.settling=8
        tab.comparison_scroll.set_vadjustment(tab.scroll.get_vadjustment())
        tab.comparison_scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.EXTERNAL)
        tab._shared_comparison=True
        tab.update_highlights()

    def layout(self):
        tab=self.tab
        if not getattr(tab,'_shared_comparison',False):return
        geometry=(tab.text.get_width(),tab.comparison_text.get_width(),tab.preferences.size,
                  tab.preferences.font,tab.preferences.line_spacing)
        if geometry!=self.geometry:
            self.geometry=geometry;self.settling=8
            for side in (0,1):
                self.padding[side]=[0]*len(self.rows)
                for tag in self.tags[side]:tag.props.pixels_above_lines=0
                self.bottom_tags[side].props.pixels_below_lines=0
        if not self.settling:return
        self.settling-=1
        if self.settling:return
        positions=[];ends=[]
        for side,view in enumerate((tab.text,tab.comparison_text)):
            buffer=view.get_buffer()
            positions.append([view.get_iter_location(buffer.get_iter_at_offset(body)).y for body in self.bodies[side]])
            last,height=view.get_line_yrange(buffer.get_iter_at_offset(max(0,buffer.get_char_count()-1)))
            ends.append(last+height)
        # Read native geometry before changing any tags. Cumulative paragraph
        # padding aligns corresponding bodies even when headings/poetry differ.
        added=[0,0]
        for i in range(len(self.rows)):
            target=max(positions[side][i]+added[side] for side in (0,1))
            for side in (0,1):
                padding=target-positions[side][i]-added[side]
                self.padding[side][i]=padding
                added[side]+=padding
        end=max(ends[side]+added[side] for side in (0,1))
        for side in (0,1):
            for tag,padding in zip(self.tags[side],self.padding[side]):tag.props.pixels_above_lines=padding
            self.bottom_tags[side].props.pixels_below_lines=end-ends[side]-added[side]

    def leave(self):
        tab=self.tab
        if not getattr(tab,'_shared_comparison',False):return
        tab._shared_comparison=False;self.signature=None
        buffer=tab.text.get_buffer()
        selected=[tab._document.anchor(i.get_offset()) for i in buffer.get_selection_bounds()]
        tab.comparison_scroll.set_vadjustment(Gtk.Adjustment())
        tab.comparison_scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
        tab.render_chapter(tab.current)
        if selected:buffer.select_range(*(buffer.get_iter_at_offset(tab._document.locate(a)) for a in selected))
