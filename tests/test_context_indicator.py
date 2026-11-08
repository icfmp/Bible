import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture,spin
from tests.test_reading_sync import linked_commentary


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ContextIndicatorTests(unittest.TestCase):
    def test_notes_and_references_share_transient_indicator_and_adaptive_context(self):
        from bible.ui import Application,Window,Library
        from bible.notes import PassageLink
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[(f'Gen.1.{i}',f'Verse {i} words '*12) for i in range(1,9)]+[('Gen.2.1','Next chapter')])
            w=Window(app,Library(Path(directory)/'translations'));w.set_default_size(1440,900);w.present()
            try:
                tab=w.active_tab;tab.navigate('Test','Gen.1.2');w.study_button.set_active(True)
                w.study.tools.set_visible_child_name('notes');spin(lambda:not tab._restoring_scroll)
                self.assertIsNone(tab._study_coverage)
                note=w.notes_store.save('Preserved note',[],versification='KJV',start='Gen.1.2',end='Gen.1.3',
                    origin_translation='Test',origin_language='en',links=[PassageLink('KJV','Gen.2.1','Gen.2.1')])
                w.study.notes.refresh();spin()
                self.assertEqual(tab._study_coverage,('KJV','Gen.1.2','Gen.1.3'))
                self.assertFalse(w.study.context_heading.get_visible())
                text=tab.text.get_buffer().props.text
                tab.select_verse('Gen.1.7');spin()
                self.assertIsNone(tab._study_coverage)
                tab.navigate('Test','Gen.2.1');spin(lambda:not tab._restoring_scroll)
                self.assertEqual(tab._study_coverage,('KJV','Gen.2.1','Gen.2.1'))
                w.study.tools.set_visible_child_name('references');spin()
                self.assertEqual(tab._study_coverage,('KJV','Gen.2.1','Gen.2.1'))
                self.assertFalse(w.study.context_heading.get_visible())
                w.set_default_size(560,700);spin(duration=.3)
                self.assertTrue(w.split.get_collapsed());self.assertTrue(w.study.context_heading.get_visible())
                self.assertTrue(w.study.context_heading.get_text())
                self.assertEqual(w.notes_store.get(note.id),note)
                self.assertFalse((Path(directory)/'highlights.json').exists())
            finally:w.close()

    def test_true_range_is_paint_only_and_clears_without_navigation(self):
        from bible.ui import Application,Window,Library
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[(f'Gen.1.{i}',f'Verse {i} words '*12) for i in range(1,9)])
            linked_commentary(directory)
            window=Window(app,Library(Path(directory)/'translations'));window.set_default_size(1440,900);window.present()
            try:
                tab=window.active_tab;tab.navigate('Test','Gen.1.3');tab.state.commentary='Notes'
                window.study_button.set_active(True);window.study.refresh()
                spin(lambda:not tab._restoring_scroll and not window.study._positioning)
                self.assertEqual(tab._study_coverage,('KJV','Gen.1.2','Gen.1.3'))
                self.assertEqual(tab.text.study_ranges,tuple(tab._verse_ranges[r] for r in ['Gen.1.2','Gen.1.3']))
                self.assertEqual(tab.state.reference,'Gen.1.3')
                self.assertTrue(tab.text.indicator_segments())
                buffer=tab.text.get_buffer();text=buffer.props.text
                start=tab._marker_ends['Gen.1.3']
                buffer.select_range(buffer.get_iter_at_offset(start+1),buffer.get_iter_at_offset(start+8))
                bounds=tuple(i.get_offset() for i in buffer.get_selection_bounds())
                window.study.update_indicator()
                self.assertEqual(tuple(i.get_offset() for i in buffer.get_selection_bounds()),bounds)
                self.assertEqual(buffer.props.text,text)
                window.study_button.set_active(False);spin()
                self.assertFalse(tab.text.study_ranges)
                self.assertEqual(tab.state.reference,'Gen.1.3')
                window.study_button.set_active(True);spin()
                self.assertEqual(len(tab.text.study_ranges),2)
                introduction=next(i for i,s in enumerate(window.study.reader.index.sections) if s.introduction)
                window.study.current_position=introduction;window.study.update_indicator()
                self.assertFalse(tab.text.study_ranges)
                self.assertNotIn('_study_coverage',vars(tab.state))
                self.assertFalse((Path(directory)/'highlights.json').exists())
            finally:window.close()
