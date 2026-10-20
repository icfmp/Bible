"""Verify a warmed real catalogue and installed detail without any network."""
import argparse
from pathlib import Path
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('--screenshot-prefix');args=parser.parse_args()
    from bible.ui import Application,Window,Gtk
    from bible.library import Library
    from tests.test_ui import spin
    app=Application.get_default() or Application();app.register()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    window=Window(app,Library(Path(args.profile)/'translations'));window.present()
    try:
        with patch('urllib.request.urlopen',side_effect=AssertionError('Offline verification')):
            dialog=window.open_library()
            assert dialog.resources,'Expected previously validated real cache'
            immediate=len(dialog.resources)
            dialog.load_catalogue(force=False);spin(lambda:not dialog.busy,duration=.3)
            assert len(dialog.resources)==immediate
            dialog.language.set_selected(dialog.language.codes.index('fr'))
            if args.screenshot_prefix:
                from PIL import ImageGrab
                ImageGrab.grab().save(args.screenshot_prefix+'-list.png')
            index=next(i for i,r in enumerate(dialog.filtered_resources) if r.id=='FreLSN1872')
            dialog.open_details(None,index);spin(duration=.3)
            assert dialog.installed_state.get_visible()
            assert not dialog.download_button.get_visible()
            assert dialog.selected_resource().id=='FreLSN1872'
            dialog.filter_resources()
            assert dialog.selected_resource().id=='FreLSN1872'
            if args.screenshot_prefix:ImageGrab.grab().save(args.screenshot_prefix+'-installed.png')
            print(f'PASS: {immediate} cached resources immediately available offline; French filtering; installed Lausanne identity and selection preserved',flush=True)
            dialog.close()
    finally:window.close()


if __name__=='__main__':main()
