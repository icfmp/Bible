"""Offline regression checks; synthetic HTML only."""
import contextlib
from email.message import Message
import io
import json
from pathlib import Path
import tempfile
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
            args = ['collector', '--output', str(directory)]
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


if __name__ == '__main__':
    unittest.main()
