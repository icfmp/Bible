"""Capture/verify the real reader in a disposable validation profile only.

This intentionally resets reading settings in the supplied TEST profile.
Never point it at a user's profile. No downloaded scripture is committed.
"""
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('--screenshots');args=parser.parse_args()
    from bible.ui import Application,Window,Gtk
    from bible.library import Library
    from tests.test_ui import spin
    app=Application.get_default() or Application();app.register()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    window=Window(app,Library(Path(args.profile)/'translations'));window.set_default_size(1200,900);window.present()
    def capture(name):
        spin(lambda:not window.active_tab._restoring_scroll,duration=.3)
        if args.screenshots:
            from PIL import ImageGrab
            ImageGrab.grab().save(args.screenshots+'-'+name+'.png')
    try:
        tab=window.active_tab;tab.state.comparison=None;tab.refresh_comparison()
        window.study_button.set_active(False)
        window.appearance.reset()
        assert window.preferences.value.size==14
        assert tab.navigate('FreSegond1910','John.3.16')
        capture('airy')
        assert window.reader_controls.get_parent() is tab.reading_overlay
        window.appearance.update('line_spacing','very-airy');capture('very-airy')
        window.appearance.update('line_spacing','airy')
        for palette,mode,attribute in [('white','day','day_palette'),('paper','day','day_palette'),
                                       ('dark','night','night_palette'),('black','night','night_palette')]:
            window.appearance.update(attribute,palette);window.appearance.update('mode',mode)
            assert window.reading_style.palette==palette
            capture(palette)
        window.appearance.reset()
        window.choose_passage(direct=True);capture('selector')
        assert window.navigation.direct.get_mapped()
        window.navigation.popdown()
        space=window.open_notes();space.create_note()
        space.editor.body.get_buffer().set_text('Validation note — test data only.\n\n**Reading** and offline study.')
        space.editor.labels.set_values(['Reading','Review'])
        assert space.editor.save(close=False)
        capture('notes')
        print('PASS: real reading resource; active Bible overlays; 14 pt defaults; four palettes; Very airy; top reference field; notes workspace',flush=True)
    finally:
        if window.note_editor:window.note_editor._discard=True
        window.close()


if __name__=='__main__':main()
