"""Shared full/express settings, legacy persistence and actual reading reflow."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from bible.preferences import Preferences,ReadingPreferences
from bible.reading_metrics import line_spacing,text_width


class ReadingPreferenceDataTests(unittest.TestCase):
    def test_legacy_defaults_custom_values_and_future_files_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'reading.json';path.write_text('{"font":"Serif","size":24,"line_spacing":"airy","column_width":"wide"}')
            p=Preferences(path);self.assertTrue(p.writable)
            self.assertEqual((p.value.study_font,line_spacing(p.value),text_width(p.value)),('sans-serif',10,960))
            p.value.line_spacing_px=12;p.value.text_width_px=713;p.value.side_margin_px=82
            p.value.study_font='Absent test family';p.value.alignment='justified';p.value.immersion_columns='one';p.save()
            self.assertEqual(Preferences(path).value,p.value)
            value=json.loads(path.read_text());value['version']=99;path.write_text(json.dumps(value))
            original=path.read_bytes();future=Preferences(path);self.assertFalse(future.writable)
            with self.assertRaises(ValueError):future.save()
            self.assertEqual(path.read_bytes(),original)


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ReadingSettingsTests(unittest.TestCase):
    def test_full_express_custom_roundtrip_independent_study_font_and_reset(self):
        from bible.ui import Application,Window,Library,Gtk
        from bible.application_surfaces import show_preferences
        from tests.test_ui import installed_fixture,spin
        from tests.test_reading_sync import linked_commentary
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed_fixture(root,long_text=True);linked_commentary(root)
            app=Application.get_default() or Application();app.register();w=Window(app,Library(root/'translations'));w.present();spin()
            try:
                original=w.active_tab.state.reference;d=show_preferences(w);full=d.reading_settings
                full.line_spacing_px.set_value(12);full.text_width_px.set_value(713);full.side_margin_px.set_value(82)
                full.size.set_value(23);spin(lambda:not w.appearance._apply_id,duration=.2)
                p=w.preferences.value
                self.assertEqual((p.size,p.line_spacing_px,p.text_width_px,p.side_margin_px),(23,12,713,82))
                self.assertIn('12 px',w.appearance.line_spacing.get_model().get_string(w.appearance.line_spacing.get_selected()))
                self.assertIn('713 px',w.appearance.column_width.get_model().get_string(w.appearance.column_width.get_selected()))
                d.close();spin();d=show_preferences(w);full=d.reading_settings
                self.assertEqual((full.line_spacing_px.get_value(),full.text_width_px.get_value()),(12,713))
                self.assertEqual(Preferences(root/'reading-preferences.json').value,p)
                w.appearance.update('line_spacing','normal');w.appearance.update('column_width','wide');spin()
                self.assertIsNone(p.line_spacing_px);self.assertIsNone(p.text_width_px)
                self.assertEqual((full.line_spacing_px.get_value(),full.text_width_px.get_value()),(5,960))
                full.update('study_font','Saved unavailable study family');spin(lambda:not w.appearance._apply_id)
                self.assertEqual(p.study_font,'Saved unavailable study family')
                self.assertIn('Saved unavailable study family',full.study_font._family_row.get_subtitle())
                full.update('study_font','DejaVu Sans Mono');spin(lambda:not w.appearance._apply_id)
                self.assertEqual(p.font,'DejaVu Serif');self.assertEqual(w.study.sidebar_preferences.font,'DejaVu Sans Mono')
                full.update('font','DejaVu Sans');spin(lambda:not w.appearance._apply_id)
                self.assertEqual(p.study_font,'DejaVu Sans Mono')
                full.update('immersion_columns','one');d.close();spin()
                w.enter_immersion('bible');spin(lambda:w.immersion.layout_ready,timeout=15)
                self.assertEqual(w.immersion.count,1)
                before=w.immersion.stream.anchor();w.appearance.update('alignment','justified')
                spin(lambda:w.immersion.layout_ready,duration=.2)
                self.assertEqual(w.immersion.stream.anchor(),before)
                self.assertEqual(w.immersion.views[0].get_justification(),Gtk.Justification.FILL)
                w.leave_immersion();w.appearance.reset();spin()
                self.assertEqual(p,ReadingPreferences());self.assertEqual(w.active_tab.state.reference,original)
            finally:
                if getattr(w,'preferences_window',None):w.preferences_window.close()
                w.close()
