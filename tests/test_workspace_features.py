"""Real GTK interaction checks for the new main-window workspaces."""
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture, spin, close_test_dialogs

@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires Xvfb')
class WorkspaceFeaturesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application
        cls.app=Application.get_default() or Application();cls.app.register()

    def tearDown(self):
        close_test_dialogs()

    def test_history_travel_does_not_append_and_preferences_keep_reference(self):
        from bible.ui import Window, Library
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory);installed_fixture(directory,'Other')
            w=Window(self.app,Library(Path(directory)/'translations'));w.present()
            try:
                w.navigate_selection('Test','Gen.2.1');w.navigate_selection('Other','John.1.1')
                tab=w.active_tab;count=len(tab.state.history)
                self.assertTrue(tab.travel(count-2));self.assertEqual(tab.state.reference,'Gen.2.1')
                self.assertEqual(len(tab.state.history),count)
                tab.preferences.verse_numbers=False;tab.preferences.chapter_numbers=False;tab.apply_appearance()
                self.assertEqual(tab.state.reference,'Gen.2.1')
                self.assertEqual(tab._marker_ends['Gen.2.1'],tab._verse_offsets['Gen.2.1'])
                w.navigation.refresh_history();self.assertIsNotNone(w.navigation.history_list.get_first_child())
                tab.state.comparison='Other';tab.refresh_comparison()
                text=tab.comparison_text.get_buffer();self.assertIn('NEXT CHAPTER',text.get_text(text.get_start_iter(),text.get_end_iter(),False))
                spin()
            finally:w.close()

    def test_notes_save_discard_cancel_and_return_keep_reading(self):
        from bible.ui import Window, Library
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            w=Window(self.app,Library(Path(directory)/'translations'));w.present()
            try:
                w.navigate_selection('Test','Gen.2.1');tab=w.active_tab
                space=w.open_notes();space.create_note();editor=space.editor
                editor.body.get_buffer().set_text('A local note')
                space.leave();self.assertEqual(w.main_pages.get_visible_child_name(),'notes')
                editor._confirmation.response('cancel');spin()
                self.assertFalse(editor.closed);self.assertTrue(editor.dirty)
                space.leave();editor._confirmation.response('save');spin()
                self.assertEqual(w.main_pages.get_visible_child_name(),'reading')
                self.assertEqual(w.notes_store.all()[0].body,'A local note')
                self.assertIs(w.active_tab,tab);self.assertEqual(tab.state.reference,'Gen.2.1')
                space.present();spin()
                def visible_labels(widget):
                    from bible.ui import Gtk
                    values=[widget.get_text()] if isinstance(widget,Gtk.Label) else []
                    child=widget.get_first_child()
                    while child:
                        values.extend(visible_labels(child));child=child.get_next_sibling()
                    return values
                # Check factory-bound native rows: callback exceptions otherwise
                # print to stderr while a unittest can still appear to pass.
                self.assertIn('A local note',visible_labels(space.list))
                space.open_note(w.notes_store.all()[0]);editor=space.editor
                editor.body.get_buffer().set_text('Discard me');space.leave();editor._confirmation.response('discard');spin()
                self.assertEqual(w.notes_store.all()[0].body,'A local note')
                self.assertEqual(w.main_pages.get_visible_child_name(),'reading')
            finally:
                if w.note_editor:w.note_editor._discard=True
                w.close()

    def test_library_autoload_language_search_and_detail_back(self):
        from unittest.mock import patch
        from bible.ui import Window, Library, Gtk
        from bible.library import Resource
        from bible.language_picker import LanguagePicker
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            w=Window(self.app,Library(Path(directory)/'translations'));w.present()
            try:
                with patch('bible.catalogue_window.catalogue',return_value=[] ) as fetch:
                    w.application_settings.set('library_language','')
                    dialog=w.open_library();spin(lambda:dialog._catalogue_requested and not dialog.busy,duration=.3)
                    self.assertTrue(fetch.called)
                dialog.resources=[w.library.resource('Test')];dialog.update_languages()
                dialog.open_details(None,0)
                self.assertEqual(dialog.pages.get_visible_child_name(),'detail')
                dialog.back_to_list();self.assertEqual(dialog.pages.get_visible_child_name(),'list')
                self.assertEqual(dialog.choice_model.get_n_items(),1)
                picker=dialog.language;picker.set_codes(['','az','azb','fr','sr-Latn'])
                picker.search.set_text('azb');picker.filter()
                self.assertEqual(picker.visible_codes,['','azb'])
                spin(lambda:picker.strings.get_n_items()==2 and 'azb' in picker.strings.get_string(1))
                picker.activate(None,1);self.assertEqual(picker.codes[picker.get_selected()],'azb')
                self.assertIn('français',LanguagePicker.display_language('fr').lower())
                theme=Gtk.IconTheme.get_for_display(w.get_display())
                self.assertTrue(theme.has_icon('bible-notes-symbolic'))
                self.assertTrue(theme.has_icon('bible-library-symbolic'))
                dialog.close()
            finally:w.close()
