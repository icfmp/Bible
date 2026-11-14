"""Native consumer quiescence before module replacement, not stale-handle reuse."""
import os,tempfile,unittest,weakref
from pathlib import Path
from dataclasses import replace,asdict
from unittest.mock import patch
from tests.test_module_lifecycle import package
from tests.test_ui import spin,close_test_dialogs


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires actual GTK/SWORD')
class ModuleUILifecycleTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        from bible.providers import CROSSWIRE
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()));self.library=Library(self.root/'translations')
        self.old,self.old_zip=package('1.0','ORIGINAL MODULE WORDING')
        self.new,self.new_zip=package('1.1','UPDATED MODULE WORDING')
        other=replace(self.old,provider_id=CROSSWIRE.id,source=CROSSWIRE.name,source_url=CROSSWIRE.url,acquisition='')
        with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(self.old_zip)):
            self.library.install(self.old);self.library.install(other)
        app=Application.get_default() or Application();app.register()
        self.w=Window(app,self.library);self.w.set_default_size(1280,900);self.w.present();spin()
        self.w.application_settings.set('automatic_catalogue_refresh',False)
        tab=self.w.active_tab;tab.navigate(self.old.id,'Gen.1.1');tab.state.comparison=other.id;self.w.sync_comparison()
        self.w.study_button.set_active(True);self.w.study.tools.set_visible_child_name('notes')
        self.note=self.w.notes_store.save('Existing **personal note**',('Keep',),versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation=self.old.id,origin_language='en')
        self.w.highlights.set('KJV',['Gen.1.1'],'yellow',self.old.id)
        self.w.study.notes.refresh(force=True);spin(lambda:not tab._restoring_scroll)
        self.dialog=self.w.open_library();spin(lambda:not self.dialog.preparing)

    def tearDown(self):
        if self.w.note_editor:self.w.note_editor._discard=True;self.w.note_editor.close()
        close_test_dialogs();self.dialog.close();self.w.close()

    def test_update_releases_primary_comparison_and_hidden_caches_without_losing_draft(self):
        from bible.module_lifecycle import ModuleLifecycle
        from bible.module_ui_lifecycle import ModuleViewChange
        w=self.w;tab=w.active_tab
        editor=w.study.notes.open_note(self.note);editor.body.get_buffer().set_text('Unsaved personal draft')
        before=[asdict(n) for n in w.notes_store.all()];history=list(tab.state.history)
        old_reader=weakref.ref(tab.reader)
        # Exercise the hidden native-owner caches as well as the visible pane.
        w.navigation.reader=tab.reader;w.search_popover.text_search.search_reader=tab.reader
        w.search_popover.reader=tab.reader
        tab.inline_markers.editorial[(tab.reader,'retained-chapter')]=()
        bridge=ModuleViewChange(self.dialog,self.old.id);lifecycle=ModuleLifecycle(self.library)
        with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(self.new_zip)):
            self.dialog.task('Updating',lambda:lifecycle.update(self.new,before_switch=bridge.before_switch),
                             lambda _:None,resource=self.new,settled=bridge.resume)
            spin(lambda:not self.dialog.busy,timeout=15,duration=.3)
        self.assertEqual(self.dialog._phase,'complete',self.dialog.status.get_text())
        self.assertIsNone(old_reader());self.assertIn('UPDATED MODULE WORDING',tab.text.get_buffer().props.text)
        self.assertIn('ORIGINAL MODULE WORDING',tab.comparison_text.get_buffer().props.text)
        self.assertEqual(tab.state.history,history);self.assertEqual(tab.state.reference,'Gen.1.1')
        self.assertIs(w.study.notes.editor,editor);self.assertEqual(editor.body.get_buffer().props.text,'Unsaved personal draft')
        self.assertEqual([asdict(n) for n in w.notes_store.all()],before)
        self.assertEqual(w.highlights.entries[('KJV','Gen.1.1')]['color'],'yellow')

    def test_failed_download_leaves_existing_native_reader_and_text_usable(self):
        from bible.module_lifecycle import ModuleLifecycle
        from bible.module_ui_lifecycle import ModuleViewChange
        tab=self.w.active_tab;old=tab.reader;bridge=ModuleViewChange(self.dialog,self.old.id)
        with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(self.new_zip+b'corrupt')):
            self.dialog.task('Updating',lambda:ModuleLifecycle(self.library).update(self.new,before_switch=bridge.before_switch),
                             lambda _:None,resource=self.new,settled=bridge.resume)
            spin(lambda:not self.dialog.busy,timeout=15)
        self.assertEqual(self.dialog._phase,'error');self.assertIs(tab.reader,old)
        self.assertIn('ORIGINAL MODULE WORDING',tab.text.get_buffer().props.text)
        self.assertEqual(self.library.resource(self.old.id).version,'1.0')
