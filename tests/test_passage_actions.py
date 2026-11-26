"""Native selection actions, source-aware copying and annotation commands."""
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture, spin


@unittest.skipUnless(os.environ.get("DISPLAY"), "Requires GTK")
class PassageActionTests(unittest.TestCase):
    def test_copy_formats_preserve_unicode_and_cross_chapter_selection_extent(self):
        from types import SimpleNamespace
        from bible.passage_actions import Source, Target, copy_text

        # Explicit sentinel content exercises code points and line boundaries;
        # no generated fixture is presented as a Bible resource.
        source = Source(
            None, "sentinel", SimpleNamespace(versification="KJV"), None, 0, None, "test"
        )
        for text in ("Écl", "אֱלֹהִים", "Éclair…\nאֱלֹהִים — fin."):
            value = Target(
                source,
                None,
                None,
                ("Gen.1.31", "Gen.2.1"),
                text,
                ("WHOLE FIRST VERSE", "WHOLE SECOND VERSE"),
                True,
                0,
                edition="Sentinel edition",
            )
            self.assertEqual(copy_text(value), text)
            citation = copy_text(value, "label")
            self.assertIn("1:31–2:1", citation)
            self.assertTrue(citation.endswith(" — Sentinel edition"))
            self.assertEqual(copy_text(value, "reference"), citation + "\n" + text)
            self.assertNotIn("WHOLE", copy_text(value, "reference"))

    def test_frozen_comparison_source_copy_note_and_stale_selection(self):
        from bible.ui import Application, Window, Library

        app = Application.get_default() or Application()
        app.register()
        with tempfile.TemporaryDirectory() as directory:
            for name, system in [("Test", "KJV"), ("Other", "Segond")]:
                installed_fixture(
                    directory,
                    name,
                    entries=[
                        (f"Gen.1.{i}", f"{name} verse {i} source words " * 8) for i in range(1, 5)
                    ],
                    versification=system,
                )
            window = Window(app, Library(Path(directory) / "translations"))
            window.present()
            try:
                tab = window.active_tab
                tab.navigate("Test", "Gen.1.1")
                tab.state.comparison = "Other"
                window.sync_comparison()
                spin(
                    lambda: not tab._restoring_scroll
                    and not getattr(tab, "_comparison_positioning", False)
                )
                actions = window.passage_actions
                view = tab.comparison_text
                buffer = view.get_buffer()
                first, last = (
                    tab._comparison_markers["Gen.1.2"] + 1,
                    tab._comparison_markers["Gen.1.3"] + 5,
                )
                buffer.select_range(
                    buffer.get_iter_at_offset(first), buffer.get_iter_at_offset(last)
                )
                spin()
                self.assertFalse(
                    actions.bar.get_visible(), "Programmatic selection must not open the bar"
                )
                factory = lambda: actions.ordinary(tab, True)
                actions.capture(view, factory, None)
                self.assertEqual(actions.target.references, ("Gen.1.2", "Gen.1.3"))
                self.assertEqual(actions.target.source.resource, "Other")
                self.assertEqual(actions.target.source.reader.versification, "Segond")
                # The chevron never copies; each format copies the same partial
                # source selection, rather than expanding it to complete verses.
                from bible.passage_actions import copy_text

                frozen = actions.target
                window.get_clipboard().set("UNCHANGED CLIPBOARD")
                from tools.check_alpha_ui import X11Input

                native = X11Input()

                def activate(button):
                    if os.environ.get("BIBLE_TEST_ISOLATED_CLICK") == "1":
                        native.click(button)
                    elif hasattr(button, "popup"):
                        button.popup()
                    else:
                        button.emit("clicked")

                try:
                    spin()
                    activate(actions.copy_options)
                    spin(lambda: actions.copy_popover.get_mapped())
                    unchanged = []
                    window.get_clipboard().read_text_async(
                        None,
                        lambda clipboard, result: unchanged.append(
                            clipboard.read_text_finish(result)
                        ),
                    )
                    spin(lambda: bool(unchanged))
                    self.assertEqual(unchanged, ["UNCHANGED CLIPBOARD"])
                    self.assertEqual(actions.target, frozen)
                    for index, mode in enumerate(("selected", "reference", "label")):
                        if index:
                            actions.capture(view, factory, None)
                            spin()
                            activate(actions.copy_options)
                            spin(lambda: actions.copy_popover.get_mapped())
                        button = actions.copy_popover.get_child().get_first_child()
                        for _ in range(index):
                            button = button.get_next_sibling()
                        activate(button)
                        spin()
                        result = []
                        window.get_clipboard().read_text_async(
                            None,
                            lambda clipboard, value: result.append(
                                clipboard.read_text_finish(value)
                            ),
                        )
                        spin(lambda: bool(result))
                        self.assertEqual(result, [copy_text(frozen, mode)])
                        self.assertFalse(actions.bar.get_visible())
                        self.assertFalse(actions.copy_popover.get_visible())
                    self.assertEqual(copy_text(frozen), frozen.text)
                    self.assertNotEqual(frozen.text, "\n".join(frozen.verses))
                    self.assertTrue(copy_text(frozen, "reference").endswith("\n" + frozen.text))
                    self.assertIn("Other", copy_text(frozen, "label"))
                    actions.capture(view, factory, None)
                finally:
                    native.close()
                from bible.highlights import COLORS

                self.assertEqual(set(actions.highlight_buttons), set(COLORS))
                for color in ("yellow", "green", "green", "blue"):
                    actions.highlight_buttons[color][0].emit("clicked")
                    self.assertEqual(
                        [
                            window.highlights.entries[("Segond", ref)]["color"]
                            for ref in actions.target.references
                        ],
                        [color, color],
                    )
                self.assertFalse(hasattr(actions, "compare_button"))
                copied = []
                expected = actions.target.text
                actions.copy()
                window.get_clipboard().read_text_async(
                    None,
                    lambda clipboard, result: copied.append(clipboard.read_text_finish(result)),
                )
                spin(lambda: bool(copied))
                self.assertEqual(copied[0], expected)
                self.assertEqual(
                    tuple(i.get_offset() for i in buffer.get_selection_bounds()), (first, last)
                )
                self.assertFalse(actions.bar.get_visible())
                actions.capture(view, factory, None)
                actions.note()
                editor = window.note_editor
                self.assertEqual(editor.context["origin_translation"], "Other")
                self.assertEqual(editor.context["versification"], "Segond")
                self.assertEqual(
                    (editor.context["start"], editor.context["end"]), ("Gen.1.2", "Gen.1.3")
                )
                editor.close()
                spin()
                actions.capture(view, factory, None)
                # A new selection must invalidate the old frozen action target.
                changed = tab._comparison_markers["Gen.1.4"]
                buffer.select_range(
                    buffer.get_iter_at_offset(changed), buffer.get_iter_at_offset(changed + 5)
                )
                self.assertFalse(actions.valid())
                actions.study_word()
                spin()
                self.assertIsNone(window.study.words.dialog)
                actions.copy()
                self.assertFalse(actions.bar.get_visible())
                self.assertEqual(tab.state.resource, "Test")
                if not hasattr(window, "highlights"):
                    self.assertIsNone(actions.highlight_button)
            finally:
                window.close()

    def test_programmatic_anchor_and_study_updates_do_not_open_actions(self):
        from bible.ui import Application, Window, Library

        app = Application.get_default() or Application()
        app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = Window(app, Library(Path(directory) / "translations"))
            window.present()
            try:
                tab = window.active_tab
                tab.select_verse("Gen.1.2")
                tab.mark_commentary_range("Gen.1.1", "Gen.1.2")
                spin()
                self.assertFalse(window.passage_actions.bar.get_visible())
            finally:
                window.close()

    def test_vertical_labelled_actions_fit_and_tab_in_order(self):
        from bible.ui import Application, Window, Library
        from tools.check_alpha_ui import X11Input

        app = Application.get_default() or Application()
        app.register()
        native = X11Input()
        try:
            for width in (360, 900):
                with self.subTest(width=width), tempfile.TemporaryDirectory() as directory:
                    installed_fixture(directory, long_text=True)
                    w = Window(app, Library(Path(directory) / "translations"))
                    w.set_default_size(width, 700)
                    w.present()
                    spin(
                        lambda: w.get_width() <= width and not w.active_tab._restoring_scroll,
                        duration=0.3,
                    )
                    try:
                        w.study_button.set_active(False)
                        tab = w.active_tab
                        buffer = tab.text.get_buffer()
                        offset = tab._marker_ends["Gen.1.1"] + 3
                        buffer.select_range(
                            buffer.get_iter_at_offset(offset),
                            buffer.get_iter_at_offset(offset + 12),
                        )
                        a = w.passage_actions
                        a.capture(tab.text, lambda: a.ordinary(tab), None)
                        spin(duration=0.4)
                        buttons = [
                            *[v[0] for v in a.highlight_buttons.values()],
                            a.copy_button,
                            a.copy_options,
                            a.note_button,
                            a.word_button,
                        ]
                        for button in buttons:
                            found, bounds = button.compute_bounds(w)
                            self.assertTrue(found)
                            self.assertGreaterEqual(bounds.get_x(), 0)
                            self.assertLessEqual(bounds.get_x() + bounds.get_width(), w.get_width())
                            self.assertGreaterEqual(bounds.get_y(), 0)
                            self.assertLessEqual(
                                bounds.get_y() + bounds.get_height(), w.get_height()
                            )
                        if os.environ.get("BIBLE_TEST_ISOLATED_CLICK") == "1":
                            native.activate(w)
                            buttons[0].grab_focus()
                            for button in buttons[1:]:
                                native.key("Tab")
                                spin(duration=0.05)
                                focus = w.get_focus()
                                self.assertTrue(
                                    focus is button or focus and focus.is_ancestor(button),
                                    (width, button, focus),
                                )
                    finally:
                        w.close()
        finally:
            native.close()
