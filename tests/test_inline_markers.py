"""Inline objects are source-aware, independent and absent from copied Scripture."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK')
class InlineMarkerTests(unittest.TestCase):
    def test_notes_ranges_hidden_numbers_copy_and_live_edits(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[('Gen.1.1','First source words.'),('Gen.1.2','Second source words.'),('Gen.1.3','Third source words.')])
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(Path(directory)/'translations'));window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Test','Gen.1.1')
                original=tab._document.copy(0,len(tab._document.text))
                for start,end,body in [('Gen.1.1','Gen.1.2','A personal note'),('Gen.1.1','Gen.1.1','Another note')]:
                    window.notes_store.save(body,[],versification='KJV',start=start,end=end,origin_translation='Test',origin_language='en')
                window.highlights.set('KJV',['Gen.1.3'],'blue','Test')
                window.notes_changed();spin()
                self.assertEqual(len(tab.text._inline_buttons),1)
                self.assertEqual(tab._document.copy(0,len(tab._document.text)),original)
                self.assertNotIn('\ufffc',tab._document.copy(0,len(tab._document.text)))
                self.assertEqual(tab.text.get_buffer().get_char_count(),len(tab._document.text))
                before=tab.scroll.get_vadjustment().get_value()
                tab.text._inline_buttons[0].emit('clicked');spin()
                self.assertEqual(window.study.tool,'notes');self.assertIsNone(window.study.notes.editor)
                self.assertEqual(len(window.study.notes.rows),2)
                window.appearance.update('verse_numbers',False);spin()
                self.assertEqual(len(tab.text._inline_buttons),1)
                window.appearance.update('note_indicators',False);spin()
                self.assertFalse(tab.text._inline_buttons)
                self.assertNotIn('\ufffc',tab._document.text)
                self.assertEqual(len(window.notes_store.all()),2)
                window.appearance.update('note_indicators',True);spin()
                editor=window.study.notes.open_note(window.notes_store.all()[0])
                editor.body.get_buffer().set_text('Draft kept')
                tab.text._inline_buttons[0].emit('clicked');spin()
                self.assertIs(window.study.notes.editor,editor)
                self.assertEqual(editor.body.get_buffer().props.text,'Draft kept')
                editor._discard=True;editor.close()
                self.assertGreaterEqual(before,0)
            finally:close_test_dialogs();window.close()

    def test_place_fallback_and_note_coexist_after_verified_mapping_without_network(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        from tests.test_place_data import inputs,pins
        from bible import place_data
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed_fixture(directory,entries=[('John.1.5','Exact scripture without geographic name matching.')])
            files=inputs(root);data=place_data.PlaceData(root/'study-data')
            with patch.object(place_data,'FILES',pins(files)):data.install_files(files)
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(root/'translations'));window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Test','John.1.5')
                window.notes_store.save('Note',[],versification='KJV',start='John.1.5',end='John.1.5',origin_translation='Test',origin_language='en')
                window.notes_changed();spin(lambda:len(tab.text._inline_buttons)==2,duration=.5)
                self.assertEqual(len(tab.text._inline_buttons),2)
                self.assertIn('Exact scripture',tab._document.copy(0,len(tab._document.text)))
                geographic=next(b for b in tab.text._inline_buttons if b.get_icon_name()=='mark-location-symbolic')
                with patch('urllib.request.urlopen',side_effect=AssertionError('Offline')):
                    geographic.emit('clicked');spin()
                    self.assertEqual(window.place_dialog.current_place['id'],'a123456')
                    window.place_dialog.close();spin()
                window.appearance.update('place_markers',False);spin()
                self.assertEqual(len(tab.text._inline_buttons),1)
                self.assertIsNone(window.study.places_button.get_parent())
            finally:close_test_dialogs();window.close()
