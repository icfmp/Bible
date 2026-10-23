import os
from dataclasses import replace
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from bible.library import CatalogueResult, Library
from bible.providers import EXTRA
from tests.test_library import RESOURCE, archive_bytes
from tests.test_ui import installed_fixture, spin
from tests.fixtures import module_fixture


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK display')
class ProviderUITests(unittest.TestCase):
    def setUp(self):
        # These unit cases explicitly supply provider results; do not race an
        # unrelated live auto-refresh while arranging their resource fixtures.
        self.enterContext(patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False))

    def open_library(self,window):
        dialog=window.open_library();spin(lambda:not dialog.preparing)
        return dialog
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application, Gtk
        cls.app = Application.get_default() or Application()
        cls.app.register()
        Gtk.Settings.get_default().set_property('gtk-enable-animations', False)

    def test_failed_install_keeps_resource_error_and_retry_after_selection_and_refresh(self):
        from bible.ui import Window
        from bible.i18n import tr
        with tempfile.TemporaryDirectory() as directory:
            window=Window(self.app,Library(Path(directory)/'translations'));window.present()
            release=threading.Event()
            try:
                dialog=self.open_library(window);dialog.resources=[RESOURCE,replace(RESOURCE,name='Other')]
                dialog.update_languages();dialog.open_details(None,0)
                def failed(*args,**kwargs):
                    release.wait(3);raise ValueError('Conditions really changed')
                with patch.object(window.library,'install',side_effect=failed):
                    dialog.install();dialog.choices.set_selected(1);release.set()
                    spin(lambda:not dialog.busy)
                self.assertEqual(dialog._phase,'error')
                self.assertIn('Test: Conditions really changed',dialog.status.get_text())
                self.assertTrue(dialog.status.get_visible());self.assertTrue(dialog.progress.get_visible())
                self.assertEqual(dialog.download_button.get_label(),tr('Download'))
                dialog.choices.set_selected(0);self.assertEqual(dialog.download_button.get_label(),tr('Retry'))
                with patch('bible.catalogue_window.catalogue',return_value=CatalogueResult(tuple(dialog.resources),{})):
                    dialog.load_catalogue();spin(lambda:not dialog.refreshing)
                self.assertTrue(dialog.status.get_visible())
                self.assertIn('Conditions really changed',dialog.status.get_text())
                self.assertEqual(window.library.installed(),[])
                dialog.close()
            finally:release.set();window.close()

    def test_coptic_catalogue_load_search_and_select(self):
        from bible.ui import Window
        from bible.languages import language_info
        coptic = replace(RESOURCE, name='CopticFixture', language='cop')
        with tempfile.TemporaryDirectory() as directory:
            window = Window(self.app, Library(Path(directory) / 'translations'))
            window.present()
            dialog = None
            try:
                language_info.cache_clear()
                with patch('babel.Locale.get_display_name', return_value=None), patch(
                        'bible.catalogue_window.catalogue',
                        return_value=CatalogueResult((RESOURCE, coptic), {})):
                    dialog = self.open_library(window)
                    dialog.load_catalogue()
                    spin(lambda: not dialog.busy)
                    self.assertNotEqual(dialog._phase, 'error', dialog.status.get_text())
                    self.assertEqual(len(dialog.filtered_resources), 2)
                    self.assertTrue(dialog.catalogue_button.get_sensitive())
                    for query in ('cop', 'copte', 'Coptic'):
                        dialog.language.search.set_text(query)
                        dialog.language.filter()
                        self.assertIn('cop', dialog.language.visible_codes)
                    dialog.language.activate(None, dialog.language.visible_codes.index('cop'))
                    self.assertEqual(dialog.filtered_resources, [coptic])
                    self.assertEqual(dialog.selected_resource(), coptic)
                    self.assertTrue(dialog.download_button.get_sensitive())
                    self.assertNotIn('None', dialog.language.display_language('cop'))
            finally:
                language_info.cache_clear()
                if dialog is not None:
                    dialog.close()
                window.close()

    def test_cached_results_load_without_network_and_survive_failed_refresh(self):
        from bible.ui import Window
        from bible.catalogue_cache import CatalogueCache
        from bible.providers import CROSSWIRE
        with tempfile.TemporaryDirectory() as directory:
            cache=CatalogueCache(Path(directory)/'catalogue-cache')
            cache.write(CROSSWIRE,[RESOURCE])
            window=Window(self.app,Library(Path(directory)/'translations'));window.present()
            try:
                dialog=self.open_library(window)
                self.assertEqual(dialog.resources,[RESOURCE])
                dialog.open_details(None,0)
                with patch('bible.library.catalogue',side_effect=OSError('offline fixture')):
                    dialog.load_catalogue();spin(lambda:not dialog.busy)
                self.assertEqual(dialog.selected_resource(),RESOURCE)
                self.assertEqual(dialog.pages.get_visible_child_name(),'detail')
                self.assertIn('offline fixture',dialog.refresh_status.get_text())
                self.assertTrue(dialog.download_button.get_sensitive())
                dialog.close()
            finally:window.close()

    def test_progressive_results_are_interactive_during_refresh(self):
        from bible.ui import Window
        from bible.providers import CROSSWIRE
        release=threading.Event();self.addCleanup(release.set)
        def fetch(**kwargs):
            kwargs['on_provider'](CROSSWIRE,[RESOURCE],None,{})
            release.wait(3)
            return CatalogueResult((RESOURCE,),{})
        with tempfile.TemporaryDirectory() as directory:
            window=Window(self.app,Library(Path(directory)/'translations'));window.present()
            try:
                with patch('bible.catalogue_window.catalogue',side_effect=fetch):
                    dialog=self.open_library(window);dialog.load_catalogue()
                    spin(lambda:bool(dialog.filtered_resources))
                    self.assertTrue(dialog.refreshing)
                    dialog.open_details(None,0)
                    self.assertTrue(dialog.download_button.get_sensitive())
                    self.assertEqual(dialog.selected_resource(),RESOURCE)
                    release.set();spin(lambda:not dialog.busy)
                    self.assertEqual(dialog.pages.get_visible_child_name(),'detail')
                    dialog.close()
            finally:window.close()

    def test_selection_and_installed_state_survive_list_refresh(self):
        from bible.ui import Window
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window=Window(self.app,Library(Path(directory)/'translations'));window.present()
            try:
                dialog=self.open_library(window)
                installed=window.library.resource('Test')
                other=replace(installed,name='Another')
                dialog.resources=[other,installed];dialog.update_languages()
                dialog.open_details(None,1)
                self.assertTrue(dialog.installed_state.get_visible())
                self.assertFalse(dialog.download_button.get_visible())
                dialog.resources=[installed,other];dialog.filter_resources()
                self.assertEqual(dialog.selected_resource().id,'Test')
                self.assertTrue(dialog.installed_state.get_visible())
                dialog.choices.set_selected(1)
                self.assertEqual(dialog.selected_resource().id,'Another')
                self.assertFalse(dialog.installed_state.get_visible())
                self.assertTrue(dialog.download_button.get_visible())
                dialog.close()
            finally:window.close()

    def test_partial_catalogue_source_filter_and_retry(self):
        from bible.ui import Window
        with tempfile.TemporaryDirectory() as directory:
            window = Window(self.app, Library(Path(directory) / 'translations'))
            window.present()
            try:
                extra = replace(RESOURCE, provider_id=EXTRA.id, source=EXTRA.name, source_url=EXTRA.url)
                result = CatalogueResult((RESOURCE, extra), {'STEP': 'HTTP 503 fixture'})
                # Install the worker fixture before presenting the auto-loading UI.
                with patch('bible.catalogue_window.catalogue', return_value=result):
                    dialog = self.open_library(window)
                    dialog.load_catalogue()
                    spin(lambda: not dialog.busy)
                self.assertEqual(len(dialog.filtered_resources), 2)
                self.assertIn('HTTP 503', dialog.status.get_text())
                labels = [dialog.choices.get_model().get_item(i).resource.source for i in range(2)]
                self.assertIn(EXTRA.name, labels)
                dialog.source_filter.set_selected(dialog.source_ids.index(EXTRA.id))
                self.assertEqual([r.id for r in dialog.filtered_resources], [extra.id])
                self.assertIn(EXTRA.name, dialog.metadata.get_text())
                self.assertTrue(dialog.download_button.get_sensitive())
                with patch('bible.catalogue_window.catalogue', return_value=CatalogueResult((extra,), {})):
                    dialog.load_catalogue()
                    spin(lambda: not dialog.busy)
                self.assertNotIn('503', dialog.status.get_text())
                self.assertEqual(dialog.selected_resource().id, extra.id)
                dialog.close()
            finally:
                window.close()

    def test_additional_commentary_install_callback_following_and_session_restore(self):
        from bible.ui import Window
        from bible.session import SessionStore
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as source:
            installed_fixture(directory)
            module_fixture(source, 'Notes', [('Gen.1.1', 'EXTRA SENTINEL ONE'),
                                           ('Gen.1.2', 'EXTRA SENTINEL TWO')], commentary=True)
            from bible.library import resource_from_section, config
            resource = resource_from_section('Notes', config((Path(source) / 'mods.d/test.conf').read_bytes())['Notes'], EXTRA)
            payload = archive_bytes({str(p.relative_to(source)): p.read_bytes()
                                     for p in Path(source).rglob('*') if p.is_file()})
            library = Library(Path(directory) / 'translations')
            window = Window(self.app, library)
            window.present()
            try:
                dialog = self.open_library(window)
                dialog.resources = [resource]
                dialog.kind.set_selected(1)
                dialog.update_languages()
                with patch('bible.library.download', side_effect=lambda url,out,progress: out.write(payload)):
                    dialog.install()
                    spin(lambda: not dialog.busy)
                self.assertEqual(window.active_tab.state.commentary, resource.id)
                window.active_tab.navigate('Test', 'Gen.1.2')
                window.study.refresh(force=True)
                buffer = window.study.text.get_buffer()
                self.assertEqual(window.study.entry_text, 'EXTRA SENTINEL TWO')
                self.assertIn('EXTRA SENTINEL ONE', buffer.props.text)
                self.assertEqual(buffer.props.text.count('EXTRA SENTINEL TWO'), 1)
                self.assertIn(EXTRA.name, window.study.source.get_text())
                dialog.close()
            finally:
                window.close()
            self.assertEqual(SessionStore(Path(directory) / 'session.json').load().tabs[0].commentary, resource.id)
            with patch('urllib.request.urlopen', side_effect=AssertionError('offline')):
                restored = Window(self.app, library)
                try:
                    self.assertEqual(restored.active_tab.state.commentary, resource.id)
                    self.assertIn(EXTRA.name, restored.study.source.get_text())
                finally:
                    restored.close()
