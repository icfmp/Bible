# Selection, study and download feedback: issues 150–160

This batch refines the native selection, lexical, Header Bar, place, reference
and search surfaces. PR #154 is already merged and published at baseline
`be7eeb8f0511fd2c6b5b77ef31554bd8de7d9289`; its scrolling correction remains intact.
Issues remain open for client validation. Numbered release #87 remains paused.

## Implemented behavior

- The existing dark selection toolbar exposes the actual three-color highlight
  palette directly. Repeated application preserves a mark; comparison remains
  available elsewhere. Copy, captured passage-note targets and removal through
  the native context menu remain available.
- Word study opens a native transient window, preserving the existing study
  pane, its selected tool and drafts. Selected text and its source are visible;
  lexical ambiguity and explicitly named alternative original-language sources
  retain their conservative alignment rules. Native activation finishes before
  hiding its anchor; closing cancels queued requests and invalidates callbacks.
- Header selectors are flat. The passage shows book/chapter; the translation
  uses a supplied public abbreviation, with a full public-name fallback and
  complete accessible labels. Small windows retain the selectors inside the
  Header Bar; the existing overflow/menu retains commands hidden from the bar.
- Explicit translation opening preserves an available book/chapter if exact
  verse resolution fails. This chapter fallback is not used for commentaries,
  highlights, notes or comparison. The old full-width fallback banner is gone.
- The place card uses one virtualized body, including its map/header and all
  references. Approximate-location and passage metadata share a wrapping line.
  The native map retains its camera while offscreen, without retaining its
  loading layer; synthetic HTTP test caches use separate provider identities.
- Text search groups secondary filters, keeps Enter/Search activation and shows
  a localized result count without repeating the query. Topics combine their
  name/count and omit visible ranking scores; source ranking remains unchanged.
- Study References immediately exposes every relationship in its native list,
  with a compact linked `OpenBible.info · CC BY 4.0` footer. The Notes teaser is
  separate and retains its link to References.

## Verified numbering bridge

YouVersion LSG 1910 (edition 93) had a verified source index but an explicitly
empty semantic bridge. Its identifiers differ from registered Segond bounds in
Job 34 and Mark 10, so an edition-wide identity assumption is unsafe.

The same independently distributed CrossWire Segond 1910 was compared verse by
verse. Unicode word tokens were compared after case/diacritic folding; whitespace
and punctuation differences were ignored for this audit only. Source text is
never rewritten. 31,098 of 31,170 verses matched and received explicit verified
correspondences through the existing Segond bridge; 72 remain unmapped.
Audited intervals take 27 KiB, rather than materializing a large correspondence
cache at runtime. Reference bounds and annotation identities do not change.

Reproduce using locally authorized installed resources:

```sh
python3 -m tools.versification.verify_youversion_identity SOURCE_93_ROOT CROSSWIRE_SEGOND_ROOT
```

The tool checks the pinned source-archive and control-resource hashes and exports
only aggregate counts. Its inputs and Scripture bodies are not committed.

## Download diagnosis and material limits

The live French catalogue identifies **104 as Nouvelle Bible Segond (NBS)**;
Nouvelle Segond révisée is a different edition, 2053. The first NBS failure was
`GEN/INTRO1.yves`, an unsupported introductory paragraph marker `im`. Its complete
archive also required standard `imi`, `is`, and `li` forms. All 1,245 actual NBS
chapters/introductions passed conversion and compiled text/editorial readback in
the local native worker. An independent HTML/DOM audit also verified all 31,169
verse units and 27,682 notes against actual application readback. Installed-Library
validation is recorded separately.

NFC 2367 first failed index validation for split identifiers such as `ESG.1_1`.
Consecutive, non-overlapping sections can now retain every physical-file receipt
and their explicit verse numbers. Deuterocanonical inline/note markers and
published secondary verse labels retain their source text and semantic roles.
However, NFC's `SIR.1` prologue and `SIR.1_1` chapter contain different text with
overlapping verse identities. Its `SIR.43` also contains interleaved non-contiguous
fragments of verse 17 around verse 16. These cannot be silently dropped, merged,
renumbered or declared a verified installation. NFC remains an explicit,
chapter-specific unsupported-structure failure; full lossless NFC support is
still outstanding. Failed conversion remains atomic and preserves old resources.

For #151, 51 actual pointer activations on the installed baseline (GTK 4.20.4,
software OpenGL) produced no crash or Python exception: 27 initial KJV/Segond/BDS
activations plus 24 checks of complete, explicitly tagged lexical units and
unavailable/ambiguous selections, each with STEP present and absent. The latter
checks verified actual supplied IDs for `was`, `the Word`, and `the beginning`;
selecting only `beginning` correctly supplies no lexical ID. The retained STEP
database was restored byte-for-byte after the missing-data checks. This
is not a demonstrated root-cause fix for the client's reported crash. Exact
client resource/word/build details were requested; #151 remains unconfirmed.
The presentation change in #152 is not being used as proof that #151 is solved.

## Checks and delivery

Neutral regression fixtures cover split source sections, rejected overlapping
identities, and the observed introductory/note styles. Existing canonical-action,
draft, source-switch, search and native layout tests were updated for the agreed
behavior. The real X11 probe exercises selection, recoloring, lexical opening,
source switching, MHC, text/topics, place/reference lists and light/dark/high
contrast at normal/narrow widths, with original screenshots and aggregate receipts.

Publication identifiers, installed-package checks, retained-profile update proof
and remaining desktop limitations belong in the final delivery evidence. No
numbered prerelease is authorized while #87 is paused.
