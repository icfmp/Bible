"""Native two-text-view layout with one adjustment and shared wrapped rows."""
from gi.repository import Gtk
from .comparison_layout import correspondences, row_document
from .paged_sources import BiblePages
from .bible_render import render
from .i18n import tr


class ComparisonRows:
    def __init__(self,tab):
        self.tab=tab;self.signature=None;self.tags=[[],[]];self.bounds=[(),()]
        self.geometry=None;self.settling=0;self.padding=[[],[]]

    def build(self,chapter):
        tab=self.tab;left=tab.reader;right=tab._comparison_reader
        signature=(id(left),id(right),tab.current.reference,chapter.reference,tuple(vars(tab.preferences).items()))
        if signature==self.signature:return
        primary=BiblePages(left,None).document(tab.current.reference,tab.preferences)
        secondary=BiblePages(right,None).document(chapter.reference,tab.preferences)
        rows=correspondences(left,right,[s.reference for s in primary.spans],[s.reference for s in secondary.spans])
        self.rows=rows
        for side,view,reader,source in ((0,tab.text,left,primary),(1,tab.comparison_text,right,secondary)):
            buffer=view.get_buffer()
            anchors=[getattr(view,'_bible_copy_source',(source,0))[0].anchor(i.get_offset()) for i in buffer.get_selection_bounds()]
            doc,self.bounds[side]=row_document(source,rows,side,tr('No verse in this edition.'))
            values=render(view,reader,tab.current if side==0 else chapter,tab.preferences,doc)
            if side==0:tab._document,tab._verse_offsets,tab._verse_ranges,tab._marker_ends=values
            else:tab._comparison_document,tab._comparison_offsets,tab._comparison_ranges,tab._comparison_markers=values
            for tag in self.tags[side]:buffer.get_tag_table().remove(tag)
            self.tags[side]=[];self.padding[side]=[0]*len(rows)
            for start,end in self.bounds[side]:
                tag=buffer.create_tag(None,pixels_below_lines=0)
                # GTK paragraph properties are taken at the paragraph start,
                # not at its terminal newline. Preserve internal source breaks.
                last=buffer.get_iter_at_offset(max(start,end-1))
                last.set_line_offset(0)
                buffer.apply_tag(tag,last,buffer.get_iter_at_offset(end))
                self.tags[side].append(tag)
            if anchors and all(any(s.reference==a.reference for s in doc.spans) for a in anchors):
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
                for tag in self.tags[side]:tag.props.pixels_below_lines=0
        if not self.settling:return
        self.settling-=1
        if self.settling:return
        heights=[]
        for side,view in enumerate((tab.text,tab.comparison_text)):
            buffer=view.get_buffer();values=[]
            for i,(start,end) in enumerate(self.bounds[side]):
                y=view.get_iter_location(buffer.get_iter_at_offset(start)).y
                if i+1<len(self.bounds[side]):
                    next_y=view.get_iter_location(buffer.get_iter_at_offset(self.bounds[side][i+1][0])).y
                else:
                    last,height=view.get_line_yrange(buffer.get_iter_at_offset(max(start,end-1)))
                    next_y=last+height
                values.append(max(0,next_y-y))
            heights.append(values)
        for i in range(len(self.rows)):
            maximum=max(heights[0][i],heights[1][i])
            for side in (0,1):
                padding=maximum-heights[side][i]
                self.padding[side][i]=padding
                self.tags[side][i].props.pixels_below_lines=padding

    def leave(self):
        tab=self.tab
        if not getattr(tab,'_shared_comparison',False):return
        tab._shared_comparison=False;self.signature=None
        tab.comparison_scroll.set_vadjustment(Gtk.Adjustment())
        tab.comparison_scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
        tab.render_chapter(tab.current)
