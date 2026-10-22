"""Offline regression checks; synthetic HTML only."""
import contextlib
from email.message import Message
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import zipfile

from tools.research import collect_bds_pages as c


def sample(ref):
    return f'<html><div class="prefix_chapter" data-usfm="{ref}">synthetic sample</div></html>'.encode()


class CollectorTests(unittest.TestCase):
    def test_index_restricts_source_and_keeps_introductions(self):
        p = c.IndexParser()
        p.feed('<a href="/fr/bible/21/JHN.1.BDS">one</a>'
               '<a href="/fr/bible/21/JHN.1.BDS?x=1">duplicate</a>'
               '<a href="/fr/bible/21/JHN.INTRO1.BDS">intro</a>'
               '<a href="https://elsewhere.invalid/fr/bible/21/JHN.2.BDS">foreign</a>'
               '<a href="/fr/bible/22/JHN.2.BDS">other version</a>')
        self.assertEqual(list(p.pages), ['JHN.1', 'JHN.INTRO1'])

    def test_error_page_not_accepted_as_index(self):
        with self.assertRaises(ValueError):
            c.discover(b'<html>Try again later</html>')

    def test_correct_chapter_required(self):
        c.check_page(sample('JHN.1'), 'JHN.1')
        c.check_page(sample('JHN.INTRO1'), 'JHN.INTRO1')
        for payload in [sample('JHN.2'), b'<html>captcha/error</html>']:
            with self.assertRaises(ValueError):
                c.check_page(payload, 'JHN.1')

    def test_rate_limit_and_forbidden_stop_without_retry(self):
        for status in [401, 403, 429]:
            headers = Message()
            headers['Retry-After'] = '120'
            error = HTTPError(c.INDEX, status, 'blocked', headers, None)
            with patch.object(c, 'urlopen', side_effect=error) as fetch, patch.object(c.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, str(status)):
                    c.Fetcher(2).fetch(c.INDEX)
                self.assertEqual(fetch.call_count, 1)

    def test_interrupted_collection_resumes_and_repairs_corruption(self):
        refs = {'JHN.1': 'https://www.bible.com/fr/bible/21/JHN.1.BDS',
                'PSA.3': 'https://www.bible.com/fr/bible/21/PSA.3.BDS'}
        def result(data, url):
            return data, dict(url=url, bytes=len(data), sha256=c.sha(data))
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/'pages-out'
            args = ['collector', '--output', str(directory), '--workers', '1']
            first = [result(b'<html>synthetic index</html>', c.INDEX),
                     result(sample('JHN.1'), refs['JHN.1']), KeyboardInterrupt()]
            with patch.object(c.sys, 'argv', args), patch.object(c, 'discover', return_value=refs), contextlib.redirect_stdout(io.StringIO()):
                with patch.object(c.Fetcher, 'fetch', side_effect=first):
                    self.assertEqual(c.main(), 1)
                manifest = json.loads((directory/'manifest.json').read_text())
                self.assertFalse(manifest['complete'])
                self.assertEqual(manifest['missing'], ['PSA.3'])
                with zipfile.ZipFile(directory.with_name('pages-out.zip')) as archive:
                    self.assertIn('pages/JHN.1.html', archive.namelist())
                    self.assertNotIn('pages/PSA.3.html', archive.namelist())
                with patch.object(c.Fetcher, 'fetch', return_value=result(sample('PSA.3'), refs['PSA.3'])) as fetch:
                    self.assertEqual(c.main(), 0)
                    fetch.assert_called_once_with(refs['PSA.3'])
                self.assertTrue(json.loads((directory/'manifest.json').read_text())['complete'])
                (directory/'pages/JHN.1.html').write_bytes(b'corrupt')
                with patch.object(c.Fetcher, 'fetch', return_value=result(sample('JHN.1'), refs['JHN.1'])) as fetch:
                    self.assertEqual(c.main(), 0)
                    fetch.assert_called_once_with(refs['JHN.1'])
                with zipfile.ZipFile(directory.with_name('pages-out.zip')) as archive:
                    self.assertEqual(archive.testzip(), None)
                    self.assertEqual(archive.read('pages/JHN.1.html'), sample('JHN.1'))

    def test_ten_transfers_overlap_and_manifest_stays_consistent(self):
        refs = {f'JHN.{n}': f'https://www.bible.com/fr/bible/21/JHN.{n}.BDS' for n in range(1, 11)}
        barrier = threading.Barrier(10)
        lock = threading.Lock()
        active = peak = 0
        def fetch(url):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(active, peak)
            barrier.wait(timeout=5)
            ref = c.REF.fullmatch(c.urlsplit(url).path)
            data = sample(ref[1]+'.'+ref[2])
            with lock:
                active -= 1
            return data, dict(url=url, sha256=c.sha(data), bytes=len(data))
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory/'pages').mkdir()
            manifest = dict(index_pages=refs, pages={}, errors=[])
            with patch.object(c.Fetcher, 'fetch', side_effect=fetch), contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(c.collect(directory, manifest, c.Fetcher(0.5), 10, None))
            self.assertEqual(peak, 10)
            self.assertEqual(set(manifest['pages']), set(refs))
            saved = json.loads((directory/'manifest.json').read_text())
            self.assertEqual(len(saved['pages']), 10)
            for ref, record in saved['pages'].items():
                self.assertEqual(c.sha((directory/'pages'/(ref+'.html')).read_bytes()), record['sha256'])

    def test_stop_event_prevents_new_network_request(self):
        fetcher = c.Fetcher(0.5)
        fetcher.stop.set()
        with patch.object(c, 'urlopen') as network:
            with self.assertRaises(c.CancelledError):
                fetcher.fetch(c.INDEX)
            network.assert_not_called()

    def test_rate_limit_is_shared_across_threads(self):
        fetcher = c.Fetcher(0.5)
        clock, pauses = [100.0], []
        def pause(seconds):
            pauses.append(seconds)
            clock[0] += seconds
            return False
        def slot():
            fetcher.request_slot()
        with patch.object(c.time, 'monotonic', side_effect=lambda: clock[0]), patch.object(fetcher.stop, 'wait', side_effect=pause):
            threads = [threading.Thread(target=slot) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(pauses, [0, 0.5, 0.5, 0.5])
        self.assertEqual(fetcher.last, 101.5)


if __name__ == '__main__':
    unittest.main()
