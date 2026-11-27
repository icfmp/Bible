"""Native allocation checks for the small, source-independent heading inset."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace


@unittest.skipUnless(os.environ.get("DISPLAY"), "Requires GTK/Pango")
class HeadingLeadingTests(unittest.TestCase):
    def test_wrapped_heading_lines_gain_room_without_changing_font_or_body(self) -> None:
        from bible.ui import Gtk
        from bible.bible_render import render
        from bible.pagination import Document, PassageSpan, StyleSpan, attributes
        from bible.preferences import ReadingPreferences
        from gi.repository import Pango
        from tests.test_ui import spin

        Gtk.init()
        chapter = "Genèse 13 — Écriture\n"
        heading = "Melchisédek — Élévation, accents et descendantes gy\n"
        text = chapter + heading + "Exact source body, punctuation and verse reference."
        body = len(chapter) + len(heading)
        doc = Document(
            "fixture",
            text,
            (PassageSpan("Gen.13.1", 0, body, len(text)),),
            (StyleSpan("chapter", 0, len(chapter)), StyleSpan("heading", len(chapter), body)),
        )
        window = Gtk.Window(default_width=560, default_height=640)
        box = Gtk.Box(homogeneous=True)
        window.set_child(box)
        views = [Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, hexpand=True) for _ in range(2)]
        for view in views:
            box.append(view)
        window.present()
        spin()
        try:
            for font in ("Roboto Serif", "Roboto"):
                for size in (13, 14, 15, 28):
                    for spacing in ("tight", "very-airy"):
                        with self.subTest(font=font, size=size, spacing=spacing):
                            prefs = ReadingPreferences(font=font, size=size, line_spacing=spacing)
                            for view in views:
                                render(view, SimpleNamespace(rtl=False), None, prefs, doc)
                            # Previous allocation, with identical text, glyph size,
                            # paragraph gaps and width, in the adjacent control.
                            for kind in ("chapter", "heading"):
                                views[0].get_buffer().get_tag_table().lookup(
                                    "verse-" + kind
                                ).props.line_height = 1
                            spin()
                            for start, end in ((0, len(chapter)), (len(chapter), body)):
                                rows = []
                                for view in views:
                                    buffer = view.get_buffer()
                                    lines = {}
                                    for offset in range(start, end - 1):
                                        rect = view.get_iter_location(
                                            buffer.get_iter_at_offset(offset)
                                        )
                                        lines.setdefault(rect.y, rect.height)
                                    rows.append(sorted(lines.items()))
                                self.assertEqual(len(rows[0]), len(rows[1]))
                                # Iterator rectangles describe the glyph's font
                                # box, not the extra leading around that box.
                                self.assertEqual([h for _, h in rows[0]], [h for _, h in rows[1]])
                                ranges = [
                                    v.get_line_yrange(v.get_buffer().get_iter_at_offset(start))
                                    for v in views
                                ]
                                self.assertGreater(ranges[1][1], ranges[0][1])
                                if len(rows[0]) > 1:
                                    self.assertGreater(
                                        rows[1][1][0] - rows[1][0][0], rows[0][1][0] - rows[0][0][0]
                                    )
                                self.assertTrue(
                                    all(
                                        y + h <= ny for (y, h), (ny, _) in zip(rows[1], rows[1][1:])
                                    )
                                )
                            for view in views:
                                buffer = view.get_buffer()
                                self.assertEqual(buffer.props.text, text)
                                self.assertEqual(doc.locate(doc.anchor(body)), body)
                            a, b = [
                                v.get_iter_location(v.get_buffer().get_iter_at_offset(body))
                                for v in views
                            ]
                            self.assertEqual(a.height, b.height)
                            self.assertGreater(b.y, a.y)
                            # The independent page planner must budget the same
                            # extra internal leading, including wrapped titles.
                            layout = views[1].create_pango_layout(text)
                            layout.set_font_description(Pango.FontDescription(f"{font} {size}"))
                            layout.set_width(240 * Pango.SCALE)
                            layout.set_wrap(Pango.WrapMode.WORD_CHAR)
                            attrs = attributes(
                                doc, context=views[1].get_pango_context(), preferences=prefs
                            )
                            layout.set_attributes(attrs)
                            after = layout.get_pixel_size()[1]
                            control = attrs.copy()
                            control.filter(
                                lambda attr: attr.klass.type == Pango.AttrType.LINE_HEIGHT
                            )
                            layout.set_attributes(control)
                            before = layout.get_pixel_size()[1]
                            self.assertGreater(after, before)
            self.assertEqual(doc.copy(0, len(text)), text)
        finally:
            window.destroy()
