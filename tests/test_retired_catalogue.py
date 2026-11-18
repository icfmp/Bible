"""Removal history is not a live provider catalogue or an availability proof."""
from dataclasses import asdict,replace
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from bible.catalogue_cache import CatalogueCache
from bible.catalogue_session import CatalogueSession
from bible.library import Library,catalogues
from bible.module_lifecycle import ModuleLifecycle
from bible.providers import BIBLE_RESOURCES,CROSSWIRE,YOUVERSION
from tests.test_library import RESOURCE
from tests.test_curated_catalogue import record


def commentary(name,version):
    entry=record();entry.update(id='mhcc-crosswire',canonical_edition_id='mhcc-crosswire',
        sword_id=name,version=version,category='commentary')
    entry['download']['url']=BIBLE_RESOURCES.packages_url+name+'.zip'
    return replace(RESOURCE,name=name,version=version,description='Same source title',driver='RawCom',
        category='Commentaries',provider_id=BIBLE_RESOURCES.id,source=BIBLE_RESOURCES.name,
        source_url=BIBLE_RESOURCES.url,acquisition=json.dumps(dict(catalogue_url=BIBLE_RESOURCES.catalogue_url,entry=entry)))


class RetiredCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.library=Library(self.root/'translations')
        self.old=commentary('BRMHCC','0.1.0');self.current=commentary('MHCC','0.1.1')
        lifecycle=ModuleLifecycle(self.library)
        folder,journal=lifecycle.begin(self.old.id,'remove',{})
        journal.update(state='committed',resource_metadata=asdict(self.old));lifecycle.journal(folder,journal)
        self.journal=folder/'journal.json';self.before=self.journal.read_bytes()

    def session(self):
        session=CatalogueSession(self.library);self.addCleanup(session.close)
        session.bootstrap_future.result(timeout=5)
        return session

    def refresh(self,session,items,error=None):
        with patch('bible.library.catalogue',side_effect=error,return_value=items):
            session.refresh(catalogues,True,(BIBLE_RESOURCES,)).result(timeout=5)
            session.schedule(lambda:None).result(timeout=5)

    def test_replaced_sword_id_does_not_resurrect_from_journal_after_refresh_or_reopen(self):
        CatalogueCache(self.root/'catalogue-cache').write(BIBLE_RESOURCES,[self.old])
        session=self.session()
        self.assertIn(self.old.id,session.snapshot.archived_resources)
        self.refresh(session,[self.current])
        self.assertEqual([r.id for r in session.snapshot.resources],[self.current.id])
        self.assertFalse(session.snapshot.archived_resources)
        self.assertEqual(self.journal.read_bytes(),self.before)
        session.close();reopened=self.session()
        self.assertEqual([r.id for r in reopened.snapshot.resources],[self.current.id])
        self.assertEqual(ModuleLifecycle(self.library).removed_resources()[self.old.id],self.old)

    def test_offline_history_is_archived_until_current_availability_is_verified(self):
        cache=CatalogueCache(self.root/'catalogue-cache');cache.write(BIBLE_RESOURCES,[self.old])
        session=self.session();self.refresh(session,[],OSError('offline'))
        self.assertEqual(session.snapshot.resources,(self.old,))
        self.assertEqual(session.snapshot.archived_resources,frozenset((self.old.id,)))
        self.assertIn(BIBLE_RESOURCES.name,session.snapshot.errors)
        self.refresh(session,[self.old]);self.assertFalse(session.snapshot.archived_resources)
        self.refresh(session,[],OSError('offline again'))
        self.assertIn(self.old.id,session.snapshot.archived_resources)
        self.assertEqual(self.journal.read_bytes(),self.before)

    def test_current_same_id_version_and_distinct_provider_titles_are_not_deduplicated(self):
        session=self.session();new=replace(self.old,version='0.1.2')
        foreign=replace(self.current,provider_id=CROSSWIRE.id,source=CROSSWIRE.name,source_url=CROSSWIRE.url,acquisition='')
        session.providers[CROSSWIRE.id]=(foreign,)
        self.refresh(session,[new])
        self.assertEqual({r.id:r.version for r in session.snapshot.resources},{new.id:'0.1.2',foreign.id:'0.1.1'})
        self.assertFalse(session.snapshot.archived_resources)

    def test_installed_retired_edition_is_preserved_separately_from_new_download(self):
        session=self.session();session.installed={self.old.id:self.old}
        self.refresh(session,[self.current])
        self.assertEqual(session.snapshot.installed[self.old.id],self.old)
        self.assertEqual(session.snapshot.resources,(self.current,))
        self.assertEqual(self.journal.read_bytes(),self.before)

    def test_partial_youversion_language_catalogue_does_not_retire_another_language(self):
        session=self.session()
        historical=replace(RESOURCE,name='YV100',provider_id=YOUVERSION.id,source=YOUVERSION.name,source_url=YOUVERSION.url)
        session.removed[historical.id]=historical;session.providers[YOUVERSION.id]=()
        session.verified_providers.add(YOUVERSION.id)
        session.publish()
        self.assertIn(historical.id,{r.id for r in session.snapshot.resources})
        self.assertIn(historical.id,session.snapshot.archived_resources)

    @unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
    def test_archived_row_and_detail_cannot_start_download_then_current_refresh_replaces_it(self):
        from bible.ui import Application,Window
        from bible.application_settings import ApplicationSettings
        from tests.test_ui import installed_fixture,spin
        installed_fixture(self.root);settings=ApplicationSettings(self.root)
        settings.set('automatic_catalogue_refresh',False);settings.set('library_language','en')
        app=Application.get_default() or Application();app.register()
        w=Window(app,self.library);w.catalogue_session=self.session();w.present()
        try:
            d=w.open_library('commentary');spin(lambda:not d.preparing and not d._building_rows)
            self.assertIn(self.old.id,d._archived_ids)
            d.open_details(None,d.filtered_resources.index(self.old));spin()
            self.assertFalse(d.download_button.get_sensitive())
            with patch.object(d,'task',side_effect=AssertionError('Archived resource downloaded')):
                d.install(resource=self.old);d.row_action(self.old)
            self.refresh(w.catalogue_session,[self.current]);spin(lambda:self.current in d.resources and not d._building_rows)
            self.assertNotIn(self.old.id,{r.id for r in d.resources})
            d.open_details(None,d.filtered_resources.index(self.current));spin()
            self.assertTrue(d.download_button.get_sensitive())
            d.close();spin()
            d=w.open_library('commentary');spin(lambda:not d.preparing and not d._building_rows)
            self.assertNotIn(self.old.id,{r.id for r in d.resources})
            self.assertEqual(self.journal.read_bytes(),self.before)
            d.close()
        finally:w.close();spin()
