"""Study typography, adaptive width, canonical context and draft identity."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from bible.study_settings import StudySettings


class StudySettingsTests(unittest.TestCase):
    def test_atomic_preferences_and_preserved_unsupported_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'study-preferences.json'
            settings=StudySettings(path);settings.width=537;settings.tool='notes';settings.save()
            restored=StudySettings(path)
            self.assertEqual((restored.width,restored.tool),(537,'notes'))
            path.write_text('{"version":2,"width":600,"tool":"future"}')
            original=path.read_bytes();invalid=StudySettings(path)
            self.assertTrue(invalid.error)
            with self.assertRaises(ValueError):invalid.save()
            self.assertEqual(path.read_bytes(),original)


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class PassageStudyTests(unittest.TestCase):
    def window(self, directory):
        from bible.ui import Application, Window, Library
        app=Application.get_default() or Application();app.register()
        window=Window(app,Library(Path(directory)/'translations'))
        window.set_default_size(1100,850);window.present()
        return window

    def test_fixed_commentary_typography_and_saved_width_under_narrow_clamping(self):
        from tests.test_ui import installed_fixture,spin
        from tests.test_commentary import commentary_fixture
        from gi.repository import Gdk
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,long_text=True);commentary_fixture(directory,'Notes')
            window=self.window(directory)
            try:
                tab=window.active_tab;tab.state.commentary='Notes'
                window.study_button.set_active(True);window.study.refresh()
                spin(lambda:not tab._restoring_scroll and not window.study._positioning)
                buffer=window.study.text.get_buffer();text=buffer.props.text
                typography=buffer.get_tag_table().lookup('reader-typography')
                self.assertEqual(typography.props.family,'sans-serif')
                self.assertEqual(typography.props.size_points,12)
                self.assertAlmostEqual(typography.props.line_height,1.5)
                window.appearance.update('size',30);window.appearance.update('line_spacing','very-airy')
                window.appearance.update('column_width','wide');spin()
                self.assertEqual(typography.props.size_points,12)
                self.assertEqual(buffer.props.text,text)
                self.assertEqual(window.study.text.get_pixels_inside_wrap(),0)
                self.assertEqual(window.study.text.get_left_margin(),24)
                history=list(tab.state.history)
                window.study_divider.key(None,Gdk.KEY_Left,0,0);spin()
                preferred=window.study_settings.width
                self.assertGreater(preferred,420)
                self.assertAlmostEqual(window.split.get_sidebar().get_width(),preferred,delta=2)
                window.study_divider.begin()
                window.study_button.set_active(False)
                self.assertFalse(window._study_resizing)
                self.assertFalse(window.study_divider.active)
                window.study_button.set_active(True);spin()
                window.set_default_size(360,850);spin(lambda:window.split.get_collapsed())
                self.assertEqual(window.study_settings.width,preferred)
                self.assertFalse(window.study_divider.get_visible())
                window.set_default_size(1100,850);spin(lambda:not window.split.get_collapsed())
                self.assertEqual(window.study_settings.width,preferred)
                self.assertAlmostEqual(window.split.get_sidebar().get_width(),preferred,delta=2)
                self.assertEqual(tab.state.history,history)
                self.assertEqual(window.study.text.get_buffer().props.text,text)
            finally:window.close()
            restored=self.window(directory)
            try:self.assertEqual(restored.study_settings.width,preferred)
            finally:restored.close()

    def test_contextual_range_notes_highlights_and_captured_draft_across_sources(self):
        from tests.test_ui import installed_fixture,spin
        from bible.notes_window import buffer_text
        with tempfile.TemporaryDirectory() as directory:
            entries=[('Ps.3.1','SYNTHETIC HEADING'),('Ps.3.2','SYNTHETIC VERSE TWO'),('Ps.3.3','SYNTHETIC VERSE THREE')]
            installed_fixture(directory,'Segond',entries=entries,versification='Segond')
            installed_fixture(directory,'Base',entries=entries)
            window=self.window(directory)
            try:
                window.active_tab.navigate('Segond','Ps.3.2')
                context=dict(versification='KJV',start='Ps.3.1',end='Ps.3.2',origin_translation='Base',origin_language='en')
                first=window.notes_store.save('FIRST **saved note**',('Study',),**context)
                second=window.notes_store.save('SECOND <literal> note',(),**context)
                window.highlights.set('KJV',['Ps.3.1'],'blue','Base')
                window.study_button.set_active(True);window.study.tools.set_visible_child_name('notes');spin()
                notes=window.study.notes
                self.assertEqual({n.id for n in notes.rows},{first.id,second.id})
                self.assertEqual(len(notes.marks),1)
                self.assertEqual(notes.marks[0]['reference'],'Ps.3.1')
                self.assertFalse(window.study.immersive_button.get_visible())
                self.assertEqual(window.study.tools.get_pages().get_n_items(),2)
                notes.add_note();editor=window.note_editor
                editor.body.get_buffer().set_text('DRAFT WITH FIXED TARGET')
                captured=dict(editor.context)
                window.active_tab.navigate('Base','Ps.3.3');spin()
                self.assertEqual(editor.context,captured)
                self.assertEqual(buffer_text(editor.body),'DRAFT WITH FIXED TARGET')
                self.assertTrue(editor.save())
                saved=next(n for n in window.notes_store.all() if n.body=='DRAFT WITH FIXED TARGET')
                self.assertEqual((saved.versification,saved.start),('Segond','Ps.3.2'))
                window.active_tab.navigate('Segond','Ps.3.3');spin()
                self.assertEqual({n.id for n in notes.rows},{first.id,second.id})
                self.assertEqual(window.notes_store.get(first.id).body,'FIRST **saved note**')
                self.assertEqual(window.highlights.entries[('KJV','Ps.3.1')]['color'],'blue')
            finally:window.close()
            restored=self.window(directory)
            try:self.assertEqual(restored.study.tool,'notes')
            finally:restored.close()

    def test_tool_switching_stops_hidden_commentary_following(self):
        from tests.test_ui import installed_fixture,spin
        from tests.test_commentary import commentary_fixture
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,long_text=True);commentary_fixture(directory,'Notes')
            window=self.window(directory)
            try:
                tab=window.active_tab;tab.state.commentary='Notes'
                window.study_button.set_active(True);window.study.refresh()
                spin(lambda:not tab._restoring_scroll and not window.study._positioning)
                before=(tab.state.reference,list(tab.state.history))
                window.study.tools.set_visible_child_name('notes')
                window.reading_sync.driver='commentary';window.reading_sync.needs_sync=True
                window.reading_sync.synchronize();spin()
                self.assertEqual((tab.state.reference,tab.state.history),before)
                self.assertIsNone(tab._study_coverage)
                window.study.tools.set_visible_child_name('commentaries');spin()
                self.assertTrue(window.study.text.get_mapped())
                self.assertIn('COMMENTARY TEST DATA',window.study.text.get_buffer().props.text)
            finally:window.close()
