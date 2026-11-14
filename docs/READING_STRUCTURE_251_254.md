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

## Validation

Focused tests exercise paired/explicit breaks, blank-line allocation in real
GTK/Pango, composed titles, literal stars, note boundaries, copying and canonical
anchors. Native annotation clicks are tested in a fresh composited X11 session;
the installed-alpha baseline and changed source both pass those gestures.
Genesis25 before/after captures use the actual installed alpha as baseline and
the changed application source on the same GNOME49 runtime. The broader
installed-runtime suite, final CI, packaged validation and signed publication
are delivery gates; do not infer their completion from this document.
