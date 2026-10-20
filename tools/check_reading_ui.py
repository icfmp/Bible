"""Native X11 keyboard/mouse regression checks for issues 24 and 25.

Uses explicitly synthetic SWORD fixtures; not a manual GNOME/Flatpak test.
"""
from pathlib import Path
import tempfile
from tests.test_ui import installed_fixture,spin
from tests.test_reading_sync import linked_commentary
from tools.check_alpha_ui import X11Input
from bible.ui import Application,Window,Library


def main():
    app=Application();app.register();native=X11Input()
    with tempfile.TemporaryDirectory() as directory:
        installed_fixture(directory,entries=[(f'Gen.1.{i}',f'VERSE {i} TEST '*100) for i in range(1,9)]+[('Gen.2.1','NEXT CHAPTER TEST')])
        linked_commentary(directory)
        window=Window(app,Library(Path(directory)/'translations'));window.present();window.set_default_size(1180,780)
        try:
            window.active_tab.state.commentary='Notes';window.study_button.set_active(True);window.study.refresh()
            spin(lambda:not window.active_tab._restoring_scroll and not window.study._positioning,duration=.3)
            native.click(window.active_tab.text);native.key('Page_Down')
            spin(lambda:window.reading_sync.driver=='bible')
            assert window.active_tab.visible_reference()==window.active_tab.state.reference
            native.click(window.study.text);native.key('End')
            # End alone moves the caret; Ctrl+End scrolls to the final actual section.
            code=native.x11.XKeysymToKeycode(native.display,native.x11.XStringToKeysym(b'Control_L'))
            native.xtest.XTestFakeKeyEvent(native.display,code,True,0)
            native.key('End')
            native.xtest.XTestFakeKeyEvent(native.display,code,False,0);native.x11.XFlush(native.display)
            spin(lambda:window.reading_sync.driver=='commentary',duration=.3)
            # The preceding commentary traversal may leave the Bible on its
            # final, short chapter. Test PageDown from a known long passage,
            # rather than requiring a page beyond the end of the resource.
            assert window.navigate_selection(window.active_tab.state.resource,'Gen.1.1')
            spin(lambda:not window.active_tab._restoring_scroll and not window.study._positioning)
            native.key('F11');spin(lambda:window.immersion is not None and window.immersion.layout_ready)
            reading=window.immersion;assert reading.kind=='bible'
            reading.views[0].grab_focus();before=reading.stream.cursor
            assert reading.stream.step(reading.addresses[-1],1) is not None, 'PageDown requires another page'
            native.key('Page_Down')
            spin(lambda:reading.stream.cursor!=before and reading.layout_ready)
            assert reading.stream.cursor!=before
            native.key('F10');assert reading.top.get_reveal_child()
            native.click(reading.aa);spin(lambda:window.appearance.get_visible())
            native.key('Escape');assert window.immersion is reading
            native.key('Escape');spin(lambda:window.immersion is None)
            print('PASS: native mouse/keyboard driver changes, F11 entry, PageDown, F10 controls, Escape popup then exit')
        finally:window.close();native.close()


if __name__=='__main__':main()
