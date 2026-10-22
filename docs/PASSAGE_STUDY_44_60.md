# Passage study (#44 / #60)

The updated 22 October brief and client's supplied mockup define one native right
drawer. The Bible stays on the left. Aligned Adwaita headers, continuous secondary
surface, F9 and the native animated/adaptive OverlaySplitView remain. Native tool
tabs expose **Notes** and **Commentaries**; References follows with #47. No inert
Original tab or fabricated cross-reference teaser is shown.

## Typography and resizing

Docked commentary uses native sans-serif at **12 points and 1.5 line height**,
independent of Bible Aa typography, column width and decorative palettes. Native
sidebar ink follows light/dark and high-contrast themes. Point sizing honors
desktop text scaling. The single global Aa still controls Bible/comparison and
existing immersive reading, without another commentary settings panel.

Drag the native 8-pixel separator, or focus it and use Left/Right (32 pixels) or
Home (default 420). Width and selected tool are atomically stored in a separate
`study-preferences.json`; unknown versions remain untouched. The desktop drawer
leaves at least 480 pixels for the Bible area. Existing comparison adaptation
supplies its single-column fallback where two readable columns cannot fit.
Narrow windows use the established overlay. Automatic clamping never replaces
the preferred desktop width. Closing during a held drag safely ends resizing.

Reflow retains reading anchors and native selection. Scroll-driven following
pauses during resize and while Notes is selected; returning to Commentaries
follows the actual passage. The temporary dotted commentary cue is absent from
Notes and is never stored as a personal highlight. Existing commentary immersion,
source choice, conditions, source headings and verified emphasis remain.

## Annotations and source capabilities

Notes shows multiple overlapping verse/range notes, safe native Markdown previews,
labels and dates. Add/Edit reuse the existing captured-target note editor, save/
discard guards and conflict handling. My notes remains the global workspace.
Long previews and initial lists are bounded without editing stored content.
Native highlight menus create, recolor and remove actual personal marks through
the existing store, with excerpts from the displayed local Bible.

The verified resolver projects existing annotation identities into the displayed
translation, including renumbered Psalms, without migrating their original data.
Every source verse of a note range is resolved independently; no endpoint-based
gap filling or guessed correspondence is allowed. No data-format migration occurs.
Reference teasers and clickable note citations remain #47 and #50 respectively.

Actual installed John 3:16 OSIS inspection found lemma and morphology attributes
in KJV, lemma attributes in FreSegond1910, and neither in the inspected eBible JND
entry. This is not a usable Original study implementation. Verified token/source
alignment, suitable lexicon coverage and faithful presentation remain future work;
no morphology or explanation is invented.

## Verification and delivery boundaries

- **Sources:** 184 tests passed with local HTTP fixture servers enabled. Targeted
  reviewed checks cover typography, annotations, widths, synchronization and
  comparison. The real-resource native X11/Xvfb probe runs offline and exercises
  pointer/keyboard resizing, F9 during a held drag, selections, menus, captured
  drafts, narrow/wide/comparison layouts and restart. Emulated 150% desktop text
  scaling increased the measured native line box from 19 to 28 pixels.
- **Installed Flatpak:** checked independently with application imports asserted
  under `/app`, GNOME 49 and actual FreSegond1910/KJV/MHC. The native probe disables
  networking. A separate affected-package regression receipt records its results.
- **Publication:** local builds are validation artifacts. The PR records the exact
  reviewed commit, green CI, signed alpha provenance, actual old-to-new update and
  controlled-profile preservation after the normal publisher succeeds. No new
  public channel or separate client installation is required.

These are automated GTK/Xvfb checks, not manual acceptance on the client's GNOME/
Wayland desktop. In-depth accessibility and assistive-technology acceptance are
deferred and **have not been tested**. Bible.com/BDS remains outside this increment.

Package captures: `captures/passage-study-44-*`; compact receipts:
`evidence/study-44-60/`. Existing MHC Genesis 1:24–25 source SHA-256 remains
`9b270ff42998dfb9ff04e23dd2f6ab27900f030b3b1db5b6cd85f88c1a0c471c`.
