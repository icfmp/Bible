# Alpha stabilization handoff — 21 October 2026

## Offline continuation — 22 October 2026 (current local work)

Resume from [OFFLINE_RESUMPTION_2026_10_22.md](OFFLINE_RESUMPTION_2026_10_22.md)
before using older publication/candidate statements below. Base **884591c** is
confirmed locally. Its remote CI, reported nine installations/eight comparison
configurations and corresponding signed publication remain unverified. The last
saved signed provenance is still **6560dc4 / 39674239853-2**.

Local implementation commit **fa2bfa0** on `feat/24-offline-preparation` adds #24 document/plan caching,
cooperative cancellation, UTF-8 preparation optimization and heading keep-with-next.
34 local tests pass; five native GTK tests skip. These include actual headless
Pango with synthetic data, not real installed-module or built-package checks.
GTK/Adwaita/SWORD/Flatpak and old test profiles are unavailable in this executor;
no further Docker/network retry is made. #57 retains the explicit Luther guard:
required AndBible/JSword conversion sources/tables are missing and itemized in
the report. Existing #53–56 corrections are preserved; package checkers and the
remaining validation order are prepared there. No new alpha or remote delivery
is claimed, and the signed channel/user data are unchanged.

## Completed pending deliveries — current verified state

This section supersedes all older pending-review/publication/issue-state entries
below. PRs **#41 → #38 → #40 → #39** were technically reviewed and merged in that
order under the client's authorization. Final application source **6560dc4** is
actually available through the existing signed alpha, revision **39674239853-2**,
Flatpak commit `f36e063db7004fc6a20aa8051234e2f488f8a09c5b6ce3e399d779c1e595452a`. Main CI **39673122687** and publication
**39674239853** are green; downloaded CI bundle, public provenance and updated
system alpha client match. Signing fingerprint/channel/URLs/configuration are
unchanged. Actual profile notes/session/preferences/highlights/backup hashes
survived the update unchanged.

The temporary delivery hold after `1e7613d` is resolved: a native GTK layout abort
from redundant highlight repaint was diagnosed and fixed, without disabling
synchronization or persistent marks. Final installed /app checks pass: 28 affected
unit tests + one isolated native pointer case, 16 palette pixel states, real book
pagination, eBible offline fidelity, persistent marks/backup, contextual actions,
MHC true end/both synchronization directions/notes/session and temporary-cue
coexistence. All 159 full tests and 70 French UI CI tests pass. These automated
Xvfb results do not replace client GNOME/Wayland/accessibility acceptance.

Page is public and verified: https://icfmp.github.io/Bible/ . Its approved layout,
real signed-alpha hero, current package provenance, installation/update/key/source
links and actual HTTPS signed install/update all pass. #37 deployment criteria are
satisfied. #34/#27/#24 remain open for client GNOME acceptance; the client already
validated and closed #51/#36. eBible JND 2.17 installs and reads offline; upstream
F10/FOB/FRANCL/SBL metadata conflicts remain refused by the unchanged guard.
Personal persistent marks are now published, independently from the commentary cue.

Detailed final source/revision/proof/remaining tests:
[PENDING_DELIVERIES_2026_10_21.md](PENDING_DELIVERIES_2026_10_21.md).
No pending PRs remain. #26 is excluded, #28 retains its manual fallback, new
OpenBible features and the general code review remain deferred. This final
handoff is documentation only; the published application source above is exact.

## Product-manager cleanup — current tracking decision

The client requested a project-wide cleanup on 21 October 2026. This section
supersedes older issue-state and pending-product-review statements below;
historical delivery evidence is retained unchanged.

- Published application remains **c964162**, revision **39640813062-2**.
- Implementation issues **#12, #15, #16, #19, #20, #25, #32, #33, #35,
  #42, #43 and #45** are closed as implemented/tested/published. Their still
  unperformed manual GNOME/accessibility acceptance is explicitly transferred
  to [#52](https://github.com/icfmp/Bible/issues/52). Closing these tickets
  does not claim those manual checks passed. New defects get focused issues
  or reopen the original issue.
- **#51 and #36 stay open** for the client's crash and comparison retests.
- **#31** retains the active-version chooser placement decision; **#44** retains
  the newer unified study-tab direction; **#46** awaits Highlight from PR #40.
- PR **#38** (eBible), **#39** (continuous-book pagination), **#40** (personal
  highlights) and **#41** (landing page) remain unmerged. Incorporate the current
  main fixes and rerun affected checks before integration. Do not advertise
  their candidate features as public-alpha features.
- **PR #41 product presentation is approved** after desktop/mobile/dark review.
  Before merge/publication, refresh its old 4a285f3 hero using an authentic
  current-alpha screenshot, update review evidence, integrate main and verify
  CI/channel preservation. Keep **#37** open until public HTTPS installation
  and update links are checked. No redesigned page was published by this review.
- **#47–#50** remain the approved OpenBible backlog. **#26** stays excluded;
  **#28** retains manual Do Not Disturb guidance, not automatic suppression.
- No general code review, pending PR merge or application-code change was
  performed as part of this bookkeeping and product review.

## Current priority follow-up — #51 crash, then #36 surfaces

Verified published application source: `c9641627b5449d940634443dc4a504969a73e679`;
crash increment `679f8e6`, visual/recovery increment `c964162`. Both pushed.
CI **39639628244** and publication **39640813062** are green. Actual public
revision **39640813062-2**. The existing system alpha client
updated to `ea17ae42b4407397212c9d92a926e99b625e03a1c269bdb93bbadc794f07d57a`, exactly matching public provenance.
Signing fingerprint unchanged: `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.
CI bundle SHA-256 `18c651446c2d32df71d900868c1fccc6f927c6855c8ccff3b9c798890e0b17e4` matches both the downloaded,
natively tested bundle and the public provenance. No channel/configuration/key
or token change. Proof: `evidence/alpha-51-36-provenance.json`.

- #51 reproduced in the real original /app Flatpak (GTK 4.20.4, Segond 4.0,
  MHC 2.2): native 133/SIGTRAP in visible-byte-index hit-testing around invisible
  inline source-decoration tags, after several progressive loads in Genesis.
  Python/GDB traces: `evidence/commentary-51-original-trace.txt`. Controlled
  original-package run with only that attribute omitted survives 100 rounds.
- Verified source decorations now have zero font scale, retaining original
  characters/offsets and exact Copy; unknown/literal text is unchanged. Scroll/
  load callbacks are coalesced/cancelled, retention capped at 20 entries, terminal
  loads no-op. Study synchronization is preserved. See `COMMENTARY_CRASH_51.md`.
- The real candidate-runtime probe survives 100 native rounds; the complete
  boundary tool crosses loads/evictions, reverse/wheel/keyboard/long drag, both
  sync directions, tab/source/hide changes, actual final MHC Rev.22.20–21,
  repeated terminal scrolling and saved note/session reopen.
- #36 confirms native gray (250/250/250) around White (255/255/255). Both Bible
  surfaces and common gutter now share the active palette; study stays secondary.
  Actual pixel checks cover four palettes, both emulated high-contrast modes,
  study open/closed, resize, unavailable/empty and restored content. Recovery
  also fixes indexing a None document signature after an unavailable comparison.
  See `COMPARISON_SURFACE_36.md` and its real screenshots.
- 145 local tests pass. Native real Segond/Lausanne following, equal widths,
  selection/reflow and no-history tests pass. Native study wheel and two >1.5 s
  drags pass with focus/history retained. Candidate source overlays are explicitly
  identified. The actual CI bundle passes the complete native real boundary
  probe with asserted /app imports (evidence/commentary-51-fixed-package.txt).
  After the actual public update, all 8 affected tests pass on /app code, and
  the full palette/state pixel matrix passes on the public alpha. Final captures
  are from that public Flatpak, not the earlier source overlay.
- Issues 51/36 have English implementation/evidence comments and remain open
  for manual GNOME/Wayland/physical trackpad/live high contrast/accessibility.
- Current GNOME retest order: (1) update the existing alpha and check notes/
  session, (2) scroll MHC through successive loaded boundaries, reverse, use
  keyboard/physical trackpad and long scrollbar drags, (3) reach Revelation 22
  and keep scrolling at the real end; change tab/source and hide/reopen study,
  then restart and check positions/notes, (4) compare Lausanne in every palette
  and actual desktop high contrast, study open/closed and resized; check exact
  Copy, selection and both reference-following directions.
- No pending PR merged or new OpenBible functionality. #26 stays excluded.
  Review branches have not been revalidated against this new follow-up; bring
  main's fixes into candidates before any later reviewed integration.

**Previous delivered application source:** `08a00d2c3133764fbfd7e70f2ad5350cb0e1c3cf`.
The client corrected #44 to a RIGHT drawer, Bible LEFT. The targeted follow-up
is implemented, tested, pushed and published. All 143 tests and real native
drawer/coverage checks pass. Captures show the corrected layout.

**Verified final delivery:** CI [39631126308](https://github.com/icfmp/Bible/actions/runs/39631126308)
and publication [39632604890](https://github.com/icfmp/Bible/actions/runs/39632604890)
are green. Public revision **39632604890-2**. An existing system
alpha client actually updated to Flatpak
`d14a066a86a5d17247ce3ced766373b9dd8b3969690f85cf1adb346f66aa74e7`, matching public provenance.
Fingerprint unchanged: `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.
The public install/update workflow also verifies user-data preservation. No token,
signing key, channel or repository configuration was regenerated or changed.
The PR41 redesign was not published by this ordinary alpha delivery.
Eleven affected geometry/native UI/context/action tests also pass in the actually
updated public alpha, with imports asserted under `/app/lib/bible-python` rather
than the source checkout. This is GTK/Xvfb evidence, not manual GNOME acceptance.

## Earlier stabilized increments — before the #51 report

- #43, #42, #12/#15 and #36 were delivered first in `d48c760`: CI
  39591287215/publication 39592269695 green, revision 39592269695-2,
  actual public update verified. See `CORRECTIVE_ALPHA_42_43_36.md`.
- #44 initially used a full left drawer (superseded by the client's explicit
  correction to RIGHT); the initial increment followed in `370d2e5`/`ef4df7e`: 140 tests, real GTK
  captures/slide recording and native study wheel/long-drag checks. Published
  source ef4df7e, CI 39598544372/publication 39599447490 green, revision
  39599447490-2, actual installed Flatpak 770f499300b796448ed32bd868446961c9280cdc659051e8de9c400e22307d87.
  The first drawer CI caught an unallocated test button; the checker now waits
  for its native allocation. The actual navigation behavior was preserved.
- #45 temporary mapped full-range dotted cue: `247a1dc`; #46 frozen-source
  passage actions: `71524e2`; native pointer/keyboard CI fixture: `f8395bc`.
  Published interim source f8395bc: CI 39607925555/publication 39609190124
  green, revision 39609190124-2; public install/update checks passed.
  143 full local tests, 10 final affected tests and real offline native action,
  popup, coverage and comparison probes pass. Final native study wheel and
  >1.5-second drags pass in both directions with focus/history preserved.
- PR #40 remains unmerged at `09d24c6`: main through 08a00d2 coordinated;
  CI 39631209621 green (148 full tests plus 67 localized checks); 11 affected
  local tests pass after the side correction. Earlier 3496f1a: CI
  39608953767 green, 148 full tests,
  native actual second-Bible Highlight source/versification verified; personal
  overlap, hide/show independence and immersion verified. This is the explicit
  remaining dependency for #46's Highlight button; main has Copy/Note/Compare.
- PR #39 remains unmerged at `f079f9d`: main through 08a00d2 coordinated;
  CI 39631262242 green (146 full tests plus 67 localized checks); 11 affected
  local tests pass after the side correction. Earlier c981f95: CI
  39609210333 green, 146 full tests,
  actual offline Genesis 211 exact pages/42 chapter continuations, 1.47 s
  preparation, 75 GTK heartbeat ticks, maximum observed gap 0.365 s. Canonical
  reflow anchor and native contextual actions pass. Whole-book shaping keeps
  nonbreaking presentation spaces without redundant expensive Pango ranges.
- PR #38 source-policy review and PR #41 product-manager review remain pending.
  The new landing page is prepared with screenshots, not published. Existing
  signed-channel publication does not publish the PR41 redesign.
- The client validated GNOME Bible↔commentary scrolling on 4a285f3. Preserve
  it; automated Xvfb evidence does not validate the new layout on GNOME or close
  every #25 criterion. No issue is closed solely on automated evidence.
- #26 excluded; #28 manual fallback preserved. #31's chooser-location question
  remains unchanged. The general code review is a separate future assignment.
- All code/captures/review notes are committed and pushed. Working container
  `bible-night`: `/src` is this checkout, `/evidence` is host `/tmp`. Test profiles
  under `/tmp/bible-night-*` are disposable and must never be used as client data.
  For packaged probes run from `/tmp`, import `/app/lib/bible-python` before
  `/src`, and assert `bible.__file__` starts with `/app/`; do not test source
  overlays accidentally. Public branch `//alpha` is distinct from `//master`.

### Ordered client checks for the final source (right drawer)

1. Update the existing alpha and reopen saved resources, notes, session and
   explicit appearance preferences. Reset only a disposable profile to check
   14 pt / Very airy / Narrow defaults.
2. Passage/comparison/Aa: trigger, outside click, Escape; comparison selection
   applies and closes. Resource details: no automatic selection, deliberate
   copy works, no visible RTF paragraph commands or lost attribution.
3. Both Bibles: complete gray verse numbers, no orphan marker, exact partial
   copy, equal widths and bidirectional reference-based following (also Psalms).
4. Right commentary drawer: F9, slide, narrow/wide, theme, local Aa/conditions,
   immersion/return; repeat the previously working two-way scroll/long entry.
5. Temporary full commentary range: wrapped verses, hide/reopen, themes and
   pagination. Deliberate Bible selection: exact Copy, correct original-source
   Note, Compare, keyboard/pointer selection and Escape/outside dismissal.
   Highlight and continuous-book pagination await PR40/PR39 review and delivery.

## Historical overnight baseline (superseded where noted)

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

## Historical delivery and resumption before the corrective work

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

## Historical checks for the earlier alpha

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
