# Source structure and heading investigation

Related to #251 and #254. This records application work, not client acceptance
or a release. Only `icfmp/Bible` is changed; resource files are read unchanged.

## Actual resources inspected

- YouVersion21, La Bible du Semeur2015: verified archive SHA256
  `0209c76b6d3598147d348bbbe74f4fc2977fb7ded68d36307cb88b8266f085b2`.
- YouVersion104, Nouvelle Bible Segond: verified archive SHA256
  `4c1cdef48a25bcc9894416a71fe938db0f50270aa9d511293bad398722ca21e4`.
- CrossWire `FrePGR`1.2.2, Bible Perret-Gentil et Rilliet, downloaded using the
  existing installer into an isolated test library. The installed BDS/NBS
  metadata does not declare a SWORD Version; none is invented.

Genesis25:19–26 has real editorial differences. BDS provides paragraph endings
after20 and21 and a paragraph within22; NBS keeps20–22 continuous. Both describe
four poetic lines in23. PGR also supplies explicit line breaks, including two
adjacent `<lb/>` elements before the oracle. Uniformizing their prose would
erase source information and is not the correction.

## Measured application defects and targeted changes

1. The structured parser collapsed PGR's two explicit line breaks as though
   they were duplicate OSIS start/end milestones. Explicit line breaks and
   supplied blank-line markers now retain their count; paired line milestones
   still contribute one boundary. Milestones inside hidden notes cannot insert
   visible breaks into Scripture.
2. A blank paragraph separator occupied another full-size font line, with the
   normal line padding applied again. At28pt, a native test line allocated44px
   for that empty paragraph. The same source newline now allocates11px, with no
   extra empty-line padding. Only whitespace is tagged: body text, source
   boundaries, verse identities and copy offsets remain intact. The same style
   is used by GTK rendering and independent Pango page measurement, including
   whole-book immersion and commentary documents.
3. Inline title fragments could become separate headings, and a title after a
   verse could start on the preceding body line. Contiguous title fragments
   now retain their actual internal text/emphasis and start on their own line.
4. PGR's small-caps/emphasis is represented by additional asterisks in SWORD's
   plain output. Reuse the existing verified commentary decoration detector;
   preserve every authored character and literal asterisk, omit only proven
   native decorations from painting/copy, and retain their native character
   positions for anchors. This text-only style is separate from copy-excluded
   native annotation widgets. A source mismatch still falls back to SWORD's
   exact plain output; missing content is never reconstructed.

No module, conversion archive, dataset, reference registry, annotation or
preference is rewritten. No provider or distribution route is added.

## Separate status of #254

The reported `L'approche de la mort` heading identifies the tested NBS chapter.
The actual chapter/section text is present, with complete glyphs in the initial
GTK4.20.4/X11 tests using Roboto Serif and Roboto at16,28 and40pt: Cairo, software
OpenGL and2× OpenGL captures are retained. These observations do **not** prove
that the client's clipping regression is fixed. No speculative font shrinking,
per-string offset or added clipping workaround is applied. Client font, text
size and desktop scaling have been requested while other work continues.
Wayland/hardware GPU/fractional desktop scaling remain separate validation.

### Client refinement and cautious leading adjustment, 16 November

The client subsequently provided Esdras1/Melchisédek screenshots (F10), then
Genesis13 in BRLSG1910 at13/14/15pt: the defect is reported specifically at14pt.
The client confirmed **Roboto Serif and GNOME100%** and explicitly requested
checking/increasing the heading line height as a precaution. This supersedes
the earlier unknown-font/size statement, but does not establish a root cause.

Installed alpha.32 on GTK4.20.4 was compared at13/14/15pt using the existing
BRLSG1910 resource, Genesis13, Ezra1 and Genesis14. Tests include changing size
without navigation, actual Aa mouse clicks, parallel geometry with Study open,
native Vulkan/OpenGL/Cairo rendering, and additional font-metric/hinting controls.
No matching malformed glyph has yet been isolated in this X11/software-GPU
environment. Normal Pango ink bounds fit inside the measured font boxes;
these geometric observations alone cannot establish client pixel fidelity.

The requested precaution adds **1.15 line height** to shared Bible chapter and
section heading tags, and to immersive Bible/commentary headings. It changes
internal leading, not font family, weight, size, source strings or per-title
offsets. Existing paragraph gaps remain. The independent Pango page planner
uses the same factor so wrapped headings cannot consume unbudgeted page space.
Study-sidebar/source-preface headings already inherit1.5 line height; that
larger allocation is preserved. There is no new timer, renderer or cache.

Native regression coverage compares the old/new allocations at13/14/15/28pt
in both reader fonts with tight/very-airy spacing. It verifies extra paragraph
and wrapped-line room, identical glyph/body heights, unchanged source text and
anchors, and matching extra space in Pango. Pagination, immersive page-end fit,
comparison rows and commentary source fidelity remain separate native gates.
This adjustment must not be described as a reproduced/proven #254 fix; client
acceptance at14pt is still required. CI/publication evidence belongs to the
actual delivery report, not an assumed outcome in this source document.

## Validation

Focused tests exercise paired/explicit breaks, blank-line allocation in real
GTK/Pango, composed titles, literal stars, note boundaries, copying and canonical
anchors. Native annotation clicks are tested in a fresh composited X11 session;
the installed-alpha baseline and changed source both pass those gestures.
Genesis25 before/after captures use the actual installed alpha as baseline and
the changed application source on the same GNOME49 runtime. The broader
installed-runtime suite, final CI, packaged validation and signed publication
are delivery gates; do not infer their completion from this document.

### GTK4.14 passage-following regression found by CI

The native chapter-notes wheel check failed deterministically in Ubuntu's
GTK4.14.5/libadwaita1.5, while the same check passed on GTK4.18 and4.20. The exact
older libraries and pinned reader fonts reproduced it locally: at scroll1127px,
the stored passage stayed Acts1:4 while the settled viewport began at Acts1:3.
Styling the selected verse number invalidated GtkTextView's lazy line layout
after the coordinator had already consumed its scroll intent. No subsequent
input meant no final synchronization request.

Selection now requests one bounded recheck through the existing layout gate.
It waits for the existing reflow frames, does not change native scroll physics,
and creates no permanent polling/tick. The same older-GTK native wheel case now
settles at Acts1:3 in both state and viewport; reverse wheel, draft ownership,
stable note cards, focus and history also pass. Required CI still remains a gate.
