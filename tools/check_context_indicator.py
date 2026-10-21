"""Real offline dotted commentary coverage; TEST profile only, no personal data."""
import argparse
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import spin
from bible.ui import Application,Window,Library,Gtk
from bible.reference_resolution import resolve


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('prefix');args=parser.parse_args()
    from PIL import ImageGrab
    app=Application();app.register();Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline test')):
        window=Window(app,Library(Path(args.profile)/'translations'));window.set_default_size(1600,950);window.present()
        try:
            tab=window.active_tab;window.appearance.reset();window.appearance.update('mode','day')
            tab.navigate('FreSegond1910','Gen.1.1');tab.state.comparison='FreLSN1872';window.sync_comparison()
            tab.state.commentary='MHC';window.study_button.set_active(True);window.study.refresh()
            spin(lambda:not tab._restoring_scroll and not window.study._positioning and not getattr(tab,'_comparison_positioning',False),duration=.3)
            assert tab._study_coverage[1:]==('Gen.1.1','Gen.1.2'),tab._study_coverage
            assert len(tab.text.study_ranges)==2 and len(tab.comparison_text.study_ranges)==2
            assert tab.text.indicator_segments() and tab.comparison_text.indicator_segments()
            before=tab.text.get_buffer().props.text
            ImageGrab.grab().save(args.prefix+'-light.png')
            window.appearance.update('mode','night');spin(duration=.2)
            ImageGrab.grab().save(args.prefix+'-dark.png')
            assert tab.text.get_buffer().props.text==before
            tab.navigate('FreSegond1910','Ps.3.2')
            spin(lambda:not tab._restoring_scroll and not window.study._positioning,duration=.2)
            section=window.study.reader.index.sections[window.study.current_position]
            expected=resolve(section.start,window.study.reader.versification,tab.reader,require_entry=False).start
            assert tab._study_coverage[1]==expected
            assert tab.text.study_ranges
            window.study_button.set_active(False);assert not tab.text.study_ranges
            window.study_button.set_active(True);assert tab.text.study_ranges
            tab.navigate('FreSegond1910','Gen.1.1');spin(lambda:not tab._restoring_scroll and not window.study._positioning)
            from tests.test_appearance import SystemStyleOverride
            with SystemStyleOverride() as override:
                window.appearance.update('mode','system');override.set(dark=False,high=True);spin(duration=.2)
                assert tab.text._reading_palette=='contrast-day'
                ImageGrab.grab().save(args.prefix+'-high-contrast-emulated.png')
            if hasattr(window,'highlights'):
                tab.select_verse('Gen.1.1');window.mark_highlight('yellow');spin(duration=.2)
                ranges=tab.text.study_ranges
                ImageGrab.grab().save(args.prefix+'-personal-overlap-candidate.png')
                window.appearance.show_highlights.set_active(False)
                assert tab.text.study_ranges==ranges and tab.text.indicator_segments()
            assert window.enter_immersion('bible')
            spin(lambda:window.immersion.layout_ready)
            assert any(getattr(v,'study_ranges',()) for v in window.immersion.views)
            ImageGrab.grab().save(args.prefix+'-immersion.png')
            window.leave_immersion()
            print('PASS: actual MHC Genesis 1:1–2 coverage in both Bibles, mapped Psalm case, '
                  'hide/reopen, unchanged text, emulated high contrast and paginated coverage; '
                  'personal overlap only when executing the PR40 candidate',flush=True)
        finally:window.close()


if __name__=='__main__':main()
