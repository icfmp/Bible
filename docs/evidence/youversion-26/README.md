# Issue 26: Bible.com offline acquisition and fidelity

**Delivered:** signed alpha **40456634652-2**, source `d39a99eb44be1c3257a9ba75f60f7f324282b1b1`, merged through [PR 134](https://github.com/icfmp/Bible/pull/134). The application tree is identical to the verified feature source `916b35a627fb80848107bc3a5701313c903e9883`. Numbered release #87 remains paused, and issue #26 stays open for client acceptance.

## Seven actual editions

| Edition | ID | Chapters | Introductions | Source units | Editorial notes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Semeur 2015 | 21 | 1,189 | 66 | 31,112 | 7,363 |
| Segond 1910 | 93 | 1,189 | 66 | 31,170 | 9,751 |
| J.N. Darby | 64 | 1,189 | 0 | 31,170 | 6,340 |
| Ostervald | 131 | 1,189 | 0 | 31,165 | 0 |
| King James Version | 1 | 1,189 | 0 | 31,102 | 0 |
| American Standard Version | 12 | 1,189 | 0 | 31,102 | 16 |
| Berean Standard Bible | 3034 | 1,189 | 0 | 31,086 | 4,854 |

Local independent DOM → OSIS → native SWORD → application Reader comparison passes for every chapter. Comparisons preserve case, punctuation and words, normalizing only NFC and semantic whitespace. Every individual OSIS document validates against OSIS 2.1.1: 8,455 documents, zero schema errors. See [local counts and limits](local-verification.json).

The local native GTK suite passed 358 tests, followed by 62 affected French tests. After the introduction-only spacing correction, 31 affected tests passed. Exact final-source ordinary CI [40427232547](https://github.com/icfmp/Bible/actions/runs/40427232547) and installed Flatpak proof [40427232536](https://github.com/icfmp/Bible/actions/runs/40427232536) both pass. The installed suite also passes 166 tests plus 11 immersion checks; all 14 online/offline seven-edition receipts pass. See [installed receipts](installed-flatpak/build-info.json) and [final source results](final-source-ci.json). Earlier source `34a64d7` passed its source job (358 tests, two native-scheme tests skipped in the unpatched system environment; 144 French tests); its remaining workflow was cancelled when the real introduction presentation problem was found. Skipped system tests are not counted as native reference-system validation; patched local and packaged checks exercise those systems.

The installed proof acquires the six additional editions through the installed application's actual downloader, with no archive seed. Semeur reuses the already acquired verified archive. Each edition is then reopened with Flatpak `--unshare=network`. A shared disposable profile retains earlier resources, personal notes and reading preferences. Only statistics and hashes are uploaded; no Bible archive, full source HTML/OSIS, compiled module or profile is distributed here.

## Actual GTK views

These are unedited X11 root-window captures from the **local source environment**, GTK 4.14.5/OpenGL under Xvfb. They are not screenshots of the client's desktop or the installed Flatpak. The resources were reinstalled through the final application worker from retained verified archives, in a copy of the test profile; no existing client data was changed. The gray outside the window is the test desktop. Small-window captures exercise responsive panel collapse, rather than squeezing the study drawer and two columns into 360 pixels.

| Actual edition | Light | Dark |
| --- | --- | --- |
| Semeur | [view](local-gtk/edition-21-white.png) | [view](local-gtk/edition-21-dark.png) |
| Segond | [view](local-gtk/edition-93-white.png) | [view](local-gtk/edition-93-dark.png) |
| Darby | [view](local-gtk/edition-64-white.png) | [view](local-gtk/edition-64-dark.png) |
| Ostervald | [view](local-gtk/edition-131-white.png) | [view](local-gtk/edition-131-dark.png) |
| KJV | [view](local-gtk/edition-1-white.png) | [view](local-gtk/edition-1-dark.png) |
| ASV | [view](local-gtk/edition-12-white.png) | [view](local-gtk/edition-12-dark.png) |
| Berean | [view](local-gtk/edition-3034-white.png) | [view](local-gtk/edition-3034-dark.png) |
| Semeur, 360 × 600 | [view](local-gtk/edition-21-white-small.png) | [view](local-gtk/edition-21-dark-small.png) |

The real Semeur introduction exposed stacked paragraph breaks from nested source block wrappers. The correction reduces the longest newline run from six to two, with every non-whitespace character unchanged; see [measured comparison](introduction-spacing.json).

| Introduction | Before | After |
| --- | --- | --- |
| Light | [view](local-gtk/edition-21-white-introduction-before.png) | [view](local-gtk/edition-21-white-introduction.png) |
| Dark | [view](local-gtk/edition-21-dark-introduction-before.png) | [view](local-gtk/edition-21-dark-introduction.png) |

## Material limits

- The exact Segond and Ostervald publisher indexes are preserved separately. Automatic cross-edition verse alignment and annotation display across other reference systems remain unavailable for these two indexes; independent parallel reading stays available. No false equivalence is inferred from the common metadata label `org`.
- The current legacy metadata/offline endpoints are observed working, not an official supported third-party API contract. Reachability does not establish provider permission. Actual conditions, email-agreement requirement and attribution are retained; acknowledgement is local and no provider agreement is submitted or asserted.
- Source text, notes and provenance remain on the installing user's machine. No translation is bundled with the application.
- Linux/Flatpak and developer Xvfb checks do not prove behavior on the client's GNOME/Wayland hardware, Windows or macOS. Later separately assigned comparison and visual feedback issues are not represented as completed by this delivery.

## Signed delivery and retained-profile update

[Main CI 40454566453](https://github.com/icfmp/Bible/actions/runs/40454566453), [signed publication 40456634652](https://github.com/icfmp/Bible/actions/runs/40456634652) and [old-alpha upgrade 40454817687](https://github.com/icfmp/Bible/actions/runs/40454817687) pass. [Delivery receipt](delivery.json) records exact source, bundle, OSTree commit and stable signing identity. Independent verification matches 378 project files and all three dependency sources; all 40 historical source records remain unchanged (41 now). Numbered releases are unchanged.

The retained real-resource profile updates from source `67d741f` / OSTree `49e1338d…` to `d39a99e` / OSTree `47d14bcb…`, retaining remote `bible-alpha`, the alpha ref and fingerprint `47A17230403EA4953745E6E020EB9FFCCECAFD8F`. Its personal note, reading preferences, 37 module files and all four installed study databases remain unchanged. Combined reading runs four scrollbar cycles before and after; updated single/parallel/study cases run two wheel cycles each. Every case records zero adjustment changes more than 500 ms after input stops. See [bounded reading measurements](signed-reading-summary.json); virtual software-rendering figures are not client-device performance claims. An initial public pull returned HTTP 503; a bounded retry completed the genuine signed installation without weakening verification.

Update: `flatpak update --user io.github.icfmp.Bible//alpha`. Fresh installation: [signed Flatpak reference](https://icfmp.github.io/Bible/alpha/Bible.flatpakref).

Client checks:
1. In Library, find Semeur 2015, review source conditions and install it; the final verification phase must complete before it is installed.
2. Reopen without networking, read several books, open the supplied introduction and Translation notes, and check existing personal notes remain separate.
3. Try one French and one English edition, plus parallel reading. Segond/Ostervald explicitly retain independent reading where cross-edition alignment is unverified.

Issue #26 remains OPEN. Project 5 still returns `Resource not accessible by integration`; under the paused numbered-publication workflow the manual status remains **In review**, not Done. Numbered release #87 stays paused.
