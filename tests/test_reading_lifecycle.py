"""First successful install and deterministic recovery of unusable sessions."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
class ReadingLifecycleTests(unittest.TestCase):
    def window(self,root):
        from bible.ui import Application,Window,Library,Gtk
        app=Application.get_default() or Application();app.register()
        Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
        window=Window(app,Library(root/'translations'));window.present();spin()
        self.addCleanup(lambda:window.close() if not window.closed else None)
        return window

    def test_first_install_opens_immediately_and_survives_workspace_switch_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);w=self.window(root)
            self.assertEqual(w.main_pages.get_visible_child_name(),'welcome')
            installed_fixture(root,'First');w.resource_installed('First');spin()
            self.assertEqual(w.main_pages.get_visible_child_name(),'reading')
            self.assertEqual((w.active_tab.state.resource,w.active_tab.state.reference),('First','Gen.1.1'))
            self.assertIn('SENTINEL',w.active_tab.text.get_buffer().props.text)
            w.open_notes();spin();w.notes_space.leave();spin()
            self.assertEqual(w.main_pages.get_visible_child_name(),'reading')
            self.assertTrue(w.active_tab.navigate('First','John.3.16'));w.close();spin()
            w=self.window(root)
            self.assertEqual((w.active_tab.state.resource,w.active_tab.state.reference),('First','John.3.16'))
            self.assertEqual(w.main_pages.get_visible_child_name(),'reading')

    def test_missing_and_unreadable_saved_resources_choose_stable_readable_fallback(self):
        from bible.session import SessionStore,Session,TabState
        for previous in (None,'Removed','AAEmpty'):
            with self.subTest(previous=previous),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);installed_fixture(root,'AAEmpty',entries=[])
                installed_fixture(root,'BBReadable');installed_fixture(root,'CCReadable')
                SessionStore(root/'session.json').save(Session([TabState(resource=previous,reference='Gen.11.1')]))
                w=self.window(root)
                self.assertEqual((w.active_tab.state.resource,w.active_tab.state.reference),('BBReadable','Gen.1.1'))
                self.assertEqual(w.main_pages.get_visible_child_name(),'reading');w.close();spin()

    def test_subsequent_install_preserves_existing_reader_passage_and_notes_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed_fixture(root,'Existing');w=self.window(root)
            w.active_tab.navigate('Existing','John.3.16');w.open_notes();spin()
            installed_fixture(root,'Added');w.resource_installed('Added');spin()
            self.assertEqual(w.main_pages.get_visible_child_name(),'notes')
            self.assertEqual((w.active_tab.state.resource,w.active_tab.state.reference),('Existing','John.3.16'))
