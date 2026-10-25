"""Native correspondence layout keeps source words and one shared adjustment."""
import os
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK')
class ComparisonRowsTests(unittest.TestCase):
    def test_split_final_john_verses_form_one_correspondence_group(self):
        from bible.comparison_layout import correspondences
        from bible.sword_provider import Reader
        from tests.test_ui import installed_fixture
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,'Base',entries=[('3John.1.14','BASE ENTIRE VERSE')])
            installed_fixture(directory,'NRSV',versification='NRSV',entries=[('3John.1.14','FIRST SOURCE PART'),('3John.1.15','SECOND SOURCE PART')])
            root=Path(directory)/'translations'
            left=Reader(root/'Base','Base');right=Reader(root/'NRSV','NRSV')
            rows=correspondences(left,right,['3John.1.14'],['3John.1.14','3John.1.15'])
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0].secondary,('3John.1.14','3John.1.15'))

    def test_wrapped_rows_stay_aligned_reflow_and_single_prose_restore(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin
        with tempfile.TemporaryDirectory() as directory:
            for name,count in [('Primary',5),('Secondary',40)]:
                installed_fixture(directory,name,entries=[(f'Gen.1.{v}',f'{name} UNIQUE{v} '+('words '*((count+v)%45+1))) for v in range(1,20)])
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(Path(directory)/'translations'));window.set_default_size(1250,850);window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Primary','Gen.1.1')
                ordinary=tab._document.copy(0,len(tab._document.text))
                tab.state.comparison='Secondary';window.sync_comparison();spin(duration=.5)
                self.assertTrue(tab._shared_comparison)
                self.assertIs(tab.scroll.get_vadjustment(),tab.comparison_scroll.get_vadjustment())
                def aligned():
                    for left,right in zip(tab.comparison_rows.bounds[0],tab.comparison_rows.bounds[1]):
                        a=tab.text.get_iter_location(tab.text.get_buffer().get_iter_at_offset(left[0])).y
                        b=tab.comparison_text.get_iter_location(tab.comparison_text.get_buffer().get_iter_at_offset(right[0])).y
                        self.assertAlmostEqual(a,b,delta=1)
                aligned()
                for view in (tab.text,tab.comparison_text):
                    text=view.get_buffer().props.text
                    for v in range(1,20):self.assertEqual(text.count(f'UNIQUE{v} '),1)
                window.set_default_size(900,720);spin(duration=.5);aligned()
                history=list(tab.state.history)
                adjustment=tab.scroll.get_vadjustment();adjustment.set_value(400);spin()
                self.assertEqual(tab.comparison_scroll.get_vadjustment().get_value(),adjustment.get_value())
                self.assertEqual(tab.state.history,history)
                window.end_comparison();spin()
                self.assertFalse(tab._shared_comparison)
                self.assertEqual(tab._document.copy(0,len(tab._document.text)),ordinary)
            finally:window.close()

    def test_chapter_navigation_discards_previous_reflow_anchor(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[('Gen.1.1','First chapter'),('Gen.2.1','Second chapter')])
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(Path(directory)/'translations'));window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Test','Gen.1.1');spin(lambda:not tab._restoring_scroll)
                tab._layout_anchor=('Gen.1.1',3)
                tab.navigate('Test','Gen.2.1')
                self.assertIsNone(tab._layout_anchor)
                # A pending layout callback from the former document is inert.
                tab._appearance_anchor=('Gen.1.1',3)
                window.set_default_size(540,730)
                spin(lambda:not tab._restoring_scroll)
                self.assertEqual(tab.state.reference,'Gen.2.1')
                self.assertIsNone(tab._appearance_anchor)
            finally:window.close()

    def test_split_mapping_groups_and_known_absence_preserve_every_source_verse(self):
        from bible.comparison_layout import correspondences
        from bible.sword_provider import Reader
        from tests.test_ui import installed_fixture
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,'Base',entries=[('Ps.3.1','A'),('Ps.3.2','B'),('Ps.3.3','C')])
            installed_fixture(directory,'Shift',versification='Segond',entries=[('Ps.3.2','AA'),('Ps.3.3','BB')])
            root=Path(directory)/'translations'
            left=Reader(root/'Base','Base');right=Reader(root/'Shift','Shift')
            rows=correspondences(left,right,['Ps.3.1','Ps.3.2','Ps.3.3'],['Ps.3.2','Ps.3.3'])
            self.assertEqual(rows[0].primary,('Ps.3.1',));self.assertEqual(rows[0].secondary,('Ps.3.2',))
            self.assertEqual(rows[1].primary,('Ps.3.2',));self.assertEqual(rows[1].secondary,('Ps.3.3',))
            self.assertEqual(rows[2].secondary,())
