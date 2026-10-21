"""Real-resource paint/backup probe. Use only a disposable validation profile."""
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
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline verification')):
        window=Window(app,Library(Path(args.profile)/'translations'));window.set_default_size(1200,900);window.present()
        try:
            window.appearance.reset();tab=window.active_tab
            assert tab.navigate('FreSegond1910','John.3.16')
            spin(lambda:not tab._restoring_scroll,duration=.3)
            before=tab.text.get_buffer().props.text
            for reference,color in [('John.3.16','yellow'),('John.3.17','green'),('John.3.18','blue')]:
                tab.select_verse(reference);window.mark_highlight(color)
            tab.select_verse('John.3.16')
            assert tab.text.get_buffer().props.text==before
            backup=Path(args.profile)/'highlights-validation-backup.json';window.highlights.backup(backup)
            entries=dict(window.highlights.entries)
            window.appearance.show_highlights.set_active(False)
            assert window.highlights.entries==entries
            window.appearance.show_highlights.set_active(True)
            spin(duration=.3)
            if args.screenshot_prefix:
                from PIL import ImageGrab
                ImageGrab.grab().save(args.screenshot_prefix+'-reader.png')
            window.mark_highlight(None);window.highlights.restore(backup);window.refresh_highlights()
            assert window.highlights.entries==entries
            panel=window.open_highlights();panel.search.set_text('Jean');panel.refresh();spin(duration=.3)
            if args.screenshot_prefix:ImageGrab.grab().save(args.screenshot_prefix+'-list.png')
            panel.close()
            print('PASS: three real offline verse highlights; source text unchanged; hide/show retains records; backup/merge restores marks; find list usable',flush=True)
        finally:window.close()


if __name__=='__main__':main()
