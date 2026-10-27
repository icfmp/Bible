import os
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from contextlib import contextmanager
from tests.test_ui import installed_fixture,spin
from tests.test_reading_sync import linked_commentary


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK/Pango under Xvfb')
class ImmersionTests(unittest.TestCase):
    def test_worker_pagination_matches_the_native_font_context(self):
        from bible.ui import Gtk
        from bible.book_stream import BookStream
        from bible.pagination import Document,StyleSpan,paginate
        from bible.preferences import ReadingPreferences
        text='SYNTHETIC SOURCE HEADING\n\n'+('Exact multilingual words αὐτός שלום — continuation and punctuation. '*120)
        document=Document('fixture',text,(),(StyleSpan('heading',0,23),))
        class Source:
            def clone(self):return self
            def document(self,*args,**kwargs):return document
        window=Gtk.Window(default_width=500,default_height=700)
        view=Gtk.TextView();window.set_child(view);window.present();spin()
        try:
            for size,spacing,alignment in [(14,None,'left'),(24,12,'justified'),(48,None,'left')]:
                preferences=ReadingPreferences(size=size,line_spacing='very-airy',line_spacing_px=spacing,alignment=alignment)
                expected=paginate(view,document,preferences,330,600)
                stream=BookStream(view,Source(),preferences)
                try:
                    future=stream.executor.submit(stream.build,'fixture',preferences,330,600,None)
                    spin(lambda:future.done(),timeout=10)
                    actual=future.result()
                    self.assertEqual(actual.pages,expected.pages)
                    self.assertAlmostEqual(actual.capacity,expected.capacity,delta=.01)
                    self.assertAlmostEqual(actual.reading_height,expected.reading_height,delta=.01)
                finally:stream.close()
        finally:window.destroy()

    @classmethod
    def setUpClass(cls):
        from bible.ui import Application,Gtk
        cls.app=Application.get_default() or Application();cls.app.register()
        Gtk.Settings.get_default().set_property('gtk-enable-animations',False)

    @contextmanager
    def profile(self):
        with tempfile.TemporaryDirectory() as directory:
            windows=[]
            self._profile_windows=windows
            try:yield directory
            finally:
                for window in reversed(windows):
                    if not window.closed:
                        editor=window.note_editor
                        if editor and not editor.closed:
                            editor._discard=True;editor.close()
                        window.close()

    def window(self,directory,rtl=False,entries=None):
        from bible.ui import Window,Library
        root=installed_fixture(directory,entries=entries or [('Gen.1.1',('טקסט מקור — TEST TEXT. ' if rtl else 'SOURCE TEST α — words. ')*200),
                                                  ('Gen.1.2','SECOND SOURCE TEST '*150),('Gen.2.1','NEXT CHAPTER SOURCE '*180)])
        if rtl:
            with (root/'mods.d/test.conf').open('a') as file:file.write('Direction=RtoL\n')
        installed_fixture(directory,'Other');linked_commentary(directory)
        w=Window(self.app,Library(Path(directory)/'translations'));w.present();w.set_default_size(1180,760)
        self._profile_windows.append(w)
        w.navigate_selection('Test','Gen.1.1');spin(lambda:not w.active_tab._restoring_scroll,duration=.2)
        return w

    def entered(self,w,kind='bible'):
        self.assertTrue(w.enter_immersion(kind))
        spin(lambda:w.immersion and w.immersion.layout_ready,duration=.1)
        return w.immersion

    def test_real_pages_fit_and_partition_and_roundtrip_restores_panels(self):
        with self.profile() as directory:
            w=self.window(directory);tab=w.active_tab
            tab.state.comparison='Other';tab.state.commentary='Notes';w.study_button.set_active(True);w.update_navigation();spin()
            history=len(tab.state.history);original_tabs=w.tabs();r=self.entered(w)
            self.assertEqual(r.count,2);self.assertFalse(w.split.get_mapped())
            initial=r.stream.cursor;seen=[]
            while True:
                spin(lambda:r.layout_ready,duration=.05)
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
            expected=r.source.document('Gen',w.preferences.value).text
            self.assertEqual(''.join(t for _,t in seen),expected)
            reached=r.stream.anchor();w.leave_immersion();spin(lambda:not tab._restoring_scroll)
            self.assertEqual(tab.state.reference,reached.reference)
            self.assertEqual(tab.state.comparison,'Other');self.assertTrue(w.split.get_show_sidebar())
            self.assertEqual(w.tabs(),original_tabs);self.assertEqual(len(tab.state.history),history)
            self.assertIsNone(w.immersion);w.close()

    def test_reflow_preserves_inside_verse_and_selection_escape_precedence(self):
        from gi.repository import Gdk
        with self.profile() as directory:
            w=self.window(directory);r=self.entered(w);self.assertTrue(r.turn(1))
            before=r.stream.anchor();self.assertGreater(before.offset,0)
            w.appearance.update('size',64)
            spin(lambda:r.layout_ready and r.count==1,duration=.1)
            self.assertEqual(r.stream.anchor(),before)
            w.appearance.update('verse_numbers',False)
            spin(lambda:r.layout_ready,duration=.1)
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
            spin(lambda:r.layout_ready,duration=.1)
            self.assertTrue(r.any_selection(), 'Selection lost after settled 64 → 24 reflow')
            copied=[];next(v for v in r.views if v.get_buffer().get_has_selection()).emit('copy-clipboard')
            r.get_clipboard().read_text_async(None,lambda clipboard,result:copied.append(clipboard.read_text_finish(result)))
            spin(lambda:bool(copied));self.assertEqual(copied[0],text)
            w.show_appearance();spin();r.key_pressed(None,Gdk.KEY_Escape,0,0)
            self.assertIs(w.immersion,r);self.assertFalse(w.appearance.get_visible())
            r.key_pressed(None,Gdk.KEY_Escape,0,0);self.assertIsNone(w.immersion)
            w.close()

    def test_commentary_entry_limits_resume_and_bible_unchanged(self):
        with self.profile() as directory:
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
        with self.profile() as directory:
            w=self.window(directory,rtl=True);r=self.entered(w)
            self.assertTrue(r.source.rtl);self.assertEqual(r.pages.get_direction(),Gtk.TextDirection.LTR)
            self.assertLess(r.frames[0].get_allocation().x,r.frames[1].get_allocation().x)
            self.assertEqual(r.views[0].get_direction(),Gtk.TextDirection.RTL)
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

    def test_native_click_targets_notes_and_context_copy_on_each_page(self):
        if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')!='1':
            # Native pointer events require an isolated display: other tests
            # intentionally create modal dialogs and may retain GTK grabs.
            environment=dict(os.environ,BIBLE_TEST_ISOLATED_CLICK='1')
            result=subprocess.run(['dbus-run-session','--','xvfb-run','-a',sys.executable,
                                   '-m','unittest',self.id(),'-v'],env=environment,
                                  capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return
        from tools.check_alpha_ui import X11Input
        from bible.notes_window import passage_label
        from bible.ui import Gtk
        with self.profile() as directory:
            entries=[(f'Gen.1.{i}',f'VERSE {i} SOURCE TEST. '*8) for i in range(1,30)]
            w=self.window(directory,entries=entries);native=X11Input()
            try:
                for page_index in (0,1):
                    r=self.entered(w);self.assertEqual(len(r.addresses),2)
                    view=r.views[page_index];address=r.addresses[page_index]
                    plan=r.stream.plan(address.key);page=plan.pages[address.index]
                    candidates=[span for span in plan.document.spans
                                if page.start<span.body and span.end<page.end]
                    self.assertGreater(len(candidates),1)
                    target=candidates[-1];iterator=view.get_buffer().get_iter_at_offset(target.body-page.start+4)
                    rect=view.get_iter_location(iterator)
                    x,y=view.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,rect.x+2,rect.y+rect.height//2)
                    native.click_at(view,x,y)
                    self.assertEqual(r.clicked_reference,target.reference)
                    self.assertEqual(r.selected_passage(),(target.reference,target.reference))
                    self.assertEqual(r.stream.cursor,r.addresses[0])
                    w.lookup_action('copy-reference').activate(None);copied=[]
                    r.get_clipboard().read_text_async(None,lambda c,result:copied.append(c.read_text_finish(result)))
                    spin(lambda:bool(copied))
                    self.assertIn(passage_label(target.reference,versification=w.active_tab.reader.versification),copied[0])
                    w.lookup_action('note').activate(None)
                    editor=w.note_editor;self.assertIsNotNone(editor)
                    self.assertEqual((editor.context['start'],editor.context['end']),(target.reference,target.reference))
                    editor.body.get_buffer().set_text('SYNTHETIC NOTE FROM CLICK')
                    self.assertTrue(editor.save())
                    saved=w.notes_store.passage('KJV',target.reference,target.reference)
                    self.assertEqual(len(saved),1)
                    self.assertEqual((saved[0].start,saved[0].end),(target.reference,target.reference))
            finally:native.close()

    def test_passage_navigation_keeps_the_continuous_book_source(self):
        with self.profile() as directory:
            w=self.window(directory,entries=[('Gen.1.1','FIRST CHAPTER TEST. '*50),
                                             ('Gen.2.1','SECOND CHAPTER TEST. '*50)])
            reading=self.entered(w)
            self.assertTrue(w.active_tab.navigate('Test','Gen.2.1'))
            spin(lambda:reading.stream.cursor is not None and reading.layout_ready)
            self.assertTrue(reading.source.book_pages)
            self.assertEqual(reading.stream.cursor.key,'Gen')
            self.assertEqual(reading.stream.anchor().reference,'Gen.2.1')

    def test_multiverse_selection_overrides_click_and_navigation_clears_click(self):
        with self.profile() as directory:
            entries=[(f'Gen.1.{i}',f'VERSE {i} SOURCE TEST. '*6) for i in range(1,30)]
            w=self.window(directory,entries=entries);r=self.entered(w)
            view=r.views[0];plan=r.stream.plan(r.addresses[0].key);page=plan.pages[r.addresses[0].index]
            spans=[span for span in plan.document.spans if page.start<=span.body and span.end<page.end]
            self.assertGreater(len(spans),2)
            # A later text selection takes precedence over a previous point click.
            r.clicked_reference=spans[-1].reference
            buffer=view.get_buffer();buffer.select_range(buffer.get_iter_at_offset(spans[0].body-page.start+2),
                                                          buffer.get_iter_at_offset(spans[1].body-page.start+4))
            self.assertEqual(r.selected_passage(),(spans[0].reference,spans[1].reference))
            w.lookup_action('note').activate(None);editor=w.note_editor
            self.assertEqual((editor.context['start'],editor.context['end']),(spans[0].reference,spans[1].reference))
            editor.body.get_buffer().set_text('MULTIVERSE NOTE TEST');self.assertTrue(editor.save())
            r=self.entered(w);r.clicked_reference=spans[-1].reference
            self.assertTrue(r.turn(1));self.assertIsNone(r.clicked_reference)
            self.assertEqual(r.selected_passage(),(r.stream.anchor().reference,)*2)
            r.clicked_reference=r.stream.anchor().reference
            w.appearance.update('size',24);spin(lambda:r.layout_ready)
            self.assertIsNone(r.clicked_reference)
            r.clicked_reference=r.stream.anchor().reference;r.go_to_reference('Gen.1.1')
            self.assertIsNone(r.clicked_reference)

    def test_deferred_native_selection_clear_is_restored_after_reflow(self):
        with self.profile() as directory:
            w=self.window(directory);r=self.entered(w)
            w.appearance.update('size',64);spin(lambda:r.layout_ready)
            buffer=r.views[0].get_buffer()
            buffer.select_range(buffer.get_iter_at_offset(2),buffer.get_iter_at_offset(11))
            expected=buffer.get_text(*buffer.get_selection_bounds(),False)
            cleared=[]
            def deferred_clear(*_):
                if r.stream.cursor is None:return True
                # Simulate GTK moving the native marks during font allocation,
                # after render, before stable frames restore the canonical range.
                buffer.place_cursor(buffer.get_start_iter());cleared.append(True)
                return False
            w.appearance.update('size',24);r.add_tick_callback(deferred_clear)
            spin(lambda:r.layout_ready)
            self.assertTrue(cleared);self.assertTrue(r.any_selection())
            copied=[];r.views[0].emit('copy-clipboard')
            r.get_clipboard().read_text_async(None,lambda c,result:copied.append(c.read_text_finish(result)))
            spin(lambda:bool(copied));self.assertEqual(copied[0],expected)

    def test_profile_closes_window_before_resources_even_after_failure(self):
        with self.assertRaisesRegex(RuntimeError,'test interruption'):
            with self.profile() as directory:
                w=self.window(directory);self.entered(w)
                raise RuntimeError('test interruption')
        self.assertTrue(w.closed)
        self.assertFalse(Path(directory).exists())

    def test_exit_during_preparation_cancels_worker_and_keeps_reading_state(self):
        from concurrent.futures import CancelledError
        from threading import Event
        import time
        from unittest.mock import patch
        from bible.book_stream import BookStream
        from bible.preparation import checkpoint
        entered, cancelled, release = Event(), Event(), Event()
        build = BookStream.build

        def delayed(stream, key, preferences, width, height, anchor, is_cancelled=None):
            entered.set()
            deadline = time.monotonic() + 3
            try:
                while not release.wait(.005):
                    checkpoint(is_cancelled)
                    if time.monotonic() > deadline:
                        raise TimeoutError('Preparation was neither released nor cancelled')
            except CancelledError:
                cancelled.set()
                raise
            return build(stream, key, preferences, width, height, anchor, is_cancelled)

        with self.profile() as directory:
            w = self.window(directory)
            tab = w.active_tab
            reference, tabs = tab.state.reference, w.tabs()
            try:
                with patch.object(BookStream, 'build', delayed):
                    self.assertTrue(w.enter_immersion())
                    reading = w.immersion
                    spin(entered.is_set)
                    self.assertIsNone(reading.stream.cursor)
                    w.leave_immersion()
                self.assertIsNone(w.immersion)
                self.assertTrue(cancelled.is_set())
                self.assertTrue(reading.stream.closed)
                self.assertTrue(all(not thread.is_alive() for thread in reading.stream.executor._threads))
                self.assertEqual(tab.state.reference, reference)
                self.assertEqual(w.tabs(), tabs)
                self.assertIs(w.active_tab, tab)
            finally:
                release.set()

    def test_commentary_inline_formatting_survives_highlight_integration(self):
        with self.profile() as directory:
            w=self.window(directory);tab=w.active_tab
            tab.state.commentary='Notes';w.study_button.set_active(True);w.update_navigation();spin()
            r=self.entered(w,'commentary')
            from bible.pagination import StyleSpan
            for address in r.addresses:
                document=r.stream.plan(address.key).document
                document.styles=(*document.styles,StyleSpan('hidden',0,1),StyleSpan('italic',1,5))
            r.render();spin(lambda:r.layout_ready)
            for view in r.views[:len(r.addresses)]:
                table=view.get_buffer().get_tag_table()
                self.assertIsNotNone(table.lookup('source-hidden'))
                self.assertEqual(table.lookup('source-hidden').props.scale,0)
                self.assertIsNotNone(table.lookup('source-italic'))
