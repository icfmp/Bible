"""Every production glyph resolves without a desktop theme or Adwaita install."""

import hashlib
import json
import os
from pathlib import Path
import unittest
from tools.icon_inventory import references

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "bible/icons/manifest.json").read_text())


class IconAssetsTests(unittest.TestCase):
    def test_all_referenced_names_have_verified_assets_or_explicit_gtk_resources(self):
        used, computed = references(ROOT)
        self.assertEqual(computed, [], "Register the exact possible names of a computed icon")
        entries = {row["name"]: row for row in MANIFEST["icons"]}
        self.assertEqual(len(entries), len(MANIFEST["icons"]))
        self.assertFalse(set(used) - set(entries), sorted(set(used) - set(entries)))
        for name, row in entries.items():
            with self.subTest(name=name):
                self.assertTrue(row["source"]["license"])
                if row["kind"] == "bundled":
                    asset = ROOT / row["path"]
                    self.assertTrue(asset.is_file())
                    self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), row["sha256"])
                    self.assertTrue((ROOT / row["source"]["license_path"]).is_file())
                else:
                    self.assertEqual(row["kind"], "gtk-resource")
                    self.assertTrue(
                        row["resource_uri"].startswith("resource:///org/gtk/libgtk/icons/")
                    )

    @unittest.skipUnless(os.environ.get("DISPLAY"), "Requires native GTK")
    def test_minimal_theme_resolves_every_real_glyph_in_both_directions_without_adwaita(self):
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
        from bible.icons import configure_theme, ICON_ROOT

        Gtk.init()
        theme = Gtk.IconTheme.new()
        theme.set_search_path([])
        theme.set_theme_name("hicolor")
        configure_theme(theme)
        before = (theme.get_search_path(), theme.get_resource_path())
        configure_theme(theme)
        self.assertEqual((theme.get_search_path(), theme.get_resource_path()), before)
        self.assertEqual(theme.get_search_path(), [str(ICON_ROOT)])
        # A partial app hicolor index used to hide GTK's status directory,
        # causing native infinite fallback recursion for an unknown icon.
        self.assertFalse((ICON_ROOT / "hicolor/index.theme").exists())
        missing = theme.lookup_icon(
            "bible-nonexistent-test-icon",
            None,
            24,
            1,
            Gtk.TextDirection.LTR,
            Gtk.IconLookupFlags.PRELOAD,
        )
        self.assertTrue(missing.get_file().get_uri().endswith("/16x16/status/image-missing.png"))
        for row in MANIFEST["icons"]:
            for direction in (Gtk.TextDirection.LTR, Gtk.TextDirection.RTL):
                with self.subTest(name=row["name"], direction=direction):
                    self.assertTrue(theme.has_icon(row["name"]), row["name"])
                    image = theme.lookup_icon(
                        row["name"], None, 24, 1, direction, Gtk.IconLookupFlags.FORCE_SYMBOLIC
                    )
                    self.assertTrue(image.is_symbolic())
                    file = image.get_file()
                    self.assertIsNotNone(file)
                    if row["kind"] == "bundled":
                        self.assertTrue(file.get_path().startswith(str(ICON_ROOT)))
                    else:
                        self.assertTrue(
                            file.get_uri().startswith("resource:///org/gtk/libgtk/icons/")
                        )
