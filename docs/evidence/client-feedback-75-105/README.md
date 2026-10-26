# Client feedback batch — signed alpha verified

Related to #75, #94, #99, #98, #102 and #105. All remain OPEN for client acceptance. Numbered publication #87 remains paused; no numbered release was created.

**Delivered source:** `758fb1600b00027b47ac0f4998f34bed6806d8e5` · [merged PR #132](https://github.com/icfmp/Bible/pull/132) · [green main CI](https://github.com/icfmp/Bible/actions/runs/40265503566) · [successful signed publication](https://github.com/icfmp/Bible/actions/runs/40267227219) · **alpha `40267227219-2`**.

[Delivery receipt](delivery.json) · [independent source/channel verification](delivered/source-channel-verification.json) · [build identity](delivered/build-info.json). The source archive matches all 335 corresponding project files and all three original dependency archives. All 38 historical source records are unchanged; there are now 39. Signed-channel ref, remote and GPG fingerprint are preserved. Numbered release records are unchanged.

Update: `flatpak update --user io.github.icfmp.Bible//alpha`. [Signed installation link](https://icfmp.github.io/Bible/alpha/Bible.flatpakref).

## Checks and update preservation

Main CI passes **322 source tests, 143 French checks and 141 installed Flatpak tests**, native input/workspace checks and actual-resource/offline checks. The installed `/app/` implementation on GNOME Platform 49, GTK 4.20.4, OpenGL, composited Xvfb and scale 1 passes 99 captures, all 16 page turns (including rapid reversals), and stable 15-second immersion. [UI report](delivered/ui-report.json). This is developer validation, not client GNOME/Wayland or fractional-scaling acceptance.

[Public install report](delivered/public-install-check.json) · [public update report](delivered/public-update-check.json). The workflow actually installs signed packaging revision 1 from HTTPS, starts Bible, and updates to revision 2 of the same application source. Commit/summary signature checking remains enabled; note/preferences/resource sentinel hashes in the disposable profile remain unchanged. Separate source/installed tests verify actual annotation/resource persistence and offline behavior. No client profile was accessed. No data schema or preference-key change was made.

## Actual installed blur correction

[Before: installed intermediate candidate with the broken clip](installed-before-blur.png) · [after: delivered installed build](delivered/blur-diagnostic-16.png) · [delivered zero-radius diagnostic](delivered/blur-diagnostic-0.png).

The old clip referenced freed temporary `Gsk.RoundedRect` storage. Retaining its owner until GTK copies the clip restores blur of the real reader. The effect uses native GSK blur 16, a 48-pixel sampling margin and a rounded final clip; controls stay sharp above a restrained dark tint. Blur edge energy falls from 62007 to 18056, changing 13695 pixels. Cairo is explicitly selected for headless test coverage only; the application leaves renderer selection to GTK. There is no custom CPU blur, rendering worker, custom texture cache or new production dependency.

## Visible popups, palettes and small windows

[Light selection](delivered/white-selection.png) · [dark selection](delivered/dark-selection.png) · [light Copy menu](delivered/white-copy-menu.png) · [dark Copy menu](delivered/dark-copy-menu.png) · [White study](delivered/white-study-notes.png) · [Dark study](delivered/dark-study-notes.png) · [Paper study](delivered/paper-study-notes.png) · [Black study](delivered/black-study-notes.png) · [French backups, narrow/large type](delivered/preferences-white-small-large-type-bottom.png) · [dark preferences](delivered/preferences-dark-wide-top.png) · [narrow immersion](delivered/immersion-narrow.png) · [narrow study](delivered/study-narrow.png).

[Full before/after index, diagnosis and actual recordings](../../captures/client-feedback-75-105/README.md). Historical source/candidate measurements there are labeled; the delivered installed measurements below supersede them for this publication.

## Native cache and the first wheel event

GTK's current immutable paintable image and cached background GSK node are reused while content, geometry and appearance stay unchanged. Native invalidation requests drawing/settling placement only when needed. The former periodic selection timer and continuous placement polling were removed. Hiding disconnects/releases the paintable and cancels pending placement before ordinary scroll handling continues.

[Delivered cache/scroll diagnostic](delivered/live-report.json) records **zero backdrop snapshots, invalidation callbacks, placement callbacks and periodic checks** over six seconds with a stationary visible bar, and after dismissal. This measures associated application work, not zero total GTK/GPU activity.

[Initially hidden native wheel baseline](delivered/scroll-hidden.json) · [initially visible bar](delivered/scroll-toolbar.json). Independent real X11 wheel input hides/releases the bar in **0.249 ms**, produces the first reader adjustment after **0.825 ms**, and reaches GTK's first after-paint after **19.109 ms**, with the bar already absent. Cleanup completes before motion. Sustained input and direction reversals pass; there are zero adjustment changes more than 500 ms after input stops. The baseline first movement is 1.214 ms and first paint 18.588 ms; frame phase varies, so these are observations rather than a speedup claim.

| Six-second software OpenGL diagnostic | p95 frame gap | CPU seconds / ~6.1 wall seconds | Associated callbacks |
| --- | ---: | ---: | --- |
| Scroll without bar | 17.18 ms | 1.99 s | 0 |
| Content changes behind visible bar via scrollbar adjustment | 17.35 ms | 10.65 s | native invalidation/rendering |
| Visible bar, unchanged background | 17.48 ms | 0.16 s | 0 |
| Scroll after dismissal | 17.22 ms | 1.98 s | 0 |

Changing content behind a deliberately visible blurred bar costs more software-renderer CPU across threads. Real wheel input removes that effect before scrolling. The diagnostic uses scrollbar adjustment without overriding the normal wheel lifecycle; it does not predict client GPU timings.

## Acceptance and authorization history

The client explicitly authorized PR #132 merge and signed-alpha publication on 26 October 2026. [The historical pre-approval receipt](review-ready.json) preserves the earlier automatic-review rejection; that blocker is resolved and its no-publication state is historical, not current.

Project access was rechecked and still returns `Resource not accessible by integration`. Manual status remains **In review** because numbered publication #87 is paused under the existing workflow; only the client accepts/closes issues. No automatic closing references were present on merge.
