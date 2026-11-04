"""Responsive edition rows keep native selection and truthful source metadata."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class TranslationPickerTests(unittest.TestCase):
    def test_long_edition_rows_resize_while_open_and_keep_selection(self):
        from bible.ui import Application,Window,Library,Gtk
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed_fixture(root)
            library=Library(root/'translations');original=library.resource
            title='A complete edition name with a very long description that must remain readable in a small window'
            with patch.object(library,'resource',side_effect=lambda name:replace(original(name),description=title,abbreviation='ABC')):
                w=Window(app,library);w.set_default_size(1200,800);w.present();spin()
                try:
                    chooser=w.primary_version;chooser.popup();spin(duration=.3)
                    wide=chooser.popover.get_child().get_width()
                    row=chooser.choices.list.get_row_at_index(0);box=row.get_child();labels=box.get_first_child()
                    self.assertEqual(labels.get_first_child().get_text(),title)
                    self.assertEqual(labels.get_last_child().get_text(),'CrossWire')
                    self.assertEqual(labels.get_next_sibling().get_text(),'ABC')
                    self.assertEqual(chooser.choices.rows[0].get_opacity(),1)
                    w.set_default_size(360,800);spin(lambda:not w._controls_tick,duration=.4)
                    # The header moves at the breakpoint, closing its native popup.
                    if not chooser.popover.get_visible():chooser.popup();spin(duration=.3)
                    self.assertLess(chooser.popover.get_child().get_width(),wide)
                    self.assertLessEqual(chooser.popover.get_child().get_width(),w.get_width())
                    text=labels.get_first_child()
                    self.assertGreaterEqual(text.get_height(),text.get_layout().get_pixel_size()[1])
                    badge=labels.get_next_sibling()
                    self.assertGreaterEqual(badge.get_width(),badge.create_pango_layout('ABC').get_pixel_size()[0])
                    chooser.choices.list.emit('row-activated',row);spin()
                    self.assertFalse(chooser.popover.get_visible())
                    self.assertEqual(w.active_tab.state.resource,'Test')
                finally:w.close()
