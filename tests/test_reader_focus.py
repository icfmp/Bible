"""Actual GTK pixels and unchanged reading across native keyboard focus.

Xvfb tests focus drawing; real Mutter/Wayland Alt+Tab is verified separately.
No compositor, Pillow or application dependency is introduced by these tests.
"""
import ctypes
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture,spin
from tests.test_appearance import SystemStyleOverride
from tools.check_alpha_ui import X11Input


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires X11 GTK')
class ReaderFocusTests(unittest.TestCase):
    def test_focus_mark_pixels_native_keyboard_selection_and_geometry(self):
        from bible.ui import Application,Window,Library,Gtk
        from bible.reading_style import PALETTES
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory,SystemStyleOverride() as system:
            installed_fixture(directory,long_text=True)
            w=Window(app,Library(Path(directory)/'translations'));w.set_default_size(720,500);w.present()
            native=X11Input();x=native.x11;pointer=ctypes.c_void_p;ulong=ctypes.c_ulong
            x.XGetImage.argtypes=[pointer,ulong,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint,ulong,ctypes.c_int];x.XGetImage.restype=pointer
            x.XGetPixel.argtypes=[pointer,ctypes.c_int,ctypes.c_int];x.XGetPixel.restype=ulong
            x.XDestroyImage.argtypes=[pointer];x.XDestroyImage.restype=ctypes.c_int
            try:
                tab=w.active_tab;view=tab.text;spin(lambda:not tab._restoring_scroll,duration=.3)
                native.activate(w)
                def pixel(px,py):
                    found,bounds=view.compute_bounds(w);self.assertTrue(found)
                    rx,ry,child=ctypes.c_int(),ctypes.c_int(),ulong()
                    self.assertTrue(x.XTranslateCoordinates(native.display,w.get_surface().get_xid(),x.XDefaultRootWindow(native.display),0,0,ctypes.byref(rx),ctypes.byref(ry),ctypes.byref(child)))
                    scale=view.get_scale_factor();dx,dy=w.get_surface_transform()
                    sx=rx.value+round((dx+bounds.origin.x+px)*scale);sy=ry.value+round((dy+bounds.origin.y+py)*scale)
                    image=x.XGetImage(native.display,x.XDefaultRootWindow(native.display),sx,sy,1,1,ulong(-1),2);self.assertTrue(image)
                    try:value=x.XGetPixel(image,0,0)
                    finally:x.XDestroyImage(image)
                    return tuple((value>>shift)&255 for shift in (16,8,0))
                def rgb(value):return tuple(int(value[i:i+2],16) for i in (1,3,5))
                for dark,high in ((False,False),(True,False),(False,True),(True,True)):
                    system.set(dark=dark,high=high);spin(duration=.25)
                    for rtl in (False,True):
                        view.set_direction(Gtk.TextDirection.RTL if rtl else Gtk.TextDirection.LTR)
                        view.grab_focus();w.set_focus_visible(False);spin(duration=.2)
                        # These are explicit focus-state unit transitions. The native
                        # Tab event below must retain keyboard focus-visible state.
                        buffer=view.get_buffer();start=tab._marker_ends['Gen.1.1']
                        buffer.select_range(buffer.get_iter_at_offset(start+3),buffer.get_iter_at_offset(start+13))
                        selection=buffer.get_text(*buffer.get_selection_bounds(),False)
                        before=(view.get_width(),view.get_height(),view.get_visible_rect().y,tab.state.reference,tab.position_anchor(start+7))
                        w.set_focus_visible(True);spin(duration=.2)
                        self.assertTrue(view.has_visible_focus());self.assertTrue(view.get_focusable())
                        bg,_,link,_,_=PALETTES[w.reading_style.palette]
                        edge=view.get_width()-1 if rtl else 1;other=1 if rtl else view.get_width()-1
                        self.assertEqual(pixel(edge,view.get_height()/2),rgb(link))
                        # The rest of the former rectangle must remain background.
                        for px,py in ((other,view.get_height()/2),(20,1),(20,view.get_height()-2)):
                            self.assertEqual(pixel(px,py),rgb(bg))
                        self.assertEqual((view.get_width(),view.get_height(),view.get_visible_rect().y,tab.state.reference,tab.position_anchor(start+7)),before)
                        self.assertEqual(buffer.get_text(*buffer.get_selection_bounds(),False),selection)
                        native.key('Tab');self.assertTrue(w.get_focus_visible())
                print('PASS: native GTK focus pixels, no full rectangle, LTR/RTL, light/dark/high contrast; selection and canonical/intra-verse anchors preserved',flush=True)
            finally:w.close();native.close()
