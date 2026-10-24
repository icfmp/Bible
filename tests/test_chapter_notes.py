"""Chapter membership, semantic following and draft ownership without migrations."""
import os
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace
from tests.test_ui import installed_fixture,spin,close_test_dialogs
from bible.i18n import tr


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
class ChapterNotesTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        installed_fixture(self.root,entries=[(f'Acts.1.{n}',f'EXACT FIXTURE {n} '+('word '*50)) for n in range(1,27)]+[('Acts.2.1','NEXT CHAPTER')])
        app=Application.get_default() or Application();app.register()
        self.w=Window(app,Library(self.root/'translations'));self.w.set_default_size(1250,800);self.w.present();spin()
        self.w.active_tab.navigate('Test','Acts.1.1');self.w.study_button.set_active(True);self.w.study.tools.set_visible_child_name('notes')
        self.p=self.w.study.notes
        self.notes=[self.save(v,f'Personal note {v} '+('body '*20)) for v in (15,8,2,8)]
        self.w.highlights.set('KJV',['Acts.1.8'],'blue','Test');self.p.refresh(force=True);spin()

    def save(self,verse,body):
        return self.w.notes_store.save(body,[],versification='KJV',start=f'Acts.1.{verse}',end=f'Acts.1.{verse}',origin_translation='Test',origin_language='en')

    def tearDown(self):
        if self.w.note_editor:self.w.note_editor._discard=True;self.w.note_editor.close()
        close_test_dialogs();self.w.close()

    def test_whole_chapter_canonical_order_group_gaps_no_rebuild_or_navigation(self):
        p=self.p;tab=self.w.active_tab;cards=list(p.cards);history=list(tab.state.history)
        self.assertEqual(len(cards),5);self.assertEqual([n.start for n in p.rows],['Acts.1.2','Acts.1.8','Acts.1.8','Acts.1.15'])
        self.assertTrue(p.heading.get_text().endswith('1'));self.assertNotIn(':',p.heading.get_text())
        self.assertFalse(hasattr(p,'add'));self.assertFalse(hasattr(tab,'note_button'))
        for verse in [8,9,15,26,2,1]:
            tab.select_verse(f'Acts.1.{verse}');spin()
            self.assertEqual(p.cards,cards);self.assertEqual(tab.state.history,history)
            candidates=[(c,spans) for c,spans in p._card_targets if any(a<=tab.reader.key(tab.state.reference).getIndex()<=b for a,b,_,_ in spans)]
            if candidates:
                rect=candidates[0][0].compute_bounds(p.scroll)[1]
                self.assertGreaterEqual(rect.get_y(),-1);self.assertLess(rect.get_y(),p.scroll.get_height())
        before=p.scroll.get_vadjustment().get_value();p.queue_follow(tab.state.reference);spin()
        self.assertEqual(p.scroll.get_vadjustment().get_value(),before)

    def test_manual_browsing_suspends_and_explicit_resume_uses_same_records(self):
        p=self.p;tab=self.w.active_tab;p.suspend_following();p.scroll.get_vadjustment().set_value(120)
        before=p.scroll.get_vadjustment().get_value();tab.state.reference='Acts.1.15';p.refresh();spin()
        self.assertEqual(p.scroll.get_vadjustment().get_value(),before);self.assertTrue(p.resume.get_visible())
        p.resume_following();spin();self.assertTrue(p.following);self.assertFalse(p.resume.get_visible())
        p.suspend_following();tab.select_verse('Acts.1.2');spin();self.assertTrue(p.following)

    def test_draft_keeps_context_across_chapter_tab_callbacks_and_restart(self):
        p=self.p;editor=p.open_note(self.notes[1]);editor.body.get_buffer().set_text('Captured draft kept')
        context=dict(editor.context);self.w.active_tab.navigate('Test','Acts.2.1');self.w.new_tab();spin()
        self.assertIs(p.editor,editor);self.assertEqual(editor.context,context);self.assertEqual(editor.body.get_buffer().props.text,'Captured draft kept')
        p.resume_following();self.assertFalse(p.following);self.assertTrue(editor.save())
        self.assertEqual(self.w.notes_store.get(self.notes[1].id).start,'Acts.1.8')
        self.w.active_tab.navigate('Test','Acts.1.2');self.w.reveal_passage_annotations();spin()
        self.assertIsNone(p.editor);self.assertIsNone(self.w.note_editor if self.w.note_editor and not self.w.note_editor.closed else None)
        self.assertEqual(len(p.rows),4)

    def test_verified_cross_chapter_mapping_and_range_projection_once(self):
        from bible.sword_provider import Reader
        from bible.passage_annotations import PassageAnnotations
        installed_fixture(self.root,'Luther',versification='Luther',entries=[('Gen.31.54','TARGET ONE'),('Gen.32.1','TARGET TWO')])
        installed_fixture(self.root,'Base',entries=[('Gen.31.54','SOURCE ONE'),('Gen.31.55','SOURCE TWO'),('Gen.32.1','THIRD')])
        note=self.w.notes_store.save('Cross target chapter note',[],versification='KJV',start='Gen.31.54',end='Gen.31.55',origin_translation='Base',origin_language='de')
        self.w.active_tab.navigate('Luther','Gen.31.54');self.p.refresh(force=True);spin();self.assertEqual([n.id for n in self.p.rows],[note.id])
        self.w.active_tab.navigate('Luther','Gen.32.1');self.p.refresh();spin();self.assertEqual([n.id for n in self.p.rows],[note.id])
        crossing=self.w.notes_store.save('Actual cross-chapter note',[],versification='KJV',start='Gen.31.55',end='Gen.32.1',origin_translation='Base',origin_language='en')
        self.w.active_tab.navigate('Base','Gen.31.55');self.p.refresh(force=True);spin()
        self.assertEqual([n.id for n in self.p.rows].count(crossing.id),1)
        self.w.active_tab.navigate('Base','Gen.32.1');self.p.refresh();spin()
        self.assertEqual([n.id for n in self.p.rows].count(crossing.id),1)
        self.assertEqual(self.w.notes_store.get(crossing.id),crossing)
        space=self.w.open_notes();space.versions.set_selected(space.version_names.index('Base'));space.open_note(crossing);spin()
        self.assertTrue(space.open_button.get_sensitive())
        self.assertIn('SOURCE TWO',space.excerpt.get_text());self.assertIn('THIRD',space.excerpt.get_text());space.leave()
        self.w.notes_store.delete(crossing)
        self.w.active_tab.navigate('Luther','Gen.32.1');self.p.refresh(force=True);spin()
        # Read-only range projection keeps native chapter introductions out.
        spans=PassageAnnotations().positions(Reader(self.w.library.root/'Base','Base'),'KJV','Gen.31.55','Gen.32.1')
        self.assertEqual(len(spans),2);self.assertEqual(spans[0][2],'Gen.31.55');self.assertEqual(spans[-1][3],'Gen.32.1')
        self.assertEqual(self.w.notes_store.get(note.id),note)
        # The existing comparison driver maps back into the leading Bible;
        # chapter Notes observes that semantic reference without reverse scroll.
        from unittest.mock import patch
        tab=self.w.active_tab;tab.state.comparison='Base';self.w.sync_comparison();spin()
        history=list(tab.state.history);self.p.suspend_following()
        with patch.object(tab,'comparison_visible_reference',return_value='Gen.31.55'):
            tab.comparison_sync.intent('comparison');tab.comparison_sync.synchronize();spin()
        self.assertEqual(tab.state.reference,'Gen.32.1');self.assertTrue(self.p.following)
        self.assertEqual(tab.state.history,history);self.assertEqual([n.id for n in self.p.rows],[note.id])

    def test_large_collection_all_reachable_and_stale_reveal_cancelled(self):
        for i in range(200):self.save(20,f'Independent note {i}')
        self.p.refresh(force=True);spin();self.assertEqual(len(self.p.cards),205)
        self.w.active_tab.select_verse('Acts.1.20');self.w.active_tab.navigate('Test','Acts.2.1');spin()
        self.assertEqual(self.p.cards,[]);self.assertEqual(self.p.rows,[]);self.assertEqual(self.w.active_tab.state.reference,'Acts.2.1')
        self.assertIn(tr('No annotations in this chapter.'),self.p.status.get_text())
