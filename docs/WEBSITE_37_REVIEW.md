# Alpha landing page — product review required

This is a proposal for issue #37. **Do not merge or publish before product-manager
review.** No Pages configuration, public signing key, channel URL or repository
history has been changed.

The English page uses local assets, system fonts, responsive layout, native
light/dark preference, visible keyboard focus and a skip link. It contains no
JavaScript, analytics, external fonts or account flow. Installation targets the
existing `alpha/Bible.flatpakref`. Update help uses `flatpak update` without
assuming a user installation. Technical details, source archive, license,
notices, public key and fallback bundles remain accessible in disclosure content.

`tools/site_render.py` renders the template during `prepare()`, copying local
assets on every generation. Provenance is escaped and follows the package being
published. Historical archives and OSTree objects are not removed. The real
application screenshot is deliberately identified separately: public source
`4a285f327b84008b398d3bf6841737534da831f0`, alpha revision `39558047623-2`,
Flatpak commit `46b9ed2d2077d6163470fc37450dc33eb86bc6e59e838566fbc0f3e2dba0f5a3`.
It was captured from the installed signed public alpha, with a disposable profile,
English UI and real offline FreSegond1910 John 3. No proposed features are shown.
The screenshot must be reviewed/replaced when the published interface changes.

Review captures:

- [Desktop](captures/website-37-desktop.png)
- [Mobile](captures/website-37-mobile.png)
- [Dark](captures/website-37-dark.png)

Browser checks in Chromium at 1440×1000 and 390×844 verify no horizontal overflow,
loaded images, keyboard skip/install/disclosure navigation and retrieval of the
existing signed alpha descriptor. These are automated browser checks, not manual
screen-reader acceptance. The page does not promise Windows/macOS, Flathub listing,
Bible.com/Semeur, unmerged highlights or continuous-book pagination.

Local repeated-render tests preserve sentinel descriptors, key, historical object
and archive while updating provenance. Existing publication-gate and persistence
tests also run. Controlled signed installation/update validation uses a disposable
test-only key and isolated client; it never replaces the public key. Public HTTPS
installation has already been checked for the current alpha, but this proposed
page is not deployed and must be verified again after an approved publication.
