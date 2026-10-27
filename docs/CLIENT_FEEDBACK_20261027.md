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

## #128: full global reading preferences, shared with Aa

General and backups remain on General; a native Reading page groups Font,
independent Study content font, Layout and Colors. A standard Gtk.FontDialog
chooses an installed family, with a native Pango preview. A missing saved family
is retained and labelled with its fallback rather than silently replaced or
shown as None. Accepting the chooser explicitly can replace that saved choice,
even when the selected family is the same as its temporary fallback.

Both presentations edit the same ReadingPreferences instance. Advanced values
appear as Custom in Aa; merely opening either presentation does not snap them
to a preset. Native numeric changes save immediately and coalesce expensive
reflow into one pending main-loop idle; closing the owner cancels that callback.
The existing worker cancellation and bounded plan cache retain only current
settings. No periodic work is introduced.

Version 1 is backward compatible with existing files and defaults. Unsupported
future versions and malformed values preserve the original file and refuse
writes. New fields/defaults and ownership:

| Setting | Default / bounds | Scope |
| --- | --- | --- |
| Reading font/size | Existing DejaVu Serif, 14 pt; 12–64 pt | Shared reading and separate immersive readers |
| Study family | Existing sans-serif; installed choice or retained missing name | Docked content only, including Notes, References, Commentaries and their previews; controls/global Notes/immersive commentary stay independent |
| Extra line spacing | Existing preset, 16 px by default; optional integer 0–48 px | Reading layout, native GTK and worker Pango use the same value |
| Maximum text width | Existing Narrow/580 px; optional 280–1440 logical px | Shared reading and immersion; available width may be smaller |
| Minimum scrolling margin | Existing 66 px; optional 48–160 logical px | Scrolling readers; small windows clamp to safe available space. Existing immersive insets are retained |
| Alignment | Existing natural start (left, right for RTL), or justified | Reading source text; copied/stored text is unchanged |
| Immersive columns | Existing Automatic, or One column | Maximum two; narrow windows never force two columns |
| Palettes | Existing day/night choices and system/high-contrast ownership | Existing whole-window model, with named visual swatches |

Reset reading settings restores these reading defaults only. Notes, resources,
application language/backups and stored annotation data are untouched. Optional
per-pane font/size/background overrides remain explicitly deferred until after
beta and have no unfinished controls here.

No automatic-hyphenation toggle is exposed: the available native
[Pango insert-hyphens attribute](https://docs.gtk.org/Pango/func.attr_insert_hyphens_new.html)
adds a visual hyphen when a word must break, rather than providing a verified
French/English dictionary-based syllable-hyphenation service. Existing native
wrapping remains; no source characters, soft hyphens or new engine are inserted.

Source GTK 4.20.4 checks cover legacy/custom/future-file persistence, full/Aa
round trips and Custom labels, reset, unavailable family preservation, study
font independence, one-column mode, justified reflow and exact anchors.
Worker/native partition equivalence also covers custom spacing plus justification.
The 25-test appearance/immersion/pagination suite and 21-test settings/immersion/
comparison/RTL suite pass; the final focused settings/client-feedback suite has
9 passing tests. A real native family chooser accepts a replacement for a saved
missing Study family without changing the Bible font. Actual source GTK captures
cover white/dark/sepia/black, wide and 560 px with larger interface type. These
are developer source checks; final installed-package checks and signed delivery
remain pending.

The complete patched native source suite also passes: **368 tests**, including
all four native map checks, the new settings checks and existing persistence,
annotation, source-text and navigation regressions (GTK 4.14.5). The current
map packaging retry corrects the measured `/app/lib64` install to `/app/lib`;
a successful local source run is not a substitute for that pending installed
Flatpak verification.

## #102: cancel stale selection completions, keep native selection gestures

A valid native interleaving reproduces a missing bar with a genuinely new
selection: release Shift after selecting two source characters, then start a
mouse drag before the queued keyboard idle executes. The old keyboard callback
has no intent generation; it sees the new drag's temporarily empty selection,
dismisses it and invalidates its completion. Actual FreBDM1707 Genesis 11,
GTK 4.20.4/OpenGL with Study → Notes open: old range 163–165 is replaced by
230–350, but the bar stays hidden. This is a measured lifecycle defect; the
client screenshots alone do not prove their exact input sequence or cause.

There is now one pending, cancellable main-loop capture. Pointer and keyboard
completions both carry their intent generation. A new gesture, dismissal,
scroll/source/tab change or owner closure cancels obsolete work. Escape also
cancels a completion before its bar appears. Native GTK selection/drag-and-drop,
gesture handling and scrolling remain; no raw input replacement, polling,
whole-verse selection, permanent toolbar or new renderer is added. Hidden
backdrops continue to detach through the existing path.

The same native keyboard → mouse sequence now selects 229–350 (the metadata
slots moved in #106) and reveals the correct current source actions after
release. No bar appears mid-drag. Fourteen focused tests pass, including a real
native input regression, repeated forward/backward replacement, wheel dismissal
and reopening, Escape cancellation, copy/source identity, hidden-work and idle
layout checks. The unchanged baseline itself also passes 24 qualified ordinary
forward/backward new selections. Initial unqualified trials that started inside
old text selection or outside the viewport are discarded: GTK drag-and-drop
is not evidence of a newly completed selection. Final installed-package matrix,
real-resource controls and client GNOME/Wayland acceptance remain required.

Map packaging retry **40492374457** passes the installed Flatpak checks, including
the required native map HTTP/cache/image-failure tests. The successful source is
`fb110cc6b9c9a5b2c7797824a24adb9e4a4f5ac2`; this feature-branch package is not yet
a published signed alpha. Shinar's supplied role is a representative point,
so its detail explicitly says the area is approximate rather than implying an
exact historical site. Nonlocated alternatives remain acknowledged.

## #105: one native Study boundary, intact resizing

The actual widget tree has an 8 px interactive StudyDivider containing a
Gtk.Separator, next to OverlaySplitView's existing full-height boundary. Only
that redundant decorative child is removed. The native split view, hit area,
col-resize cursor, focus outline, drag/key controllers, saved width and
adaptive bounds are retained. No layout replacement or new setting is added.

GTK 4.20.4/OpenGL real Segond/MHC checks in White, Dark, Paper and Black pass:
actual mouse drags change 420 -> 500 -> 420 px, Left/Right change 32 px each,
hide/reopen retains the width, and a 560 px window collapses the drawer and
hides the handle. Measured header/background RGBs match across each header's
allocated width and the adjacent plain body surface: 240/240/240, 48/48/48,
229/220/195 and 18/18/18 respectively. Bottom rounded-window shadows are not
misreported as a header mismatch. Before/after whole native captures are
retained; actual installed final verification remains required.

## #75: collection editing, distinct panes and editor bands

The global workspace has no New passage note button or equivalent implicit
creation route. Ctrl+N is disabled there, and direct creation callbacks refuse
the hidden reading context. Existing-record editing, reader-context creation,
selection actions and the passage drawer remain. The unused legacy collection
window also loses its creation button. No data/schema change is made.

Filters, list and editor use scoped native/palette surfaces, a thin native
list/detail separator, compact inset rows with quiet separators and native
accent selection. Detail separates displayed excerpt/version from the selected
note's original source, formatting/writing and labels/related records. Insets
are aligned; related records follow editing rather than interrupting context.
Separate excerpt and related-list scrollers are removed. The native text
editor retains its own caret-following scroll; the outer form scroll remains
for controls that exceed short/large-type windows, rather than forcing an
unbounded text widget or adding a custom caret/scroll bridge.

37 affected tests pass with patched GTK 4.14.5. The additional no-global-create
check and 28 native UI cases pass with the available GTK 4.20.4 source runtime;
that run's separate language-restart subprocess fails to launch under the
extracted runtime ABI and is not claimed as passed (the system suite and real
installed CI cover process startup). Actual native pointer/keyboard checks with
a copied real-resource profile pass typing/autosave, SQLite write prohibition,
cancel retaining the draft, workspace flush, Library access, highlight removal
confirmation/cancel, related-note preservation and full-content search. All 64
resource files are unchanged. Native source captures include several distinct
notes/highlights, a long note, four palettes/high contrast, 560 px panes and
large UI type. Installed-package checks and final publication remain pending.

## #111: direct chapter activation, exact verses through typed references

The entire graphical Verse row, adjacent arrow and Open chapter confirmation
are removed. A native chapter button commits its actual first available verse,
dismisses the picker and focuses the existing reading tab. Book browsing,
hover and focus alone do not navigate. Typed localized references still reach
an exact verse. Missing verses, NT-only editions, source changes, other tabs,
Text/Themes and history use the existing providers and navigation contract.

Actual GTK 4.20.4 pointer, Space and Return inputs pass. The native check also
checks focus/hover without navigation and one history entry per activation.
Source before/after wide/narrow light/dark captures are retained. The complete
patched GTK 4.14.5 source suite now passes **371 tests**, including annotation,
selection lifecycle, native map, typography, source identity and persistence
checks. Installed package validation and publication of the final source remain
required.

## #114: retain and revalidate the delivered first word-study increment

Its current description and only comment have no new scope-changing feedback.
The deliberate word-study action, honest verse-source fallback, temporary
Study detail/Back and shared lemma occurrence search are retained. No permanent
tab, TIPNR prose, translation-wide token alignment or new provider is added.
The source provider/draft/heading/mapping regressions remain in the full suite.

With the real installed optional STEP dataset and real Bible modules, the
source check passes Hebrew Genesis 1:1 exploration (seven source words), exact
H1254A identity (53 tokens / 45 numeric verses) and Greek G3056 counts (330 /
317), shared occurrence results, and the numbered-Psalm-heading guard. Segond
51:3 maps to the actual NRSV source 51:1; three numbered titles remain honestly
unavailable. The comparison's 19 actual body starts align to 0 px. Notes,
schema and all 64 resource files remain unchanged. Final actual installed
package, offline and signed-update verification remain required.
