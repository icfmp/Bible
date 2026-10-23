"""Shared note previews preserve note identity, drafts and explicit navigation."""
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture,spin,close_test_dialogs


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class NoteCitationTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        self.directory=self.enterContext(tempfile.TemporaryDirectory());self.root=Path(self.directory)
        for name,system,psalm in [('French','Segond','Ps.3.2'),('English','KJV','Ps.3.1')]:
            installed_fixture(self.directory,name,versification=system,entries=[
                ('John.1.5','SOURCE '+name),('John.3.16','EXACT JOHN '+name),(psalm,'EXACT PSALM '+name)])
        self.app=Application.get_default() or Application();self.app.register()
        self.window=Window(self.app,Library(self.root/'translations'));self.window.set_default_size(1200,900);self.window.present()
        self.window.active_tab.navigate('English','John.1.5')
        self.note=self.window.notes_store.save('Voir **Psaumes 3:2** et John 3:16. `John 1:5`',[],
            versification='Segond',start='John.1.5',end='John.1.5',origin_translation='French',origin_language='fr')

    def tearDown(self):
        close_test_dialogs()
        if self.window.note_editor:self.window.note_editor._discard=True;self.window.note_editor.close()
        self.window.close()

    def editor(self,embedded=True):
        if embedded:
            notes=self.window.open_notes();notes.open_note(self.note);editor=notes.editor
        else:editor=self.window.edit_note(note=self.note)
        editor.stack.set_visible_child_name('preview');spin(duration=.2)
        return editor

    def test_passage_and_global_previews_share_links_and_real_numbering_without_storage_changes(self):
        from bible.note_preview import NotePreview
        from bible.annotation_card import AnnotationPreview
        w=self.window;w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');w.study.notes.refresh();spin()
        def walk(widget):
            if isinstance(widget,(NotePreview,AnnotationPreview)):yield widget
            child=widget.get_first_child()
            while child:yield from walk(child);child=child.get_next_sibling()
        preview=next(walk(w.study.notes.list));self.assertEqual(len(preview.citations),2)
        self.assertIn('<b>Psaumes 3:2</b>',preview.get_label(),
                      'Generated links must preserve Markdown bold weight')
        before=(w.active_tab.state.reference,list(w.active_tab.state.history),w.view.get_n_pages())
        preview.activate(0);spin()
        self.assertEqual(w.reference_preview.body.get_buffer().props.text,'EXACT PSALM English')
        self.assertEqual(w.reference_preview.target,('English','Ps.3.1'))
        self.assertEqual((w.active_tab.state.reference,w.active_tab.state.history,w.view.get_n_pages()),before)
        w.reference_preview.dismiss();editor=self.editor()
        cursor=editor.body.get_buffer().get_iter_at_mark(editor.body.get_buffer().get_insert()).get_offset()
        editor.preview.activate(0);spin()
        self.assertEqual(w.reference_preview.target,('English','Ps.3.1'))
        w.reference_preview.dismiss()
        self.assertEqual(editor.body.get_buffer().get_iter_at_mark(editor.body.get_buffer().get_insert()).get_offset(),cursor)
        self.assertEqual(w.notes_store.get(self.note.id),self.note)

    def test_dirty_editor_cancel_then_save_guards_explicit_new_tab_without_retargeting_note(self):
        from bible.notes_window import buffer_text
        w=self.window;editor=self.editor();editor.body.get_buffer().insert_at_cursor(' unsaved')
        before=(w.active_tab.state.reference,w.view.get_n_pages())
        editor.preview.activate(0);spin();w.reference_preview.open_new.emit('clicked');spin()
        self.assertTrue(editor._confirmation.get_visible())
        self.assertEqual((w.active_tab.state.reference,w.view.get_n_pages()),before)
        editor._confirmation.response('cancel');editor._confirmation.destroy();spin()
        self.assertFalse(editor.closed);self.assertIn('unsaved',buffer_text(editor.body))
        editor.preview.activate(0);spin();w.reference_preview.open_new.emit('clicked');spin()
        editor._confirmation.response('save');editor._confirmation.destroy();spin()
        self.assertEqual(w.view.get_n_pages(),before[1]+1)
        self.assertEqual(w.active_tab.state.reference,'Ps.3.1');self.assertEqual(w.active_tab.state.resource,'English')
        saved=w.notes_store.get(self.note.id)
        self.assertEqual((saved.versification,saved.start,saved.origin_translation),('Segond','John.1.5','French'))
        self.assertIn('unsaved',saved.body)

    def test_standalone_editor_closes_on_explicit_navigation_and_unmapping_dismisses_preview(self):
        w=self.window;editor=self.editor(embedded=False)
        editor.preview.activate(1);spin();self.assertIsNotNone(w.reference_preview.popover)
        editor.stack.set_visible_child_name('edit');spin();self.assertIsNone(w.reference_preview.popover)
        editor.stack.set_visible_child_name('preview');spin();editor.preview.activate(1);spin()
        w.reference_preview.open_here.emit('clicked');spin()
        self.assertTrue(editor.closed);self.assertEqual(w.active_tab.state.reference,'John.3.16')
        self.assertEqual(w.notes_store.get(self.note.id),self.note)

    def test_missing_translation_and_keyboard_traversal_leave_content_and_context_unchanged(self):
        from bible.ui import Gtk
        w=self.window;editor=self.editor();preview=editor.preview
        self.assertTrue(preview.child_focus(Gtk.DirectionType.TAB_FORWARD))
        self.assertEqual(preview._citation_focus,0)
        self.assertTrue(preview.child_focus(Gtk.DirectionType.TAB_FORWARD));self.assertEqual(preview._citation_focus,1)
        self.assertFalse(preview.child_focus(Gtk.DirectionType.TAB_FORWARD))
        w.active_tab.state.resource=None;w.active_tab.load_resource();w.tab_changed(w.active_tab);spin()
        preview.activate(0);spin()
        self.assertFalse(w.reference_preview.open_here.get_sensitive());self.assertFalse(w.reference_preview.open_new.get_sensitive())
        self.assertEqual(w.reference_preview.body.get_buffer().props.text,'')
        self.assertEqual(w.notes_store.get(self.note.id),self.note)
