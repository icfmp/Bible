"""Installed metadata refresh must retain native resource-row identities."""

import os, tempfile, unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import installed_fixture, spin


@unittest.skipUnless(os.environ.get("DISPLAY"), "Requires native GTK")
class LibraryPositionTests(unittest.TestCase):
    def test_display_titles_sort_installed_first_with_accents_and_stable_source_identity(self):
        from bible.ui import Application, Window, Library
        from bible.library import Resource
        from bible.study_resources import StudyResource

        app = Application.get_default() or Application()
        app.register()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("bible.catalogue_window.CatalogueWindow.auto_load", return_value=False),
        ):
            root = Path(directory)
            w = Window(app, Library(root / "translations"))
            w.present()
            spin()
            try:
                d = w.open_library()
                spin(lambda: not d.preparing)
                d.language_choice = ""
                d._language_records = {}
                d._search_terms = {}
                for category in range(3):
                    with self.subTest(category=category):
                        if category == 2:
                            resources = [
                                StudyResource(
                                    id="openbible-cross-references"
                                    if i == 0
                                    else "study-" + str(i),
                                    description=title,
                                )
                                for i, title in enumerate(
                                    ("Zulu", "étude", "École", "alpha", "alpha")
                                )
                            ]
                            self.enterContext(
                                patch.object(d.study_resources, "available", return_value=resources)
                            )
                            self.enterContext(
                                patch.object(
                                    d.study_resources,
                                    "installed_resource",
                                    return_value=resources[0],
                                )
                            )
                            d._installed_metadata = {}
                            d._study_installed = {resources[0].id}
                        else:
                            resources = [
                                Resource(
                                    "ID" + str(i),
                                    title,
                                    "fr",
                                    "Public Domain",
                                    category="Commentaries" if category else "Biblical Texts",
                                    provider_id="ebible" if i == 4 else "crosswire",
                                )
                                for i, title in enumerate(
                                    ("Zulu", "étude", "École", "alpha", "alpha")
                                )
                            ]
                            d.resources = resources
                            d._installed_metadata = {resources[0].id: resources[0]}
                            d._study_installed = set()
                        d.kind.set_selected(category)
                        d.update_languages()
                        spin(lambda: not d._building_rows)
                        self.assertEqual(
                            [r.id for r in d.filtered_resources],
                            [resources[i].id for i in (0, 3, 4, 2, 1)],
                        )
                        self.assertEqual(len({r.id for r in d.filtered_resources}), 5)
                        d.search.set_text("alpha")
                        d.filter_resources()
                        spin(lambda: not d._building_rows)
                        self.assertEqual(
                            [r.id for r in d.filtered_resources], [resources[i].id for i in (3, 4)]
                        )
                        d.search.set_text("")
                        d.filter_resources()
                        spin(lambda: not d._building_rows)
            finally:
                if w.catalogue_window:
                    w.catalogue_window.close()
                w.close()
                spin()

    def test_installation_reorders_existing_rows_without_losing_visible_anchor_or_selection(self):
        from bible.ui import Application, Window, Library
        from bible.library import Resource

        app = Application.get_default() or Application()
        app.register()
        for kind in ("bible", "commentary"):
            with (
                self.subTest(kind=kind),
                tempfile.TemporaryDirectory() as directory,
                patch("bible.catalogue_window.CatalogueWindow.auto_load", return_value=False),
                patch(
                    "bible.catalogue_session.CatalogueSession.load_youversion_language",
                    return_value=None,
                ),
            ):
                root = Path(directory)
                installed_fixture(root)
                w = Window(app, Library(root / "translations"))
                w.present()
                spin()
                try:
                    w.application_settings.set("library_language", "")
                    d = w.open_library()
                    spin(lambda: not d.preparing, duration=0.3)
                    d.resources = [
                        Resource(
                            "R" + str(i),
                            f"Resource {i:04}",
                            "fr",
                            "Public Domain",
                            category="Commentaries" if kind == "commentary" else "Biblical Texts",
                        )
                        for i in range(200)
                    ]
                    d._installed_metadata = {}
                    d._language_records = {"fr": ("French", "French", "french")}
                    d._search_terms = {}
                    d.language_choice = ""
                    d.kind.set_selected(1 if kind == "commentary" else 0)
                    d.update_languages()
                    spin(lambda: not d._building_rows, duration=1)
                    a = d.list_scroll.get_vadjustment()
                    self.assertGreater(a.get_upper(), a.get_page_size() * 3)
                    a.set_value(a.get_upper() * 0.6)
                    spin(duration=0.3)

                    def visible():
                        result = []
                        for item in d._bound_rows:
                            found, bounds = item.get_child().compute_bounds(d.list_scroll)
                            if (
                                found
                                and bounds.get_y() >= 0
                                and bounds.get_y() < d.list_scroll.get_height()
                            ):
                                result.append((bounds.get_y(), item.get_item().resource.id))
                        return sorted(result)

                    anchor_y, anchor_id = visible()[0]
                    d.choices.set_selected(
                        next(i for i, r in enumerate(d.filtered_resources) if r.id == anchor_id)
                    )
                    anchor_row = next(
                        item for item in d._bound_rows if item.get_item().resource.id == anchor_id
                    )
                    anchor_row.action.grab_focus()
                    spin()
                    anchor_y = dict((identifier, y) for y, identifier in visible())[anchor_id]
                    items = [d.choice_model.get_item(i) for i in range(200)]
                    changes = []
                    d.choice_model.connect(
                        "items-changed", lambda _, p, r, a: changes.append((p, r, a))
                    )
                    d._installed_metadata = {
                        d.resources[190].id: replace(
                            d.resources[190], description="Verified installed attribution"
                        )
                    }
                    d.filter_resources()
                    spin(duration=0.4)
                    self.assertTrue(changes)
                    self.assertEqual(set(items), {d.choice_model.get_item(i) for i in range(200)})
                    self.assertEqual(d.filtered_resources[0].id, "R190")
                    self.assertEqual(
                        d.filtered_resources[0].description, "Verified installed attribution"
                    )
                    self.assertEqual(d.selected_resource().id, anchor_id)
                    self.assertIs(d.get_focus(), anchor_row.action)
                    positions = {identifier: y for y, identifier in visible()}
                    self.assertIn(anchor_id, positions)
                    self.assertAlmostEqual(positions[anchor_id], anchor_y, delta=2)
                    changes.clear()
                    d.filter_resources()
                    spin()
                    self.assertEqual(changes, [])
                    # Finishing another queued install while a detail page is
                    # open must not restore an obsolete absolute list offset.
                    d.open_details(
                        None,
                        next(i for i, r in enumerate(d.filtered_resources) if r.id == anchor_id),
                    )
                    d._installed_metadata[d.resources[185].id] = d.resources[185]
                    d.filter_resources()
                    spin()
                    d.back_to_list()
                    spin(duration=0.3)
                    self.assertEqual(d.selected_resource().id, anchor_id)
                    positions = {identifier: y for y, identifier in visible()}
                    self.assertIn(anchor_id, positions)
                    self.assertAlmostEqual(positions[anchor_id], anchor_y, delta=2)
                    d.search.set_text("Resource 01")
                    d.filter_resources()
                    spin(lambda: not d._building_rows, duration=0.3)
                    self.assertTrue(d.filtered_resources)
                    self.assertLess(len(d.filtered_resources), 200)
                finally:
                    if w.catalogue_window and not w.catalogue_window.closed:
                        w.catalogue_window.close()
                    w.close()
                    spin()
