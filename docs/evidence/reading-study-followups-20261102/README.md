# Native reading and study follow-ups

Delivery scope: issues 123, 118, 130, 139–143 and 145–147. Issue 138 was delivered
in the preceding YouVersion catalogue batch; number 144 is that batch's PR.
All implementation issues remain OPEN for client acceptance. Numbered release
87 remains paused by the client. No numbered tag or prerelease is created.

This report will be finalized only after installed candidate verification,
main CI, signed alpha publication and an actual retained-profile update pass.
It must not be read as evidence of a published batch before those checks.

## Changes and simple client checks

| Issue | Implemented behavior | Client checks |
| --- | --- | --- |
| 123 | Generic OSIS/ThML paragraph, poetry, heading and emphasis handling; verified generated markers are hidden without changing ordinary character offsets. Complete long source prefaces are available separately. | Compare F10/SBL Psalm 13 and F10 Genesis 2. Open MHC Genesis 1 source preface. Check FreAug/FreChry Psalm 13: authored capitals, literal punctuation and source numbering remain. |
| 118 | Chapter-only passage/tab labels; complete native translation selectors; existing actions in Header Bar with narrow-window and enlarged-font fallback. | Switch single/comparison reading. Resize the window and increase UI text size. Check both complete translation selectors and Aa without duplicate headings. |
| 130 | Bibles/Commentaries/Study tools in one Library, existing download services and independent category search/filter state. | Switch categories while a places download runs. Return to each previous query/filter. Existing reference/topic data remains usable; fresh upstream ZIPs are currently rejected when their reviewed pin differs. |
| 139 | Explicitly mapped commentary introductions are handled separately from ordinary verses, without clamping zero to one. | Read FRANCL Psalm 17:1 with MHC. Check actual source introduction and mapped ordinary coverage. Restart offline at the same passage. |
| 140 | Existing native raster map/cache uses an attributed French/Latin-readable style. | Open Shinar and Jerusalem. Check pan/zoom and readable context. English uses the available French/Latin fallback, not guaranteed English translations of every label. |
| 141 | Place/location/qualification hierarchy distinguishes approximate regions, precise points and candidate locations. | Compare Shinar/Babylonia with Jerusalem. Open Emmaus alternatives and Nod's unknown location. Resize each card and return to the studied passage. |
| 142 | Compact References cards share the passage Notes surface; complete normal-color references and three-line exact excerpts retain existing activation. | Open Genesis 11:3 References. Activate the card by pointer and keyboard. Check actual View all count and unchanged Notes. |
| 143 | Only the redundant passage-picker close row is removed. | Open picker, dismiss by Escape, then by clicking outside. Reopen and select a chapter. Check reader position/focus and retained input. |
| 145 | Strict local results precede bounded close French/English matches; quoted phrases stay strict, scope/negation/exact source text retained. | In Semeur search Car Dieu a tant aimé le monde: John 3:16 is a close match. Quote the phrase to require strict wording. Compare English KJV and a restricted book scope. |
| 146 | Effective regional French labels; all 50 reviewed topics use the available picker height and remain reachable by keyboard/wheel. | Test French and English. Reach the last theme in a small window. Enlarge text and repeat. |
| 147 | Delayed unchanged notifications retain selected results/preview; complete native previews fit enlarged text; source/license details remain accessible behind discreet OpenBible.info credit. | Select Love/Amour and activate first then second result. Reopen/change a theme and repeat by keyboard. Open source information and dismiss it without losing the picker. |

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

## Verified candidate and captures

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

## Current publication gate: native scroll pause

The merged application is not yet published to the signed alpha. Main CI
41477968873 observed a 494 ms direction change (400 ms limit) in single reading
with the toolbar hidden. The independent input process sent 48 events during
the 492 ms GTK pause. There was no movement later than 500 ms after stopping.

An installed A/B comparison used the exact verified old/candidate packages,
retained real resources and three runs per version:

| Version | Maximum GTK main-loop gaps in the three runs | Longest direction change |
| --- | --- | --- |
| Previous package | 18, 23, 19 ms | 20 ms |
| Candidate | 18, 416, 18 ms | 419 ms |

The candidate's second run failed its unchanged timing assertion. Completing
the diagnostic collection is not a passing publication gate. Python GC stayed
below 4 ms and callback profiles did not explain the pause. Native CPU analysis
is in progress. No product feature was disabled and no client profile was reset.
The signed-update waiting run was cancelled and will be restarted after the
blocking check is resolved. The previous signed alpha remains available.

A follow-up installed comparison ([41517637227](https://github.com/icfmp/Bible/actions/runs/41517637227)) attached the native sampler only after reader initialization and independently verified the Python 3.13 application process and its input child. All six measurements completed. Previous-package maximum GTK gaps were 30, 23 and 35 ms; candidate gaps were 528, 24 and 34 ms. During the 528 ms gap, main-thread CPU increased by 510 ms over a 537 ms sampling window; no traced native wait longer than 5 ms overlapped it. One direction response was missing in that candidate run; its unchanged assertions failed. The other five runs passed, and all six had zero late adjustments. This identifies native CPU work rather than a long system wait, but does not yet identify the responsible function. Earlier CPU/wait estimates from the host-supervisor sampler were invalid and are not evidence about the application. A time-correlated native function profile is the next check.

Native function attribution is now available from [41523430369](https://github.com/icfmp/Bible/actions/runs/41523430369): a candidate run paused for 450 ms, with 440 ms of main-thread CPU and 83 user-CPU samples inside the exact gap. Approximately 72% of self samples were in LLVM and 20% in Mesa/Gallium. Inclusive stacks contain `gsk_gl_device_use_program`, `gsk_gl_frame_use_program`, `gsk_gpu_shader_op_gl_command_n`, `llvm::MCJIT::emitObject` and `llvm::SelectionDAGISel::CodeGenAndEmitDAG`. This identifies synchronous native shader compilation during a GSK/OpenGL paint; it is not evidence of an expensive Python callback or a long system wait. The native selection toolbar was hidden. The responsible render primitive is still being isolated by a transient CSS comparison on the unchanged installed candidate. Earlier collectors with missing/incorrect symbol extraction, and the entirely unresolved debugger stack, are not used for function attribution.

The render primitive is isolated by [41524487320](https://github.com/icfmp/Bible/actions/runs/41524487320), alternating six controls and six transient CSS variants on the unchanged installed candidate. Both variants used a disabled Mesa disk shader cache. Controls recorded maximum GTK gaps of 24, 31, 492, 505, 22 and 495 ms; three failed their unchanged assertions. Removing only the native overshoot background/shadow produced 21, 22, 31, 21, 24 and 22 ms, all six passing, with a worst direction response of 29 ms and zero late adjustments. The three slow controls again sampled predominantly LLVM/Mesa compilation. This is diagnostic attribution, not proof of a packaged correction.

[PR 154](https://github.com/icfmp/Bible/pull/154), source `976a0e39c31c256656df4246261fe04d7debc6d1`, removes that decorative edge glow from Bible, comparison and commentary scrollers while retaining native scrolling and the existing selection toolbar. Nine local GTK checks pass. [Exact-source CI 41526308283](https://github.com/icfmp/Bible/actions/runs/41526308283) and [retained signed update 41526437205](https://github.com/icfmp/Bible/actions/runs/41526437205) are in progress. Final installed-package verification and signed publication remain outstanding; the currently published alpha has not been replaced.

This public report contains aggregate measurements only. Raw diagnostic traces
are not added to this evidence branch.
