"""Regressions for source restoration and coordinated study/navigation work."""
import os
from pathlib import Path
import tempfile
import unittest

from bible.study_settings import StudySettings


class RememberedSourceTests(unittest.TestCase):
    def test_legacy_and_qualified_identity_and_invalid_file_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'study.json'
            path.write_text('{"version":1,"width":420,"tool":"notes"}')
            settings = StudySettings(path)
            self.assertIsNone(settings.last_commentary)
            settings.last_commentary = 'crosswire~MHC'
            settings.save()
            self.assertEqual(StudySettings(path).last_commentary, 'crosswire~MHC')
            path.write_text('{"version":1,"width":420,"tool":"notes","last_commentary":"../bad"}')
            original = path.read_bytes()
            settings = StudySettings(path)
            self.assertTrue(settings.error)
            with self.assertRaises(ValueError):
                settings.save()
            self.assertEqual(path.read_bytes(), original)


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires native GTK')
class CommentaryRestoreTests(unittest.TestCase):
    def test_chapter_stream_keeps_all_entries_and_missing_coverage_without_replacement(self):
        from bible.ui import Application, Window, Library
        from tests.test_ui import installed_fixture, spin
        from tests.test_commentary import commentary_fixture
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory, entries=[(f'Gen.1.{v}', f'BIBLE {v}') for v in range(1,32)])
            commentary_fixture(directory, entries=[(f'Gen.1.{v}', f'ENTRY {v} '+('long '*150)) for v in (1,5,15,31)])
            app=Application.get_default() or Application();app.register()
            window=Window(app, Library(Path(directory)/'translations'));window.present();spin()
            try:
                window.study_button.set_active(True);panel=window.study
                panel.choices.set_selected(panel.names.index('Notes'));spin(lambda:not panel._positioning)
                text=panel.text.get_buffer().props.text
                self.assertEqual(len(panel.loaded),4)
                for v in (1,5,15,31):self.assertEqual(text.count(f'ENTRY {v} '),1)
                history=list(window.active_tab.state.history)
                for v in (15,16,31,5):
                    window.active_tab.select_verse(f'Gen.1.{v}');spin(duration=.4)
                    self.assertEqual(panel.text.get_buffer().props.text,text)
                    self.assertEqual(window.active_tab.state.history,history)
                    if v==16:self.assertIsNone(panel.current_position)
                self.assertIsNotNone(panel.current_position)
            finally:window.close()

    def test_last_explicit_source_defaults_only_unchosen_tabs_and_survives_absence(self):
        from bible.ui import Application, Window, Library
        from tests.test_ui import installed_fixture, spin
        from tests.test_commentary import commentary_fixture
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            source = commentary_fixture(directory, 'Notes')
            other_source = commentary_fixture(directory, 'OtherNotes')
            app = Application.get_default() or Application(); app.register()
            library = Library(Path(directory) / 'translations')
            window = Window(app, library); window.present(); spin()
            try:
                window.study_button.set_active(True)
                panel = window.study
                panel.refresh(force=True)
                panel.choices.set_selected(panel.names.index('Notes')); spin()
                self.assertEqual(window.study_settings.last_commentary, 'Notes')
                first = window.active_tab
                from bible.session import TabState
                page = window.append_tab(TabState(resource='Test'))
                window.view.set_selected_page(page)
                second = page.get_child()
                panel.refresh(force=True); spin()
                self.assertEqual(second.state.commentary, 'Notes')
                panel.choices.set_selected(panel.names.index('OtherNotes')); spin()
                window.view.set_selected_page(window.view.get_page(first)); spin()
                self.assertEqual(first.state.commentary, 'Notes')
                self.assertEqual(window.study_settings.last_commentary, 'OtherNotes')
            finally:
                window.close()
            # Remove only the session: a fresh reading tab uses the global choice.
            (Path(directory) / 'session.json').unlink(missing_ok=True)
            window = Window(app, library); window.present(); spin()
            try:
                window.study_button.set_active(True); window.study.refresh(force=True)
                self.assertEqual(window.active_tab.state.commentary, 'OtherNotes')
                self.assertIsNotNone(window.study.reader)
            finally:
                window.close()
            shutil.rmtree(other_source)
            self.assertEqual(StudySettings(Path(directory) / 'study-preferences.json').last_commentary, 'OtherNotes')
            window = Window(app, library); window.present(); spin()
            try:
                window.study_button.set_active(True); window.study.refresh(force=True)
                self.assertEqual(window.active_tab.state.commentary, 'OtherNotes')
                self.assertIsNone(window.study.reader)
                self.assertIn('OtherNotes', window.study.choices.get_selected_item().get_string())
                self.assertTrue(source.exists())
            finally:
                window.close()
