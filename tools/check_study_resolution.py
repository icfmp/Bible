"""Real module probe and offline GTK study/comparison regression for #35/#36.

Run once with --install, then under Xvfb with --offline. Downloads remain in
the caller's temporary library; no scripture is committed to the repository.
"""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from bible.library import Library, catalogue
from bible.reference_resolution import resolve
from bible.sword_provider import Reader, CommentaryReader


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory')
    parser.add_argument('--install',action='store_true')
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--screenshot')
    args=parser.parse_args()
    library=Library(Path(args.directory)/'translations')
    names=('FreSegond1910','FreLSN1872','MHC')
    if args.install:
        resources={r.name:r for r in catalogue()}
        for name in names:
            if name not in library.installed():library.install(resources[name])
    if not args.offline:return
    from bible.ui import Application, Window, Gtk
    from tests.test_ui import spin
    app=Application.get_default() or Application();app.register()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline validation')):
        bible=Reader(library.root/names[0],names[0])
        commentary=CommentaryReader(library.root/'MHC','MHC')
        comparison=Reader(library.root/names[1],names[1])
        identities={name:dict(versification=reader.versification,
                             version=reader.module.getConfigEntry('Version'),
                             driver=reader.module.getConfigEntry('ModDrv'))
                    for name,reader in zip(names,(bible,comparison,commentary))}
        window=Window(app,library);window.set_default_size(1440,900);window.present()
        spin(duration=.3)
        try:
            tab=window.active_tab
            tab.state.comparison=None;tab.refresh_comparison()
            for reference in ('Gen.1.25','John.3.16','Ps.3.2','Ps.51.3'):
                assert tab.navigate(names[0],reference)
                tab.state.commentary='MHC';window.study_button.set_active(True);window.study.refresh(force=True)
                spin(lambda:not tab._restoring_scroll and not window.study._positioning,duration=.3)
                mapped=resolve(reference,bible.versification,commentary)
                assert window.study.entry_text, (reference,window.study.status.get_text())
                assert commentary.entry(reference,bible.versification) in window.study.entry_text
                assert window.study.reader.index.locate(mapped.start)==window.study.current_position
                if args.screenshot and reference=='Gen.1.25':
                    from PIL import ImageGrab
                    ImageGrab.grab().save(str(Path(args.screenshot).with_stem(Path(args.screenshot).stem+'-study')))
                print(json.dumps({'source':reference,'commentary':mapped.start,
                                  'entry':window.study.reader.index.label(window.study.current_position)}),flush=True)
            for reference in ('Ps.3.2','Ps.51.3'):
                tab.navigate(names[0],reference);tab.state.comparison=names[1];tab.refresh_comparison()
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_tick',0))
                assert tab.comparison_text.get_buffer().props.text
                assert not tab.comparison_status.get_text(),tab.comparison_status.get_text()
                assert abs(tab.reading_overlay.get_width()-tab.comparison_box.get_width())<=1
            tab.navigate(names[0],'Gen.1.19');tab.state.comparison=names[1];tab.refresh_comparison()
            spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_tick',0))
            assert tab.comparison_text.get_buffer().props.text
            assert not tab.comparison_status.get_text(),tab.comparison_status.get_text()
            window.study_button.set_active(False);spin(lambda:not tab._restoring_scroll,duration=.3)
            assert abs(tab.reading_overlay.get_width()-tab.comparison_box.get_width())<=1
            assert tab.text.get_left_margin()==tab.comparison_text.get_left_margin()
            if args.screenshot:
                from PIL import ImageGrab
                ImageGrab.grab().save(args.screenshot)
            print(json.dumps({'identities':identities,'comparison_reference':resolve('Gen.1.19',bible.versification,comparison).start,
                              'pane_widths':[tab.reading_overlay.get_width(),tab.comparison_box.get_width()],
                              'offline':True}),flush=True)
        finally:window.close()


if __name__=='__main__':main()
