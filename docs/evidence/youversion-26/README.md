# Issue 26: Bible.com offline acquisition and fidelity

Source under final validation: `916b35a627fb80848107bc3a5701313c903e9883`, reviewed in [PR 134](https://github.com/icfmp/Bible/pull/134). Signed-alpha delivery is still pending; this page does not claim publication. Numbered release #87 remains paused, and issue #26 stays open for client acceptance.

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

The local native GTK suite passed 358 tests, followed by 62 affected French tests. After the introduction-only spacing correction, 31 affected tests passed. Exact final-source ordinary CI [40427232547](https://github.com/icfmp/Bible/actions/runs/40427232547) and installed Flatpak proof [40427232536](https://github.com/icfmp/Bible/actions/runs/40427232536) are still required. Earlier source `34a64d7` passed its source job (358 tests, two native-scheme tests skipped in the unpatched system environment; 144 French tests); its remaining workflow was cancelled when the real introduction presentation problem was found. Skipped system tests are not counted as native reference-system validation; patched local and packaged checks exercise those systems.

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
