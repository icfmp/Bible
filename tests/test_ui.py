import os
import tempfile
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK display (use xvfb-run)')
class WindowTests(unittest.TestCase):
    def test_empty_profile_and_async_failure_retry(self):
        from bible.ui import Application, Window, Library, GLib
        app = Application()
        app.register()
        with tempfile.TemporaryDirectory() as directory:
            window = Window(app, Library(directory))
            window.present()
            def wait():
                deadline = time.monotonic() + 5
                while window.busy and time.monotonic() < deadline:
                    GLib.MainContext.default().iteration(False)
                    time.sleep(0.01)
                self.assertFalse(window.busy)
            self.assertIsNone(window.reader)
            self.assertFalse(window.open_button.get_sensitive())
            with patch('bible.ui.catalogue', side_effect=OSError('offline test')):
                window.load_catalogue()
                self.assertTrue(window.busy)
                self.assertFalse(window.catalogue_button.get_sensitive())
                wait()
            self.assertIn('offline test', window.status.get_text())
            self.assertTrue(window.catalogue_button.get_sensitive())
            with patch('bible.ui.catalogue', return_value=[]):
                window.load_catalogue()
                wait()
            self.assertFalse(window.download_button.get_sensitive())
            window.close()

    def test_installed_translation_and_navigation(self):
        from pathlib import Path
        from bible.ui import Application, Window, Library
        from tests.test_library import fixture
        app = Application()
        app.register()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'Test'
            root.mkdir()
            fixture(root)
            (root / '.complete').write_text('Test')
            window = Window(app, Library(directory))
            window.present()
            self.assertEqual(window.current.reference, 'Gen.1')
            buffer = window.text.get_buffer()
            text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
            self.assertIn('SENTINEL α <literal>', text)
            self.assertFalse(window.previous.get_sensitive())
            self.assertTrue(window.following.get_sensitive())
            window.following.emit('clicked')
            self.assertEqual(window.current.reference, 'Gen.2')
            window.previous.emit('clicked')
            self.assertEqual(window.current.reference, 'Gen.1')
            window.show('Gen.99.1')
            self.assertEqual(window.current.reference, 'Gen.1')
            window.close()
