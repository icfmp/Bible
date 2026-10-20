import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture,spin
from tests.test_reading_sync import linked_commentary


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK/Pango under Xvfb')
class ImmersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application,Gtk
        cls.app=Application.get_default() or Application();cls.app.register()
        Gtk.Settings.get_default().set_property('gtk-enable-animations',False)

    def window(self,directory,rtl=False):
        from bible.ui import Window,Library
        root=installed_fixture(directory,entries=[('Gen.1.1',('טקסט מקור — TEST TEXT. ' if rtl else 'SOURCE TEST α — words. ')*200),
                                                  ('Gen.1.2','SECOND SOURCE TEST '*150),('Gen.2.1','NEXT CHAPTER SOURCE '*180)])
        if rtl:
            with (root/'mods.d/test.conf').open('a') as file:file.write('Direction=RtoL\n')
        installed_fixture(directory,'Other');linked_commentary(directory)
        w=Window(self.app,Library(Path(directory)/'translations'));w.present();w.set_default_size(1180,760)
        self.addCleanup(lambda:w.close() if not w.closed else None)
        w.navigate_selection('Test','Gen.1.1');spin(lambda:not w.active_tab._restoring_scroll,duration=.2)
        return w

    def entered(self,w,kind='bible'):
        self.assertTrue(w.enter_immersion(kind))
        spin(lambda:w.immersion and w.immersion.stream.cursor is not None,duration=.3)
        return w.immersion

    def test_real_pages_fit_and_partition_and_roundtrip_restores_panels(self):
        with tempfile.TemporaryDirectory() as directory:
            w=self.window(directory);tab=w.active_tab
            tab.state.comparison='Other';tab.state.commentary='Notes';w.study_button.set_active(True);w.update_navigation();spin()
            history=len(tab.state.history);original_tabs=w.tabs();r=self.entered(w)
            self.assertEqual(r.count,2);self.assertFalse(w.split.get_mapped())
            initial=r.stream.cursor;seen=[]
            while True:
                spin(duration=.05)
                for view,address in zip(r.views,r.addresses):
                    plan=r.stream.plan(address.key);page=plan.pages[address.index]
                    text=view.get_buffer().props.text;self.assertEqual(text,plan.document.text[page.start:page.end])
                    if text:
                        iterator=view.get_buffer().get_iter_at_offset(len(text)-1)
                        last=view.get_iter_location(iterator)
                        self.assertLessEqual(last.y+last.height+view.get_top_margin(),view.get_height()+1)
                    seen.append((address,text))
                before=r.stream.cursor
                if not r.turn(1):break
                self.assertTrue(r.turn(-1));self.assertEqual(r.stream.cursor,before)
                self.assertTrue(r.turn(1))
            self.assertEqual(len({a for a,_ in seen}),len(seen))
            expected=''.join(r.source.document(key,w.preferences.value).text for key in ['Gen.1','Gen.2'])
            self.assertEqual(''.join(t for _,t in seen),expected)
            reached=r.stream.anchor();w.leave_immersion();spin(lambda:not tab._restoring_scroll)
            self.assertEqual(tab.state.reference,reached.reference)
            self.assertEqual(tab.state.comparison,'Other');self.assertTrue(w.split.get_show_sidebar())
            self.assertEqual(w.tabs(),original_tabs);self.assertEqual(len(tab.state.history),history)
            self.assertIsNone(w.immersion);w.close()

    def test_reflow_preserves_inside_verse_and_selection_escape_precedence(self):
        from gi.repository import Gdk
        with tempfile.TemporaryDirectory() as directory:
            w=self.window(directory);r=self.entered(w);self.assertTrue(r.turn(1))
            before=r.stream.anchor();self.assertGreater(before.offset,0)
            w.appearance.update('size',64)
            spin(lambda:r.stream.cursor is not None and r.count==1,duration=.3)
            self.assertEqual(r.stream.anchor(),before)
            w.appearance.update('verse_numbers',False)
            spin(lambda:r.stream.cursor is not None,duration=.3)
            self.assertEqual(r.stream.anchor(),before)
            r.views[0].grab_focus();buffer=r.views[0].get_buffer()
            buffer.select_range(buffer.get_iter_at_offset(2),buffer.get_iter_at_offset(11))
            text=buffer.get_text(*buffer.get_selection_bounds(),False)
            cursor=r.stream.cursor
            self.assertFalse(r.key_pressed(None,Gdk.KEY_Page_Down,0,0));self.assertEqual(r.stream.cursor,cursor)
            copied=[];r.views[0].emit('copy-clipboard')
            r.get_clipboard().read_text_async(None,lambda clipboard,result:copied.append(clipboard.read_text_finish(result)))
            spin(lambda:bool(copied));self.assertEqual(copied[0],text)
            w.appearance.update('size',24)
            spin(lambda:r.stream.cursor is not None,duration=.3)
            copied=[];next(v for v in r.views if v.get_buffer().get_has_selection()).emit('copy-clipboard')
            r.get_clipboard().read_text_async(None,lambda clipboard,result:copied.append(clipboard.read_text_finish(result)))
            spin(lambda:bool(copied));self.assertEqual(copied[0],text)
            w.show_appearance();spin();r.key_pressed(None,Gdk.KEY_Escape,0,0)
            self.assertIs(w.immersion,r);self.assertFalse(w.appearance.get_visible())
            r.key_pressed(None,Gdk.KEY_Escape,0,0);self.assertIsNone(w.immersion)
            w.close()

    def test_commentary_entry_limits_resume_and_bible_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            w=self.window(directory);tab=w.active_tab;tab.state.commentary='Notes'
            w.study_button.set_active(True);w.study.refresh();spin(lambda:not w.study._positioning)
            original=tab.state.reference;history=len(tab.state.history)
            r=self.entered(w,'commentary');self.assertEqual(len(r.addresses),1)
            self.assertFalse(r.turn(1))  # Short first entry, explicit next entry required.
            r.change_entry(1);self.assertGreater(len(r.stream.plan(r.stream.cursor.key).pages),2)
            self.assertTrue(r.turn(1));anchor=r.stream.anchor();position=r.stream.cursor.key
            self.assertEqual(tab.state.reference,original)
            w.leave_immersion();spin(lambda:not w.study._positioning)
            self.assertEqual(tab.state.reference,original);self.assertEqual(w.study.current_position,position)
            self.assertTrue(tab.state.commentary_positions['Notes']['immersive'])
            self.assertEqual(len(tab.state.history),history)
            r=self.entered(w,'commentary');self.assertEqual(r.stream.anchor(),anchor)
            w.leave_immersion();w.close()

    def test_narrow_rtl_notifications_optout_and_suspension(self):
        from bible.ui import Gtk
        with tempfile.TemporaryDirectory() as directory:
            w=self.window(directory,rtl=True);r=self.entered(w)
            self.assertTrue(r.source.rtl);self.assertEqual(r.pages.get_direction(),Gtk.TextDirection.RTL)
            self.assertGreater(r.frames[0].get_allocation().x,r.frames[1].get_allocation().x)
            r.hide_help();self.assertTrue(w.immersion_hints.disabled)
            w.set_default_size(360,650);spin(lambda:r.count==1,duration=.3)
            self.assertLessEqual(w.get_width(),360)
            self.assertLessEqual(r.views[0].get_height(),650)
            text=r.views[0].get_buffer().props.text
            if text:
                last=r.views[0].get_iter_location(r.views[0].get_buffer().get_iter_at_offset(len(text)-1))
                self.assertLessEqual(last.y+last.height+r.views[0].get_top_margin(),r.views[0].get_height()+1)
            w.open_notes();self.assertIsNone(w.immersion);self.assertEqual(w.main_pages.get_visible_child_name(),'notes')
            w.notes_space.leave();r=self.entered(w);self.assertFalse(r.notification_help.get_revealed())
            w.leave_immersion();w.close()
