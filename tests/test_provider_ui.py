import os
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bible.library import CatalogueResult, Library
from bible.providers import EXTRA
from tests.test_library import RESOURCE, archive_bytes
from tests.test_ui import installed_fixture, spin
from tests.fixtures import module_fixture


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK display')
class ProviderUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application, Gtk
        cls.app = Application.get_default() or Application()
        cls.app.register()
        Gtk.Settings.get_default().set_property('gtk-enable-animations', False)

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
                    dialog = window.open_library()
                    dialog.load_catalogue()
                    spin(lambda: not dialog.busy)
                self.assertEqual(len(dialog.filtered_resources), 2)
                self.assertIn('HTTP 503', dialog.status.get_text())
                labels = [dialog.choices.get_model().get_item(i).resource.source for i in range(2)]
                self.assertIn(EXTRA.name, labels[1])
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
                dialog = window.open_library()
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
