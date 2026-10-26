"""Native layout invalidations settle; an idle reader must not keep polling."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ReaderLayoutIdleTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        installed_fixture(self.root,long_text=True)
        app=Application.get_default() or Application();app.register()
        self.window=Window(app,Library(self.root/'translations'));self.window.present()
        self.tab=self.window.active_tab
        spin(self.settled,duration=.4)

    def tearDown(self):self.window.close()

    def settled(self):
        w=self.window;t=self.tab
        return not (t._restoring_scroll or t._adapt_id or w._controls_tick or w.study_divider._adapt_id)

    def test_idle_has_no_geometry_or_caption_polling(self):
        w=self.window;t=self.tab
        with patch.object(t,'adapt_comparison',wraps=t.adapt_comparison) as reader, \
                patch.object(w,'fit_reader_controls',wraps=w.fit_reader_controls) as controls, \
                patch.object(w.study_divider,'adapt',wraps=w.study_divider.adapt) as divider:
            spin(duration=.6)
            reader.assert_not_called();controls.assert_not_called();divider.assert_not_called()

    def test_resize_scroll_and_font_changes_settle_with_reading_anchor(self):
        w=self.window;t=self.tab
        adjustment=t.scroll.get_vadjustment()
        adjustment.set_value((adjustment.get_upper()-adjustment.get_page_size())*.4)
        spin(self.settled,duration=.2)
        anchor=t._layout_anchor
        self.assertIsNotNone(anchor)
        with patch.object(t,'adapt_comparison',wraps=t.adapt_comparison) as reader:
            previous_width=w.get_width()
            w.set_default_size(680,600)
            # Native CSD shadows are outside get_width(), unlike default-size.
            spin(lambda:self.settled() and w.get_width()<previous_width,duration=.3)
            self.assertGreater(reader.call_count,0)
            self.assertEqual(t._layout_anchor[0],anchor[0])
            self.assertEqual(t.text.get_left_margin(),t.text.get_right_margin())
            reader.reset_mock();spin(duration=.4);reader.assert_not_called()
        w.appearance.update('size',24)
        spin(self.settled,duration=.4)
        self.assertEqual(t._layout_anchor[0],anchor[0])

    def test_hidden_actions_cancel_pending_capture_without_native_popup_work(self):
        w=self.window;t=self.tab;a=w.passage_actions
        before=a.intent
        with patch.object(a.bar,'clear_backdrop',wraps=a.bar.clear_backdrop) as backdrop, \
                patch.object(a.copy_popover,'popdown',wraps=a.copy_popover.popdown) as popup:
            for _ in range(30):a.dismiss()
            backdrop.assert_not_called();popup.assert_not_called()
        self.assertEqual(a.intent,before+30)
        buffer=t.text.get_buffer();start=t._marker_ends['Gen.1.1']
        buffer.select_range(buffer.get_iter_at_offset(start),buffer.get_iter_at_offset(start+5))
        a.capture(t.text,lambda:a.ordinary(t),None);a.dismiss();spin()
        self.assertIsNone(a.target);self.assertFalse(a.bar.get_visible())
        self.assertIsNone(a.bar.backdrop)
