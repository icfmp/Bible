from dataclasses import replace
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from bible.catalogue_cache import CatalogueCache
from bible.library import catalogues
from bible.providers import CROSSWIRE, EXTRA
from tests.test_library import RESOURCE


class CatalogueCacheTests(unittest.TestCase):
    def test_offline_empty_corrupt_and_unsupported_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=CatalogueCache(directory);cache.write(CROSSWIRE,[RESOURCE])
            self.assertEqual(cache.read(CROSSWIRE)[0],(RESOURCE,))
            with patch('bible.library.catalogue',side_effect=OSError('offline')):
                result=catalogues((CROSSWIRE,),cache=cache)
            self.assertEqual(result.resources,(RESOURCE,));self.assertIn('CrossWire',result.errors)
            cache.write(CROSSWIRE,[]);self.assertEqual(cache.read(CROSSWIRE)[0],())
            for value in ('{broken','{"version":99}', '{"version":1,"resources":null}'):
                (Path(directory)/'crosswire.json').write_text(value)
                self.assertIsNone(cache.read(CROSSWIRE))

    def test_interrupted_write_preserves_valid_previous_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=CatalogueCache(directory);cache.write(CROSSWIRE,[RESOURCE])
            with patch('bible.catalogue_cache.os.replace',side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):cache.write(CROSSWIRE,[])
            self.assertEqual(cache.read(CROSSWIRE)[0],(RESOURCE,))
            self.assertEqual(len(list(Path(directory).iterdir())),1)

    def test_fresh_cache_skips_network_until_explicit_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=CatalogueCache(directory);cache.write(CROSSWIRE,[RESOURCE])
            with patch('bible.library.catalogue',side_effect=AssertionError('unnecessary network')):
                self.assertEqual(catalogues((CROSSWIRE,),cache=cache,force=False).resources,(RESOURCE,))

    def test_fast_provider_is_delivered_before_slow_provider(self):
        release=threading.Event();delivered=[]
        extra=replace(RESOURCE,provider_id=EXTRA.id,source=EXTRA.name,source_url=EXTRA.url)
        def load(provider,timings=None):
            if provider==CROSSWIRE:
                if not release.wait(3):raise TimeoutError('slow fixture not released')
                return [RESOURCE]
            return [extra]
        def ready(provider,items,error,timings):
            delivered.append(provider.id)
            if provider==EXTRA:release.set()
        with patch('bible.library.catalogue',side_effect=load):
            result=catalogues((CROSSWIRE,EXTRA),on_provider=ready)
        self.assertEqual(delivered,[EXTRA.id,CROSSWIRE.id])
        self.assertEqual({r.id for r in result.resources},{RESOURCE.id,extra.id})

    def test_conditional_refresh_keeps_sources_and_records_zero_body_bytes(self):
        import urllib.error
        with tempfile.TemporaryDirectory() as directory:
            cache=CatalogueCache(directory)
            cache.write(CROSSWIRE,[RESOURCE],validators={'ETag':'"original"','Last-Modified':'Wed, 21 Oct 2026 12:00:00 GMT'})
            observed=[]
            def unchanged(provider,timings=None,validators=None):
                observed.append(validators)
                raise urllib.error.HTTPError(provider.catalogue_url,304,'Not Modified',{},None)
            def ready(provider,items,error,timings):
                self.assertIsNone(error);self.assertEqual(tuple(items),(RESOURCE,))
                self.assertEqual(timings['metadata_bytes'],0);self.assertEqual(timings['requests'],1)
                self.assertEqual(timings['http_status'],304)
            with patch('bible.library.catalogue',side_effect=unchanged):
                result=catalogues((CROSSWIRE,),cache=cache,force=True,on_provider=ready)
            self.assertEqual(result.resources,(RESOURCE,));self.assertFalse(result.errors)
            self.assertEqual(observed[0]['ETag'],'"original"')
            self.assertEqual(cache.read(CROSSWIRE)[0],(RESOURCE,))
