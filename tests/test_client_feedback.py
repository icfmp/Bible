"""Client acceptance regressions for the visible workspace and reader corrections."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ClientFeedbackTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        installed_fixture(self.root,long_text=True)
        self.app=Application.get_default() or Application();self.app.register()
        self.w=Window(self.app,Library(self.root/'translations'));self.w.present();spin()
    def tearDown(self):self.w.close()

    def test_visible_workspace_group_switches_both_ways_in_one_activation(self):
        from bible.ui import Gtk
        w=self.w;group=w.space_selector
        self.assertEqual(len(group.buttons),2)
        self.assertTrue(all(isinstance(b,Gtk.ToggleButton) and b.get_mapped() for b in group.buttons))
        original=w.active_tab.state.reference
        group.buttons[1].set_active(True);spin()
        self.assertEqual(w.main_pages.get_visible_child_name(),'notes')
        self.assertEqual(group.get_selected(),1)
        w.notes_space.space_selector.buttons[0].set_active(True);spin()
        self.assertEqual(w.main_pages.get_visible_child_name(),'reading')
        self.assertEqual(group.get_selected(),0)
        self.assertEqual(w.active_tab.state.reference,original)
        self.assertEqual(sum(b.get_active() for b in group.buttons),1)
        group.buttons[0].emit('clicked');spin()
        self.assertEqual(sum(b.get_active() for b in group.buttons),1)

    def test_preferences_direct_theme_choices_and_backup_rows_use_existing_actions(self):
        from bible.application_surfaces import show_preferences
        from bible.ui import Gtk
        d=show_preferences(self.w);spin()
        self.assertIsInstance(d.language,Gtk.DropDown)
        self.assertEqual(len(d.appearance.buttons),3)
        d.appearance.buttons[2].set_active(True);spin()
        self.assertEqual(self.w.application_settings.value['interface_appearance'],'dark')
        with patch('bible.application_surfaces.choose_personal_backup') as choose:
            d.backup_actions[0].emit('activated');d.backup_actions[1].emit('activated')
            self.assertEqual([call.args[-1] for call in choose.call_args_list],[False,True])
        d.close();spin()

    def test_shared_immersive_reading_box_stays_centered_when_controls_fade(self):
        w=self.w;w.set_default_size(1280,900);spin();w.enter_immersion('bible');v=w.immersion
        spin(lambda:v.layout_ready and hasattr(v,'reading_box'),timeout=15)
        top,capacity=v.reading_box
        self.assertLessEqual(abs(top-(v.get_height()-top-capacity)),2)
        self.assertEqual(v.views[0].get_top_margin(),v.views[1].get_top_margin())
        anchor=v.stream.anchor();geometry=v._geometry;bounds=v.reading_box
        v.hide_controls();spin(duration=.4)
        self.assertEqual(v.reading_box,bounds);self.assertEqual(v._geometry,geometry)
        self.assertEqual(v.stream.anchor(),anchor)
        v.reveal_controls();spin(duration=.4)
        self.assertEqual(v.reading_box,bounds);self.assertEqual(v.stream.anchor(),anchor)

    def test_immersive_keyboard_focus_stays_outside_the_moving_pages(self):
        w=self.w;w.enter_immersion('bible');v=w.immersion
        spin(lambda:v.layout_ready,timeout=15)
        w.set_focus_visible(True);v.views[0].grab_focus();spin()
        self.assertTrue(v.focus_cue.get_visible())
        self.assertFalse(v.focus_cue.get_can_target())
        self.assertFalse(v.focus_cue.is_ancestor(v.page_clamp))
        original=v.stream.cursor
        self.assertTrue(v.turn(1));spin(lambda:v.layout_ready)
        self.assertNotEqual(v.stream.cursor,original)
        self.assertTrue(v.focus_cue.get_visible())
        w.set_focus_visible(False);spin()
        self.assertFalse(v.focus_cue.get_visible())
        w.set_focus_visible(True);v.leave_button.grab_focus();spin()
        self.assertFalse(v.focus_cue.get_visible())
        self.assertIs(w.get_focus(),v.leave_button)

    def test_semantic_click_never_manufactures_selection_or_bar_and_collapse_hides(self):
        t=self.w.active_tab;a=self.w.passage_actions;b=t.text.get_buffer();offset=t._marker_ends['Gen.1.1']+3
        factory=lambda:a.ordinary(t)
        a.capture(t.text,factory,offset);spin()
        self.assertFalse(a.bar.get_visible());self.assertFalse(b.get_has_selection());self.assertIsNone(a.target)
        b.select_range(b.get_iter_at_offset(offset),b.get_iter_at_offset(offset+5));a.capture(t.text,factory,None);spin()
        self.assertTrue(a.bar.get_visible())
        self.assertIs(a.copy_button,a.copy_options)
        self.assertEqual(a.copy_button.get_child().get_icon_name(),'edit-copy-symbolic')
        self.assertIs(a.actions.get_first_child(),a.copy_button)
        b.place_cursor(b.get_iter_at_offset(offset));spin()
        self.assertFalse(a.bar.get_visible());self.assertIsNone(a.target)

    def test_context_commands_keep_comparison_source_without_floating_selection(self):
        installed_fixture(self.root,'Other',versification='Segond')
        w=self.w;t=w.active_tab;t.state.comparison='Other';w.sync_comparison();spin()
        b=t.comparison_text.get_buffer();b.place_cursor(b.get_iter_at_offset(t._comparison_markers['Gen.1.2']+2))
        t.comparison_text._passage_context.activate_action('action0',None);spin()
        self.assertEqual(w.note_editor.context['origin_translation'],'Other')
        self.assertEqual(w.note_editor.context['versification'],'Segond')
        self.assertFalse(w.passage_actions.bar.get_visible());self.assertFalse(b.get_has_selection())
        w.note_editor.close();spin()

    def test_dismiss_releases_backdrop_source_signals_and_selection_timer(self):
        t=self.w.active_tab;a=self.w.passage_actions;b=t.text.get_buffer();offset=t._marker_ends['Gen.1.1']+3
        b.select_range(b.get_iter_at_offset(offset),b.get_iter_at_offset(offset+5))
        a.capture(t.text,lambda:a.ordinary(t),None);spin()
        paintable=a.bar.backdrop;handlers=a.bar._backdrop_signals
        self.assertIs(paintable.get_widget(),t.text)
        a.capture(t.text,lambda:a.ordinary(t),None);spin()
        self.assertIs(a.bar.backdrop,paintable,'Reuse GTK paintable for an unchanged source')
        spin(lambda:a.adapt_tick==0,duration=.1)
        a.dismiss()
        self.assertIsNone(a.bar.backdrop);self.assertIsNone(paintable.get_widget());self.assertEqual(a.adapt_tick,0)
        self.assertTrue(all(not paintable.handler_is_connected(handler) for handler in handlers))
        self.assertFalse(a.bar.get_visible());self.assertTrue(b.get_has_selection())
