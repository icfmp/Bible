# Alpha stabilization handoff — 21 October 2026

Scope: batches requested by the client, in order. #26 is excluded. GitHub
content is English; the application remains French/English. Do not publish
the #37 page before product-manager review. Preserve the existing signed
alpha channel, key and installation URLs.

## Baseline

- Started from `e4ec608` on main, including published #30 fix `a8657c7`.
- #30 evidence is already green: CI 39508143082, alpha publication 39509022541;
  real Flatpak/Babel 2.18.0 catalogue: 412 resources, five Coptic resources.
- Do not repeat that investigation without a new failure.

## Batch 1 — #35, #36 and related #25

Implemented: use native SWORD `VerseKey.positionFrom` rather
than rejecting every differing versification label. It calls
`VersificationMgr::System::translateVerse` and retains the target system.
Copy construction/`copyFrom` would instead retain the source system and is
unsuitable. Only SWORD 1.9 systems with shipped mapping tables and the KJV
base are allowed across systems; unsupported pairs remain explicit.

Source evidence (reviewed, no source copied): SWORD 1.9.0 `versekey.cpp`
(`positionFrom`, `setFromOther`), `versificationmgr.cpp` and `canon_segond.h` /
`canon_calvin.h`, from the same Debian source archive as the Flatpak manifest.
Xiphos `crosswire/xiphos`, `src/backend/sword_main.cc` uses SWORD `setKey` for
rendering. This source inspection is not a claimed graphical reproduction
of Xiphos with the client's exact installed versions.

Real-resource validation helper: `tools/check_study_resolution.py`.
Never commit downloaded scripture/modules. Keep virtual-display results
distinct from the client's manual GNOME checks.

Validated with the real downloaded CrossWire modules, offline under Xvfb:
FreSegond1910 4.0 / Segond / zText, FreLSN1872 1.0.1 / Calvin / zText, MHC
2.2 / KJV / zCom4. Genesis 1:25 resolves to MHC's actual Genesis 1:24–25
entry; Psalm 3:2 resolves to KJV 3:1 and Psalm 51:3 to KJV 51:1.
Both Bible texts display at Genesis 1:19 and the tested Psalms. Comparison
widths measured 707/707 pixels with equal padding, plus equal allocation with
study open. Screenshots: `captures/study-{resolution-35,comparison-36}-{fr,en}.png`.
Full local suite: 125 tests passed with GTK, SWORD, Babel 2.18.0 and ISO
translations installed. Published in `1572378`: CI 39516862994 and alpha
publication 39517587724 both succeeded. A separate system client updated to
Flatpak `1c350c31d04396e05cb1e53b2188e699ac622cb8a04077077c3d3d10adefeecf`,
revision `39517587724-2`, matching public provenance. Real offline checks also
passed in the constructed Flatpak; native reverse MHC Psalm 3:1 → Segond
Psalm 3:2 following passed without history spam. Issues #35/#36/#25 remain
open for their outstanding manual acceptance checks.

## Batch 2 — cache and installed-state increment

Implemented per-provider versioned metadata caches, atomic replacement,
15-minute freshness, as-completed provider delivery, bounded network reads,
cache retention after failure and separate refresh/transfer state. Search,
selection, details, installed view and downloads stay available while sources
refresh. Closing invalidates pending callbacks. Transfer completion retains the
original resource identity; an installed detail shows a check and “Installed —
available offline” instead of a Download action. Library top spacing is 16 px.

Local full suite: 132 tests passed. Real four-source measurement (412 resources):
first results 0.823 s, all sources 2.047 s; warm cache 0.006 s (data/backend,
not a claimed desktop launch measurement). Per-source network/parsing seconds:
Extra 0.812/0.010, AndBible 0.968/0.003, CrossWire 1.509/0.072, STEP 2.023/0.020.
The offline GTK checker verifies immediate cached resources, French filtering,
real installed Lausanne state and stable detail selection.

Published source `20361ce`, CI 39518470411 and publication 39519173539 both
green. A separate system client updated to Flatpak
`23a16b55f9a6b2334a89cb46256f7841d808a5892c30f629e1ee5ee37bab13b6`,
revision `39519173539-2`, matching public provenance. The published Flatpak
passed the offline cache/installed-detail checker as well. Manual GNOME
acceptance is still pending.

eBible investigation: AndBible's official repository file at commit
`7e73c11508f32e4f531d531f6d5b110dd2a1f204` lists `/sword` and `/sword/zip`.
The normal Bible HTTP client retrieves the catalogue. Do not use guessed
`F10.zip` (404): its actual identity is `fraLSG1910eb`. Source addition is a
separate reviewable policy change under AGENTS.md, not an unreviewed registry
edit on main. Other observed French identities: `fraFOB1744eb`, `frajnd2024eb`,
`francl2022eb`, `frasbl2022eb`. `frd2018eb` is Fordata (`frd`), not French;
do not merge it into `fr`.

eBible is prepared in **PR #38**, branch `feat/34-ebible-provider`, commit
`20d7328`, requiring source-policy review. Local 133 tests and branch CI
39555537014 are green. JND 2.17 installs and matches direct SWORD output
offline; actual French catalogue/reader screenshots and the comparison table
are committed on that branch. F10 catalogue 90.0 versus package 99.0 has
different notices and is correctly refused by the unchanged conditions guard.
Do not merge this PR or announce eBible in the public alpha without review.

## Batch 3 — reading increment

Implemented Compare → Aa → Fullscreen in the active Bible viewport, with fixed
clearance and scoped palette surface; approved upstream CC0 GNOME icons;
14 pt/Airy/Narrow defaults preserving explicit old preferences; persisted Very
airy; always-visible top reference entry; removed redundant bottom expander
and selector download action; visible My notes workspace title.

Full local suite: 134 tests passed. Real-resource GTK checks and screenshots
cover four palettes, Airy/Very airy at 14 pt, selector and notes workspace.
`tools/check_reading_presentation.py` intentionally resets only a supplied
disposable TEST profile. Never run it against the client's profile.

**#31 product decision pending:** the existing version dropdown is retained
until an approved alternate active-translation chooser exists. Do not remove
an essential function or invent a new location silently. See
`docs/READING_ALPHA_12_31.md`. Existing history, notes, backup and faithful
source presentation have been preserved and tested, not rebuilt. CI and alpha
publication for this increment still need verification.

Client test order for this batch:
1. Update the existing system alpha installation; reopen the saved session.
2. Select FreSegond1910 and Matthew Henry Complete at Genesis 1:25, then
   Psalm 3:2 and Psalm 51:3. Check the displayed commentary reference.
3. Compare Lausanne at Genesis 1:19; open/close study and resize. Check both
   texts, equal widths, selection/copy and passage preservation.
4. Alternate Bible/commentary scrolling, including a long entry; restart and
   check saved positions. GNOME/Wayland, keyboard/focus and accessibility
   remain manual acceptance checks.

## Remaining batches

2. #32/#33/#19: published; manual acceptance remains. #34: PR #38 awaiting review.
3. #31/#16/#12/#15/#20: reading increment implemented and locally tested;
   publication verification pending; #31 version placement decision pending.
4. #24/#25: continuous chapter pagination, book starts on the left, uniform
   palette, preserve anchors and avoid hidden Bible navigation in immersion.
5. #27/#37/#28: safe highlights (reviewable persistence/backup design), page
   and screenshots in an unpublished PR, public notification API evidence.

## Manual client checks still required

No cloud or Xvfb check establishes manual GNOME/Wayland, accessibility or live
desktop high-contrast validation. Do not close issues that require those
checks until their actual acceptance criteria have been confirmed.
