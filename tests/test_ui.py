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


def installed_fixture(directory, name='Test', long_text=False, entries=None, versification='KJV', nt_only=False):
    from tests.fixtures import module_fixture
    root = Path(directory) / 'translations' / name
    module_fixture(root, name, entries if entries is not None else [
        ('Gen.1.1', 'SENTINEL α <literal>'), ('Gen.1.2', 'SECOND SENTINEL'),
        ('Gen.2.1', 'NEXT CHAPTER'), ('Gen.3.1', 'THIRD CHAPTER'),
        ('John.1.1', 'JOHN TEST DATA'), ('John.3.16', 'JOHN 3:16 TEST DATA'),
        ('John.3.17', 'JOHN 3:17 TEST DATA')], versification, nt_only)
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
            self.assertTrue(window.navigate_selection('Test', 'Gen.1.1'))
            window.choose_passage(direct=True)
            window.navigation.direct.set_text('Gen.2.1')
            window.navigation.new_button.emit('clicked')
            second = window.active_tab
            self.assertIsNot(first, second)
            self.assertEqual(first.current.reference, 'Gen.1')
            self.assertEqual(second.current.reference, 'Gen.2')
            self.assertIsNot(first.reader, second.reader)
            window.navigate_selection('Other', 'Gen.2.1')
            window.following.emit('clicked')
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
            window.navigate_selection('Test', 'Gen.1.1')
            tab.show('Gen.2.1')
            window.new_tab()
            window.navigate_selection('Other', 'Gen.2.1')
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
                window.view.set_selected_page(window.view.get_nth_page(0))
                window.choose_passage()
                self.assertIn('Test', window.navigation.names)
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

    def test_manual_scroll_to_top_wins_over_the_original_verse_target(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory, long_text=True)
            window = self.window(directory)
            first = window.active_tab
            first.show('Gen.1.2')
            spin(lambda: not first._restoring_scroll)
            self.assertGreater(first.scroll.get_vadjustment().get_value(), 100)
            first.scroll.get_vadjustment().set_value(0)
            self.assertEqual(first.state.scroll, 0)
            window.new_tab()
            window.view.set_selected_page(window.view.get_nth_page(0))
            spin(lambda: not first._restoring_scroll)
            self.assertEqual(first.scroll.get_vadjustment().get_value(), 0)
            window.close()
            restored = self.window(directory)
            spin(lambda: not restored.active_tab._restoring_scroll)
            self.assertEqual(restored.active_tab.state.reference, 'Gen.1.2')
            self.assertEqual(restored.active_tab.scroll.get_vadjustment().get_value(), 0)
            restored.close()

    def test_header_selector_reaches_john_and_changes_version_without_reference_input(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            installed_fixture(directory, 'Other')
            window = self.window(directory)
            window.choose_passage()
            nav = window.navigation
            nav.version.set_selected(nav.names.index('Test'))
            genesis = [book.code for book in nav.books].index('Gen')
            self.assertIn(nav.book.get_model().get_string(genesis), ('Genesis', 'Genèse'))
            nav.book.set_selected([book.code for book in nav.books].index('John'))
            nav.chapter.set_selected(nav.chapters.index(3))
            nav.verse.set_selected(nav.verses.index(16))
            nav.open_button.emit('clicked')
            self.assertEqual(window.active_tab.state.reference, 'John.3.16')
            self.assertIn('3:16', window.heading.get_title())
            self.assertEqual(window.heading.get_subtitle(), 'Test')
            window.choose_passage()
            nav.version.set_selected(nav.names.index('Other'))
            self.assertEqual(window.active_tab.state.resource, 'Test')  # Staged until Open.
            nav.open_button.emit('clicked')
            self.assertEqual(window.active_tab.state.resource, 'Other')
            self.assertEqual(window.active_tab.state.reference, 'John.3.16')
            self.assertEqual(window.heading.get_subtitle(), 'Other')
            window.close()

    def test_header_and_selector_follow_active_tab_and_restoration(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = self.window(directory)
            window.navigate_selection('Test', 'John.3.16')
            first = window.active_tab
            window.choose_passage()
            nav = window.navigation
            nav.book.set_selected([book.code for book in nav.books].index('Gen'))
            nav.chapter.set_selected(nav.chapters.index(2))
            nav.new_button.emit('clicked')
            self.assertEqual(window.view.get_n_pages(), 2)
            self.assertEqual(first.state.reference, 'John.3.16')
            self.assertIn('2:1', window.heading.get_title())
            window.previous.emit('clicked')
            self.assertIn('1:1', window.heading.get_title())
            window.view.set_selected_page(window.view.get_nth_page(0))
            self.assertIn('3:16', window.heading.get_title())
            self.assertEqual(nav.selected_reference(), 'John.3.16')
            window.close()
            restored = self.window(directory)
            self.assertIn('3:16', restored.heading.get_title())
            self.assertEqual(restored.navigation.selected_reference(), 'John.3.16')
            self.assertEqual(restored.navigation.selected_resource(), 'Test')
            restored.close()

    def test_nt_only_selector_and_direct_french_reference(self):
        from tests.test_navigation import NT_ENTRIES
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory, 'NTTest', entries=NT_ENTRIES, nt_only=True)
            window = self.window(directory)
            self.assertEqual(window.active_tab.state.reference, 'Matt.1.1')
            window.choose_passage()
            nav = window.navigation
            self.assertEqual([book.code for book in nav.books], ['Matt', 'John', 'Rev'])
            nav.book.set_selected(1)
            self.assertEqual(nav.chapters, [3])
            self.assertEqual(nav.verses, [16, 18])
            nav.open_button.emit('clicked')
            self.assertEqual(window.active_tab.state.reference, 'John.3.16')
            window.lookup_action('reference').activate(None)
            self.assertTrue(nav.direct_expander.get_expanded())
            nav.direct.set_text('Gen.1.1')
            nav.open_button.emit('clicked')
            self.assertEqual(window.active_tab.state.reference, 'John.3.16')
            self.assertTrue(nav.status.get_visible())
            nav.direct.set_text('Jean 3:18')
            nav.open_button.emit('clicked')
            self.assertEqual(window.active_tab.state.reference, 'John.3.18')
            self.assertIn('3:18', window.heading.get_title())
            window.close()

    def test_header_at_360_pixels_and_study_to_the_right(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = self.window(directory)
            window.set_default_size(1000, 600)
            window.study_button.set_active(True)
            spin(lambda: window.active_tab.get_width() > 400)
            _, bible = window.active_tab.compute_bounds(window)
            _, study = window.split.get_sidebar().compute_bounds(window)
            self.assertLess(bible.origin.x, study.origin.x)
            self.assertLessEqual(bible.origin.x + bible.size.width, study.origin.x + 1)
            window.set_default_size(360, 600)
            spin(lambda: window.get_width() <= 380 and window.split.get_collapsed())
            self.assertGreater(window.passage_button.get_width(), 50)
            self.assertFalse(window.previous.get_visible())
            window.study_button.set_active(False)
            window.lookup_action('choose-passage').activate(None)
            spin(lambda: window.navigation.get_visible())
            self.assertLessEqual(window.navigation.get_width(), 360,
                                 f'window={window.get_width()}, content=' + str([
                                     widget.measure(0, -1)[:2] for widget in
                                     (window.navigation.version, window.navigation.direct,
                                      window.navigation.new_button)]))
            window.close()

    def test_selected_verse_is_visible_after_wrapped_text_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            entries = [(f'John.3.{verse}', f'SENTINEL {verse} ' * 30) for verse in range(1, 31)]
            installed_fixture(directory, entries=entries)
            window = self.window(directory)
            window.navigate_selection('Test', 'Jean 3:16')
            tab = window.active_tab
            spin(lambda: not tab._restoring_scroll, duration=0.3)
            iterator = tab.text.get_buffer().get_iter_at_offset(tab._verse_offsets['John.3.16'])
            target = tab.text.get_iter_location(iterator)
            visible = tab.text.get_visible_rect()
            self.assertGreaterEqual(target.y, visible.y - 2)
            self.assertLess(target.y, visible.y + visible.height)
            window.close()
