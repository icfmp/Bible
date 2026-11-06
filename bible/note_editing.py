"""Direct native formatting over the existing, lossless Markdown note buffer.

Only presentation tags change while typing. Hidden delimiters stay in the
buffer for exact persistence, undo and old backups; no HTML or URL is executed.
"""
import re
from gi.repository import Gtk,Pango,Gdk
from .markdown import markup_regions


class NoteTextView(Gtk.TextView):
    def __init__(self):
        super().__init__(wrap_mode=Gtk.WrapMode.WORD_CHAR,left_margin=16,right_margin=16,
            top_margin=12,bottom_margin=12,pixels_inside_wrap=5)
        buffer=self.get_buffer();buffer.set_enable_undo(True)
        self.tags={'hidden':buffer.create_tag('note-markup',invisible=True),
            'bold':buffer.create_tag('note-bold',weight=Pango.Weight.BOLD),
            'italic':buffer.create_tag('note-italic',style=Pango.Style.ITALIC),
            'link':buffer.create_tag('note-inert-link',underline=Pango.Underline.SINGLE)}
        buffer.connect('changed',self.decorate)
        keys=Gtk.EventControllerKey()
        def shortcut(_,key,code,state):
            if state&Gdk.ModifierType.CONTROL_MASK and key in (Gdk.KEY_b,Gdk.KEY_B,Gdk.KEY_i,Gdk.KEY_I):
                self.format('bold' if key in (Gdk.KEY_b,Gdk.KEY_B) else 'italic');return True
            return False
        keys.connect('key-pressed',shortcut);self.add_controller(keys)

    def source(self):
        buffer=self.get_buffer();return buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True)

    def decorate(self,*_):
        buffer=self.get_buffer();start,end=buffer.get_bounds()
        for tag in self.tags.values():buffer.remove_tag(tag,start,end)
        for kind,first,last in markup_regions(self.source()):
            buffer.apply_tag(self.tags[kind],buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(last))

    def format(self,kind):
        buffer=self.get_buffer();selection=buffer.get_selection_bounds()
        start,end=selection if selection else (buffer.get_iter_at_mark(buffer.get_insert()),)*2
        first,last=start.get_offset(),end.get_offset();source=self.source()
        buffer.begin_user_action()
        if kind in ('bold','italic'):
            marker='**' if kind=='bold' else '*';width=len(marker)
            active=start.has_tag(self.tags[kind])
            remove=active and first>=width and source[first-width:first]==marker and source[last:last+width]==marker
            if remove:
                buffer.delete(buffer.get_iter_at_offset(last),buffer.get_iter_at_offset(last+width))
                buffer.delete(buffer.get_iter_at_offset(first-width),buffer.get_iter_at_offset(first))
                first-=width;last-=width
            else:
                buffer.insert(buffer.get_iter_at_offset(last),marker)
                buffer.insert(buffer.get_iter_at_offset(first),marker);first+=width;last+=width
        else:
            first=source.rfind('\n',0,first)+1
            finish=source.find('\n',max(first,last-1));last=len(source) if finish<0 else finish
            lines=source[first:last].split('\n')
            formatted='\n'.join(('• ' if kind=='bullet' else str(index+1)+'. ')+
                re.sub(r'^(?:[-*•] |[0-9]+\. )','',line) for index,line in enumerate(lines))
            buffer.delete(buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(last))
            buffer.insert(buffer.get_iter_at_offset(first),formatted);last=first+len(formatted)
        buffer.end_user_action()
        if selection:buffer.select_range(buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(last))
        else:buffer.place_cursor(buffer.get_iter_at_offset(last))
        self.grab_focus()
