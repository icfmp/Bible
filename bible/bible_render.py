"""One structured renderer for ordinary and comparison Bible panes."""
from .paged_sources import BiblePages
from .reading_style import SPACING, apply_direction
from .verse_typography import configure
from gi.repository import Gtk
from gi.repository import GObject


def copy_selection(view):
    selection=view.get_buffer().get_selection_bounds()
    if not selection:return
    document,base=view._bible_copy_source
    start,end=(base+i.get_offset() for i in selection)
    view.get_clipboard().set(document.copy(start,end))
    GObject.signal_stop_emission_by_name(view,'copy-clipboard')


def bind_copy(view, document, base=0):
    view._bible_copy_source=(document,base)
    if not getattr(view,'_bible_copy_handler',None):
        view._bible_copy_handler=view.connect('copy-clipboard',copy_selection)


def render(view, reader, chapter, preferences, document=None):
    document = document or BiblePages(reader, None).document(chapter.reference, preferences)
    buffer = view.get_buffer()
    buffer.set_text(document.text)
    bind_copy(view,document)
    apply_direction(view, reader)
    view.set_pixels_inside_wrap(SPACING[preferences.line_spacing])
    view.set_pixels_below_lines(SPACING[preferences.line_spacing]+4)
    table = buffer.get_tag_table()
    tags = {}
    for kind in ['body','chapter','heading','number','verse-start','hidden']:
        name = 'verse-'+kind if kind != 'verse-start' else kind
        tag = table.lookup(name) or buffer.create_tag(name)
        tags[kind] = tag
        if kind=='body':tag.props.family=preferences.font;tag.props.size_points=preferences.size
        elif kind=='number':configure(tag,view,preferences,getattr(view,'_reading_palette','white'))
        elif kind=='verse-start':tag.props.allow_breaks=False
        elif kind=='hidden':tag.props.style=2
        else:
            tag.props.weight=700;tag.props.size_points=preferences.size*(1.35 if kind=='chapter' else 1.12)
            tag.props.pixels_above_lines=20 if kind=='chapter' else 16
            tag.props.pixels_below_lines=20 if kind=='chapter' else 12
            tag.props.justification=Gtk.Justification.CENTER if kind=='chapter' else Gtk.Justification.LEFT
    buffer.apply_tag(tags['body'],buffer.get_start_iter(),buffer.get_end_iter())
    for style in document.styles:
        buffer.apply_tag(tags[style.kind],buffer.get_iter_at_offset(style.start),buffer.get_iter_at_offset(style.end))
    offsets, ranges, markers = {}, {}, {}
    for span in document.spans:
        marker = span.body-(len(span.reference.rsplit('.',1)[-1])+1 if preferences.verse_numbers else 0)
        offsets[span.reference]=marker;ranges[span.reference]=(marker,span.end);markers[span.reference]=span.body
    return document, offsets, ranges, markers
