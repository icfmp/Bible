# Alpha landing page — approved presentation

The product manager approved the desktop/mobile/dark presentation on PR #41.
The client authorized merge/publication after current-alpha/channel checks. No Pages configuration, public signing key, channel URL or repository
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
`8d3a1834333a55e35cf61be248352f7e34ee40b7`, alpha revision `39644596592-2`,
Flatpak commit `118c2b72752f0bce34f29c3556b357a663d849e0097ef3b0d8e76b87b602f79a`.
It was captured from /app code in the installed signed public alpha with a
private test profile, English UI, actual FreSegond1910 John 3:16 and MHC 2.2
in the right drawer. Capture resolution is 1400×900 with no generated imagery.
Current main (including the validated #51 crash and #36 surfaces fixes) is merged.

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
test-only key and isolated client; it never replaces the public key. Public HTTPS installation/update of the reviewed page and its actual signed
channel are now verified; the approved page is deployed.

## Final public deployment

https://icfmp.github.io/Bible/ is live. The final available package is source
**6560dc4**, revision **39674239853-2** (main CI **39673122687**, publication
**39674239853**, both green). Dynamic provenance matches this package; the real
hero capture remains explicitly identified separately as signed source 8d3a183.
Actual HTTPS installation and signed update pass, preserve test data and retain
the existing key, remote and descriptors. All public links/assets return correctly
and the source archive digest matches. Chromium desktop/mobile/dark, keyboard,
image and overflow checks pass on this actual public deployment.

Actual public captures: [desktop](captures/website-37-public-desktop.png),
[mobile](captures/website-37-public-mobile.png), [dark](captures/website-37-public-dark.png).
Full proof and manual-accessibility limits: [delivery](PENDING_DELIVERIES_2026_10_21.md).
