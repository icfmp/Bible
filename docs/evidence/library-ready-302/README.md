# Library delivery evidence

Related to #307, #303, #302, #306, #296 and #276. These issues remain open
for client acceptance. This directory records developer validation, not a claim
that the branch has already been merged or published.

## Native application checks

Linux x86_64, GTK 4.20.4/libadwaita in the installed GNOME 49 Flatpak runtime,
X11/compositor and software OpenGL. The `baseline` screenshot uses the actual
installed alpha 34 Python application. `after`, queue and progress captures use
the development application with the same runtime. They are unedited screen
captures, not mockups. They do not prove client Wayland/GPU or assistive-tool
acceptance. Each profile was a disposable copy; original retained profiles were
not reset. All 34 pre-existing module files stayed byte-identical during the
gallery and real queue checks.

| Ticket | Focused checks and evidence |
| --- | --- |
| #307 | Real removed BRMHCC 0.1.0 journal → current provider MHCC 0.1.1 catalogue; HTTP 200 package, reopen and unchanged journals. Historical removed identity does not return. Offline archival, incomplete YouVersion language catalogues and recovered retired requests have dedicated regressions. See `real307.json`. |
| #303 | Real YouVersion KJV download/conversion/readback. A controlled 12-second source-I/O delay makes the old ambiguous transferred-100% interval 12.204 s; the revised Preparing stage is already displayed at EOF. This proves phase visibility, not a 12-second conversion speedup. Native heartbeat max 0.188 s, p99 0.027 s in that controlled run. Real WEB remains rejected for unreviewed semantic classes; the guard was not weakened. All nine resulting KJV module files match except the receipt's install timestamp. See `preservation303.json` and the Preparing capture. |
| #302 | Actual mouse clicks queue genuine CrossWire KJV 3.1 and FreJND 3.3, then the checked existing OpenBible cross-reference archive. The first transfer waits at an explicit diagnostic barrier until the subsequent requests are visible; real provider bytes/installers and source checks are unchanged. Serial completion continues with Library hidden; installed modules and real reference queries succeed. Native heartbeat max 0.118 s in this run. See `302-live-queue.json` and the three `302-live` captures. Native regressions separately cover mixed backends, deduplication, cancellation, failure → next valid install → explicit retry, two main windows, last-window close/restart/manual Resume, corrupt journals and source revision changes. |
| #306 | Native Bibles/Commentaries/Study tools tests check installed-first titles, accents/case, distinct providers and filtering. A 200-row Bible/commentary list retains the same GObjects, visible item/pixel offset, selection and actual keyboard focus when an off-screen installation moves into the installed group. An unchanged refresh emits no model changes. The installed-results capture also shows the real reordered list. |
| #296 | Actual large FR inventory and short EN installed-language subset, with native divider, locale-first shortcuts and capitalization. No ISO-only language becomes a shortcut without known resource/provider availability. Coptic search, variants, lazy bounded model updates, stale searches and retained selections have focused checks. See both `languages` captures. |
| #276 | Actual installed BRLSG1910 0.1.0 before/after, MHCC 0.1.0 dark, Easton 2.0.1 at 360×600 with large UI text and high contrast. Description is near the actions; the complete mixed About field, including Mark 10:52 and Job 34:37 limitations, remains visible. License, source links and technical disclosure are separate. Only the application's exact structured TextSource line moves to its link row; all original metadata remains in the model/disclosure. See Segond top/bottom, MHCC and Easton captures. Existing native tests also check absent descriptions, uninstalled controls and study resources without invented versions/actions. |

## Scope and publication

Only `icfmp/Bible` changes. No resource text, dataset, provider, Bible-Resources
repository or distribution pipeline is created or modified. The queue stores
requests and source acknowledgements, not credentials or source content.
Recovered pending work is paused until an explicit Resume; failed requests need
an explicit retry. A corrupt journal is preserved and blocks queue mutation.

The publication report must separately record PR, final merged source, required
CI, signed alpha, matching numbered prerelease and actual installed update.
Source-branch screenshots are not represented as packaged-after-update tests.
Project 5 status access remains forbidden (`Resource not accessible by
integration`); report the manual status without retrying that permission.
