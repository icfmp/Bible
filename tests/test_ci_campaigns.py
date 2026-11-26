"""Coverage selection keeps unknown changes broad and known changes focused."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from tools.ci_campaigns import CAMPAIGNS, FRENCH_FULL, FRENCH_SMOKE, changed_paths, select


class CampaignTests(unittest.TestCase):
    def test_unknown_and_packaging_changes_keep_full_coverage(self) -> None:
        for paths in (
            None,
            ["bible/future_feature.py"],
            ["bible/new/notes.py"],
            ["bible/ui.py"],
            ["packaging/io.github.icfmp.Bible.json"],
            ["bible/source_versification.py"],
        ):
            with self.subTest(paths=paths):
                self.assertEqual(select(paths)[0], set(CAMPAIGNS))

    def test_backend_notes_keep_core_suites_without_historical_visual_campaigns(self) -> None:
        self.assertEqual(
            select(["bible/notes.py", "tests/test_notes.py", "docs/VALIDATION.md"]), (set(), False)
        )

    def test_specific_library_and_shared_visual_changes(self) -> None:
        self.assertEqual(select(["bible/module_updates.py"])[0], {"library"})
        self.assertEqual(select(["bible/appearance.py"])[0], {"visual", "contextual"})
        self.assertEqual(select(["bible/word_study.py"])[0], {"words", "contextual"})
        self.assertEqual(
            select(["bible/module_updates.py", "bible/word_study.py"])[0],
            {"words", "contextual", "library"},
        )

    def test_localization_and_missing_history_retain_full_french_pass(self) -> None:
        for paths in (None, ["po/fr.po"], ["bible/i18n.py"]):
            self.assertEqual(select(paths), (set(CAMPAIGNS), True))

    def test_manual_and_unavailable_git_history_are_conservative(self) -> None:
        self.assertIsNone(changed_paths("workflow_dispatch", {}, "a" * 40))
        self.assertIsNone(changed_paths("push", {"before": "0" * 40}, "a" * 40))
        with patch(
            "tools.ci_campaigns.subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            self.assertIsNone(changed_paths("push", {"before": "b" * 40}, "a" * 40))

    def test_changed_paths_handle_renames_deletions_and_spaces(self) -> None:
        with patch(
            "tools.ci_campaigns.subprocess.check_output",
            return_value=b"bible/notes.py\0docs/a b.md\0",
        ):
            self.assertEqual(
                changed_paths("push", {"before": "b" * 40}, "a" * 40),
                ["bible/notes.py", "docs/a b.md"],
            )

    def test_french_targets_exist_and_do_not_repeat_pure_backup_or_parsing(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertLess(len(FRENCH_SMOKE), len(FRENCH_FULL))
        for target in FRENCH_SMOKE:
            module, *names = target.split(".")
            source = ast.parse((root / "tests" / (module + ".py")).read_text())
            if names:
                cls = next(
                    n for n in source.body if isinstance(n, ast.ClassDef) and n.name == names[0]
                )
                self.assertIn(
                    names[1], [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
                )
            self.assertNotIn(
                module, ("test_personal_backup", "test_step_data", "test_word_metadata")
            )
