"""Actual local metadata, conditional requests and fail-closed edition identity."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
from bible.module_updates import ModuleCatalogue,installed_modules,assessment,parse_catalogue,public_source


def catalogue(modules=()):
    return json.dumps(dict(schema_version=1,repository='Bible Resources',
        repository_url='https://icfmp.github.io/Bible-Resources/',modules=list(modules))).encode()


class Response(io.BytesIO):
    headers={'ETag':'"fixture"','Last-Modified':'Sun, 08 Nov 2026 00:00:00 GMT'}


class ModuleUpdateTests(unittest.TestCase):
    def test_app_and_external_sword_roots_are_read_only_and_credentials_are_not_exposed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);library=root/'translations';app=library/'Test';external=root/'copied'
            for folder,version in ((app,'1.2.9'),(external,'1.2.10')):
                (folder/'mods.d').mkdir(parents=True)
                (folder/'mods.d/test.conf').write_text('[Test]\nDescription=Same ID different copy\nVersion='+version+
                    '\nInstallSource=https://name:secret@example.org/sword/?token=secret\nCipherKey=secret\n')
            (app/'.complete').touch()
            before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            rows,errors=installed_modules(library,[external])
            own=[row for row in rows if row.root in (app,external)]
            self.assertEqual(sorted(row.version for row in own),['1.2.10','1.2.9'])
            self.assertTrue(all(row.source=='https://example.org/sword/' for row in own))
            self.assertNotIn('secret',repr(own));self.assertEqual(before,{p:p.read_bytes() for p in before})
            self.assertEqual(public_source('name:secret@host'), '')

    def test_etag_304_and_offline_cache_preserve_actual_catalogue(self):
        with tempfile.TemporaryDirectory() as directory:
            store=ModuleCatalogue(directory);requests=[]
            def first(request,timeout):requests.append(request);return Response(catalogue())
            result=store.check(first);self.assertFalse(result['cached'])
            def unchanged(request,timeout):
                self.assertEqual(request.get_header('If-none-match'),'"fixture"')
                raise HTTPError(request.full_url,304,'Not modified',{},None)
            self.assertFalse(store.check(unchanged)['cached'])
            original=store.path.read_bytes()
            def offline(*args,**kwargs):raise OSError('fixture offline')
            saved=store.check(offline);self.assertTrue(saved['cached']);self.assertIn('offline',saved['error'])
            self.assertEqual(saved['catalogue']['modules'],[]);self.assertEqual(store.path.read_bytes(),original)

    def test_invalid_network_result_never_overwrites_valid_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            store=ModuleCatalogue(directory);store.check(lambda *args,**kwargs:Response(catalogue()))
            original=store.path.read_bytes()
            result=store.check(lambda *args,**kwargs:Response(b'{"schema_version":true}'))
            self.assertTrue(result['cached']);self.assertEqual(store.path.read_bytes(),original)

    def test_id_or_newer_version_never_proves_edition_identity(self):
        from bible.module_updates import InstalledModule
        installed=InstalledModule('Test','1.2.9','Other publisher',Path('/fixture'),'KJV','Same title')
        item=dict(id='other-edition',sword_id='Test',version='1.2.10',edition='faithful',
            download=dict(url='https://icfmp.github.io/Bible-Resources/sword/packages/Test.zip',sha256='a'*64,size_bytes=10))
        self.assertEqual(assessment(installed,parse_catalogue(catalogue([item]))),'identity-unverified')
        self.assertEqual(assessment(installed,parse_catalogue(catalogue())),'no-curated-edition')

    def test_no_cache_network_failure_is_not_reported_as_current(self):
        with tempfile.TemporaryDirectory() as directory:
            def offline(*args,**kwargs):raise OSError('fixture offline')
            with self.assertRaises(OSError):ModuleCatalogue(directory).check(offline)
