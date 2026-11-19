# Application icon inventory — #292

`bible/icons/manifest.json` lists every production symbolic name, its literal
call sites, immutable upstream revision, editable source path, license and
bundled hash or GTK resource URI. `python -m tools.icon_inventory` audits Python,
UI and CSS without starting the application; computed names require review.
`tests.test_icons` checks coverage, asset/license integrity and actual native
lookup in both text directions with no desktop theme search paths.

Bible preserves the user's icon theme and adds its small hicolor fallback.
Unmodified official Adwaita SVGs supplement existing project/CC0 artwork. GTK
built-ins provide the guaranteed native actions; their paths also exist in the
supported GTK 4.14 sources. `THIRD_PARTY_NOTICES.md` and installed license files
record the independently licensed artwork. No whole theme or runtime download
is added.

The Library menu uses the exact GNOME Web 49 bookmarks books glyph
`ephy-library-symbolic.svg` (#207), rather than guessing from the name of an
unrelated theme icon. Existing dictionary/notebook workspace icons (#208), the
comparison icon (#209) and original place artwork (#210) remain intact.
Invalid native names `emblem-ok`, `format-text` and `sidebar-show-left` were
replaced with the corresponding checkmark, font and left-sidebar symbolics.

A pre-existing partial `hicolor/index.theme` listed only actions. In a minimal
theme it hid GTK's own status/missing-image directories; a missing internal
widget icon then recursively requested `image-missing` until a native crash.
The partial index is removed so GTK's complete built-in fallback index is used.
The regression checks a deliberately unknown icon as well as all application
names. This also removes the need for a custom resource-directory workaround.

Native GNOME 49/GTK 4.20 captures and minimal-theme FR/EN dialog checks are
separate from a KDE session test: no Plasma desktop is available here. Minimal
lookup proves that application glyphs come from Bible/GTK without a desktop
Adwaita install; it does not establish KDE desktop acceptance or remove the
libadwaita toolkit's own internal resources. Theme recoloring, large type and
high contrast are checked in the real GTK application.
