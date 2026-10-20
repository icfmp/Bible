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
translations installed. CI/Flatpak publication verification is still pending.

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

2. #32/#33/#19/#34: immediate per-source catalogue cache, progressive refresh,
   accurate installed/selection state, spacing, verified eBible source (PR
   required for content-source policy).
3. #31/#16/#12/#15/#20: simplify selector; keep translation choice accessible;
   overlays/icons/defaults; preserve working history, notes and text fidelity.
4. #24/#25: continuous chapter pagination, book starts on the left, uniform
   palette, preserve anchors and avoid hidden Bible navigation in immersion.
5. #27/#37/#28: safe highlights (reviewable persistence/backup design), page
   and screenshots in an unpublished PR, public notification API evidence.

## Manual client checks still required

No cloud or Xvfb check establishes manual GNOME/Wayland, accessibility or live
desktop high-contrast validation. Do not close issues that require those
checks until their actual acceptance criteria have been confirmed.
