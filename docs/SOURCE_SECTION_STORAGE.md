# Explicit source sections and overlapping verse fragments

Related to #153. This describes the implementation under review, not a published
NFC installation receipt. Signed Flatpak installation and client acceptance must
be reported separately.

## Demonstrated source structures

NFC edition 2367 metadata marks both `SIR.1` and `SIR.1_1` as canonical, with
printed chapter label `1`; their texts differ. The former contains a translator
preface, but its heading is not permission to change the metadata's canonical
flag. `SIR.INTRO1` is a separate, explicitly noncanonical introduction.

The same archive presents Sirach 43 in the order `17a, 16, 17b`. Sirach 44 has a
shared `22+23` unit followed by the continuation of 23. Identical complete native
linked entries cannot represent that partial bridge. Grouping all text of 17
into one display block would also change the source order.

These observations come from a complete 1,424-file source audit of archive SHA256
`ba907f83af7826abf134da92dba4e8cbbc5e12f4c2a45ad511270ce04c072fd0`.
No source corpus or actual translation is included in the repository.

## Common representation

`source_sections.py` preserves explicit section IDs, printed labels and canonical
flags. Only books with demonstrated overlapping physical sections need private
chapter storage slots. Existing disjoint sections continue to join into their
numbered chapter. No edition ID, book number or heading selects an exception.

`source_units.py` describes anomalous chapters as ordered units, each carrying
the explicit source verse IDs that cover it. A verse can cover several units;
a unit can cover several verses. The reference-only `.source-addresses.json`
file is bounded, validated and bound to the installation verification receipt
by SHA256. It contains no text and is about 6 KiB for the demonstrated NFC.
Ordinary chapters retain their existing storage path.

Conversion preserves all ordered semantic nodes while assigning private native
slots. The existing compiler inventory, text, note, heading and semantic-role
checks remain mandatory. The public key adapter exposes stable source IDs such
as `Sir.1_1.1`; native slot numbers must never become note, session or citation
identities. Reader discovery still uses index lookups, not full-corpus decoding.

The reading document retains one span per presentation unit, its source members
and per-member character bases. Repeated fragments have distinct anchor positions.
Copying complete verses deduplicates shared units and retains presentation order.
Exact search indexes complete logical verses, with independent row positions so
partially shared aliases do not collide. Highlights cover every matching fragment;
personal-note markers appear once at the final relevant fragment.

Comparison row construction includes every fragment once in source order. If
shared rows would regroup interleaved fragments, it rejects that layout and uses
the established independent-pane comparison instead. There is no inferred
cross-edition equivalence for the NFC source-specific numbering.

## Persistence and validation

Existing numeric references, SQLite schema, preferences and translation files
remain unchanged. New source-section references remain explicit in annotations,
sessions and backups; reference metadata is retained when a resource is removed.
An older application cannot interpret a new section ID and may reject that
backup; do not replace its IDs with private storage coordinates for compatibility.
Conflicting retained native numbering/index metadata still stops installation
instead of reinterpreting existing annotations.

Neutral tests compile the overlapping sections, interleaved verse fragments and
partial bridge through the real SWORD compiler. They check public/native keys,
text search, exact anchors, copy, highlights, markers, comparison layouts and note
backup/restore. The independent DOM oracle does not consume the converter's
semantic document. On the actual archive it verifies 1,340 canonical chapters,
76 introductions, 35,277 ordered units, 9,417 canonical-chapter notes (bodies and
locators) and 4,021 canonical-chapter headings. The ordinary full compiler check
also covers introduction editorial content. A separate reader/body comparison
covers 4,160,340 non-whitespace characters with no mismatch and 11,606 positions
in the four sensitive sections. These are local developer checks; installed
Flatpak GUI, actual Library download, offline restart, retained-profile update
and publication remain required before declaring the issue delivered.
