"""Shared reader contracts: numbering, annotation identity and safe UI actions."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bible.book_names import canonical_input
from tests.test_ui import installed_fixture,spin,close_test_dialogs


class ReferenceInputTests(unittest.TestCase):
    def test_explicit_singular_plural_and_attached_chapter_preserve_distinct_books(self):
        for value in ('psaume100','Psaumes 100','PSALM 100','Ps100'):
            self.assertEqual(canonical_input(value),'Ps.100')
        self.assertEqual(canonical_input('Psaume 151'),'Ps151.1')
        self.assertEqual(canonical_input('Ps.151'),'Ps.151')


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK/SWORD')
class ReaderContracts(unittest.TestCase):
    def test_embedded_editor_owns_quiet_open_and_confirmed_bottom_delete(self):
        from bible.ui import Gtk
        note=self.w.notes_store.save('Keep original note',[],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='Second',origin_language='en')
        space=self.w.open_notes();space.open_note(note);spin();editor=space.editor
        self.assertIsNone(editor.actions_menu)
        self.assertIs(editor.delete_button.get_parent(),editor.embedded_content)
        self.assertIs(editor.open_button.get_parent(),editor.reference_row)
        self.assertIsInstance(editor.open_button,Gtk.Button)
        self.assertTrue(editor.open_button.has_css_class('flat'))
        self.assertTrue(editor.open_button.get_sensitive())
        self.assertIs(space.open_button.get_parent(),space.context_panel)
        editor.open_button.emit('clicked');spin()
        self.assertEqual(self.w.active_tab.state.resource,'Second')
        self.assertEqual(self.w.active_tab.state.reference,'Gen.1.1')
        self.assertEqual(self.w.notes_store.get(note.id),note)
        self.w.open_notes();space.open_note(note);spin();editor=space.editor
        editor.body.get_buffer().insert_at_cursor(' Pending update')
        editor.delete_button.emit('clicked');spin()
        self.assertTrue(editor._confirmation.get_visible())
        editor._confirmation.response('confirm');spin(duration=.7)
        self.assertTrue(editor.closed);self.assertEqual(editor._autosave_id,0)
        self.assertIsNone(self.w.notes_store.get(note.id))
        missing=self.w.notes_store.save('Keep unavailable source',[],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='MissingSource',origin_language='en')
        space.open_note(missing);spin()
        self.assertFalse(space.editor.open_button.get_sensitive())
        self.assertEqual(space.editor.note.id,missing.id)

    def setUp(self):
        from bible.ui import Application,Window,Library
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        installed_fixture(self.root,'First');installed_fixture(self.root,'Second')
        self.app=Application.get_default() or Application();self.app.register()
        self.w=Window(self.app,Library(self.root/'translations'));self.w.present();spin()
        self.w.active_tab.navigate('First','Gen.1.1');spin()

    def tearDown(self):
        close_test_dialogs()
        if not self.w.closed:self.w.close()

    def test_highlight_card_keeps_actual_origin_words_and_cache_separate_between_editions(self):
        import shutil
        installed_fixture(self.root,'Third',entries=[('Gen.1.1','THIRD SOURCE WORDING')])
        installed_fixture(self.root,'Fourth',entries=[('Gen.1.2','FOURTH SOURCE WORDING')])
        w=self.w;w.highlights.set('KJV',['Gen.1.1'],'green','Third')
        w.highlights.set('KJV',['Gen.1.2'],'blue','Fourth')
        original={key:dict(mark) for key,mark in w.highlights.entries.items()}
        panel=w.study.notes;w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes')
        panel.refresh(force=True);spin()
        cards={c.highlight_key:c for c in panel.cards if hasattr(c,'highlight_key')}
        for ref,source,words in [('Gen.1.1','Third','THIRD SOURCE WORDING'),('Gen.1.2','Fourth','FOURTH SOURCE WORDING')]:
            card=cards[('KJV',ref)]
            self.assertEqual(card._card_content.excerpt.get_text(),words)
            self.assertEqual(card._card_content.source_caption.get_text(),w.library.resource(source).description)
        self.assertEqual(w.highlights.entries,original)
        # Simulate a completed uninstall after releasing shared native readers;
        # the original card must remain truthful when explicitly inspected.
        w.library._annotation_readers.clear();panel.annotations.clear()
        shutil.rmtree(w.library.root/'Third')
        panel.highlight_card(original[('KJV','Gen.1.1')],w.active_tab.reader)
        from bible.i18n import tr
        content=panel.cards[-1]._card_content
        self.assertEqual(content.excerpt.get_text(),tr('Original translation unavailable.'))
        self.assertEqual(content.source_caption.get_text(),'Third')
        self.assertEqual(w.highlights.entries,original)

    def test_short_popup_stays_natural_across_reopens_and_unlink_is_full_width(self):
        from bible.notes import PassageLink
        note=self.w.notes_store.save('Short draft',[],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='Second',origin_language='en',links=[PassageLink('KJV','John.3.16','John.3.17')])
        for width,height in [(680,740),(360,600),(900,1000),(680,740)]:
            editor=self.w.edit_note(note=note);editor.set_default_size(width,height);editor.links.disclosure.set_active(True);spin(duration=.2)
            links=editor.links;card=links.rows.get_first_child()
            found,card_bounds=card.compute_bounds(editor);self.assertTrue(found)
            found,row_bounds=links.row.get_parent().compute_bounds(editor);self.assertTrue(found)
            self.assertAlmostEqual(card_bounds.get_x(),row_bounds.get_x(),delta=1)
            self.assertAlmostEqual(card_bounds.get_width(),row_bounds.get_width(),delta=1)
            self.assertLess(editor.writing.get_height(),230)
            self.assertGreaterEqual(editor.body_scroll.get_height(),96)
            found,link_bounds=links.compute_bounds(editor);self.assertTrue(found)
            found,delete_bounds=editor.delete_button.compute_bounds(editor);self.assertTrue(found)
            self.assertLess(delete_bounds.get_y()-(link_bounds.get_y()+link_bounds.get_height()),32)
            editor.close();spin()
        self.assertEqual(self.w.notes_store.get(note.id),note)

    def test_long_popup_uses_outer_scroll_without_clipping_editor_content(self):
        note=self.w.notes_store.save('Long personal note line.\n'*80,[],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='Second',origin_language='en')
        editor=self.w.edit_note(note=note);editor.set_default_size(360,600);spin(duration=.3)
        outer=editor.get_content().get_last_child().get_vadjustment()
        inner=editor.body_scroll.get_vadjustment()
        self.assertGreater(outer.get_upper(),editor.get_height()*2)
        self.assertAlmostEqual(inner.get_upper(),inner.get_page_size(),delta=1)
        editor.close();spin();self.assertEqual(self.w.notes_store.get(note.id),note)

    def test_annotations_share_projection_and_exact_edition_color_wins_without_migration(self):
        from bible.passage_annotations import PassageAnnotations
        w=self.w;reader=w.active_tab.reader;project=PassageAnnotations(w.library)
        note=w.notes_store.save('Kept body',['existing'],versification='KJV',start='Gen.1.1',end='Gen.1.2',origin_translation='Second',origin_language='en')
        w.highlights.set('KJV',['Gen.1.1'],'blue','Second')
        self.assertEqual(project.colors(reader,['Gen.1.1'],w.highlights)['Gen.1.1']['color'],'blue')
        self.assertEqual([n.id for n in project.note_map(reader,['Gen.1.1'],w.notes_store)['Gen.1.1']],[note.id])
        w.active_tab.update_notes(force=True)
        self.assertEqual([n.id for n in w.active_tab._note_refs['Gen.1.1']],[note.id])
        w.active_tab.update_highlights();buffer=w.active_tab.text.get_buffer()
        start=w.active_tab._verse_ranges['Gen.1.1'][0]
        self.assertIn('highlight-blue',[tag.props.name for tag in buffer.get_iter_at_offset(start).get_tags()])
        self.assertEqual(w.notes_store.get(note.id),note)
        self.assertEqual(w.highlights.entries[('KJV','Gen.1.1')]['resource'],'Second')
        installed_fixture(self.root,'Third',versification='KJVA')
        w.highlights.set('KJVA',['Gen.1.1'],'green','Third')
        w.highlights.set('KJV',['Gen.1.1'],'yellow','First')
        for entries in (dict(w.highlights.entries),dict(reversed(list(w.highlights.entries.items())))):
            w.highlights.entries=entries
            self.assertEqual(project.colors(reader,['Gen.1.1'],w.highlights)['Gen.1.1']['color'],'yellow')
        self.assertEqual(len(w.highlights.entries),2)

    def test_label_candidates_are_real_nonblank_case_accent_search_and_reopen(self):
        from bible.notes_window import Labels
        labels=Labels(['test','toto','Éclair',''],lambda:None)
        def candidates():
            values=[];child=labels.suggestion_rows.get_first_child()
            while child:values.append(child.get_label());child=child.get_next_sibling()
            return values
        self.assertEqual(candidates(),['test','toto','Éclair'])
        labels.entry.set_text('T');self.assertEqual(candidates(),['test','toto'])
        labels.entry.set_text('ecl');self.assertEqual(candidates(),['Éclair'])
        labels.entry.set_text('test');labels.add();labels.entry.set_text('t')
        self.assertEqual(candidates(),['toto']);self.assertEqual(labels.values,['test'])
        labels.set_suggestions(['test','toto','Other']);self.assertEqual(candidates(),['toto'])

    def test_annotation_range_keeps_verified_body_past_unmapped_numbered_titles(self):
        from bible.passage_annotations import PassageAnnotations
        from bible.sword_provider import Reader
        installed_fixture(self.root,'French',versification='Segond',entries=[('Ps.51.1','NUMBERED TITLE'),('Ps.51.2','SECOND TITLE'),('Ps.51.3','SOURCE BODY')])
        installed_fixture(self.root,'English',entries=[('Ps.51.1','TARGET BODY')])
        note=self.w.notes_store.save('Whole source passage',[],versification='Segond',start='Ps.51.1',end='Ps.51.3',origin_translation='French',origin_language='fr')
        reader=Reader(self.w.library.root/'English','English');projection=PassageAnnotations(self.w.library)
        spans=projection.positions(reader,note.versification,note.start,note.end,note.origin_translation)
        self.assertEqual([(first,last) for _,_,first,last in spans],[('Ps.51.1','Ps.51.1')])
        self.assertEqual([value.id for value in projection.notes(reader,'Ps.51.1','Ps.51.1',self.w.notes_store)],[note.id])
        self.assertEqual(self.w.notes_store.get(note.id),note)

    def test_link_cards_use_saved_origin_and_unlink_keeps_note_body(self):
        from bible.notes_window import NoteEditor
        from bible.notes import PassageLink
        note=self.w.notes_store.save('Keep exactly',[],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='Second',origin_language='en',links=[PassageLink('KJV','John.3.16','John.3.17')])
        editor=self.w.edit_note(note=note);links=editor.links
        card=links.rows.get_first_child()
        self.assertEqual(card._target,('Second','John.3.16'))
        self.assertIn('JOHN 3:16 TEST DATA',card._reference_labels[1].get_text())
        self.w.active_tab.navigate('First','Gen.2.1');links.refresh()
        card=links.rows.get_first_child();self.assertEqual(card._target[0],'Second')
        with patch.object(self.w,'navigate_selection') as navigate:
            card.unlink_button.emit('clicked');navigate.assert_not_called()
        editor.close();spin()
        saved=self.w.notes_store.get(note.id);self.assertEqual(saved.body,'Keep exactly');self.assertEqual(saved.links,())

    def test_ctrl_q_flushes_draft_through_the_normal_close_guard(self):
        from bible.notes import NoteStore
        editor=self.w.edit_note(context=dict(versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='First',origin_language='en'))
        editor.body.get_buffer().set_text('Retained on Ctrl+Q')
        self.app.activate_action('quit',None);spin(lambda:self.w.closed)
        store=NoteStore(self.root/'notes.sqlite3')
        try:self.assertIn('Retained on Ctrl+Q',[note.body for note in store.all()])
        finally:store.close()
