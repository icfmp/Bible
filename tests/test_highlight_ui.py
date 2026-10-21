import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
class HighlightUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application,Gtk
        cls.app=Application.get_default() or Application();cls.app.register()
        Gtk.Settings.get_default().set_property('gtk-enable-animations',False)

    def test_range_selection_hide_show_reflow_and_high_contrast_preserve_marks(self):
        from bible.ui import Window,Library
        from tests.test_appearance import SystemStyleOverride
        from gi.repository import Pango
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory);window=Window(self.app,Library(Path(directory)/'translations'));window.present()
            try:
                spin();tab=window.active_tab;buffer=tab.text.get_buffer()
                buffer.select_range(buffer.get_iter_at_offset(tab._marker_ends['Gen.1.1']),buffer.get_iter_at_offset(tab._verse_ranges['Gen.1.2'][1]))
                selected=buffer.get_text(*buffer.get_selection_bounds(),False);history=len(tab.state.history)
                window.mark_highlight('yellow');self.assertEqual(len(window.highlights.entries),2)
                tag=buffer.get_tag_table().lookup('highlight-yellow')
                self.assertTrue(buffer.get_iter_at_offset(tab._marker_ends['Gen.1.1']).has_tag(tag))
                self.assertEqual(buffer.get_text(*buffer.get_selection_bounds(),False),selected)
                window.appearance.show_highlights.set_active(False)
                self.assertFalse(buffer.get_iter_at_offset(tab._marker_ends['Gen.1.1']).has_tag(tag))
                self.assertEqual(len(window.highlights.entries),2)
                window.appearance.show_highlights.set_active(True)
                before=window.highlights.path.read_bytes()
                with SystemStyleOverride() as style:
                    style.set(dark=False,high=True);spin()
                    self.assertEqual(tag.props.underline,Pango.Underline.DOUBLE)
                    style.set(dark=False,high=False);spin()
                    self.assertEqual(tag.props.underline,Pango.Underline.NONE)
                self.assertEqual(window.highlights.path.read_bytes(),before)
                self.assertEqual(len(tab.state.history),history)
                panel=window.open_highlights();panel.search.set_text('Gen');panel.refresh()
                self.assertEqual(len(panel.rows),2);panel.activate(None,0)
                self.assertEqual(window.active_tab.state.reference,'Gen.1.2')
            finally:window.close()

    def test_missing_system_does_not_open_a_different_passage_or_delete_mark(self):
        from bible.ui import Window,Library
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory);window=Window(self.app,Library(Path(directory)/'translations'));window.present()
            try:
                window.highlights.set('Segond',['Ps.3.2'],'blue','Missing')
                panel=window.open_highlights();reference=window.active_tab.state.reference
                panel.activate(None,0)
                self.assertEqual(window.active_tab.state.reference,reference)
                self.assertIn(('Segond','Ps.3.2'),window.highlights.entries)
                self.assertTrue(panel.status.get_text());panel.close()
            finally:window.close()
