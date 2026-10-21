import os
from pathlib import Path
import tempfile
import unittest
from tests.fixtures import module_fixture
from tests.test_ui import installed_fixture,spin
from bible.sword_provider import CommentaryReader


def linked_commentary(directory):
    import Sword
    root=Path(directory)/'translations'/'Notes'
    module_fixture(root,'Notes',[('Gen.1.1','FIRST COMMENT TEST'),('Gen.1.2','LONG COMMENT TEST '*900),
                               ('Gen.1.4','UNLINKED IDENTICAL'),('Gen.1.5','UNLINKED IDENTICAL'),
                               ('Gen.2.1','NEXT CHAPTER COMMENT TEST')],commentary=True)
    module=Sword.RawCom(str(root/'modules/texts/rawtext/test'),'Notes','Test data only')
    module.setKey(Sword.VerseKey('Gen.1.3'));module.linkEntry(Sword.VerseKey('Gen.1.2'))
    key=Sword.VerseKey();key.setIntros(True);key.setIndex(2)
    module.setKey(key);module.setEntry('BOOK INTRODUCTION TEST');del module
    (root/'.complete').write_text('Notes');return root


class CommentaryIndexTests(unittest.TestCase):
    def test_native_links_introductions_and_distinct_identical_texts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=linked_commentary(directory);reader=CommentaryReader(root,'Notes');index=reader.index
            two=index.locate('Gen.1.2');self.assertEqual(index.locate('Gen.1.3'),two)
            self.assertEqual((index.sections[two].start,index.sections[two].end),('Gen.1.2','Gen.1.3'))
            self.assertNotEqual(index.locate('Gen.1.4'),index.locate('Gen.1.5'))
            self.assertTrue(index.sections[0].introduction)
            self.assertIn('INTRODUCTION',index.text(0))
            self.assertIsNone(index.locate('John.1.1'))


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ReadingSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application,Gtk
        cls.app=Application.get_default() or Application();cls.app.register()
        Gtk.Settings.get_default().set_property('gtk-enable-animations',False)

    def setup_window(self,directory):
        from bible.ui import Window,Library
        entries=[(f'Gen.1.{i}',(f'VERSE {i} TEST '*90)) for i in range(1,9)]+[('Gen.2.1','SECOND CHAPTER BIBLE TEST')]
        installed_fixture(directory,entries=entries);linked_commentary(directory)
        window=Window(self.app,Library(Path(directory)/'translations'));window.present()
        window.active_tab.state.commentary='Notes';window.study_button.set_active(True);window.study.refresh()
        self.addCleanup(lambda:window.close() if not window.closed else None)
        spin(lambda:not window.active_tab._restoring_scroll and not window.study._positioning,duration=.3)
        return window

    def scroll_reference(self,w,reference):
        tab=w.active_tab;view=tab.text
        w.reading_sync.intent('bible',tab)
        iterator=view.get_buffer().get_iter_at_offset(tab._verse_offsets[reference])
        target=view.get_iter_location(iterator);rect=view.get_visible_rect()
        adjustment=tab.scroll.get_vadjustment();adjustment.set_value(adjustment.get_value()+target.y-rect.y)
        spin(lambda:tab.state.reference==reference and not w.study._positioning,duration=.25)

    def test_both_directions_ranges_missing_history_focus_and_long_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            w=self.setup_window(directory);tab=w.active_tab;study=w.study
            history_count=len(tab.state.history)
            self.scroll_reference(w,'Gen.1.2')
            self.assertIn('LONG COMMENT',study.entry_text)
            long_position=study.reader.index.locate('Gen.1.2')
            # Real user driver, then a scroll inside the long entry.
            w.reading_sync.intent('commentary');study.text.grab_focus()
            start,body,end=study.ranges[long_position]
            target=study.text.get_iter_location(study.text.get_buffer().get_iter_at_offset(body+1200))
            rect=study.text.get_visible_rect();adj=study.scroll.get_vadjustment()
            adj.set_value(adj.get_value()+target.y-rect.y);spin(duration=.3)
            before=adj.get_value();focus=w.get_focus()
            self.scroll_reference(w,'Gen.1.3')
            self.assertAlmostEqual(adj.get_value(),before,delta=4)
            self.assertIs(w.get_focus(),focus)
            # An explicit entry action advances the commentary and leads the Bible.
            study.current_position=study.reader.index.locate('Gen.1.5');study.step_entry(1)
            spin(lambda:tab.state.reference=='Gen.2.1',duration=.3)
            self.assertEqual(len(tab.state.history),history_count)
            self.assertIn('Gen.2.1',str(tab.state.commentary_positions))
            tab._travelling=True
            try:tab.show('Gen.1.6')
            finally:tab._travelling=False
            spin(lambda:not tab._restoring_scroll)
            self.assertEqual(study.entry_text,'')
            self.assertEqual(study.text.get_buffer().props.text,'')
            from bible.i18n import tr
            self.assertEqual(tr('No commentary for this passage.'),study.status.get_text())
            w.close()
            from bible.session import SessionStore
            restored=SessionStore(Path(directory)/'session.json').load()
            self.assertIn('Notes',restored.tabs[0].commentary_positions)

    def test_partial_copy_stays_partial_and_selection_does_not_sync(self):
        from gi.repository import GLib
        with tempfile.TemporaryDirectory() as directory:
            w=self.setup_window(directory);tab=w.active_tab;buffer=tab.text.get_buffer()
            start=tab._marker_ends['Gen.1.1']
            buffer.select_range(buffer.get_iter_at_offset(start+3),buffer.get_iter_at_offset(start+13))
            expected=buffer.get_text(*buffer.get_selection_bounds(),False)
            tab.text.emit('copy-clipboard');result=[]
            tab.get_clipboard().read_text_async(None,lambda clipboard,r:result.append(clipboard.read_text_finish(r)))
            spin(lambda:bool(result));self.assertEqual(result[0],expected)
            w.lookup_action('copy-with-reference').activate(None);result=[]
            tab.get_clipboard().read_text_async(None,lambda clipboard,r:result.append(clipboard.read_text_finish(r)))
            spin(lambda:bool(result))
            self.assertIn('Test',result[0]);self.assertIn('VERSE 1 TEST '*3,result[0])
            self.assertNotEqual(result[0],expected)
            w.reading_sync.intent('bible',tab)
            adj=tab.scroll.get_vadjustment();adj.set_value(adj.get_upper()*.4);spin(duration=.2)
            self.assertEqual(tab.state.reference,'Gen.1.1')
            w.close()

    def test_scroll_work_is_coalesced_cancelled_and_stops_at_resource_end(self):
        from unittest.mock import patch
        from bible.ui import GLib
        with tempfile.TemporaryDirectory() as directory:
            w=self.setup_window(directory);study=w.study
            try:
                with patch.object(study,'remember_position') as remember:
                    study.scrolled();study.scrolled()
                    self.assertTrue(study._scroll_idle)
                    remember.assert_not_called()
                    spin(lambda:not study._scroll_idle)
                    remember.assert_called_once()
                study.scrolled();self.assertTrue(study._scroll_idle)
                w.study_button.set_active(False)
                self.assertEqual(study._scroll_idle,0)
                w.study_button.set_active(True);spin(lambda:not study._positioning)
                # A queued load must not act on a replaced source/tab buffer.
                study._loading=True;study._load_idle=GLib.idle_add(study.load_more,1)
                study.clear_content()
                self.assertEqual(study._load_idle,0);self.assertFalse(study._loading)
                study.follow('Gen.2.1');spin(lambda:not study._positioning)
                self.assertEqual(study.loaded[-1],len(study.reader.index.sections)-1)
                with patch.object(study,'rebuild') as rebuild:
                    study.load_more(1);rebuild.assert_not_called()
                study.scrolled();w.close()
                self.assertEqual(study._scroll_idle,0);self.assertEqual(study._load_idle,0)
            finally:
                if not w.closed:w.close()
