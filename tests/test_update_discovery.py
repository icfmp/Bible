"""Startup discovery stays asynchronous and uses the existing safe queue."""
import json,os,tempfile,threading,unittest
from pathlib import Path
from dataclasses import replace,asdict
from unittest.mock import patch
from tests.test_ui import spin,close_test_dialogs
from tests.test_library import archive_bytes
from tests.test_curated_catalogue import record


def resource_package(name,version,*,commentary=False):
    from tests.fixtures import module_fixture
    from bible.library import config,resource_from_section
    from bible.providers import BIBLE_RESOURCES
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)/name
        module_fixture(root,name,[('Gen.1.1','EXPLICIT SYNTHETIC UPDATE FIXTURE '+version)],commentary=commentary)
        conf=next((root/'mods.d').glob('*.conf'))
        conf.write_bytes(conf.read_bytes()+f'Version={version}\nTextSource=Identified synthetic update fixture\n'.encode())
        payload=archive_bytes({str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})
        entry=dict(record(payload),id=name,canonical_edition_id='fixture-'+name,sword_id=name,version=version,category='commentary' if commentary else 'bible')
        entry['download']['url']=BIBLE_RESOURCES.packages_url+name+'.zip'
        resource=replace(resource_from_section(name,config(conf.read_bytes())[name],BIBLE_RESOURCES),acquisition=json.dumps(dict(catalogue_url=BIBLE_RESOURCES.catalogue_url,entry=entry)))
    return resource,payload


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK/SWORD')
class DiscoveryTests(unittest.TestCase):
    def test_slow_discovery_is_shared_and_updates_use_existing_queue_with_failure_isolation(self):
        from bible.ui import Application,Window,Library
        from bible.application_settings import ApplicationSettings
        from bible.catalogue_cache import CatalogueCache
        from bible.providers import BIBLE_RESOURCES
        from bible.library import CatalogueResult
        from bible.update_discovery import discovery
        root=Path(self.enterContext(tempfile.TemporaryDirectory()));library=Library(root/'translations')
        old,payload=resource_package('StudyBible','1.0');new,new_payload=resource_package('StudyBible','1.1')
        old_com,com_payload=resource_package('StudyCommentary','1.0',commentary=True)
        new_com,new_com_payload=resource_package('StudyCommentary','1.1',commentary=True)
        with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(com_payload if 'StudyCommentary' in url else payload)):
            library.install(old);library.install(old_com)
        from tests.test_study_catalogue import archive,revision,catalogue
        from bible.study_resources import StudyResources,REFERENCE_RESOURCE_ID
        from bible.study_catalogue import CATALOGUE_URL
        old_refs=archive(root/'old-refs.zip','references','2026-10-19','John.1.5\tGen.1.3\t1\n')
        new_refs=archive(root/'new-refs.zip','references','2026-11-02','John.1.5\tIsa.9.2\t18\n')
        old_revision=revision(REFERENCE_RESOURCE_ID,old_refs,'2026-10-19');new_revision=revision(REFERENCE_RESOURCE_ID,new_refs)
        study=StudyResources(root/'study-data');study.references.install_archive(root/'old-refs.zip',revision=old_revision)
        study_metadata=catalogue(**{REFERENCE_RESOURCE_ID:new_revision});study.catalogue.path.write_bytes(catalogue(**{REFERENCE_RESOURCE_ID:old_revision}))
        settings=ApplicationSettings(root);settings.set('automatic_catalogue_refresh',False)
        app=Application.get_default() or Application();app.register();w=Window(app,library);w.present();spin()
        second=Window(app,library);second.present();spin()
        self.addCleanup(lambda:(close_test_dialogs(),second.close(),w.close()))
        manager=discovery(w);self.assertIs(manager,discovery(second))
        self.assertFalse(w.resource_updates_button.get_visible())
        note=w.notes_store.save('Preserved note',[],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation=old.id,origin_language='en')
        before=asdict(note);began=threading.Event();release=threading.Event();calls=[]
        def fetch(**kwargs):
            calls.append(tuple(p.id for p in kwargs['providers']));began.set()
            if not release.wait(10):raise TimeoutError('Test network did not resume')
            CatalogueCache(root/'catalogue-cache').write(BIBLE_RESOURCES,[new,new_com])
            study.catalogue.path.write_bytes(study_metadata)
            kwargs['on_provider'](BIBLE_RESOURCES,[new,new_com],None,{})
            return CatalogueResult((new,new_com),{})
        with patch('bible.library.catalogues',side_effect=fetch):
            manager.start(True);manager.start(True);manager.check()
            spin(began.is_set);self.assertTrue(manager.checking)
            w.active_tab.navigate(old.id,'Gen.1.1');spin()
            self.assertIn('SYNTHETIC UPDATE FIXTURE 1.0',w.active_tab.text.get_buffer().props.text)
            self.assertEqual(library.resource(old.id).version,'1.0') # discovery never installs
            release.set();spin(lambda:not manager.checking and len(manager.eligible())==3)
        self.assertEqual(calls,[('bible-resources',)])
        self.assertTrue(w.resource_updates_button.get_visible());self.assertTrue(second.resource_updates_button.get_visible())
        # One rejected update must not prevent the later commentary update.
        def download(url,out,progress=lambda *_:None,**kwargs):
            data=(study_metadata if url==CATALOGUE_URL else new_refs if url==new_revision.url else
                  new_com_payload if 'StudyCommentary' in url else new_payload+b'CORRUPT')
            out.write(data);progress(len(data),len(data))
        with patch('bible.library.download',side_effect=download),patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
            dialog=manager.queue_all(w)
            spin(lambda:not dialog.busy and not dialog._queue_active and not any(r.state in ('queued','active') for r in dialog.downloads.requests),timeout=20)
        self.assertEqual(library.resource(old.id).version,'1.0')
        self.assertEqual(library.resource(old_com.id).version,'1.1')
        self.assertEqual(dialog.downloads.find(old.id).state,'failed')
        self.assertEqual(study.references.metadata()['archive_sha256'],new_revision.sha256)
        self.assertEqual(study.references.query(['John.1.5'])[0].start,'Isa.9.2')
        self.assertEqual(asdict(w.notes_store.get(note.id)),before)
        self.assertEqual(w.active_tab.state.resource,old.id)
        with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(new_payload)):
            manager.queue_all(w)
            spin(lambda:not dialog.busy and not dialog.downloads.requests,timeout=20)
        self.assertEqual(library.resource(old.id).version,'1.1')
        spin(lambda:not manager.eligible())
        self.assertFalse(w.resource_updates_button.get_visible());self.assertFalse(second.resource_updates_button.get_visible())
        # Closing one window must not stop the other window's metadata service.
        second.close();self.assertFalse(manager.session.closed)

    def test_fresh_cache_avoids_network_but_expired_offline_metadata_never_claims_current(self):
        from bible.ui import Application,Window,Library
        from bible.application_settings import ApplicationSettings
        from bible.catalogue_cache import CatalogueCache
        from bible.providers import BIBLE_RESOURCES
        from bible.update_discovery import discovery
        root=Path(self.enterContext(tempfile.TemporaryDirectory()));library=Library(root/'translations')
        old,payload=resource_package('CachedBible','1.0');new,_=resource_package('CachedBible','1.1')
        with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(payload)):library.install(old)
        ApplicationSettings(root).set('automatic_catalogue_refresh',False)
        cache=CatalogueCache(root/'catalogue-cache');cache.write(BIBLE_RESOURCES,[new])
        app=Application.get_default() or Application();app.register();w=Window(app,library);w.present();spin()
        self.addCleanup(lambda:(close_test_dialogs(),w.close()))
        manager=discovery(w)
        self.assertFalse(manager.started);self.assertFalse(manager.checking)
        with patch('bible.library.catalogue',side_effect=AssertionError('Fresh cache should avoid network')) as fetch:
            manager.start(True);spin(lambda:not manager.checking and bool(manager.reports))
        self.assertEqual(fetch.call_count,0);self.assertEqual(manager.reports[old.id]['state'],'available')
        path=cache.root/'bible-resources.json';data=json.loads(path.read_text());data['updated']=0;path.write_text(json.dumps(data))
        manager.session.verified_providers.clear()
        with patch('bible.library.catalogue',side_effect=OSError('Explicit offline test')):
            manager.check();spin(lambda:not manager.checking and manager.state=='offline')
        spin(lambda:manager.reports[old.id]['state']=='offline')
        self.assertFalse(manager.eligible());self.assertFalse(w.resource_updates_button.get_visible())
        self.assertEqual(library.resource(old.id).version,'1.0')

    def test_study_offline_metadata_is_not_a_verified_update(self):
        from bible.update_discovery import ResourceUpdates
        from bible.library import Library
        from bible.study_resources import REFERENCE_RESOURCE_ID
        from tests.test_study_catalogue import archive,revision,catalogue
        root=Path(self.enterContext(tempfile.TemporaryDirectory()));manager=ResourceUpdates(Library(root/'translations'))
        self.addCleanup(manager.session.close);manager.session.bootstrap_future.result(10)
        old=archive(root/'old.zip','references','2026-10-19','John.1.5\tGen.1.3\t1\n')
        new=archive(root/'new.zip','references','2026-11-02','John.1.5\tIsa.9.2\t18\n')
        before=revision(REFERENCE_RESOURCE_ID,old,'2026-10-19');after=revision(REFERENCE_RESOURCE_ID,new)
        manager.session.study.references.install_archive(root/'old.zip',revision=before)
        manager.session.study.catalogue.path.write_bytes(catalogue(**{REFERENCE_RESOURCE_ID:after}))
        reports={};manager.add_study(reports,{'Study tools':'Offline test'})
        self.assertEqual(reports[REFERENCE_RESOURCE_ID]['state'],'offline')
        self.assertEqual(manager.session.study.references.metadata()['archive_sha256'],before.sha256)
