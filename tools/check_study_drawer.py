"""Real offline GTK drawer capture/input check; use only a disposable TEST profile."""
import argparse
import hashlib
from pathlib import Path
import time
from unittest.mock import patch
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from bible.ui import Application, Window, Library, Gtk
from bible.reference_resolution import resolve


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('prefix')
    parser.add_argument('--frames-directory');args=parser.parse_args()
    from PIL import ImageGrab
    app=Application();app.register();native=X11Input()
    settings=Gtk.Settings.get_default();settings.set_property('gtk-enable-animations',False)
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline test')):
        window=Window(app,Library(Path(args.profile)/'translations'));window.set_default_size(1440,900);window.present()
        try:
            window.appearance.reset();window.appearance.update('mode','day')
            tab=window.active_tab;tab.state.comparison=None;tab.refresh_comparison()
            tab.navigate('FreSegond1910','Gen.1.25');tab.state.commentary='MHC'
            window.study_button.set_active(True);window.study.refresh()
            spin(lambda:not tab._restoring_scroll and not window.study._positioning,duration=.3)
            study=window.study
            _,sidebar=study.compute_bounds(window);_,bible=tab.compute_bounds(window)
            assert sidebar.origin.x+sidebar.size.width<=bible.origin.x+1
            assert study.header.get_height()==window.header.get_height()
            original=study.entry_text
            buffer=study.text.get_buffer()
            visible=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),False)
            assert '* 24 *' not in visible and '* it was *' not in visible
            assert '<hi' not in visible and 'The Creation.' in visible
            native.move_at(window,2,2);spin(duration=.2)
            ImageGrab.grab().save(args.prefix+'-light.png')
            native.click(study.appearance_button);native.click(study.appearance.larger)
            assert window.preferences.value.size==15
            native.click(study.appearance.smaller);native.click(study.appearance_button)
            assert not study.appearance.get_visible();assert study.entry_text==original
            native.click(study.more);native.click(study.info)
            assert study.metadata.get_text() and study.info.get_popover().get_visible()
            native.click_at(tab.text,tab.text.get_width()-8,300)
            assert not study.more.get_popover().get_visible() and not study.info.get_popover().get_visible()
            history=len(tab.state.history)
            for view in [tab.text,study.text]:
                native.wheel(view,3)
                spin(lambda:not study._positioning and not tab._restoring_scroll,duration=.3)
            section=study.reader.index.sections[study.current_position]
            start=resolve(section.start,study.reader.versification,tab.reader).start
            end=resolve(section.end,study.reader.versification,tab.reader).end
            assert tab.reader.key(start).getIndex()<=tab.reader.key(tab.state.reference).getIndex()<=tab.reader.key(end).getIndex()
            assert len(tab.state.history)==history
            reference=tab.state.reference;position=study.current_position
            native.click(study.immersive_button)
            spin(lambda:window.immersion is not None and window.immersion.layout_ready,duration=.2)
            native.key('Escape');spin(lambda:window.immersion is None and not study._positioning)
            assert tab.state.reference==reference and study.current_position==position
            window.appearance.update('mode','night');spin(duration=.3)
            native.move_at(window,2,2);ImageGrab.grab().save(args.prefix+'-dark.png')
            window.appearance.update('size',28);spin(lambda:not study._positioning and not tab._restoring_scroll)
            ImageGrab.grab().save(args.prefix+'-large.png')
            window.appearance.update('size',14);window.appearance.update('mode','day')
            if args.frames_directory:
                directory=Path(args.frames_directory);directory.mkdir(parents=True,exist_ok=True)
                settings.set_property('gtk-enable-animations',True)
                window.study_button.set_active(False);spin(duration=.3)
                widths=[];index=0;started=time.monotonic()
                for shown in [True,False,True]:
                    window.study_button.set_active(shown)
                    for _ in range(12):
                        spin(duration=.04)
                        widths.append(tab.get_width())
                        ImageGrab.grab().save(directory/f'drawer-{index:03d}.png');index+=1
                assert len(set(widths))>2,'Native slide transition was not observed'
                print('animation_frames',index,'seconds',round(time.monotonic()-started,3),flush=True)
            settings.set_property('gtk-enable-animations',False)
            for shown in [False,True,False,True]:
                window.study_button.set_active(shown);spin(duration=.08)
                assert window.split.get_show_sidebar()==shown
                _,bounds=tab.compute_bounds(window)
                # Native clipping can retain a mapped sidebar widget. Verify
                # the public state and completed allocation, not that detail.
                assert (bounds.origin.x>100) if shown else (bounds.origin.x<2)
            window.set_default_size(360,700)
            spin(lambda:window.split.get_collapsed() and window.get_width()<380,duration=.3)
            assert study.get_width()<=window.get_width()
            native.move_at(window,2,2);ImageGrab.grab().save(args.prefix+'-narrow.png')
            print('PASS: full-height left drawer, aligned headers, compact actions, shared Aa, '
                  'offline source/conditions, bidirectional following, no history spam, narrow adaptation, '
                  'rapid toggles and disabled animations',flush=True)
            print('MHC_entry_sha256',hashlib.sha256(original.encode()).hexdigest(),
                  'verified_sword_plain_markers',original.count('*'),flush=True)
        finally:window.close();native.close()


if __name__=='__main__':main()
