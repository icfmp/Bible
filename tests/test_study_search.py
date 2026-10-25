"""Search lifecycle and passage-selector integration against a real SWORD fixture."""
import os
from pathlib import Path
import tempfile
import threading
import unittest
from bible.reference_data import Relationship
from tests.test_ui import installed_fixture,spin,close_test_dialogs


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class StudySearchTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()));installed_fixture(self.root)
        from bible.ui import Application,Window,Library
        app=Application.get_default() or Application();app.register()
        self.window=Window(app,Library(self.root/'translations'));self.window.present()
        self.window.active_tab.navigate('Test','John.1.1');spin(lambda:not self.window.active_tab._restoring_scroll)
        self.navigation=self.window.navigation;self.navigation.sync(force=True)

    def tearDown(self):
        close_test_dialogs();self.window.close()

    def test_superseded_worker_cannot_replace_new_result_or_reopen_preview(self):
        panel=self.navigation.text_search;started=threading.Event();release=threading.Event()
        self.addCleanup(release.set)
        def old():started.set();release.wait(3);return [Relationship('Gen.1.1','Gen.1.1',0,1)],1
        panel.launch(old,'old','KJV');self.assertTrue(started.wait(2))
        panel.launch(lambda:([Relationship('John.3.16','John.3.16',0,1)],1),'new','KJV');release.set()
        spin(lambda:not panel.pending)
        self.assertEqual([row.start for row in panel.rows],['John.3.16'])
        self.assertEqual(panel.heading.get_text(),'new');self.assertIsNone(self.window.reference_preview.popover)
        self.assertEqual(self.window.active_tab.state.reference,'John.1.1')

    def test_mode_change_invalidates_results_and_missing_data_keeps_passage_usable(self):
        n=self.navigation;p=n.topic_search;before=list(self.window.active_tab.state.history)
        n.modes.set_visible_child_name('topics');p.entry.set_text('pardon');p.changed()
        self.assertEqual(p.topic_model.get_n_items(),4);self.assertTrue(p.download.get_visible())
        p.choose(p.topic_model.get_item(0).value);self.assertFalse(p.pending);self.assertFalse(p.rows)
        n.modes.set_visible_child_name('passage');n.direct.set_text('John 3:16');n.commit();spin()
        self.assertEqual(self.window.active_tab.state.reference,'John.3.16')
        self.assertEqual(len(self.window.active_tab.state.history),len(before)+1)

    def test_unavailable_translation_and_invalid_phrase_do_not_launch_worker(self):
        p=self.navigation.text_search;p.entry.set_text('x'*201);p.run_text()
        self.assertFalse(p.pending);self.assertIsNone(p.future)
        p.search_reader=None;p.entry.set_text('source');p.run_text()
        self.assertFalse(p.pending);self.assertEqual(p.model.get_n_items(),0)

    def test_source_heading_occurrence_remains_unmapped_without_fabricated_verse_one(self):
        from gi.repository import Gtk
        n=self.navigation;n.owner.choose_passage();n.modes.set_visible_child_name('text')
        panel=n.text_search;before=(self.window.active_tab.state.reference,list(self.window.active_tab.state.history))
        panel.launch(lambda:([Relationship('Ps.3.0','Ps.3.0',0,1)],1),'Source heading','NRSV')
        spin(lambda:not panel.pending,duration=.2)
        def walk(widget):
            yield widget
            child=widget.get_first_child()
            while child:yield from walk(child);child=child.get_next_sibling()
        button=next(w for w in walk(panel.results) if isinstance(w,Gtk.Button) and hasattr(w,'_result'))
        button.emit('clicked');spin()
        preview=self.window.reference_preview
        self.assertIsNone(preview.target)
        self.assertFalse(preview.open_here.get_sensitive());self.assertFalse(preview.open_new.get_sensitive())
        self.assertEqual((self.window.active_tab.state.reference,self.window.active_tab.state.history),before)


if __name__=='__main__':unittest.main()
