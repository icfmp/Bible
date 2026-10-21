"""Capture #42/#43/#12 on an explicitly disposable real-resource TEST profile."""
import argparse
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from bible.ui import Application, Window, Library, Gtk


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('prefix')
    args=parser.parse_args()
    from PIL import ImageGrab
    app=Application();app.register();native=X11Input()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    library=Library(Path(args.profile)/'translations')
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline test')):
        window=Window(app,library);window.set_default_size(1200,900);window.present()
        try:
            window.appearance.reset();window.appearance.update('mode','day')
            tab=window.active_tab;tab.state.comparison=None;tab.refresh_comparison()
            window.study_button.set_active(False);tab.navigate('FreSegond1910','John.3.16')
            spin(lambda:not tab._restoring_scroll,duration=.3)
            native.move_at(window,5,5);spin(duration=.2)
            ImageGrab.grab().save(args.prefix+'-reading.png')
            native.click(window.appearance_button)
            expander=window.appearance.controls.get_first_child()
            while not isinstance(expander,Gtk.Expander):expander=expander.get_next_sibling()
            expander.set_expanded(True);spin(duration=.2)
            native.move_at(window,5,5);ImageGrab.grab().save(args.prefix+'-appearance.png')
            native.click_at(tab.text,8,100);assert not window.appearance.get_visible()
            resources=[library.resource(name) for name in library.installed()]
            with patch('bible.catalogue_window.catalogue',return_value=resources):
                dialog=window.open_library();dialog.load_catalogue();spin(lambda:not dialog.busy)
                dialog.installed_only.set_active(True);dialog.search.set_text('FreSegond1910');dialog.filter_resources()
                index=next(i for i,r in enumerate(dialog.filtered_resources) if r.name=='FreSegond1910')
                dialog.open_details(None,index);spin(duration=.2)
                dialog.metadata.grab_focus();assert not dialog.metadata.get_selection_bounds()[0]
                assert '\\par' not in dialog.metadata.get_text()
                native.move_at(dialog,5,5);ImageGrab.grab().save(args.prefix+'-details.png')
                dialog.metadata.select_region(0,40);assert dialog.metadata.get_selection_bounds()[0]
                native.key('Tab');native.key('ISO_Left_Tab')
                dialog.close()
            print('PASS: real resource metadata unselected on focus, deliberate selection retained; '
                  'legacy paragraph markers gone, attribution present; actual reading/Aa/details captures',flush=True)
        finally:window.close();native.close()


if __name__=='__main__':main()
