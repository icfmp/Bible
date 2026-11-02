"""Full native selectors remain usable without duplicating reader commands."""
import os,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ReaderChromeTests(unittest.TestCase):
    def test_chapter_titles_full_names_narrow_controls_and_restore(self):
        from bible.ui import Application,Window,Library,Gtk
        from bible.book_names import display_name
        from bible.i18n import LANGUAGE
        chapter=display_name('John','John',LANGUAGE)+' 3'
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed_fixture(root,entries=[('John.3.16','Exact verse 16'),('John.3.17','Exact verse 17')])
            library=Library(root/'translations');original=library.resource
            title='The complete translation with additional source information'
            with patch.object(library,'resource',side_effect=lambda name:replace(original(name),description=title)):
                w=Window(app,library);w.present()
                settings=Gtk.Settings.get_default();font=settings.props.gtk_font_name
                try:
                    t=w.active_tab;t.navigate('Test','John.3.16');spin(lambda:not t._restoring_scroll)
                    self.assertEqual(t.title(),chapter);self.assertEqual(w.heading.get_subtitle(),'')
                    self.assertEqual(w.primary_version.caption.get_text(),title)
                    t.navigate('Test','John.3.17');spin(lambda:not t._restoring_scroll)
                    self.assertEqual(t.title(),chapter);self.assertEqual(t.state.reference,'John.3.17')
                    for size in (font,'Sans 18'):
                        settings.props.gtk_font_name=size
                        for width in (1200,360):
                            w.set_default_size(width,800)
                            spin(lambda:not w._controls_tick and not t._restoring_scroll,duration=.4)
                            self.assertLessEqual(w.header.get_width(),w.get_width()+4)
                            self.assertGreater(w.passage_button.get_width(),80)
                            label=w.primary_version.caption
                            self.assertGreater(label.get_width(),80)
                            self.assertGreaterEqual(label.get_height(),label.get_layout().get_pixel_size()[1])
                            self.assertEqual(label.get_ellipsize(),0)
                            if width==360:
                                w.open_reading_popup(w.appearance_button);spin(lambda:w.appearance.get_visible())
                                self.assertTrue(w.reader_overflow.get_active());w.dismiss_popovers();spin()
                    self.assertEqual(t.state.reference,'John.3.17')
                finally:settings.props.gtk_font_name=font;w.close()
