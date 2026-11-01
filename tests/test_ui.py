import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch


def spin(until=lambda: True, duration=0.1, timeout=4):
    from bible.ui import GLib
    deadline = time.monotonic() + timeout
    minimum = time.monotonic() + duration
    loop = GLib.MainLoop()
    settled = False
    errors = []
    def check():
        try:
            return check_condition()
        except BaseException as error:
            errors.append(error)
            loop.quit()
            return False
    def check_condition():
        nonlocal settled
        now = time.monotonic()
        if now >= minimum and until():
            settled = True
            loop.quit()
            return False
        if now >= deadline:
            loop.quit()
            return False
        return True
    # Run the native event loop: processing just one event every 5 ms can
    # starve idle completions behind frame/layout events in a full GTK suite.
    GLib.timeout_add(5, check)
    loop.run()
    if errors:
        raise errors[0]
    if not settled:
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


def close_test_dialogs():
    from bible.ui import Adw, Gtk
    # response() emits the signal without the native button's dismissal.
    # Release test-created modal grabs before another window receives input.
    for dialog in Gtk.Window.list_toplevels():
        if isinstance(dialog,Adw.MessageDialog):dialog.destroy()


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK display (use xvfb-run)')
class WindowTests(unittest.TestCase):
    def test_metadata_focus_does_not_select_but_explicit_selection_does(self):
        from bible.library import Resource
        with tempfile.TemporaryDirectory() as directory:
            window = self.window(directory)
            with patch('bible.catalogue_window.catalogue', return_value=[Resource('Test','Resource test','fr','Public Domain')]):
                dialog = window.open_library(); dialog.load_catalogue()
                spin(lambda: not dialog.busy)
                for _ in range(2):
                    dialog.open_details(None, 0); spin()
                    self.assertFalse(dialog.metadata.get_selection_bounds()[0])
                    dialog.metadata.grab_focus(); spin()
                    self.assertFalse(dialog.metadata.get_selection_bounds()[0])
                    dialog.metadata.select_region(0, 10)
                    self.assertTrue(dialog.metadata.get_selection_bounds()[0])
                    self.assertTrue(dialog.metadata.get_selectable())
                    dialog.back_to_list()
                dialog.close()

    @classmethod
    def setUpClass(cls):
        from bible.ui import Application, Gtk
        cls.app = Application.get_default() or Application()
        cls.app.register()
        Gtk.Settings.get_default().set_property('gtk-enable-animations', False)

    def tearDown(self):
        close_test_dialogs()

    def window(self, directory):
        from bible.ui import Library, Window
        # These are interaction/data fixtures. Catalogue network integration is
        # tested separately; an automatic refresh must not race a local transfer
        # or turn a four-second GTK assertion into an external HTTP timeout.
        self.enterContext(patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False))
        window = Window(self.app, Library(Path(directory) / 'translations'))
        # These regression fixtures cover multiple languages, independently of
        # the locale-default contract exercised by test_library_polish.
        window.application_settings.set('library_language','')
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
            window.lookup_action('new-tab').activate(None)
            window.choose_passage(direct=True)
            window.navigation.direct.set_text('Gen.2.1')
            window.navigation.direct.emit('activate')
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

    def test_hidden_download_window_finishes_without_selecting_an_empty_tab(self):
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
                self.assertIsNone(window.active_tab.state.resource)
                self.assertIsNone(window.active_tab.reader)
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
            self.assertIn(nav.book_rows['Gen'].get_child().get_text(), ('Genesis', 'Genèse'))
            nav.book_list.emit('row-activated', nav.book_rows['John'])
            nav.chapter_buttons[3].emit('clicked')
            self.assertEqual(window.active_tab.state.reference,'John.3.16')
            self.assertFalse(nav.get_visible())
            window.choose_passage();nav.direct.set_text('Jean 3:16');nav.direct.emit('activate')
            self.assertEqual(window.active_tab.state.reference, 'John.3.16')
            self.assertIn('3:16', window.heading.get_title())
            self.assertEqual(window.heading.get_subtitle(), 'Test')
            window.choose_passage()
            nav.version.set_selected(nav.names.index('Other'))
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
            window.lookup_action('new-tab').activate(None)
            window.choose_passage()
            nav = window.navigation
            nav.book_list.emit('row-activated', nav.book_rows['Gen'])
            nav.chapter_buttons[2].emit('clicked')
            self.assertEqual(window.active_tab.state.reference,'Gen.2.1')
            self.assertFalse(nav.get_visible())
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
            nav.book_list.emit('row-activated', nav.book_rows['John'])
            self.assertEqual(nav.chapters, [3])
            self.assertEqual(nav.verses, [16, 18])
            self.assertEqual(window.active_tab.state.reference,'Matt.1.1')
            nav.chapter_buttons[3].emit('clicked')
            self.assertEqual(window.active_tab.state.reference, 'John.3.16')
            window.lookup_action('reference').activate(None)
            self.assertTrue(nav.direct.get_mapped())
            nav.direct.set_text('Gen.1.1')
            nav.direct.emit('activate')
            self.assertEqual(window.active_tab.state.reference, 'John.3.16')
            self.assertTrue(nav.status.get_visible())
            nav.direct.set_text('Jean 3:18')
            nav.direct.emit('activate')
            self.assertEqual(window.active_tab.state.reference, 'John.3.18')
            self.assertIn('3:18', window.heading.get_title())
            window.close()

    def test_header_at_360_pixels_and_full_height_study_to_the_right(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = self.window(directory)
            window.set_default_size(1000, 600)
            window.study_button.set_active(True)
            spin(lambda: window.active_tab.get_width() > 400)
            _, bible = window.active_tab.compute_bounds(window)
            _, study = window.split.get_sidebar().compute_bounds(window)
            self.assertGreater(study.origin.x, bible.origin.x)
            self.assertLessEqual(bible.origin.x + bible.size.width, study.origin.x + 1)
            self.assertEqual(window.header.get_height(),window.study.header.get_height())
            self.assertFalse(window.header.get_show_end_title_buttons())
            self.assertTrue(window.study.header.get_show_end_title_buttons())
            window.set_default_size(360, 600)
            spin(lambda: window.get_width() <= 380 and window.split.get_collapsed())
            self.assertTrue(window.previous.get_visible())
            window.study_button.set_active(False)
            spin(lambda:window.passage_button.get_mapped())
            self.assertGreater(window.passage_button.get_width(),50)
            window.lookup_action('choose-passage').activate(None)
            spin(lambda: window.navigation.get_visible())
            self.assertLessEqual(window.navigation.get_width(), 360,
                                 f'window={window.get_width()}, content=' + str([
                                     widget.measure(0, -1)[:2] for widget in
                                     (window.navigation.version, window.navigation.direct,
                                      window.navigation.search)]))
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

    def test_catalogue_language_search_conditions_and_locked_resource(self):
        from bible.library import Resource
        from bible.i18n import tr
        resources = [
            Resource('FreTest', 'Bible annotée — test fixture', 'fr', 'Copyrighted',
                     about='<p>Attribution fixture</p><script>UNTRUSTED_SCRIPT</script>',
                     conditions='Personal reading only.'),
            Resource('Locked', 'Locked fixture', 'fr', 'Copyrighted', locked=True),
            Resource('English', 'English fixture', 'en', 'Creative Commons: BY 4.0'),
        ]
        with tempfile.TemporaryDirectory() as directory:
            window = self.window(directory)
            dialog = window.open_library()
            with patch('bible.catalogue_window.catalogue', return_value=resources):
                dialog.load_catalogue()
                spin(lambda: not dialog.busy)
            dialog.language.set_selected(dialog.languages.index('fr'))
            self.assertEqual([r.name for r in dialog.filtered_resources], ['FreTest', 'Locked'])
            dialog.search.set_text('ANNOTEE')
            dialog.filter_resources()
            self.assertEqual([r.name for r in dialog.filtered_resources], ['FreTest'])
            for text in ['Copyrighted', 'Personal reading only.', 'Attribution fixture', 'CrossWire']:
                self.assertIn(text, dialog.metadata.get_text())
            self.assertNotIn('UNTRUSTED_SCRIPT', dialog.metadata.get_text())
            self.assertTrue(dialog.download_button.get_sensitive())
            dialog.search.set_text('Locked')
            dialog.filter_resources()
            self.assertFalse(dialog.download_button.get_sensitive())
            self.assertIn(tr('Access key required. Encrypted resources are not supported.'),
                          dialog.metadata.get_text())
            with patch.object(dialog.library, 'install', side_effect=AssertionError('Must not download')):
                dialog.install()
            dialog.search.set_text('absent')
            dialog.filter_resources()
            self.assertFalse(dialog.download_button.get_sensitive())
            self.assertIn(tr('No matching resource.'), dialog.metadata.get_text())
            dialog.close()
            window.close()

    def test_installed_attribution_is_available_without_loading_catalogue(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = self.window(directory)
            with patch('urllib.request.urlopen', side_effect=AssertionError('Offline')):
                dialog = window.open_library()
                dialog.language.set_selected(0)
                spin(lambda:not dialog.preparing and not dialog._building_rows)
                self.assertEqual([r.name for r in dialog.filtered_resources], ['Test'])
                self.assertIn('CrossWire', dialog.metadata.get_text())
                self.assertIn('Public Domain', dialog.metadata.get_text())
                self.assertFalse(dialog.download_button.get_sensitive())
                dialog.close()
            window.close()

    def study_text(self, window):
        buffer = window.study.text.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

    def choose_commentary(self, window, name):
        window.study.refresh(force=True)
        window.study.choices.set_selected(window.study.names.index(name))

    def test_commentary_follows_clicked_verse_and_keyboard_without_stale_text(self):
        from tests.test_commentary import commentary_fixture
        from bible.i18n import tr
        from bible.ui import Gtk
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            commentary_fixture(directory)
            window = self.window(directory)
            tab = window.active_tab
            window.lookup_action('study').activate(None)
            self.choose_commentary(window, 'Notes')
            spin(lambda: not tab._restoring_scroll)
            self.assertIn('COMMENTARY TEST DATA', self.study_text(window))
            self.assertIn('CrossWire', window.study.source.get_text())
            self.assertIn('Public Domain', window.study.metadata.get_text())
            self.assertIn('עברית', self.study_text(window))
            iterator = tab.text.get_buffer().get_iter_at_offset(tab._verse_offsets['Gen.1.2'] + 3)
            rect = tab.text.get_iter_location(iterator)
            x, y = tab.text.buffer_to_window_coords(Gtk.TextWindowType.WIDGET, rect.x + 2, rect.y + 2)
            tab.verse_click.emit('released', 1, float(x), float(y))
            self.assertEqual(tab.state.reference, 'Gen.1.2')
            self.assertIn('COMMENTARY TEST DATA',self.study_text(window))
            self.assertIsNone(window.study.current_position)
            self.assertEqual(window.study.status.get_text(), tr('No commentary for this passage.'))
            window.lookup_action('previous-verse').activate(None)
            self.assertEqual(tab.state.reference, 'Gen.1.1')
            self.assertIn('COMMENTARY TEST DATA', self.study_text(window))
            window.navigate_selection('Test', 'John.3.16')
            self.assertIn('JOHN COMMENTARY', self.study_text(window))
            window.lookup_action('next-verse').activate(None)
            self.assertEqual(tab.state.reference, 'John.3.17')
            self.assertIn('JOHN COMMENTARY',self.study_text(window))
            self.assertIsNone(window.study.current_position)
            window.new_tab()
            self.assertIn('JOHN COMMENTARY',self.study_text(window))
            window.view.set_selected_page(window.view.get_nth_page(0))
            self.assertIn('JOHN COMMENTARY',self.study_text(window))
            window.close()

    def test_commentary_choice_restores_per_tab_and_missing_resource_is_kept(self):
        from tests.test_commentary import commentary_fixture
        from bible.i18n import tr
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            first_root = commentary_fixture(directory, 'Notes')
            commentary_fixture(directory, 'OtherNotes', entries=[('Gen.1.1', 'SECOND COMMENTARY TEST DATA')])
            window = self.window(directory)
            self.choose_commentary(window, 'Notes')
            window.study_button.set_active(True)
            window.new_tab()
            self.choose_commentary(window, 'OtherNotes')
            window.study_button.set_active(True)
            self.assertIn('SECOND COMMENTARY', self.study_text(window))
            window.view.set_selected_page(window.view.get_nth_page(0))
            self.assertEqual(window.active_tab.state.commentary, 'Notes')
            self.assertNotIn('SECOND COMMENTARY', self.study_text(window))
            window.close()
            restored = self.window(directory)
            self.assertEqual(restored.active_tab.state.commentary, 'Notes')
            self.assertIn('COMMENTARY TEST DATA', self.study_text(restored))
            restored.view.set_selected_page(restored.view.get_nth_page(1))
            self.assertIn('SECOND COMMENTARY', self.study_text(restored))
            restored.close()
            shutil.rmtree(first_root)
            missing = self.window(directory)
            missing.view.set_selected_page(missing.view.get_nth_page(0))
            self.assertEqual(missing.active_tab.state.commentary, 'Notes')
            self.assertEqual(self.study_text(missing), '')
            self.assertIn(tr('This commentary is no longer installed. Choose another or download it again.'),
                          missing.study.status.get_text())
            missing.close()
            self.assertEqual(missing.store.load().tabs[0].commentary, 'Notes')

    def test_commentary_types_mismatch_and_install_refresh(self):
        from tests.test_commentary import commentary_fixture
        from bible.i18n import tr
        with tempfile.TemporaryDirectory() as directory:
            commentary_fixture(directory, 'Notes')
            window = self.window(directory)
            self.assertIsNone(window.active_tab.state.resource)
            window.resource_installed('Notes')
            self.assertIsNone(window.active_tab.state.resource)
            self.assertIsNone(window.active_tab.state.commentary)
            window.open_installed_resource('Notes')
            self.assertEqual(window.active_tab.state.commentary, 'Notes')
            self.assertEqual(self.study_text(window), '')
            installed_fixture(directory)
            window.resource_installed('Test')
            self.assertIsNone(window.active_tab.state.resource)
            window.open_installed_resource('Test')
            self.assertEqual(window.active_tab.state.resource, 'Test')
            self.assertIn('COMMENTARY TEST DATA', self.study_text(window))
            window.navigation.sync(force=True)
            self.assertEqual(window.navigation.names, ['Test'])
            commentary_fixture(directory, 'CatholicNotes', versification='LXX')
            self.choose_commentary(window, 'CatholicNotes')
            self.assertEqual(self.study_text(window), '')
            self.assertIn(tr('No verified alignment for this passage.'),
                          window.study.status.get_text())
            self.assertIn('LXX', window.study.status.get_text())
            resources = [window.library.resource(name) for name in window.library.installed()]
            with patch('bible.catalogue_window.catalogue', return_value=resources):
                dialog = window.open_library('commentary')
                dialog.load_catalogue()
                spin(lambda: not dialog.busy)
            self.assertEqual({r.name for r in dialog.filtered_resources}, {'CatholicNotes', 'Notes'})
            dialog.kind.set_selected(0)
            self.assertEqual([r.name for r in dialog.filtered_resources], ['Test'])
            dialog.close()
            window.close()

    def test_commentary_remains_readable_in_one_narrow_overlay(self):
        from tests.test_commentary import commentary_fixture
        directory=self.enterContext(tempfile.TemporaryDirectory())
        installed_fixture(directory)
        commentary_fixture(directory)
        commentary_fixture(directory, 'OtherNotes', entries=[('Gen.1.1', 'OTHER COMMENTARY TEST DATA')])
        window = self.window(directory)
        window.set_default_size(1000, 600)
        window.study_button.set_active(True)
        self.choose_commentary(window, 'Notes')
        spin(lambda: window.active_tab.get_width() > 400)
        _, bible = window.active_tab.compute_bounds(window)
        _, study = window.study.compute_bounds(window)
        self.assertLessEqual(bible.origin.x + bible.size.width, study.origin.x + 1)
        reading_width = window.active_tab.get_width()
        window.lookup_action('study').activate(None)
        spin(lambda: window.active_tab.get_width() > reading_width)
        window.study_button.set_active(True)
        window.set_default_size(360, 600)
        # Collapsed is notified before the new child allocation is complete.
        spin(lambda: window.get_width() <= 380 and window.split.get_collapsed()
             and window.active_tab.get_width() >= 340
             and window.study.get_width() <= window.get_width())
        self.assertGreaterEqual(window.active_tab.get_width(), 340)
        self.assertLessEqual(window.study.get_width(), window.get_width())
        self.choose_commentary(window, 'OtherNotes')
        self.assertEqual(window.study.entry_text, 'OTHER COMMENTARY TEST DATA')
        window.study.info.set_active(True)
        spin(lambda: window.study.info.get_popover().get_visible())
        self.assertLessEqual(window.study.info.get_popover().get_width(), 360)
        window.close()


    def write_note(self, window, text, labels=()):
        editor = window.new_note(force_new=True)
        self.assertIsNotNone(editor)
        editor.body.get_buffer().set_text(text)
        for label in labels:
            editor.labels.entry.set_text(label)
            editor.labels.add()
        self.assertTrue(editor.save(close=False), editor.status.get_text())
        note = editor.note
        editor.close()
        self.assertTrue(editor.closed)
        return note

    def test_passage_notes_range_survive_translation_language_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            origin = installed_fixture(directory)
            other = installed_fixture(directory, 'Other')
            path = other / 'mods.d/test.conf'
            path.write_bytes(path.read_bytes().replace(b'Lang=en', b'Lang=de'))
            window = self.window(directory)
            window.navigate_selection('Test', 'Gen.1.1')
            tab = window.active_tab
            buffer = tab.text.get_buffer()
            buffer.select_range(buffer.get_start_iter(), buffer.get_end_iter())
            first = self.write_note(window, '**Ancienne** note sur deux versets', ['Étude', 'Foi'])
            self.assertEqual((first.start, first.end), ('Gen.1.1', 'Gen.1.2'))
            self.assertEqual((first.origin_translation, first.origin_language), ('Test', 'en'))
            self.assertIn('Gen.1.2', tab._note_refs)
            self.assertEqual(len(tab.text._inline_buttons),1)
            self.assertTrue(all(ref=='Gen.1.1' for ref,kind,_ in tab._document.inline.values() if kind=='note'))
            window.navigate_selection('Other', 'Gen.1.2')
            self.assertFalse(hasattr(tab,'note_button'))
            editor = window.open_passage_notes()
            self.assertEqual(editor.note.id, first.id)
            self.assertEqual(editor.context['origin_translation'], 'Test')
            editor.close()
            window.navigate_selection('Other', 'Gen.2.1')
            second = self.write_note(window, 'Seconde note', ['Lecture'])
            self.assertEqual(second.origin_language, 'de')
            central = window.open_notes()
            central.search.set_text('ancienne')
            central.labels.entry.set_text('FOI')
            central.labels.add()
            central.refresh()
            self.assertEqual([a.note.id for a in central.rows if a.note], [first.id])
            central.search.set_text('Genèse 1:1')
            central.refresh()
            self.assertEqual([a.note.id for a in central.rows if a.note], [first.id])
            central.list.emit('activate', 0)
            self.assertEqual(window.active_tab.state.reference, 'Gen.2.1')  # Editing in My notes does not navigate the reader.
            self.assertEqual(window.note_editor.note.id, first.id)
            window.note_editor.close()
            window.close()
            shutil.rmtree(origin)
            reopened = self.window(directory)
            self.assertEqual(len(reopened.notes_store.all()), 2)
            self.assertEqual(reopened.notes_store.get(first.id), first)
            editor = reopened.open_saved_note(first)
            self.assertEqual(reopened.active_tab.state.resource, 'Other')
            self.assertEqual(reopened.active_tab.state.reference, 'Gen.1.1')
            self.assertEqual(editor.note.body, first.body)
            editor.close()
            reopened.close()

    def test_incompatible_note_stays_accessible_without_false_marker(self):
        from bible.i18n import tr
        with tempfile.TemporaryDirectory() as directory:
            origin = installed_fixture(directory)
            installed_fixture(directory, 'CatholicBible', versification='Catholic')
            window = self.window(directory)
            window.navigate_selection('Test', 'Gen.1.1')
            note = self.write_note(window, 'Original KJV note', ['Keep'])
            window.navigate_selection('CatholicBible', 'Gen.1.1')
            self.assertFalse(hasattr(window.active_tab,'note_button'))
            self.assertEqual(window.active_tab._note_refs, {})
            shutil.rmtree(origin)
            editor = window.open_saved_note(note)
            self.assertEqual(window.active_tab.state.resource, 'CatholicBible')
            self.assertIn(tr('No compatible translation installed. The note remains available.'), editor.status.get_text())
            self.assertEqual(editor.note.body, note.body)
            self.assertEqual(editor.note.labels, ('Keep',))
            editor.close()
            central = window.open_notes()
            self.assertEqual([a.note.id for a in central.rows if a.note], [note.id])
            window.close()

    def test_note_delete_and_unsaved_close_require_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = self.window(directory)
            note = self.write_note(window, 'Keep until confirmed', ['Keep'])
            editor = window.open_saved_note(note)
            editor.ask_delete()
            editor._confirmation.response('cancel')
            self.assertIsNotNone(window.notes_store.get(note.id))
            editor.ask_delete()
            editor._confirmation.response('confirm')
            self.assertTrue(editor.closed)
            self.assertIsNone(window.notes_store.get(note.id))
            self.assertFalse(hasattr(window.active_tab,'note_button'))
            draft = window.new_note(force_new=True)
            draft.body.get_buffer().set_text('Unsaved draft')
            draft.close()
            self.assertFalse(draft.closed)
            draft._confirmation.response('cancel')
            self.assertFalse(draft.closed)
            window.close()
            self.assertFalse(window.closed)
            draft._confirmation.response('cancel')
            self.assertTrue(draft.save())
            self.assertFalse(window.closed)
            self.assertEqual(window.notes_store.all()[0].body, 'Unsaved draft')
            window.close()

    def test_notes_backup_restore_and_safe_preview_remain_local(self):
        from bible.notes_window import buffer_text
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = self.window(directory)
            with patch('urllib.request.urlopen', side_effect=AssertionError('No network for notes')):
                note = self.write_note(window, '**Gras**\n- עברית\n<script>bad()</script>\n[x](javascript:bad)', ['Local'])
                editor = window.open_saved_note(note)
                self.assertIn('Gras', buffer_text(editor.preview))
                self.assertIn('<script>bad()</script>', buffer_text(editor.preview))
                self.assertIn('javascript:bad', buffer_text(editor.preview))
                self.assertIsNotNone(editor.labels.entry.get_completion())
                editor.close()
                central = window.open_notes()
                backup = Path(directory) / 'backup.json'
                self.assertTrue(central.backup_to(backup))
                window.notes_store.delete(note)
                self.assertTrue(central.restore_from(backup))
                self.assertEqual(window.notes_store.get(note.id), note)
                self.assertIn('Gen.1.1', window.active_tab._note_refs)
                backup.write_text('invalid')
                self.assertFalse(central.restore_from(backup))
                self.assertEqual(window.notes_store.get(note.id), note)
            window.close()

    def test_note_windows_at_360_pixels_and_commentary_independence(self):
        from tests.test_commentary import commentary_fixture
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            commentary_fixture(directory)
            window = self.window(directory)
            self.choose_commentary(window, 'Notes')
            commentary = self.study_text(window)
            note = self.write_note(window, 'Note text', ['L' * 80])
            self.assertEqual(self.study_text(window), commentary)
            editor = window.open_saved_note(note)
            editor.set_default_size(360, 650)
            spin(lambda: editor.get_width() > 0)
            self.assertLessEqual(editor.get_width(), 360)
            editor.close()
            central = window.open_notes()
            central.set_default_size(360, 650)
            spin(lambda: central.get_width() > 0)
            self.assertLessEqual(central.get_width(), 360)
            self.assertEqual(self.study_text(window), commentary)
            window.close()

    def test_invalid_notes_database_preserves_file_and_reading(self):
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            database = Path(directory) / 'notes.sqlite3'
            original = b'Unrecognized notes data. Preserve me.'
            database.write_bytes(original)
            window = self.window(directory)
            self.assertIsNotNone(window.active_tab.reader)
            self.assertIsNone(window.notes_store)
            self.assertFalse(window.lookup_action('notes').get_enabled())
            self.assertTrue(window.notes_status.get_visible())
            self.assertEqual(database.read_bytes(), original)
            window.close()

    def test_note_formatting_commands_and_catholic_reference_labels(self):
        from bible.notes_window import buffer_text, passage_label
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window = self.window(directory)
            editor = window.new_note(force_new=True)
            buffer = editor.body.get_buffer()
            for text, prefix, suffix, expected in [
                    ('alpha', '**', '**', '**alpha**'),
                    ('alpha', '*', '*', '*alpha*'),
                    ('alpha\nbeta\n', '- ', '', '- alpha\n- beta\n'),
                    ('label', '[', '](https://)', '[label](https://)')]:
                buffer.set_text(text)
                buffer.select_range(buffer.get_start_iter(), buffer.get_end_iter())
                editor.format(prefix, suffix)
                self.assertEqual(buffer_text(editor.body), expected)
            editor.labels.entry.set_text('Pending label')
            self.assertTrue(editor.save(close=False))
            self.assertEqual(editor.note.labels, ('Pending label',))
            self.assertNotIn('Genesis', passage_label('Tob.3.16', versification='Catholic'))
            editor.close()
            window.close()
