"""Exercise real X11 input against GTK using sentinel SWORD test data.

Run with dbus-run-session and xvfb-run; requires libXtst. This automated check
is distinct from manual validation on the client's GNOME desktop.
"""
import ctypes
import os
from pathlib import Path
import tempfile

import gi

gi.require_version('GdkX11', '4.0')
from gi.repository import GdkX11  # noqa: F401 — register X11 surface methods

from tests.test_ui import installed_fixture, spin
from bible.ui import Application, Gtk, Library, Window


class X11Input:
    def __init__(self):
        self.x11 = ctypes.CDLL('libX11.so.6')
        self.xtest = ctypes.CDLL('libXtst.so.6')
        pointer = ctypes.c_void_p
        ulong = ctypes.c_ulong
        integer = ctypes.c_int
        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x11.XOpenDisplay.restype = pointer
        self.x11.XCloseDisplay.argtypes = [pointer]
        self.x11.XDefaultRootWindow.argtypes = [pointer]
        self.x11.XDefaultRootWindow.restype = ulong
        self.x11.XTranslateCoordinates.argtypes = [
            pointer, ulong, ulong, integer, integer, ctypes.POINTER(integer),
            ctypes.POINTER(integer), ctypes.POINTER(ulong)]
        self.x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.x11.XStringToKeysym.restype = ulong
        self.x11.XKeysymToKeycode.argtypes = [pointer, ulong]
        self.x11.XKeysymToKeycode.restype = ctypes.c_ubyte
        self.x11.XFlush.argtypes = [pointer]
        self.x11.XSetInputFocus.argtypes = [pointer, ulong, integer, ulong]
        self.xtest.XTestFakeMotionEvent.argtypes = [pointer, integer, integer, integer, ulong]
        self.xtest.XTestFakeButtonEvent.argtypes = [pointer, ctypes.c_uint, integer, ulong]
        self.xtest.XTestFakeKeyEvent.argtypes = [pointer, ctypes.c_uint, integer, ulong]
        self.display = self.x11.XOpenDisplay(os.environ['DISPLAY'].encode())
        if not self.display:
            raise RuntimeError('Requires an X11 display (use xvfb-run)')

    def activate(self, window):
        """Supply the window manager's focus handoff in a bare Xvfb session."""
        assert window.get_mapped()
        self.x11.XSetInputFocus(self.display, window.get_surface().get_xid(), 2, 0)
        self.x11.XFlush(self.display)
        spin(lambda: window.is_active())

    def key(self, name):
        symbol = self.x11.XStringToKeysym(name.encode())
        code = self.x11.XKeysymToKeycode(self.display, symbol)
        assert code, name
        self.xtest.XTestFakeKeyEvent(self.display, code, True, 0)
        self.xtest.XTestFakeKeyEvent(self.display, code, False, 0)
        self.x11.XFlush(self.display)
        spin(duration=0.15)

    def click(self, widget):
        self.click_at(widget,widget.get_width()/2,widget.get_height()/2)

    def move_at(self, widget, local_x, local_y):
        native = widget.get_native()
        found, bounds = widget.compute_bounds(native)
        assert found and widget.get_mapped()
        dx, dy = native.get_surface_transform()
        root_x, root_y, child = ctypes.c_int(), ctypes.c_int(), ctypes.c_ulong()
        assert self.x11.XTranslateCoordinates(
            self.display, native.get_surface().get_xid(),
            self.x11.XDefaultRootWindow(self.display), 0, 0,
            ctypes.byref(root_x), ctypes.byref(root_y), ctypes.byref(child))
        x = int(root_x.value + dx + bounds.origin.x + local_x)
        y = int(root_y.value + dy + bounds.origin.y + local_y)
        self.xtest.XTestFakeMotionEvent(self.display, -1, x, y, 0)
        self.x11.XFlush(self.display)

    def click_at(self, widget, local_x, local_y):
        self.move_at(widget,local_x,local_y)
        self.xtest.XTestFakeButtonEvent(self.display, 1, True, 0)
        self.xtest.XTestFakeButtonEvent(self.display, 1, False, 0)
        self.x11.XFlush(self.display)
        spin(duration=0.2)

    def wheel(self,widget,steps):
        self.move_at(widget,widget.get_width()/2,widget.get_height()/2)
        spin(duration=.1)
        for _ in range(abs(steps)):
            button=5 if steps>0 else 4
            self.xtest.XTestFakeButtonEvent(self.display,button,True,0)
            self.xtest.XTestFakeButtonEvent(self.display,button,False,0)
        self.x11.XFlush(self.display);spin(duration=.2)

    def drag_at(self,widget,x,start,end,observed=None):
        self.move_at(widget,x,start);spin(duration=.15)
        self.xtest.XTestFakeButtonEvent(self.display,1,True,0);self.x11.XFlush(self.display)
        spin(duration=.1)
        try:
            for index in range(1,11):
                self.move_at(widget,x,start+(end-start)*index/10)
                spin(duration=.15)
                if observed:observed()
        finally:
            self.xtest.XTestFakeButtonEvent(self.display,1,False,0);self.x11.XFlush(self.display)
            spin(duration=.2)

    def close(self):
        self.x11.XCloseDisplay(self.display)


def main():
    app = Application()
    app.register()
    Gtk.Settings.get_default().set_property('gtk-enable-animations', False)
    inputs = X11Input()
    try:
        with tempfile.TemporaryDirectory() as directory:
            entries = [('Gen.1.1', 'FIRST TEST DATA'), ('Exod.1.1', 'SECOND BOOK TEST DATA')]
            entries += [(f'1Cor.{chapter}.1', f'CHAPTER {chapter} TEST DATA') for chapter in range(1, 17)]
            installed_fixture(directory, entries=entries)
            window = Window(app, Library(Path(directory) / 'translations'))
            try:
                window.present()
                spin(duration=0.3)
                window.choose_passage()
                spin(duration=0.4)
                nav = window.navigation
                inputs.click(nav.book_rows['1Cor'])
                assert window.active_tab.state.reference == '1Cor.1.1'
                inputs.click(nav.chapter_buttons[15])
                assert window.active_tab.state.reference == '1Cor.15.1'
                nav.chapter_buttons[16].grab_focus()
                inputs.key('space')
                assert window.active_tab.state.reference == '1Cor.16.1'
                nav.book_rows['Gen'].grab_focus()
                inputs.key('Return')
                assert window.active_tab.state.reference == 'Gen.1.1'
                nav.book_rows['Gen'].grab_focus()
                inputs.key('Down')
                assert window.active_tab.state.reference == 'Exod.1.1'
                nav.search.grab_focus()
                for letter in 'cor':
                    inputs.key(letter)
                spin(lambda: list(nav.book_rows) == ['1Cor'])
                assert window.active_tab.state.reference == 'Exod.1.1'
                inputs.click(nav.close_button)
                assert not nav.get_visible()
                second = window.new_tab()
                # A newly selected page is mapped before its overlay buttons
                # receive their first allocation. Do not click a zero-width
                # target at an obsolete position after the split-header layout.
                spin(lambda:second.following.get_mapped() and second.following.get_width()>0,duration=.05)
                inputs.click(second.following)
                assert second.state.reference == '1Cor.1.1'
                assert window.tabs()[0].state.reference == 'Exod.1.1'
                # Exercise Aa with actual X11 pointer/key events as well.
                inputs.click(window.appearance_button)
                aa=window.appearance
                inputs.click(aa.larger)
                assert window.preferences.value.size == 15
                aa.smaller.grab_focus();inputs.key('space')
                assert window.preferences.value.size == 14
                aa.fonts['DejaVu Sans'].grab_focus();inputs.key('space')
                assert window.preferences.value.font == 'DejaVu Sans'
                inputs.click(aa.palettes['paper'])
                assert window.preferences.value.day_palette == 'paper'
                assert window.preferences.value.mode == 'system'
                inputs.click(aa.mode);inputs.key('End');inputs.key('Return')
                assert window.preferences.value.mode == 'night'
                aa.verse_numbers.grab_focus();inputs.key('space')
                assert not window.preferences.value.verse_numbers
                inputs.key('Escape')
                assert not aa.get_visible()
                assert second.state.reference == '1Cor.1.1'
                print('PASS: native X11 book/chapter clicks, chapter Space, book Return/Down, '
                      'typed search, close, overlay, independent tabs and Aa mouse/keyboard controls', flush=True)
            finally:
                window.close()
    finally:
        inputs.close()


if __name__ == '__main__':
    main()
