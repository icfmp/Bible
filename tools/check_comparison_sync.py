"""Actual offline resources and native X11 comparison input for #36."""
import argparse
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from bible.ui import Application, Window, Library, Gtk
from bible.reference_resolution import resolve


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('--screenshot-prefix')
    args=parser.parse_args()
    app=Application();app.register();native=X11Input()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline test')):
        window=Window(app,Library(Path(args.profile)/'translations'))
        window.set_default_size(1440,1000);window.present()
        try:
            tab=window.active_tab;tab.navigate('FreSegond1910','Gen.1.1')
            tab.state.comparison='FreLSN1872';window.sync_comparison()
            window.appearance.update('size',14);window.appearance.update('line_spacing','very-airy')
            window.study_button.set_active(False)
            spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False),duration=.4)
            before=len(tab.state.history)
            for side in ['primary','comparison','primary','comparison']:
                view=tab.text if side=='primary' else tab.comparison_text
                native.wheel(view,6)
                spin(lambda:not tab.comparison_sync.pending and not getattr(tab,'_comparison_positioning',False),duration=.4)
                primary,comparison=tab.visible_reference(),tab.comparison_visible_reference()
                if side=='primary':expected=resolve(primary,tab.reader.versification,tab._comparison_reader).start;assert comparison==expected,(side,primary,comparison,expected)
                else:
                    expected=resolve(comparison,tab._comparison_reader.versification,tab.reader).start
                    assert tab.state.reference==expected,(side,primary,comparison,expected)
                    location=tab.text.get_iter_location(tab.text.get_buffer().get_iter_at_offset(tab._verse_offsets[expected]))
                    visible=tab.text.get_visible_rect()
                    # At a chapter's end the native adjustment can clamp while
                    # the corresponding verse is already fully on screen.
                    assert visible.y<=location.y<visible.y+visible.height
                print(side,primary,comparison,flush=True)
            assert len(tab.state.history)==before
            assert abs(tab.reading_overlay.get_width()-tab.comparison_box.get_width())<=1
            for view in [tab.text,tab.comparison_text]:
                number=view.get_buffer().get_tag_table().lookup('verse-number')
                assert number.props.scale==.60 and number.props.rise>0
                assert view.get_pixels_inside_wrap()==16
            # A native selection survives a shared reflow without text changes.
            buffer=tab.comparison_text.get_buffer();first=next(iter(tab._comparison_markers.values()))
            buffer.select_range(buffer.get_iter_at_offset(first+1),buffer.get_iter_at_offset(first+8))
            selected=buffer.get_text(*buffer.get_selection_bounds(),False)
            window.appearance.update('font','DejaVu Sans')
            spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False))
            assert buffer.get_text(*buffer.get_selection_bounds(),False)==selected
            buffer.place_cursor(buffer.get_start_iter())
            if args.screenshot_prefix:
                from PIL import ImageGrab
                ImageGrab.grab().save(args.screenshot_prefix+'-light.png')
                window.appearance.update('mode','night');spin(duration=.3)
                ImageGrab.grab().save(args.screenshot_prefix+'-dark.png')
            print('PASS: real offline bidirectional corresponding verse scrolling; equal widths; shared '
                  'rendering; exact selected text retained through reflow; no history spam',flush=True)
        finally:window.close();native.close()


if __name__=='__main__':main()
