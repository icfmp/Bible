import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from bible.library import Library, Resource, catalogue, config, download, safe_path

RESOURCE = Resource('Test', 'Test fixture, not a Bible translation', 'en', 'Public Domain')
CONF = b'''[Test]
DataPath=./modules/texts/rawtext/test/
ModDrv=RawText
Lang=en
DistributionLicense=Public Domain
Encoding=UTF-8
SourceType=Plaintext
'''


def fixture(root):
    """Create real SWORD files with sentinel test data, never application content."""
    import Sword
    path = Path(root) / 'modules/texts/rawtext/test'
    path.mkdir(parents=True)
    Sword.RawText.createModule(str(path))
    module = Sword.RawText(str(path), 'Test', 'Test fixture')
    for ref, text in [('Gen.1.1', 'SENTINEL α <literal>'),
                      ('Gen.1.2', 'SECOND SENTINEL'), ('Gen.2.1', 'NEXT CHAPTER')]:
        module.setKey(Sword.VerseKey(ref))
        module.setEntry(text)
    del module
    conf = Path(root) / 'mods.d/test.conf'
    conf.parent.mkdir()
    conf.write_bytes(CONF)


def archive_bytes(files):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        for name, value in files.items():
            archive.writestr(name, value)
    return data.getvalue()


class LibraryTests(unittest.TestCase):
    def test_sword_configuration_continuation(self):
        data = CONF + b'About=First line \\\nCopyright and address \\\nLast line\nBareKey\n'
        parsed = config(data)
        self.assertEqual(parsed['Test']['About'], 'First line Copyright and address Last line')
        self.assertEqual(parsed['Test']['DistributionLicense'], 'Public Domain')

    def test_fresh_profile(self):
        with tempfile.TemporaryDirectory() as d:
            library = Library(d)
            (Path(d) / '.install-interrupted').mkdir()
            self.assertEqual(library.installed(), [])

    def test_archive_paths(self):
        for value in ['../escape', '/absolute', 'modules/../../escape', 'modules\\escape']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                safe_path(value)

    def test_catalogue_is_remote_and_filters_license(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as archive:
            for name, license in [('Test', 'Public Domain'), ('GPLTest', 'GPL'), ('Private', 'Copyright'), ('Helper', 'Public Domain')]:
                content = CONF.replace(b'[Test]', f'[{name}]'.encode()).replace(
                    b'Public Domain', license.encode())
                if name == 'Helper':
                    content = content.replace(b'Lang=en\n', b'')
                info = tarfile.TarInfo(f'mods.d/{name}.conf')
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
        with patch('bible.library.download', side_effect=lambda url, out, **kw: out.write(data.getvalue())):
            self.assertEqual([r.name for r in catalogue()], ['GPLTest', 'Test'])

    def test_failed_download_leaves_no_installation(self):
        with tempfile.TemporaryDirectory() as d:
            library = Library(d)
            with patch('bible.library.download', side_effect=OSError('network failed')):
                with self.assertRaisesRegex(OSError, 'network failed'):
                    library.install(RESOURCE)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_malicious_archive_not_installed(self):
        for files in [{'../escape': b'x'}, {'modules/../escape': b'x'},
                      {'mods.d/test.conf': CONF.replace(b'./modules/texts/rawtext/test/', b'/etc')},
                      {'mods.d/test.conf': CONF.replace(b'[Test]', b'[Other]')}]:
            with self.subTest(files=list(files)), tempfile.TemporaryDirectory() as d:
                def fetch(url, output, progress):
                    output.write(archive_bytes(files))
                with patch('bible.library.download', side_effect=fetch):
                    with self.assertRaises(ValueError):
                        Library(d).install(RESOURCE)
                self.assertEqual(list(Path(d).iterdir()), [])

    def test_download_limit_and_truncation(self):
        class Response(io.BytesIO):
            url = 'https://example.test/resource'
            headers = {'Content-Length': '20'}
        for limit in [2, 100]:
            with self.subTest(limit=limit), patch('urllib.request.urlopen', return_value=Response(b'abc')):
                with self.assertRaises(ValueError):
                    download('https://example.test', io.BytesIO(), limit=limit)

    def test_install_and_restart_offline_fidelity(self):
        from bible.sword_provider import Reader
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as d:
            fixture(source)
            files = {str(p.relative_to(source)): p.read_bytes()
                     for p in Path(source).rglob('*') if p.is_file()}
            payload = archive_bytes(files)
            def fetch(url, out, progress):
                out.write(payload)
                progress(len(payload), len(payload))
            library = Library(d)
            progress = []
            with patch('bible.library.download', side_effect=fetch):
                library.install(RESOURCE, lambda n, total: progress.append((n, total)))
            self.assertEqual(progress, [(len(payload), len(payload))])
            with patch('urllib.request.urlopen', side_effect=AssertionError('Offline')):
                restarted = Library(d)
                self.assertEqual(restarted.installed(), ['Test'])
                reader = Reader(Path(d) / 'Test', 'Test')
                for invalid in ['garbage', 'Gen.99.1', 'Gen.1.999', 'Gen 0:0']:
                    with self.assertRaises(ValueError):
                        reader.chapter(invalid)
                chapter = reader.chapter('Gen.1.1')
                self.assertEqual(chapter.verses[0], ('Gen.1.1', 'SENTINEL α <literal>'))
                self.assertEqual(chapter.previous, None)
                self.assertEqual(chapter.following, 'Gen.2.1')
                self.assertEqual(reader.chapter(chapter.following).verses[0][1], 'NEXT CHAPTER')
                self.assertEqual(reader.chapter('Gen.2.1').previous, 'Gen.1.1')
                self.assertEqual(reader.chapter('John.21.1').following, 'Acts.1.1')
                self.assertEqual(reader.chapter('Rev.22.1').following, None)
                library.install(RESOURCE)  # Already installed: no network request.
