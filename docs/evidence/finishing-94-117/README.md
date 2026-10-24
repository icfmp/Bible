# Desktop finishing batch: developer evidence

Related to #94, #98, #99, #101, #102, #105, #109, #110, #116 and #117.
All ten current descriptions and their complete comment lists were read; there
were no comments at the time of inspection on 24 October 2026. Implementation
issues remain open for client acceptance. Numbered publication #87 is paused.

## Reading and immersion

The #99 correction precedes #98 in history (`fa33525`, then `1e8172e`). On real
FreSegond1910 Acts 1 near verse 14, instrumentation found an artificial short
preceding page: whole-book preparation split pagination at the requested entry
anchor, independently paginating the prefix. One ordinary prefix page contained
only 100 characters. Whole-book pagination now starts at its natural beginning;
the requested canonical/intra-verse anchor remains separate and selects the
containing page. Paragraphs/headings and genuine final/book-boundary blanks remain.
Existing exact-partition, source-fidelity, sparse/long-verse, reflow and cancellation
checks exercise the original paginator; animation does not replace that algorithm.

The reported repeated vertical jump was **not reproduced** in the baseline idle
recording. It is not presented as a confirmed allocation-loop diagnosis. The new
control audit nevertheless removes the moving reveal sensor and slide-down
header, uses fixed overlay sensors and 200 ms crossfades for header and arrows,
retains keyboard/menu holds, and keeps equal top/bottom page margins. Actual arrow
rectangles retain hover in wide windows; pointer focus cannot pin the controls
indefinitely. Hidden controls do not retain hit boxes, and reader focus returns
to a selected page when pointer-focused controls fade. The hidden header reveals
at the top edge while its visible hover area uses stable child allocation.
The 25-second recording holds one page cursor and geometry throughout: hidden
at 0.7 s, revealed at 17.1 s, hidden again at 21.7 s after focus returns to reading.
Saved highlight/study decoration is suppressed only in immersion; storage and the
ordinary-reader visibility preference are unchanged. Native selection/copy remains.

Page turns use a single bounded immutable snapshot of the currently visible
spread and a native 200 ms GtkStack slide. Direction respects RTL. A new turn
cancels the previous visual transition, while each valid ready stream turn still
advances once. Reflow, source/reference/tab changes and exit cancel stale callbacks.
Disabled animations change pages immediately. Real recordings cover one/two pages,
chapter and Acts → Romans boundaries, and the public-domain Hebrew HebNTFD module.

The version and comparison popovers share one direct native list implementation;
None remains the comparison stop action. One reading tab hides the entire tab strip;
New Tab remains in the header, including narrow layouts. Existing allocation-anchor
restoration handles its changing height. The instructional TextView tooltip was
removed at its source; click/Alt+Up/Alt+Down and localized shortcut help remain.

## Appearance and selection actions

Window-scoped palette rules cover native chrome, tab strip, menus, comparison,
Notes and study surfaces. Paper uses a darker warm study surface; Black uses true
black reading and near-black chrome. White/Dark Grey retain their identities.
Native semantic accents, highlight tags, images and focus indicators are retained.
High contrast takes precedence.

Aa System uses General System/Light/Dark as its base. Explicit Aa Light/Dark wins
for the window's reading palette. The active tab owns the mode/day/night triplet;
optional, validated `reading_palette` session data preserves inactive tabs and
old version-1 sessions remain readable. Shared font/spacing/visibility settings
keep their existing behavior; no preference is reset or new user control added.

The selection bar uses a clipped GSK blur over the actual underlying reader and a
separate native dark translucent foreground box. Its white text/icons remain
outside the blur. Input and output bounds are limited to the small bar plus kernel
padding; no whole-book offscreen texture or new rendering dependency is added.
A diagnostic compares the same native surface at internal blur radii 0 and 8;
full unedited screenshots and measured pixel differences establish real blur on
GTK 4.14.5/Cairo. This is a diagnostic override, not a user setting. Repeated native
redraw tests check that the panel stays dark and its white controls stay rendered.
High contrast uses an opaque background. Headless tests do not establish performance
or portal behavior on the client's own compositor.

## Backups and startup

The annotation data integration has its own review PR, #121; see
[the snapshot review](backup-review.md). Complete notes/labels/ranges/source context
and highlights round-trip without requiring their original Bible packages.
Restore validates the whole versioned payload, states merge semantics, keeps
existing highlight conflicts, copies differing colliding notes, and verifies a
pre-restore safety backup. A durable recovery record spans the two stores; pending
recovery blocks further public annotation edits/exports. SQLite schema, resources,
credentials and general preferences are not included or migrated. Exports are
explicitly unencrypted. Legacy note/highlight formats remain supported.

Actual native GTK file selection, export, visible success, confirmation and restore
were exercised in a disposable real-resource profile. The captured local test uses
the native GTK fallback (`GTK_USE_PORTAL=0`); it does not claim a GNOME desktop
portal test. Headless installed tests construct the real chooser type and isolate
its response boundary rather than synthesizing IPC replies to an outstanding portal
request. Storage/failure/recovery tests run against the installed application too.

Each startup validates actual local Bible metadata, indexed availability and readable
text before selecting the existing welcome state. Previously seen/skipped welcome,
commentary-only profiles, missing last Bible and retained annotations do not suppress
it. Later opens Notes; returning without a reader returns to welcome. Read errors
preserve files and are distinguished in the description. Background installs retain
explicit Read/Open and never replace the chosen workspace.

## Library

Successful provider/cache coverage is tracked separately from unknown retrieval;
failed retrieval does not replace useful previous rows with an empty list. Initial
unknown results use native non-interactive skeletons and indeterminate progress;
usable rows remain during refresh. Completed covered zero results use a centered
native status page, current filters and clear/retry actions. Errors/incomplete
coverage remain distinct. Closure/completion stops animation; disabled animations
keep static skeletons. Source/query text and errors are escaped for native markup.

A **real network** run fetched 1,941 metadata entries from the five configured
providers with no errors. An explicitly recorded 1.5-second diagnostic delay makes
the initial state observable; actual provider callbacks produce the rows and coverage.
This does not download Bible texts. Empty/error screenshots use controlled snapshots
and are identified as fixtures, not fabricated network outcomes. Local installed
resources in those screenshots are actual modules. Filter/query, partial/all failure,
offline cache, close/reopen and bounded-model regressions remain covered.

## Validation and limits

[The capture gallery](../../captures/finishing-94-117/README.md) contains actual native
before/after light/dark views, small windows, high contrast, scaling and recordings.
Captures use GTK/Xvfb on Linux, disposable profiles and actual attributed SWORD
resources. They are not mockups or client desktop acceptance. Source, French UI,
installed Flatpak, CI and signed-public-update receipts are recorded after delivery.
