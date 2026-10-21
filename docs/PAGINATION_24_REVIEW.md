# Continuous book pagination — architecture review candidate

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
