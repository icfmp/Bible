"""Direct native formatting over the existing, lossless Markdown note buffer.

Only presentation tags change while typing. Hidden delimiters stay in the
buffer for exact persistence, undo and old backups; no HTML or URL is executed.
"""
import re
from bisect import bisect_left
from dataclasses import replace
from gi.repository import Gtk,Gdk
from .markdown import markup_regions
from .note_preview import NotePreview
from .i18n import tr


class NoteTextView(NotePreview):
    def __init__(self,owner,system,navigation_guard):
        super().__init__(owner=owner,system=system,navigation_guard=navigation_guard)
        self.set_editable(True);self.set_cursor_visible(True)
        self.set_left_margin(16);self.set_right_margin(16);self.set_pixels_inside_wrap(5)
        buffer=self.get_buffer();buffer.set_enable_undo(True)
        self._original_source='';self._original_display=''
        self.tags['hidden']=buffer.create_tag('note-markup',invisible=True)
        buffer.connect('changed',self.decorate)
        keys=Gtk.EventControllerKey()
        def shortcut(_,key,code,state):
            if state&Gdk.ModifierType.CONTROL_MASK and key in (Gdk.KEY_b,Gdk.KEY_B,Gdk.KEY_i,Gdk.KEY_I):
                self.format('bold' if key in (Gdk.KEY_b,Gdk.KEY_B) else 'italic');return True
            return False
        keys.connect('key-pressed',shortcut);self.add_controller(keys)

    def do_focus(self,direction):return Gtk.TextView.do_focus(self,direction)

    def pressed(self,gesture,count,x,y):
        if gesture.get_current_event_state()&Gdk.ModifierType.CONTROL_MASK:
            NotePreview.pressed(self,gesture,count,x,y)
        else:self._pressed=None

    def motion(self,controller,x,y):
        active=controller.get_current_event_state()&Gdk.ModifierType.CONTROL_MASK
        self.set_cursor_from_name('pointer' if active and self.at_point(x,y) is not None else 'text')

    def key_pressed(self,controller,key,code,state):
        if key in (Gdk.KEY_Return,Gdk.KEY_KP_Enter) and state&Gdk.ModifierType.CONTROL_MASK:
            index=self.at_offset(self.get_buffer().get_iter_at_mark(self.get_buffer().get_insert()).get_offset())
            if index is not None:self.activate(index);return True
        return False

    def source(self):
        buffer=self.get_buffer();value=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True)
        return self._original_source if value==self._original_display else value

    def set_source(self,source):
        self._original_source=source
        self._original_display=re.sub(r'(?m)^([ \t]*)[-*] ',r'\1• ',source)
        self.get_buffer().set_text(self._original_display)

    def decorate(self,*_):
        preview=self.owner.reference_preview.popover
        if preview and getattr(preview,'_note_preview',None) is self:self.owner.reference_preview.dismiss()
        buffer=self.get_buffer();start,end=buffer.get_bounds()
        for tag in self.tags.values():buffer.remove_tag(tag,start,end)
        buffer.remove_tag(self.citation_tag,start,end)
        source=buffer.get_text(*buffer.get_bounds(),True);regions=list(markup_regions(source))
        for kind,first,last in regions:
            buffer.apply_tag(self.tags[kind],buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(last))
        hidden={index for kind,first,last in regions if kind=='hidden' for index in range(first,last)}
        positions=[index for index in range(len(source)) if index not in hidden]
        visible=''.join(source[index] for index in positions)
        links=[('link',bisect_left(positions,first),bisect_left(positions,last))
               for kind,first,last in regions if kind=='link']
        from .citations import citations
        try:self.citations=[replace(c,begin=positions[c.begin],finish=positions[c.finish-1]+1)
                            for c in citations(visible,self.system,links)]
        except ValueError:self.citations=[]  # Retain notes whose numbering system is unavailable.
        for c in self.citations:
            buffer.apply_tag(self.citation_tag,buffer.get_iter_at_offset(c.begin),buffer.get_iter_at_offset(c.finish))
        self.set_tooltip_text(tr('Ctrl+click or Ctrl+Enter to preview a Bible reference.') if self.citations else None)

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
