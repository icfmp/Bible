"""Lazy, read-only source notes and introductions; no timers or personal data."""
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Adw,Gtk,Pango
from .i18n import tr
from .youversion_content import tag
from xml.etree.ElementTree import ParseError
import re


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
        block=name in ('div','p','title','l','item','table','row')
        if block and parts and not parts[-1].endswith('\n'):parts.append('\n\n')
        if name=='lb':parts.append('\n')
        if name=='cell' and parts and not parts[-1].endswith(('\n','\t')):parts.append('\t')
        if node.text:parts.append(node.text)
        for child in node:
            visit(child)
            if child.tail:parts.append(child.tail)
        if block:parts.append('\n\n')
    visit(root)
    # Native OSIS wraps introduction paragraphs in nested block divisions.
    # Their boundaries describe one paragraph break, not stacked blank lines.
    return re.sub(r'\n(?:[ \t\r]*\n)+','\n\n',''.join(parts)).strip()


def fill_introduction(view,root):
    """Apply native source styles; GTK marks preserve offsets during whitespace cleanup."""
    buffer=view.get_buffer();buffer.set_text('')
    for name,properties in (
            ('intro-heading',dict(weight=Pango.Weight.BOLD,scale=1.15,pixels_above_lines=12,pixels_below_lines=6)),
            ('intro-bold',dict(weight=Pango.Weight.BOLD)),
            ('intro-italic',dict(style=Pango.Style.ITALIC)),
            ('intro-super',dict(rise=5*Pango.SCALE,scale=.8)),
            ('intro-list',dict(left_margin=16,indent=-8))):
        if not buffer.get_tag_table().lookup(name):buffer.create_tag(name,**properties)
    def append(text):
        if text:buffer.insert(buffer.get_end_iter(),text)
    def visit(node):
        name=tag(node)
        block=name in ('div','p','title','l','item','table','row')
        end=buffer.get_end_iter()
        if block and end.get_offset() and not buffer.props.text.endswith('\n'):append('\n\n')
        if name=='lb':append('\n')
        if name=='cell' and end.get_offset() and not buffer.props.text.endswith(('\n','\t')):append('\t')
        first=buffer.create_mark(None,buffer.get_end_iter(),True)
        append(node.text)
        for child in node:
            visit(child);append(child.tail)
        style=('intro-heading' if name=='title' else 'intro-list' if name=='item' else
               {'bold':'intro-bold','b':'intro-bold','italic':'intro-italic','i':'intro-italic',
                'super':'intro-super'}.get(node.attrib.get('type')) if name=='hi' else None)
        if style:buffer.apply_tag_by_name(style,buffer.get_iter_at_mark(first),buffer.get_end_iter())
        buffer.delete_mark(first)
        if block:append('\n\n')
    visit(root)
    # Same paragraph normalization as introduction_text(). Tags remain attached
    # to their actual source characters when redundant source whitespace is removed.
    raw=buffer.props.text
    for match in reversed(list(re.finditer(r'\n(?:[ \t\r]*\n)+',raw))):
        buffer.delete(buffer.get_iter_at_offset(match.start()+1),buffer.get_iter_at_offset(match.end()-1))
    text=buffer.props.text
    tail=len(text.rstrip());head=len(text)-len(text.lstrip())
    if tail<len(text):buffer.delete(buffer.get_iter_at_offset(tail),buffer.get_end_iter())
    if head:buffer.delete(buffer.get_start_iter(),buffer.get_iter_at_offset(min(head,buffer.get_char_count())))


def show_introduction(parent,reader,book):
    from .book_names import display_name
    from .i18n import LANGUAGE
    entry=next((item for item in reader.books if item.code==book),None)
    name=display_name(book,entry.name if entry else book,LANGUAGE)
    title=tr('Book introduction')+' · '+name
    window=Adw.Window(transient_for=parent,modal=True,title=title,default_width=600,default_height=600)
    window.set_size_request(280,240)
    layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    header=Adw.HeaderBar();header.set_title_widget(Adw.WindowTitle(title=name,subtitle=tr('Book introduction')))
    layout.append(header)
    view=text_view('Book introduction');view.set_pixels_below_lines(6)
    view.set_bottom_margin(32);scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
    clamp=Adw.Clamp(child=view,maximum_size=640,tightening_threshold=480,unit=Adw.LengthUnit.PX)
    scroll.set_child(clamp);layout.append(scroll)
    try:
        root=reader.introduction(book)
        if root is not None:fill_introduction(view,root)
        else:view.get_buffer().set_text(tr('No introduction supplied by this edition.'))
    except (ValueError,RuntimeError,ParseError):view.get_buffer().set_text(tr('Unable to read this passage.'))
    window.text=view;window.source_document=root if 'root' in locals() else None
    window.set_content(layout);window.present()
    return window
