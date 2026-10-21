# Uniform comparison reading surfaces (#36)

After completing the #51 crash correction, the unwanted comparison surround was
reproduced with actual FreSegond1910/Lausanne: the white text surface was RGB
255/255/255, but the parent comparison box still used native RGB 250/250/250.
Only the primary overlay had the scoped reading-surface class. The comparison
header, gaps and empty viewport therefore exposed the window's default surface.

Apply the same existing palette surface to the common Bible layout, both reader
overlays, scroll windows and comparison container. There is no hard-coded white,
new palette, extra card, spacing change or study-drawer background change. The
existing source renderer, reference coordinators and equal allocation are kept.
An empty/error recovery probe additionally caught indexing a None document
signature after a failed comparison; the targeted guard now allows the installed
comparison to render again. The existing regression verifies that recovery.

`tools/check_comparison_surfaces.py TEST_PROFILE CAPTURE_PREFIX` samples actual
GTK/X11 screen pixels at the main surface, comparison surround, viewport, side
margin, bottom empty space and shared gutter. It verifies White, Paper, Dark,
Black and emulated high contrast day/night with study closed and open; actual
colors match the active reading palette at every sampled point (tolerance one
channel level). It also checks resizing, empty/unavailable and recovered content,
equal allocation, retained exact selected text and passage. Run on a virtual
display of at least 1800×1100 for the 1600-pixel horizontal three-pane case.

Actual GTK captures in `captures/comparison-36-surface-*.png`:

| Palette | Study closed | Study open |
| --- | --- | --- |
| White | [capture](captures/comparison-36-surface-white-plain.png) | [capture](captures/comparison-36-surface-white-study.png) |
| Paper | [capture](captures/comparison-36-surface-paper-plain.png) | [capture](captures/comparison-36-surface-paper-study.png) |
| Dark gray | [capture](captures/comparison-36-surface-dark-plain.png) | [capture](captures/comparison-36-surface-dark-study.png) |
| Black | [capture](captures/comparison-36-surface-black-plain.png) | [capture](captures/comparison-36-surface-black-study.png) |
| High contrast day (emulated) | [capture](captures/comparison-36-surface-contrast-day-plain.png) | [capture](captures/comparison-36-surface-contrast-day-study.png) |
| High contrast night (emulated) | [capture](captures/comparison-36-surface-contrast-night-plain.png) | [capture](captures/comparison-36-surface-contrast-night-study.png) |

[Smaller/adaptive resize](captures/comparison-36-surface-resize-1200.png),
[wide resize](captures/comparison-36-surface-resize-1600.png),
[unavailable/empty](captures/comparison-36-surface-unavailable-empty.png),
[recovered](captures/comparison-36-surface-restored.png).

All 145 local tests pass. Native offline Segond/Lausanne bidirectional reference
following, equal widths, selection/reflow and no-history checks pass. Existing
study wheel and two >1.5-second scrollbar drags also pass with focus/history
preserved. These Xvfb captures and high-contrast
notifications are automated evidence, not manual GNOME/Wayland, physical trackpad,
live portal or accessibility acceptance. Keep #36 open for client validation.
No pending PR is merged and the existing signed alpha channel is unchanged.
Final tests and actual published source/revision are recorded in the handoff.


## Actual published-package verification

Source `c964162`, CI 39639628244/publication 39640813062 green, revision
39640813062-2. Actual existing system update matches public provenance with the
unchanged signing fingerprint. The complete pixel matrix also passes on that
PUBLIC alpha with /app imports; captures above have been replaced by those
actual Flatpak screenshots. [Pixel log](evidence/comparison-36-public-pixels.txt).

The runtime lacks Pillow, so [the Xvfb parent](evidence/flatpak_capture_parent.py)
performs real ImageGrab captures and unmodified pixel reads, while [the worker](evidence/flatpak_capture_worker.py)
executes the checker in the sandbox and asserts /app imports. The two communicate
only over a local Unix socket in the disposable shared evidence directory. With
this environment's /src and /evidence mounts, run the parent inside bible-night
under dbus-run-session and xvfb-run (1800×1100 display), passing the checker path,
TEST profile and screenshot prefix. No source app overlay or synthetic pixels.
The helper now waits for study positioning only when the drawer is visible; an
unmapped drawer does not receive animation frames. This corrects the test wait,
not the product's reading behavior. Manual GNOME/live high contrast remains open.
