"""Unified identities, actual mapping, autosave and failure/deletion boundaries."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bible.annotation_collection import records,filter_records
from bible.notes import NoteStore
from bible.i18n import tr


class CollectionTests(unittest.TestCase):
    def test_distinct_records_counts_search_and_stable_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            store=NoteStore(Path(directory)/'notes.sqlite3')
            try:
                notes=[store.save(body,['Espérance'],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='Missing',origin_language='fr') for body in ('**Texte** unique à rechercher','Seconde note distincte')]
                mark=dict(system='KJV',reference='Gen.1.1',color='yellow',resource='Missing')
                items=records(notes,[mark]);self.assertEqual(len(items),3);self.assertEqual(len({a.key for a in items}),3)
                self.assertEqual([a.note.id for a in filter_records(items,'texte rechercher espérance')],[notes[0].id])
                self.assertEqual(len(filter_records(items,category='notes')),2)
                self.assertEqual(len(filter_records(items,category='highlights')),1)
                self.assertEqual(len(filter_records(items,labels=['espérance'])),2)
                self.assertEqual(len(filter_records(items,color='yellow')),1)
                self.assertEqual(len(filter_records(items,'Genesis',reference_names={'Gen':'Genesis'})),3)
                self.assertEqual(filter_records(items,book='John'),[])
                self.assertEqual(items[-1].modified,'')
                self.assertEqual([a.key for a in filter_records(items,order='bible')],[a.key for a in filter_records(list(reversed(items)),order='bible')])
                self.assertEqual(mark['color'],'yellow');self.assertEqual(len(store.all()),2)
            finally:store.close()


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires actual GTK')
class AnnotationWorkspaceTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        for name,system,entries in [('Luther','Luther',[('Gen.32.1','LUTHER SOURCE TEXT'),('Gen.32.2','LUTHER SECOND TEXT')]),('KingJames','KJV',[('Gen.31.55','KJV ACTUAL MAPPED TEXT'),('Gen.32.1','KJV NEXT CHAPTER TEXT')])]:
            installed_fixture(self.root,name,versification=system,entries=entries)
        self.app=Application.get_default() or Application();self.app.register()
        self.window=Window(self.app,Library(self.root/'translations'));self.window.present();spin()
        self.window.navigate_selection('Luther','Gen.32.1')
        self.first=self.save('First **editable** note; see Gen 32:2.',['First'])
        self.second=self.save('Second distinct note with espérance.',['Second'])
        self.window.highlights.set('Luther',['Gen.32.1'],'green','Luther')
        self.space=self.window.open_notes();spin()

    def save(self,body,labels=()):
        return self.window.notes_store.save(body,labels,versification='Luther',start='Gen.32.1',end='Gen.32.1',origin_translation='Luther',origin_language='en')

    def tearDown(self):
        from tests.test_ui import close_test_dialogs
        if self.window.note_editor:self.window.note_editor._discard=True;self.window.note_editor.cancel_autosave()
        close_test_dialogs();self.window.close()

    def test_coalesced_autosave_flush_on_record_switch_and_restart(self):
        from tests.test_ui import spin
        w=self.window;s=self.space;s.open_note(self.first);editor=s.editor
        with patch.object(w.notes_store,'save',wraps=w.notes_store.save) as write:
            for value in ('A','A newer draft','Final Unicode draft é — **Markdown**'):editor.body.get_buffer().set_text(value)
            spin(lambda:w.notes_store.get(self.first.id).body=='Final Unicode draft é — **Markdown**')
            self.assertEqual(write.call_count,1);self.assertFalse(editor.dirty)
        editor.body.get_buffer().set_text('Flushed before another record')
        s.open_note(self.second);self.assertEqual(w.notes_store.get(self.first.id).body,'Flushed before another record')
        self.assertEqual(s.editor.note.id,self.second.id);self.assertTrue(editor.closed)
        editor.autosave_pending();self.assertEqual(w.notes_store.get(self.second.id).body,self.second.body)
        s.editor.body.get_buffer().set_text('Flushed at normal shutdown')
        w.close()
        from bible.ui import Window
        self.window=w=Window(self.app,w.library);w.present();spin()
        self.assertEqual(w.notes_store.get(self.second.id).body,'Flushed at normal shutdown')
        self.assertEqual(w.notes_store.get(self.first.id).body,'Flushed before another record')

    def test_write_failure_and_optimistic_conflict_preserve_draft(self):
        from tests.test_ui import spin
        w=self.window;s=self.space;s.open_note(self.first);editor=s.editor
        with patch.object(w.notes_store,'save',side_effect=OSError('TEST WRITE FAILURE')):
            editor.body.get_buffer().set_text('Unsaved original target draft')
            spin(lambda:'TEST WRITE FAILURE' in editor.status.get_text())
            self.assertTrue(editor.dirty);self.assertEqual(w.notes_store.get(self.first.id).body,self.first.body)
            s.leave();self.assertEqual(w.main_pages.get_visible_child_name(),'notes')
            editor._confirmation.response('cancel');spin();self.assertFalse(editor.closed)
        s.open_note(self.second);self.assertEqual(w.notes_store.get(self.first.id).body,'Unsaved original target draft')
        editor=s.editor
        other=NoteStore(self.root/'notes.sqlite3')
        try:other.save('Changed in another window',[],existing=other.get(self.second.id))
        finally:other.close()
        editor.body.get_buffer().set_text('Keep this conflicting draft')
        spin(lambda:tr('This note changed elsewhere. Your draft has been preserved.') in editor.status.get_text())
        self.assertEqual(w.notes_store.get(self.second.id).body,'Changed in another window')
        self.assertEqual(editor.body.get_buffer().props.text,'Keep this conflicting draft');self.assertTrue(editor.dirty)

    def test_pending_delete_cannot_autosave_recreate_note_and_keeps_highlight(self):
        from tests.test_ui import spin
        w=self.window;s=self.space;s.open_note(self.first);editor=s.editor
        editor.body.get_buffer().set_text('Pending write must not resurrect deletion')
        editor.ask_delete();editor._confirmation.response('confirm');spin()
        editor.autosave_pending()
        self.assertFalse(editor.save(close=False));self.assertIsNone(w.notes_store.get(self.first.id))
        self.assertEqual(len(w.notes_store.all()),1);self.assertIn(('Luther','Gen.32.1'),w.highlights.entries)
        self.assertEqual(len(s.all_records),2)

    def test_real_numbering_difference_explicit_new_tab_and_notes_context(self):
        from tests.test_ui import spin
        w=self.window;s=self.space;tab=w.active_tab
        tab.state.comparison='KingJames';w.sync_comparison();s.open_note(self.first)
        before=(tab.state.resource,tab.state.reference,list(tab.state.history),tab.state.comparison)
        s.search.set_text('editable');s.refresh();selected=s.selected_key
        s.versions.set_selected(s.version_names.index('KingJames'));spin()
        self.assertIn('KJV ACTUAL MAPPED TEXT',s.excerpt.get_text());self.assertNotIn('LUTHER SOURCE TEXT',s.excerpt.get_text())
        self.assertIn('31:55',s.excerpt.get_text());self.assertEqual(s.editor.context['start'],'Gen.32.1')
        self.assertEqual((tab.state.resource,tab.state.reference,list(tab.state.history),tab.state.comparison),before)
        count=w.view.get_n_pages();s.open_passage();spin()
        self.assertEqual(w.view.get_n_pages(),count+1);self.assertEqual(w.active_tab.state.reference,'Gen.31.55')
        self.assertEqual(w.active_tab.state.resource,'KingJames');self.assertEqual(tab.state.reference,'Gen.32.1');self.assertEqual(tab.state.comparison,'KingJames')
        w.open_notes();spin();self.assertEqual(s.search.get_text(),'editable');self.assertEqual(s.selected_key,selected)
        self.assertEqual(s.editor.note.id,self.first.id)

    def test_highlight_recolor_remove_and_full_text_filters_do_not_merge_notes(self):
        from tests.test_ui import spin
        w=self.window;s=self.space
        self.assertEqual(len(s.rows),3);s.set_category('notes');self.assertEqual(len(s.rows),2)
        s.search.set_text('espérance');s.refresh();self.assertEqual([a.note.id for a in s.rows],[self.second.id])
        s.search.set_text('');s.set_category('highlights');a=s.rows[0];s.open_annotation(a)
        s.change_highlight(a,'blue');spin();self.assertEqual(w.highlights.entries[('Luther','Gen.32.1')]['color'],'blue')
        self.assertEqual(len(w.notes_store.all()),2)
        current=s.selected_annotation;s.change_highlight(a,None)
        self.assertIn(('Luther','Gen.32.1'),w.highlights.entries);self.assertEqual(s.status.get_text(),tr('This highlight changed elsewhere. Reopen it before editing.'))
        s.change_highlight(current,None);self.assertEqual(len(w.notes_store.all()),2);self.assertFalse(w.highlights.entries)

    def test_missing_resources_keep_annotations_editable_and_backups_compatible(self):
        import shutil
        from tests.test_ui import spin
        w=self.window;s=self.space;s.open_note(self.first);s.editor.body.get_buffer().set_text('Persist without a module');s.leave()
        backup=self.root/'legacy-notes.json';self.assertTrue(s.backup_to(backup))
        w.highlights.backup(self.root/'legacy-highlights.json');w.close();shutil.rmtree(self.root/'translations')
        self.assertFalse(w.primary_version.finish())
        from bible.ui import Window,Library
        self.window=w=Window(self.app,Library(w.library.root));w.present();s=w.open_notes();spin();s.open_note(w.notes_store.get(self.first.id))
        self.assertFalse(s.open_button.get_sensitive());self.assertIn(tr('Install a Bible to display this passage. Your annotation is kept.'),s.excerpt.get_text())
        s.editor.body.get_buffer().set_text('Edited with no Bible installed');s.leave()
        self.assertEqual(w.notes_store.get(self.first.id).body,'Edited with no Bible installed')
        added,skipped,conflicts=w.notes_store.restore(backup)
        self.assertEqual((added,skipped,conflicts),(1,1,1));self.assertEqual(len(w.highlights.entries),1)
        w.highlights.restore(self.root/'legacy-highlights.json');self.assertEqual(len(w.highlights.entries),1)

    def test_passage_footer_reveals_actual_record_in_unified_workspace(self):
        from tests.test_ui import spin
        w=self.window;s=self.space;s.search.set_text('unmatched filter');s.set_category('highlights');s.leave()
        w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');w.study.notes.refresh(force=True);spin()
        before=(w.active_tab.state.resource,w.active_tab.state.reference,list(w.active_tab.state.history))
        w.study.notes.footer.emit('clicked');spin()
        self.assertEqual(w.main_pages.get_visible_child_name(),'notes')
        self.assertEqual(s.search.get_text(),'');self.assertEqual(s.category,'all')
        self.assertEqual(s.editor.note.id,self.first.id)
        self.assertEqual((w.active_tab.state.resource,w.active_tab.state.reference,w.active_tab.state.history),before)

    def test_unavailable_imported_reference_keeps_note_without_guessing_passage(self):
        from tests.test_ui import spin
        w=self.window;s=self.space
        note=w.notes_store.save('Retain an imported annotation with an unavailable target.',[],versification='KJV',start='Gen.999.1',end='Gen.999.1',origin_translation='Missing',origin_language='en')
        before=(w.active_tab.state.resource,w.active_tab.state.reference,list(w.active_tab.state.history))
        s.refresh();s.open_note(note);spin()
        self.assertFalse(s.open_button.get_sensitive())
        self.assertEqual(w.notes_store.get(note.id),note)
        self.assertEqual((w.active_tab.state.resource,w.active_tab.state.reference,w.active_tab.state.history),before)
        self.assertIn(tr('Passage unavailable or no verified alignment.'),s.excerpt.get_text())
        self.assertEqual(s.editor.context['start'],note.start)

    def test_workspace_selector_routes_and_unfinished_label_guard(self):
        from tests.test_ui import spin
        w=self.window;s=self.space;s.open_note(self.first);editor=s.editor
        editor.labels.entry.set_text('New label');editor.body.get_buffer().set_text('Body and pending label')
        spin(lambda:editor.status.get_text()==tr('Press Enter to add the label before saving.'));self.assertTrue(editor.dirty)
        self.assertEqual(w.notes_store.get(self.first.id).body,self.first.body)
        editor.labels.entry.emit('activate');spin(lambda:w.notes_store.get(self.first.id).body=='Body and pending label')
        self.assertIn('New label',w.notes_store.get(self.first.id).labels)
        s.space_selector.set_selected(0);spin();self.assertEqual(w.main_pages.get_visible_child_name(),'reading')
        self.assertEqual(w.space_selector.get_selected(),0);self.assertFalse(hasattr(w,'my_notes_button'))
        w.space_selector.set_selected(1);spin();self.assertEqual(w.main_pages.get_visible_child_name(),'notes')
        self.assertEqual(s.space_selector.get_selected(),1)
