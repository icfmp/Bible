# Ready feedback: Library, annotations and note editors

Scope: #276, #324, #291, #322, #281, #320 and #321, including the 20 November additions to #281. Baseline pictures use the **installed alpha.37**, source `070dacc210a18f644830aa27df310a38a713a0f5`. Candidate pictures run the application source in that Flatpak's GNOME 49 / GTK 4.20.4 runtime, with actual X11/software OpenGL and existing provider modules. These are developer checks, **not a publication receipt or client acceptance**. Final build/update/release receipts belong in the delivery comments.

Personal notes and marks in these pictures are disposable test records. Original retained profiles were neither opened for editing nor reset. No Bible-Resources repository, source package, dataset or distribution service was changed.

| Issue | Implemented and checked | Client check |
| --- | --- | --- |
| #276 | Localized legal-field labels only after matching the installed SWORD configuration; original values, unknown/mixed notices and distribution restrictions remain intact. Distinct catalogue/text links, exact-URL deduplication, singular type and display capitalization. One global update-check entry remains in Library actions. Real Martin 1707 **1.1.1**, FR/EN, 360px/large-font/high-contrast; link signals retain their exact destinations. | Inspect description, both source roles, complete English restriction and contact, then global update checking. |
| #324 | Remove the permanent dark stroke only from the card's color chip. Keep its actual color, larger independent hit target and native focus/hover feedback. | Open the chip with mouse/keyboard; recolor or remove a disposable mark. |
| #291 | Balanced four-sided selection-content padding, 12 → 16 logical pixels; controls, source snapshot and colors retained. Actual BDS Genesis 1:2–5 comparison. | Check both horizontal edges, the last row, Copy and its separate chevron. |
| #322 | Read the highlight excerpt and caption from its saved origin through the existing reader pool. Namespace shared chapter previews by edition, preventing cross-edition cache contamination. Missing sources never substitute the current Bible. Mapping/navigation still use verified projection; stored marks are unchanged. | Switch Bibles and comparison while inspecting the same mark; check original wording/name and action identity. |
| #281 | Shared text/card insets, small owned Open in Bible action, no embedded overflow, and the same confirmed bottom Delete control in both hosts. Popup viewport allocates natural content height instead of compressing a long editor. Repeated short/long/reopen/width tests, original-source navigation, disabled unavailable source, autosave/failure/deletion checks and native FR/EN captures. | Reopen short and long notes, resize, open the original passage and retest the intermittent footer gap. |
| #320 | Verify native variants that retain authorial titles/prefaces before styling emphasis. Only source-verified generated stars disappear; literal stars, native text/offsets and source-only copy remain protected. No edition/verse-specific runtime exception. | Inspect MHC Genesis 1:9–13 in Study and immersion, then copy source text. |
| #321 | Full-width shared cards; a small independent Unlink action inside the header, with the navigation chevron at far right. Real keyboard unlink autosaves only that relationship without navigating. | Inspect Job 26:8 / Genesis 1:11; unlink one passage, reopen and check the note and other links. |

## Focused checks and limits

The consolidated affected-consumer run passed 43 tests before the interruption. Subsequent focused rechecks cover the corrected native viewport, source-URL roles, numeric-entity filtering and the latest #281 controls; overlapping counts are not added together. On 24 November, ten note checks, a French original-source/unavailable-source action check, and six metadata checks passed. Normal CI remains responsible for the broad regression suites and the final packaged application.

The first PR host run executed 657 tests and reported four failures: two old presentation assertions (notice heading/header gap), and two catalogue fixtures reaching an unrelated live YouVersion lookup. Those same two waiting cases passed individually against both alpha.37 and the candidate. A traced run confirmed the additional provider requests; the fixtures now explicitly select their supplied CrossWire source and reject unexpected provider lookups. Original loading/filtering/retry assertions and wait bounds are retained. A new complete CI run is required for the updated tests.

The exact client's intermittent **full-screen blank area before Delete** was not reproduced. Measurements did establish nested minimum/natural allocation problems: an 80-line editor with 1320px natural height was compressed to 231px. Native viewport natural-height allocation now passes long-note/one-scroll and repeated short-note/footer bounds checks. Confirmation on the client's desktop remains necessary.

[Commentary audit, 19 November](commentary-audit-19nov.json): 44 real samples across Bible Resources MHC/MHCC and CrossWire MHC, FreAug, FreChry, Clarke and Wesley. Generated-marker cases verify against source markup; plain ThML is not presented as rich structure. [Current MHC check](current-mhc-nov24.json): seven additional samples of the provider's now-published **MHC 1.0.0**, including exact source-only copy. The reported Genesis 1:9–13 raw/native content matches the earlier **0.1.0** reproduction. Source-owned versions/packages were only downloaded to a disposable validation profile.

Native SWORD also filters some numeric entities in MHC's preface. The verified matcher can recognize that native output but **does not reconstruct missing accented characters**; literal native sequences such as `#224;` remain as supplied. Unknown conversions retain their full native fallback. Literal-star and changed-word rejection tests remain in place.

Only alpha.37 was installed for the before comparison. The alpha.36 renderer was additionally replayed from source `43a0a622` in the same GTK runtime against the same MHC 0.1.0 input; this is **not an installed alpha.36 binary test**. PR #330 was inspected for overlapping title handling; its independent paragraph/display-offset remapping is not merged by this batch.

The Martin module's actual contact is `martin1707@ymail.com`; its original value and complete restriction were preserved. Unknown legal prose is not translated or inferred. Source-link activation was intercepted to verify exact HTTP(S)/mailto destinations, without sending mail or claiming an external browser test. Non-SWORD study notices have a separate regression check.

Cloud X11/software rendering, representative FR/EN/light/dark/high-contrast and larger text do not establish client Wayland/GPU, physical-touch or assistive-technology acceptance. Existing unsupported verse correspondences remain unavailable.

## Actual GTK comparisons

- MHC Study: [before](before/MHC-Gen1-9.png) / [after](after/MHC-Gen1-9.png); immersion: [before](before/MHC-immersion.png) / [after](after/MHC-immersion.png).
- Origin and color chip: [before](before/highlight-origin.png) / [after](after/highlight-origin.png).
- Notes workspace, Genesis 18:16–18: [before](before/notes-Gen18.png) / [after](after/notes-Gen18.png).
- Notes workspace, Psalms 12:6–7: [before](before/notes-Ps12.png) / [after](after/notes-Ps12.png); [English/narrow/high contrast](Ps12-narrow-contrast.png).
- Popup and linked cards: [before](before/note-linked-cards.png) / [after](after/note-linked-cards.png).
- Martin detail: [before](before/library-Martin1707-top.png) / [after](after/library-Martin1707-top.png); terms/footer: [before](before/library-Martin1707-terms.png) / [after](after/library-Martin1707-terms.png); [narrow/large/high contrast](library-Martin1707-narrow-terms.png).
- Selection: [before](before/selection-BDS-Gen1-2-5.png) / [after](after/selection-BDS-Gen1-2-5.png).

All seven issues remain open. Project 5 access is denied (`Resource not accessible by integration`); request manual **In validation** only after the signed update and matching numbered alpha are verified and published.
