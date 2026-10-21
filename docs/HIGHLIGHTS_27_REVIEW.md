# Simple passage highlights — storage and UI review candidate

Proposed presentation: choose Yellow, Green or Blue from a verse/selection's
context menu; remove a mark there; use Highlights in the existing main menu to
find/open marked passages. Aa's Show highlights checkbox hides paint without
deleting records. This is a small passage-mark feature, not an expanded notes
or annotation library. It is isolated for review before publication.

## Persistence/backup design

- New `highlights.json` in the existing local application data profile, schema
  version 1. Notes SQLite, labels, sessions, downloaded modules and existing
  note backups are unchanged. No migration or network service is introduced.
- Identity is `(versification, canonical verse)`; the original resource ID is
  context for reopening, not the identity. A range is stored as its actual
  verses; the same verse can have one color. Different systems are never
  painted by pretending their identical numbers correspond.
- Writes use a flushed/fsynced temporary file and atomic replacement. File
  and in-memory state change only after successful replacement. Input size,
  entry count, references, resource IDs, colors and exact schema are validated.
- Corrupt/unsupported primary files are kept untouched and read-only. They
  require repair before saving; no silent reset to empty or destructive
  migration occurs. Invalid backup imports do not alter valid current data.
- The highlight list's secondary menu exports a JSON backup through the native
  file chooser. Restore is explicitly confirmed and merges without deleting
  unrelated current marks; backup colors win for matching verses. These are
  highlight backups, separate from the existing note-backup command.

## Fidelity/accessibility

Only GTK paint tags are added. Scripture words, canonical ranges, selection,
notes and reading anchors are not rewritten. Ordinary reading, comparison and
Bible immersion paint the corresponding source's actual reference spans.
High contrast temporarily replaces decorative colors with the current high
contrast palette and a double underline, while preserving the stored color.
List rows include the color's localized name, not a color-only indication.

Opening a mark uses an installed translation in the mark's exact system. If
none can open the reference, the mark is retained and the limitation is shown;
the app does not silently display another verse or discard missing resources.

## Actual checks and limits

139 local tests passed: atomic failure, corrupt/future schema retention,
backup/merge, source-independent canonical identity, missing systems,
selection/history preservation, hide/show and emulated live high contrast,
alongside the existing note/session/reading suites. Real offline FreSegond1910
John 3:16–18 was marked in three colors, hidden/shown and restored from backup;
the source display text stayed exactly unchanged. Real GTK/Xvfb screenshots
are committed in `docs/captures/highlights-27-*-fr.png`.

Persistence/UI review, candidate Flatpak CI, the file portal on actual GNOME,
screen readers and the client's manual high-contrast checks remain separate.
This feature is not in the published alpha until review, merge and verified
publication. It is compatible with the book-document span model in PR #39;
the combined branches still require an integration check after review.

## Coordination with the corrective alpha (21 October)

Main through `d48c760` is merged into this review branch without merging the PR
into main. The shared ordinary/comparison renderer retains each pane's exact
reference ranges and reapplies personal highlights after a genuine document
rebuild. The independent comparison coordinator and the client's validated study
coordinator remain separate. The new typography/defaults and original-character
native Copy are retained. No highlight schema or backup migration was added.

143 local tests pass. The real offline highlight helper also verifies three
FreSegond verses, unchanged source words, hide/show without deletion and
backup/merge restoration. This is not yet a published feature. #45's temporary
commentary indicator must never be stored here or controlled by Show highlights;
#46 must snapshot its source/range and use this store only after required review.
Those subsequent UI changes are not claimed by this coordination commit.

## Drawer and contextual actions integration

Main through `f8395bc` is now merged into this review branch. All 148 tests pass.
The real offline native pointer/keyboard action probe applies Yellow through the
floating bar in the second Bible and verifies the recorded Calvin versification,
Lausanne resource and exact references. The frozen selection remains available
for Copy, Note and Compare. The actual MHC coverage probe confirms dotted temporary
coverage in both Bibles, mapped Psalms, immersion and coexistence with a personal
highlight. Hiding personal highlights leaves the temporary cue intact.

Real GTK screenshots: `captures/actions-46-highlight-review.png` and
`captures/context-45-personal-overlap-review.png`. These are automated Xvfb checks,
not manual GNOME validation. The store/schema and signed channel are unchanged.
PR #40 still requires review: the public main build intentionally has no Highlight
action until this dependency is approved and merged. Nothing here is published.
