"""Native temporary word study, structured occurrences and draft protection."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class WordStudyTests(unittest.TestCase):
    def test_real_provider_boundary_temporary_back_and_occurrence_search_preserve_draft(self):
        from bible.ui import Application,Window,Library
        from bible import step_data
        from bible.step_data import StepData
        from tests.test_step_data import fixtures
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        from bible.passage_actions import target
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed_fixture(root,entries=[('Gen.1.1','TEST Hebrew context'),('John.1.1','TEST Greek context'),('Acts.1.1','TEST further context')])
            files,pins=fixtures(root)
            with patch.object(step_data,'FILES',pins),patch.object(step_data,'EXPECTED_COUNTS',{'tagnt-na27':2,'tahot-main':4}):StepData(root/'study-data').install_files(files)
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(root/'translations'));window.set_default_size(1250,850);window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Test','John.1.1');window.study_button.set_active(True)
                window.study.tools.set_visible_child_name('notes')
                note=window.notes_store.save('Saved note',[],versification='KJV',start='John.1.1',end='John.1.1',origin_translation='Test',origin_language='en')
                window.notes_changed();editor=window.study.notes.open_note(note)
                editor.body.get_buffer().set_text('Unsaved draft kept')
                source=window.passage_actions.ordinary(tab)
                value=target(tab.text,source,lambda:window.passage_actions.ordinary(tab),tab._marker_ends['John.1.1'])
                history=list(tab.state.history);reference=tab.state.reference
                words=window.study.words;words.open(value)
                spin(lambda:not words.pending,duration=.2)
                self.assertEqual(window.study.tool,'word');self.assertFalse(window.study.tools_switcher.get_visible())
                self.assertIs(window.study.notes.editor,editor)
                buttons=[c for c in words.children() if hasattr(c,'emit') and c.__class__.__name__=='Button']
                self.assertTrue(buttons)
                buttons[0].emit('clicked');spin(lambda:not words.pending,duration=.3)
                self.assertEqual(words.entry['id'],'G3056')
                samples=[c._word_reference for c in words.children() if hasattr(c,'_word_reference')]
                self.assertEqual(samples,['Acts.1.1'])
                self.assertEqual(window.active_tab.state.reference,reference)
                self.assertEqual(window.active_tab.state.history,history)
                words.all_occurrences('tagnt-na27',words.entry)
                search=window.navigation.text_search;spin(lambda:not search.pending,duration=.3)
                self.assertEqual(search.lemma_query,('tagnt-na27','G3056'))
                self.assertEqual([r.start for r in search.rows],['John.1.1','Acts.1.1'])
                window.navigation.popdown();words.leave();spin()
                self.assertEqual(window.study.tool,'notes')
                self.assertEqual(editor.body.get_buffer().props.text,'Unsaved draft kept')
                self.assertEqual(window.study_settings.tool,'notes')
                editor._discard=True;editor.close()
            finally:close_test_dialogs();window.close()

    def test_missing_data_is_optional_and_does_not_launch_download_or_replace_scripture(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin
        from bible.passage_actions import target
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed_fixture(root)
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(root/'translations'));window.present();spin()
            try:
                tab=window.active_tab;source=window.passage_actions.ordinary(tab)
                before=source.document.copy(0,len(source.document.text))
                value=target(tab.text,source,lambda:window.passage_actions.ordinary(tab),tab._marker_ends[tab.state.reference])
                with patch('bible.step_data.StepData.install',side_effect=AssertionError('No automatic download')):
                    window.study.words.open(value);spin()
                self.assertFalse(window.study.words.pending)
                self.assertEqual(tab._document.copy(0,len(tab._document.text)),before)
                self.assertIsNone(window.catalogue_window)
                window.study.words.leave()
            finally:window.close()
