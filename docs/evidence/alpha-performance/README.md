# Installed-alpha CPU and memory investigation — 26 October 2026

Status: investigation and candidate validation, **not a delivered or client-accepted fix**. Graphical finishing and issue #26 are paused; numbered release #87 is paused. Client data is not available in the cloud environment and has not been reset or changed.

The client reports approximately 700–762 MB at startup, a logical CPU saturated after the first mouse-wheel or native scrollbar gesture, later 1.91 GB, and a temporary GNOME unresponsive warning. Their startup configuration is one tab with comparison and Study open together, with maps/references/other optional study resources installed. They cannot currently confirm the selected Study tool. Translation, passage, scale, GPU/driver and exact installed commit remain unconfirmed.

## Verified published inputs

| Input | Source | Signed alpha | Signed OSTree commit | Verified original CI bundle |
| --- | --- | --- | --- | --- |
| Previous | `7a633f3281d0a6086cb822a1ac9f055beb53445b` | 40221899923-2 | `56d9a5cb2c52d41f7218ec4345aca46530787b5b5974bb56c652cdad7a9013b6` | [40220519597](https://github.com/icfmp/Bible/actions/runs/40220519597) |
| Current | `758fb1600b00027b47ac0f4998f34bed6806d8e5` | 40267227219-2 | `d0d8a6309e3f75d87e1892d23c3f2efd2c99843e44a8c60fffdb1a8a87de33ce` | [40265503566](https://github.com/icfmp/Bible/actions/runs/40265503566) |

Previous bundle SHA-256: `c31ece2a487e61eecb7fbf0d158ce859501b589fffccd8754d2c21f193031a57`. Current bundle SHA-256: `d8d5eeb9ca0e9349d2b7fe36dfc7ebe8a96e4993997678e6437c0f396b5f3b87`.

The initial A/B/previous-repeat uses actual signed public alpha installs. After two HTTP 503 failures fetching the public repository in later jobs, extended diagnostics install the verified original CI master bundles whose application code was imported into the corresponding signed alphas. These are distinct test scopes; CI refs are not described as signed-alpha installations. Candidate packages are feature-branch CI refs until a signed deployment and update are separately verified.

## Measurement method

Each test uses actual `/app/lib/bible-python` imports and records their paths/hashes and GTK renderer. A persistent disposable profile contains real downloaded translations and a real validation note. It is retained across version switches and repeated cycles. No forced garbage collection, allocator trimming or profile reset is performed. Four real SWORD resources are used: FreSegond1910, FreBDM1707, KJV and Wesley.

An independent XTest process sends sustained input at approximately 100 Hz, with repeated direction changes. It samples process-wide CPU and `/proc` RSS/PSS/anonymous memory every 200 ms. **100% CPU means one logical CPU**, equivalent to approximately 25% total on a four-thread machine. CPU includes native renderer workers. Memory is process resident memory, not GPU VRAM or an unspecified desktop monitor's application/cgroup total. Values below use MiB (1,048,576 bytes).

An initial six-second idle period is followed by eight seconds of input and six seconds after stopping, repeated without restarting the process. A passive frame-clock after-paint observer does not add a tick. The GTK heartbeat runs every 50 ms, so its maximum interval includes the normal 50 ms polling period. Adjustment timestamps prove viewport movement independently of frame-clock observations; later reports also record first movement/paint, first visible-toolbar dismissal and adjustments later than 500 ms after release.

Python cProfile/tracemalloc and native-allocation profiling are separate diagnostic runs: their amplified timings are not used as decisive consumption or responsiveness measurements. Native CPU sampling must target the actual packaged Python process, not Flatpak's sandbox init/wrapper. A successful workflow step alone does not establish usable profiling data.

## Before application changes

Full selected summaries, including per-cycle RSS/PSS/anonymous memory and CPU, are in [baseline-summaries.json](baseline-summaries.json). Raw samples and logs are retained in the linked workflow artifacts.

| Installed scenario | Previous startup → final RSS | Current startup → final RSS | Scroll CPU, one core |
| --- | ---: | ---: | ---: |
| Signed alpha, scale 1, 14 pt, Psalm 119, four cycles | 332.0 → 343.6 MiB | 303.0 → 344.8 MiB | roughly 33–38% |
| Exact CI bundles, scale 1, 24 pt, FreBDM Genesis 6, twelve cycles | 329.6 → 371.7 MiB | 299.1 → 366.4 MiB | roughly 24–30% |
| Exact CI bundles, scale 2, 24 pt, native scrollbar, eight cycles | 379.5 → 392.5 MiB | 350.0 → 409.0 MiB | roughly 105–108% for both |

The signed previous-repeat ends at 322.9 MiB. Scale-two first scrollbar movement is approximately 3.7 ms and first paint approximately 5.7 ms in both sources. The developer environment can reproduce a saturated logical CPU while scrolling at scale two with software rendering in both published builds. It has not reproduced the client's 1.91 GB or multi-second hang. These findings do not identify the client's GPU/renderer or establish that their reported regression is absent.

Signed A/B: [40289934685](https://github.com/icfmp/Bible/actions/runs/40289934685), artifact 12635478798, SHA-256 `db1e3fe915a416bc63121b1e7e21436ebbc7a108735cc9603ef0f9749b3e9924`. All nine measurements succeeded; the job failed a receipt-only list/tuple normalization assertion. That assertion was corrected, not relaxed, in later preservation checks.

Extended/native: [40293965351](https://github.com/icfmp/Bible/actions/runs/40293965351), artifact 12637278581, SHA-256 `965080e55141ece17e85690a3c7f405f8f1a0ea573841e307455d0c6855c1e52`. Consumption, native allocations and normalized preservation succeeded; native CPU sampling failed before recording because the executable search did not follow a symlink.

Scrollbar/scale two: [40296371345](https://github.com/icfmp/Bible/actions/runs/40296371345), artifact 12639245927, SHA-256 `e3d71fa92b6bcb4b216249d4af2f3dfdde66feb853d51b4157383d2837b56095`. Consumption, native allocations and preservation succeeded. The old perf step targeted a sandbox wrapper and used an unsupported `tid` sort key; its output is **not a valid native CPU profile**.

## Measured work addressed by the candidate

- Three permanent layout ticks execute even when geometry and content are unchanged. Native geometry/adjustment/appearance invalidations now request bounded settling and stop on unmap. Reader anchors, comparison alignment, sidebar resizing and caption adaptation remain active.
- Following a verse with Study open repeatedly parses the same translation configurations and provenance. A separate Python profile counted 212 resource metadata reads for two semantic updates. The immutable results are now stored in a standard bounded LRU of 128 entries; both file revisions invalidate the result. Completeness, removal and source identity checks remain active. No Reader or Library object is retained by this cache.
- The closed passage selector rebuilds book/chapter/search widgets during verse following. Defer those rebuilds until opening, while retaining initial and tab/source context updates and forced refresh on opening.
- Already-hidden selection actions avoid repeated native popdown/backdrop teardown; delayed selection capture still gets cancelled.

These changes target measured unnecessary work. They do not justify claiming the client's severe memory regression is resolved before installed candidate measurements and desktop acceptance.

## Blur and allocations

Signed-alpha runs with the toolbar initially visible compare native blur, radius zero and the complete backdrop disabled in the test process only. Scroll CPU remains approximately 31–36% of one core; no basis was established to attribute the reported regression to blur. Hidden toolbar profiles show no continuing backdrop snapshot/invalidation/layout work. Candidate tests separately measure the first dismissal transition. Blur rendering and preferences are unchanged by this correction.

Python traced memory in the separate baseline profile is about 13–15 MiB, much less than total RSS. Native memray stacks identify retained Vulkan/llvmpipe swapchain, JIT, GSK node processor and shader caches. Retained caches at tracker/process end are not by themselves proof of a leak. Instrumented memory/time overhead is explicitly excluded from normal-run conclusions. No forced collection or cache purge is used to manufacture a plateau.

## Optional resource reproducibility

The final combined scenario includes STEP words, places/maps, OpenBible cross-references and topics. The live weekly topic archive changed and was correctly rejected by the published application's pinned checksum in runs 40302528970 and 40303071642; those runs stopped before measurements and preservation receipt creation. The application validation was not weakened. Tests now reuse the [attributed, previously validated installed topic index](fixtures/README.md), verifying both compressed and database hashes before first use. They preserve its bytes across all version switches/cycles, together with the other study databases, module files, reading preferences and note.

## Candidate verification

Candidate application: [PR #133](https://github.com/icfmp/Bible/pull/133), source `f74b09267f3b02850095af674d3a35ac5791829f`. [Application CI 40324387706](https://github.com/icfmp/Bible/actions/runs/40324387706) is green: 328 source tests, 144 French UI tests, 136 installed-Flatpak tests and 11 installed immersion tests; counts overlap. Actual installed OpenGL captures and existing sustained-input/study checks also pass.

A subsequent workflow-only repair at `dae8929aa44e59f501494e1fcf54f12d9bd6b1fd` avoids reinstalling the same baseline bundle before the first case. The earlier normal/native jobs stopped before measurement with `io.github.icfmp.Bible already installed`; their preservation checks passed, but their measurements are not claimed. The repaired performance workflow uses the already verified application build above and asserts that every application/build/test/tool file at its own head is identical to that build's source; only its workflow file may differ. Exact-head [CI 40328540462](https://github.com/icfmp/Bible/actions/runs/40328540462) is additionally running.

Installed baseline/candidate performance: [40328432157](https://github.com/icfmp/Bible/actions/runs/40328432157). Combined native allocations: [40328445407](https://github.com/icfmp/Bible/actions/runs/40328445407). Combined native CPU and resident mapping breakdowns: [40328445423](https://github.com/icfmp/Bible/actions/runs/40328445423). These measurement jobs are still running at this report snapshot; final measured results and exact artifact digests remain pending. No signed correction has been published.

The later source-only CPU investigation also found that every canonical reference reconstructed all 85 French normalized book aliases. Reusing the static table preserves all 260 checked French/case/OSIS variants. An external cProfile run without tracemalloc counted 20,157 canonical lookups and 1,733,569 normalizations before, versus 28,952 lookups and 29,104 normalizations after. These are diagnostic call counts, not unprofiled performance timings; native GI/thread callbacks give misleading blocking cumulative wall times for some profiler rows. A separate unprofiled, same-source process-only ablation reduced scroll CPU from 86.9/91.9% to 83.4/84.8% of one core, and the maximum heartbeat intervals from 138/142 ms to 123/94 ms. Those are exploratory source GL results, not the final installed or client result. Their variable RSS does not establish resolution of the 700 MB startup report.

## Optional client-side read-only capture

If the severe discrepancy remains specific to the client's machine, [collect-client.py](collect-client.py) can record the existing running Flatpak without changing its profile. It records version/GPU IDs, selected graphics environment settings, process RSS/PSS/high-water memory and CPU/thread counters. Where available it separately records the Bible-specific cgroup's memory and file cache, so a desktop monitor's app total can be compared with process memory. It records no notes, preferences, translation contents, full environment, host name or network traffic, uses no sudo, and refuses to overwrite its output.

Example after downloading/reviewing the script, with Bible already running: `python3 collect-client.py bible-performance.json --seconds 120`. Leave Bible idle briefly, use the wheel and scrollbar with direction changes, then stop and leave it idle. This is an optional way to capture the actual desktop discrepancy when the client is back at their computer, not a required replacement for developer testing. The helper's argument parsing and own-process `/proc` reads were smoke-checked here; it has not been verified on the client's Flatpak or claimed to diagnose their device already.
