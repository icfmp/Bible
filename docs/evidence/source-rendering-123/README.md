# Source rendering follow-up — issue 123

Status: local implementation and native GTK validation; installed Flatpak/package delivery remains pending. This branch follows the separately publishing issue 26 batch. Issues remain OPEN and numbered release 87 remains paused.

## Measured causes

- HTMLParser lowercases OSIS sID/eID attribute names. The renderer tested mixed-case eID, treating closing poetry/group milestones as new starts. Whitespace-separated boundaries also escaped coalescing. Real F10/SBL Psalm 13 documents had 39 newlines, including triples; both now have 20 with the actual line/stanza boundaries preserved.
- F10 marks reference-only blocks as title type=parallel. They now remain compact editorial blocks, distinct from genuine section titles, in ordinary/comparison reading and immersion. Native source text, targets and numbering remain unchanged.
- Native OSISPlain excludes preverse material and uses one suspension buffer for nested hi. The former caused a whole-entry style fallback for MHC Gen 1/FreAug Ps 13; the latter produced differently positioned generated stars in MHC Gen 2/Ps 13. The bounded matcher verifies every source character/literal star and permits exactly the generated marker count at actual emphasis boundaries. Unknown conversions keep native output.
- Actual preverse prose remains accessible above the current entry, with its own semantic styling, outside legacy native body offsets. Following opens the source's current heading. A backward-compatible optional prefix-position flag preserves newly accessible preface positions across resize/restart; existing anchors remain valid. The interface coverage-heading tag is confined to the interface heading, not preface prose.

## Local evidence

Resource identities, versions and source hashes are recorded alongside before/after parser/native receipts. Actual local GTK 4.18.6 captures cover MHC, FreAug, FreChry, F10, SBL, JND and explicitly identified Martin 1744 in white/dark at wide/narrow widths. These are not client-desktop or installed Flatpak claims; installed captures must follow before delivery. The client's abbreviated Marbr1744 identity/settings remain unconfirmed; the recorded official CrossWire FreBDM1744 is an explicit comparison.

All five real commentary cases preserve source body characters, literal stars and legacy body length. FreChry retains its three literal stars, actual uppercase letters and authored italics. The largest sampled MHC document, including its real preface, took about 19 ms to format locally; other sampled documents took 3–7 ms. These are single-machine local timings, not scrolling or client-GNOME measurements.

Focused source/GTK checks cover paired milestones, editorial roles, nested emphasis, literal stars, fallback safety, preface styling and position persistence, module hashes, canonical anchors, pagination, clipboard, chapter following and immersion. The installed suite now includes the new renderer checks. Remaining: installed before/after and performance/idle checks, RTL/non-Latin actual-resource checks, signed publication and retained-profile verification.

## Outstanding local geometry diagnosis

Repeated mixed-source capture cycles with animations enabled exposed a current-entry position offset in the long MHC preface after reopening/theme changes (up to 27,387 pixels). Simpler first-open/resize fixtures pass. GTK scroll-to-iterator/mark experiments did not resolve it and were reverted. The branch retains the established reveal path while an explicit non-publication workflow compares real resources with the installed GTK 4.20 runtime and development Python source. This diagnostic mode must not be described as an installed candidate application delivery. No source/text change is inferred from the geometry failure.
