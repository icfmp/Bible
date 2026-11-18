"""Real native installs and reference indexing through the shared GTK queue."""
from dataclasses import asdict
import os,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from bible.library import Library,config,resource_from_section
from tests.test_library import archive_bytes
from tests.test_ui import installed_fixture,spin


def package(name,commentary=False):
    from tests.fixtures import module_fixture
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        module_fixture(root,name,[('Gen.1.1',name+' QUEUE TEST DATA')],commentary=commentary)
        resource=resource_from_section(name,config((root/'mods.d/test.conf').read_bytes())[name])
        return resource,archive_bytes({str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK/SWORD')
class DownloadQueueUITests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window
        from bible.application_settings import ApplicationSettings
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        installed_fixture(self.root,'Existing')
        settings=ApplicationSettings(self.root);settings.set('automatic_catalogue_refresh',False);settings.set('library_language','en')
        self.enterContext(patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False))
        self.enterContext(patch('bible.catalogue_session.CatalogueSession.load_youversion_language',return_value=None))
        self.library=Library(self.root/'translations');self.app=Application.get_default() or Application();self.app.register()
        self.windows=[];self.w=self.window();self.d=self.w.open_library();spin(lambda:not self.d.preparing)
        self.a,self.a_zip=package('First');self.b,self.b_zip=package('Second',True);self.c,self.c_zip=package('Third')
        self.d.resources=[self.a,self.b,self.c];self.d.update_languages();spin(lambda:not self.d._building_rows)
        self.entered=threading.Event();self.release=threading.Event();self.calls=[];self.inflight=set();self.lock=threading.Lock()
        self.payloads={'First.zip':self.a_zip,'Second.zip':self.b_zip,'Third.zip':self.c_zip}

    def window(self):
        from bible.ui import Window
        w=Window(self.app,self.library);self.windows.append(w);w.present();spin();return w

    def tearDown(self):
        self.release.set()
        for w in self.windows:
            if not w.closed:w.close()
        spin(duration=.1)

    def transfer(self,url,output,progress=lambda *_:None,**_):
        name=url.rsplit('/',1)[-1]
        with self.lock:
            self.assertFalse(self.inflight,'Overlapping archive transfers')
            self.inflight.add(name);self.calls.append(name)
        try:
            if name=='First.zip' and not self.release.is_set():
                self.entered.set()
                if not self.release.wait(8):raise TimeoutError('Fixture transfer was not released')
            data=self.payloads[name];output.write(data);progress(len(data),len(data))
        finally:
            with self.lock:self.inflight.remove(name)

    def settled(self):
        return not self.d.busy and not any(r.state in ('active','queued') for r in self.d.downloads.requests)

    def test_mixed_backends_continue_hidden_share_windows_and_preserve_browsing_and_notes(self):
        from bible.study_catalogue import CATALOGUE_URL
        from bible.study_resources import REFERENCE_RESOURCE_ID
        from tests.test_study_catalogue import archive,revision,catalogue
        payload=archive(self.root/'references.zip','references','2026-11-02','John.1.5\tIsa.9.2\t18\n')
        wanted=revision(REFERENCE_RESOURCE_ID,payload);metadata=catalogue(**{REFERENCE_RESOURCE_ID:wanted})
        def receive(url,output,progress=lambda *_:None,**kwargs):
            if url==CATALOGUE_URL:output.write(metadata);progress(len(metadata),len(metadata));return
            if url==wanted.url:
                self.assertTrue((self.library.root/self.b.id/'.complete').exists(),'Study install overtook native validation')
                self.calls.append(REFERENCE_RESOURCE_ID);output.write(payload);progress(len(payload),len(payload));return
            if url.endswith('Second.zip'):self.assertTrue((self.library.root/self.a.id/'.complete').exists())
            return self.transfer(url,output,progress,**kwargs)
        note=self.w.notes_store.save('Preserved note',[],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='Existing',origin_language='en')
        before=asdict(note);reference=self.w.active_tab.state.reference
        with patch('bible.library.download',side_effect=receive):
            self.d.install(resource=self.a);spin(lambda:self.entered.is_set())
            self.d.install(resource=self.b);self.d.install(resource=self.b)
            self.d.kind.set_selected(2);spin(lambda:not self.d._building_rows)
            self.d.install(resource=self.d.study_resources.resource(REFERENCE_RESOURCE_ID))
            spin(lambda:self.d.downloads.find(REFERENCE_RESOURCE_ID) is not None)
            self.assertEqual([r.resource.id for r in self.d.downloads.requests],[self.a.id,self.b.id,REFERENCE_RESOURCE_ID])
            self.d.kind.set_selected(0);self.d.search.set_text('Third');spin()
            language=self.d.language_choice;selected_source=self.d.source_filter.get_selected()
            self.d.close();self.assertFalse(self.d.closed);self.assertFalse(self.d.get_visible())
            second=self.window();self.assertIs(second.open_library(),self.d)
            self.w.close();self.assertFalse(self.d.closed);self.assertIs(self.d.owner,second)
            self.release.set();spin(self.settled,timeout=20)
        self.assertEqual(self.calls,['First.zip','Second.zip',REFERENCE_RESOURCE_ID])
        self.assertEqual(self.d.search.get_text(),'Third');self.assertEqual(self.d.language_choice,language)
        self.assertEqual(self.d.source_filter.get_selected(),selected_source)
        self.assertEqual(second.active_tab.state.resource,'Existing');self.assertEqual(second.active_tab.state.reference,reference)
        self.assertEqual(asdict(second.notes_store.get(note.id)),before)
        self.assertEqual(self.d.study_resources.references.query(['John.1.5'])[0].start,'Isa.9.2')
        from bible.sword_provider import Reader,CommentaryReader
        self.assertIn('First QUEUE TEST DATA',Reader(self.library.root/self.a.id,self.a.name).chapter('Gen.1.1').verses[0][1])
        self.assertEqual(CommentaryReader(self.library.root/self.b.id,self.b.name).entry('Gen.1.1','KJV'),'Second QUEUE TEST DATA')

    def test_pending_active_cancel_and_corrupt_source_do_not_block_a_later_install_or_retry(self):
        with patch('bible.library.download',side_effect=self.transfer):
            self.d.install(resource=self.a);spin(lambda:self.entered.is_set())
            self.d.install(resource=self.b);self.d.row_action(self.b)
            self.assertIsNone(self.d.downloads.find(self.b.id))
            self.payloads['Second.zip']=b'Invalid archive';self.d.install(resource=self.b);self.d.install(resource=self.c)
            self.d.cancel_download();self.release.set();spin(self.settled,timeout=20)
            self.assertFalse((self.library.root/self.a.id).exists());self.assertFalse((self.library.root/self.b.id).exists())
            self.assertIn(self.c.id,self.library.installed())
            self.assertEqual(self.d.downloads.find(self.a.id).state,'failed');self.assertEqual(self.d.downloads.find(self.b.id).state,'failed')
            self.payloads['Second.zip']=self.b_zip
            self.d.install(resource=self.a);self.d.install(resource=self.b);spin(self.settled,timeout=20)
        self.assertEqual(set(self.library.installed()),{'Existing',self.a.id,self.b.id,self.c.id})
        self.assertFalse(self.d.downloads.requests)

    def test_last_window_close_pauses_requests_and_restart_does_not_transfer_until_resume(self):
        with patch('bible.library.download',side_effect=self.transfer):
            self.d.install(resource=self.a);spin(lambda:self.entered.is_set());self.d.install(resource=self.b)
            self.w.close();self.release.set();spin(lambda:not self.inflight,duration=.2)
            self.assertTrue(self.d.closed)
            self.w=self.window();self.d=self.w.open_library();spin(lambda:not self.d.preparing)
            self.assertEqual(self.calls,['First.zip'])
            self.assertEqual([r.state for r in self.d.downloads.requests],['paused','paused'])
            self.d.resume_queue();spin(self.settled,timeout=20)
        self.assertEqual(self.calls,['First.zip','First.zip','Second.zip'])
        self.assertEqual(set(self.library.installed()),{'Existing',self.a.id,self.b.id})

    def test_committed_install_is_discovered_after_restart_without_redownloading_it(self):
        self.d.downloads.enqueue(self.a);self.d.downloads.start();self.d.downloads.enqueue(self.b)
        self.release.set()
        with patch('bible.library.download',side_effect=self.transfer):self.library.install(self.a)
        self.w.close();spin()
        self.w=self.window();self.d=self.w.open_library();spin(lambda:not self.d.preparing)
        self.assertEqual(self.calls,['First.zip'])
        with patch('bible.library.download',side_effect=self.transfer):self.d.resume_queue();spin(self.settled,timeout=20)
        self.assertEqual(self.calls,['First.zip','Second.zip'])

    def test_a_conflicting_version_request_does_not_block_the_existing_queue(self):
        from dataclasses import replace
        self.d.downloads.enqueue(self.a);self.release.set()
        with patch('bible.library.download',side_effect=self.transfer):
            self.d.queue_request(replace(self.a,version='2.0'))
            self.assertIsNone(self.d._queue_problem)
            self.d.queue_request(self.b);spin(self.settled,timeout=20)
        self.assertEqual(self.calls,['First.zip','Second.zip'])
        self.assertEqual(self.library.resource(self.a.id).version,'')
