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
