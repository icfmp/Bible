import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture, spin
from bible.i18n import tr


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ComparisonTests(unittest.TestCase):
    def test_switching_primary_clears_an_obsolete_alignment_error(self):
        from bible.ui import Application, Window, Library
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,'Unsupported',versification='LXX')
            installed_fixture(directory,'Primary')
            installed_fixture(directory,'Target',entries=[('Gen.1.1','TARGET SOURCE TEXT')])
            window=Window(app,Library(Path(directory)/'translations'));window.present()
            try:
                tab=window.active_tab;tab.navigate('Unsupported','Gen.1.1')
                tab.state.comparison='Target';window.sync_comparison()
                spin(lambda:not tab._restoring_scroll)
                self.assertTrue(tab.comparison_status.get_text())
                self.assertIn('TARGET SOURCE TEXT',tab.comparison_text.get_buffer().props.text)
                self.assertIn(tr('Independent reading'),tab.comparison_heading.get_text())
                before=tab.state.reference;history=list(tab.state.history)
                for side in ('primary','comparison'):
                    tab.comparison_sync.intent(side);tab.comparison_sync.synchronize()
                    self.assertEqual(tab.state.reference,before)
                    self.assertIn('TARGET SOURCE TEXT',tab.comparison_text.get_buffer().props.text)
                self.assertEqual(tab.state.history,history)
                # Same printed reference and comparison resource, new primary.
                self.assertTrue(tab.navigate('Primary','Gen.1.1'))
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False))
                self.assertFalse(tab.comparison_status.get_text())
                self.assertIn('TARGET SOURCE TEXT',tab.comparison_text.get_buffer().props.text)
            finally:window.close()

    def test_switching_primary_recomputes_the_same_printed_psalm_reference(self):
        from bible.ui import Application, Window, Library
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            entries=[('Ps.3.1','FIRST SOURCE VERSE'),('Ps.3.2','SECOND SOURCE VERSE')]
            installed_fixture(directory,'Primary',entries=entries)
            installed_fixture(directory,'Shifted',entries=entries,versification='Segond')
            installed_fixture(directory,'Target',entries=entries)
            window=Window(app,Library(Path(directory)/'translations'));window.present()
            try:
                tab=window.active_tab;tab.navigate('Primary','Ps.3.2')
                tab.state.comparison='Target';window.sync_comparison()
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False))
                self.assertTrue(tab.comparison_heading.get_text().endswith('Ps.3.2'))
                self.assertTrue(tab.navigate('Shifted','Ps.3.2'))
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False))
                self.assertFalse(tab.comparison_status.get_text())
                self.assertTrue(tab.comparison_heading.get_text().endswith('Ps.3.1'))
            finally:window.close()

    def test_shared_render_and_reference_follow_without_history(self):
        from bible.ui import Application, Window, Library
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            for name,length in [('Test',70),('Other',110)]:
                installed_fixture(directory,name,entries=[(f'Gen.1.{i}',f'{name} verse {i} words '*length) for i in range(1,9)])
            window=Window(app,Library(Path(directory)/'translations'));window.present()
            try:
                tab=window.active_tab;tab.navigate('Test','Gen.1.1')
                tab.state.comparison='Other';window.sync_comparison()
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False))
                for view in [tab.text,tab.comparison_text]:
                    self.assertEqual(view.get_pixels_inside_wrap(),16)
                    self.assertIsNotNone(view.get_buffer().get_tag_table().lookup('verse-number'))
                    self.assertIsNotNone(view.get_buffer().get_tag_table().lookup('verse-start'))
                before=len(tab.state.history)
                tab.comparison_sync.intent('comparison')
                buffer=tab.comparison_text.get_buffer();offset=tab._comparison_offsets['Gen.1.3']
                target=tab.comparison_text.get_iter_location(buffer.get_iter_at_offset(offset))
                adjustment=tab.comparison_scroll.get_vadjustment();rect=tab.comparison_text.get_visible_rect()
                adjustment.set_value(adjustment.get_value()+target.y-rect.y)
                spin(lambda:tab.state.reference=='Gen.1.3')
                self.assertEqual(len(tab.state.history),before)
                self.assertEqual(tab.visible_reference(),'Gen.1.3')
                # A later layout/programmatic movement with no input lease must
                # not become another comparison leader.
                tab.comparison_sync.armed_until=0
                state=tab.state.reference;adjustment.set_value(0);spin(duration=.2)
                self.assertEqual(tab.state.reference,state)
                tab.reveal_comparison('Gen.1.3',settle=True)
                spin(lambda:not getattr(tab,'_comparison_positioning',False))
                before=tab.comparison_visible_reference()
                window.study_button.set_active(True)
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False),duration=.3)
                self.assertEqual(tab.comparison_visible_reference(),before)
                tab.state.comparison='Missing';tab.refresh_comparison()
                self.assertTrue(tab.comparison_status.get_text())
                self.assertFalse(buffer.props.text)
                tab.state.comparison='Other';tab.refresh_comparison()
                spin(lambda:not getattr(tab,'_comparison_positioning',False))
                self.assertFalse(tab.comparison_status.get_text())
                self.assertIn('Other verse 3 words',buffer.props.text)
            finally:window.close()
