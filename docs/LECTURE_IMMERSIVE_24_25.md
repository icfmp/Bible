# Immersive reading and commentary — #24 and #25

## Current behavior

F11, the fullscreen button beside Aa, and the menu action enter native
immersive reading. Two adjacent pages contain successive portions of one
resource. Narrow windows and large text switch to one page. The reading
palette covers text, margins and gutter uniformly; there are no page cards.

Chapters flow continuously within a page and across spreads. Only a new
biblical book starts a new spread, always on the left, including for RTL
resources. An odd final page leaves the right side blank; an even final page
does not add an empty spread. Ordinary-reader arrows still change chapters;
immersive arrows turn pages.

Pango measures actual shaped lines. Display and copy partitions preserve the
source text. Chapter/source headings and verse numbers stay with the first
body line/word when the combined group fits. Oversized groups still make
progress. Canonical reference and intra-verse anchors preserve position during
reflow; selection is restored after GTK allocations settle.

A background worker owns a separate SWORD reader and Pango font map. Up to
three documents and page plans are retained in memory, around the current
book. Typography changes reuse source documents; number visibility rebuilds
them. Superseded preparation is cancelled cooperatively. Closing joins the
worker before resource backing files can be released. A single native call
cannot be interrupted mid-call; there is no hard cancellation-latency bound.

## Try the controls

Use a disposable test profile with resources downloaded explicitly through
the Library; no translation is bundled with the application.

1. Open a Bible and enter immersion with F11 or the button beside Aa.
2. Turn pages with the circular arrows, Page Down/Up, or Space/Shift+Space.
   Check a chapter transition within a column and a book transition on the left.
3. Change Aa, font size, spacing and window width. Check the same passage and
   selection after one/two-page transitions, including long verses and RTL text.
4. Reveal controls with the pointer or F10. Focused controls and open popovers
   remain visible. Escape closes the active popover/action surface first, then
   exits immersion. F11 and the exit button also leave immersion.
5. Check exact native selection/copy and note actions on either page. Normal
   tabs and study panels return with their state, at the passage reached.
6. Exit while preparation is pending. Open Notes or Library, then return.
   Immersion is not forced on application restart.

The commentary's local immersion button opens that selected commentary only.
Entry navigation uses actual SWORD keys, ranges and introductions. Missing
entries remain explicit. Commentary pagination does not navigate the hidden
Bible; Open in Bible is deliberate. Existing commentary selection/position and
study configuration are preserved on return. Full rich formatting and
simultaneous comparison of several commentaries remain separate limitations.

Automatic notification suppression belongs to #28. The current manual Do Not
Disturb help does not change host notification settings or claim suppression.

## Validation and remaining acceptance

The [recovery validation report](RECOVERY_VALIDATION_24.md) records fresh source
checks, installed Flatpak checks, screenshots, exact identities and limitations.
It supersedes earlier offline-only readiness statements for this candidate.
Historical evidence remains in Git and in the linked recovery report.

Xvfb verifies actual GTK widgets and native X11 input, including inside an
installed Flatpak. It does not establish GNOME/Wayland fullscreen behavior,
physical touchpad gestures, screen-reader usability, or client desktop
acceptance. Those checks remain open; #24 is not closed and #57 has not resumed.
