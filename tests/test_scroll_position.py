"""Viewport movement persists without rediscovering resources or rebuilding UI."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ScrollPositionTests(unittest.TestCase):
    def test_native_adjustment_only_persists_position_but_passage_change_still_updates(self):
        from bible.ui import Application,Window,Library
        from bible.session import SessionStore
        from tests.test_ui import installed_fixture,spin
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed_fixture(root,long_text=True)
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(root/'translations'));window.present();spin()
            try:
                tab=window.active_tab;spin(lambda:not tab._restoring_scroll)
                before=(tab.state.reference,list(tab.state.history))
                with patch.object(window,'update_navigation',wraps=window.update_navigation) as navigation,patch.object(window.library,'resource',wraps=window.library.resource) as metadata:
                    adjustment=tab.scroll.get_vadjustment()
                    maximum=adjustment.get_upper()-adjustment.get_page_size();self.assertGreater(maximum,0)
                    for fraction in (.2,.4,.6,.3):adjustment.set_value(maximum*fraction)
                    spin(duration=.4)
                    navigation.assert_not_called();metadata.assert_not_called()
                    self.assertAlmostEqual(tab.state.scroll,.3,places=2)
                    self.assertEqual((tab.state.reference,tab.state.history),before)
                    self.assertAlmostEqual(SessionStore(root/'session.json').load().tabs[0].scroll,.3,places=2)
                    tab.select_verse('Gen.1.2');self.assertTrue(navigation.called)
            finally:window.close()
