# Continuous book pagination — integration review

This branch replaces chapter-sized Bible page plans with one continuous
document per actual SWORD book. Chapter titles use remaining page space;
only a new book starts a spread. An odd final page leaves the right page blank,
then the next book starts on the left. Backward turns recover the preceding
book's correct full or half spread. In one-page mode a new book starts a page.
Bible spread order stays left-to-right even for RTL resources; the text views
retain their actual RTL direction. Verse numbers use a non-breaking space.

The reader surface, gutters and margins use the same scoped reading palette;
there are no page cards on a separate gray canvas.

## Preparation and state

Synchronous whole-book preparation measured about 0.9 seconds for Genesis and
1.5 seconds for Psalms, so it is not performed on GTK's thread. A single worker
uses a separate SWORD manager/key and a private PangoCairo font map. GTK widgets
are accessed only on their owning thread. Completed immutable document/page
data is collected by GTK's existing tick callback. Only current/adjacent books
are prepared and the cache is bounded to three books, never an entire Bible.
Superseded queued work is canceled. Closing joins active work before a test or
profile can remove SWORD's backing files.

Canonical reference/character anchors and selected passage positions remain
the existing persistence contract; no notes/session migration is introduced.
Reflow temporarily prepares pages without moving the hidden commentary or
losing canonical selection. Commentary immersion keeps its real entry
boundaries, explicit entry navigation and unchanged hidden Bible position.

## Actual validation

- 137 local tests passed, including chapter joins, odd/even book boundaries,
  backward/forward round trips, one/two pages, RTL, canonical intra-verse reflow,
  selection/copy/notes, commentary return and main-loop responsiveness.
- Real FreSegond1910, offline in GTK/Xvfb: Genesis produced 180 pages; 42 chapter
  headings continued inside a page. The exact page slices reconstruct the
  entire source document without omissions/duplication.
- First preparation/layout stabilization took 1.675 s while GTK processed 65
  heartbeat ticks; the largest measured heartbeat gap was 0.244 s. This is
  an actual virtual-display measurement, not a desktop latency guarantee.
- Very airy reflow retained the canonical intra-verse anchor. The committed
  screenshot shows Genesis 2 continuing on the right-hand page after Genesis 1.
- Native mouse/keyboard F11, PageDown, F10 and Escape checks passed locally.

The worker/page-plan change is isolated for architectural review under
AGENTS.md. Candidate Flatpak CI and manual GNOME/Wayland/accessibility testing
remain separate checks. Do not advertise this candidate as available through
the public signed channel until review, merge and publication are verified.

## Coordination with the corrective alpha (21 October)

Merged main through `d48c760` into this review branch, without merging this PR
into main. The 14 pt / Very airy / Narrow defaults, font-relative gray numbers,
nonbreaking first-word presentation and original-character native Copy now work
through whole-book documents as well. Book composition explicitly concatenates
copy text alongside display text so presentation spaces cannot leak into Copy.

Whole-book Pango shaping exposed a significant slowdown from thousands of
ALLOW_BREAKS attribute ranges. Nonbreaking presentation spaces already enforce
the grouping, so the redundant Pango attributes are omitted; span metadata still
prevents anchor/page partitions from splitting a marker/first word.

141 full local tests passed; after the final shaping correction, 12 affected
pagination/immersion/typography tests passed. The real offline Genesis check has
211 pages and 42 chapter continuations with the new default; preparation stabilized
in 1.377 s while GTK processed 77 heartbeat ticks (largest gap 0.325 s). Display
page slices reconstruct the complete document, generated marker gaps copy as
ordinary spaces, marker/word groups do not split at page boundaries and reflow
retains the canonical anchor. These metrics supersede the old Airy measurements
for this coordinated candidate. [Actual GTK capture](captures/continuous-book-24-corrective.png).

Architecture review and manual GNOME/Wayland/accessibility acceptance remain
required. A new branch CI/Flatpak candidate must be verified; nothing in this PR
is announced as published.

## Drawer and contextual actions coordination

Main through `f8395bc` is merged on this review branch without publishing the PR.
All 146 tests pass. Actual offline FreSegond Genesis produces 211 pages with 42
chapter starts continuing within a page; preparation took 1.47 seconds with 75
GTK heartbeat ticks (largest observed gap 0.365 seconds). Exact page partition
and canonical in-verse reflow anchors remain intact. Original-character Copy,
nonbreaking verse starts and the efficient whole-book Pango attributes are kept.

The real native pointer/keyboard action probe also passes in this candidate,
including partial Copy, original second-Bible note context, mapped Compare and
immersive selection/closing without accidental page turns. Screenshot:
`captures/continuous-book-24-drawer-actions.png`. These are Xvfb checks, not manual
GNOME validation. PR #39 remains awaiting review and is not in the public alpha.

## Final combined integration review — 21 October 2026

The client authorized sequential completion of the outstanding deliveries.
Current main, including reviewed PRs #41, #38 and #40, is integrated in
`b90bd9b`. The architecture review confirms a single background worker with
independent SWORD and Pango state, bounded current/adjacent-book plans and GTK
updates on its owning thread. There is no data/schema migration. The existing
commentary crash, palette, reference synchronization and original-character
Copy fixes remain present. Personal highlights and the temporary commentary
indicator remain separate; commentary inline styles are applied on every page.

All **157 combined local tests pass**. Real offline FreSegond Genesis has
**211 pages and 42 chapter continuations within pages**, an exact text partition
and preserved canonical anchor after Very airy reflow. Stabilization took
1.427 seconds with 75 GTK heartbeat ticks (largest observed gap 0.358 seconds).
The refreshed [actual GTK capture](captures/continuous-book-24-final-review.png)
comes from this integrated code with real downloaded modules. Native pointer
and keyboard action validation also checks immersive selection and Copy without
unintended page turns, as well as persistent highlights and second-Bible note
context. These automated Xvfb checks do not replace client GNOME/Wayland or
accessibility acceptance. Actual signed-channel availability is checked after
main CI and publication, not inferred from this source review.
