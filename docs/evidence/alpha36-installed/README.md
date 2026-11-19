# Installed alpha.36 verification

Application PR #318 and diagnostic-only PR #319. Exact application source:
`43a0a622095324b89c12ce7d8a17914bb5117c3e`.
Green [main CI 44471909330](https://github.com/icfmp/Bible/actions/runs/44471909330)
and [signed publication 44476258836](https://github.com/icfmp/Bible/actions/runs/44476258836).

The public signed Flatpak actually updated from alpha.35 to
`7f9d3bc6e41b3fc35b54d4492a55b933490be49bff759b5a2e7c8b14363cc71a`.
[Update receipt](update318-verified.json) and [public provenance](public318-provenance.json):
all 118 Python files and all 37 icon/manifest/license files match the verified
source, including absence of the obsolete partial hicolor index. The sole
trusted signing key and both GPG verification settings remain unchanged. All
159 checked files in the three original retained validation profiles remain
byte-identical, checked again after the GUI tests. No original profile is reset.
The temporary validation bus expired during an environment restart; restoring
that local bus allowed the normal signed update without modifying app data.

| Actual installed GTK check | Evidence |
| --- | --- |
| FR/light note popup, fixed source context and durable body/label/linked passage after Close/reopen | [Popup](fr-note-popup.png), [receipt](fr.json) |
| EN/dark note popup at 400×580 with 16pt interface/high contrast; bottom Delete reachable by normal scrolling | [Popup](en-note-popup.png), [bottom](en-note-popup-bottom.png), [receipt](en.json) |
| Exact partial selected text with actual edition, default Copy, independent chevron and nested Escape | [FR](fr-selection.png), [EN](en-selection.png); actual clipboard assertions in both receipts |
| Genuine KJV and existing OpenBible references | [FR](fr-references.png), [EN](en-references.png) |
| Implemented Original text / Map, retained native dialog controls | [FR Study](fr-study.png), [EN Study](en-study.png) |
| Seamless secondary headers: Preferences / Shortcuts / Library | [Preferences](fr-preferences.png), [Shortcuts](en-shortcuts.png), [Library](fr-library.png); all five dialog classes verified in each receipt |
| Real pointer hover at card edge / center / chevron and outside, Notes and References | [Installed alpha.35 before](hover-before.mp4), [installed alpha.36 after](hover-after.mp4), [after receipt](hover-after.json) |

The hover videos are unedited native root-window recordings, H.264, 1440×1100,
15fps. They use matching disposable copies of retained real resources plus an
explicit test personal note/green mark. They measure no latency or throughput.
The after clip is 68 frames/4.53 seconds. The original annotation data is not
modified. The preserved reading preferences explain the large Bible text in
these captures; no profile reset is used to obtain a different appearance.

Both native FR/EN flows import the actual `/app/` code and use GTK 4.20.4,
GNOME 49, X11/software OpenGL at scale 100%. Five further installed checks pass:
all icon inventory/unknown-icon native fallbacks, coalesced note body/labels/links
and immediate Close, confirmed delete without pending-write resurrection, and
out-of-order/stale reference completion. Synthetic Cairo fixtures emitted native
allocation warnings; the actual GL screenshots were inspected separately.
The full packaged CI additionally covers real-resource/offline, old backups,
comparison/immersion, word/contextual flows and first-input/hidden-work guards.

[Development before/after captures, geometry and reference-transition videos](../notes-interface-ready/README.md)
remain valid for unchanged application code and clearly identify their baselines.
The controlled reference-video latency is not a performance benchmark.
No actual KDE/Plasma, client Wayland/GPU, physical touch or assistive-technology
session is claimed. The local real-place diagnostic proves canvas/layer cleanup;
its tile loader needs a working desktop Flatpak portal and was not validated as
live tile rendering. Missing data is left unavailable. All nine issues remain
open for client acceptance; #252's earlier legitimate numbering-data dependency
is unchanged. No Bible-Resources change or generated study content is included.
