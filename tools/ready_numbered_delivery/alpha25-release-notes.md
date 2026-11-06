This batch improves reading controls, source-note access, search and Study layout, immersion preparation, and both note editors. One note can now be linked explicitly to additional passages without duplication. The client has since accepted and closed the selected tickets; this publication records the verified batch without reopening them.

Changes since 0.1.0-alpha.24:

- **Reading and navigation:** gray superscript translation-note markers with native dark hover/click presentation and keyboard access (#185); the corrected complete chapter-heading toggle with the existing saved preference retained (#192); one Study boundary with functional resizing (#196); active book/chapter reveal and independent scrolling in the passage picker (#197). Source editorial headings, Bible text and navigation references are retained.
- **Search and Study:** compact query/scope/search controls that resolve the active reading translation at execution, including Enter (#187); naturally compact empty Text search and stable adaptive Text/Themes width around 480 logical pixels (#188); a shared Study header hierarchy, one contextual reference and quieter accurate empty states, with the translation-notes action retained separately (#189).
- **Appearance:** discreet shared translation-download footers (#190); compact Aa controls and a remembered collapsible visible-elements group (#191); Search → Comparison → Aa → Immersion → Study → Menu ordering (#193); independent Serif/Sans reading families and study-content size using the existing preferences (#194); shared saturated highlight colors with faithful swatches, retained stored color IDs and a compact accessible original-text action using GTK's standard dictionary symbol (#198). The client-supplied comparison-off icon uploaded since alpha.24 is retained.
- **Immersion:** bounded native Pango paragraph shaping and indexed protected-block lookup reduce repeated long-book preparation. A discreet delayed native indicator covers remaining preparation (#199). Matched installed measurements below; native pagination/text equivalence checks passed.
- **Notes:** a common minimal direct-format editor in the compact quick dialog and three-column Notes workspace, with bold/italic/lists, original-source excerpt and label chips (#200). The redundant workspace menu is removed; Preferences remains the backup/restore entry point. Workspace autosave commits in bounded windows while typing continues, with error/draft guards; quick notes keep explicit Save (#201). Explicit manual offline passage links, optional existing-reference suggestions, shared note identity, overlap deduplication, unlinking and versioned restore are supported (#202). The annotation compatibility work is limited to the documented contract; the broader #126 scope is not delivered.

Validation and measured behavior:

- PRs [#203](https://github.com/icfmp/Bible/pull/203), [#216](https://github.com/icfmp/Bible/pull/216) [#217](https://github.com/icfmp/Bible/pull/217) and [#229](https://github.com/icfmp/Bible/pull/229), exact release source `c7009d0162c0b2b85cc8f99e5b024e17e764bd3e`.
- Green ordinary main CI [42280604893](https://github.com/icfmp/Bible/actions/runs/42280604893): host regressions, French subset, native mouse/keyboard checks, real resource/offline checks, Flatpak build/install, packaged regressions and GL visual/scroll checks. Platform/dependency skips are recorded in CI, not counted as client desktop acceptance.
- [Installed GTK evidence](https://github.com/icfmp/Bible/actions/runs/42258008846): full corpus at source `2a19acaca475cfadc99696205b6ab144b7a7ed49`, with distinct Ready tests in French and English; light/dark and 1200/680/360 logical-width captures, enlarged interface text, source-marker mouse/keyboard interaction, secondary-pane note popup, real divider drag, offline manual linking, shared UUID across Semeur/KJV/Segond, actual reopening, legacy import and linked backup restoration. Later application-code changes are the original-text icon name in #217 and the Linux native OpenGL default in #229 (the corpus already used OpenGL); the final signed release reruns all 27 dedicated Ready/link/pagination tests in each language and supplies four updated selection captures. The archive labels both tested sources explicitly.
- [Retained signed-update proof](https://github.com/icfmp/Bible/actions/runs/42280645207): actual installed alpha.24 → this release on one retained real-resource profile, GPG/ref/origin continuity, note fields, labels, highlights, old preference values, module/study-file hashes and verified private schema-1 migration snapshot, followed by the final signed Ready tests and standard-symbol captures. No reset or customer profile access.
- Matched entry-to-first-usable-painted-text measurements from installed alpha.24 and the batch implementation, same runner/resources/preferences, GTK 4.20.4, composited X11/software OpenGL:

| Resource / passage | Fresh-process alpha.24 → updated | Warm re-entry alpha.24 → updated |
| --- | --- | --- |
| Semeur / Psalms 34:2 | 4.593 s → 1.866 s | 4.581 s → 1.838 s |
| KJV / Psalms 119:1 | 2.363 s → 2.036 s | 2.329 s → 2.038 s |
| KJV / Philemon 1:1 | 0.570 s → 0.564 s | 0.555 s → 0.550 s |

“Fresh process” does not mean flushed OS/font/disk caches. These are observed developer timings, not a hardware-independent promise. These corpus-source measurements vary from the earlier candidate run on another runner; both showed a large long-Semeur improvement and essentially unchanged short-book entry. The final measurement JSON and source receipts are included. Remaining main-loop maximum gaps in this run were approximately 0.25–0.39 seconds; entry is improved, not instantaneous.


- **Native renderer stabilization:** Linux now defaults to GTK/GSK OpenGL, honoring explicit `GSK_RENDERER` overrides. In the final signed retained-profile test, default startup RSS was 359.8 MiB and after 24 combined scrollbar cycles RSS stayed between 423.3 and 425.9 MiB (last eight: 425.1–425.9 MiB). All 24 stops had zero position changes after 500 ms. First movement/paint were about 3.0/5.8 ms. Earlier unchanged-source Vulkan testing rose from 462 to 554 MiB over 12 cycles; Python memory and widget counts stayed stable. This avoids the measured native renderer path; the exact upstream allocation site is not identified. Synthetic sustained-input CPU remained about 101–103% of one logical CPU, with lower frame throughput than Vulkan; it is not a claim of low CPU use or equal-throughput acceleration. Additional single, parallel and Study wheel runs passed; their two cycles are a shorter endurance sample. The hidden menu had no retained backdrop or placement callback. See [the rendering report](https://github.com/icfmp/Bible/blob/c7009d0162c0b2b85cc8f99e5b024e17e764bd3e/docs/READY_RENDERING_VALIDATION.md).

Screenshots: download **Bible-alpha25-GTK-evidence.zip**, extract it and open **overview.html**. Original PNGs, JSON measurements, provenance and checksums are included. No full Bible modules, customer profile or database is attached.

Install or update:

```sh
flatpak install --user https://icfmp.github.io/Bible/alpha/Bible.flatpakref
# Existing installation:
flatpak update --user io.github.icfmp.Bible//alpha
```

Use the existing signed channel. The numbered Git tag identifies the verified source; the channel is continuous and may later serve a newer verified alpha. Do not uninstall/reset application data to update.

Publication provenance:

- Source: `c7009d0162c0b2b85cc8f99e5b024e17e764bd3e`; ordinary main build: `42280604893`.
- Signed publication: [42284382101](https://github.com/icfmp/Bible/actions/runs/42284382101), revision `42284382101-1`.
- OSTree commit: `0841dca6e6d3cd1d191314e2ffde228151f298c3186773ab4972d3b185cbaba2`; ref `app/io.github.icfmp.Bible/x86_64/alpha`; remote `bible-alpha`.
- Signing fingerprint: `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.

Material limits:

- Developer checks use Linux x86_64 and composited X11/software OpenGL. Client GNOME/Wayland, hardware GPU, other operating systems and a separate high-contrast desktop run remain unverified.
- Clipboard transfer is native plain text. Editing a legacy list body can normalize its bullet prefix; viewing, metadata-only edits and full undo retain the original body. Workspace autosave has a 600 ms pending window that abrupt termination can lose. Manual label/reference input is not committed until Add.
- Notes schema 2 is additive and retains a verified private schema-1 recovery snapshot. Older schema-1 alphas cannot edit the migrated database; never replace current notes silently with that snapshot. See [the notes data contract](https://github.com/icfmp/Bible/blob/c7009d0162c0b2b85cc8f99e5b024e17e764bd3e/docs/NOTES_DATA_FORMAT.md).
- Source-note marker interaction is verified in ordinary and parallel reading; this batch does not add that marker UI to immersive pagination.
- Newly reported alignment cases in #215 and the separate #204–#214 follow-ups are outside this selected batch. Do not infer that those client reports have been corrected by these interface changes.

The client independently accepted and closed these tickets during delivery. Their accepted states are preserved; no agent closed or reopened them. GitHub project integration remains inaccessible (`Resource not accessible by integration`); this release does not change project status.
