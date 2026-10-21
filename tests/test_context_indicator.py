import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture,spin
from tests.test_reading_sync import linked_commentary


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ContextIndicatorTests(unittest.TestCase):
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
