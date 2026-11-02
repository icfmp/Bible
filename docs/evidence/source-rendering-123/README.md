# Source rendering follow-up — issue 123

Status: local implementation and native GTK validation; installed Flatpak/package delivery remains pending. This branch follows the already published issue 26 batch. Issues remain OPEN and numbered release 87 remains paused.

## Measured causes

- HTMLParser lowercases OSIS sID/eID attribute names. The renderer tested mixed-case eID, treating closing poetry/group milestones as new starts. Whitespace-separated boundaries also escaped coalescing. Real F10/SBL Psalm 13 documents had 39 newlines, including triples; both now have 20 with the actual line/stanza boundaries preserved.
- F10 marks reference-only blocks as title type=parallel. They now remain compact editorial blocks, distinct from genuine section titles, in ordinary/comparison reading and immersion. Native source text, targets and numbering remain unchanged.
- Native OSISPlain excludes preverse material and uses one suspension buffer for nested hi. The former caused a whole-entry style fallback for MHC Gen 1/FreAug Ps 13; the latter produced differently positioned generated stars in MHC Gen 2/Ps 13. The bounded matcher verifies every source character/literal star and permits exactly the generated marker count at actual emphasis boundaries. Unknown conversions keep native output.
- Actual preverse prose is available through Read source preface in the commentary actions and immersion source information. The native reading window preserves its semantic headings, emphasis and copy text. Ordinary following keeps the current native entry and its existing body offsets; it does not first lay out and jump past a 38,622-character MHC foreword. No session or personal-data schema change is required.

## Local evidence

Resource identities, versions and source hashes are recorded alongside before/after parser/native receipts. Actual local GTK 4.18.6 captures cover MHC, FreAug, FreChry, F10, SBL, JND and explicitly identified Martin 1744 in white/dark at wide/narrow widths. These are not client-desktop or installed Flatpak claims; installed captures must follow before delivery. The client's abbreviated Marbr1744 identity/settings remain unconfirmed; the recorded official CrossWire FreBDM1744 is an explicit comparison.

All five real commentary cases preserve source body characters, literal stars and legacy body length. FreChry retains its three literal stars, actual uppercase letters and authored italics. The largest sampled MHC document, including its real preface, took about 19 ms to format locally; other sampled documents took 3–7 ms. These are single-machine local timings, not scrolling or client-GNOME measurements.

Focused source/GTK checks cover paired milestones, editorial roles, nested emphasis, literal stars, fallback safety, preface styling, separate copy and preserved parent position, module hashes, canonical anchors, pagination, clipboard, chapter following and immersion. The installed suite now includes the new renderer checks. Remaining: installed before/after and performance/idle checks, RTL/non-Latin actual-resource checks, signed publication and retained-profile verification.

## Source-preface geometry

A real-resource comparison with GTK 4.20 demonstrated that embedding the entire
MHC foreword in the ordinary chapter could shift the current entry after theme
changes/reopening. The separate native preface reader keeps existing body
coordinates and persisted anchors stable. The 30-case local source/window cycle
then had no unexpected context positions, with unchanged module hashes. Final
installed candidate, publication and retained-update receipts remain required.

Python 3.12.14 also introduced HTML RCDATA title semantics. The OSIS/ThML parsers explicitly retain XML inline-title handling across Python versions; a structured parallel-reference regression verifies that nested reference markup is not displayed as literal XML.
