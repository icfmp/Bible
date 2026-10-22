# Comparison interoperability — resumed after signed alpha publication

## Delivered prerequisite; separate working branch

PR #61 was reviewed and merged as `87b9803eebf56fbd3acaa1e3c6b9cfd8f5d60d0b`.
PR CI `39759284053`, main CI `39761313126`, and signed publication `39762295612`
all succeeded. The existing `bible-alpha` remote and `//alpha` ref now serve
`f876b328b4777182cdb499dd7cb617d328cdb30a6ada042f7a3f15560aea3294`.
The signing fingerprint remains `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.

An independent client updated from the previous public alpha `1d272b6` to this
commit with GPG commit/summary verification enabled. All 31 hashes in the
controlled profile survived the update; actual notes, preferences, two tabs,
highlights and three resources reopened in the upgraded GTK application offline.
The public source archive and CI bundle matched provenance. See
[update proof](evidence/comparison-57-resumption/alpha-update-proof.json) and
[provenance](evidence/comparison-57-resumption/alpha-provenance.json).
The test profile was disposable; no client personal profile was accessed.

The client explicitly authorized continuing #57 without waiting for desktop
acceptance. #24 remains open. Work here is isolated on
`feat/57-versification-interoperability`; it is not part of the published alpha.

## Actual signed-package reproduction

New disposable resources include eBible `frajnd2024eb` 2.17 (Luther),
`fraLSG1910eb` 99.0 (NRSV), `frasbl2022eb` 170.0 (NRSVA), CrossWire
`FreLSN1872` 1.0.1 (Calvin), and `GerBoLut` 3.0 (German). Their original terms
are retained in [resource metadata](evidence/comparison-57-resumption/resources.json).
No complete resource text is committed. These are backend downloads, not a claim
of fresh UI-installation acceptance.

The actual published alpha was probed with networking disabled and application
imports under `/app/lib/bible-python`:

- Every sampled John 3:16 text matches an independent direct SWORD read.
- Darby/JND reads alone, but Segond/Luther and Luther/Segond comparison fail.
- NRSVA and German also expose missing cross-system capabilities.
- KJV/Segond and NRSV/Segond resolve through the existing native path.
- The GTK probe reproduces empty comparison panes and explicit errors.

[Read-only resolver results](evidence/comparison-57-resumption/signed-reproducer.json)
and [GTK results](evidence/comparison-57-resumption/signed-ui.json) record the
exact installed commit. This is reproduction of the open defect, not acceptance
of a correction.

## First shared-path correction on this branch

The comparison refresh stamp previously omitted the primary resource/system.
Changing only the primary Bible at the same printed reference could retain a
previous mapping error or a previous Psalm target. For example, after Darby
failed against Segond, switching the primary to Lausanne could leave the stale
Luther/Segond error instead of rebuilding the supported comparison.

The stamp now includes the primary resource identity and versification. Two GTK
regressions verify recovery from a previous unsupported pair and recalculation
from KJV Psalm 3:2 to Segond Psalm 3:2, whose KJV target is Psalm 3:1.
Both fail when the published refresh method is restored, and pass with this
branch. The fixture text is explicitly synthetic.

Validation: five targeted comparison/reference tests pass; the full native
source suite passes **177 tests**. An initial run failed an existing following
assertion; its unchanged rerun and full suite passed. That initial log is kept
as a timing observation, not silently counted as a pass.

A fresh source-only offline GTK probe with the actual downloaded resources now
restores both Lausanne/Segond directions and reports the correct German error
instead of retaining the previous NRSVA error. See [source UI results](evidence/comparison-57-resumption/source-ui.json).
This source correction has not been built or published as a Flatpak. The missing
Luther/NRSVA/German mappings are still explicit; no name exception or approximate
same-number alignment is introduced.

## Recovered mapping inputs and independent upstream execution

The examined AndBible commit `7e73c11508f32e4f531d531f6d5b110dd2a1f204`
contains the JSword gitlink `6ebd10a005fa7761e611c048ececea1430e22546`.
This pins the inspected source tree; it does not establish the exact version of
the client's previously reported AndBible installation.

The recovered JSword tree contains its registry, all 12 properties tables,
conversion implementation, canon definitions and tests. Paths/hashes and the
archive hash are recorded in [source inventory](evidence/comparison-57-resumption/upstream-source.json).
The relevant code/data declares LGPL 2.1 or later; no upstream implementation or
mapping table is added to the application in this increment.

A local Java 21 compiler built the pinned upstream source with its declared
library versions. The three targeted upstream mapping suites pass **39 tests**,
separate from Bible's tests. The dependency hashes and reproducible runner are
retained. An actual upstream mapper probe produces:

| Source | Reference | Target | Upstream result |
| --- | --- | --- | --- |
| Luther | Genesis 32:1 | KJVA | Genesis 31:55 |
| Luther | Psalm 3:2 | KJVA | Psalm 3:1 |
| Segond | Psalm 3:2 | Luther | Psalm 3:2 |
| Luther | 1 Samuel 21:15 | KJVA | 1 Samuel 21:14–15 |
| Luther | Acts 19:40 | KJVA | Acts 19:40–41 |

The pinned SWORD archive was also recovered from the builder cache and its
`VersificationMgr` inspected directly. Luther, German, Catholic/Catholic2 and
other systems are registered without native mapping data. Forward/reverse
translation can return without modifying the reference when data is absent.
The [native source inventory](evidence/comparison-57-resumption/native-source.json)
records the exact file hashes and registrations.

## Mapping adapter still required

The next increment must preserve these verified semantics:

- JSword's intermediate named KJV in its implementation is actually **KJVA**.
- Duplicate property keys, part qualifiers, absent/named sections and many-to-many
  results cannot be flattened into a last-value dictionary.
- `!zerosUnmapped` is ignored by the inspected parser; verse-zero behavior must
  come from actual code/tests, not assumptions based on that flag's name.
- The top-level mapper explicitly guesses unchanged references when mapper data
  is missing. That fallback must not be copied into Bible's exact resolver.
- Implicit identity within a successfully loaded table's contract is different
  from missing mapping data. Native and Java canon definitions need comparison
  before sharing expanded data.
- Non-contiguous targets, split/merged/omitted verses, headings, canon differences
  and transitive part mappings need explicit results or honest unsupported states.
- Unsupported alignment must preserve readable independent content rather than
  blanking a pane or presenting stale/false following.

The full shared mapping correction, the representative bidirectional native
input matrix, package validation and publication for #57 remain outstanding.
Neither #57 nor #24 is closed by this increment.
