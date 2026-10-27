# Reading feedback validation — 27 October 2026

PR #135 starts from the delivered issue-26 alpha `d39a99e`. Numbered release
#87 remains paused and all issues stay open for client acceptance. This record
is development evidence; final batch publication is still pending.

[Implementation, measured causes and checks](../../CLIENT_FEEDBACK_20261027.md).

## Native source evidence

The [source captures and motion](source/) are unedited native GTK/Xvfb surfaces,
not installed-Flatpak captures. They are labelled separately from package and
publication evidence. [SHA-256 manifest](source/SHA256.json).

| Feedback | Before | After / check |
| --- | --- | --- |
| #107 actual verse bodies | [Light](source/comparison-before/white.png), [dark](source/comparison-before/dark.png) | [Light](source/comparison-after/white.png), [dark](source/comparison-after/dark.png); real Semeur/KJV John 1, 431 -> 0 px maximum body-start difference |
| #99 pagination bounds | [Native glyph geometry](source/immersion-before-2/geometry.json) | [Corrected geometry](source/immersion-99-final/geometry.json); source partition/copy and first visible heading retained |
| #98 moving focus edge | [60 fps before](source/immersion-before-2/turns.mp4), [analysis](source/immersion-before-2/blue-analysis.json) | [60 fps after](source/immersion-focus-after/turns.mp4), [dark one-column](source/immersion-focus-dark-one-column/turns.mp4); zero interior blue runs |
| #102 queued-selection race | [Native interleaving](source/selection-race-before/report.json), [capture](source/selection-race-before/keyboard-pointer-race.png) | [Same interleaving](source/selection-race-after/report.json), [capture](source/selection-race-after/keyboard-pointer-race.png); stale keyboard idle cannot cancel the new pointer selection |
| #105 doubled Study boundary | [Light](source/divider-before/white.png), [dark](source/divider-before/dark.png) | [Light](source/divider-after/white.png), [dark](source/divider-after/dark.png); four palettes, 420 -> 500 -> 420 px actual drags, keys, hide/reopen and narrow collapse |
| #75 Notes hierarchy | [Light](source/notes-before/white-wide.png), [dark](source/notes-before/dark-wide.png) | [Light](source/notes-after-final/white-wide.png), [dark](source/notes-after-final/dark-wide.png), [large-type narrow](source/notes-after-final/narrow-large-type.png); distinct synthetic notes/highlights, native editing and original data identities |
| #111 direct chapters | [Light](source/navigation-before/white-wide.png), [dark](source/navigation-before/dark-wide.png) | [Light](source/navigation-after/white-wide.png), [dark](source/navigation-after/dark-wide.png); exact typed verses remain |
| #128 reading preferences | Existing General-only surface is retained in earlier package evidence | [Reading](source/preferences-captures/white-wide-top.png), [layout/colors](source/preferences-captures/white-wide-bottom.png), [narrow](source/preferences-captures/white-narrow-large-type-top.png), [native font picker](source/font-chooser-captures/native-family-picker.png) |
| #104 / #106 maps and markers | Earlier published coastline detail is retained in preceding evidence | [Shinar](source/formal-markers-gl/Shinar-white-map.png), [dark](source/formal-markers-gl/Shinar-dark-map.png), [Haran](source/formal-markers-gl/Haran-white-map.png); real labelled native OSM map, proposed/approximate locations, reader behind transient detail |

GTK 4.20.4/OpenGL was used for immersion, selection, Notes, navigation and full
preferences source captures. The map after evidence explicitly records GTK
4.14.5/GLRenderer. The comparison geometry check was also repeated explicitly
with GTK 4.14.5/GLRenderer at 0 px; earlier source captures are not assigned an
unrecorded renderer. Source checks do not establish the client's GNOME/Wayland,
hardware touchpad, fractional scaling or specialist accessibility acceptance.

Map screenshots retain visible attribution: © OpenStreetMap contributors,
<https://www.openstreetmap.org/copyright>, ODbL 1.0. Place relationships and
candidate data: OpenBible.info, CC BY 4.0, with OSM-derived credits retained.
Bible excerpts come from actual installed modules, never generated text. Test
notes are synthetic. No complete translation, raw provider archive or user
profile is included.

## Verified installed package so far

[CI 40505266274](https://github.com/icfmp/Bible/actions/runs/40505266274), source
`bf60b781162b0803895299cc5d015ef637f6ab10`, passes 174 installed tests, 12 immersive
checks and six isolated marker/selection checks, actual native map HTTP/cache/
image failure tests and real-resource online/offline study. Bundle SHA-256:
`85c3a925afc2ee2cee4de532dba478adfbf329cb5c0b02ffd3d5d2a394063967`.

Actual sustained/reversed scrolling has zero adjustment later than 500 ms
after input stops in single, comparison and Study modes. GL first-toolbar-hide
transition: 0.218 ms handler, 0.820 ms first adjustment, 16.505 ms first paint;
bar absent in that first frame, backdrop released and placement stopped. These
are installed GTK/Xvfb software-renderer measurements, not desktop benchmarks.
The separate diagnostic that deliberately changes a scrollbar adjustment while
keeping the bar visible incurs higher GPU/CPU work; it must not be confused
with native wheel/scrollbar input, which dismisses the bar. At unchanged content
it records zero snapshot/invalidation/adaptation callbacks over the idle phase.

The expanded installed before/after visual and CPU/memory comparison and actual
signed update remain pending. The first comparison attempt stopped before
measurements when the mutable optional cross-reference ZIP failed its pin.
Both versions reuse the [same validated installed index](fixtures/) instead;
application download checks and user data are unchanged.
