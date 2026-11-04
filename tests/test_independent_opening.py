"""Explicitly opening a Bible is distinct from cross-resource verse alignment."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
class IndependentOpeningTests(unittest.TestCase):
    def test_library_and_selector_open_unmapped_target_without_relabeling_a_passage(self):
        from bible.ui import Application,Window,Library
        from bible.reference_resolution import resolve,VersificationMismatch
        from bible.sword_provider import Reader
        from bible.i18n import tr
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        with tempfile.TemporaryDirectory() as directory,patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
            root=Path(directory)
            installed_fixture(directory,'Source',entries=[('Gen.19.1','SYNTHETIC SOURCE NINETEEN')])
            installed_fixture(directory,'Target',versification='LXX',entries=[('Gen.1.1','SYNTHETIC TARGET START'),('Gen.19.1','SYNTHETIC TARGET NINETEEN')])
            installed_fixture(directory,'Mapped',entries=[('Gen.1.1','SYNTHETIC MAPPED START'),('Gen.19.1','SYNTHETIC MAPPED NINETEEN')])
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(root/'translations'));window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Source','Gen.19.1');spin()
                note=window.notes_store.save('PRESERVED PERSONAL NOTE',[],versification='KJV',start='Gen.19.1',end='Gen.19.1',origin_translation='Source',origin_language='en')
                preferences=window.preferences.path.read_bytes() if window.preferences.path.exists() else None
                target=Reader(root/'translations/Target','Target')
                with self.assertRaises(VersificationMismatch):resolve('Gen.19.1','KJV',target)
                dialog=window.open_library();spin(lambda:not dialog.preparing)
                dialog.read_resource(window.library.resource('Target'));spin()
                self.assertTrue(dialog.closed);self.assertEqual(tab.state.resource,'Target')
                self.assertEqual(tab.state.reference,'Gen.19.1')
                self.assertIn('SYNTHETIC TARGET NINETEEN',tab.text.get_buffer().props.text)
                self.assertFalse(tab.status.get_visible())
                self.assertTrue(tab.show('Gen.19.1'));spin()
                self.assertIn('SYNTHETIC TARGET NINETEEN',tab.text.get_buffer().props.text)
                window.primary_version.sync()
                window.primary_version.choices.set_selected(window.primary_version.names.index('Source'));spin()
                self.assertEqual(tab.state.resource,'Source');self.assertEqual(tab.state.reference,'Gen.19.1')
                self.assertFalse(window.primary_version.status.get_visible())
                tab.state.comparison='Target';tab.refresh_comparison();spin()
                self.assertIsNotNone(tab._comparison_reader);self.assertFalse(tab._comparison_aligned)
                self.assertEqual(tab.comparison_reference,'Gen.19.1')
                self.assertEqual(tab._comparison_document.key,'Gen.19')
                self.assertIn('SYNTHETIC TARGET NINETEEN',tab.comparison_text.get_buffer().props.text)
                self.assertTrue(window.switch_translation('Mapped'));spin()
                self.assertEqual(tab.state.reference,'Gen.19.1')
                self.assertIn('SYNTHETIC MAPPED NINETEEN',tab.text.get_buffer().props.text)
                self.assertEqual(window.notes_store.all(),[note])
                if preferences is not None:self.assertEqual(window.preferences.path.read_bytes(),preferences)
            finally:window.close();close_test_dialogs();spin()

    def test_independent_comparison_restores_qualified_position_and_rejects_unavailable_chapter(self):
        from bible.ui import Application,Window,Library
        from bible.i18n import tr
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        with tempfile.TemporaryDirectory() as directory,patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
            root=Path(directory)
            installed_fixture(root,'Source',entries=[('Gen.19.1','SOURCE NINETEEN'),('Gen.20.1','SOURCE TWENTY')])
            installed_fixture(root,'Target',versification='LXX',entries=[('Gen.1.1','TARGET FIRST'),('Gen.19.1','TARGET NINETEEN'),('Gen.19.2','TARGET SECOND')])
            installed_fixture(root,'Other',versification='LXX',entries=[('Gen.1.1','OTHER FIRST'),('Gen.19.1','OTHER NINETEEN')])
            app=Application.get_default() or Application();app.register();library=Library(root/'translations')
            window=Window(app,library);window.present();spin()
            try:
                tab=window.active_tab;self.assertTrue(tab.navigate('Source','Gen.19.1'))
                tab.state.comparison='Target';window.sync_comparison()
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False))
                self.assertEqual(tab.comparison_reference,'Gen.19.1');self.assertFalse(tab._comparison_aligned)
                self.assertTrue(tab.remember_comparison('Gen.19.2'))
                window.close();spin()
                window=Window(app,library);window.present();spin()
                tab=window.active_tab
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False))
                self.assertEqual(tab.state.resource,'Source');self.assertEqual(tab.state.reference,'Gen.19.1')
                self.assertEqual(tab.comparison_reference,'Gen.19.2');self.assertEqual(tab._comparison_document.key,'Gen.19')
                self.assertFalse(tab._comparison_aligned)
                tab.state.comparison='Other';window.sync_comparison();spin()
                self.assertEqual(tab.comparison_reference,'Gen.19.1')
                self.assertEqual(tab.state.comparison_position,dict(resource='Other',reference='Gen.19.1'))
                window.end_comparison();self.assertEqual(tab.state.comparison_position,{})
                self.assertTrue(tab.navigate('Source','Gen.20.1'));spin(lambda:not tab._restoring_scroll)
                tab.state.comparison='Other';window.sync_comparison();spin()
                self.assertIsNone(tab.comparison_reference)
                self.assertEqual(tab.comparison_text.get_buffer().props.text,'')
                self.assertEqual(tab.comparison_status.get_text(),tr('This chapter is not available in this translation.'))
                self.assertEqual(tab.state.reference,'Gen.20.1');self.assertIn('SOURCE TWENTY',tab.text.get_buffer().props.text)
            finally:window.close();close_test_dialogs();spin()
