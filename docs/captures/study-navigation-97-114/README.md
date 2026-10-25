# Study and navigation: native validation

Related to #97, #100, #104, #106, #107, #111 and #114. These are actual GTK4/libadwaita windows under Linux/Xvfb, not mockups or proof of acceptance on the client's GNOME desktop. Black surrounding areas are the Xvfb desktop. Resources are real installed FreSegond1910, KJV, MHC and Wesley, with OpenBible geography/topics and reviewed STEP data. Visible notes are disposable developer-authored annotations, never client data.

Before: source `88098507179d2b1bea7905a979c5819bdc716517`. After: application source `c9013fc4edc8e21baddee2df325d65b3ac218937`, with word-detail sample refinement `a43a088` captured afterward. Capture-only evidence does not alter source texts. Screenshots retain the original captured pixels.

## Before and after

| Surface | Before light / dark | After light / dark |
| --- | --- | --- |
| Continuous reader | [Light](before/inline-markers-day.png) / [Dark](before/inline-markers-night.png) | [Light](after/inline-markers-day.png) / [Dark](after/inline-markers-night.png) |
| Comparison | [Light](before/comparison-day.png) / [Dark](before/comparison-night.png) | [Light](after/comparison-day.png) / [Dark](after/comparison-night.png) |
| Chapter commentary | [Light](before/chapter-commentary-day.png) / [Dark](before/chapter-commentary-night.png) | [Light](after/chapter-commentary-day.png) / [Dark](after/chapter-commentary-night.png) |
| Passage picker | [Light](before/passage-day.png) / [Dark](before/passage-night.png) | [Light](after/passage-day.png) / [Dark](after/passage-night.png) |
| Text search | [Light](before/text-results-day.png) / [Dark](before/text-results-night.png) | [Light](after/text-results-day.png) / [Dark](after/text-results-night.png) |
| Indexed themes | [Light](before/theme-results-day.png) / [Dark](before/theme-results-night.png) | [Light](after/theme-results-day.png) / [Dark](after/theme-results-night.png) |
| Narrow reader | [Light](before/reader-narrow-day.png) / [Dark](before/reader-narrow-night.png) | [Light](after/reader-narrow-day.png) / [Dark](after/reader-narrow-night.png) |

Actual eight-second recordings: [before](following-before.mp4), [after](following-after.mp4). Recorded native frames at 24 fps include actual wheel input and automatic following; JSON adjustment samples accompany them in [before](motion-before.json) and [after](motion-after.json). Shared comparison uses one native adjustment, so neither column is animated a second time. Separate commentary/Notes following uses an interruptible 200 ms ease-out; disabled system animations settle immediately. Static images alone do not demonstrate motion.

## Inline access and responsive layouts

- Distinct note and geography controls: [place chooser light](after/place-chooser-day.png), [dark](after/place-chooser-night.png); [Notes context light](after/notes-context-day.png), [dark](after/notes-context-night.png). Actual pointer activation of the chooser and keyboard Return on the note icon were checked without opening the passage action bar.
- Independent visibility: [appearance light](after/visible-elements-day.png), [dark](after/visible-elements-night.png); [hidden verse numbers](after/markers-without-numbers-day.png); [both markers disabled](after/markers-disabled-night.png). No UI objects enter copied Scripture and no marker introduces a paragraph in the ordinary reader.
- [Charan light](after/charan-detail-day.png), [dark](after/charan-detail-night.png): one title, modern-location context, evidence status, offline Natural Earth coastlines, references and collapsed technical details. No map tiles were downloaded or promised. These are modern simplified coastlines, not ancient boundaries or a labelled tile basemap.
- The installed OpenBible metadata supplies verse associations, **zero proven translation-specific word spans**. This delivery deliberately uses the mandatory verse-level fallback. It does not guess a place-name position or claim word-level precision. Multiple supported biblical identities remain distinct.
- 360 px picker: [Passage light](after/passage-narrow-day.png), [dark](after/passage-narrow-night.png); [Text light](after/text-narrow-day.png), [dark](after/text-narrow-night.png); [Themes light](after/topics-narrow-day.png), [dark](after/topics-narrow-night.png).
- Narrow comparison keeps readable columns with horizontal scrolling: [light](after/comparison-narrow-day.png), [dark](after/comparison-narrow-night.png).
- [Large text](after/large-text-markers.png), [emulated high contrast light](contrast/large-markers-day.png), [dark](contrast/large-markers-night.png). High contrast uses libadwaita's test settings override; this is not a GNOME portal integration claim.

## Shared comparison and complete commentary

Real Acts 1 Segond/KJV: 26 correspondence rows, maximum top-position difference **0 px**, light and dark. Real Psalms 3, 4 and 51: 8/8/19 groups, maximum difference **0 px**; numbered Segond titles are included in the first mapped group, each source passage exactly once. Psalm 51 groups Segond 1–3 against KJV 1. Source labels are retained; visual padding is GTK paragraph spacing, not copied text. A split-final-3-John regression also covers KJV 14 against NRSV 14–15.

Unverified/non-contiguous mappings retain independently readable source content and an explicit alignment warning. For example, the pinned Luther Genesis 32 mapping includes an introduction address not supported by the strict reader; no equivalence is invented.

[MHC complete chapter](after/mhc-complete-chapter.png): Acts 7 exposes seven actual linked entries, 99,440 source characters, all loaded bodies equal to the provider's native documents. First load measured 0.777 s including a deliberate 0.5 s settling interval; maximum GTK heartbeat gap 0.432 s. Same-chapter following retains the document. Missing coverage clears the active entry, retaining the chapter. Actual downloaded Kretzmann also passed native SWORD fidelity and isolated offline reopen.

## STEP word study

[Provider/content-policy audit](../../STEP_WORD_STUDY_AUDIT.md) was recorded in the PR before UI implementation. Restricted TBESH definitions and CC BY-NC TTESV are excluded. No translation-wide alignment or inferred extended sense is claimed.

| Flow | Light | Dark |
| --- | --- | --- |
| Selected French word: honest Strong lexical lookup | [Offer](word/lexical-offer-day.png) | [Offer](word/lexical-offer-night.png) |
| Greek lexical detail | [Detail](word/greek-detail-day.png) | [Detail](word/greek-detail-night.png) |
| Shared occurrence search | [Results](word/greek-occurrences-day.png) | [Results](word/greek-occurrences-night.png) |
| Hebrew source-verse fallback | [Words](word/hebrew-words-day.png) | [Words](word/hebrew-words-night.png) |
| Hebrew selected source token | [Detail](word/hebrew-detail-day.png) | [Detail](word/hebrew-detail-night.png) |
| 360 px temporary drawer | [Narrow](word/word-narrow-day.png) | [Narrow](word/word-narrow-night.png) |

Counts: TAGNT explicit NA27 membership, supplied spellings **137,992 tokens**; TAHOT main L/Q, supplied segmentation **305,465 tokens**. G3056: 330 tokens / 317 numeric verses. H1254A: 53 tokens / 45 verses; H1254B remains a different lexical identity. English glosses are labelled as English. Hebrew source accents are preserved; the developer image's fonts lack some cantillation glyphs, visible as missing-glyph boxes. Text is not stripped to disguise that limitation; the installed desktop's font fallback may differ.

Actual optional download/cancel/retry: 105,074,789 bytes, successful retry plus indexing **37.58 s**, 274,313,216-byte SQLite index, maximum GTK heartbeat gap **62.5 ms**. This installer proof uses a synthetic reader fixture and real upstream STEP files, not client notes. Other native captures use real installed Bibles. Atomic failed-update and unsaved-note preservation are covered separately by regressions.

## Checks and limits

Full French source suite: **312 tests passed** before the final anchor correction; its focused four-test comparison suite passed afterward, including the new stale-anchor regression. A subsequent source-title guard adds two regressions; final totals and installed Flatpak evidence are recorded in the delivery report; do not infer packaging success from these screenshots.

Native X11 checks covered passage navigation, selection/Aa shortcuts, nested popover dismissal, immersion, wheel input in both panes and long scrollbar drags. Real integrated search: exact French/English phrases, themes, explicit preview/current/new-tab actions, accurate French Psalm mapping, zero results, failed-update preservation and offline restart. Cold KJV indexing/search measured 8.925 s off GTK, maximum heartbeat gap 51 ms. Unquoted terms mean all normalized words in any order; quoted phrases are contiguous under documented language-aware normalization. Original excerpt positions are preserved.

[Native proof](native-ui-proof.json), [search proof](search-final-proof.json), [STEP provider proof](step-provider-audit.json), [installer proof](live-step-proof.json), [module metadata audit](sword-token-audit.json), [word-selection proof](word-ui-proof.json).

Keyboard/mouse checks are developer validation; screen-reader acceptance and the client's GNOME desktop acceptance remain outstanding. Some Xvfb/libadwaita runs emit allocation/portal warnings; these are not presented as a warning-free desktop run. Implementation issues remain OPEN. The client explicitly keeps numbered release task #87 paused; this batch must not silently publish a numbered prerelease.

## Source-heading guard before publication

A final real-data check found that native SWORD collapses Segond Psalm superscriptions onto the following body verse. Word exploration now reuses the pinned verse-part bridge: Segond 3:1 and 51:1–2 remain unavailable rather than displaying body words, while Segond 51:3 opens the actual TAHOT words at NRSV 51:1. The shared comparison grouping is preserved. The initial main pipeline was cancelled before any alpha publication.

Actual GTK: unavailable title [light](heading-guard/heading-unavailable-day.png) / [dark](heading-guard/heading-unavailable-night.png); correctly mapped body words [light](heading-guard/mapped-body-words-day.png) / [dark](heading-guard/mapped-body-words-night.png).
