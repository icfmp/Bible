import io
import tarfile
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bible.library import Library, Resource, catalogue, catalogues, resource_from_section, config
from bible.providers import CROSSWIRE, EXTRA, ANDBIBLE, STEP, identity
from bible.session import Session, SessionStore, TabState
from tests.test_library import RESOURCE, fixture, archive_bytes


class ProviderTests(unittest.TestCase):
    def test_one_failed_source_keeps_others_and_retry_is_fresh(self):
        def load(provider,timings=None):
            if provider == EXTRA:
                raise OSError('source offline')
            return [replace(RESOURCE, provider_id=provider.id, source=provider.name, source_url=provider.url)]
        with patch('bible.library.catalogue', side_effect=load):
            result = catalogues((CROSSWIRE, EXTRA, STEP))
        self.assertEqual({r.id for r in result.resources}, {'Test', 'step~Test'})
        self.assertEqual(result.errors, {EXTRA.name: 'source offline'})
        with patch('bible.library.catalogue', return_value=[RESOURCE]):
            self.assertFalse(catalogues((EXTRA,)).errors)

    def test_colliding_names_keep_separate_content_provenance_and_session(self):
        from bible.sword_provider import Reader
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as directory:
            fixture(source)
            payload = archive_bytes({str(p.relative_to(source)): p.read_bytes()
                                     for p in Path(source).rglob('*') if p.is_file()})
            library = Library(Path(directory) / 'translations')
            extra = replace(RESOURCE, provider_id=EXTRA.id, source=EXTRA.name, source_url=EXTRA.url)
            store = SessionStore(Path(directory) / 'session.json')
            store.save(Session([TabState('Test', commentary=extra.id)]))
            before = store.path.read_bytes()
            notes = Path(directory) / 'notes.sqlite3'
            notes.write_bytes(b'Existing notes: untouched by installation')
            urls = []
            def fetch(url, output, progress):
                urls.append(url)
                output.write(payload)
            with patch('bible.library.download', side_effect=fetch):
                library.install(RESOURCE)
                library.install(extra)
            original = {str(p.relative_to(library.root / 'Test')): p.read_bytes()
                        for p in (library.root / 'Test').rglob('*') if p.is_file()}
            with patch('urllib.request.urlopen', side_effect=AssertionError('offline')):
                self.assertEqual(library.installed(), ['Test', extra.id])
                self.assertEqual(library.resource(extra.id), replace(extra, description='Test'))
                self.assertEqual(library.resource('Test'), replace(RESOURCE, description='Test'))
                self.assertEqual(Reader(library.root / extra.id, extra.id).chapter('Gen.1.1').verses[0][1], 'SENTINEL α <literal>')
                library.install(extra)  # No overwrite, no network.
            self.assertEqual(urls, [CROSSWIRE.packages_url + 'Test.zip', EXTRA.packages_url + 'Test.zip'])
            self.assertEqual(original, {str(p.relative_to(library.root / 'Test')): p.read_bytes()
                                       for p in (library.root / 'Test').rglob('*') if p.is_file()})
            self.assertEqual(store.path.read_bytes(), before)
            self.assertEqual(store.load().tabs[0].commentary, extra.id)
            self.assertEqual(notes.read_bytes(), b'Existing notes: untouched by installation')

    def test_legacy_attribution_without_source_file_and_namespace_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'Test'
            fixture(root)
            (root / '.complete').write_text('Test')
            self.assertEqual(Library(directory).resource('Test').provider_id, 'crosswire')
        for value in ['../escape', 'bad~name', 'x/y']:
            with self.assertRaises(ValueError):
                identity(EXTRA.id, value)

    def test_no_hidden_license_or_missing_language_filter(self):
        content = b'[Demo]\nModDrv=RawCom\nDistributionLicense=Copyright\n'
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as archive:
            member = tarfile.TarInfo('mods.d/demo.conf')
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        with patch('bible.library.download', side_effect=lambda url,out,**kw: out.write(data.getvalue())):
            resource, = catalogue(EXTRA)
        self.assertEqual(resource.language, 'und')
        self.assertEqual(resource.license, 'Copyright')
        self.assertTrue(resource.installable)
        self.assertFalse(replace(resource, locked=True).installable)
        self.assertFalse(replace(resource, category='Images').installable)
