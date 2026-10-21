# Full-height right study drawer (#44)

The client corrected the side after the first drawer delivery: the complete
commentary drawer belongs on the right, with the Bible on the left.
The existing native OverlaySplitView now contains the complete Bible column and
the complete right commentary column, each with an aligned Header Bar. The rightmost
visible header exposes the native end window controls at every width. Source
choice, Aa, immersion and secondary actions are compact; conditions and Library
remain available. Installed content has no permanent download/instruction strip.

The native show/hide transition moves the entire drawer, including its header.
It follows GTK's animation preference. At narrow widths the drawer becomes the
adaptive view instead of compressing two readers. Its subtle secondary surface
follows the reading palette; high contrast removes decorative blending. Font,
size, spacing and width settings are shared with the Bible, with either Aa panel
resynchronizing the other. No user-data format changed.

## Source rendering and preservation

Actual MHC is OSIS. Inspection showed that SWORD's OSISPlain filter adds `*`
around `hi` elements, including superscript quote numbers and italic emphasis.
These are not blindly treated as Markdown. The formatter verifies the entire
non-whitespace filtered sequence, including literal and generated stars, against
the raw OSIS representation. Only proven decoration ranges are hidden; unknown
conversions fall back to original plain text. Real source headings/paragraphs
and emphasis are rendered safely, without interpreting scripts or external links.

Paragraph replacements retain body length, and decorations remain at their
original hidden offsets. Original-character body positions therefore remain
compatible. Source headings have an explicit body prefix; ordinary/immersive
anchor conversion accounts for that prefix. Native Copy filters proven hidden
decorations and retains literal stars. No downloaded module is edited.

The original MHC Genesis 1:24–25 entry SHA-256 remains
`9b270ff42998dfb9ff04e23dd2f6ab27900f030b3b1db5b6cd85f88c1a0c471c`;
its ten SWORD-generated emphasis markers are verified and styled. Plaintext and
unknown filter output remain untouched. Exact canonical Bible copying is unchanged.

## Validation

140 full local tests passed. Tests cover literal-star preservation, safe fallback,
body-length compatibility, the existing study synchronization and immersion.
The previous right-pane assertions were updated to the approved left arrangement.
Comparison anchors now survive drawer-induced reflow as well.

`tools/check_study_drawer.py` uses a disposable profile with real offline
FreSegond1910/MHC. It checks aligned headers, source/conditions access, shared Aa,
two-way following without history spam, commentary immersion/return without hidden
Bible movement, rapid toggles, actual slide frames and disabled-animation final
allocations. The existing native wheel and >1.5 s scrollbar-drag checker passes.
These are Xvfb checks, not manual GNOME/Wayland or assistive-technology acceptance.

Actual GTK evidence:

- [Light](captures/study-drawer-44-light.png)
- [Dark](captures/study-drawer-44-dark.png)
- [Large text](captures/study-drawer-44-large.png)
- [Narrow](captures/study-drawer-44-narrow.png)
- [Native opening/closing recording](captures/study-drawer-44-slide.webm)

Published drawer increment: source `ef4df7e`, CI 39598544372 and publication
39599447490 green, revision 39599447490-2. An actual system update matched
Flatpak `770f499300b796448ed32bd868446961c9280cdc659051e8de9c400e22307d87`.
The original channel fingerprint was preserved. The latest combined delivery
is recorded in `ALPHA_OVERNIGHT_HANDOFF.md`.

Keep the client's positive GNOME two-way scrolling validation distinct from
this new drawer's manual retest. Verified inline styling falls back to original
plain source for conversions that cannot be proved character-for-character;
not every entry/module is claimed to provide rich formatting.


## Client side correction

After the initial drawer delivery the client explicitly corrected the requested
side to RIGHT. The Bible remains on the left. This follow-up changes only native
sidebar placement, the dismissal arrow and which aligned header shows native end
window controls. Existing study/reference/selection algorithms are preserved.
Updated captures and the slide recording above show the actual right drawer.
The targeted geometry/native action checks pass; final delivery metadata is in
`ALPHA_OVERNIGHT_HANDOFF.md`. Earlier left-drawer screenshots in historical issue
comments are superseded by these captures.


The RIGHT-drawer follow-up is published in source `08a00d2`: CI 39631126308
and publication 39632604890 green, revision 39632604890-2. An actual existing
system alpha update matches public provenance; the signing fingerprint is
unchanged. This does not replace the client's manual GNOME retest.
