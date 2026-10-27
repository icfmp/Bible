# Reading feedback — 27 October 2026

Work follows the delivered signed issue-26 source `d39a99e`. Assigned issues remain open; numbered release #87 is paused. This document records implementation checks, not client acceptance or a published batch.

## #97 / #107: native manual scrolling and actual verse alignment

Manual wheel/touchpad, scrollbar and ordinary keyboard scrolling already use GTK's own adjustment/input handling. `ScrollMotion` has capture-phase cancellation handlers returning false, and only its explicit `move()` calls animate programmatic reveal/following. Callers are `ReadingTab.reveal_reference`, `StudyPanel.reveal` and `PassageNotes.follow`; shared comparison returns early from independent following and uses one adjustment. No application-added interpolation of ordinary manual scrolling was found. No redundant removal or global animation change is made. Native touchpad hardware is unavailable in the development environment; immersion's separate page gestures/slides are retained.

The comparison bug is measurable with actual Semeur/KJV John 1: row-start alignment reports zero while the real verse-body first lines differ by up to **431 px**, because source headings belong to the same source block. The correction aligns actual body positions using native paragraph padding, retaining every heading/word and all copy offsets. At fixed geometry, native positions are read once before tags change; cumulative padding aligns subsequent correspondence groups, and final bottom padding preserves equal document extents. Geometry/content invalidation restarts the bounded settling path; no permanent tick or per-scroll full-document alignment pass is introduced.

Local GTK 4.14.5/OpenGL, 1280 × 850, 24-point source reading: all actual John 1 body starts align to **0 px** in light/dark after correction. Row starts that contain different editorial headings are intentionally not used as a proxy for verse alignment. Native source-heading/wrapping/resize/large-type and text-copy checks accompany this change. Installed Flatpak, motion recordings and final batch publication remain required.
