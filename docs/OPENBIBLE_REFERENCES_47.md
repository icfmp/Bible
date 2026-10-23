# Offline passage references (#47)

The native Passage study drawer adds **References** beside Notes and
Commentaries. Notes also shows three suggestions from the same current-passage
results. OpenBible relationships are an optional Library → Study resources
download, separate from installed SWORD translations and personal annotations.
No account, AI service, developer key or additional runtime is required.

## Audited source and numbering

- Source: <https://www.openbible.info/labs/cross-references/>.
- Download: <https://a.openbible.info/data/cross-references.zip>.
- The source page links to [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  The actual TSV header is `From Verse\tTo Verse\tVotes\t#www.openbible.info CC-BY 2026-10-19`.
- ZIP SHA-256: `5f61f4525156b7c7b8f7ae07e3a4225038cf4b60def39247df8b92916e14c56f`.
  The 1,983,329-byte ZIP contains one 8,302,897-byte `cross_references.txt`,
  with **344,799 directed relationships** and community scores. No English ESV
  quotations are imported, stored, or shipped.
- The 66-book reference space is **ESV-style, not unqualified KJV**: 3 John has
  15 verses. All other chapter sizes agree with the existing KJV canonical
  address data. The publisher's parser at commit
  [`15c9f0993267014d9d3aa81256b9ff5565e58856`](https://github.com/openbibleinfo/Bible-Passage-Reference-Parser/tree/15c9f0993267014d9d3aa81256b9ff5565e58856)
  documents its ESV-style default; its first 66 chapter arrays have been checked
  against that address space. The publisher's 3 John 15 page confirms the split
  greeting. This audit does not import the JavaScript parser or add Node.

Real SWORD checks found a native split-verse error for 3 John (including a false
NRSV 14 → Segond 15 correspondence). The resolver uses the application's already
pinned JSword verse-part tables where both canons match those verified tables.
OpenBible 3 John 14/15 is projected through that verified split convention;
whole KJV 14 correctly covers both. A genuinely unsupported system reports
unavailable alignment rather than guessing. Other books use the verified resolver,
including actual Psalm numbering differences. Each source verse in a selected
range and each destination verse is resolved separately; endpoint-based gap
filling is forbidden. Strict bounds also reject SWORD's otherwise accepted
out-of-range KJV `3John.1.15`.

## Transformation, storage and safety

The Library details, list footer and preview credit OpenBible.info, link its
source and CC BY 4.0, and identify the dataset date/checksum and transformations.
Only relationships and community scores are indexed in a separate SQLite file
under `study-data`. Quotes come exclusively from the active installed translation
and retain that resource's own conditions. Missing text never selects another
translation or triggers an online fallback.

Download is bounded to 8 MiB; expansion to 16 MiB, one exact filename, supported
compression only, no extraction, links or encryption. Header, UTF-8, every
canonical address, ordered range and bounded score are checked. The archive hash
is pinned before indexing. A staged, integrity-checked SQLite index is atomically
replaced only after success; an invalid update preserves the previous index.
Unsupported/corrupt indexes offer repair through the same Library flow. Future
upstream changes require an application update and a new reviewed source pin.

Directed source links are not made reciprocal. Intentional passage selections
aggregate their verse-based links, deduplicate exact destination ranges, and
rank by maximum community score, then canonical destination order. Scores are
community suggestions, not theological authority. The initial list contains up
to five destinations; View all uses a native virtualized list. A background
worker queries relationships; generation/context guards discard stale work after
rapid passage, translation or tab changes. Cached exact excerpts are bounded.

## Shared preview and navigation

A reference click opens one shared native local preview and leaves reading,
history and tabs unchanged. Return/Space activation, Escape and outside dismissal
use the existing popup lifecycle. Explicit current-tab/new-tab actions capture
the selected translation and mapped reference. Missing passage/alignment states
keep both navigation actions disabled. Notes will reuse this component in #50;
plain note text is not yet automatically linked in this delivery.

The three native tool labels fit narrow layouts. Long lists scroll separately
from the reader; theme-native text and source credit remain readable. Changing
passage does not move focus into results. Existing two-way commentary following
remains confined to the Commentaries tool. No inert Original tab is introduced.

## Validation boundaries

Source tests and real native GTK/X11 probes are distinct from installed Flatpak
checks. Receipts record actual downloaded relationships, exact French/English
SWORD excerpts, Psalms, split 3 John, intentional ranges, explicit navigation,
rapid changes, corrupt-update preservation, narrow/dark layouts and restart.
Offline probes disable networking; source tests with local HTTP fixtures retain
loopback. In bare Xvfb, the input harness supplies the window manager's parent
focus handoff after closing Library, then exercises actual pointer/key events.

The PR records exact commits, CI, package audit, measured timings and signed-alpha
update receipts when complete. Local validation branches are internal artifacts,
not a separate installation requested of the client. Actual client GNOME/Wayland
acceptance and in-depth accessibility/assistive technologies are **not tested**
by these automated checks. Bible.com/BDS is outside this delivery.

Recorded checks before PR: **195 source tests** and **60 affected installed-Flatpak
tests** passed. The package audit matches all **73 application files**, verifies
the existing 14 canonical mappings and installed mapping-license notices. Real
Library download/indexing took 5.051 s / 2.604 s on sources and 6.738 s / 3.544 s
in the validation Flatpak. For 250 local queries with 1–5 origins, median latency
was 0.307 ms and p95 0.461 ms (one cold check took 41.471 ms). These are measured
container observations, not performance guarantees. Compact receipts are in
`evidence/study-47/`; installed-package captures are `captures/study-47-*`.
Emulated high contrast is a theme check, not assistive-technology acceptance.
