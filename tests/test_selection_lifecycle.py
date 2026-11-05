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
    def test_native_text_drag_completion_cancel_and_copy_preserve_selection(self):
        if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')!='1':
            result=subprocess.run(['dbus-run-session','--','xvfb-run','-a',sys.executable,
                                   '-m','unittest',self.id(),'-v'],
                                  env=dict(os.environ,BIBLE_TEST_ISOLATED_CLICK='1'),
                                  capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr);return
        from bible.ui import Application,Window,Library,Gtk
        from tools.check_alpha_ui import X11Input
        from tools.check_passage_actions import point
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[(f'Gen.1.{i}',f'Verse {i} exact synthetic source words. '*3) for i in range(1,7)])
            app=Application.get_default() or Application();app.register()
            w=Window(app,Library(Path(directory)/'translations'));w.set_default_size(1200,900);w.present();spin()
            n=X11Input();n.activate(w)
            try:
                t=w.active_tab;v=t.text;b=v.get_buffer();a=w.passage_actions
                spin(lambda:not t._restoring_scroll,duration=.3)
                observed=set();ended=[]
                def observe(controller,*_):
                    drop=controller.get_drop();drag=drop.get_drag() if drop else None
                    if drag is not None and drag not in observed:
                        observed.add(drag)
                        drag.connect('cancel',lambda _,reason:ended.append(reason.value_nick))
                        drag.connect('dnd-finished',lambda *_:ended.append('finished'))
                controllers=w.observe_controllers()
                observer=next(controllers.get_item(i) for i in range(controllers.get_n_items())
                              if isinstance(controllers.get_item(i),Gtk.DropControllerMotion))
                observer.connect_after('enter',observe);observer.connect_after('motion',observe)
                def press(offset):
                    n.move_at(v,*point(v,offset));n.xtest.XTestFakeButtonEvent(n.display,1,True,0)
                    n.x11.XFlush(n.display);spin(duration=.04)
                def release():
                    n.xtest.XTestFakeButtonEvent(n.display,1,False,0);n.x11.XFlush(n.display);spin(duration=.25)
                def move(first,last):
                    start,end=point(v,first),point(v,last)
                    for step in range(1,9):
                        n.move_at(v,start[0]+(end[0]-start[0])*step/8,start[1]+(end[1]-start[1])*step/8)
                        spin(duration=.02)
                first,last=t._marker_ends['Gen.1.1']+2,t._marker_ends['Gen.1.3']+10
                for backward in (False,True)*4:
                    start,end=(last,first) if backward else (first,last)
                    press(start);move(start,end)
                    self.assertFalse(a.bar.get_visible(),'The bar must remain hidden during the native gesture')
                    release()
                    self.assertTrue(b.get_has_selection());self.assertTrue(a.bar.get_visible())
                    self.assertTrue(a.valid());self.assertFalse(a.dragging);self.assertEqual(a.capture_idle,0)
                self.assertIn('no-target',ended,'Exercise native DND, not just ordinary text selection')
                # Escape cancels the native drag without reopening its toolbar.
                low,high=(i.get_offset() for i in b.get_selection_bounds());middle=low+30
                old=b.get_text(b.get_iter_at_offset(low),b.get_iter_at_offset(high),False)
                spin(duration=.55)
                press(middle);move(middle,high-10)
                n.key('Escape');release()
                self.assertFalse(a.bar.get_visible());self.assertFalse(a.dragging)
                self.assertEqual(b.get_text(*b.get_selection_bounds(),False),old)
                # Keep native COPY into an editable GTK target fully functional.
                destination=Gtk.TextView(editable=True,width_request=300,height_request=80,
                                         halign=Gtk.Align.END,valign=Gtk.Align.END,margin_bottom=120)
                t.reading_overlay.add_overlay(destination);spin(duration=.55)
                n.click_at(v,*point(v,t._marker_ends['Gen.1.5']+4))
                press(first);move(first,last);release();spin(duration=.55)
                low,high=(i.get_offset() for i in b.get_selection_bounds());middle=low+30
                old=b.get_text(b.get_iter_at_offset(low),b.get_iter_at_offset(high),False)
                previous=len(observed)
                for attempt in range(3):
                    press(middle);move(middle,high-10)
                    if len(observed)>previous:break
                    release();spin(duration=.55)
                self.assertGreater(len(observed),previous,'Start a real native COPY gesture')
                n.move_at(destination,30,20);spin(duration=.3)
                n.move_at(destination,35,25);spin(duration=.3);release()
                target=destination.get_buffer()
                self.assertEqual(target.get_text(*target.get_bounds(),False),old)
                self.assertIn('finished',ended)
                self.assertEqual(b.get_text(*b.get_selection_bounds(),False),old)
                self.assertFalse(a.dragging)
                t.reading_overlay.remove_overlay(destination);spin()
                # A later fresh selection still works after both native endings.
                n.click_at(v,*point(v,t._marker_ends['Gen.1.5']+4))
                press(first);move(first,last);release()
                self.assertTrue(a.bar.get_visible());self.assertTrue(a.valid())
                n.wheel(v,1);self.assertFalse(a.bar.get_visible())
                self.assertEqual(a.capture_idle,0);self.assertEqual(a.adapt_tick,0)
                self.assertFalse(a._native_drags)
            finally:n.close();close_test_dialogs();w.close()

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
                # A real scrollbar press must release the same blur/capture
                # lifetime before the first drag motion, without stealing GTK's
                # native gesture. Programmatic adjustment changes are separate.
                adjustment=t.scroll.get_vadjustment();adjustment.set_value(0);spin(duration=.2)
                begin=t._marker_ends['Gen.1.1']+4
                b.select_range(b.get_iter_at_offset(begin),b.get_iter_at_offset(begin+8))
                a.capture(v,lambda:a.ordinary(t),None);spin();self.assertTrue(a.bar.get_visible())
                track=t.scroll.get_vscrollbar().get_first_child();low,high=track.get_slider_range()
                y=(low+high)/2;x=track.get_width()/2
                n.move_at(track,x,y);spin(duration=.1)
                n.xtest.XTestFakeButtonEvent(n.display,1,True,0);n.x11.XFlush(n.display);spin(duration=.04)
                self.assertFalse(a.bar.get_visible());self.assertIsNone(a.bar.backdrop)
                self.assertEqual(a.capture_idle,0);self.assertEqual(a.adapt_tick,0)
                n.move_at(track,x,min(track.get_height()-4,y+100));spin(duration=.1)
                n.xtest.XTestFakeButtonEvent(n.display,1,False,0);n.x11.XFlush(n.display);spin(duration=.2)
                self.assertGreater(adjustment.get_value(),0)
                b.place_cursor(b.get_start_iter())
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
