"""Select additional CI campaigns; unknown inputs retain full coverage."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict

import json
import os
from pathlib import Path
import re
import subprocess
import sys

CAMPAIGNS = ("visual", "words", "contextual", "library")
GROUPS = {
    "visual": {
        "bible/reading/appearance.py",
        "bible/reading/reading_style.py",
        "bible/reading/reading_preferences.py",
        "bible/reading/reading_metrics.py",
        "bible/reading/immersion.py",
        "bible/pagination.py",
        "bible/paged_sources.py",
        "bible/passage_actions.py",
        "bible/reading/scroll_motion.py",
        "bible/annotations_ui/notes_window.py",
        "bible/annotations_ui/note_editing.py",
        "bible/annotations_ui/note_preview.py",
        "bible/workspace_selector.py",
    },
    "words": {
        "bible/study/word_study.py",
        "bible/word_metadata.py",
        "bible/step_data.py",
        "bible/step_sources.py",
        "bible/study/passage_study.py",
        "bible/study/place_cards.py",
        "bible/place_data.py",
        "bible/study/place_map.py",
        "bible/place_names.py",
    },
    "contextual": {
        "bible/reference_preview.py",
        "bible/study/study_empty.py",
        "bible/study/study_panel.py",
        "bible/study/study_references.py",
        "bible/study/study_search.py",
        "bible/topic_data.py",
        "bible/topic_vocabulary.py",
        "bible/study/search_popover.py",
        "bible/text_search.py",
        "bible/study/context_indicator.py",
        "bible/annotations_ui/annotation_card.py",
        "bible/annotation_collection.py",
        "bible/annotations_ui/note_links.py",
    },
    "library": {
        "bible/library.py",
        "bible/catalogue/catalogue_window.py",
        "bible/catalogue/catalogue_cache.py",
        "bible/catalogue/catalogue_session.py",
        "bible/module_updates.py",
        "bible/catalogue/module_management.py",
        "bible/module_lifecycle.py",
        "bible/catalogue/module_ui_lifecycle.py",
        "bible/catalogue/module_updates_window.py",
        "bible/curated_catalogue.py",
        "bible/catalogue/version_chooser.py",
        "bible/catalogue/language_picker.py",
        "bible/resource_details.py",
        "bible/native_module_probe.py",
    },
}
# These persistence mechanisms remain covered by the full host and packaged suites.
CORE_ONLY = {
    "bible/notes.py",
    "bible/highlights.py",
    "bible/session.py",
    "bible/history.py",
    "bible/personal_backup.py",
    "bible/markdown.py",
}
FRENCH_FULL = """test_ui test_alpha_ui test_provider_ui test_workspace_features test_appearance
 test_reading_preferences test_immersion test_reading_sync test_pagination test_reading_direction
 test_library_polish test_annotation_workspace test_chapter_notes test_finishing test_personal_backup
 test_personal_backup_ui test_study_navigation test_scroll_motion test_comparison_rows test_inline_markers
 test_word_study test_text_search test_step_data test_word_metadata test_study_search test_scroll_position
 test_independent_opening test_verse_typography test_reader_chrome""".split()
FRENCH_SMOKE = [
    "test_ui.WindowTests." + name
    for name in (
        "test_empty_profile_and_async_failure_retry",
        "test_client_detail_hierarchy_preserves_source_terms_and_actions",
        "test_header_at_360_pixels_and_full_height_study_to_the_right",
        "test_nt_only_selector_and_direct_french_reference",
        "test_catalogue_language_search_conditions_and_locked_resource",
        "test_note_formatting_commands_and_catholic_reference_labels",
    )
] + [
    "test_reader_chrome",
    "test_personal_backup_ui",
    "test_finishing.FinishingTests.test_catalogue_loading_zero_failure_and_retained_rows_are_distinct",
    "test_provider_ui.ProviderUITests.test_failed_install_keeps_resource_error_and_retry_after_selection_and_refresh",
    "test_study_search.StudySearchTests.test_loading_keeps_completed_rows_inert_without_a_status_line_or_control_resize",
    "test_study_search.StudySearchTests.test_mode_change_invalidates_results_and_missing_data_keeps_passage_usable",
]


class _BaseCommit(TypedDict, total=False):
    """Subset of the GitHub base commit used to choose a safe diff."""

    sha: str


class _PullRequest(TypedDict, total=False):
    """Pull-request event fields consumed by the campaign selector."""

    base: _BaseCommit


class ChangeEvent(TypedDict, total=False):
    """Optional GitHub event fields; missing identities force full coverage."""

    pull_request: _PullRequest
    before: str


def select(paths: Iterable[str] | None) -> tuple[set[str], bool]:
    """Select additional regression campaigns from changed paths, falling back to full coverage for unknown inputs."""
    if paths is None:
        return set(CAMPAIGNS), True
    selected: set[str] = set()
    localization = False
    for name in paths:
        path = Path(name)
        if path.suffix in (".po", ".pot", ".mo") or name == "bible/i18n.py":
            localization = True
            selected.update(CAMPAIGNS)
        elif path.is_relative_to("bible") and path.suffix == ".py":
            found = {group for group, modules in GROUPS.items() if name in modules}
            if not found and name not in CORE_ONLY:
                found = set(CAMPAIGNS)
                localization = True
            selected.update(found)
        elif name.startswith(("docs/", "wiki/", ".github/", "tests/")) or name in (
            "AGENTS.md",
            "README.md",
            "tools/ci_campaigns.py",
        ):
            continue
        else:
            # Packaging, provider data, unclassified tools and future files are conservative.
            selected.update(CAMPAIGNS)
            if not name.startswith(("tools/check_", "tools/research/check_")):
                localization = True
    # Shared typography/dialog changes affect several historical visual surfaces.
    if "visual" in selected or "words" in selected:
        selected.add("contextual")
    return selected, localization


def changed_paths(event: str, payload: ChangeEvent, head: str) -> list[str] | None:
    """Return the checked Git comparison paths, or None when the event/base cannot be trusted."""
    if event == "workflow_dispatch":
        return None
    base = (
        payload.get("pull_request", {}).get("base", {}).get("sha")
        if event == "pull_request"
        else payload.get("before")
    )
    if (
        not base
        or not head
        or not all(re.fullmatch("[0-9a-f]{40}", s) and set(s) != {"0"} for s in (base, head))
    ):
        return None
    try:
        return (
            subprocess.check_output(
                ["git", "diff", "--no-renames", "--name-only", "-z", base, head],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .split("\0")[:-1]
        )
    except (subprocess.CalledProcessError, UnicodeError):
        return None


def main() -> None:
    """Print campaign selectors and the appropriate French validation targets for the current Actions event."""
    payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    groups, localization = select(
        changed_paths(os.environ["GITHUB_EVENT_NAME"], payload, os.environ["GITHUB_SHA"])
    )
    for group in CAMPAIGNS:
        print(f"{group}={str(group in groups).lower()}")
    targets = FRENCH_FULL if localization else FRENCH_SMOKE
    print("french=" + " ".join("tests." + target for target in targets))
    print(
        "Additional campaigns: "
        + (", ".join(sorted(groups)) or "none")
        + f"; French selectors: {len(targets)}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
