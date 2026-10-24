"""Native regression coverage for the October desktop finishing batch."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import spin,installed_fixture
from bible.i18n import tr

@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class FinishingTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()));installed_fixture(self.root,long_text=True)
        self.app=Application.get_default() or Application();self.app.register()
        self.window=Window(self.app,Library(self.root/'translations'));self.window.present();spin()
    def tearDown(self):self.window.close()

    def test_tab_strip_allocations_and_per_tab_palette_survive_restart(self):
        from bible.ui import Window
        w=self.window;first=w.active_tab
        self.assertFalse(w.bar.get_visible());self.assertTrue(w.new_tab_button.get_mapped())
        w.appearance.update('mode','day');w.appearance.update('day_palette','paper')
        second=w.new_tab();spin();self.assertTrue(w.bar.get_mapped())
        w.appearance.update('mode','night');w.appearance.update('night_palette','black')
        w.view.set_selected_page(w.view.get_page(first));spin()
        self.assertEqual(w.reading_style.palette,'paper');self.assertEqual(second.state.reading_palette['night_palette'],'black')
        w.close();self.window=w=Window(self.app,w.library);w.present();spin()
        self.assertEqual(w.reading_style.palette,'paper');self.assertTrue(w.bar.get_mapped())
        w.view.close_page(w.view.get_nth_page(1));spin();self.assertFalse(w.bar.get_visible())
        self.assertEqual(w.active_tab.state.reference,first.state.reference)

    def test_one_click_lists_and_canvas_tooltip(self):
        from bible.version_chooser import DirectChoices
        installed_fixture(self.root,'Other')
        w=self.window;w.sync_comparison();self.assertIsNone(w.active_tab.text.get_tooltip_text())
        w.primary_version.popup();spin();self.assertTrue(w.primary_version.choices.get_mapped())
        self.assertIsInstance(w.primary_version.choices,DirectChoices)
        self.assertTrue(w.primary_version.choices.list.get_row_at_index(0).get_mapped());w.primary_version.popdown()
        w.comparison_button.popup();spin();self.assertIsInstance(w.comparison_choices,DirectChoices)
        self.assertTrue(w.comparison_choices.list.get_row_at_index(0).get_mapped())
        for index,expected in ((1,w._comparison_names[1]),(0,None),(0,None)):
            if not w.comparison_popover.get_visible():w.comparison_button.popup();spin()
            w.comparison_choices.list.emit('row-activated',w.comparison_choices.list.get_row_at_index(index));spin()
            self.assertEqual(w.active_tab.state.comparison,expected)
            self.assertFalse(w.comparison_popover.get_visible())

    def test_immersive_turns_cancel_on_resize_and_disabled_animations(self):
        from bible.ui import Gtk
        w=self.window;w.enter_immersion('bible');v=w.immersion;spin(lambda:v.layout_ready,timeout=10)
        initial=v.stream.anchor();self.assertTrue(v.turn(1));spin(duration=.04)
        self.assertNotEqual(initial,v.stream.anchor());self.assertEqual(v.page_stack.get_transition_duration(),200)
        self.assertTrue(v.turn(-1));spin(duration=.3)
        self.assertEqual(v.page_stack.get_visible_child_name(),'live')
        w.set_default_size(800,650);spin(lambda:v.layout_ready);self.assertIsNone(v.previous_page.get_paintable())
        settings=Gtk.Settings.get_default();old=settings.get_property('gtk-enable-animations')
        try:
            settings.set_property('gtk-enable-animations',False);v.turn(1);spin()
            self.assertIsNone(v.previous_page.get_paintable())
        finally:settings.set_property('gtk-enable-animations',old)

    def test_catalogue_loading_zero_failure_and_retained_rows_are_distinct(self):
        from dataclasses import replace
        from bible.catalogue_window import CatalogueWindow
        from bible.providers import PROVIDERS
        with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
            w=self.window;w.application_settings.set('library_language','');d=CatalogueWindow(w,w.library,w.resource_installed);d.present();spin(lambda:not d.preparing)
            snapshot=d.session.snapshot
            d.resources=[];d._installed_metadata={};d.filtered_resources=[];d.preparing=True;d.update_result_state()
            self.assertEqual(d.result_pages.get_visible_child_name(),'loading')
            d._catalogue_requested=True
            d.apply_snapshot(replace(snapshot,resources=(),installed={},covered_providers=frozenset(p.id for p in PROVIDERS)));spin()
            self.assertEqual(d.result_pages.get_visible_child_name(),'empty');self.assertEqual(d.empty_page.get_title(),tr('No Bible found'))
            d.apply_snapshot(replace(snapshot,resources=(),installed={},errors={'Library':'offline'}));spin()
            self.assertEqual(d.empty_page.get_title(),tr('Catalogue unavailable'))
            d.apply_snapshot(replace(snapshot,refreshing=True));spin()
            self.assertEqual(d.result_pages.get_visible_child_name(),'rows');self.assertTrue(d.catalogue_progress.get_visible())
            d.close();spin()

    def test_unreadable_installed_metadata_keeps_welcome_and_original_files(self):
        from bible.ui import Window
        w=self.window;w.close()
        conf=self.root/'translations/Test/mods.d/test.conf';original=conf.read_bytes();conf.write_bytes(b'not a module configuration')
        self.window=w=Window(self.app,w.library);w.present();spin()
        self.assertEqual(w.main_pages.get_visible_child_name(),'welcome');self.assertTrue(w.startup_resource_error)
        self.assertEqual(conf.read_bytes(),b'not a module configuration')
        w.open_notes();spin();self.assertEqual(w.main_pages.get_visible_child_name(),'notes')
        w.return_to_reading();self.assertEqual(w.main_pages.get_visible_child_name(),'welcome')
        conf.write_bytes(original)

    def test_immersion_hides_saved_marks_without_changing_preferences_or_storage(self):
        w=self.window;tab=w.active_tab;w.highlights.set('KJV',['Gen.1.1'],'green','Test');w.refresh_highlights()
        original=w.highlights.path.read_bytes();prefs=w.preferences.path.read_bytes() if w.preferences.path.exists() else None
        offset=tab._marker_ends['Gen.1.1']+2
        self.assertTrue(tab.text.get_buffer().get_iter_at_offset(offset).has_tag(tab.text.get_buffer().get_tag_table().lookup('highlight-green')))
        w.enter_immersion('bible');v=w.immersion;spin(lambda:v.layout_ready,timeout=10)
        for view in v.views:
            b=view.get_buffer();tag=b.get_tag_table().lookup('highlight-green')
            if tag:
                self.assertFalse(any(b.get_iter_at_offset(i).has_tag(tag) for i in range(b.get_char_count())))
        self.assertEqual(w.highlights.path.read_bytes(),original);self.assertTrue(w.preferences.value.show_highlights)
        w.leave_immersion();spin()
        self.assertTrue(tab.text.get_buffer().get_iter_at_offset(offset).has_tag(tab.text.get_buffer().get_tag_table().lookup('highlight-green')))
        self.assertEqual(w.highlights.path.read_bytes(),original)
        self.assertEqual(w.preferences.path.read_bytes() if w.preferences.path.exists() else None,prefs)

    def test_action_surface_stays_dark_and_readable_after_repeated_native_redraw(self):
        import ctypes
        from tools.check_alpha_ui import X11Input
        w=self.window;w.set_default_size(800,600);w.appearance.update('mode','day');spin()
        tab=w.active_tab;actions=w.passage_actions
        actions.capture(tab.text,lambda:actions.ordinary(tab),tab._marker_ends['Gen.1.1']+3);spin()
        native=X11Input();x=native.x11;pointer=ctypes.c_void_p;ulong=ctypes.c_ulong
        x.XGetImage.argtypes=[pointer,ulong,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint,ulong,ctypes.c_int];x.XGetImage.restype=pointer
        x.XGetPixel.argtypes=[pointer,ctypes.c_int,ctypes.c_int];x.XGetPixel.restype=ulong
        x.XDestroyImage.argtypes=[pointer];x.XDestroyImage.restype=ctypes.c_int
        try:
            native.activate(w)
            for _ in range(3):
                actions.bar.queue_draw();actions.bar.get_child().queue_draw();spin(duration=.2)
                found,bounds=actions.bar.compute_bounds(w);self.assertTrue(found)
                rx,ry,child=ctypes.c_int(),ctypes.c_int(),ulong()
                self.assertTrue(x.XTranslateCoordinates(native.display,w.get_surface().get_xid(),x.XDefaultRootWindow(native.display),0,0,ctypes.byref(rx),ctypes.byref(ry),ctypes.byref(child)))
                scale=w.get_scale_factor();dx,dy=w.get_surface_transform()
                width,height=round(bounds.size.width*scale),round(bounds.size.height*scale)
                image=x.XGetImage(native.display,x.XDefaultRootWindow(native.display),rx.value+round((dx+bounds.origin.x)*scale),ry.value+round((dy+bounds.origin.y)*scale),width,height,ulong(-1),2)
                self.assertTrue(image)
                try:
                    colors=[tuple((x.XGetPixel(image,px,py)>>shift)&255 for shift in (16,8,0)) for py in range(height) for px in range(width)]
                finally:x.XDestroyImage(image)
                self.assertGreater(sum(max(c)<110 for c in colors),len(colors)*.6)
                self.assertGreater(sum(min(c)>220 for c in colors),100)
                self.assertTrue(actions.bar.get_mapped());self.assertEqual(actions.target.references,('Gen.1.1',))
        finally:native.close()

    def test_reference_opened_tab_keeps_inherited_palette_after_switch_and_restart(self):
        from bible.ui import Window
        w=self.window;first=w.active_tab
        w.appearance.update('mode','day');w.appearance.update('day_palette','paper')
        w.new_tab();w.appearance.update('mode','night');w.appearance.update('night_palette','black')
        self.assertTrue(w.navigate_selection('Test','Gen.1.2',new_tab=True))
        self.assertEqual(w.reading_style.palette,'black')
        w.view.set_selected_page(w.view.get_page(first));spin()
        self.assertEqual(w.reading_style.palette,'paper')
        w.close();self.window=w=Window(self.app,w.library);w.present();spin()
        self.assertEqual(w.reading_style.palette,'paper')
        w.view.set_selected_page(w.view.get_nth_page(2));spin()
        self.assertEqual(w.reading_style.palette,'black');self.assertEqual(w.active_tab.state.reference,'Gen.1.2')

    def test_wide_immersive_arrows_hold_hover_and_mouse_focus_does_not_pin_chrome(self):
        from bible.ui import GLib
        w=self.window;w.set_size_request(1800,700);w.set_default_size(1920,1000);spin()
        w.enter_immersion('bible');v=w.immersion;spin(lambda:v.layout_ready,timeout=10)
        geometry=v._geometry;v.views[0].grab_focus();w.set_focus_visible(False);v.reveal_controls();spin()
        found,bounds=v.nav_revealers[1].compute_bounds(v);self.assertTrue(found)
        x,y=bounds.origin.x+bounds.size.width/2,bounds.origin.y+bounds.size.height/2
        self.assertTrue(75<x<v.get_width()-75)
        def hide():
            if v._hide_id:GLib.source_remove(v._hide_id);v._hide_id=0
            v.hide_controls()
        v.pointer_moved(None,x,y);hide();self.assertTrue(v.nav_revealers[1].get_reveal_child())
        v.pointer_moved(None,v.get_width()/2,v.get_height()/2);v.forward.grab_focus();w.set_focus_visible(False);hide();spin(duration=.3)
        self.assertFalse(v.top.get_reveal_child());self.assertFalse(v.nav_revealers[1].get_reveal_child())
        self.assertIs(w.get_focus(),v.views[0]);self.assertFalse(v.top.get_can_target())
        v.pointer_moved(None,v.get_width()/2,65);self.assertFalse(v.top.get_reveal_child())
        v.reveal_controls();v.leave_button.grab_focus();w.set_focus_visible(True);hide()
        self.assertTrue(v.top.get_reveal_child());self.assertEqual(v._geometry,geometry)
