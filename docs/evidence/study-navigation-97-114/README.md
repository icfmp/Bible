# Study and navigation delivery evidence

Application issues: #97, #100, #104, #106, #107, #111 and #114. Implementation review: [PR #124](https://github.com/icfmp/Bible/pull/124), plus the source-title correction in [PR #127](https://github.com/icfmp/Bible/pull/127). All implementation issues stay OPEN for client acceptance. This evidence branch changes documentation only; it does not rebuild or republish the application.

Final application source: `48b8148e682741d137c2d0c6f189dcdd6bef95c9`. [Actual native before/after screenshots and motion recordings](https://github.com/icfmp/Bible/blob/48b8148e682741d137c2d0c6f189dcdd6bef95c9/docs/captures/study-navigation-97-114/README.md). [Pinned STEP content-policy audit](https://github.com/icfmp/Bible/blob/48b8148e682741d137c2d0c6f189dcdd6bef95c9/docs/STEP_WORD_STUDY_AUDIT.md).

**Signed alpha publication verified.** [Final CI 40200868244](https://github.com/icfmp/Bible/actions/runs/40200868244), [publication 40202173987](https://github.com/icfmp/Bible/actions/runs/40202173987), canonical revision `40202173987-2`. [Install/update](https://icfmp.github.io/Bible/alpha/Bible.flatpakref). Existing installations: `flatpak update --user io.github.icfmp.Bible//alpha`.

Final main checks: **315 source tests, 142 French UI tests, 121 installed-Flatpak tests and 11 installed immersion tests**, plus actual real-resource online/offline checks including the source-title guard. Counts overlap and are not a sum of unique tests. [Final main receipt](main-ci.json), [installed online](packaged-study-online.json), [installed without network](packaged-study-offline.json).

[Public verification](final-verification.json) matches the public provenance, CI bundle checksum and corresponding source archive. Installation verifies the commit and summary GPG signatures and GTK startup; a real public update changes the installed OSTree commit and preserves its three validation sentinels. Actual note/schema/resource/preference preservation is established separately by the source/installed regressions and real-resource/profile checks below. [Install receipt](public-install-check.json), [update receipt](public-update-check.json), [provenance](provenance.json).

Stable channel: `app/io.github.icfmp.Bible/x86_64/alpha`, remote `bible-alpha`, fingerprint `47A17230403EA4953745E6E020EB9FFCCECAFD8F`. Installed canonical commit: `e75cc75f17fbcca000f1c4f4ea210bc66eb0fb2e2a8928674fc1081b45a5bb64`. All 327 corresponding project files and three original dependency source archives were verified. All 36 historical source records remain unchanged (37 total); source payloads remain outside the Pages site (15,409,589 bytes). Numbered prereleases remain unchanged; #87 is still paused. The two internal signed deployment revisions verify one application batch, not two application updates.

[Corresponding source archive](https://github.com/icfmp/Bible/releases/download/alpha-source-archives/Bible-48b8148e682741d137c2d0c6f189dcdd6bef95c9-sources.tar.gz), SHA-256 `c02c74b787927783cc6da5f31d71748a7b0be4f78b48b2b9ee8f0d70176e0ff3`.

## Scope and source fidelity

Chapter commentary retains every actual covering entry once, including introductions and linked ranges; a missing entry clears active coverage without replacing the readable chapter. Successful explicit source selection supplies a remembered default without overwriting existing tab choices. Interruptible native motion follows valid targets only; comparison uses one shared adjustment and connected reference groups, with GTK-only row padding and readable horizontally scrollable narrow columns.

Personal-note and geographic markers are distinct native inline objects, excluded from copied Scripture. Their persistent appearance toggles are independent of verse numbers. Geography has **no proven translation-specific word spans** in the installed metadata, so the approved verse-level fallback is delivered. Place details use attributed simplified modern coastlines; no labelled tile basemap or ancient boundaries are claimed.

Passage, Text and Themes share one picker, retaining deliberate navigation, installed search-source identity, canon-aware scopes, exact source excerpts and the existing licensed OpenBible topic relationships. Unquoted terms mean all words in any order; double-quoted phrases are contiguous under documented language-aware normalization. STEP lemma occurrences reuse these results, not a new permanent mode.

STEP is optional and downloaded only on request. TAGNT uses explicit NA27 membership and supplied source spellings; TAHOT uses main L/Q records and supplied segmentation. Restricted TBESH definitions and CC BY-NC TTESV are excluded. Strong lexical lookup does not establish exact token/morphology/extended-sense alignment. English lexical content is labelled as English. Some Hebrew cantillation glyphs are missing from the developer image's fonts; original Unicode is retained.

A real-data check before publication exposed SWORD's collapsed Psalm-title mapping. The superseded first main pipeline was cancelled and its alpha job skipped. PR #127 distinguishes pinned `!pv` superscriptions from `!v` body mappings: Segond Psalm 51:1–2 remain unavailable for source-word exploration, while 51:3 opens actual TAHOT NRSV 51:1. Shared comparison grouping remains intact. No affected alpha was published.

## Developer checks

The final complete French source suite passed **315 tests**. Focused source-word/draft/GTK checks passed six tests. [Real source-data guard proof](real-study-heading-guard.json) records three rejected titles, actual Hebrew body words, 19 Psalm 51 groups aligned to 0 px, 36 Wesley entries, exact lemma totals, unchanged note/schema and 54 unchanged installed-module files.

Earlier reviewed branch [CI 40197604854](https://github.com/icfmp/Bible/actions/runs/40197604854) passed 313 source tests, 140 French UI tests, 119 installed-Flatpak tests and 11 installed immersion tests. Its real-resource checks executed application imports from `/app`, both online and without network, preserving a note/schema and 27 installed-module files. These earlier counts do not replace the final main CI and must not be summed into a unique-test total. [Branch receipt](branch-ci.json), [online](branch-packaged-study-online.json), [offline](branch-packaged-study-offline.json).

[Legacy-profile preservation](preservation-source.json): actual note, highlight, original preference bytes, selected tab/passages, schema and 36 resource-file hashes survived reopening without network. [Independent real-resource offline source run](real-study-offline-source.json) passed as well. These are disposable developer profiles, not private client data.

The gallery includes real GTK light/dark before/after views, 360 px layouts, large text, emulated high contrast, geographic chooser/Charan, Greek/Hebrew and an actual eight-second motion recording. Native X11 interaction checks cover pointer, keyboard, nested dismissal, immersion, wheel and long scrollbar drags. This establishes developer validation on Linux/Xvfb, not screen-reader acceptance or acceptance on the client's GNOME desktop.

## Client workflow

[Project-access receipt](project-access.json) records the exact refusal: `Resource not accessible by integration`. Manual status requested for all seven issues: **In review**. The client explicitly keeps numbered publication task #87 PAUSED; this overrides the standing numbered-prerelease authorization and prevents an automatic In validation claim under the current workflow. Only the client moves issues to Done or closes them.

## Translation without word metadata

Actual FreLSN1872 John 1:1, selected French “Parole”: no usable source-word lexical metadata is claimed. The contextual action offers original-verse exploration; it shows the actual 17 TAGNT source tokens rather than an inferred lemma for the clicked French word. Actual source at the final application commit: offer [light](unaligned/unaligned-offer-day.png) / [dark](unaligned/unaligned-offer-night.png), source words [light](unaligned/unaligned-source-words-day.png) / [dark](unaligned/unaligned-source-words-night.png), [proof](unaligned/proof.json).
