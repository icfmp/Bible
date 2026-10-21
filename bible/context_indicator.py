"""Paint-only dotted study coverage; never selection, tags or saved highlights."""
import gi
gi.require_version('Graphene','1.0')
from gi.repository import Gdk, Graphene, Gtk
from .verse_typography import NUMBER_COLORS
from .reading_style import PALETTES


class ContextTextView(Gtk.TextView):
    def set_study_ranges(self, ranges):
        value=tuple(ranges)
        if value!=getattr(self,'study_ranges',()):
            self.study_ranges=value;self.queue_draw()

    def indicator_segments(self):
        ranges=getattr(self,'study_ranges',())
        if not ranges or not self.get_mapped():return []
        buffer=self.get_buffer();visible=self.get_visible_rect()
        _,first=self.get_iter_at_location(visible.x,visible.y)
        _,last=self.get_iter_at_location(visible.x+visible.width,visible.y+visible.height)
        self.backward_display_line_start(first);self.forward_display_line_end(last)
        low,high=first.get_offset(),min(buffer.get_char_count(),last.get_offset()+1)
        selection=buffer.get_selection_bounds()
        selected=tuple(i.get_offset() for i in selection)
        palette=getattr(self,'_reading_palette','white')
        neutral=NUMBER_COLORS[palette];rows=[]
        for start,end in ranges:
            iterator=buffer.get_iter_at_offset(max(start,low))
            while iterator.get_offset()<min(end,high):
                rect=self.get_iter_location(iterator)
                if rect.width:
                    x,y=self.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,rect.x,rect.y)
                    left,right=sorted((x,x+rect.width));bottom=y+rect.height
                    if bottom>0 and y<self.get_height():
                        color=neutral
                        if selected and selected[0]<=iterator.get_offset()<selected[1]:color=PALETTES[palette][4]
                        else:
                            for tag in iterator.get_tags():
                                if (tag.props.name or '').startswith('highlight-') and tag.props.foreground_set:
                                    color=tag.props.foreground_rgba.to_string()
                        row=next((r for r in rows if max(y,r[0])<min(bottom,r[1])),None)
                        if row is None:row=[y,bottom,[]];rows.append(row)
                        row[0]=min(row[0],y);row[1]=max(row[1],bottom)
                        row[2].append((left,right,color))
                if not iterator.forward_char():break
        segments=[]
        for _,bottom,intervals in rows:
            for left,right,color in sorted(intervals):
                y=bottom-.5+min(2,max(0,(self.get_pixels_inside_wrap()-1)/2))
                if segments and segments[-1][2:]==(y,color) and left<=segments[-1][1]+1:
                    previous=segments.pop();left=previous[0];right=max(right,previous[1])
                segments.append((left,right,y,color))
        return segments

    def do_snapshot(self, snapshot):
        Gtk.TextView.do_snapshot(self,snapshot)
        segments=self.indicator_segments()
        if not segments:return
        clip=Graphene.Rect();clip.init(0,0,self.get_width(),self.get_height())
        snapshot.push_clip(clip)
        for left,right,y,value in segments:
            color=Gdk.RGBA();color.parse(value)
            x=left
            while x<right:
                dot=Graphene.Rect();dot.init(x,y,min(1,right-x),1)
                snapshot.append_color(color,dot);x+=3
        snapshot.pop()
