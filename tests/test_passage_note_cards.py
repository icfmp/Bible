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
        self.assertIn('ACTUAL SWORD FIXTURE',card.excerpt.get_text())
        self.assertIn('<b>Legacy note</b>',card.preview.get_label())
        card.preview.activate(0);spin()
        self.assertIsNone(panel.editor)
        self.assertEqual(self.w.reference_preview.target,('Test','John.3.16'))
        self.w.reference_preview.dismiss();panel.refresh(force=True);spin()
        self.assertEqual(self.w.notes_store.all(),before);self.assertEqual(self.w.highlights.entries,marks)

    def test_inline_expand_same_document_failure_cancel_save_and_context(self):
        from bible.notes_window import buffer_text
        panel=self.w.study.notes;editor=panel.open_note(self.note);original_buffer=editor.body.get_buffer()
        spin();self.assertTrue(editor.embedded);self.assertIs(editor.embedded_content.get_parent(),panel.editor_panel)
        editor.body.get_buffer().set_text('Unsaved **draft** John 3:16.')
        editor.labels.set_values(['Keep','Draft'])
        self.w.active_tab.navigate('Test','Acts.1.23');self.w.study.tools.set_visible_child_name('references')
        self.w.new_tab();spin()
        self.w.study_button.set_active(False);spin()
        self.assertEqual(editor.context['start'],'Acts.1.21');self.assertIn('Unsaved',buffer_text(editor.body))
        self.w.study_button.set_active(True);self.w.study.tools.set_visible_child_name('notes')
        panel.expand_editor();spin(lambda:not editor.embedded)
        self.assertIs(editor.body.get_buffer(),original_buffer);self.assertFalse(editor.embedded)
        self.assertIs(editor.dialog_parent,editor)
        with patch.object(self.w.notes_store,'save',side_effect=OSError('Test write failure')):
            self.assertFalse(editor.save());self.assertIn('Unsaved',buffer_text(editor.body));self.assertFalse(editor.closed)
        editor.close();spin();self.assertTrue(editor._confirmation.get_visible())
        editor._confirmation.response('cancel');editor._confirmation.destroy();spin();self.assertFalse(editor.closed)
        self.assertTrue(editor.save());spin()
        saved=self.w.notes_store.get(self.note.id)
        self.assertEqual(saved.body,'Unsaved **draft** John 3:16.')
        self.assertEqual((saved.start,saved.end),('Acts.1.21','Acts.1.22'))
        self.assertEqual(saved.labels,('Draft','Keep'))
        self.assertEqual(self.w.highlights.entries[('KJV','Acts.1.22')]['color'],'green')

    def test_switch_note_prompt_cancel_and_discard_do_not_lose_current_draft(self):
        panel=self.w.study.notes;first=panel.open_note(self.note)
        first.body.get_buffer().set_text('Keep me until a deliberate decision')
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
        self.assertNotIn('ACTUAL SWORD FIXTURE',card.excerpt.get_text())
        editor=panel.open_note(self.note)
        self.assertEqual(editor.note.id,self.note.id)
        self.assertEqual(editor.context['origin_translation'],'Test')

    def test_empty_draft_save_failure_and_empty_preview_do_not_change_storage(self):
        from dataclasses import replace
        from bible.annotation_card import AnnotationPreview
        panel=self.w.study.notes;before=self.w.notes_store.all()
        editor=panel.open_note(context=dict(self.context));spin()
        self.assertFalse(editor.save());self.assertFalse(editor.closed)
        self.assertTrue(editor.embedded);self.assertTrue(editor.status.get_text())
        preview=AnnotationPreview(self.w,replace(self.note,body=''),lambda:None)
        self.assertTrue(preview.get_text())
        self.assertEqual(self.w.notes_store.all(),before)
