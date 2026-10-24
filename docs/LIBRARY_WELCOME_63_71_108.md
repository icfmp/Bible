# Library, first launch and global menu (#63/#71/#108)

This delivery combines the approved Library hierarchy with first-use guidance
and replacement Library entry points. It retains #78's worker-based metadata
service, bounded native models, guarded SWORD installation and stable resource
identities. It does not implement #96/#106 annotation redesigns or #75 workspaces.

## Library

Bibles and Commentaries are the only primary type tabs. A single virtualized
native list combines installed and downloadable resources, with search, Language
and Source filters. There is no Explore/Installed top split, category rail or
status filter. Installed resources remain available even if the provider cache
is incomplete or the network fails; source attribution stays visible per row
and full details/notices remain accessible by activating the row.

The language initially follows the effective French/English application UI;
unsupported/system `C` locales fall back to English. An explicit choice, including
All languages, persists in the separate atomic application settings across type
changes, refresh, dialog reopen and restart. Validated aliases such as fr/fra/fre
match; script/region distinctions remain separate. Full local ISO choices are
prepared by the existing metadata worker when the language picker is opened or
searched, so an empty/cold provider cache cannot hide languages. Empty selected
languages explain the result and never silently broaden the filter.

A row's Download button starts the existing guarded installation directly,
without activating details. Locked/unsupported resources stay blocked. The task
captures the actual resource; progress, validation, failure/retry and Installed
state do not move to a different selected row. Download cancellation is available
before finalization. Completion is reported only after package/SWORD validation.
The existing source identity, notice-change, HTTPS, archive/path/size and atomic
installation guards remain in force. Download availability does not grant
redistribution rights; original source conditions remain available offline.

Installation refreshes resource choices across the relevant windows, without
changing the selected Bible, comparison, commentary, passage or history. The
resource-specific Read/Open action is explicit. Contextual access captures the
intended tab weakly; closing or changing tabs cannot silently retarget completion.
Notes retains its save/discard/cancel guard before an explicit reading transition.
The existing study-data Library entry is retained as an internal contextual view.

## Metadata refresh: network versus local work

All five configured SWORD providers expose a global `mods.d.tar.gz` archive. No
unverified language/type endpoint or invented query parameter is introduced.
Language/type/search changes filter the existing metadata locally and do not
fetch text packages. A selected Source scopes the providers in the next refresh;
already-running requests can finish, but their snapshots are filtered using the
current UI choices. Results from other providers remain cached and installed
resources are not discarded on partial failure. Concurrency remains bounded at
four metadata requests.

The existing fifteen-minute freshness cache is reused. Ordinary warm opening can
skip the network. Explicit Refresh means checking the selected providers again,
using ETag/Last-Modified validators when available; a valid HTTPS 304 refreshes
freshness without downloading/parsing a new archive body. A server without
validators still sends its global archive. These are metadata changes, never an
automatic request for Bible/commentary text.

Measured in the disposable Linux/Xvfb environment (not universal guarantees):

| Observation | Result |
| --- | --- |
| Cold global metadata | 1,941 supported entries, 5 requests, 1,044,733 response-body bytes, 2.03 s total |
| First provider usable during metadata fetch | 0.63 s |
| Warm fresh metadata | 0 requests, 0 response-body bytes |
| Explicit selected eBible revalidation | 1 request, HTTP 304, 0 body bytes, 0.35 s; other providers not requested |
| Native cold French Library, no installed resources | first populated frame 1.95 s; complete refresh/list 2.09 s; 21 filtered Bibles |
| Native warm French Library, no installed resources | first populated frame 0.47 s; complete list 0.59 s |
| Actual restored-profile Library | first painted frame 0.20 s; maximum heartbeat gap 0.28 s |

Bytes exclude HTTP/TLS overhead. The original unconditional global archive sizes
were also measured from before source. The French default reduces the displayed
list, not the first network archive size. Timing JSON retains each provider's
request/body bytes and network/parse duration. Input-driven reopen totals include
automation delays and must not be presented as constructor-only benchmarks.

## First launch and entry points

A genuinely empty new profile receives a calm native main-window welcome with
the existing blue Bible icon, Choose my Bible, Later and an offline-supporting
line. It opens the same Library, prefiltered to Bibles; it does not auto-download
text. An explicit Read action leads into reading after a successful installation.

First-use detection runs before SQLite/session/settings files are created and
conservatively recognizes existing user data/resources. Missing new preference
keys alone never turn an existing profile into a new user. The marker is written
atomically; skip, restart, app update or removal of the last resource does not
replay onboarding. The ordinary empty reader retains Download a Bible and honest
unavailable/error guidance. Existing session and readable resources take priority.

Download more is available from primary/comparison version controls and the
commentary chooser, retaining its intended target. The main menu opens Library
from reading, welcome, Notes and immersion. No permanent Header Bar Library icon
remains. Closing Library returns to the previous workspace/draft without navigation.

## Global menu and responsive controls

The shared native menu has exactly Library, Preferences, Keyboard Shortcuts and
About Bible, in that order, with monochrome symbolic icons and one separator
before About. Library retains Ctrl+L; Preferences implements Ctrl+,; shortcut help
implements Ctrl+? and lists accelerators obtained from the actual application.
Preferences edits real Library language and automatic metadata-refresh settings;
Aa retains reading appearance. About identifies continuous alpha, GPL-2.0-only,
contributors and project/third-party links.

Removed contextual menu entries do not remove their actions or shortcuts. Notes
and Study keep Header Bar pointer access at narrow widths. New Tab has one
visible control: Header Bar normally, native tab-bar end action when narrow.
Highlights overview/backup/restore remains reachable from annotation tools and
the local Notes actions, preserving the existing window rather than introducing
a new annotation workspace. Narrow/150% layout constrains menu width and allows
labels to wrap. Notes' sidebar uses pixel bounds so large system fonts do not
force its minimum beyond the actual narrow window. Full clipped captions remain
available through accessible names, tooltips or their chooser.

## Validation and delivery

[Evidence gallery](evidence/library-63-71-108/README.md): 81 actual PNGs, including
32 before/after pairs, French/English, light/dark, narrow/normal, 150% system
fonts and test-only high contrast. These are native automated Xvfb captures,
not manual client GNOME acceptance. Specialist accessibility remains deferred.

Local full suite: 260 tests passed; focused final-layout/Library checks cover
later responsive adjustments. CI repeats the full source suite, French UI suite
and installed Flatpak tests. The installed test command asserts application
imports come from `/app/`, not the host checkout. Unit/HTTPS fixtures use labelled
synthetic data; actual eBible transfer and exact local SWORD reading were checked
separately with real X11 pointer/keyboard input. Network-disabled English checks
cover fresh use/failure, skip/restart, installed browsing, Notes menu and dialogs.

A real pre-change test profile preserved its SQLite note/labels, highlight,
explicit reading preferences, primary/comparison session and all 36 installed
resource file digests. No personal client profile was accessed. No annotation,
Bible text or installed-resource identity migration is introduced.

After green review/CI, deliver one application batch through the existing signed
alpha and verify actual public installation/update and data preservation. The
storage policy introduced by #112 remains in effect. **Numbered release #87
remains paused**; no numbered prerelease is part of this batch.

Ordinary update command after verified publication:

```sh
flatpak update io.github.icfmp.Bible//alpha
```
