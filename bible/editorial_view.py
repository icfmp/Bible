"""Lazy, read-only source notes and introductions; no timers or personal data."""
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Adw,Gtk
from .i18n import tr
from .youversion_content import tag
from xml.etree.ElementTree import ParseError


def text_view(label):
    view=Gtk.TextView(editable=False,cursor_visible=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,
        left_margin=20,right_margin=20,top_margin=16,bottom_margin=20)
    view.add_css_class('study-reader')
    view.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
    return view


def introduction_text(root):
    """Retain block breaks, without inserting spaces inside inline words."""
    parts=[]
    def visit(node):
        name=tag(node)
        block=name in ('div','p','title','l','item')
        if block and parts and not parts[-1].endswith('\n'):parts.append('\n\n')
        if name=='lb':parts.append('\n')
        if node.text:parts.append(node.text)
        for child in node:
            visit(child)
            if child.tail:parts.append(child.tail)
        if block:parts.append('\n\n')
    visit(root)
    return ''.join(parts).strip()


def show_introduction(parent,reader,book):
    window=Adw.Window(transient_for=parent,modal=True,title=tr('Book introduction'),
                      default_width=600,default_height=600)
    window.set_size_request(280,240)
    layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    header=Adw.HeaderBar();header.set_title_widget(Adw.WindowTitle(title=tr('Book introduction')))
    layout.append(header)
    view=text_view('Book introduction');scroll=Gtk.ScrolledWindow(vexpand=True)
    scroll.set_child(view);layout.append(scroll)
    try:
        root=reader.introduction(book)
        text=introduction_text(root) if root is not None else tr('No introduction supplied by this edition.')
    except (ValueError,RuntimeError,ParseError):text=tr('Unable to read this passage.')
    view.get_buffer().set_text(text)
    window.set_content(layout);window.present()
    return window


class TranslationNotes(Gtk.ScrolledWindow):
    def __init__(self,owner):
        super().__init__(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.owner=owner;self.stamp=None
        self.text=text_view('Translation notes');self.set_child(self.text)
        self.connect('map',lambda *_:self.refresh())

    def refresh(self,force=False):
        if self.owner.closed or not self.get_mapped() or not self.owner.split.get_show_sidebar():return
        tab=self.owner.active_tab
        if not tab or not tab.reader:
            self.stamp=None;self.text.get_buffer().set_text(tr('Choose a passage'));return
        chapter=tab.state.reference.rsplit('.',1)[0]
        stamp=(id(tab.reader),chapter)
        if stamp==self.stamp and not force:return
        self.stamp=stamp
        try:
            notes=tab.reader.editorial_notes(tab.state.reference)
            resource=self.owner.library.resource(tab.state.resource)
            text=resource.description+' · '+chapter+'\n\n'
            text+='\n\n'.join((note.locator or note.reference)+'\n'+note.text for note in notes) if notes else tr('No translation notes in this chapter.')
        except (ValueError,RuntimeError,ParseError):text=tr('Translation notes unavailable.')
        self.text.get_buffer().set_text(text)
