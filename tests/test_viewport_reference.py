"""Keep first-visible semantics while avoiding full offscreen GTK layout scans."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
class ViewportReferenceTests(unittest.TestCase):
    def test_wrapped_and_partial_lines_match_existing_reference_semantics_in_both_directions(self):
        from bible.ui import Application,Window,Library,Gtk
        for rtl in (False,True):
            with self.subTest(rtl=rtl),tempfile.TemporaryDirectory() as directory:
                words='אבג דהו זחט יכל מנס עפר צקש ת ' if rtl else 'TEST DATA ONLY long words '
                installed_fixture(directory,entries=[(f'Gen.1.{v}',words*(1 if v%4==0 else 20+v)) for v in range(1,32)])
                app=Application.get_default() or Application();app.register()
                window=Window(app,Library(Path(directory)/'translations'));window.present();spin()
                try:
                    tab=window.active_tab;view=tab.text;buffer=view.get_buffer()
                    if rtl:view.set_direction(Gtk.TextDirection.RTL);view.set_justification(Gtk.Justification.RIGHT)
                    for width in (950,560):
                        window.set_default_size(width,600)
                        spin(lambda:not tab._restoring_scroll and not tab._adapt_id,duration=.3)
                        # Validate test geometry before comparing both queries.
                        for offset in tab._verse_offsets.values():view.get_iter_location(buffer.get_iter_at_offset(offset))
                        spin(lambda:not tab._restoring_scroll and not tab._adapt_id,duration=.2)
                        adj=tab.scroll.get_vadjustment()
                        for fraction in (0,.001,.03,.1,.24,.41,.6,.79,.95,1):
                            adj.set_value((adj.get_upper()-adj.get_page_size())*fraction);spin(duration=.03)
                            rect=view.get_visible_rect()
                            starts=[(ref,view.get_iter_location(buffer.get_iter_at_offset(offset)).y) for ref,offset in tab._verse_offsets.items()]
                            visible=[ref for ref,y in starts if rect.y<=y<rect.y+rect.height]
                            preceding=[ref for ref,y in starts if y<=rect.y]
                            expected=visible[0] if visible else preceding[-1] if preceding else starts[0][0]
                            with patch.object(view,'get_iter_location',wraps=view.get_iter_location) as locations:
                                self.assertEqual(tab.visible_reference(),expected,(rtl,width,fraction))
                                self.assertLess(locations.call_count,10,'Offscreen verse positions should not be scanned')
                finally:window.close()
