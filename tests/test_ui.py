import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch


def spin(until=lambda: True, duration=0.1):
    from bible.ui import GLib
    deadline = time.monotonic() + 4
    minimum = time.monotonic() + duration
    while time.monotonic() < deadline:
        GLib.MainContext.default().iteration(False)
        if time.monotonic() >= minimum and until():
            return
        time.sleep(0.005)
    raise AssertionError('GTK layout/task did not settle')


def installed_fixture(directory, name='Test', long_text=False):
    from tests.test_library import fixture
    root = Path(directory) / 'translations' / name
    root.mkdir(parents=True)
    fixture(root)
    conf = root / 'mods.d/test.conf'
    conf.write_bytes(conf.read_bytes().replace(b'[Test]', f'[{name}]'.encode()))
    if long_text:
        import Sword
        module = Sword.RawText(str(root / 'modules/texts/rawtext/test'), name, 'Test data only')
        for reference in ['Gen.1.1', 'Gen.2.1']:
            module.setKey(Sword.VerseKey(reference))
            module.setEntry((f'SENTINEL {name} — test data only. ' * 300))
        del module
    (root / '.complete').write_text(name)
    return root


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK display (use xvfb-run)')
class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application, Gtk
        cls.app = Application()
        cls.app.register()
        Gtk.Settings.get_default().set_property('gtk-enable-animations', False)

    def window(self, directory):
        from bible.ui import Library, Window
        window = Window(self.app, Library(Path(directory) / 'translations'))
        self.addCleanup(lambda: window.close() if not window.closed else None)
        window.present()
        return window

    def test_empty_profile_and_async_failure_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            window = self.window(directory)
            self.assertIsNone(window.active_tab.reader)
            dialog = window.open_library()
            with patch('bible.catalogue_window.catalogue', side_effect=OSError('offline test')):
                dialog.load_catalogue()
                self.assertTrue(dialog.busy)
                self.assertFalse(dialog.catalogue_button.get_sensitive())
                spin(lambda: not dialog.busy)
            self.assertIn('offline test', dialog.status.get_text())
            self.assertTrue(dialog.catalogue_button.get_sensitive())
            with patch('bible.catalogue_window.catalogue', return_value=[]):
                dialog.load_catalogue()
                spin(lambda: not dialog.busy)
            self.assertFalse(dialog.download_button.get_sensitive())
            dialog.close()
            window.close()

    def test_independent_passages_translations_and_closing(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            installed_fixture(directory, 'Other')
            window = self.window(directory)
            first = window.active_tab
            first.translations.set_selected(first.names.index('Test'))
            first.reference.set_text('Gen.2.1')
            first.new_passage.emit('clicked')
            second = window.active_tab
            self.assertIsNot(first, second)
            self.assertEqual(first.current.reference, 'Gen.1')
            self.assertEqual(second.current.reference, 'Gen.2')
            self.assertIsNot(first.reader, second.reader)
            second.translations.set_selected(second.names.index('Other'))
            second.following.emit('clicked')
            self.assertEqual(first.state.resource, 'Test')
            self.assertEqual(first.current.reference, 'Gen.1')
            self.assertEqual(second.state.resource, 'Other')
            self.assertEqual(second.current.reference, 'Gen.3')
            window.close_tab()
            self.assertEqual(window.view.get_n_pages(), 1)
            self.assertIs(window.active_tab, first)
            window.save_session()
            self.assertEqual(len(window.store.load().tabs), 1)
            window.close()

    def test_restore_tabs_selection_scroll_and_study(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory, long_text=True)
            window = self.window(directory)
            window.set_default_size(1000, 550)
            first = window.active_tab
            window.study_button.set_active(True)
            spin(lambda: not first._restoring_scroll)
            adjustment = first.scroll.get_vadjustment()
            maximum = adjustment.get_upper() - adjustment.get_page_size()
            self.assertGreater(maximum, 100)
            adjustment.set_value(maximum * 0.55)
            first_fraction = first.state.scroll
            second = window.new_tab()
            second.show('Gen.2.1')
            spin(lambda: not second._restoring_scroll)
            adjustment = second.scroll.get_vadjustment()
            adjustment.set_value((adjustment.get_upper() - adjustment.get_page_size()) * 0.35)
            window.close()
            restored = self.window(directory)
            restored.set_default_size(1000, 550)
            self.assertEqual(restored.view.get_n_pages(), 2)
            self.assertEqual(restored.active_tab.state.reference, 'Gen.2.1')
            spin(lambda: not restored.active_tab._restoring_scroll)
            self.assertAlmostEqual(restored.active_tab.state.scroll, 0.35, delta=0.04)
            restored.view.set_selected_page(restored.view.get_nth_page(0))
            spin(lambda: not restored.active_tab._restoring_scroll)
            self.assertEqual(restored.active_tab.state.reference, 'Gen.1.1')
            self.assertTrue(restored.split.get_show_sidebar())
            self.assertAlmostEqual(restored.active_tab.state.scroll, first_fraction, delta=0.04)
            restored.close()

    def test_missing_translation_keeps_passage_and_other_tabs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = installed_fixture(directory)
            installed_fixture(directory, 'Other')
            window = self.window(directory)
            tab = window.active_tab
            tab.translations.set_selected(tab.names.index('Test'))
            tab.show('Gen.2.1')
            window.new_tab().translations.set_selected(0)
            window.close()
            shutil.rmtree(root)
            restored = self.window(directory)
            restored.view.set_selected_page(restored.view.get_nth_page(0))
            tab = restored.active_tab
            self.assertIsNone(tab.reader)
            self.assertEqual(tab.state.reference, 'Gen.2.1')
            self.assertEqual(tab.state.resource, 'Test')
            self.assertNotEqual(tab.status.get_text(), 'Ready')
            self.assertIsNotNone(restored.tabs()[1].reader)
            restored.close()
            self.assertEqual(restored.store.load().tabs[0].resource, 'Test')

    def test_study_releases_width_and_adapts_to_narrow_window(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = self.window(directory)
            window.set_default_size(1000, 600)
            tab = window.active_tab
            spin(lambda: tab.get_width() > 800)
            full_width = tab.get_width()
            window.study_button.set_active(True)
            spin(lambda: tab.get_width() < full_width - 150)
            window.study_button.set_active(False)
            spin(lambda: tab.get_width() >= full_width - 10)
            window.set_default_size(540, 600)
            spin(lambda: window.split.get_collapsed())
            self.assertGreater(tab.text.get_width(), 300)
            window.lookup_action('new-tab').activate(None)
            self.assertEqual(window.view.get_n_pages(), 2)
            window.lookup_action('close-tab').activate(None)
            self.assertEqual(window.view.get_n_pages(), 1)
            window.close()

    def test_corrupt_session_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            session_file = Path(directory) / 'session.json'
            session_file.write_text('{broken')
            window = self.window(directory)
            self.assertTrue(window.session_status.get_visible())
            window.new_tab()
            window.close()
            self.assertEqual(session_file.read_text(), '{broken')

    def test_closed_last_tab_leaves_a_usable_empty_tab(self):
        with tempfile.TemporaryDirectory() as directory:
            window = self.window(directory)
            window.close_tab()
            self.assertEqual(window.view.get_n_pages(), 1)
            self.assertIsNone(window.active_tab.state.resource)
            window.close()

    def test_hidden_download_window_finishes_and_refreshes_the_active_empty_tab(self):
        import threading
        with tempfile.TemporaryDirectory() as directory:
            window = self.window(directory)
            first = window.active_tab
            window.new_tab()
            installed_fixture(directory)
            dialog = window.open_library()
            release = threading.Event()
            try:
                dialog.task('Downloading…', lambda: release.wait(3),
                            lambda _: window.resource_installed('Test'))
                dialog.close()
                self.assertFalse(dialog.closed)
                self.assertFalse(dialog.get_visible())
                release.set()
                spin(lambda: not dialog.busy)
                self.assertEqual(window.active_tab.state.resource, 'Test')
                self.assertIsNotNone(window.active_tab.reader)
                self.assertIsNone(first.state.resource)
                self.assertIn('Test', first.names)
            finally:
                release.set()
                window.close()

    def test_reordered_tabs_restore_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = self.window(directory)
            second = window.new_tab()
            second.show('Gen.2.1')
            window.view.reorder_page(window.view.get_selected_page(), 0)
            window.close()
            restored = self.window(directory)
            self.assertEqual([tab.state.reference for tab in restored.tabs()], ['Gen.2.1', 'Gen.1.1'])
            self.assertEqual(restored.active_tab.state.reference, 'Gen.2.1')
            restored.close()
