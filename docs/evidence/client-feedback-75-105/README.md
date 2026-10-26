# Client feedback batch — verified candidate awaiting merge authorization

Related to #75, #94, #99, #98, #102 and #105. All remain OPEN. Numbered publication #87 stays paused.

**Source:** `bce5a17549d0dcafd5a91ab08088fd5c8e73f862` · [PR #132](https://github.com/icfmp/Bible/pull/132) · [green CI 40246836190](https://github.com/icfmp/Bible/actions/runs/40246836190).

The candidate passes 322 source tests, 143 French checks, 141 installed Flatpak tests, native input/workspace checks and real-resource/offline checks. These PNGs and reports are from the actual installed `/app/` code on GNOME Platform 49, GTK 4.20.4, OpenGL and composited Xvfb. They do not establish acceptance on the client's GNOME/Wayland desktop or fractional scaling.

## Actual installed blur correction

| Before (intermediate candidate `aceda275b7790a229bb01d21d1247dd2c73236ab`) | After (verified candidate `bce5a17549d0dcafd5a91ab08088fd5c8e73f862`) |
| --- | --- |
| [Installed before](installed-before-blur.png) | [Installed after](installed-after-blur.png) |

The old clip contained freed `Gsk.RoundedRect` storage and invalid coordinates. Keeping its owner alive until GTK copies the clip restores the bounded native GSK blur. The native current paintable image and background render node are reused until content/size/appearance invalidation. There is no application renderer switch, CPU blur, rendering worker or custom texture cache. Cairo is explicitly selected for headless GTK/GSK test coverage only.

The installed run records 99 captures, 16 successful page turns (including rapid reversals), stable 15-second immersion, and blur edge energy 62007 → 18056. [UI report](installed-ui-report.json).

## Open popups, study surfaces and small windows

[Light Copy menu](installed-white-copy-menu.png) · [Dark Copy menu](installed-dark-copy-menu.png) · [Light study](installed-white-study-notes.png) · [Dark study](installed-dark-study-notes.png) · [Paper study](installed-paper-study-notes.png) · [Black study](installed-black-study-notes.png) · [French backups, narrow with large type](installed-preferences-white-small-large-type-bottom.png) · [Dark preferences](installed-preferences-dark-wide-top.png) · [Narrow immersion](installed-immersion-narrow.png) · [Narrow study](installed-study-narrow.png).

[The full before/after index and actual live recordings](../../captures/client-feedback-75-105/README.md) include Bible/Notes, preferences, source/menu/context/action popups, immersion and the diagnosed clip defect.

## Cache and actual first wheel event

[Installed live/cache report](installed-live-report.json) records zero backdrop snapshots, invalidation callbacks, placement callbacks and periodic checks during six seconds with a stationary visible bar, and after dismissal. GTK's native cache/invalidation drives updates; the old continuous placement polling and selection timer were removed.

[Initially hidden baseline](installed-scroll-hidden.json) · [Initially visible bar](installed-scroll-toolbar.json). Real independent X11 wheel input hides and releases the bar in **0.23 ms**, changes reader position after **0.80 ms**, and reaches the first GTK after-paint after **16.97 ms** with the bar already absent. Cleanup finishes before motion. Direction changes remain reactive; there are zero adjustment changes more than 500 ms after input stops. The source/installed sustained checks also cover single, comparison and study modes.

The matched software OpenGL scrollbar-adjustment diagnostic has p95 frame gaps of 17.37 ms without the bar and 17.41 ms with changing content behind the visible bar. CPU time across software-renderer threads rises from 1.88 to 9.14 seconds per 6.1 wall seconds in that changing-content case; blur has a measurable rendering cost. It is reused at rest, and the real wheel gesture removes it before scrolling. This diagnostic does not claim wheel input leaves the bar visible or predict client GPU timings.

## Exact publication state

[Review receipt](review-ready.json) · [build identity](build-info.json) · [unchanged current public alpha](current-public-alpha.json).

The CI artifact is a tested candidate (`master` ref), not a newly published signed-alpha update. The automatic authorization review rejected merging PR #132 because the client's explicit merge authorization covered PR #131. No merge or signed-alpha publication was performed; public source remains `7a633f3281d0a6086cb822a1ac9f055beb53445b`, packaging `40221899923-2`. Public install/update preservation checks for this new source must follow explicit merge authorization and successful signed deployment. Implementation data/persistence tests pass, but no new public update is claimed here.

The GitHub merge state is CLEAN and there are no automatic issue-closing references. Manual project status is **In review**; project access is refused (`Resource not accessible by integration`). Only the client accepts/closes the implementation issues. Numbered publication #87 remains paused.
