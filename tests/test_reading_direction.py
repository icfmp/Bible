"""Keep resource direction independent of French/English native controls."""
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture,spin
from tests.test_commentary import commentary_fixture
from bible.sword_provider import Reader


def set_rtl(root):
    config=next((root/'mods.d').glob('*.conf'))
    with config.open('a') as output:output.write('Direction=RtoL\n')


class DirectionTests(unittest.TestCase):
    def test_native_sword_direction_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=installed_fixture(directory);self.assertFalse(Reader(root,'Test').rtl)
            set_rtl(root);self.assertTrue(Reader(root,'Test').rtl)


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK under Xvfb')
class DirectionUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application
        cls.app=Application.get_default() or Application();cls.app.register()

    def test_bible_comparison_and_commentary_restore_direction_per_resource(self):
        from bible.ui import Window,Library,Gtk
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            root=installed_fixture(directory,'Rtl',entries=[('Gen.1.1','בדיקה — RTL SOURCE TEST'),('Gen.1.2','SECOND RTL SOURCE TEST')]);set_rtl(root)
            notes=commentary_fixture(directory,'RtlNotes');set_rtl(notes)
            commentary_fixture(directory)
            window=Window(self.app,Library(Path(directory)/'translations'));window.present()
            try:
                window.navigate_selection('Rtl','Gen.1.1');tab=window.active_tab
                self.assertEqual(tab.text.get_direction(),Gtk.TextDirection.RTL)
                self.assertEqual(tab.text.get_justification(),Gtk.Justification.RIGHT)
                self.assertEqual(tab._chapter_tag.props.justification,Gtk.Justification.CENTER)
                self.assertIn('בדיקה — RTL SOURCE TEST',tab.text.get_buffer().props.text)
                tab.state.comparison='Test';tab.refresh_comparison()
                self.assertEqual(tab.comparison_text.get_direction(),Gtk.TextDirection.LTR)
                tab.state.commentary='RtlNotes';window.study_button.set_active(True);window.study.refresh(force=True)
                self.assertEqual(window.study.text.get_direction(),Gtk.TextDirection.RTL)
                self.assertNotEqual(window.get_direction(),Gtk.TextDirection.RTL)
                window.navigate_selection('Test','Gen.1.1')
                self.assertEqual(tab.text.get_direction(),Gtk.TextDirection.LTR)
                self.assertEqual(tab.text.get_justification(),Gtk.Justification.LEFT)
                tab.state.comparison='Rtl';tab.refresh_comparison()
                self.assertEqual(tab.comparison_text.get_direction(),Gtk.TextDirection.RTL)
                tab.state.commentary='Notes';window.study.refresh(force=True)
                self.assertEqual(window.study.text.get_direction(),Gtk.TextDirection.LTR)
            finally:window.close()
