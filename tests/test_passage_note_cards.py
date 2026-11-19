"""Rendering is read-only; the shared editor retains record identity and drafts."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin,close_test_dialogs


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class PassageNoteCardTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        directory=self.enterContext(tempfile.TemporaryDirectory());self.root=Path(directory)
        installed_fixture(directory,entries=[('Acts.1.21','ACTUAL SWORD FIXTURE 21'),('Acts.1.22','ACTUAL SWORD FIXTURE 22'),('Acts.1.23','NEXT FIXTURE'),('John.3.16','CITATION FIXTURE')])
        app=Application.get_default() or Application();app.register()
        self.w=Window(app,Library(self.root/'translations'));self.w.set_default_size(1200,900);self.w.present()
        spin()
        self.w.active_tab.navigate('Test','Acts.1.22');self.w.study_button.set_active(True);self.w.study.tools.set_visible_child_name('notes')
        self.context=dict(versification='KJV',start='Acts.1.21',end='Acts.1.22',origin_translation='Test',origin_language='en')
        self.note=self.w.notes_store.save('**Legacy note** John 3:16.\n\n'+('Long personal note.\n\n'*100),['Keep'],**self.context)
        self.other=self.w.notes_store.save('Independent same-range note.',[],**self.context)
        self.w.highlights.set('KJV',['Acts.1.22'],'green','Test');self.w.study.notes.refresh(force=True);spin()

    def tearDown(self):
        close_test_dialogs()
        if self.w.note_editor and not self.w.note_editor.closed:self.w.note_editor._discard=True;self.w.note_editor.close()
        self.w.close()

    def test_unified_independent_cards_bounded_preview_and_no_render_writes(self):
        panel=self.w.study.notes;before=self.w.notes_store.all();marks=dict(self.w.highlights.entries)
        self.assertEqual(len(panel.cards),3)
        self.assertEqual({c.note_id for c in panel.cards if hasattr(c,'note_id')},{self.note.id,self.other.id})
        self.assertIsNone(self.w.study.references.teaser.get_parent())
        card=next(c for c in panel.cards if getattr(c,'note_id',None)==self.note.id)
        self.assertEqual(card.preview.get_lines(),3)
        self.assertNotIn('\n',card.preview.get_text())
        self.assertLess(card.preview.get_height(),100)
        self.assertFalse(hasattr(card,'excerpt'))
        self.assertFalse(hasattr(card,'actions'))
        self.assertIn('21',card._reference_labels[0].get_text())
        self.assertIn('<b>Legacy note</b>',card.preview.get_label())
        from tools.check_alpha_ui import X11Input
        from bible.ui import Pango
        native=X11Input();self.addCleanup(native.close);native.activate(self.w)
        citation=card.preview.citations[0]
        offset=len(card.preview.get_text()[:citation.begin].encode())
        rectangle=card.preview.get_layout().index_to_pos(offset)
        left,top=card.preview.get_layout_offsets()
        with patch.object(panel,'open_note',wraps=panel.open_note) as opened:
            if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')=='1':
                native.click_at(card.preview,left+(rectangle.x+rectangle.width/2)/Pango.SCALE,
                                top+(rectangle.y+rectangle.height/2)/Pango.SCALE)
            else:card.preview.emit('activate-link','bible-preview:0')
            self.assertEqual(opened.call_count,0)
        self.assertIsNone(panel.editor)
        self.assertEqual(self.w.reference_preview.target,('Test','John.3.16'))
        self.w.reference_preview.dismiss();spin()
        card.primary_action.grab_focus()
        if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')=='1':native.key('Return')
        else:card.primary_action.emit('clicked')
        spin()
        self.assertEqual(panel.editor.note.id,self.note.id)
        self.assertEqual(panel.editor.body.source(),self.note.body)
        self.assertFalse(panel.editor.embedded);panel.editor.close();spin()
        mark=next(c for c in panel.cards if hasattr(c,'highlight_key'))
        with patch.object(panel,'navigate_annotation',wraps=panel.navigate_annotation) as navigate:
            if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')=='1':native.click(mark.actions)
            else:mark.actions.popup()
            self.assertTrue(mark.actions.get_popover().get_visible())
            self.assertEqual(navigate.call_count,0)
            mark.actions.popdown()
        panel.refresh(force=True);spin()
        self.assertEqual(self.w.notes_store.all(),before);self.assertEqual(self.w.highlights.entries,marks)

    def test_shared_popup_keeps_document_context_and_failed_close_retains_the_draft(self):
        from bible.notes_window import buffer_text
        panel=self.w.study.notes;editor=panel.open_note(self.note);original_buffer=editor.body.get_buffer()
        spin();self.assertFalse(editor.embedded);self.assertTrue(editor.autosave)
        self.assertFalse(hasattr(panel,'editor_panel'));self.assertFalse(editor.save_button.get_visible())
        self.assertIsNone(editor.actions_menu)
        editor.body.get_buffer().set_text('Unsaved **draft** John 3:16.')
        editor.labels.set_values(['Keep','Draft'])
        self.w.active_tab.navigate('Test','Acts.1.23');self.w.study.tools.set_visible_child_name('references')
        self.w.new_tab();spin()
        self.w.study_button.set_active(False);spin()
        self.assertEqual(editor.context['start'],'Acts.1.21');self.assertIn('Unsaved',buffer_text(editor.body))
        self.w.study_button.set_active(True);self.w.study.tools.set_visible_child_name('notes')
        self.assertIs(editor.body.get_buffer(),original_buffer);self.assertFalse(editor.embedded)
        self.assertIs(editor.dialog_parent,editor)
        with patch.object(self.w.notes_store,'save',side_effect=OSError('Test write failure')):
            self.assertFalse(editor.save());self.assertIn('Unsaved',buffer_text(editor.body));self.assertFalse(editor.closed)
            editor.close();spin();self.assertTrue(editor._confirmation.get_visible())
            editor._confirmation.response('cancel');editor._confirmation.destroy();spin();self.assertFalse(editor.closed)
        editor.close();spin();self.assertTrue(editor.closed)
        saved=self.w.notes_store.get(self.note.id)
        self.assertEqual(saved.body,'Unsaved **draft** John 3:16.')
        self.assertEqual((saved.start,saved.end),('Acts.1.21','Acts.1.22'))
        self.assertEqual(saved.labels,('Draft','Keep'))
        self.assertEqual(self.w.highlights.entries[('KJV','Acts.1.22')]['color'],'green')

    def test_switch_note_prompt_cancel_and_discard_do_not_lose_current_draft(self):
        panel=self.w.study.notes;first=panel.open_note(self.note)
        first.body.get_buffer().set_text('Keep me until a deliberate decision')
        with patch.object(self.w.notes_store,'save',side_effect=OSError('Test write failure')):
            panel.open_note(self.other);spin();dialog=first._confirmation
            dialog.response('cancel');dialog.destroy();spin()
            self.assertIs(panel.editor,first);self.assertFalse(first.closed)
            panel.open_note(self.other);spin();dialog=first._confirmation
            dialog.response('discard');dialog.destroy();spin()
        self.assertTrue(first.closed);self.assertEqual(panel.editor.note.id,self.other.id)
        self.assertEqual(self.w.notes_store.get(self.note.id).body,self.note.body)

    def test_unavailable_original_resource_keeps_note_visible_and_editable(self):
        tab=self.w.active_tab;tab.reader=None
        panel=self.w.study.notes;panel.refresh(force=True);spin()
        self.assertEqual({n.id for n in panel.rows},{self.note.id,self.other.id})
        card=next(c for c in panel.cards if getattr(c,'note_id',None)==self.note.id)
        self.assertFalse(hasattr(card,'excerpt'))
        self.assertIn('Legacy note',card.preview.get_text())
        editor=panel.open_note(self.note)
        self.assertEqual(editor.note.id,self.note.id)
        self.assertEqual(editor.context['origin_translation'],'Test')

    def test_empty_draft_save_failure_and_empty_preview_do_not_change_storage(self):
        from dataclasses import replace
        from bible.annotation_card import AnnotationPreview
        panel=self.w.study.notes;before=self.w.notes_store.all()
        editor=panel.open_note(context=dict(self.context));spin()
        self.assertFalse(editor.save());self.assertFalse(editor.closed)
        self.assertFalse(editor.embedded);self.assertTrue(editor.status.get_text())
        preview=AnnotationPreview(self.w,replace(self.note,body=''),lambda:None)
        self.assertTrue(preview.get_text())
        self.assertEqual(self.w.notes_store.all(),before)

    def test_popup_coalesces_text_labels_links_and_flushes_immediate_close(self):
        from bible.notes import NoteStore
        from bible.notes_window import buffer_text
        from bible.ui import Gtk
        panel=self.w.study.notes;editor=panel.open_note(self.note);spin()
        self.assertEqual(editor.header.get_decoration_layout(),':close')
        self.assertEqual(editor.labels.add_menu.get_direction(),Gtk.ArrowType.NONE)
        self.assertEqual(editor.links.add_button.get_direction(),Gtk.ArrowType.NONE)
        self.assertEqual(editor.labels.add_menu.get_width(),editor.links.add_button.get_width())
        with patch.object(self.w.notes_store,'save',wraps=self.w.notes_store.save) as write:
            for body in ('A','A newer draft','**Final** Unicode é'):editor.body.get_buffer().set_text(body)
            editor.labels.entry.set_text('Added');editor.labels.add()
            editor.links.entry.set_text('John 3:16');self.assertTrue(editor.links.add())
            editor.close();spin()
            self.assertEqual(write.call_count,1);self.assertTrue(editor.closed)
        witness=NoteStore(self.root/'notes.sqlite3')
        try:
            saved=witness.get(self.note.id)
            self.assertEqual(saved.body,'**Final** Unicode é')
            self.assertIn('Added',saved.labels);self.assertEqual(saved.links[0].start,'John.3.16')
            self.assertEqual(saved.start,self.note.start)
        finally:witness.close()
        reopened=panel.open_note(saved);spin()
        self.assertEqual(buffer_text(reopened.body),saved.body)
        self.assertEqual(reopened.note.id,self.note.id)

    def test_confirmed_delete_cancels_pending_autosave_without_resurrection(self):
        editor=self.w.study.notes.open_note(self.note);spin()
        marks=dict(self.w.highlights.entries)
        editor.body.get_buffer().set_text('Pending edit must not resurrect a deleted note')
        editor.ask_delete();spin();editor._confirmation.response('confirm');spin()
        self.assertTrue(editor.closed);self.assertEqual(editor._autosave_id,0)
        editor.autosave_pending();spin(duration=.7)
        self.assertIsNone(self.w.notes_store.get(self.note.id))
        self.assertEqual(self.w.notes_store.get(self.other.id),self.other)
        self.assertEqual(self.w.highlights.entries,marks)
