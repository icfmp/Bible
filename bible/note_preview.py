"""Shared safe native Markdown view for notes; display never rewrites storage."""
from gi.repository import Gtk, Pango
from .markdown import render
from .i18n import tr


class NotePreview(Gtk.TextView):
    def __init__(self, **kwargs):
        super().__init__(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR,
                         left_margin=12, right_margin=12, top_margin=12, bottom_margin=12, **kwargs)
        self.update_property([Gtk.AccessibleProperty.LABEL], [tr('Safe preview')])
        buffer = self.get_buffer()
        self.tags = {'bold': buffer.create_tag(None, weight=700),
                     'italic': buffer.create_tag(None, style=Pango.Style.ITALIC),
                     'link': buffer.create_tag(None, underline=Pango.Underline.SINGLE)}

    def set_source(self, source):
        text, spans = render(source)
        buffer = self.get_buffer(); buffer.set_text(text)
        for kind, start, end in spans:
            buffer.apply_tag(self.tags[kind], buffer.get_iter_at_offset(start), buffer.get_iter_at_offset(end))
