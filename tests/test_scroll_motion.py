"""Exercise native frame-clock motion, retargeting and interruption."""
import os
import unittest


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires native GTK')
class ScrollMotionTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('BIBLE_TEST_ISOLATED_CLICK')=='1','Requires isolated native X11 input')
    def test_native_edge_rebound_cannot_replace_a_new_programmatic_target(self):
        from bible.ui import Gtk
        from bible.scroll_motion import ScrollMotion
        from tests.test_ui import spin
        from tools.check_alpha_ui import X11Input
        window=Gtk.Window(default_width=400,default_height=400)
        scroll=Gtk.ScrolledWindow();scroll.set_child(Gtk.Label(label='Synthetic line\n'*300))
        window.set_child(scroll);window.present();spin()
        native=X11Input();native.activate(window);motion=ScrollMotion(scroll)
        settings=Gtk.Settings.get_default();animations=settings.get_property('gtk-enable-animations')
        try:
            settings.set_property('gtk-enable-animations',False)
            for kinetic in (False,True):
                scroll.set_kinetic_scrolling(kinetic);motion.move(0,animate=False)
                # Real discrete wheel overshoot starts a GTK deceleration even
                # with animations off; an old frame used to replace 300 by 0.
                native.wheel(scroll,-6);motion.move(300,animate=False)
                self.assertEqual(scroll.get_kinetic_scrolling(),kinetic)
                self.assertAlmostEqual(scroll.get_vadjustment().get_value(),300,delta=1)
                spin(duration=.7)
                self.assertAlmostEqual(scroll.get_vadjustment().get_value(),300,delta=1)
                self.assertFalse(motion.running)
        finally:
            settings.set_property('gtk-enable-animations',animations);window.destroy();native.close()

    def test_frames_latest_target_input_reflow_and_disabled_animations(self):
        from bible.ui import Gtk
        from bible.scroll_motion import ScrollMotion
        from tests.test_ui import spin
        window=Gtk.Window(default_width=400,default_height=400)
        scroll=Gtk.ScrolledWindow();scroll.set_child(Gtk.Label(label='text\n'*200))
        window.set_child(scroll);window.present();spin()
        motion=ScrollMotion(scroll);adjustment=scroll.get_vadjustment()
        settings=Gtk.Settings.get_default();old=settings.get_property('gtk-enable-animations')
        try:
            settings.set_property('gtk-enable-animations',True)
            motion.move(300);spin(lambda:adjustment.get_value()>0,duration=0,timeout=2)
            self.assertTrue(motion.running);self.assertGreater(adjustment.get_value(),0)
            self.assertLess(adjustment.get_value(),300)
            motion.move(100);spin(lambda:not motion.running,duration=.3)
            self.assertAlmostEqual(adjustment.get_value(),100,delta=1)
            motion.move(350);spin(duration=.05);motion.cancel()
            stopped=adjustment.get_value();spin(duration=.3)
            self.assertEqual(adjustment.get_value(),stopped)
            motion.move(200,valid=lambda:False);spin()
            self.assertFalse(motion.running)
            settings.set_property('gtk-enable-animations',False)
            motion.move(250);self.assertFalse(motion.running)
            self.assertAlmostEqual(adjustment.get_value(),250,delta=1)
            settings.set_property('gtk-enable-animations',True)
            motion.move(100);window.set_visible(False);spin()
            self.assertFalse(motion.running)
        finally:
            settings.set_property('gtk-enable-animations',old);window.destroy()
