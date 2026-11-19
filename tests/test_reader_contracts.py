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
        card=links.rows.get_first_child().get_first_child()
        self.assertEqual(card._target,('Second','John.3.16'))
        self.assertIn('JOHN 3:16 TEST DATA',card._reference_labels[1].get_text())
        self.w.active_tab.navigate('First','Gen.2.1');links.refresh()
        card=links.rows.get_first_child().get_first_child();self.assertEqual(card._target[0],'Second')
        links.remove(links.values[0]);editor.close();spin()
        saved=self.w.notes_store.get(note.id);self.assertEqual(saved.body,'Keep exactly');self.assertEqual(saved.links,())

    def test_ctrl_q_flushes_draft_through_the_normal_close_guard(self):
        from bible.notes import NoteStore
        editor=self.w.edit_note(context=dict(versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='First',origin_language='en'))
        editor.body.get_buffer().set_text('Retained on Ctrl+Q')
        self.app.activate_action('quit',None);spin(lambda:self.w.closed)
        store=NoteStore(self.root/'notes.sqlite3')
        try:self.assertIn('Retained on Ctrl+Q',[note.body for note in store.all()])
        finally:store.close()
