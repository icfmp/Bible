"""Real native selection boundaries and cancellation between queued inputs."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tests.test_ui import installed_fixture,spin,close_test_dialogs


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK and isolated native input')
class SelectionLifecycleTests(unittest.TestCase):
    def test_pending_keyboard_capture_cannot_cancel_a_new_mouse_selection(self):
        if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')!='1':
            result=subprocess.run(['dbus-run-session','--','xvfb-run','-a',sys.executable,
                                   '-m','unittest',self.id(),'-v'],
                                  env=dict(os.environ,BIBLE_TEST_ISOLATED_CLICK='1'),
                                  capture_output=True,text=True,timeout=50)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr);return
        from bible.ui import Application,Window,Library
        from tools.check_alpha_ui import X11Input
        from tools.check_passage_actions import point,hold
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[(f'Gen.1.{i}',f'Verse {i} exact synthetic source words. '*3) for i in range(1,7)])
            app=Application.get_default() or Application();app.register()
            w=Window(app,Library(Path(directory)/'translations'));w.set_default_size(1280,900);w.present();spin()
            n=X11Input();n.activate(w)
            try:
                t=w.active_tab;w.appearance.update('size',24)
                w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes')
                spin(lambda:not t._restoring_scroll,duration=.3)
                a=w.passage_actions;v=t.text;b=v.get_buffer()
                v.scroll_to_iter(b.get_iter_at_offset(t._marker_ends['Gen.1.1']),0,True,0,.1);spin(duration=.2)
                n.click_at(v,*point(v,t._marker_ends['Gen.1.1']+4))
                hold(n,'Shift_L',True);n.key('Right');n.key('Right')
                old=tuple(i.get_offset() for i in b.get_selection_bounds());self.assertTrue(old)
                first=point(v,t._marker_ends['Gen.1.2']+4);last=point(v,t._marker_ends['Gen.1.3']+8)
                n.move_at(v,*first)
                shift=n.x11.XKeysymToKeycode(n.display,n.x11.XStringToKeysym(b'Shift_L'))
                # Native key release queues its idle; a new press reaches GTK
                # before that idle, which must not inspect/cancel the new drag.
                n.xtest.XTestFakeKeyEvent(n.display,shift,False,0)
                n.xtest.XTestFakeButtonEvent(n.display,1,True,0);n.x11.XFlush(n.display);spin(duration=.12)
                self.assertFalse(a.bar.get_visible())
                def finish_drag(first,last,pressed=False):
                    if not pressed:
                        n.move_at(v,*first);n.xtest.XTestFakeButtonEvent(n.display,1,True,0);n.x11.XFlush(n.display);spin(duration=.03)
                    for step in range(1,9):
                        n.move_at(v,first[0]+(last[0]-first[0])*step/8,first[1]+(last[1]-first[1])*step/8);spin(duration=.02)
                    n.xtest.XTestFakeButtonEvent(n.display,1,False,0);n.x11.XFlush(n.display);spin(duration=.2)
                finish_drag(first,last,True)
                self.assertNotEqual(tuple(i.get_offset() for i in b.get_selection_bounds()),old)
                self.assertTrue(a.bar.get_visible());self.assertTrue(a.valid())
                self.assertEqual(a.target.references,('Gen.1.2','Gen.1.3'))
                n.wheel(v,1);self.assertFalse(a.bar.get_visible());self.assertEqual(a.capture_idle,0)
                v.scroll_to_iter(b.get_iter_at_offset(t._marker_ends['Gen.1.1']),0,True,0,.1);spin(duration=.2)
                for backward in (False,True,False,True):
                    first=point(v,t._marker_ends['Gen.1.3' if backward else 'Gen.1.1']+4)
                    last=point(v,t._marker_ends['Gen.1.2']+8)
                    self.assertTrue(all(0<y<v.get_height() for _,y in (first,last)))
                    finish_drag(first,last)
                    self.assertTrue(b.get_has_selection());self.assertTrue(a.bar.get_visible());self.assertTrue(a.valid())
                    self.assertEqual(a.capture_idle,0);n.key('Escape');self.assertFalse(a.bar.get_visible())
                n.click_at(v,*point(v,t._marker_ends['Gen.1.1']+4));self.assertFalse(a.bar.get_visible())
                hold(n,'Shift_L',True);n.key('Right')
                escape=n.x11.XKeysymToKeycode(n.display,n.x11.XStringToKeysym(b'Escape'))
                n.xtest.XTestFakeKeyEvent(n.display,shift,False,0)
                n.xtest.XTestFakeKeyEvent(n.display,escape,True,0);n.xtest.XTestFakeKeyEvent(n.display,escape,False,0)
                n.x11.XFlush(n.display);spin(duration=.25)
                self.assertFalse(a.bar.get_visible());self.assertEqual(a.capture_idle,0)
            finally:n.close();close_test_dialogs();w.close()
