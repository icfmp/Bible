# Bible 0.1.0-alpha.27

This batch delivers the native reading, study, Library and Notes follow-ups in PR #244. It preserves downloaded Scripture, canonical references, annotations, linked passages, preferences and offline study resources. No profile reset or note schema change is required. All 25 implementation issues remain open for client acceptance.

## Changes since alpha.26

- **Cards and original words (#204–#206):** compact, visibly actionable native cards across references, text/theme results, occurrences, places and Notes; independent embedded citation links; no redundant hover preview. A progressive passage → word → occurrences flow explains Greek/Hebrew exploration and keeps technical details secondary. Real English STEP glosses are identified honestly; no French lexical text or translation alignment is invented.
- **Icons and offline fonts (#207–#211, #220):** consistently use the requested dictionary, notebook, location, filter and talking symbols, removing unused custom assets. Four unavailable runtime symbols are supplied as the client's explicitly approved, pinned official CC0 SVGs. Roboto and Roboto Serif ship with their licenses and work offline; existing saved font choices remain intact. Translation-note markers preserve exact locators, mouse and keyboard activation.
- **Library and installation (#212–#214):** repair packaged AppStream metadata and GNOME Software details; update existing Library rows without rebuilding the visible model; automatically open the first usable downloaded Bible and repair only an unusable active reader, preserving valid reading/Notes sessions and unsavable drafts.
- **Places and Study (#218–#226):** reviewed, separately maintained place context with documented identities, uncertainty and attribution; optional hash-checked Jerusalem photo with bounded cache and full-image viewer. Remove redundant translation-notes and commentary overflow controls while retaining inline notes and unique contextual navigation. Simplify search loading, Study tabs and Aa grouping; restore one native resizable divider; make book introductions discoverable and render source headings, paragraphs and emphasis faithfully. A measured libshumate lost one-shot frame wakeup is repaired in the existing native packaging patch.
- **Selection and commentary (#227–#228):** show the Original text label in the adaptive toolbar; preserve native backdrop caching and immediate dismissal on scroll. Commentary can continue and reverse across chapter boundaries in ordinary and immersive reading using a bounded entry window; Bible text loading remains unchanged.
- **Notes (#230–#232):** consistent compact quick, inline, workspace and summary surfaces; source context remains separate from the user's text; labels, linked passages and confirmed deletion stay accessible. Remove redundant wide Filters and Study follow/collection buttons while preserving adaptive sidebar access, manual browsing, automatic following, drafts and the main Notes route. Summary cards show the user's note rather than repeating Scripture/translation, as specified in #205.

## Verified source, build and publication

- PR: https://github.com/icfmp/Bible/pull/244 (merged).
- Exact source/tag: `b8142132c9655abeda03292c6382512c198a557c`.
- Main CI: https://github.com/icfmp/Bible/actions/runs/42411803046 and restore check https://github.com/icfmp/Bible/actions/runs/42411802981 — successful.
- Signed channel deployment: https://github.com/icfmp/Bible/actions/runs/42413962294 — attempt 2 successful, reusing the same verified build. Attempt 1 published Pages but encountered a transient HTTP503 at the immediate public-update check; the successful retry and independent retained-profile update verified the final public repository.
- Public installed-profile alpha.26 → alpha.27 update: https://github.com/icfmp/Bible/actions/runs/42411810775 — successful, same profile and resources retained.
- Final signed OSTree: `86936bc90a52e1efdf918d68e97d8ce3409ad0c017dc69d9b3eab8f55499374d`.
- Existing signing fingerprint: `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.
- Matching [source archive](https://github.com/icfmp/Bible/releases/download/alpha-source-archives/Bible-b8142132c9655abeda03292c6382512c198a557c-sources.tar.gz), SHA256 `49cd93a3cd7bf1bb2d6f655c32ac2410aa119fb42c5d3b59db071633fad58eae`.

No application rebuild or tag movement was performed to create this numbered release. Unrelated open PRs #242 and #245 are not included.

## Tests and actual application evidence

- Host suite: 497 tests, 26 environment skips; French suite: 183 tests, 2 skips. Native pointer/keyboard/citation actions, 360px/150% editor and draft guards, backup/linked-reference compatibility and real CrossWire integration passed.
- The actually built and installed GNOME49/GTK4.20.4 Flatpak passed its 264-test suite, 13 immersion tests, 7 selection/inline tests, actual YouVersion opening, real study/navigation/offline checks, software-GL rendering/cache checks and sustained/reversing scrolling in single, parallel and Study modes.
- [Additional exact-bundle tests](https://github.com/icfmp/Bible/actions/runs/42411253489) downloaded and converted actual Semeur BDS resources, then exercised offline French/English Greek Mark7:4 and Hebrew Genesis1:1, occurrences/back navigation, Jeremiah introductions including the last paragraph, packaged icons/fonts and a 360px dark place dialog. The tested candidate tree is byte-identical to the merged application tree.
- GNOME Software46 was checked with the actual local bundle and again after the signed public update: name, icon, description and real application screenshot are visible from `bible-alpha`.
- Retained-profile checks preserved the synthetic linked note/labels, highlights, saved typography, session and downloaded modules/study data. The preservation receipt records 27 module files, 5 study files and the same profile reused. These tests do not inspect or reset the client's own profile.
- Actual GTK screenshots are attached as evidence archives. Each archive identifies its source/environment. The new before/after captures use exact alpha.26 `6faab9201d4fdf496ccb931c62b1cf9aa9e7f233` versus merged `b814213`, matched saved DejaVu Serif14, GTK4.18.6/X11/Cairo, French/English, light/dark and wide/narrow windows; they are **development captures**, separately labeled from installed-Flatpak GTK4.20.4/GL captures. All PNGs are unedited native captures. Old temporary development captures were lost on environment resume; replacement captures were recorded on 8 November without changing the application. Notes in capture profiles are synthetic, downloaded Scripture is real, and no profile/database/full translation is distributed in the evidence.

## Measurements and limits

- Actual installed main-build GL wheel input: first motion **0.84–1.22ms**, first usable GTK paint **13.80–20.99ms** across single/toolbar/parallel/Study cases. With the toolbar initially open: input→dismiss start **0.18ms**, dismissal **0.22ms**, first motion **1.11ms**, first paint **14.74ms**; the bar is hidden before paint, backdrop released and placement stopped. Direction reversals remained responsive and post-stop checks passed. These are measured CI-machine timings, not a benchmark of the client's computer.
- Cached visible-idle and dismissed/hidden backdrop checks recorded **zero** Python snapshot/change/adapt/watch calls. A deliberate diagnostic control that keeps the bar visible while moving its background by scrollbar adjustment remains expensive: ~226.84% of one CPU versus ~30.16% without the bar, ~1.83% idle, ~29.28% after dismissal. Normal wheel gestures dismiss on the first event; this control is not normal wheel behavior. Raw measurements and method are included rather than hidden.
- Four actual BDS/Segond × MHC/Wesley commentary combinations completed eight forward/reverse cycles. Alpha.26 stopped at chapter1; the candidate continued in both directions with 13–14 loaded entries. Development RSS stabilized around159.6–175.2MiB in these cases. Startup/immersion timings do **not** establish a general speed improvement; the detailed comparison table and boundaries are included.
- Real native Library installs retained279 Bible/41 commentary row objects with zero model-change events; the same visible surrounding row remained within3/0 logical pixels after the final frame. NT-only Geneva1669 opened Matthew1:1; installing Wesley retained the active Bible.
- Client usability acceptance of #206 is still required. The walkthrough is in the evidence bundle. STEP's available glosses can be English; uncertain place identities and unavailable correspondences are reported locally without invention. Optional reviewed history/photo coverage is currently Jerusalem, not a general encyclopedia service.
- Automated and manual developer validation used Linuxx86_64/X11 and software rendering. It does not establish behavior on the client's GNOME/Wayland/GPU, touch devices, Windows or macOS. A narrow Notes allocation warning is reproducible in both old and new development runtimes; captured editors remain usable within the viewport. Existing source/versification limitations remain applicable.
- Project5 writes remain forbidden with `Resource not accessible by integration`. Once this release is verified, the25 issues are eligible for a **manual In validation** transition; no project status or client acceptance is fabricated, and issues remain OPEN.

## Install or update the signed alpha

```sh
flatpak install --user https://icfmp.github.io/Bible/alpha/Bible.flatpakref
flatpak update --user io.github.icfmp.Bible//alpha
```

Use the signed channel above. The CI's unsigned `master` test bundle is intentionally not attached as a signed-alpha installer. Evidence and provenance assets have SHA256 checksums; open each evidence archive's `overview.html` or README after extraction.
