# Reader focus after application switching (#70)

## Actual reproduction

The existing signed alpha reproduces the full dark viewport rectangle in a real
Mutter 48.7 nested Wayland session, using its installed GNOME 49 Flatpak runtime.
A second GTK application has a separate application ID. XTest sends pointer and
Alt+Tab events to the outer compositor surface; Mutter performs the actual inner
Wayland application activation. GDK reports WaylandDisplay/WaylandToplevel.
This is actual compositor switching, not a bare-Xvfb focus-state simulation or a
claim about the client's own GNOME Shell session.

At FreSegond1910 Genesis 5:11, a pointer-focused reader has focus-visible false.
Switching away and back leaves GTK's keyboard focus-visible true, as expected for
keyboard input. The project's shared `textview.<scope>:focus-visible` rule then
draws a 2-pixel text-colored outline around the entire text viewport. Captures and
actual pixel samples establish the drawing cause independently of the screenshot
reported by the client. The reference and scroll position survive the switch.

## Scoped correction

Replace this project-defined rectangle with a two-pixel leading focus mark on
the TextView **text CSS node**, three pixels in high contrast, using the existing
palette's contrasting link color. Mirror the inset shadow for RTL. A shadow on
the parent TextView would be hidden by the text node's opaque background; this
was checked during investigation. The final mark is visibly rendered.

GTK still owns activation, focus-visible and modality. No event handler, focus
reset, synthetic click, global outline removal or text-focusability change is
introduced. The inset shadow changes no allocation, padding or text layout.
Native focus indications on buttons and other controls remain under Adwaita.
The same existing style decoration covers ordinary reading, comparison,
commentary/study and immersion. No resource, schema or persisted-data change.

## Validation and limits

The complete **229 source tests** pass. The affected installed Flatpak suite
passes as 25 ordinary cases plus the existing native immersion case on a fresh
isolated display, 26 cases total. That case is run with
`BIBLE_TEST_ISOLATED_CLICK=1` because the sandbox does not ship a nested
`xvfb-run`; no application dependency is added to make the test harness work.
Actual GTK pixel regression checks cover both text directions, light/dark and
emulated system high contrast, keyboard focus, unchanged selection, scroll,
allocation and canonical/intra-verse positions. The same focus test also runs at
system scale 2 on source GTK and the installed Flatpak.

`tools/check_reader_focus_switch.py` records actual Mutter/Wayland before/after
focus states and rendered pixels, plus native selection/copy, F9/F10/F11, tab
creation/return and opening/closing an untouched note. It requires a disposable
profile, a second application and the nested compositor's X11 input surface ID;
that outer input setup is a test harness, never a product workaround. Source and
installed-package receipts/captures are separate under `docs/evidence/focus-70`.
Installed application bytes, all 14 canonical tables and notices are audited.
Portal/display warnings remain in the original validation logs.

Deep accessibility is deferred and **has not been tested**. Basic native keyboard,
contrast and scaling checks do not imply specialist accessibility acceptance.
Bible.com/BDS remains outside this defect correction; accepted immersion #24 is
not reopened or redesigned.

Publication is a distinct gate after review/exact-head CI: merge/main CI, the
existing signed alpha, actual ordinary update of the controlled installation,
source-byte audit and preservation of notes, highlights, modules, preferences,
three study indexes and catalogue caches. Those results are recorded publicly
on the PR/issue only after they pass.
