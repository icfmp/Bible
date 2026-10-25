# Client feedback: workspace, preferences, immersion and popups

Related to #75, #94, #99, #98, #102 and #105. All descriptions and comments were reread. The immersion geometry correction was implemented and checked before the keyboard correction. The issues stay OPEN for client acceptance; numbered publication #87 remains paused.

These are actual GTK screenshots, not mockups or retouched images. Before: `7a633f3281d0a6086cb822a1ac9f055beb53445b`. After: the implementation in this PR. The source capture environment is GTK 4.14/libadwaita 1.5, the new OpenGL renderer (`NglRenderer`), Xvfb with an X11 compositor, at scale 1. The compositor is a test dependency only; nothing was added to the application runtime. Disposable profiles contain real downloaded resources. FreBDM1707 is used for the client's Genesis example; no complete Bible module is included here.

The workflow also installs the built Flatpak and captures its actual `/app/` implementation with GNOME Platform 49, OpenGL and composited X11. Its full capture matrix, input/geometry measurements, live-backdrop checks and renderer identity are retained in the `Bible-alpha-linux-x86_64` artifact (`client-feedback/`, `packaged-client-feedback.log`). CI receipts distinguish those installed results from the source results below. This does not establish acceptance on the client's GNOME/Wayland desktop, portal integration or fractional display scaling.

## Changes and proof

| Surface | Before | After |
| --- | --- | --- |
| Direct Bible / Notes, light | [Before](before-white-reading.png) | [After](after-white-reading.png) |
| Direct Bible / Notes, dark | [Before](before-dark-reading.png) | [After](after-dark-reading.png) |
| Preferences, light | [Before](before-preferences-white-wide-top.png) | [After](after-preferences-white-wide-top.png) |
| Preferences, dark | [Before](before-preferences-dark-wide-top.png) | [After](after-preferences-dark-wide-top.png) |
| Study header, light | [Before](before-white-study-notes.png) | [After](after-white-study-notes.png) |
| Study header, dark | [Before](before-dark-study-notes.png) | [After](after-dark-study-notes.png) |
| Study header, paper | [Before](before-paper-study-notes.png) | [After](after-paper-study-notes.png) |
| Study header, black | [Before](before-black-study-notes.png) | [After](after-black-study-notes.png) |
| Selection bar, light | [Before](before-white-selection.png) | [After](after-white-selection.png) |
| Selection bar, dark | [Before](before-dark-selection.png) | [After](after-dark-selection.png) |
| Copy popup, light | [Before](before-white-copy-menu.png) | [After](after-white-copy-menu.png) |
| Copy popup, dark | [Before](before-dark-copy-menu.png) | [After](after-dark-copy-menu.png) |
| Main menu | [Before](before-white-main-menu.png) | [After](after-white-main-menu.png) |
| Native context menu | [Before](before-white-context-menu.png) | [After](after-white-context-menu.png) |
| Shared immersive reading box | [Before](before-immersion-idle-start.png) | [After](after-immersion-idle-start.png) |

Additional captures: [French backup actions with large type](after-preferences-white-small-large-type-bottom.png), [English preferences](after-en-preferences-white-wide-top.png), [English backups with large type](after-en-preferences-white-small-large-type-bottom.png), [narrow immersion](after-immersion-narrow.png), [narrow study](after-study-narrow.png).

- **#75:** two visible native grouped toggle buttons, one activation per space change, no dropdown. Existing workspace, drafts, annotations and navigation are retained. The 360 px Notes regression is checked.
- **#94:** direct System/Light/Dark controls, unchanged language dropdown, plain theme explanation, translated French backup heading, separate native export/restore action rows, and explicit unencrypted annotation-backup scope. The existing backup implementation is reused without storage/schema changes.
- **#99:** the footer is an overlay; the shared usable text budget is centered in the full immersive viewport, including the shaped trailing-line reserve. Both columns retain one common origin/budget. A short final column or book end remains naturally short. Control reveal/fade does not reflow or repaginate the text. Existing exact whole-book partition, anchor and last-line tests pass.
- **#98:** the previous stack transition could leave keyboard focus unset; a subsequent arrow merely reacquired focus. Preserve focus in the reading view through the transition, and decide whether controls own the event before changing focus visibility. Real X11 input reproduces missed keys before, and each tested key turns after. Menus, deliberate control focus, text selection and editing keep their own keys. The existing slide and reduced-motion behavior remain.
- **#102:** a genuine nonempty text selection is required for the floating bar. Simple verse activation and blank clicks do not create it; collapsed selection clears it. Copy is one menu button; only choosing a command copies. Right-click/keyboard text menus remain native and keep a separate source-specific clicked/selected target, including comparison versification and immersion.
- **#102 shared popup cause:** the palette's broad `.background` selector also painted the native `popover.background` root. It created an extra rectangular backing outside the native rounded contents; the copy arrow also inherited the light palette. Exclude popover roots, retain native contents/shadows, and style their arrows coherently. Only the selection action menus use the specifically requested dark surface. Open main, passage, version, source, Aa, text context, Copy and highlight popups were captured in white/dark/paper/black and emulated high contrast.
- **#102 blur:** the existing bounded reader paintable is sampled through its actual coordinate transform; blur is strengthened to 16 with a three-radius input margin, rounded output clipping, then a separate dark translucent foreground. The captures and a zero-blur diagnostic show actual glyph smoothing, rather than merely checking for a blur node. The source new OpenGL and Cairo renderers render the effect. GTK 4.14's legacy OpenGL renderer produced sharp glyphs in the diagnostic; this is distinct from the new OpenGL renderer used by the supported Platform 49 package. High contrast retains the readable opaque fallback. No renderer is forced in the application and no CPU screenshot/readback was added to production rendering.
- **#105:** the complete study header uses the secondary study surface, including its native start/title/end boxes. Measured colors match the body across all four palettes. Active-tab ownership and stored palette preferences are unchanged; no Map tab was reintroduced.

## Measured checks

[Source measurements](measurements.json) retain real input results, palette pixels and sustained-scroll metrics. **321 source tests pass**, plus native mouse/keyboard passage actions, double-click selection, explicit context targeting and the workspace/backup regressions. Before/after idle samples keep the page geometry and anchor stable for 15 seconds. [Idle and input recording](immersion-idle-and-input.mp4) shows the actual immersive window with real FreBDM1707 text; it includes normal and disabled animation input.

The #125 sustained-input check passes in single, comparison and study modes and with the selection toolbar initially visible: real independent X11 input continues while GTK renders, direction changes are bounded, and there are zero adjustment changes more than 500 ms after input stops. The toolbar still dismisses on wheel input, as before.

[Light live-backdrop recording](white-live-backdrop.mp4) and [dark live-backdrop recording](dark-live-backdrop.mp4) show the actual reader moving both ways beneath the selection surface. This diagnostic drives the reader's existing scrollbar adjustment to keep the selection surface visible; it does not claim that wheel input leaves the bar open. Controls remain a separate sharp overlay, selection is retained, and no video blur was applied.

The source checks are developer evidence. Installed Flatpak and signed-channel update/preservation outcomes are recorded in the delivery receipt after their actual completion. No data migration, preference schema change, resource removal or persistent feature disable is included.
