"""Actual GTK language discovery and offline new-edition reading, disposable profiles only."""
import argparse
import inspect
import json
from pathlib import Path
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--require-packaged',action='store_true');args=parser.parse_args()
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin,close_test_dialogs
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    assert args.profile.name in ('profile','shared-proof-profile'),'Use a disposable proof profile'
    args.output.mkdir(parents=True,exist_ok=False)
    app=Application.get_default() or Application();app.register()
    window=Window(app,Library(args.profile/'translations'));window.set_default_size(1100,760);window.present();spin()
    native=X11Input();native.activate(window);screen=Screen(native);captures=[];dialog=None
    try:
        with SystemStyleOverride() as style:
            for mode,palette in [('day','white'),('night','dark')]:
                style.set(dark=mode=='night',high=False)
                window.appearance.update('mode',mode)
                window.appearance.update('day_palette' if mode=='day' else 'night_palette',palette)
                with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
                    dialog=window.open_library();spin(lambda:not dialog.preparing)
                dialog.source_filter.set_selected(dialog.source_ids.index('youversion'))
                dialog.load_catalogue(force=False);spin(lambda:not dialog.busy,duration=.3)
                for language in ('es','fr','ar'):
                    dialog.language.set_selected(dialog.language.codes.index(language))
                    spin(lambda:not dialog.busy,duration=.3)
                    assert dialog.filtered_resources and all(r.provider_id=='youversion' for r in dialog.filtered_resources)
                    name=f'catalogue-{language}-{palette}.png';native.move_at(dialog,2,2);spin(duration=.1)
                    screen.grab(args.output/name);captures.append(dict(file=name,language=language,rows=len(dialog.filtered_resources)))
                dialog.close();dialog=None;spin()
                tab=window.active_tab
                tab.state.comparison='';tab.refresh_comparison();spin()
                with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Unexpected offline reading request')):
                    for edition,reference in [(504,'Tob.1.1'),(36,'Isa.38.1'),(13,'John.1.1'),(2599,'Matt.1.1')]:
                        window.set_default_size(1100,760);tab.navigate('youversion~YV'+str(edition),reference);spin()
                        assert tab._document.spans and tab.text.get_buffer().get_char_count()>100
                        if edition==13:assert tab.text.get_direction()==Gtk.TextDirection.RTL
                        if edition==36:
                            refs=[int(ref.rsplit('.',1)[1]) for ref,_ in tab.reader.chapter(reference).unique_verses()]
                            assert refs==[*range(1,7),21,22,*range(7,21)]
                            layout=tab.text.create_pango_layout(tab.text.get_buffer().props.text)
                            assert layout.get_unknown_glyphs_count()==0,'Missing CJK font on the validation host'
                        window.study_button.set_active(True);window.study.tools.set_visible_child_name('translation-notes');spin()
                        name=f'edition-{edition}-{palette}.png';native.move_at(window,2,2);screen.grab(args.output/name)
                        captures.append(dict(file=name,edition=edition,size=[window.get_width(),window.get_height()]))
                    window.set_default_size(360,600);spin(duration=.3)
                    name=f'edition-small-{palette}.png';screen.grab(args.output/name)
                    captures.append(dict(file=name,size=[window.get_width(),window.get_height()]))
    finally:
        if dialog:dialog.close()
        window.close();close_test_dialogs();spin();native.close()
    report=dict(result='PASS',app_import=inspect.getfile(Window),gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],
                actual_packaged_application=args.require_packaged,captures=captures)
    (args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
