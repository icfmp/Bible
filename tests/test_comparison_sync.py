import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture, spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ComparisonTests(unittest.TestCase):
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
            finally:window.close()
