"""Main-loop responsiveness, shared work and close/exit with slow metadata."""
from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from tests.test_library import RESOURCE
from tests.test_ui import spin,close_test_dialogs
from bible.library import Library,CatalogueResult
from bible.catalogue_cache import CatalogueCache
from bible.providers import CROSSWIRE


class MetadataExitTests(unittest.TestCase):
    def test_process_exit_never_joins_blocked_catalogue_workers(self):
        code='''from bible.metadata_workers import MetadataExecutor
from bible.library import catalogues
from bible.providers import CROSSWIRE
from unittest.mock import patch
from threading import Event
entered=Event();release=Event()
def stalled(*args,**kwargs):entered.set();release.wait(60);return []
with patch('bible.library.catalogue',side_effect=stalled):
    worker=MetadataExecutor();worker.submit(catalogues,(CROSSWIRE,))
    assert entered.wait(2)
    worker.shutdown(wait=False,cancel_futures=True)
    print('EXIT_WITH_BLOCKED_NETWORK',flush=True)
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=4)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('EXIT_WITH_BLOCKED_NETWORK',result.stdout)


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class LibraryStartupTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        from bible.ui import Application,Window
        app=Application.get_default() or Application();app.register()
        self.window=Window(app,Library(self.root/'translations'));self.window.present()
        self.window.application_settings.set('library_language','en')
        self.enterContext(patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False))

    def tearDown(self):
        close_test_dialogs();self.window.close()

    def test_slow_cache_opens_shell_and_close_reopen_share_one_preparation(self):
        entered=threading.Event();release=threading.Event();calls=[];self.addCleanup(release.set)
        def read(_,provider):
            calls.append((provider.id,threading.get_ident()));entered.set();release.wait(3)
            return ((RESOURCE,),time.time()) if provider==CROSSWIRE else None
        owner=threading.get_ident()
        with patch.object(CatalogueCache,'read',read):
            start=time.monotonic();first=self.window.open_library()
            self.assertLess(time.monotonic()-start,.5);self.assertTrue(entered.wait(.5))
            ticks=[]
            from gi.repository import GLib
            timer=GLib.timeout_add(10,lambda:ticks.append(time.monotonic()) or True)
            try:spin(lambda:len(ticks)>=5,duration=.12,timeout=.5)
            finally:GLib.source_remove(timer)
            self.assertTrue(first.preparing);self.assertTrue(first.get_mapped())
            start=time.monotonic();first.close();self.assertLess(time.monotonic()-start,.2)
            reopened=self.window.open_library();self.assertIs(first.session,reopened.session)
            self.assertEqual(len(calls),1);release.set();spin(lambda:not reopened.busy)
            self.assertEqual([r.id for r in reopened.resources],[RESOURCE.id])
            self.assertTrue(all(thread!=owner for _,thread in calls));self.assertEqual(len(calls),5)
            self.assertEqual(first.choice_model.get_n_items(),0)

    def test_reopen_during_slow_refresh_deduplicates_and_keeps_progressive_results(self):
        entered=threading.Event();release=threading.Event();calls=[];self.addCleanup(release.set)
        def fetch(**kwargs):
            calls.append(1);kwargs['on_provider'](CROSSWIRE,[RESOURCE],None,{})
            entered.set();release.wait(3);return CatalogueResult((RESOURCE,),{})
        with patch('bible.catalogue_window.catalogue',side_effect=fetch):
            first=self.window.open_library();first.load_catalogue()
            spin(lambda:bool(first.resources));self.assertTrue(entered.is_set());self.assertTrue(first.refreshing)
            first.close();second=self.window.open_library();second.load_catalogue()
            spin(lambda:bool(second.resources));self.assertEqual(len(calls),1)
            self.assertTrue(second.download_button.get_sensitive())
            release.set();spin(lambda:not second.busy)
            self.assertEqual(second.selected_resource().id,RESOURCE.id)

    def test_large_valid_cache_uses_owner_thread_bounded_models_and_keeps_heartbeat(self):
        from bible.catalogue_window import ResourceItem
        from gi.repository import GLib
        cache=CatalogueCache(self.root/'catalogue-cache')
        cache.write(CROSSWIRE,[replace(RESOURCE,name=f'Fixture{i:05d}') for i in range(8000)])
        original=ResourceItem.__init__;owner=threading.get_ident();threads=[]
        def construct(item,resource):threads.append(threading.get_ident());original(item,resource)
        ticks=[];timer=GLib.timeout_add(10,lambda:ticks.append(time.monotonic()) or True)
        try:
            with patch.object(ResourceItem,'__init__',construct):
                start=time.monotonic();dialog=self.window.open_library()
                self.assertLess(time.monotonic()-start,.5)
                loop=GLib.MainLoop();deadline=time.monotonic()+8
                def settled():
                    if dialog.busy and time.monotonic()<deadline:return True
                    loop.quit();return False
                GLib.timeout_add(10,settled);loop.run();self.assertFalse(dialog.busy)
                self.assertEqual(dialog.choice_model.get_n_items(),8000)
                self.assertTrue(threads and all(thread==owner for thread in threads))
                self.assertGreaterEqual(len(ticks),5)
                self.assertLess(max(b-a for a,b in zip(ticks,ticks[1:])),.5)
                dialog.choices.set_selected(7999);selected=dialog.selected_resource().id
                generation=dialog._rows_generation
                dialog.filter_resources()
                self.assertEqual(dialog._rows_generation,generation);self.assertEqual(dialog.selected_resource().id,selected)
        finally:GLib.source_remove(timer)

    def test_metadata_failure_is_visible_and_retry_does_not_remain_busy(self):
        with patch.object(CatalogueCache,'read',side_effect=OSError('metadata failure fixture')):
            dialog=self.window.open_library();spin(lambda:not dialog.preparing)
            self.assertIn('metadata failure fixture',dialog.refresh_status.get_text())
        with patch('bible.catalogue_window.catalogue',return_value=CatalogueResult((RESOURCE,),{})):
            dialog.load_catalogue();spin(lambda:not dialog.busy)
        self.assertEqual(dialog.selected_resource().id,RESOURCE.id)

    def test_refresh_status_keeps_unchanged_native_models_and_selection(self):
        cache=CatalogueCache(self.root/'catalogue-cache');cache.write(CROSSWIRE,[RESOURCE])
        dialog=self.window.open_library();spin(lambda:not dialog.busy)
        changes=[];language_changes=[]
        dialog.choice_model.connect('items-changed',lambda *_:changes.append(1))
        dialog.language.strings.connect('items-changed',lambda *_:language_changes.append(1))
        snapshot=replace(dialog.session.snapshot,refreshing=True,generation=2)
        dialog.apply_snapshot(snapshot)
        self.assertTrue(dialog.refreshing);self.assertEqual(changes,[]);self.assertEqual(language_changes,[])
        self.assertEqual(dialog.selected_resource().id,RESOURCE.id)

    def test_large_language_changes_use_bounded_native_updates_and_discard_stale_search(self):
        from bible.language_picker import LanguagePicker
        picker=LanguagePicker(lambda:None);changes=[]
        picker.strings.connect('items-changed',lambda _,position,removed,added:changes.append((removed,added)))
        picker.set_codes(['','fr'],{'fr':('French','French (fr)','fr')})
        picker.filter(force=True)
        codes=['']+[f'fixture{i}' for i in range(2000)]+['fr']
        records={code:(code,code,code) for code in codes if code}
        records['fr']=('French','French (fr)','fr')
        picker.set_codes(codes,records)
        self.assertLessEqual(picker.strings.get_n_items(),18)
        picker.activate(None,picker.strings.get_n_items()-1)
        self.assertEqual(picker.codes[picker.get_selected()],'fr')
        picker.search.set_text('fixture1999');picker.filter()
        spin(lambda:picker.strings.get_n_items()==2 and picker.strings.get_string(1)=='fixture1999')
        self.assertEqual(picker.strings.get_string(1),'fixture1999')
        self.assertTrue(all(max(change)<=16 for change in changes))

    def test_reopen_rechecks_resources_installed_by_another_window(self):
        from tests.test_ui import installed_fixture
        first=self.window.open_library();spin(lambda:not first.busy);first.close()
        installed_fixture(self.root)
        second=self.window.open_library()
        spin(lambda:'Test' in second.installed_ids())
        self.assertEqual(second.selected_resource().id,'Test')
        self.assertIn('Public Domain',second.metadata.get_text())
        self.assertTrue(second.installed_state.get_visible());self.assertFalse(second.download_button.get_visible())


if __name__=='__main__':unittest.main()
