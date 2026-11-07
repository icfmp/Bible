# Resource alignment capabilities and regression #215

## Demonstrated causes

The regression was reproduced before application changes at alpha.25 source
`c7009d0162c0b2b85cc8f99e5b024e17e764bd3e`, with fresh YouVersion PDV2017
(133), S21 (152), NFC (2367), installed CrossWire LSG and MHC. Both comparison
directions opened Genesis 1 but the three editions could not follow it. MHC
worked with LSG primary and became unavailable with each reported edition.
The first reproduction used native GTK 4.18.6/X11/Cairo, not the packaged runtime.

Two shared capability checks were responsible:

1. `source_versification` required a complete source canon to equal a supported
   convention and rejected every resource carrying a source-address index.
   S21's Numbers 25 maximum differs from Original (18 versus 19). PDV/NFC also
   include additional canonical books and transformations in particular books.
   These local differences revoked Genesis and Psalms capabilities globally.
2. `versification_mapping.table` inspected native bounds with automatic
   normalization enabled. NFC's Greek Daniel index has genuine zero-verse
   chapter slots. Asking SWORD for chapter 1 silently moved to chapter 3 and
   reported 90 verses; asking for chapter 4 moved to chapter 13 and reported 64.
   This made the unchanged verified index appear inconsistent. Disabling
   normalization during index inspection returns the real bounds, including 0.

The displayed Genesis chapter was not missing, and MHC's content was present.
No SWORD engine replacement, new numbering tables or translation-specific UI
workaround is needed. Existing native SWORD mappings and pinned JSword-derived
tables retain their separate responsibilities.

## Shared correction and evidence boundary

Keep each installed system name, private storage coordinate and public source
identity unchanged. A source-specific index may reuse an existing convention
only for an independently compatible **whole book**. The capability requires:

- A supported explicit source numbering declaration (`org` or `eng`), not the
  language, translation title, ID or similar-looking printed references.
- The verified conversion receipt and unchanged reference-index hash, with
  the declared storage system equal to the registered native system.
- The entire book's chapter bounds matching the explicitly declared convention.
  An equal individual verse or chapter is not sufficient.
- No source chapter-section or overlapping-unit transformation in that book.
  Source-address metadata is loaded through the existing hash-verified adapter.
- An independent native full-storage-index comparison, with normalization off.

The existing table bridge delegates only covered books to the declared
convention. Forward and reverse lookups both reject uncovered books. Unknown
declarations, unverified/missing/corrupt metadata and incompatible native indexes
do not gain mappings. A changed declaration revokes previously cached capability.
The existing bounded registration/table caches own lifetime and invalidation;
no polling, per-frame index scan or new cache framework is introduced.

Matching dimensions **alone** are not semantic proof. This correction reuses
the source's explicit convention only inside its independently checked scope;
it does not relabel the source as that convention. Neither chapter availability
nor an available nearby verse is substituted for exact correspondence.

## Deliberate local limits

For the measured archives, S21's Numbers book remains unverified. PDV's
Zechariah has overlapping units, and PDV/NFC Acts differs at chapter 19;
those books remain unverified. Additional/sectioned deuterocanonical books do
not inherit a correspondence merely because some printed numbers match.
The policy is conservative for the entire affected book until additional
documented mapping evidence exists; it does not certify the other chapters in
that book by matching their dimensions in isolation.

Ordinary reading and available-chapter independent comparison remain usable in
those locations, with truthful labels/status. No Genesis 1 fallback or guessed
equivalence is added. Source fragments, headings, introductions, reference order,
stored annotations, translations and preferences are not rewritten.

Existing verse-part distinctions remain intact: for example, the audited YV93
bridge can return Psalm 3:1–2 for an unqualified first-verse input, whereas a
native SWORD route can return only the spoken verse. Tests must preserve these
documented ranges rather than force identical printed numbers everywhere.

## Verification

`tests/test_declared_reference_convention.py` covers both directions, changed
books versus unchanged books, partial/extended canons, transformed public
addresses hidden behind identical native dimensions, zero-verse chapter slots,
unsupported declarations and cached-capability revocation. Existing native and
pinned-table tests cover real numbering changes, split/merged/disjoint ranges,
missing verses and introduction handling.

`tools/check_alignment_regression.py` uses a marked disposable profile with nine
real Bibles across CrossWire/YouVersion and MHC/Wesley. Its matrix checks all 72
ordered resource pairs, independently expected ordinary/Psalm references,
chapter-boundary shifts and exact superscription ranges, actual GTK chapter
opening and translation changes, alternating native wheel input in both panes,
commentary switching, saved-session restoration and offline reruns. It checks
annotation identities/content, preference bytes and resource-file hashes.
The baseline option explicitly requires the reported failures on unchanged
alpha.25. Screenshots and JSON name the actual imported source/runtime; this
document does not claim a candidate or signed release passed before it did.

Final CI, installed Flatpak results, source/build/publication provenance and
remaining platform limits belong to the issue and numbered release evidence.
Cloud X11 checks do not certify the client's GNOME/Wayland or hardware GPU.
