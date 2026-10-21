# Temporary commentary coverage (#45)

The active SWORD entry supplies its actual start/end, mapped with the verified
resolver. A paint-only dotted underline covers all matching Bible verse text,
including wrapped lines, both comparison panes and Bible pagination. It does not
select text, fill a background, modify layout/words or create a saved annotation.
An introduction, unknown mapping, missing entry or hidden study clears the cue.
The exact Bible anchor is retained when already inside an entry's range.

`ContextTextView` appends one-pixel dots to GTK's snapshot using native character
rectangles. It scans only visible display lines, handles RTL rectangles and uses
palette-appropriate neutral colors; high contrast uses full contrast. Native
selection and personal-highlight foregrounds take precedence for legibility.
The cue sits below glyphs and is independent of Show highlights and saved colors.
No extra preference, file, server or sandbox permission is introduced.

The existing study coordinator is retained. Only clearing/refreshing the visual
range and updating the current source reference/actions are added to its paths.
Actual entry links determine ranges; references mentioned in prose are ignored.

Validation: targeted study/pagination/indicator tests pass, including an actual
linked synthetic range 1:2–3, complete range painting, unchanged buffer/selection,
no annotation persistence, introduction clearing and hide/reopen behavior.
Real offline FreSegond1910/MHC Genesis 1:1–2 and a differing-versification Psalm
case pass in `tools/check_context_indicator.py`; Lausanne paints its independently
mapped coverage. The helper also checks Bible pagination and emulated high contrast.

Actual GTK captures: [light](captures/context-45-light.png),
[dark](captures/context-45-dark.png),
[emulated high contrast](captures/context-45-high-contrast-emulated.png),
[pagination](captures/context-45-immersion.png).

Personal-highlight overlap was also checked on the separately reviewed PR40
candidate `3496f1a`: 148 tests and real native overlap/hide-show/immersion pass.
Evidence: `captures/context-45-personal-overlap-review.png` on that branch.
Personal highlights are not a feature of current main or the public alpha. In high contrast a
personal highlight's double underline and this dotted cue can coexist; neither
changes the other's state. Manual GNOME/Wayland, live desktop high contrast and
assistive-technology acceptance remain distinct from these Xvfb checks.

Published in final source `08a00d2`, CI 39631126308/publication 39632604890
green, revision 39632604890-2; actual system alpha update verified against
public provenance with unchanged signing fingerprint. Captures now show the
client-corrected right drawer. See `ALPHA_OVERNIGHT_HANDOFF.md`. No issue is closed merely from
the presence of this visual cue; #25 retains its remaining acceptance criteria.
