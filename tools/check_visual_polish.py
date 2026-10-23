"""Actual GTK captures for #64/#66/#69, using a disposable real-resource profile.

Can also run against the pre-change source via PYTHONPATH, for matched captures.
No user profile must be supplied: reading preferences are reset here.
"""
import argparse
import json
from pathlib import Path
from PIL import ImageGrab
from bible.ui import Application, Window, Library, Gtk
from tests.test_ui import spin


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('output');parser.add_argument('--phase',default='after');args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    from bible.i18n import LANGUAGE
    app=Application.get_default() or Application();app.register()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    w=Window(app,Library(Path(args.profile)/'translations'));w.present()
    report=[]
    def settle():spin(lambda:not w.active_tab._restoring_scroll and not getattr(w.active_tab,'_comparison_positioning',False),duration=.35)
    def capture(name):
        settle();scale=w.get_scale_factor()
        path=out/f'{args.phase}-{LANGUAGE}-{theme}-{name}.png'
        ImageGrab.grab(bbox=(0,0,w.get_width()*scale,w.get_height()*scale)).save(path)
        report.append(dict(file=path.name,width=w.get_width(),height=w.get_height(),scale=scale))
    try:
        tab=w.active_tab;w.study_button.set_active(False);tab.state.comparison=None
        assert tab.navigate('FreSegond1910','Gen.5.7')
        for theme,mode in [('light','day'),('dark','night')]:
            w.set_default_size(1200,850);w.appearance.reset();w.appearance.update('mode',mode);w.sync_comparison();settle()
            w.study_button.set_active(False);settle()
            capture('reader')
            w.show_appearance();capture('appearance');w.appearance.popdown()
            tab.state.comparison='ebible~frajnd2024eb';w.sync_comparison();capture('comparison')
            if hasattr(w,'compared_version'):
                w.compared_version.popup();capture('comparison-chooser');w.compared_version.popdown()
            w.study_button.set_active(True);capture('comparison-study');w.study_button.set_active(False)
            tab.state.comparison=None;w.sync_comparison();settle()
            buffer=tab.text.get_buffer();first=tab._marker_ends['Gen.5.7'];last=tab._verse_ranges['Gen.5.10'][1]
            buffer.select_range(buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(last))
            actions=w.passage_actions;actions.capture(tab.text,lambda:actions.ordinary(tab),None)
            capture('selection');actions.dismiss()
            w.set_default_size(360,600);settle();capture('small')
            w.show_appearance();capture('small-appearance');w.appearance.popdown()
            if hasattr(w,'primary_version'):
                assert w.reader_controls.get_width()<=tab.reading_overlay.get_width()
                assert w.appearance.get_width()<=w.get_width()
            buffer.select_range(buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(last))
            actions.capture(tab.text,lambda:actions.ordinary(tab),None);capture('small-selection');actions.dismiss()
            if hasattr(w,'primary_version'):assert actions.bar.get_width()<=tab.reading_overlay.get_width()
            tab.state.comparison='ebible~frajnd2024eb';w.sync_comparison();capture('small-comparison')
            tab.state.comparison=None;w.sync_comparison()
        from tests.test_appearance import SystemStyleOverride
        with SystemStyleOverride() as system:
            w.set_default_size(1200,850);w.study_button.set_active(False);w.appearance.update('mode','system')
            for dark in (False,True):
                system.set(dark=dark,high=False);theme='system-dark' if dark else 'system-light'
                capture('reader');w.show_appearance();capture('appearance');w.appearance.popdown()
        (out/f'{args.phase}-{LANGUAGE}-captures.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
    finally:w.close()


if __name__=='__main__':main()
