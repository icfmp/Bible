# Study and navigation follow-ups

Related to #165, #171 and #179–#184. #184 was already closed as a duplicate;
its reproducer is covered with #171 without changing that decision. #159,
#97, #114 and #152 are not reopened. Translation-note styling is recorded
separately in #185 and is not implemented in this batch.

## Measured causes and changes

- Library repeated transfer information in the row, progress bar and status.
  Its active footer now has a divider, phase, captured resource name, one slim
  progress indicator/percentage and a Cancel action. Unknown totals and
  conversion/verification remain explicit. The row hides its inactive action
  during that job. Completion removes the footer, retaining the brief native
  toast and actual installed row. Failure/retry ownership remains independent.
- The reference preview imposed a 160 px text minimum and a generic status.
  Natural-height text, bounded viewport width, responsive adjacent/stacked
  actions and linked source/license credit replace those redundant elements.
  Unmapped triggers cannot open an orphan popup outside the window.
- The reference list's initially lone footer remained GTK's scroll anchor
  when actual cards were inserted above it: the real Psalm 34:18 baseline
  opened at 335/335 px. A new passage requests the first item once, after
  allocation. Tool activation no longer rebuilds an unchanged context/index.
  Same-context manual scrolling is preserved. Calling GTK 4.18 scroll_to before
  first allocation also produced invalid INT_MIN-sized requests; an isolated
  probe confirmed their absence when that early call was suppressed. The
  corrected lifecycle uses one guarded idle request, with no polling loop.
  A delayed same-passage data refresh also emptied the model, leaving the
  footer as anchor: a native regression moved from 250 to 2,501 px. Keeping
  existing rows until the replacement arrives preserves GTK's anchor without
  saving/restoring pixel positions. Missing/failed data still clears the list.
  Native loading-label allocation may adjust row estimates by a few pixels;
  broader GTK 4.18 tests still emit some transient allocation warnings.
- Theme passages reuse the References card builder. Back, topic and actual
  count share a row; the native back icon retains an accessible All themes
  name. The list has its own viewport above the source control so its final
  card can be fully revealed. Literal search and ranking are unchanged.
- Original text starts with source words grouped by selected verse, not an
  empty verse chooser. Hebrew/Aramaic words flow right-to-left; source-order
  tokens, diacritics and verse boundaries are retained. Word details and
  paginated occurrences are separate views with Back. English glosses remain
  explicitly English and describe possible senses, not the translation.
  Raw headers were already stored as metadata but were reinserted into the
  dialog's Source notices/Details: that presentation path is removed. Credits
  and license links remain visible, and original headers remain in the index.
  The parser now classifies complete numeric token keys and lexical-ID fields.
  TAHOT's documented gloss/sub-meaning/person-address syntax is decoded on read
  for existing indexes; there is no database migration or required redownload.
  The selected-translation context is a compact two-line excerpt with display
  whitespace collapsed; full source text and the immutable selection remain
  unchanged. This leaves original words visible immediately in a 360 × 480
  dialog rather than consuming its height with explicit paragraph breaks.
- The contextual comparison action lists actual translations/download-more
  when off, and exits directly with a crossed-out symbolic icon when on.
  The secondary pane's selector continues to change its translation. Tab and
  session synchronization uses the actual state; primary reading is retained.

## Storage numbering versus reference capabilities

The measured Semeur/NBS Psalm 33 failure reports
`No verified alignment: Original Ps.33.1 / YouVersion104`. Both chapters exist;
the exact NBS storage index had no registered semantic mapping capability.
This is separate from the old first-chapter fallback corrected in alpha 22.

Reference capability is derived from the verified source convention (`org` /
Original, `eng` / English KJV), its exact registered native inventory, and the
existing pinned mapping tables. A complete matching inventory alone is never
sufficient: a supported declaration, matching storage identity, digest-checked
index and successful full source readback receipt are required. Addressed split
sections, incompatible inventories and unknown conventions do not gain a map.
Existing explicit edition mapping tables retain priority. No edition-ID, title,
language, sample passage or scroll-ratio branch is added.

The dynamic storage name, module files and personal references are unchanged.
The shared table resolver can reuse the established convention only after those
checks. Current NBS's entire inventory matches Original. Cross-system splits,
merged verses and unsupported verse parts continue through the existing native
and pinned-table contracts. A shared padded-row failure is now distinct from
failure to map the current verse: reference following remains available where
verified, and a genuine unmapped location stops locally. Independent positions
remain resource-qualified and are not overwritten to manufacture alignment.

Inputs: source `vrs` retained by the metadata adapter, `.verified.json` and
`.source-versification`; existing [SIL provenance](../third_party/libpalaso/provenance.json)
and [Original bridge generator](../tools/versification/original.py).
TAHOT's pinned file headers document `»` sub-meanings and `@` named-person
addresses; see [STEP audit](STEP_WORD_STUDY_AUDIT.md) and `step_sources.py` pins.

## Verification state

Local GTK 4.18.6/Cairo checks use a disposable developer profile containing real
CrossWire KJV, FreSegond1910, FreJND and YouVersion 21/93/104 resources. Ten
directional cases cover Genesis 11, Psalm 33, Psalm 3:1/3:2 and Genesis 31:55 /
32:1. Native wheel gestures check mapped body/group anchors, not identical
pixel offsets or unqualified printed numbers. Merged title/body groups may
have different first visible native iterators while their group anchors align.
Light/dark and 360 px previews, theme final-card bounds and passage → Hebrew
word → occurrences checks are exercised. Existing module hashes and notes are
retained. Full pinned STEP parsing preserves 137,992 Greek tokens, 305,465
Hebrew/Aramaic tokens and 11,035 Greek lexical records.

These are implementation/developer checks, not a publication receipt. Exact
candidate CI, installed Flatpak/OpenGL checks, offline restart, signed update
with retained data and numbered alpha publication remain delivery gates.
Original screenshots are private. Client GNOME/Wayland, assistive technologies
and long-session hardware performance remain separate acceptance checks.
Keep implementation issues open; only the client marks Done. Project 5 access
currently returns Resource not accessible by integration.
