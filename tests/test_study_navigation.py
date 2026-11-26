"""Regressions for source restoration and coordinated study/navigation work."""

import os
from pathlib import Path
import tempfile
import unittest

from bible.study_settings import StudySettings


class RememberedSourceTests(unittest.TestCase):
    def test_legacy_and_qualified_identity_and_invalid_file_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "study.json"
            path.write_text('{"version":1,"width":420,"tool":"notes"}')
            settings = StudySettings(path)
            self.assertIsNone(settings.last_commentary)
            settings.last_commentary = "crosswire~MHC"
            settings.save()
            self.assertEqual(StudySettings(path).last_commentary, "crosswire~MHC")
            path.write_text('{"version":1,"width":420,"tool":"notes","last_commentary":"../bad"}')
            original = path.read_bytes()
            settings = StudySettings(path)
            self.assertTrue(settings.error)
            with self.assertRaises(ValueError):
                settings.save()
            self.assertEqual(path.read_bytes(), original)


@unittest.skipUnless(os.environ.get("DISPLAY"), "Requires native GTK")
class CommentaryRestoreTests(unittest.TestCase):
    def test_chapter_stream_keeps_all_entries_and_missing_coverage_without_replacement(self):
        from bible.ui import Application, Window, Library
        from tests.test_ui import installed_fixture, spin
        from tests.test_commentary import commentary_fixture

        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(
                directory, entries=[(f"Gen.1.{v}", f"BIBLE {v}") for v in range(1, 32)]
            )
            commentary_fixture(
                directory,
                entries=[(f"Gen.1.{v}", f"ENTRY {v} " + ("long " * 150)) for v in (1, 5, 15, 31)],
            )
            app = Application.get_default() or Application()
            app.register()
            window = Window(app, Library(Path(directory) / "translations"))
            window.present()
            spin()
            try:
                window.study_button.set_active(True)
                panel = window.study
                panel.choices.set_selected(panel.names.index("Notes"))
                spin(lambda: not panel._positioning)
                text = panel.text.get_buffer().props.text
                self.assertEqual(len(panel.loaded), 4)
                for v in (1, 5, 15, 31):
                    self.assertEqual(text.count(f"ENTRY {v} "), 1)
                history = list(window.active_tab.state.history)
                for v in (15, 16, 31, 5):
                    window.active_tab.select_verse(f"Gen.1.{v}")
                    spin(duration=0.4)
                    self.assertEqual(panel.text.get_buffer().props.text, text)
                    self.assertEqual(window.active_tab.state.history, history)
                    if v == 16:
                        self.assertIsNone(panel.current_position)
                self.assertIsNotNone(panel.current_position)
            finally:
                window.close()

    def test_last_explicit_source_defaults_only_unchosen_tabs_and_survives_absence(self):
        from bible.ui import Application, Window, Library
        from tests.test_ui import installed_fixture, spin
        from tests.test_commentary import commentary_fixture
        import shutil

        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            source = commentary_fixture(directory, "Notes")
            other_source = commentary_fixture(directory, "OtherNotes")
            app = Application.get_default() or Application()
            app.register()
            library = Library(Path(directory) / "translations")
            window = Window(app, library)
            window.present()
            spin()
            try:
                window.study_button.set_active(True)
                panel = window.study
                panel.refresh(force=True)
                panel.choices.set_selected(panel.names.index("Notes"))
                spin()
                self.assertEqual(window.study_settings.last_commentary, "Notes")
                first = window.active_tab
                from bible.session import TabState

                page = window.append_tab(TabState(resource="Test"))
                window.view.set_selected_page(page)
                second = page.get_child()
                panel.refresh(force=True)
                spin()
                self.assertEqual(second.state.commentary, "Notes")
                panel.choices.set_selected(panel.names.index("OtherNotes"))
                spin()
                window.view.set_selected_page(window.view.get_page(first))
                spin()
                self.assertEqual(first.state.commentary, "Notes")
                self.assertEqual(window.study_settings.last_commentary, "OtherNotes")
            finally:
                window.close()
            # Remove only the session: a fresh reading tab uses the global choice.
            (Path(directory) / "session.json").unlink(missing_ok=True)
            window = Window(app, library)
            window.present()
            spin()
            try:
                window.study_button.set_active(True)
                window.study.refresh(force=True)
                self.assertEqual(window.active_tab.state.commentary, "OtherNotes")
                self.assertIsNotNone(window.study.reader)
            finally:
                window.close()
            shutil.rmtree(other_source)
            self.assertEqual(
                StudySettings(Path(directory) / "study-preferences.json").last_commentary,
                "OtherNotes",
            )
            window = Window(app, library)
            window.present()
            spin()
            try:
                window.study_button.set_active(True)
                window.study.refresh(force=True)
                self.assertEqual(window.active_tab.state.commentary, "OtherNotes")
                self.assertIsNone(window.study.reader)
                self.assertIn("OtherNotes", window.study.choices.get_selected_item().get_string())
                self.assertTrue(source.exists())
            finally:
                window.close()


@unittest.skipUnless(os.environ.get("DISPLAY"), "Requires native GTK/SWORD")
class CommentaryRemovalTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application, Window, Library
        from bible.application_settings import ApplicationSettings
        from tests.test_ui import installed_fixture, spin
        from tests.test_commentary import commentary_fixture

        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        installed_fixture(self.root)
        commentary_fixture(self.root, "Notes")
        commentary_fixture(self.root, "OtherNotes")
        ApplicationSettings(self.root).set("automatic_catalogue_refresh", False)
        self.app = Application.get_default() or Application()
        self.app.register()
        self.library = Library(self.root / "translations")
        self.windows = []
        self.w = self.open_window()

    def open_window(self):
        from bible.ui import Window
        from tests.test_ui import spin

        w = Window(self.app, self.library)
        self.windows.append(w)
        w.present()
        w.study_button.set_active(True)
        w.study.tools.set_visible_child_name("commentaries")
        spin(lambda: not w.active_tab._restoring_scroll)
        return w

    def tearDown(self):
        for w in self.windows:
            if not w.closed:
                w.close()

    def choose(self, w, name):
        from tests.test_ui import spin

        w.study.choices.set_selected(w.study.names.index(name))
        spin(lambda: not w.study._choice_idle and not w.study._positioning, duration=0.1)
        self.assertEqual(w.active_tab.state.commentary, name)
        self.assertEqual(w.study.reader.name if w.study.reader else None, name)

    def remove(self, name):
        from tests.test_ui import spin

        d = self.w.open_library("commentary")
        spin(lambda: not d.preparing)
        d.modules.run("remove", resource=self.library.resource(name))
        spin(lambda: not d.busy and not d.preparing, timeout=15, duration=0.2)
        self.assertEqual(d._phase, "complete", d.status.get_text())
        self.assertFalse((self.library.root / name).exists())
        d.close()

    def test_remove_active_source_releases_handles_in_all_windows_and_keeps_other_choice(self):
        import weakref
        from dataclasses import asdict

        w = self.w
        second = self.open_window()
        self.choose(w, "OtherNotes")
        other = weakref.ref(w.study.reader)
        self.choose(w, "Notes")
        self.choose(second, "Notes")
        removed = [weakref.ref(view.study.reader) for view in (w, second)]
        note = w.notes_store.save(
            "Personal note",
            ("Keep",),
            versification="KJV",
            start="Gen.1.1",
            end="Gen.1.1",
            origin_translation="Test",
            origin_language="en",
        )
        before = asdict(note)
        reference = w.active_tab.state.reference
        self.remove("Notes")
        for view in (w, second):
            self.assertNotIn("Notes", view.study.names)
            self.assertIsNone(view.study.reader)
            self.assertEqual(view.active_tab.state.commentary, "Notes")
        self.assertTrue(all(reader() is None for reader in removed))
        self.assertIsNotNone(other())
        for view in (w, second):
            for _ in range(2):
                self.choose(view, "OtherNotes")
                self.choose(view, None)
            self.choose(view, "OtherNotes")
        self.assertEqual(asdict(w.notes_store.get(note.id)), before)
        self.assertEqual(w.active_tab.state.reference, reference)

    def test_missing_legacy_choice_switches_after_native_notification_and_uses_stable_identity(
        self,
    ):
        from tests.test_ui import spin

        panel = self.w.study
        self.w.active_tab.state.commentary = "MissingNotes"
        panel.refresh(force=True)

        def labels():
            model = panel.choices.get_model()
            return tuple(model.get_string(i) for i in range(model.get_n_items()))

        original = labels()
        seen = []
        panel.choices.connect("notify::selected", lambda *_: seen.append(labels()))
        panel.choices.set_selected(panel.names.index("OtherNotes"))
        self.assertTrue(seen)
        self.assertEqual(seen[0], original)
        spin(lambda: not panel._choice_idle and not panel._positioning)
        self.assertEqual(panel.reader.name, "OtherNotes")
        self.assertNotIn("MissingNotes", panel.names)
        self.assertEqual(self.w.study_settings.last_commentary, "OtherNotes")

    def test_last_removal_restart_and_reinstall_keep_unavailable_context_without_auto_switch(self):
        from tests.test_commentary import commentary_fixture
        from tests.test_ui import spin

        self.choose(self.w, "Notes")
        self.remove("Notes")
        self.remove("OtherNotes")
        self.assertIsNone(self.w.study.reader)
        self.assertEqual(self.w.study.names, [None, self.w.study._download_choice])
        self.w.close()
        self.w = self.open_window()
        self.assertEqual(self.w.active_tab.state.commentary, "Notes")
        self.assertIsNone(self.w.study.reader)
        self.assertNotIn("Notes", self.w.study.names)
        commentary_fixture(self.root, "OtherNotes")
        self.w.resource_installed("OtherNotes")
        spin()
        self.assertIsNone(self.w.study.reader)
        self.assertEqual(self.w.active_tab.state.commentary, "Notes")
        self.choose(self.w, "OtherNotes")

    def test_pending_choices_coalesce_and_close_cancels_native_work(self):
        from tests.test_ui import spin

        panel = self.w.study
        for name in ("Notes", "OtherNotes", None):
            panel.choices.set_selected(panel.names.index(name))
        spin(lambda: not panel._choice_idle)
        self.assertIsNone(panel.reader)
        panel.choices.set_selected(panel.names.index("Notes"))
        self.w.close()
        spin()
        self.assertEqual(panel._choice_idle, 0)

    def test_removal_cancels_a_pending_choice_before_it_opens_a_native_source(self):
        from bible.module_lifecycle import ModuleLifecycle
        from bible.module_ui_lifecycle import ModuleViewChange
        from tests.test_ui import spin

        self.choose(self.w, "OtherNotes")
        d = self.w.open_library("commentary")
        spin(lambda: not d.preparing)
        self.w.study.choices.set_selected(self.w.study.names.index("Notes"))
        bridge = ModuleViewChange(d, "Notes")
        ModuleLifecycle(self.library).remove("Notes", before_switch=lambda _: bridge.pause())
        bridge.resume()
        spin()
        self.assertIsNone(self.w.study.reader)
        self.assertNotIn("Notes", self.w.study.names)
        self.assertEqual(self.w.study_settings.last_commentary, "OtherNotes")
        self.choose(self.w, "OtherNotes")
        d.close()

    def test_same_native_module_name_in_another_provider_root_stays_usable(self):
        import shutil
        from tests.test_ui import spin

        alias = "andbible-extra~Notes"
        shutil.copytree(self.library.root / "Notes", self.library.root / alias)
        (self.library.root / alias / ".complete").write_text(alias)
        (self.library.root / alias / ".source.json").write_text(
            '{"provider_id":"andbible-extra","module_name":"Notes"}'
        )
        self.w.study.refresh(force=True)
        spin()
        self.choose(self.w, alias)
        other = self.w.study.reader
        self.choose(self.w, "Notes")
        self.remove("Notes")
        self.assertIs(self.w.study._readers[alias], other)
        self.choose(self.w, alias)
        self.assertEqual(self.w.study.reader.root, self.library.root / alias)
        self.assertTrue(self.w.study.entry_text)
