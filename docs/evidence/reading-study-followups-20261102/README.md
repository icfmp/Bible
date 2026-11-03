# Native reading and study follow-ups

Delivery scope: issues 123, 118, 130, 139–143 and 145–147. Issue 138 was delivered
in the preceding YouVersion catalogue batch; number 144 is that batch's PR.
All implementation issues remain OPEN for client acceptance. Numbered release
87 remains paused by the client. No numbered tag or prerelease is created.

Published to the signed alpha channel after green candidate/main checks,
installed GTK verification and a successful update on the same retained profile.
The exact publication and its limits are recorded below.

Corrected package: [337-image installed proof, attempt 2](https://github.com/icfmp/Bible/actions/runs/41529836329) and [135 selected original before/after captures](CORRECTED-GALLERY.md), source `976a0e39c31c256656df4246261fe04d7debc6d1`. All 18 native-import receipts and three mapped-place views pass; source data hashes remain unchanged. The final signed source is `be7eeb8f0511fd2c6b5b77ef31554bd8de7d9289`; its complete Git tree matches this verified candidate.

## Changes and simple client checks

| Issue | Implemented behavior | Client checks |
| --- | --- | --- |
| [#123](https://github.com/icfmp/Bible/issues/123) | Generic OSIS/ThML paragraph, poetry, heading and emphasis handling; verified generated markers are hidden without changing ordinary character offsets. Complete long source prefaces are available separately. | Compare F10/SBL Psalm 13 and F10 Genesis 2. Open MHC Genesis 1 source preface. Check FreAug/FreChry Psalm 13: authored capitals, literal punctuation and source numbering remain. |
| [#118](https://github.com/icfmp/Bible/issues/118) | Chapter-only passage/tab labels; complete native translation selectors; existing actions in Header Bar with narrow-window and enlarged-font fallback. | Switch single/comparison reading. Resize the window and increase UI text size. Check both complete translation selectors and Aa without duplicate headings. |
| [#130](https://github.com/icfmp/Bible/issues/130) | Bibles/Commentaries/Study tools in one Library, existing download services and independent category search/filter state. | Switch categories while a places download runs. Return to each previous query/filter. Existing reference/topic data remains usable; fresh upstream ZIPs are currently rejected when their reviewed pin differs. |
| [#139](https://github.com/icfmp/Bible/issues/139) | Explicitly mapped commentary introductions are handled separately from ordinary verses, without clamping zero to one. | Read FRANCL Psalm 17:1 with MHC. Check actual source introduction and mapped ordinary coverage. Restart offline at the same passage. |
| [#140](https://github.com/icfmp/Bible/issues/140) | Existing native raster map/cache uses an attributed French/Latin-readable style. | Open Shinar and Jerusalem. Check pan/zoom and readable context. English uses the available French/Latin fallback, not guaranteed English translations of every label. |
| [#141](https://github.com/icfmp/Bible/issues/141) | Place/location/qualification hierarchy distinguishes approximate regions, precise points and candidate locations. | Compare Shinar/Babylonia with Jerusalem. Open Emmaus alternatives and Nod's unknown location. Resize each card and return to the studied passage. |
| [#142](https://github.com/icfmp/Bible/issues/142) | Compact References cards share the passage Notes surface; complete normal-color references and three-line exact excerpts retain existing activation. | Open Genesis 11:3 References. Activate the card by pointer and keyboard. Check actual View all count and unchanged Notes. |
| [#143](https://github.com/icfmp/Bible/issues/143) | Only the redundant passage-picker close row is removed. | Open picker, dismiss by Escape, then by clicking outside. Reopen and select a chapter. Check reader position/focus and retained input. |
| [#145](https://github.com/icfmp/Bible/issues/145) | Strict local results precede bounded close French/English matches; quoted phrases stay strict, scope/negation/exact source text retained. | In Semeur search Car Dieu a tant aimé le monde: John 3:16 is a close match. Quote the phrase to require strict wording. Compare English KJV and a restricted book scope. |
| [#146](https://github.com/icfmp/Bible/issues/146) | Effective regional French labels; all 50 reviewed topics use the available picker height and remain reachable by keyboard/wheel. | Test French and English. Reach the last theme in a small window. Enlarge text and repeat. |
| [#147](https://github.com/icfmp/Bible/issues/147) | Delayed unchanged notifications retain selected results/preview; complete native previews fit enlarged text; source/license details remain accessible behind discreet OpenBible.info credit. | Select Love/Amour and activate first then second result. Reopen/change a theme and repeat by keyboard. Open source information and dismiss it without losing the picker. |

## Scope and fidelity limits

Resources are downloaded into isolated, marked validation profiles. No client
profile is reset or accessed. No complete Bible corpus is committed or bundled.
Source text, canonical ordinary offsets and installed module files are preserved.
FreChry's authored uppercase/italics and differing Psalm title numbering are
preserved. FreBDM1744 is a verified official representative; the client's exact
historical “Marbr1744” identity is not established.

Arabic reading/immersion is checked with a real downloaded YouVersion edition.
Automatic cross-edition alignment is unsupported for that source, so comparison
truthfully uses the existing independent mode.

Fresh OpenBible reference and topic archives have changed upstream since the
reviewed pins. Their acquisition remains rejected; no checksum bypass or silent
content update is included. Retained attributed relationship-only indices are
used for reproducible rendering checks. Real pinned places acquisition succeeds.

Cloud native GTK/Xvfb checks are developer evidence, not acceptance on the
client's GNOME desktop, hardware or compositor. Search cold indexing and native
result presentation have nonzero measured costs, documented with the captures.

Project 5 access remains forbidden by the GitHub integration:
“Resource not accessible by integration”. Issues remain open; no automatic
issue-closing development links or Done transition is used.

## Initial candidate and captures

- Reviewed feature source: `99b4689bfb575260ccb7cc9e526fb7876960ed2c`.
- Merged application source: `9fb9e3307294e8bf1113d65aec7f9756b8b4dfc0` ([PR 149](https://github.com/icfmp/Bible/pull/149)). Their complete Git trees are identical.
- [Green exact-head CI 41472220377](https://github.com/icfmp/Bible/actions/runs/41472220377): 405 tests (10 outside-package skips), 167 French UI tests, 211 installed Flatpak tests, 12 immersion tests and six selection/inline-marker tests; actual input, real study resources/offline restart and sustained scrolling also pass. These overlapping suites are not a count of unique cases.
- [Green installed before/after proof 41476084834](https://github.com/icfmp/Bible/actions/runs/41476084834): 18 application-import verification receipts and 337 original GTK screenshots. All checked source files remain unchanged. Actual places acquisition and native first/subsequent topic pointer/keyboard activation pass in French/English and enlarged text.
- [Selected original screenshots and gallery](GALLERY.md): 135 persistent images, including light/dark, narrow/wide, Sepia/Black and enlarged text states.

The build-info and checksums under installed-ci refer to the bundle in the
matching Actions artifact; a duplicate installable package is not included here.
Baseline bundle source 51d8efd and published previous main 83248ef have identical
Git tree 75a3f706df5c9d6967fcc72beec734e3af9794be. The before/after images use
installed master-channel test bundles; final retained-profile verification uses
the actual signed alpha channel separately.

Installed whole-Bible search results: Semeur's first search rebuilds only its
incompatible accent-normalization cache in 2.53 s; later measured searches take
0.43–0.57 s, including the harness's 0.2 s settling interval. KJV reuses its
compatible pre-update cache. Largest observed GTK heartbeat interval is 114 ms
when presenting strict KJV results; most other cases remain around 16–22 ms.
Cold KJV indexing was about 10.2 s in a separate local source run, not this warm
installed comparison. Search matching is local, French/English close matching
only, without semantic synonym recognition.

Installed wheel regression checks (Cairo/Xvfb, separate from later signed-channel
Vulkan consumption measurements) observed first movement at 0.56–0.84 ms and
first paint at 7.95–17.04 ms. Each simple/comparison/study/initial-toolbar case
moved during sustained input and recorded zero adjustments after 500 ms of
stopping. In the initially visible toolbar case, dismissal took 0.177 ms;
the backdrop was released and placement stopped before the first motion.

## Verified correction for native shader compilation

[PR 154](https://github.com/icfmp/Bible/pull/154), source `976a0e39c31c256656df4246261fe04d7debc6d1`, passes [ordinary CI 41526308283](https://github.com/icfmp/Bible/actions/runs/41526308283): 405 source tests (10 outside-package skips), 167 French UI tests, 211 installed Flatpak tests, 12 immersion tests and six selection/inline-marker checks. These suites overlap. The bundle SHA-256 is `e6d51485445301303aaf85846d8d0304f0706db0e3a17e82e45cc41080fbbd05`.

The initial main merge was blocked by a 494 ms direction change against the unchanged 400 ms limit, with one Bible, Study closed and the selection toolbar hidden. Installed A/B comparisons reproduced intermittent candidate pauses of 416–538 ms. A native profile ([41523430369](https://github.com/icfmp/Bible/actions/runs/41523430369)) captured a 450 ms gap with 440 ms of main-thread CPU and 83 user-CPU samples inside that exact gap: approximately 72% in LLVM and 20% in Mesa/Gallium. Stacks include `gsk_gl_device_use_program`, `gsk_gl_frame_use_program`, `gsk_gpu_shader_op_gl_command_n`, `llvm::MCJIT::emitObject` and native code generation. The measured cost is synchronous GSK/OpenGL shader compilation during paint; Python GC remained below 4 ms and no long native system wait explained the gap.

An alternating experiment ([41524487320](https://github.com/icfmp/Bible/actions/runs/41524487320)) isolated GTK's decorative overshoot halo on the unchanged installed candidate, with the Mesa disk shader cache disabled equally:

| Six trials | Maximum GTK gaps (ms) | Assertions |
| --- | --- | --- |
| Original edge glow | 24, 31, 492, 505, 22, 495 | Three failures |
| Only overshoot background/shadow removed transiently | 21, 22, 31, 21, 24, 22 | Six passes |

The production change scopes that removal to ordinary Bible, comparison and commentary scrollers. Native scrolling, inertia, scrollbars, synchronization, focus cues and the selection toolbar remain. No custom shader cache, performance setting, data migration or preference reset was introduced.

The final main bundle (`be7eeb8`, SHA-256 `1c019e318b5d35b3bf01a3f3288078f209430a10023083cadbb381e08067d42e`) passes all four **GLRenderer** sustained-input checks with the driver disk shader cache disabled. Original thresholds are retained:

| Scenario | Maximum GTK gap | Worst direction response | First movement / paint |
| --- | ---: | ---: | ---: |
| Single Bible, Study closed | 17.4 ms | 13.0 ms | 1.06 / 7.98 ms |
| Initially visible selection toolbar | 17.5 ms | 15.5 ms | 1.01 / 15.23 ms |
| Comparison | 17.3 ms | 18.9 ms | 0.56 / 17.88 ms |
| Wesley study open | 50.2 ms | 50.1 ms | 1.04 / 6.99 ms |

All four recorded zero adjustments later than 500 ms after stopping. Toolbar dismissal took 0.310 ms, releasing the backdrop and stopping placement before the first scroll paint. [Aggregate final-main receipt](main-ci/cold-scroll-summary.json) and [matching build information](main-ci/build-info.json) contain no raw input streams, source bodies or profile snapshots. Earlier unsuccessful collectors and the unresolved debugger stack are excluded from native function attribution.

The corrected installed before/after matrix passes [proof 41529836329](https://github.com/icfmp/Bible/actions/runs/41529836329), attempt 2, with 337 original GTK screenshots and 18 native-import receipts. The [corrected-package gallery](CORRECTED-GALLERY.md) retains 135 original light/dark, narrow/wide and enlarged-text captures plus aggregate verification receipts. Its packaged source and the final merged source have identical complete Git trees. The first comparison stopped while the map in the previous package did not settle within 40 seconds; the unchanged retry passed. The first signed-update wait expired before merge/publication; the final retained update below completed on the same profile across versions. Assertions were not relaxed.

This public report contains aggregate measurements only. Raw diagnostic traces are not added to this evidence branch. Cloud software-rendered X11 checks do not establish acceptance on the client's GNOME/GPU.

## Signed publication and retained update

- Application source: `be7eeb8f0511fd2c6b5b77ef31554bd8de7d9289`. Main CI [41582452296](https://github.com/icfmp/Bible/actions/runs/41582452296) passed.
- [Signed publication 41584806903](https://github.com/icfmp/Bible/actions/runs/41584806903), final revision `41584806903-2`.
- Final OSTree: `8ef2f00c20238804805c5d2bcd542481903fd4e361463016a9ff06ed0cfa8308`. Fingerprint: `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.
- Install/update: https://icfmp.github.io/Bible/alpha/Bible.flatpakref ; ref `app/io.github.icfmp.Bible/x86_64/alpha`, remote `bible-alpha`.
- [Actual signed update 41526437205](https://github.com/icfmp/Bible/actions/runs/41526437205) reused the same isolated profile: six real resources, one synthetic annotation, all 55 module-file hashes, unchanged preference bytes and all four installed study-dataset file hashes were checked before/after (attempt 2). See [the preservation receipt](signed-update/preservation.json) for aggregate preservation counts. Raw annotations and profile snapshots are not exported here. The client profile was never accessed or reset.

The initial main CI source stage timed out once waiting for the offline ISO language inventory; its prerequisite retry passed. Five consecutive local repeats passed in 3.4 seconds. The same initial run later stopped at the independently reproduced native rendering gate, corrected above. The final matching main CI is green. Assertions and timeouts were not relaxed.

## Consumption comparison on the retained signed profile

Both runs: GTK 4.20.4, renderer `VulkanRenderer`, 4 logical CPUs, scale 2; FreSegond1910 Psalm 119, comparison and Wesley commentary open, four scrollbar cycles. CPU is normalized to **one** logical core (divide by the CPU count for total-system percentage).

| Measurement | Previous signed alpha | Updated signed alpha |
| --- | --- | --- |
| Startup RSS (MiB) | 437.9 | 429.1 |
| Final RSS after four cycles (MiB) | 455.3 | 453.4 |
| Startup PSS (MiB) | 436.0 | 427.1 |
| Final PSS after four cycles (MiB) | 449.0 | 447.0 |
| Startup idle CPU (% of one logical core) | 5.3 | 7.0 |
| Scrolling CPU (% of one logical core) | 114.0 | 112.7 |
| After-scroll idle CPU (% of one logical core) | 4.6 | 5.1 |
| First movement (ms) | 2.18 | 2.36 |
| First paint (ms) | 3.84 | 3.96 |
| Adjustments later than 500 ms after stopping | 0 | 0 |

The updated RSS at the end of the four idle phases was 449.7, 450.7, 451.8 and 453.4 MiB. The reported rise to 1.91 GB was not reproduced in this bounded run; a few MiB of later growth remain, so this is not proof against long-term accumulation. Mean scrolling CPU is essentially unchanged in this software Vulkan workload: 112.7% of one core is about 28.2% of total capacity on four logical CPUs. The demonstrated improvement is the intermittent OpenGL shader-compilation pause, not a general CPU/RAM reduction.

The public table and [per-cycle consumption receipt](signed-update/consumption-summary.json) report aggregate measurements only; raw profiler and profile
snapshots are not copied to this evidence branch. Separate installed checks cover
single/comparison/study wheel input. This is a bounded software-rendered
CI regression check, not proof of performance on the client GPU/compositor or a
new general memory optimization. The large MHC source cases are separate rendering
checks, not this Wesley consumption benchmark. Hidden toolbar processing is
checked through backdrop release and stopped placement callbacks.

## Source and history audit

All 408 archived project files and all 4 dependency archives match the verified source/manifest. All 43 historical archive records are unchanged; the catalogue now has 44. The numbered tags are unchanged. Source archive SHA-256: `462fd6295431744f5d3da119512283dd051ed23d492fa28a1d91662d60252e62` (22959866 bytes). See [the source audit](publication-audit/verification.json).

## Manual project actions

Project 5 remains forbidden to the integration. Keep or move the eleven scoped
issues to In review under the current numbered-release gate while #87 is paused;
the signed alpha is available for client testing. Only the client sets Done and
closes issues. No numbered release or closure is substituted for unavailable
project access.
