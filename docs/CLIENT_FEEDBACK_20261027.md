# Reading feedback — 27 October 2026

Work follows the delivered signed issue-26 source `d39a99e`. Assigned issues remain open; numbered release #87 is paused. This document records implementation checks, not client acceptance or a published batch.

## #97 / #107: native manual scrolling and actual verse alignment

Manual wheel/touchpad, scrollbar and ordinary keyboard scrolling already use GTK's own adjustment/input handling. `ScrollMotion` has capture-phase cancellation handlers returning false, and only its explicit `move()` calls animate programmatic reveal/following. Callers are `ReadingTab.reveal_reference`, `StudyPanel.reveal` and `PassageNotes.follow`; shared comparison returns early from independent following and uses one adjustment. No application-added interpolation of ordinary manual scrolling was found. No redundant removal or global animation change is made. Native touchpad hardware is unavailable in the development environment; immersion's separate page gestures/slides are retained.

The comparison bug is measurable with actual Semeur/KJV John 1: row-start alignment reports zero while the real verse-body first lines differ by up to **431 px**, because source headings belong to the same source block. The correction aligns actual body positions using native paragraph padding, retaining every heading/word and all copy offsets. At fixed geometry, native positions are read once before tags change; cumulative padding aligns subsequent correspondence groups, and final bottom padding preserves equal document extents. Geometry/content invalidation restarts the bounded settling path; no permanent tick or per-scroll full-document alignment pass is introduced.

Local GTK 4.14.5/OpenGL, 1280 × 850, 24-point source reading: all actual John 1 body starts align to **0 px** in light/dark after correction. Row starts that contain different editorial headings are intentionally not used as a proxy for verse alignment. Native source-heading/wrapping/resize/large-type and text-copy checks accompany this change. Installed Flatpak, motion recordings and final batch publication remain required.

## #99: native pagination metrics and shared visible reading area

Actual GTK 4.20.4/OpenGL, FreBDM1707 Genesis 6 at 1600 × 900 and 24-point DejaVu Serif/very airy spacing exposed two independent problems. The worker used different glyph rounding/font options: one source fragment measured 13 lines / 686 px privately but 14 lines / 729.5 px in the native context. Copying rounding alone fixed line breaks but left a 10.5 px height error. Copying the native font options as well exactly matches native Pango. The worker owns an independent options copy and private font map; no GTK widget crosses threads and no rendering dependency is added. The existing PangoCairo API measures fonts; GTK/GSK still renders the application.

The shared reading area now uses a full-line grid derived from actual metrics, excluding unused fractional capacity and trailing-newline safety. Both columns keep one baseline. On normal real filled pages, measured clearances become about 112 px top/bottom. A short chapter ending remains short. A rare paragraph sliced before final Greek punctuation can acquire an additional native line; the two displayed buffers are measured once after stable allocation so that genuinely larger glyph bounds expand the common safe area rather than clipping. This does not shrink/center short final columns, repaginate on controls fading, or add periodic geometry queries.

A canonical chapter prefix can include only separators on the previous spread. Page lookup now chooses the following visible heading/body while retaining exact Document.locate, copy and selection offsets. The source partition remains complete and contiguous.

All 22 affected immersion/pagination/client-feedback tests pass with patched source GTK 4.14.5 and with the available GTK 4.20.4 runtime. They include worker/native partition equivalence at 14/24/48 points, exact clipping/continuity/reflow/selection/anchor checks and unchanged controls-fade geometry. The GTK 4.20 run uses an isolated outer display and the existing isolated-click mode; these remain source-environment checks, not installed Flatpak acceptance. The separate moving focus-edge correction is implemented only after this pagination increment.

## #98: stationary accessible keyboard focus during native slides

The actual 60 fps recording reproduces the reported 804 px vertical blue edge moving across the page. It is the existing `:focus-visible text` inset shadow included in the moving page/snapshot, rather than a text-selection or blur effect. A diagnostic-only focus-style ablation removes it; that diagnostic is not shipped.

Only immersive pages now paint this focus cue on a stationary, noninteractive viewport overlay. Normal reader focus styles, genuine text selection, keyboard routing and the native 200 ms slides remain. Focus/modality changes update the cue through native signals; window handlers disconnect on leaving immersion, without polling or extra animation work.

Source GTK 4.20.4/OpenGL recordings: before, 193 of 235 frames contain an interior vertical blue run (maximum 804 px); after, zero of 237 frames do. A visible keyboard cue remains fixed at x=0. The dark 720 × 900 one-column recording also has zero interior runs across 235 frames. All six deliberate Right/Left inputs turn once in each recording. The 23 affected tests pass, covering focus versus controls/pointer modality, source fidelity, selection, reflow, anchors and existing navigation. Actual installed-package motion and final delivery are still pending.

## #106 / #104: coordinated verse-end metadata

Both actions now occupy compact native child-anchor slots after the verse's final punctuation and before its trailing paragraph separators. The note icon and an original outlined place pin share the exact active verse-number colour token, including high contrast. Independent visibility toggles remove slots entirely. Copy and canonical anchors delegate to the original source document, so UI objects never count as Scripture characters or move source offsets.

The reported silent click was not reproduced in the initial simple native pointer case: Notes opened on the first click with Study closed or showing References. Investigation did reproduce a separate native crash when rebuilding the hovered note anchor while enabling comparison. GDB identifies GTK 4.20 selection invalidation reentering a partly deleted text tree during automatic child unmapping. Explicitly removing old child widgets before deleting text avoids that unsafe sequence; no toolkit setting or feature is disabled.

Seventeen affected source-runtime tests pass, including actual pointer activation across repeated simple/comparison changes, Study initially closed or showing another tab, two notes without arbitrary editing, rebuilding under the pointer, independent visibility, mapped targets, clean copy, canonical round trips, comparison alignment, action selection and scroll persistence. Existing draft checks remain. Actual installed-package/palette captures and the map-detail follow-up are still pending.

## #104: native contextual map and a real transient place window

The detail is now an `Adw.Window` transient/modal to the actual Bible window,
with a labelled studied passage and the owning reading palette. The Bible is
not replaced with an opaque dialog host. Closing or closing its owner ends
the map/provider lifetime. Internal module IDs, coordinate/score dumps and the
technical expander are removed from the reader flow; stored evidence is kept.
Excerpts are regular-weight, with two initial related references and the
existing deliberate View all expansion.

The maintained raster-only libshumate 1.5.5 dependency is pinned to its official
GNOME archive (SHA-256 `ce27d88537a37cd5c45959c3bb7cc18c1c18b3d2e663d02bcf46fc66f7414a92`),
with LGPL-2.1-or-later COPYING and corresponding source. Its native downloader,
cache, renderer, pan and zoom are reused. Three tiny dependency corrections
make its existing public User-Agent setter effective, propagate native image
decode failures, and preserve load-completion notification when optional
Sysprof support is disabled. These were found through actual HTTP/GTK checks;
there is no replacement tile client, custom image loader or sandbox bypass.
See THIRD_PARTY_NOTICES.md and the three source patches.

The standard HTTPS OSM service is requested only on intentionally opening the
visible detail. Native caching keeps a seven-day freshness period, conditional
ETag/Last-Modified validation and a 100 MB limit. No map prefetch, bulk download
or offline-package feature is added. The stable app-identifying User-Agent and
visible linked OpenStreetMap attribution are verified; OpenBible/CC BY and
OSM-derived ODbL credits remain short visible links. Natural Earth's public
domain notice is removed from the active footer; its installed data is retained.

Actual source GTK 4.14.5/OpenGL shows regional labelled OSM maps for Shinar and
Charan in light/dark, supplied candidate points, real Bible references and the
reading window behind the detail. A second reproduced bug affected multi-place
popups attached directly to scrolled text child anchors; the chooser now uses
the stable reading overlay, explicit current bounds and a usable bounded width.
Nine source tests pass, including native single/multi-place pointer input,
scrolled chooser targets, source-aware previews, unavailable metadata, local
synthetic tile HTTP identification, unchanged-region cache reuse, malformed
image failure, retry availability and no requests after closure. Public tile
views are limited to the explicitly requested visual cases, never automated
map scans. Synthetic network tests use localhost only.

The extracted GTK 4.20 source runtime cannot launch its native Glycin image
sandbox inside this restricted development container. This is an environment
limit, not an installed-Flatpak result; confinement is preserved. The new
packaged native-map checks require the bundled dependency and must pass in the
actual Flatpak before delivery. Final installed light/dark/narrow/palette,
network-failure, performance and signed-public-update checks remain required.
