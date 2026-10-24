"""Regression contracts for the coordinated reader controls (#64/#66/#69)."""
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture, spin


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK')
class VisualPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application
        cls.app=Application.get_default() or Application();cls.app.register()

    def test_pane_choosers_keep_tabs_data_and_verified_mapping(self):
        from bible.ui import Window,Library
        with tempfile.TemporaryDirectory() as directory:
            for name,system in [('Darby','Luther'),('KingJames','KJV'),('Segond','Segond')]:
                installed_fixture(directory,name,entries=([('Gen.31.55','SOURCE '+name)] if system!='Luther' else [])+[('Gen.32.1','SOURCE '+name),('Gen.32.2','SOURCE '+name)],versification=system)
            library=Library(Path(directory)/'translations')
            w=Window(self.app,library);w.present()
            try:
                tab=w.active_tab;tab.navigate('Darby','Gen.32.1');tab.state.comparison='KingJames';w.sync_comparison();spin()
                original_order=[w.study_button,w.my_notes_button]
                self.assertFalse(hasattr(w,'library_button'))
                self.assertLess(original_order[0].compute_bounds(w)[1].origin.x,original_order[1].compute_bounds(w)[1].origin.x)
                self.assertIs(w.appearance_button.get_parent(),w.reader_controls)
                self.assertIs(w.compared_version.get_parent(),tab.comparison_controls)
                self.assertFalse(w.immersive_button.get_visible())
                self.assertFalse(w.comparison_choices.get_visible())
                self.assertIn('Gen.32.1',tab.primary_heading.get_text())
                self.assertIn('Gen.31.55',tab.comparison_heading.get_text())
                w.compared_version.choices.set_selected(w.compared_version.names.index('Segond'));spin()
                self.assertEqual(tab.state.resource,'Darby');self.assertEqual(tab.state.comparison,'Segond')
                count=w.view.get_n_pages()
                w.primary_version.choices.set_selected(w.primary_version.names.index('KingJames'));spin()
                self.assertEqual(w.view.get_n_pages(),count)
                self.assertEqual((tab.state.resource,tab.state.reference,tab.state.comparison),('KingJames','Gen.31.55','Segond'))
                w.end_comparison();spin()
                self.assertFalse(tab.primary_heading.get_visible());self.assertTrue(w.immersive_button.get_visible())
                w.close();w=Window(self.app,library);w.present();spin()
                self.assertEqual((w.active_tab.state.resource,w.active_tab.state.reference),('KingJames','Gen.31.55'))
            finally:w.close()

    def test_active_palette_pair_switches_without_losing_saved_other_pair(self):
        from bible.ui import Window,Library
        from tests.test_appearance import SystemStyleOverride
        with tempfile.TemporaryDirectory() as directory, SystemStyleOverride() as system:
            installed_fixture(directory)
            w=Window(self.app,Library(Path(directory)/'translations'));w.present()
            try:
                aa=w.appearance
                aa.update('day_palette','paper');aa.update('night_palette','black')
                for dark in (False,True,False):
                    system.set(dark=dark,high=False);spin()
                    self.assertEqual(aa.palette_rows['night_palette'].get_visible(),dark)
                    self.assertEqual(aa.palette_rows['day_palette'].get_visible(),not dark)
                    self.assertEqual(w.preferences.value.day_palette,'paper')
                    self.assertEqual(w.preferences.value.night_palette,'black')
                w.close();w=Window(self.app,w.library);w.present();spin()
                self.assertEqual((w.preferences.value.day_palette,w.preferences.value.night_palette),('paper','black'))
            finally:w.close()
