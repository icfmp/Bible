"""Real GTK pixels for all comparison palettes; disposable TEST profile only."""
import argparse
import ctypes
from pathlib import Path
from unittest.mock import patch
from PIL import ImageGrab
from bible.ui import Application,Window,Library,Gtk
from bible.reading_style import PALETTES
from tests.test_ui import spin
from tests.test_appearance import SystemStyleOverride
from tools.check_alpha_ui import X11Input


def point(native,widget,x,y):
    surface=widget.get_native();ok,bounds=widget.compute_bounds(surface);assert ok
    dx,dy=surface.get_surface_transform();rx,ry,child=ctypes.c_int(),ctypes.c_int(),ctypes.c_ulong()
    assert native.x11.XTranslateCoordinates(native.display,surface.get_surface().get_xid(),native.x11.XDefaultRootWindow(native.display),
        0,0,ctypes.byref(rx),ctypes.byref(ry),ctypes.byref(child))
    return int(rx.value+dx+bounds.origin.x+x),int(ry.value+dy+bounds.origin.y+y)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('prefix');args=parser.parse_args()
    app=Application.get_default() or Application();app.register();native=X11Input()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline test')),SystemStyleOverride() as system:
        w=Window(app,Library(Path(args.profile)/'translations'));w.set_default_size(1600,950);w.present()
        try:
            w.appearance.reset();tab=w.active_tab;tab.navigate('FreSegond1910','Gen.1.15')
            tab.state.comparison='FreLSN1872';tab.state.commentary='MHC';w.sync_comparison()
            spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False))
            tab.reveal_comparison('Gen.1.15',settle=True)
            spin(lambda:not getattr(tab,'_comparison_positioning',False),duration=.2)
            buffer=tab.comparison_text.get_buffer();body=tab._comparison_markers['Gen.1.15']
            buffer.select_range(buffer.get_iter_at_offset(body+3),buffer.get_iter_at_offset(body+21))
            def selection():return tab._comparison_document.copy(*(i.get_offset() for i in buffer.get_selection_bounds()))
            selected=selection();reference=tab.state.reference
            def check(label):
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False)
                     and (not w.split.get_show_sidebar() or not w.study._positioning),duration=.3)
                native.move_at(w,2,2);image=ImageGrab.grab();image.save(args.prefix+'-'+label+'.png')
                palette=w.reading_style.palette;bg=PALETTES[palette][0]
                expected=tuple(int(bg[i:i+2],16) for i in (1,3,5))
                samples=[(tab.reading_overlay,3,3),(tab.comparison_box,3,3),
                         (tab.comparison_scroll,3,tab.comparison_scroll.get_height()/2),
                         (tab.comparison_overlay,3,tab.comparison_overlay.get_height()-3),
                         (tab.comparison_text,3,80)]
                if tab.reading_layout.get_orientation()==Gtk.Orientation.HORIZONTAL:
                    samples.append((tab.reading_layout,tab.reading_overlay.get_width()+8,100))
                for widget,x,y in samples:
                    actual=image.getpixel(point(native,widget,x,y))[:3]
                    assert max(abs(a-b) for a,b in zip(actual,expected))<=1,(label,type(widget).__name__,actual,expected)
                assert abs(tab.reading_overlay.get_width()-tab.comparison_box.get_width())<=1
                print('SURFACE',label,palette,'RGB',expected,'widths',tab.reading_overlay.get_width(),tab.comparison_box.get_width(),flush=True)
            for palette,mode in [('white','day'),('paper','day'),('dark','night'),('black','night'),('contrast-day','day'),('contrast-night','night')]:
                system.set(dark=mode=='night',high=palette.startswith('contrast'))
                if not palette.startswith('contrast'):w.appearance.update('day_palette' if mode=='day' else 'night_palette',palette)
                w.appearance.update('mode',mode)
                for shown in (False,True):
                    w.study_button.set_active(shown);check(palette+('-study' if shown else '-plain'))
                    assert selection()==selected and tab.state.reference==reference
            system.set(dark=False,high=False);w.appearance.update('mode','day');w.appearance.update('day_palette','white')
            for width in (1200,1600):
                w.set_default_size(width,950);check('resize-'+str(width))
                assert selection()==selected
            tab.state.comparison='MissingForSurfaceTest';tab.refresh_comparison();check('unavailable-empty')
            assert tab.comparison_status.get_text() and not buffer.props.text
            tab.state.comparison='FreLSN1872';tab.refresh_comparison();check('restored')
            assert buffer.props.text,(tab.comparison_status.get_text(),tab.state.reference,tab._comparison_name)
            print('PASS: viewport/margins/gutter/empty space pixels, all palettes and emulated high contrast, '
                  'study open/closed, resize, empty/error and restored content; equal widths, selection and anchor',flush=True)
        finally:w.close();native.close()


if __name__=='__main__':main()
