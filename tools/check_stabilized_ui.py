"""Actual GTK/native pointer evidence for #53–55 and immersive focus/controls."""
import argparse
from pathlib import Path
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('prefix')
    parser.add_argument('--require-packaged',action='store_true');args=parser.parse_args()
    import bible
    if args.require_packaged:assert bible.__file__.startswith('/app/'),bible.__file__
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_comparison_surfaces import point
    from PIL import ImageGrab
    app=Application();app.register();native=X11Input()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    def buttons(widget):
        if isinstance(widget,Gtk.MenuButton) and widget.get_label()=='Aa' and widget.get_mapped():yield widget
        child=widget.get_first_child()
        while child:
            yield from buttons(child);child=child.get_next_sibling()
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline GUI verification')),SystemStyleOverride() as system:
        w=Window(app,Library(Path(args.profile)/'translations'));w.set_default_size(1440,950);w.present()
        try:
            w.appearance.reset();tab=w.active_tab;tab.navigate('FreSegond1910','Gen.1.25')
            tab.state.commentary='MHC';tab.state.comparison=None;w.sync_comparison()
            w.study_button.set_active(True);w.study.refresh()
            def settled():return not tab._restoring_scroll and not w.study._positioning
            spin(settled,duration=.3)
            assert list(buttons(w))==[w.appearance_button]
            assert not hasattr(w.study,'appearance_button')
            assert w.appearance_button.get_next_sibling() is w.menu
            for mode,high in [('day',False),('night',False),('day',True)]:
                system.set(dark=mode=='night',high=high);w.appearance.update('mode',mode);spin(settled,duration=.3)
                native.move_at(w,2,2);image=ImageGrab.grab()
                samples=[(w.study.header,3,3),(w.study,3,w.study.header.get_height()+3),(w.study.text,3,80)]
                colors=[image.getpixel(point(native,widget,x,y))[:3] for widget,x,y in samples]
                assert all(max(abs(a-b) for a,b in zip(colors[0],value))<=1 for value in colors),colors
                image.save(args.prefix+'-drawer-'+mode+('-contrast' if high else '')+'.png')
                print('DRAWER',mode,high,'uniform RGB',colors[0],flush=True)
            system.set(dark=False,high=False);w.appearance.update('mode','day');spin(settled)
            native.click(w.appearance_button);native.click(w.appearance.larger)
            assert w.preferences.value.size==15
            native.click(w.appearance.smaller);native.key('Escape');assert not w.appearance.get_visible()
            for shown in (False,True):
                w.study_button.set_active(shown);spin(settled,duration=.3)
                found,rect=tab.following.compute_bounds(tab.reading_overlay);assert found
                text_end=tab.scroll.get_width()-tab.text.get_right_margin()
                assert 4<=rect.origin.x-text_end<=16
                assert rect.origin.y+rect.size.height/2>tab.reading_overlay.get_height()*.65
                assert abs(rect.size.width-rect.size.height)<=1
                native.move_at(w,2,2)
                ImageGrab.grab().save(args.prefix+('-open' if shown else '-closed')+'.png')
            native.key('F11');spin(lambda:w.immersion is not None and w.immersion.layout_ready)
            r=w.immersion;page=r.views[0]
            native.click_at(page,100,100);spin()
            assert not w.get_focus_visible(),page.get_state_flags()
            assert list(buttons(w))==[r.aa]
            spin(lambda:r.layout_ready,duration=.3)
            assert page.get_buffer().get_char_count()>0
            ImageGrab.grab().save(args.prefix+'-immersion-pointer.png')
            native.key('F10');assert w.get_focus_visible() and w.get_focus() is r.leave_button
            native.click(r.aa);spin();r.hide_controls()
            assert w.appearance.get_visible() and r.top.get_reveal_child()
            native.key('Escape');assert not w.appearance.get_visible() and w.immersion is r
            native.key('F10');r.hide_controls();assert r.top.get_reveal_child()
            spin(lambda:r.layout_ready,duration=.3)
            assert page.get_buffer().get_char_count()>0
            ImageGrab.grab().save(args.prefix+'-immersion-keyboard.png')
            native.key('Escape');assert w.immersion is None
            assert list(buttons(w))==[w.appearance_button]
            print('PASS: uniform native sidebar/header, single shared Aa, lower round safe-margin arrows, '
                  'pointer vs keyboard focus and revealed immersive controls/popover lifecycle',flush=True)
        finally:w.close();native.close()


if __name__=='__main__':main()
