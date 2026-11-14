# Ready UX follow-ups

Application-only work for #221 and #258–#262. This records implementation and
developer checks; merge, signed publication and client acceptance are separate.

| Issue | Application change | Distinct validation |
| --- | --- | --- |
| #221 | Three Library-style neutral placeholder cards during genuinely pending Text searches, after a short one-shot delay. Native animation stops when hidden/completed/cancelled and honors reduced motion. Existing search algorithms and stale-response guards remain intact. | Controlled pending/cancellation/reduced-motion tests; real NBS zero/two/many results and unchanged Themes lists, FR/EN, light/dark, desktop/narrow/large type. Correct first-allocation sizing uses the popover's allocated width, never a provisional 1px row width. |
| #258 | Shared native restrained empty presentation for successful zero references, a chapter without personal annotations, and a genuinely empty commentary chapter. Attribution remains accessible; populated lists and continuous commentary streams are preserved. | Genuine empty versus unavailable/error/mapping cases; populated-to-empty transitions; drafts remain visible; real OpenBible zero lookup at Numbers2:1 and real installed Segond text; large type and emulated high contrast. |
| #259 | Native view selector in the contextual header, full names on desktop and icons at small/text-scaled widths. The studied passage appears once; close remains separate. The standalone place component retains its own context. | Keyboard walkthrough across BDS, NBS, Segond and KJV, Genesis11:4–6 and Mark11:29–30; exact excerpts and unchanged reading history/notes; four selected-view captures; narrow large-type regression. |
| #260 | Remove the whole-editor maximum-width wrapper and let the shared writing region expand vertically in the main Notes workspace. Secondary labels and links follow the flexible writing area in the existing focus-aware scroll viewport. | Wide editor allocation and short/narrow reachability; autosave, record switching, draft/conflict safeguards, unchanged note IDs/text/references; actual FR/EN before/after captures. |
| #261 | Modest disclosure-label padding and a native separator inside the expanded Visible elements child. | Expanded/collapsed FR/EN captures and existing visibility/persistence tests; no divider remains when collapsed. |
| #262 | Top/bottom scroll insets only in the expanded passage-note window; retain the quick editor's layout and the same buffer. | Actual FR/EN linked/unlinked, narrow/wide and light/dark captures; expand/save/failure/cancel and source-context preservation. |

## Reproducible checks and limitations

The focused native GTK suite passed59 tests before the final small header and
commentary allocation assertions. Additional note-store/import/linked-reference
checks passed; these overlap and are not added into a fictitious unique total.
Final CI and packaged checks must still pass before delivery. The existing
packaged controls walkthrough now captures a held **real** search followed by
real results (`--pending`); the test-only gate does not fabricate result content.

Before captures use the actual installed alpha.28 application. Development-after
captures use the changed source with the same installed GNOME49 runtime
(GTK4.20.4/libadwaita1.8), composited X11 and Cairo/software OpenGL as recorded.
These are not evidence that the new source is already in the published Flatpak.
Personal notes used for screenshots are disposable test notes; Scripture and
study-resource files are actual existing downloads and are not rewritten.

The local Cloud environment lacks the Flatpak portal needed by the sandboxed
Glycin tile loader. Place metadata, tab navigation and hidden-map shutdown can be
verified here; map-tile rendering remains a full packaged-CI/client check. The
image sandbox is not disabled. Native X11 focus handoff is supplied explicitly
after test-created modal windows because Xvfb has no window manager.

Emulated high contrast and keyboard checks are distinct from screen-reader,
client GNOME/Wayland, hardware-GPU and fractional desktop-scale acceptance. All
issues remain open. Nothing in this batch edits resource datasets or another
repository, or claims unavailable dictionaries/people content now exists.
