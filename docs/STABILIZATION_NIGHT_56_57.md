# Current alpha stabilization — resource installation and reading UI

Published baseline remains source **6560dc4**, revision **39674239853-2**,
unchanged signed fingerprint `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.
Main `8e94fd7` already contains reviewed page/eBible/highlights/pagination PRs;
none of those integrations is repeated. Current candidate work is separate.

## #56 — actual installation cause and targeted correction

Actual signed /app code fetched the five current French eBible packages.
FOB, F10, FRANCL and SBL fail the strict notice comparison; JND installs.
Detailed evidence shows **only generated terminal revision dates differ**:
About on all four, and CopyrightNotes also on FRANCL. Actual license, author,
rights prose, holders and restrictions are unchanged. These are not four
substantive conditions conflicts. The earlier delivery's broad metadata
rejection diagnosis is corrected by this direct field comparison.

Reviewed AndBible current-stable JSword submodule commit
`6ebd10a005fa7761e611c048ececea1430e22546`,
`src/main/java/org/crosswire/jsword/book/install/sword/AbstractSwordInstaller.java`
(install, lines 229–272): the configured package ZIP is downloaded, unpacked
into mods.d/modules and registered. It does not require catalogue/package About
byte equality. Bible retains its additional archive/identity/path/encryption,
actual capability, conditions and readable-content checks rather than copying
an unguarded extraction path.

The narrow compatibility correction recognizes a terminal date-only update in
otherwise identical About, with matching CopyrightNotes dates if present, only
for a package explicitly declaring Haiola auto-generation in its version history.
It never ignores CopyrightDate, license, holder, attribution wording, author or
restriction changes. Both the raw package configuration and original catalogue
notices are retained; installed details read actual package notices. This is a
generator-metadata capability rule, not an allowlist of Bible names/providers.
Regression tests still refuse genuine changed conditions, encryption and unsafe
archives. Failure remains resource-specific and visible after selection or
catalogue refresh, with Retry for the failed resource; transfer completion is
not reported as usable installation.

13 library tests and 8 affected GTK/provider tests pass, plus the French error-state
regression. Candidate UI installation immediately exposes all five French eBible
Bibles and two additional actual CrossWire Bibles (KJV and Crampon). Seven independent
SWORD John 3:16 comparisons pass. All seven reopen/read after restart inside an
isolated network namespace. Five systems are represented: NRSV, Luther, Catholic2,
NRSVA and KJV. Candidate resource code is not a final packaged
verification. Final full checks/build/actual Flatpak checks remain required.

Evidence: `evidence/stabilization-56-original-package.txt`,
`evidence/stabilization-56-candidate-install.txt`,
`evidence/stabilization-56-candidate-offline.txt`.
Reproducer: `python3 -m tools.check_resource_installation TEST_PROFILE`; restart
with `--offline` in an isolated network namespace, or Flatpak `--unshare=network`.
No resources are shipped with the application.

## Escalation requested by the client

The client requested notification before changes requiring higher-reasoning review
of versification or pagination mechanisms. The following two items were explicitly
reported to the client and remain pending that review:

- #57: eBible Darby declares **Luther**. Native SWORD 1.9 registers this system
  without a mapping table (`versificationmgr.cpp`, line 74); the current whitelist
  therefore blocks it. Simply deleting the whitelist would use native identity
  fallback, falsely claiming alignment (especially Psalms). Inspect verified
  AndBible/JSword mappings and the shared mechanism; do not patch individual names.
- #24: general heading keep-with-next, preparation/cache optimization and cancellation
  affect the pagination mechanism. Preserve accepted visual layout and current
  canonical anchors; Mark 7→8 and Luke 13→14 are reproducers.

Independent #53/#54/#55 controls/surface corrections may continue. No #26 or
OpenBible #47–50 work; no visual/functional issue is closed without client acceptance.
No candidate alpha is announced as available until actual build and publication
verification. Preserve notes/highlights/resources/sessions/preferences and signing.

## Independent native UI corrections — candidate verification

- #53 uses libadwaita's documented `sidebar-pane`/`end` surface and a flat header.
  Commentary text/margins are transparent over the same native surface, with native
  sidebar foreground; primary/comparison reading palettes are unchanged. No custom
  gray is hardcoded. Verified against libadwaita 1.5 `_sidebars.scss` and
  `_header-bar.scss`; the same styles work in the actual GNOME 49 runtime.
- #54 moves the existing global Aa before the main Header Bar menu. Duplicate
  overlay/drawer controls and the duplicate appearance menu entry are removed;
  the single existing popover/preferences are reparented into immersive controls.
- #55 positions the same circular actions near the actual text margins, around
  80% of the reading viewport. Width/drawer/comparison/resize recompute safe margins;
  page vs chapter semantics are unchanged. No scripture/selection rewrite.
- #24 controls/focus only: compact exit/Aa at the top right, no native window-title
  buttons in immersion, reveal on pointer movement/F10/entry and retain visibility
  while focused or a popover is open. The actual published GTK trace showed
  `GtkWindow:focus-visible` remaining true after pointer selection. Use native
  `set_focus_visible(False)` on pointer presses and true on keyboard events;
  no global CSS outline removal or loss of focusability. Pagination algorithms,
  heading grouping, preparation/cancellation/cache remain unchanged and pending.

161 full local tests pass. Affected tests include Header Bar order/shared popover,
original notes/selection/immersion state and safe-margin lower navigation across
wide/narrow/drawer layouts. Actual native pointer/keyboard checks in the GNOME 49
runtime pass, including uniform header/content pixels in light/dark and emulated
high contrast, one mapped Aa, global settings, arrows, pointer vs keyboard focus,
F10/exit/popover lifecycle. This is **explicit source-candidate code** in that
runtime, not a final installed-package claim or manual GNOME/Wayland validation.

Original signed baseline and candidate captures are under `docs/captures/` with
`stabilization-before-6560dc4` and `stabilization-candidate-*` names. Native logs are
in `docs/evidence/stabilization-native-ui-candidate.txt` and the original focus
trace. The capture helper waits for real GTK layout before saving; the remaining
blank preparation interval is not claimed fixed by these captures.

Final delivery scope is intentionally limited to verified installation and UI
corrections. The higher-reasoning versification and pagination mechanism review
remains explicit; do not ask the client to retest an unsupported Darby comparison
or claim that chapter orphans/preparation are resolved. Keep all relevant issues
open for client acceptance. Final full CI/build, actual /app resource installs,
network-isolated reading, native UI/regressions and signed publication must pass
before reporting an available revision. Test fresh KJV/Crampon plus Segond/Lausanne
controls alongside all five French eBible resources in the final package.
