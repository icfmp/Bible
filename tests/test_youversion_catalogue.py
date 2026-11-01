"""Language discovery, lazy catalogue metadata and atomic source-cache failures."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import threading
from unittest.mock import patch

from bible.youversion_catalogue import (read_languages,editions,languages,tags_for_language,
                                       resource_from_listing,saved_languages)
from bible.youversion_editions import module_id,edition_id,storage_system,CONFIGURATION_URL,VERSIONS_URL


def language(tag):
    return dict(iso_639_3=tag.split('_')[0],language_tag=tag,has_text=True,
                name='Synthetic language',local_name='Synthetic autonym')


def listing(identifier=900021,tag='spa',offline=True):
    return dict(id=identifier,local_title='Synthetic edition',title='Synthetic edition',text=True,
        language=language(tag),vrs=None,
        offline=dict(url=f'//offline-bibles-cdn.youversionapi.com/bible/text/offline/{identifier}-1.zip',
                     require_email_agreement=False,agreement_version=None) if offline else None)


def envelope(value):return dict(response=dict(code=200,data=value))


class LanguageCatalogueTests(unittest.TestCase):
    def test_session_loads_only_chosen_languages_off_thread_and_retains_previous_rows(self):
        from bible.catalogue_session import CatalogueSession
        from bible.library import Library
        from bible.providers import YOUVERSION
        from bible.languages import canonical_language
        calls=[];main=threading.get_ident()
        records={tag:language(tag) for tag in ('spa','fra')}
        def load(tag,*args,**kw):
            self.assertNotEqual(threading.get_ident(),main);calls.append(tag)
            return [resource_from_listing(listing(900021 if tag=='spa' else 900022,tag),'spa' if tag=='spa' else 'fra')]
        with tempfile.TemporaryDirectory() as directory,patch('bible.youversion_catalogue.languages',return_value=records),patch('bible.youversion_catalogue.editions',side_effect=load):
            session=CatalogueSession(Library(Path(directory)/'translations'))
            try:
                session.bootstrap_future.result(5)
                session.load_youversion_language('es').result(5)
                session.load_youversion_language('spa').result(5)
                self.assertEqual(calls,['spa'])
                session.load_youversion_language('fr').result(5)
                self.assertEqual(calls,['spa','fra'])
                self.assertEqual({r.language for r in session.providers[YOUVERSION.id]},{'spa','fra'})
                before=tuple(session.providers[YOUVERSION.id])
                with patch('bible.youversion_catalogue.editions',side_effect=ValueError('Synthetic refusal')):
                    session.load_youversion_language('fr',force=True).result(5)
                self.assertEqual(session.providers[YOUVERSION.id],before)
                self.assertIn('Synthetic refusal',session.errors[YOUVERSION.name])
                session.prepare.submit(lambda:None).result(5)
                self.assertFalse(session.snapshot.refreshing)
                self.assertIn(canonical_language('fra'),{canonical_language(c) for c in session.snapshot.languages})
            finally:session.close()
            self.assertIsNone(session.load_youversion_language('en'))

    def test_new_ids_and_source_indexes_are_not_limited_to_the_pilots(self):
        for identifier in [8,504,900021,999999999]:
            self.assertEqual(edition_id(module_id(identifier)),identifier)
            self.assertEqual(storage_system(identifier),'YouVersion'+str(identifier))
        self.assertEqual(storage_system(21),'Original')
        self.assertEqual(storage_system(93),'YouVersion93')
        for invalid in [True,0,-1,1000000000,'42']:
            with self.assertRaises(ValueError):module_id(invalid)

    def test_language_index_and_regional_lists_use_actual_tags(self):
        records=read_languages(envelope(dict(default_versions=[language('fra'),language('spa'),language('spa_es'),language('zho_tw')])))
        self.assertEqual(tags_for_language('fr',records),['fra'])
        self.assertEqual(tags_for_language('es',records),['spa','spa_es'])
        self.assertEqual(tags_for_language('es-ES',records),['spa_es'])
        self.assertEqual(tags_for_language('zh-TW',records),['zho_tw'])
        with self.assertRaises(ValueError):read_languages(dict(default_versions=[language('spa'),language('spa')]))

    def test_browsing_downloads_metadata_only_and_unchanged_cache_keeps_its_age(self):
        requests=[]
        def download(url,out,**options):
            requests.append(url)
            value=dict(default_versions=[language('spa')]) if url==CONFIGURATION_URL else dict(versions=[listing(),listing(900022,offline=False)])
            out.write(json.dumps(envelope(value)).encode())
        with tempfile.TemporaryDirectory() as directory,patch('bible.library.download',side_effect=download):
            root=Path(directory)
            records=languages(root);rows=editions('spa',root)
            self.assertEqual(len(records),1);self.assertEqual(len(rows),2)
            self.assertTrue(rows[0].installable);self.assertFalse(rows[1].installable)
            self.assertEqual(requests,[CONFIGURATION_URL,VERSIONS_URL.format(language='spa')])
            self.assertTrue(all(json.loads(r.acquisition)['_catalogue_summary'] for r in rows))
            stamp=(root/'spa.json').stat().st_mtime_ns
            self.assertEqual(editions('spa',root),rows);self.assertEqual(languages(root),records)
            self.assertEqual((root/'spa.json').stat().st_mtime_ns,stamp)
            self.assertEqual(len(requests),2)
            self.assertEqual(saved_languages(root),records)

    def test_bad_refresh_preserves_previous_language_list(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);good=envelope(dict(versions=[listing()]))
            with patch('bible.library.download',side_effect=lambda url,out,**kw:out.write(json.dumps(good).encode())):
                original=editions('spa',root)
            saved=(root/'spa.json').read_bytes()
            wrong=listing(900022,tag='fra')
            with patch('bible.library.download',side_effect=lambda url,out,**kw:out.write(json.dumps(envelope(dict(versions=[wrong]))).encode())):
                with self.assertRaises(ValueError):editions('spa',root,force=True)
            self.assertEqual((root/'spa.json').read_bytes(),saved)
            with patch('bible.library.download',side_effect=AssertionError('Unexpected network')):
                self.assertEqual(editions('spa',root),original)

    def test_unavailable_or_untrusted_source_is_never_a_downloadable_placeholder(self):
        for change in [dict(id=True),dict(language=language('fra')),dict(local_title=' ',title=' '),
                       dict(offline=dict(url='https://untrusted.invalid/bible/text/offline/900021-1.zip')),
                       dict(offline=dict(url='//offline-bibles-cdn.youversionapi.com/bible/text/offline/21-1.zip')),
                       dict(offline=dict(url=None,require_email_agreement='yes'))]:
            value={**listing(),**change}
            with self.assertRaises(ValueError):resource_from_listing(value,'spa')
        self.assertFalse(resource_from_listing(listing(offline=False),'spa').installable)
