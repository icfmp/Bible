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
source presentation have been preserved and tested, not rebuilt. Published in commits `380adec` and `4a285f3`. CI **39557301541** and alpha
publication **39558047623** succeeded. The actual system alpha update matched
Flatpak `46b9ed2d2077d6163470fc37450dc33eb86bc6e59e838566fbc0f3e2dba0f5a3`,
revision `39558047623-2`. Packaged presentation checks passed using `/app` code.
The first CI (39556671785) failed an obsolete 19 pt assertion; its publication
was skipped. The checker was corrected before the successful runs above.
All three native input, reading and scroll checks also passed.

Client test order for this batch:
1. Update the existing system alpha installation; reopen the saved session.
2. Select FreSegond1910 and Matthew Henry Complete at Genesis 1:25, then
   Psalm 3:2 and Psalm 51:3. Check the displayed commentary reference.
3. Compare Lausanne at Genesis 1:19; open/close study and resize. Check both
   texts, equal widths, selection/copy and passage preservation.
4. Alternate Bible/commentary scrolling, including a long entry; restart and
   check saved positions. GNOME/Wayland, keyboard/focus and accessibility
   remain manual acceptance checks.

## Review candidates — pushed, not published

The following PRs must not be described as public alpha features. Review may
proceed independently; no PR was merged merely to unblock another batch.

| Issue | PR / branch commit | Evidence | Next action |
| --- | --- | --- | --- |
| #34 | [#38](https://github.com/icfmp/Bible/pull/38), `20d7328` | 133 local tests; CI 39555537014 green; real eBible JND installation, offline reading and constructed Flatpak checked | Source-policy review; F10 upstream catalogue/package metadata mismatch remains rejected |
| #24/#25 | [#39](https://github.com/icfmp/Bible/pull/39), `db0e6a6` | 137 local tests; CI 39559694478 green; constructed Flatpak offline Genesis: 180 exact pages, 42 chapter continuations, 1.397 s preparation/stabilization with 63 GTK ticks; Very airy anchor retained | Architecture review, manual page/book boundaries and GNOME responsiveness |
| #27 | [#40](https://github.com/icfmp/Bible/pull/40), `38cf200` | 139 local tests; CI 39561285495 green; constructed Flatpak three real verse highlights, unchanged text, hide/show, backup/merge and list checked | Persistence/UI review; native file portals, high contrast and accessibility |
| #37 | [#41](https://github.com/icfmp/Bible/pull/41), `933516c` | 135 local tests; desktop/mobile/dark browser checks; controlled real signed install/update, data preservation and corrupt-summary rejection | **Product-manager review before merge or publication**; branch CI 39563016832 and restoration CI 39563046980 green |

Details and screenshots are in each PR's review document. #37 uses the actual
published `4a285f3` application screenshot, not the proposed pagination or
highlights. The controlled channel check used an isolated client and a disposable
**test-only** signing key; the existing public key was preserved. Public source,
license and notices links returned HTTP 200. Generated assets/provenance and
historical channel sentinels survive repeated rendering.

No combined PR39/PR40 integration has been claimed: after review, integrate
sequentially and run the affected tests before any new alpha. eBible F10's
inconsistent upstream metadata is not worked around. #31 still needs an approved
location for the active-translation chooser. #26 has not been changed.

## #28 — researched, honest manual fallback retained

See `NOTIFICATION_INTEGRATION_28.md`. The pinned public Notification/Inhibit
contracts do not provide a process-bound global notification suppression lease.
The actual alpha sandbox's container session lacks a desktop portal; this is not
a claim about the client's GNOME session. No actual suppression, crash recovery
or critical-alert filtering has been demonstrated. No host settings or permissions
were changed. Keep #28 open, retain manual Do Not Disturb guidance.

## Current delivery and precise resumption

- Public application source remains **`4a285f3`**, revision **39558047623-2**,
  Flatpak **46b9ed2d2077d6163470fc37450dc33eb86bc6e59e838566fbc0f3e2dba0f5a3**.
  Later main documentation commits do not imply a newer published application.
- Routine batches 1–3 are published; review batches above are pushed separately.
  No new public release, signing change, Pages configuration change or token
  regeneration was performed. Git pushes succeeded.
- Working container `bible-night` remains available. `//alpha` is the public
  signed build; `//master` currently contains the PR40 test candidate.
- Candidate artifacts and detailed logs are in `/tmp/bible-*-candidate`,
  `/tmp/bible-*-packaged.log`, `/tmp/bible-page-channel-test.json` and
  `/tmp/bible-night-alpha3-proof.json`. They are disposable; authoritative code,
  review notes and captures are committed/pushed. Never use these test-profile
  helpers against the client's personal profile.
- If this session is interrupted, PR41 CI 39563016832 is green. Do not publish its page before PM review.
  Process reviews and the outstanding #31 product decision. Manual validation remains open.

## Ordered client checks on the published alpha

1. Close Bible, update the existing system installation with
   `flatpak update --system io.github.icfmp.Bible//alpha`, reopen and check saved
   passages, notes, resources and explicit appearance preferences.
2. FreSegond/MHC: Genesis 1:25, Psalm 3:2, Psalm 51:3; inspect the actual commentary
   entry reference and both scroll directions, including a long entry.
3. Compare Lausanne at Genesis 1:19, resize and open/close study: two complete,
   equally allocated texts; preserved anchor, selection and copying.
4. Reopen Library with cache, search French resources, test offline restart,
   installed status and a real requested download while catalogues refresh.
5. Compare/Aa/fullscreen placement; 14 pt/Airy/Narrow on a new/reset TEST profile,
   Very airy, four palettes, live system high contrast; reference selector,
   history, note filters and unsaved-change guards. Keep personal data backed up.
6. Review PR38–41 separately. Continuous books, highlights, eBible and the new
   website are not yet in the public alpha; do not test for them there.

## Manual client checks still required

No cloud or Xvfb check establishes manual GNOME/Wayland, accessibility or live
desktop high-contrast validation. Do not close issues that require those
checks until their actual acceptance criteria have been confirmed.
