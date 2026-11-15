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
        self.assertIn('UPDATED MODULE WORDING',editor.excerpt.get_text())
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

    def test_workspace_note_keeps_unsaved_text_and_labels_while_its_source_excerpt_updates(self):
        w=self.w;self.dialog.close();w.open_notes();spin()
        space=w.notes_space;editor=space.open_note(self.note);spin()
        buffer=editor.body.get_buffer();buffer.set_text('Workspace unsaved draft')
        editor.labels.entry.set_text('pending label')
        notes=[asdict(n) for n in w.notes_store.all()]
        self.dialog=w.open_library();spin(lambda:not self.dialog.preparing)
        self.dialog.modules.reports[self.old.id]=dict(state='available',available=self.new,error='')
        self.dialog.language_choice='';self.dialog.update_languages();spin(lambda:not self.dialog._building_rows)
        self.dialog.open_details(None,next(i for i,r in enumerate(self.dialog.filtered_resources) if r.id==self.old.id))
        with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(self.new_zip)):
            self.dialog.modules.run('update');spin(lambda:not self.dialog.busy,timeout=15)
        self.assertEqual(self.dialog._phase,'complete',self.dialog.status.get_text())
        self.assertIs(space.editor,editor);self.assertIs(editor.body.get_buffer(),buffer)
        self.assertEqual(buffer.props.text,'Workspace unsaved draft');self.assertEqual(editor.labels.entry.get_text(),'pending label')
        self.assertIn('UPDATED MODULE WORDING',editor.excerpt.get_text())
        self.assertEqual([asdict(n) for n in w.notes_store.all()],notes)

    def test_closed_immersion_releases_its_sources_before_active_module_removal(self):
        w=self.w;self.dialog.close();self.assertTrue(w.enter_immersion());spin(duration=.5)
        closed=w.immersion
        self.dialog=w.open_library();spin(lambda:not self.dialog.preparing)
        self.dialog.language_choice='';self.dialog.update_languages();spin(lambda:not self.dialog._building_rows)
        self.dialog.open_details(None,next(i for i,r in enumerate(self.dialog.filtered_resources) if r.id==self.old.id))
        self.dialog.modules.run('remove');spin(lambda:not self.dialog.busy,timeout=15)
        self.assertEqual(self.dialog._phase,'complete',self.dialog.status.get_text())
        self.assertIsNone(w.immersion);self.assertIsNone(closed.source);self.assertIsNone(closed.stream.source)
        self.assertIsNone(w.active_tab.reader);self.assertEqual(w.active_tab.state.resource,self.old.id)

    def test_long_source_version_notes_stay_scrollable_with_actions_visible_in_small_window(self):
        from gi.repository import Gtk
        d=self.dialog;notes=('Exact source revision note.\n'*60).strip()
        d.modules.reports[self.old.id]=dict(state='available',available=replace(self.new,release_notes=notes),error='')
        d.language_choice='';d.update_languages();spin(lambda:not d._building_rows)
        d.open_details(None,next(i for i,r in enumerate(d.filtered_resources) if r.id==self.old.id))
        d.set_default_size(360,620);spin()
        self.assertLessEqual(d.get_width(),360);self.assertLessEqual(d.get_height(),620)
        self.assertIn(notes,d.metadata.get_text())
        self.assertFalse(d.technical.get_expanded())
        d.technical.set_expanded(True);spin()
        scroll=d.metadata.get_ancestor(Gtk.ScrolledWindow);adjustment=scroll.get_vadjustment()
        self.assertGreater(adjustment.get_upper(),adjustment.get_page_size())
        self.assertTrue(d.modules.update_button.get_mapped())
        adjustment.set_value(adjustment.get_upper()-adjustment.get_page_size());spin()
        self.assertTrue(d.modules.remove_button.get_mapped())
        # The final action is reachable below long, verbatim source notes.
        ok,bounds=d.modules.remove_button.compute_bounds(scroll)
        self.assertTrue(ok);self.assertGreaterEqual(bounds.get_y(),0)
        self.assertLessEqual(bounds.get_y()+bounds.get_height(),scroll.get_height())
        d.technical.set_expanded(False);spin()
        self.assertIsNone(d.metadata.get_ancestor(Gtk.ScrolledWindow))

    def test_library_controls_update_then_restore_the_previous_verified_package(self):
        d=self.dialog;tab=self.w.active_tab
        d.modules.reports[self.old.id]=dict(state='available',available=self.new,error='')
        d.language_choice='';d.update_languages();spin(lambda:not d._building_rows)
        index=next(i for i,r in enumerate(d.filtered_resources) if r.id==self.old.id)
        d.open_details(None,index);spin();self.assertTrue(d.modules.update_button.get_visible())
        with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(self.new_zip)):
            d.modules.update_button.emit('clicked');spin(lambda:not d.busy,timeout=15)
        self.assertEqual(d._phase,'complete',d.status.get_text())
        self.assertEqual(self.library.resource(self.old.id).version,'1.1')
        self.assertTrue(d.modules.rollback_button.get_visible())
        d.modules.run('rollback');spin(lambda:not d.busy,timeout=15)
        self.assertEqual(d._phase,'complete',d.status.get_text())
        self.assertEqual(self.library.resource(self.old.id).version,'1.0')
        self.assertIn('ORIGINAL MODULE WORDING',tab.text.get_buffer().props.text)

    def test_removal_is_independent_of_the_verified_update_provider_list(self):
        d=self.dialog
        for provider in ('youversion','step','andbible'):
            with self.subTest(provider=provider):
                resource=replace(self.old,provider_id=provider,acquisition='')
                d._installed_metadata[resource.id]=resource
                d.modules.reports[resource.id]=dict(state='provider-unavailable',available=None,error='')
                d.modules.refresh(resource)
                self.assertFalse(d.modules.update_button.get_visible())
                self.assertTrue(d.modules.remove_button.get_visible())
                self.assertTrue(d.modules.remove_button.get_sensitive())
                d._installed_metadata[resource.id]=replace(resource,locked=True)
                d.modules.refresh(resource)
                self.assertFalse(d.modules.remove_button.get_visible())

    def test_active_removal_keeps_passage_and_annotations_and_does_not_replace_on_restart(self):
        from bible.ui import Window
        d=self.dialog;w=self.w;tab=w.active_tab
        before=[asdict(n) for n in w.notes_store.all()];history=list(tab.state.history)
        d.language_choice='';d.update_languages();spin(lambda:not d._building_rows)
        index=next(i for i,r in enumerate(d.filtered_resources) if r.id==self.old.id)
        d.open_details(None,index);spin()
        d.modules.run('remove');spin(lambda:not d.busy,timeout=15)
        self.assertEqual(d._phase,'complete',d.status.get_text())
        self.assertEqual((tab.state.resource,tab.state.reference),(self.old.id,'Gen.1.1'))
        self.assertIsNone(tab.reader);self.assertEqual(tab.text.get_buffer().get_char_count(),0)
        # Without a primary source there is no safe cross-edition reference
        # context. Preserve the chosen comparison identity, with no stale text.
        self.assertEqual(tab.state.comparison,'Test')
        self.assertEqual(tab.comparison_text.get_buffer().get_char_count(),0)
        self.assertEqual(getattr(tab,'_comparison_tick',0),0)
        self.assertEqual(tab.state.history,history);self.assertEqual([asdict(n) for n in w.notes_store.all()],before)
        from tests.test_commentary import commentary_fixture
        commentary_fixture(self.root,name='AddedCommentary')
        w.resource_installed('AddedCommentary');spin()
        self.assertIsNone(tab.reader);self.assertEqual(tab.state.resource,self.old.id)
        app=w.get_application();d.close();w.close();spin()
        reopened=Window(app,self.library);reopened.present();spin()
        try:
            self.assertEqual((reopened.active_tab.state.resource,reopened.active_tab.state.reference),(self.old.id,'Gen.1.1'))
            self.assertIsNone(reopened.active_tab.reader)
            reopened.application_settings.set('automatic_catalogue_refresh',False)
            again=reopened.open_library();spin(lambda:not again.preparing)
            self.assertIn(self.old.id,[r.id for r in again.resources])
            self.assertIn(self.old.id,again._removed_ids);again.close()
            self.assertEqual([asdict(n) for n in reopened.notes_store.all()],before)
            self.assertEqual(reopened.highlights.entries[('KJV','Gen.1.1')]['color'],'yellow')
        finally:reopened.close()

    def test_update_all_runs_verified_resources_serially_and_stops_on_failure(self):
        from bible.providers import CROSSWIRE
        from gi.repository import Adw,Gtk
        d=self.dialog
        direct=replace(self.new,provider_id=CROSSWIRE.id,source=CROSSWIRE.name,source_url=CROSSWIRE.url,acquisition='')
        for damaged in (True,False):
            d.modules.reports={r.id:dict(state='available',available=r,error='') for r in (self.new,direct)}
            with patch('bible.library.download',side_effect=lambda url,out,progress:out.write(self.new_zip+(b'bad' if damaged else b''))) as fetch:
                d.modules.update_all();spin()
                prompt=next(w for w in Gtk.Window.get_toplevels() if isinstance(w,Adw.MessageDialog))
                prompt.response('update');prompt.destroy()
                spin(lambda:not d.busy and not d.modules.queue and not d.modules._next,timeout=20)
            if damaged:
                self.assertEqual(d._phase,'error');self.assertEqual(fetch.call_count,1)
                self.assertEqual(self.library.resource(self.old.id).version,'1.0')
                self.assertEqual(self.library.resource('Test').version,'1.0')
            else:
                self.assertEqual(d._phase,'complete',d.status.get_text());self.assertEqual(fetch.call_count,2)
                self.assertEqual(self.library.resource(self.old.id).version,'1.1')
                self.assertEqual(self.library.resource('Test').version,'1.1')
