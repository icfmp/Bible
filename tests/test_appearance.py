"""Reader settings and live native libadwaita style changes, without a portal."""
import ctypes
import os
from pathlib import Path
import tempfile
import unittest

from bible.preferences import Preferences, ReadingPreferences
from bible.reading_style import PALETTES, effective_palette


def contrast(a,b):
    def luminance(color):
        rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        rgb=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
        return sum(x*w for x,w in zip(rgb,(.2126,.7152,.0722)))
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)


class SystemStyleOverride:
    """Test only: upstream's private settings override API, never product code.

    Signatures checked against libadwaita 1.7 src/adw-settings-private.h. This
    emulates preference notifications, not a real GNOME portal integration.
    """
    def __enter__(self):
        self.lib=ctypes.CDLL('libadwaita-1.so.0')
        self.lib.adw_settings_get_default.restype=ctypes.c_void_p
        self.settings=self.lib.adw_settings_get_default()
        for suffix in ['start_override','end_override']:
            getattr(self.lib,'adw_settings_'+suffix).argtypes=[ctypes.c_void_p]
        for suffix in ['high_contrast','color_scheme','system_supports_color_schemes']:
            getattr(self.lib,'adw_settings_override_'+suffix).argtypes=[ctypes.c_void_p,ctypes.c_int]
        self.lib.adw_settings_start_override(self.settings)
        self.lib.adw_settings_override_system_supports_color_schemes(self.settings,1)
        self.set(dark=False,high=False)
        return self

    def set(self,*,dark,high):
        self.lib.adw_settings_override_color_scheme(self.settings,1 if dark else 2)
        self.lib.adw_settings_override_high_contrast(self.settings,int(high))

    def __exit__(self,*_):self.lib.adw_settings_end_override(self.settings)


class PaletteTests(unittest.TestCase):
    def test_approved_defaults_missing_fields_and_saved_choices(self):
        from bible.reading_style import SPACING
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'reading.json'
            value=Preferences(path).value
            self.assertEqual((value.size,value.line_spacing,value.column_width),(14,'very-airy','narrow'))
            path.write_text('{"size":19,"line_spacing":"normal","column_width":"wide"}')
            saved=Preferences(path)
            self.assertEqual((saved.value.size,saved.value.line_spacing,saved.value.column_width),(19,'normal','wide'))
            saved.value.line_spacing='very-airy';saved.save()
            self.assertEqual(Preferences(path).value.line_spacing,'very-airy')
            self.assertGreater(SPACING['very-airy'],SPACING['airy'])
    def test_contrast_text_links_numbers_selection_all_palettes(self):
        for name,(bg,fg,link,selection,selected) in PALETTES.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(contrast(bg,fg),7)
                self.assertGreaterEqual(contrast(bg,link),4.5)
                self.assertGreaterEqual(contrast(selection,selected),7 if name.startswith('contrast') else 4.5)

    def test_preferences_legacy_and_new_fields_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'appearance.json';path.write_text('{"font":"Serif","size":24}')
            p=Preferences(path);self.assertTrue(p.writable);self.assertEqual(p.value.mode,'system')
            p.value.day_palette='paper';p.value.night_palette='black';p.value.mode='night'
            p.value.line_spacing='airy';p.value.column_width='wide';p.value.size=64
            p.save();self.assertEqual(Preferences(path).value,p.value)
            self.assertEqual(effective_palette(p.value,False,True),'contrast-day')
            self.assertEqual(effective_palette(p.value,True,True),'contrast-night')
            self.assertEqual(effective_palette(p.value,False,False),'paper')
            self.assertEqual(effective_palette(p.value,True,False),'black')


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires real GTK under Xvfb')
class AppearanceTests(unittest.TestCase):
    def test_controls_follow_active_bible_overlay_and_reference_field_is_visible(self):
        from bible.ui import Window,Library
        from tests.test_ui import installed_fixture,spin
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window=Window(self.app,Library(Path(directory)/'translations'));window.present()
            try:
                spin()
                self.assertIs(window.reader_controls.get_parent(),window.active_tab.reading_overlay)
                first=window.reader_controls.get_first_child()
                self.assertIs(first,window.comparison_button)
                self.assertIs(first.get_next_sibling(),window.appearance_button)
                self.assertIs(window.appearance_button.get_next_sibling(),window.immersive_button)
                window.new_tab();spin()
                self.assertIs(window.reader_controls.get_parent(),window.active_tab.reading_overlay)
                window.choose_passage(direct=True);spin()
                self.assertTrue(window.navigation.direct.get_mapped())
                self.assertIs(window.navigation.content.get_first_child(),window.navigation.direct)
            finally:window.close()
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application
        cls.app=Application.get_default() or Application();cls.app.register()

    def test_live_modes_contrast_and_restore_do_not_change_passage(self):
        from bible.ui import Window,Library
        from tests.test_ui import installed_fixture,spin
        from tests.fixtures import module_fixture
        with tempfile.TemporaryDirectory() as directory, SystemStyleOverride() as system:
            installed_fixture(directory,long_text=True)
            root=Path(directory)/'translations'/'Comments'
            module_fixture(root,'Comments',[('Gen.1.1','COMMENTARY α — fixture only')],commentary=True)
            (root/'.complete').write_text('Comments')
            w=Window(self.app,Library(Path(directory)/'translations'));w.present()
            try:
                w.navigate_selection('Test','Gen.1.1');tab=w.active_tab;tab.state.commentary='Comments';w.study.refresh();spin()
                buffer=tab.text.get_buffer();start=tab._marker_ends['Gen.1.1']
                buffer.select_range(buffer.get_iter_at_offset(start+2),buffer.get_iter_at_offset(start+12))
                selection=buffer.get_text(*buffer.get_selection_bounds(),False)
                w.appearance.update('day_palette','paper');w.appearance.update('night_palette','black')
                self.assertEqual(w.preferences.value.mode,'system')
                self.assertEqual(w.reading_style.palette,'paper')
                for dark in (True,False):
                    system.set(dark=dark,high=False);spin()
                    self.assertEqual(w.reading_style.palette,'black' if dark else 'paper')
                    system.set(dark=dark,high=True);spin()
                    self.assertEqual(w.reading_style.palette,'contrast-night' if dark else 'contrast-day')
                    self.assertFalse(w.appearance.palettes['paper'].get_sensitive())
                    # Check the foreground actually computed by GTK on both readers.
                    expected=1.0 if dark else 0.0
                    for view in [tab.text,w.study.text]:
                        self.assertAlmostEqual(view.get_color().red,expected,places=2)
                    self.assertEqual(tab.state.reference,'Gen.1.1')
                    self.assertEqual(buffer.get_text(*buffer.get_selection_bounds(),False),selection)
                    self.assertIn('COMMENTARY',w.study.text.get_buffer().props.text)
                system.set(dark=False,high=False);spin()
                self.assertTrue(w.appearance.palettes['paper'].get_sensitive())
                w.appearance.update('mode','night');self.assertTrue(w.reading_style.manager.get_dark())
                w.appearance.update('mode','day');self.assertFalse(w.reading_style.manager.get_dark())
                self.assertEqual(w.preferences.value.night_palette,'black')
                self.assertEqual(w.preferences.value.day_palette,'paper')
                from bible.ui import Gtk
                theme=Gtk.IconTheme.get_for_display(w.get_display())
                for icon_name in ['bible-library-symbolic','bible-notes-symbolic']:
                    icon=theme.lookup_icon(icon_name,None,16,1,Gtk.TextDirection.LTR,Gtk.IconLookupFlags.FORCE_SYMBOLIC)
                    self.assertTrue(icon.is_symbolic(),icon_name)
            finally:w.close()

    def test_controls_selection_big_text_shared_tabs_and_restart(self):
        from bible.ui import Window,Library
        from tests.test_ui import installed_fixture,spin
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,long_text=True)
            library=Library(Path(directory)/'translations');w=Window(self.app,library);w.present()
            try:
                tab=w.active_tab;w.navigate_selection('Test','Gen.1.1');spin()
                buffer=tab.text.get_buffer();start=tab._marker_ends['Gen.1.1']
                buffer.select_range(buffer.get_iter_at_offset(start+3),buffer.get_iter_at_offset(start+19))
                before=buffer.get_text(*buffer.get_selection_bounds(),False)
                w.appearance.fonts['DejaVu Sans'].emit('clicked')
                self.assertEqual(w.preferences.value.font,'DejaVu Sans')
                w.appearance.larger.emit('clicked');self.assertEqual(w.preferences.value.size,15)
                w.appearance.smaller.emit('clicked');self.assertEqual(w.preferences.value.size,14)
                w.appearance.line_spacing.set_selected(2);w.appearance.column_width.set_selected(0)
                self.assertEqual(w.preferences.value.line_spacing,'airy')
                self.assertEqual(w.preferences.value.column_width,'narrow')
                w.appearance.verse_numbers.set_active(False);w.appearance.chapter_numbers.set_active(False)
                self.assertEqual(buffer.get_text(*buffer.get_selection_bounds(),False),before)
                self.assertEqual(tab.selected_passage(),('Gen.1.1','Gen.1.1'))
                w.appearance.update('size',64);w.set_default_size(360,650)
                spin(lambda:w.get_width()<=360 and not tab._restoring_scroll)
                self.assertFalse(w.appearance.larger.get_sensitive())
                self.assertLessEqual(w.get_width(),360)
                w.new_tab();self.assertIs(w.active_tab.preferences,tab.preferences)
                self.assertEqual(w.active_tab.preferences.size,64)
                reference=tab.state.reference;w.close()
                w=Window(self.app,library);w.present();spin()
                self.assertEqual(w.preferences.value.size,64)
                self.assertEqual(w.preferences.value.font,'DejaVu Sans')
                self.assertEqual(w.active_tab.state.reference,reference)
                note=w.notes_store.save('Retained note',[],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='Test',origin_language='en')
                w.appearance.reset();self.assertEqual(w.preferences.value,ReadingPreferences())
                self.assertEqual(w.notes_store.get(note.id).body,'Retained note')
                self.assertTrue(w.notes_store is not None)
            finally:w.close()

    def test_reflow_preserves_visible_body_anchor_and_non_latin_glyphs(self):
        from bible.ui import Window,Library
        from gi.repository import Pango
        from tests.test_ui import installed_fixture,spin
        entries=[(f'Gen.1.{i}',(f'VERSE {i} — données de test. '*100)) for i in range(1,11)]
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=entries)
            w=Window(self.app,Library(Path(directory)/'translations'));w.present()
            try:
                tab=w.active_tab;spin(lambda:not tab._restoring_scroll,duration=.3)
                adjustment=tab.scroll.get_vadjustment()
                adjustment.set_value((adjustment.get_upper()-adjustment.get_page_size())*.45);spin()
                def visible_anchor():
                    rect=tab.text.get_visible_rect()
                    _,iterator=tab.text.get_iter_at_location(rect.x,rect.y)
                    return tab.position_anchor(iterator.get_offset())
                before=visible_anchor();self.assertIsNotNone(before)
                w.appearance.update('size',32);w.appearance.update('column_width','narrow');spin(lambda:not tab._restoring_scroll,duration=.4)
                after=visible_anchor()
                self.assertEqual(after[0],before[0])
                self.assertLess(abs(after[1]-before[1]),120)
                for family in ('DejaVu Serif','DejaVu Sans'):
                    layout=tab.text.create_pango_layout('Écriture française — Ελληνικά עברית العربية')
                    layout.set_font_description(Pango.FontDescription(family+' 24'))
                    self.assertEqual(layout.get_unknown_glyphs_count(),0)
            finally:w.close()
