# Psalm introductory contexts — issue 139

## Measured cause

The actual eBible `ebible~francl2022eb` edition uses Catholic2 numbering. Its Psalm
17:1 contains both the superscription and ordinary verse text. The existing
pinned mapping returns KJVA `Ps.17.0` plus `Ps.17.1`; mapping to MHC (CrossWire
2.2, KJV) retains both addresses. The ordinary-verse validator rejected the zero
component before the commentary could load.

MHC has a genuine native chapter introduction (`getOSISRef()` = `Ps.17`), with
715 stripped characters, followed by its linked verses 1–7 and 8–15. FRANCL's
chapter itself has 15 actual verse spans including verse 1. The screenshot's
blank region was not missing/corrupt source data. Comparison row alignment and
scroll position must be distinguished from corpus completeness.

## Targeted change

The commentary follower explicitly requests mapped introductory contexts as
separate result metadata. A native introduction key validates those addresses
independently. Existing strict ordinary-verse resolution remains the default for
annotations and comparison. Explicit zero-valued source input is rejected before
SWORD can normalize it.

A matching real introduction is loaded and shown with the chapter's ordinary
commentary entries. If that introduction is absent, the verified ordinary verse
still appears with a localized explanation. Unsupported mappings show a
localized status; raw alignment diagnostics go to developer logging. No zero is
clamped to one and no resource text, reference target, note or preference schema
is rewritten.

## Verification

Local native tests cover combined title/verse mapping, strict annotation behavior,
rejected zero input, present/absent introduction, later verse and return,
hide/reopen, stable history and original Bible text. The real-module helper
checks FRANCL/MHC Psalm 17:1, 17:2 and return, Genesis 2, FreSegond1910/MHC,
light/dark captures, all actual chapter spans, offline restart and unchanged
resource-file hashes. Installed candidate results belong to the final batch
receipt; local source checks do not establish client GNOME acceptance.

The issue stays open and numbered release 87 remains paused.
