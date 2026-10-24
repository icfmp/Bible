"""Alpha regressions: real GTK layouts and controlled, verified local HTTPS."""
import io
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import zipfile

from tests import test_ui
from tests.fixtures import module_fixture
from bible.library import BASE, Resource


class Transfer:
    def __init__(self, payload, known=True, truncated=False):
        self.payload, self.known, self.truncated = payload, known, truncated
        self.gates = [threading.Event() for _ in range(3)]

    def release(self):
        for gate in self.gates:
            gate.set()


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK display (use xvfb-run)')
class AlphaTests(unittest.TestCase):
    setUpClass = classmethod(test_ui.WindowTests.setUpClass.__func__)
    window = test_ui.WindowTests.window

    def transfer(self, name, commentary=False, known=True, truncated=False):
        with tempfile.TemporaryDirectory() as source:
            module_fixture(source, name, [('Gen.1.1', 'TRANSFER TEST DATA')], commentary=commentary)
            data = io.BytesIO()
            with zipfile.ZipFile(data, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for path in Path(source).rglob('*'):
                    if path.is_file():
                        archive.write(path, str(path.relative_to(source)))
                archive.writestr('modules/padding', os.urandom(16 * 1024))
            payload = data.getvalue()
        self.assertLess(len(payload), 64 * 1024)  # A read(64 KiB) waits until EOF.
        resource = Resource(name, 'Controlled transfer, not a translation', 'en',
                            'Public Domain', driver='RawCom' if commentary else 'RawText')
        return resource, Transfer(payload, known, truncated)

    def local_https(self, transfer):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        cert, key = [Path(temporary.name) / n for n in ('cert.pem', 'key.pem')]
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(key), '-out', str(cert), '-days', '1',
                        '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1'],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.send_response(200)
                if transfer.known:
                    self.send_header('Content-Length', str(len(transfer.payload)))
                self.send_header('Connection', 'close')
                self.end_headers()
                quarter = len(transfer.payload) // 4
                try:
                    for index in range(4):
                        if index and not transfer.gates[index - 1].wait(8):
                            return
                        if transfer.truncated and index == 1:
                            return
                        self.wfile.write(transfer.payload[index * quarter:(index + 1) * quarter]
                                         if index < 3 else transfer.payload[index * quarter:])
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        thread.start()
        def close():
            transfer.release()
            server.shutdown()
            server.server_close()
            thread.join(2)
        self.addCleanup(close)
        trusted = ssl.create_default_context(cafile=str(cert))
        original = urllib.request.urlopen
        def open_local(request, **kwargs):
            self.assertTrue(request.full_url.startswith(BASE + 'packages/rawzip/'))
            return original(f'https://127.0.0.1:{server.server_port}/resource.zip', context=trusted, **kwargs)
        return patch('bible.library.urllib.request.urlopen', side_effect=open_local)

    @staticmethod
    def fill(bar):
        def find(widget):
            if widget.get_css_name() == 'progress':
                return widget
            child = widget.get_first_child()
            while child:
                result = find(child)
                if result is not None:
                    return result
                child = child.get_next_sibling()
        return find(bar)

    def start_transfer(self, dialog, resource):
        test_ui.spin(lambda:dialog.session.bootstrap_future.done() and not dialog.preparing)
        with dialog.session.lock:
            dialog.session.providers[resource.provider_id]=(resource,)
        dialog.resources = [resource]
        dialog.kind.set_selected(1 if resource.kind == 'commentary' else 0)
        dialog.update_languages()
        dialog.install()
        self.assertTrue(dialog.busy)
        self.assertIn(resource.name, dialog.status.get_text())

    def test_slow_transfer_renders_bytes_before_eof_and_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            window = self.window(directory)
            dialog = window.open_library()
            resource, transfer = self.transfer('SlowBible')
            validation = threading.Event()
            self.addCleanup(validation.set)
            original_install = window.library.install
            def hold_validation(resource, progress, installing):
                def started():
                    installing()
                    if not validation.wait(8):
                        raise TimeoutError('Validation test was not released')
                return original_install(resource, progress, installing=started)
            with self.local_https(transfer), patch.object(window.library, 'install', side_effect=hold_validation):
                self.start_transfer(dialog, resource)
                test_ui.spin(lambda: 0 < dialog.progress.get_fraction() < 0.4)
                test_ui.spin(lambda: self.fill(dialog.progress).get_width() > 0)
                first_width = self.fill(dialog.progress).get_width()
                self.assertTrue(dialog.progress.get_mapped())
                self.assertNotIn(resource.name, window.library.installed())
                transfer.gates[0].set()
                test_ui.spin(lambda: dialog.progress.get_fraction() > 0.45)
                test_ui.spin(lambda: self.fill(dialog.progress).get_width() > first_width)
                transfer.release()
                test_ui.spin(lambda: dialog._phase == 'installing')
                self.assertTrue(dialog.busy)
                self.assertNotIn(resource.name, window.library.installed())
                self.assertNotIn('100%', dialog.progress.get_text())
                validation.set()
                test_ui.spin(lambda: not dialog.busy)
            self.assertIn(resource.name, window.library.installed())
            self.assertEqual(dialog.progress.get_fraction(), 1)
    
    def test_cancelled_transfer_does_not_publish_a_partial_resource(self):
        with tempfile.TemporaryDirectory() as directory:
            window=self.window(directory);dialog=window.open_library()
            resource,transfer=self.transfer('CancelledBible')
            with self.local_https(transfer):
                self.start_transfer(dialog,resource)
                test_ui.spin(lambda:0<dialog.progress.get_fraction()<.4)
                dialog.cancel_button.emit('clicked');transfer.release()
                test_ui.spin(lambda:not dialog.busy)
            self.assertNotIn(resource.id,window.library.installed())
            self.assertIsNone(window.active_tab.state.resource)
            self.assertEqual(dialog._phase,'error')
            self.assertEqual(dialog._failed_resource,resource.id)
            self.assertTrue(dialog.download_button.get_sensitive())

    def test_unknown_size_commentary_error_and_second_download(self):
        with tempfile.TemporaryDirectory() as directory:
            window = self.window(directory)
            dialog = window.open_library()
            resource, transfer = self.transfer('SlowNotes', commentary=True, known=False)
            with self.local_https(transfer):
                self.start_transfer(dialog, resource)
                test_ui.spin(lambda: 'KiB' in dialog.progress.get_text())
                self.assertEqual(dialog.progress.get_fraction(), 0)
                self.assertNotIn('%', dialog.progress.get_text())
                self.assertTrue(dialog.progress.get_mapped())
                position = self.fill(dialog.progress).get_allocation().x
                test_ui.spin(lambda: self.fill(dialog.progress).get_allocation().x != position, duration=0.3)
                transfer.release()
                test_ui.spin(lambda: not dialog.busy)
            self.assertIn(resource.name, window.library.installed('commentary'))
            resource, broken = self.transfer('RetryBible', truncated=True)
            with self.local_https(broken):
                self.start_transfer(dialog, resource)
                self.assertEqual(dialog.progress.get_fraction(), 0)
                broken.release()
                test_ui.spin(lambda: not dialog.busy)
            self.assertNotIn(resource.name, window.library.installed())
            self.assertEqual(dialog.progress.get_fraction(), 0)
            self.assertEqual(dialog._pulse_id, 0)
            self.assertTrue(dialog.download_button.get_sensitive())
            resource, retry = self.transfer('RetryBible')
            with self.local_https(retry):
                self.start_transfer(dialog, resource)
                test_ui.spin(lambda: 0 < dialog.progress.get_fraction() < 0.4)
                retry.release()
                test_ui.spin(lambda: not dialog.busy)
            self.assertIn(resource.name, window.library.installed('bible'))

    def test_book_search_chapter_grid_and_immediate_independent_selection(self):
        from bible.ui import Gtk
        from bible.i18n import tr
        with tempfile.TemporaryDirectory() as directory:
            entries = [('Gen.1.1', 'FIRST TEST DATA')] + [
                (f'1Cor.{chapter}.1', f'CHAPTER {chapter} TEST DATA') for chapter in range(1, 17)
            ] + [('1Cor.15.8', 'VERSE TEST DATA'), ('Rev.1.1', 'LAST TEST DATA')]
            test_ui.installed_fixture(directory, entries=entries)
            test_ui.installed_fixture(directory, 'Other', entries=entries)
            window = self.window(directory)
            first = window.active_tab
            second = window.new_tab()
            test_ui.spin(lambda: window.get_mapped() and window.get_width() > 600)
            window.choose_passage()
            nav = window.navigation
            nav.book_list.emit('row-activated', nav.book_rows['1Cor'])
            self.assertEqual(second.state.reference, '1Cor.1.1')
            self.assertEqual(len(nav.chapter_buttons), 16)
            nav.chapter_buttons[15].emit('clicked')
            self.assertEqual(second.state.reference, '1Cor.15.1')
            self.assertTrue(nav.get_visible())
            self.assertTrue(nav.chapter_buttons[15].get_active())
            self.assertTrue(nav.chapter_buttons[15].has_css_class('suggested-action'))
            self.assertEqual(first.state.reference, 'Gen.1.1')
            self.assertEqual(window.view.get_n_pages(), 2)
            self.assertFalse(hasattr(nav, 'new_button'))
            self.assertFalse(hasattr(nav, 'open_button'))
            nav.verse.set_selected(nav.verses.index(8))
            self.assertEqual(second.state.reference, '1Cor.15.8')
            nav.version.set_selected(nav.names.index('Other'))
            self.assertEqual(second.state.resource, 'Other')
            self.assertEqual(second.state.reference, '1Cor.15.8')
            nav.search.set_text('cor')
            nav.filter_books()
            self.assertEqual(list(nav.book_rows), ['1Cor'])
            self.assertIn('Cor', nav.book_title.get_text())
            nav.search.set_text('does-not-exist')
            nav.filter_books()
            self.assertTrue(nav.no_books.get_visible())
            self.assertEqual(second.state.reference, '1Cor.15.8')
            nav.close_button.emit('clicked')
            window.choose_passage()
            self.assertEqual(nav.search.get_text(), '')
            self.assertIs(nav.book_list.get_selected_row(), nav.book_rows['1Cor'])
            self.assertTrue(nav.chapter_buttons[15].get_active())
            test_ui.spin(lambda: nav.get_width() > 600)
            self.assertEqual(nav.columns.get_orientation(), Gtk.Orientation.HORIZONTAL)
            nav.popdown()
            window.set_default_size(360, 650)
            test_ui.spin(lambda: window.get_width() <= 380)
            window.choose_passage()
            test_ui.spin(lambda: nav.columns.get_orientation() == Gtk.Orientation.VERTICAL)
            test_ui.spin(lambda: nav.get_width() <= 360)
            self.assertLessEqual(nav.get_width(), 360)
            nav.chapter_buttons[16].emit('clicked')
            self.assertEqual(second.state.reference, '1Cor.16.1')

    def test_version_rejects_missing_passage_and_different_versification(self):
        from bible.i18n import tr
        with tempfile.TemporaryDirectory() as directory:
            test_ui.installed_fixture(directory)
            test_ui.installed_fixture(directory, 'Limited', entries=[('John.1.1', 'LIMITED TEST DATA')])
            test_ui.installed_fixture(directory, 'Catholic', versification='Catholic')
            window = self.window(directory)
            window.navigate_selection('Test', 'Gen.2.1')
            test_ui.spin(lambda: window.get_mapped() and window.get_width() > 600)
            window.choose_passage()
            nav = window.navigation
            nav.version.set_selected(nav.names.index('Limited'))
            self.assertEqual(window.active_tab.state.resource, 'Test')
            self.assertEqual(window.active_tab.state.reference, 'Gen.2.1')
            self.assertIn(tr('This passage is not available in this translation.'), nav.status.get_text())
            self.assertEqual(nav.selected_resource(), 'Limited')
            self.assertFalse(any(button.get_active() for button in nav.chapter_buttons.values()))
            nav.chapter_buttons[1].emit('clicked')
            self.assertEqual(window.active_tab.state.resource, 'Limited')
            self.assertEqual(window.active_tab.state.reference, 'John.1.1')
            nav.version.set_selected(nav.names.index('Catholic'))
            self.assertEqual(window.active_tab.state.resource, 'Limited')
            self.assertIn(tr('Different versifications. Automatic alignment is unavailable.'), nav.status.get_text())
            nav.chapter_buttons[1].emit('clicked')
            self.assertEqual(window.active_tab.state.resource, 'Catholic')
            self.assertEqual(window.active_tab.reader.versification, 'Catholic')

    def test_chapter_overlay_stays_in_viewport_and_bible_panel(self):
        from bible.ui import Adw
        with tempfile.TemporaryDirectory() as directory:
            test_ui.installed_fixture(directory, long_text=True)
            window = self.window(directory)
            window.navigate_selection('Test', 'Gen.1.1')
            window.set_default_size(1000, 600)
            tab = window.active_tab
            test_ui.spin(lambda: not tab._restoring_scroll)
            def bounds():
                found, rect = tab.following.compute_bounds(tab.reading_overlay)
                self.assertTrue(found)
                center=rect.origin.y+rect.size.height/2
                self.assertGreater(center,tab.reading_overlay.get_height()*.65)
                self.assertLess(center,tab.reading_overlay.get_height()*.95)
                self.assertGreaterEqual(rect.origin.x,tab.scroll.get_width()-tab.text.get_right_margin()+4)
                self.assertGreaterEqual(rect.origin.x-(tab.scroll.get_width()-tab.text.get_right_margin()),18)
                self.assertLessEqual(rect.origin.x-(tab.scroll.get_width()-tab.text.get_right_margin()),24)
                self.assertLessEqual(rect.origin.x + rect.size.width, tab.reading_overlay.get_width())
                self.assertAlmostEqual(rect.size.width, rect.size.height, delta=1)
                self.assertGreaterEqual(tab.text.get_right_margin(), rect.size.width + 6)
                return rect
            before = bounds()
            adjustment = tab.scroll.get_vadjustment()
            adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size())
            test_ui.spin()
            self.assertAlmostEqual(bounds().origin.y, before.origin.y, delta=1)
            self.assertFalse(tab.previous.get_sensitive())
            self.assertTrue(tab.following.get_sensitive())
            self.assertTrue(tab.following.get_focusable())
            style = Adw.StyleManager.get_default()
            old_scheme = style.get_color_scheme()
            try:
                for scheme in (Adw.ColorScheme.FORCE_LIGHT, Adw.ColorScheme.FORCE_DARK):
                    style.set_color_scheme(scheme)
                    window.study_button.set_active(True)
                    test_ui.spin(lambda: tab.get_width() < 700)
                    bounds()
                    found, button = tab.following.compute_bounds(window)
                    _, study = window.study.compute_bounds(window)
                    self.assertLessEqual(button.origin.x+button.size.width, study.origin.x)
                    window.study_button.set_active(False)
                    test_ui.spin(lambda: tab.get_width() > 900)
                    bounds()
                window.set_default_size(360, 600)
                test_ui.spin(lambda: window.get_width() <= 380)
                bounds()
                test_ui.spin(lambda: tab.following.get_mapped())
                self.assertTrue(tab.following.get_mapped())
            finally:
                style.set_color_scheme(old_scheme)

    def test_overlay_chapter_limits_sparse_books_and_independent_tabs(self):
        with tempfile.TemporaryDirectory() as directory:
            entries = [('Matt.1.1', 'START TEST DATA'), ('John.3.16', 'MIDDLE TEST DATA'),
                       ('Rev.22.21', 'END TEST DATA')]
            test_ui.installed_fixture(directory, entries=entries, nt_only=True)
            window = self.window(directory)
            first = window.active_tab
            second = window.new_tab()
            self.assertFalse(second.previous.get_sensitive())
            second.following.emit('clicked')
            self.assertEqual(second.state.reference, 'John.3.16')
            test_ui.spin(lambda: not second._restoring_scroll)
            self.assertEqual(second.scroll.get_vadjustment().get_value(), 0)
            self.assertEqual(first.state.reference, 'Matt.1.1')
            second.following.emit('clicked')
            self.assertEqual(second.state.reference, 'Rev.22.21')
            self.assertFalse(second.following.get_sensitive())
            self.assertFalse(window.lookup_action('next-chapter').get_enabled())
            second.previous.emit('clicked')
            self.assertEqual(second.state.reference, 'John.3.16')
            window.view.set_selected_page(window.view.get_nth_page(0))
            self.assertFalse(first.previous.get_sensitive())
            self.assertEqual(first.state.reference, 'Matt.1.1')
