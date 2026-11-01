"""Bounded native annotation previews using the existing inert Markdown renderer."""
from gi.repository import Gtk, Pango, GLib
from .markdown import render
from .citations import citations
from .i18n import tr


class AnnotationPreview(Gtk.Label):
    def __init__(self, owner, note, open_note):
        super().__init__(xalign=0, yalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR,
                         lines=3, ellipsize=Pango.EllipsizeMode.END, width_chars=1, max_width_chars=40)
        self.add_css_class('study-content')
        self.owner=owner;self.note=note;self.open_note=open_note
        text,spans=render(note.body)
        self.citations=citations(text,note.versification,spans)
        # A bounded preview is one paragraph: Pango's negative line limit is
        # otherwise applied separately to every Markdown paragraph. Offsets stay exact.
        text=text.replace('\n',' ').replace('\r',' ')
        cuts=sorted({0,len(text),*(n for _,a,b in spans for n in (a,b)),
                     *(n for c in self.citations for n in (c.begin,c.finish))})
        chunks=[]
        for first,last in zip(cuts,cuts[1:]):
            value=GLib.markup_escape_text(text[first:last])
            for kind,start,end in spans:
                if start<=first and last<=end:
                    tag={'bold':'b','italic':'i','link':'u'}[kind];value=f'<{tag}>{value}</{tag}>'
            for index,c in enumerate(self.citations):
                if c.begin<=first and last<=c.finish:value=f'<a href="bible-preview:{index}">{value}</a>'
            chunks.append(value)
        self.set_markup(''.join(chunks) if text else GLib.markup_escape_text(tr('Empty note')))
        self._link_activated=False
        self.connect('activate-link',self.preview_citation)
        click=Gtk.GestureClick(button=1)
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def pressed(gesture,count,x,y):
            self._link_activated=False
            if count==1 and not self.over_citation(x,y):gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        click.connect('pressed',pressed)
        click.connect('released',lambda _,count,x,y:open_note() if count==1 and not self._link_activated and not self.over_citation(x,y) else None)
        self.add_controller(click)
        self.set_tooltip_text(tr('Open note'))

    def over_citation(self,x,y):
        # get_current_uri() can retain the keyboard-focused link after the
        # pointer leaves it. Hit-test the actual click instead.
        left,top=self.get_layout_offsets()
        inside,index,_=self.get_layout().xy_to_index(int((x-left)*Pango.SCALE),int((y-top)*Pango.SCALE))
        if not inside:return False
        offset=len(self.get_text().encode()[:index].decode())
        return any(c.begin<=offset<c.finish for c in self.citations)

    def preview_citation(self, _, uri):
        if not uri.startswith('bible-preview:'):return True
        try:index=int(uri.split(':',1)[1]);citation=self.citations[index]
        except (ValueError,IndexError):return True
        self._link_activated=True
        return self.activate(index)

    def activate(self,index):
        if not 0<=index<len(self.citations):return True
        citation=self.citations[index]
        tab=self.owner.active_tab;reader=tab.reader if tab else None
        resource=tab.state.resource if reader else None
        self.owner.reference_preview.show(self,resource,reader,citation.start,citation.end,
                                         source_system=citation.system)
        return True
