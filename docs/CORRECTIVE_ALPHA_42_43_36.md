# Corrective alpha after the client's GNOME test pass

The client manually validated Bible ↔ commentary scrolling on GNOME in `4a285f3`.
That core behavior is preserved. This does not close all #25 acceptance criteria.
This increment addresses #43, #42, #12/#15 and #36 before the drawer redesign.

## Changes and evidence

- #43: X11 reproduced the Aa failure after selecting a nested spacing choice,
  although simple opening/outside-click cycles passed. The parent popup's native
  modal grab could remain ineffective after the nested popup finished. Reading
  popovers now keep native content/dropdowns but use parent-surface dismissal,
  trigger toggling and Escape rather than keeping a modal parent grab. The
  dismissal click is consumed so it cannot also navigate. Comparison selection
  closes its outer chooser after native dropdown activation finishes. Aa stays
  open for further adjustments. `tools/check_popover_dismissal.py` exercises
  repeated pointer/keyboard cycles and all four spacings; it also runs in CI.
- #42: a selectable GtkLabel selected its entire contents when receiving focus
  (424 characters in the minimal reproduction). The metadata label now clears
  that focus-time selection, retains intentional selection/copy and initially
  focuses Back. Provider metadata with doubled backslashes and `par` immediately
  followed by a capital is normalized into paragraphs without deleting words,
  attribution or conditions. Unknown control words are retained.
- #12/#15: **14 pt / Very airy / Narrow** for new, missing and reset values;
  explicit saved choices survive. Shared scalable gray verse markers use body
  font metrics instead of a fixed rise. High contrast uses full-contrast numbers.
  Marker/first-word spans use nonbreaking presentation spaces, including the real
  source's leading thin-space case found in John 3:23. Display offsets retain
  their length; document copy text and native Copy restore the original
  characters. Canonical verse copying/export still reads exact SWORD text.
- #36: both Bible panes use one structured renderer, retaining each resource's
  own headings, paragraphs and words. A separate comparison coordinator reuses
  input observation without replacing the study coordinator. Actual input picks
  the leading pane; canonical references use the verified native resolver, never
  percentage alignment. Reflow/geometry/programmatic movement does not become
  user intent. Same-chapter following retains the buffer, selection and history.
  Missing mappings show an error and clear stale follower text.

## Checks

The full local suite passes 138 tests. Additional native X11 checks cover passage
and Aa input, all popup cycles, immersive input, and the existing two-way study
wheel/long-scrollbar behavior. This is **not** manual GNOME/Wayland acceptance.

Real offline resources: FreSegond1910, FreLSN1872 (Lausanne), MHC. Comparison
alternates wheel leadership through Genesis 1:8, 1:15, 1:22 and 1:28, without
adding history entries. At the chapter end the primary scrollbar can clamp;
the mapped verse remains visible and the current canonical reference is correct.
Equal pane allocation and selected-text preservation after font reflow pass.
Existing resolver tests retain differing-versification/Psalm coverage.

Helpers `tools/check_comparison_sync.py` and `tools/check_corrective_ui.py` require
a disposable TEST profile with real downloaded resources. Never run them against
the client's personal profile; the latter intentionally resets reading settings.

Actual GTK captures:

- [Reading and complete verse markers](captures/corrective-12-reading.png)
- [Aa](captures/corrective-43-appearance.png)
- [Unselected resource details](captures/corrective-42-details.png)
- [Comparison light](captures/corrective-36-light.png)
- [Comparison dark](captures/corrective-36-dark.png)

## Delivery boundary

Published source `d48c760`, CI **39591287215** and alpha publication
**39592269695** are green. Revision **39592269695-2** was installed by the
existing system client through the public signed channel, matching Flatpak
`4825d1f2e23e11edbaede22c342771af5dd5ccbc05f98e0272f2e17b7a735d9a`.
Constructed packaged `/app` code passes native popup and real comparison checks.
No signing key or channel URL changes.
Pending PR38–41 are not merged. PR39 needs these typography/copy changes integrated
and checked against its worker pagination. PR40 remains the personal-highlight
review; #45's temporary indicator must remain separate. PR41 remains unpublished
until product-manager review. #26 stays excluded; #28 retains manual guidance.

Client retest order: popup pointer/keyboard dismissal after nested choices;
unselected/copyable resource details; new/reset defaults and preserved old choices;
marker wraps/copy in ordinary and immersive reading; two-way Segond/Lausanne
scrolling and selection; then the already-working Bible/commentary scrolling.
