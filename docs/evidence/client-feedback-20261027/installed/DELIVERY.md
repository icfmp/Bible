# Signed reading-feedback delivery — 1 November 2026

[PR #135](https://github.com/icfmp/Bible/pull/135) is merged and this batch is published on the existing signed alpha channel. Numbered release #87 remains paused; no numbered prerelease or tag was created. All twelve assigned issues remain OPEN for client acceptance.

- Published source: `d9c9791c509a3d51b334ddae5cbab2c2eebe9993`.
- Verified main CI: [41336913137](https://github.com/icfmp/Bible/actions/runs/41336913137): **372 source, 154 French, 175 installed-package, 12 immersion and 6 isolated marker/selection tests** pass, with native input, real resources and offline reopening.
- Signed publication: [41338894877](https://github.com/icfmp/Bible/actions/runs/41338894877), revision **41338894877-2**.
- Installed OSTree commit: `efc220cb7cd43d67b4881763b0ec688ba747b39cf5e5e8c43a3659fd6a54cfbb`.
- Stable signing fingerprint: `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.
- Bundle SHA-256: `4d0faf0a1466cba6f9192da727dbc9359538e4339f7725ceb7a00de26ab7760c`; independently matches the main package's retained [build-info.json](final-metrics/build-info.json).
- Actual retained-profile update: [41333835468](https://github.com/icfmp/Bible/actions/runs/41333835468); independent delivery/source/data audit: [41333856056](https://github.com/icfmp/Bible/actions/runs/41333856056).

Install from [the public signed Flatpak reference](https://icfmp.github.io/Bible/alpha/Bible.flatpakref), or update the existing user installation:

```sh
flatpak update --user io.github.icfmp.Bible//alpha
```

The public installation and revision-1-to-revision-2 update both pass. A separate client actually upgraded the previously delivered signed source d39a99e (OSTree 47d14bcb…) to this source and commit, preserving the same `bible-alpha` origin and application ref. Its existing profile was not reset: **one sentinel note, preferences, 37 translation/module files and all four study-data files are unchanged**. See [delivery.json](delivery/delivery.json), [the exact update receipt](delivery/signed/signed-update.json) and [the full persisted-data comparison](delivery/signed/preservation-comparison.json).

## Scope, images and client validation

The coordinated batch covers #97/#107, #99 before #98, #106/#104, #128, #102, #105, #75, #111 and the retained first increment of #114. [Per-issue implemented scope, actual checks, limitations and up to three client steps](CLIENT_CHECKS.md) are recorded separately.

[Final-source native before/after captures](final-visuals/) include light/dark, additional reading palettes/high contrast, narrow windows and large interface type. The feature source 112f42a9… and merged published source have **zero changed files**; [FINAL_REVIEW.json](FINAL_REVIEW.json) records that correspondence and both capture attempts. Actual installed Semeur/KJV John 1 has **51 verse bodies aligned to 0 px in full window coordinates** in light/dark. This corrects both source-heading padding and the residual 16–31 px viewport-origin offset missed by initial buffer-only assertions. First Notes reveal now highlights the displayed record while cancelled/failed-save switches preserve the previous selection and draft.

The old alpha's native marker click fails in the baseline capture; its failure is explicitly retained. The first final candidate attempt exceeded the 45-second wait for map readiness/retry. An unchanged-package repeat passes all six candidate sections and four actual Shinar/Haran light/dark map views; the first failed attempt is not discarded. This does not establish continuous availability of the external tile service. Actual map images retain OpenStreetMap/OpenBible attribution.

The [earlier installed divider checks](divider-candidate/) cover all eight palette/mode combinations, 8 px drag and keyboard resizing, saved width, hide/reopen and narrow collapse. Earlier [motion analysis](review/motion-analysis.json) and performance data identify their original source 30c151f8; the immersive focus/slide implementation is unchanged in the final source. Source-only evidence remains labelled separately.

Project 5 writes remain refused by the integration: **Resource not accessible by integration**. Keep assigned items **In review** under the paused numbered-release workflow; apply any client-directed validation status manually. Do not close issues or mark Done as a substitute.

## Actual signed update: bounded CPU, RSS and responsiveness

These are **same-profile real installed signed Flatpak** measurements on GTK 4.20.4, a software Vulkan renderer under composited Xvfb, scale 2, 24-point Segond Psalm 119, downloaded resources, KJV parallel and Wesley commentary. Four native scrollbar cycles compare previous/published combined reading. Additional modes use two native wheel cycles. CPU is process CPU with **one logical CPU = 100%**, not total-machine percent. RSS includes Python/native/process rendering allocations; it is not a Python-only heap figure.

| Signed case | Cycles | Startup → final RSS (MiB) | Mean CPU during gesture | Final idle CPU | Maximum loop interval | Changes later than 500 ms after stop |
| --- | --- | --- | --- | --- | --- | --- |
| previous combined | 4 | 432.0 → 467.6 | 121.0% | 9.1% | 147.0 ms | 0 |
| published combined | 4 | 425.2 → 450.2 | 119.0% | 7.7% | 88.3 ms | 0 |
| published single | 2 | 395.9 → 400.0 | 114.7% | 4.5% | 66.4 ms | 0 |
| published parallel | 2 | 402.8 → 407.2 | 123.4% | 4.3% | 71.3 ms | 0 |
| published study | 2 | 417.8 → 449.5 | 122.9% | 7.7% | 106.6 ms | 0 |

Combined startup-to-ready is **6.25 → 5.39 seconds**. First combined scrollbar movement/paint is **3.11/5.34 → 3.02/4.88 ms**. Frames are painted throughout sustained actions (published combined 286–303 paints per gesture cycle), directions reverse and all tested modes stop without late adjustment. These results show comparable CPU and bounded short-run RSS in this environment, not a broad CPU-performance cure or an indefinite memory plateau. Earlier [eight-cycle and GL ablation records](performance/) remain available with their original source labels; their measurements are not relabelled as a new final-source run.

Raw signed before/after and per-mode data are in [delivery/signed/](delivery/signed/). Instrumented Python-allocation profiling from the earlier A/B run materially changes timing and is not reported as ordinary UI latency.

## #102: first transition and native backdrop invalidation

The [exact published-source OpenGL receipts](final-metrics/client-feedback/) use actual independent native wheel input. With the selection bar initially shown: dismissal handler **0.234 ms**, input-to-dismiss start **0.195 ms**, first text motion **0.835 ms**, first GTK paint **14.347 ms**, maximum loop interval **17.515 ms**, zero intervals over 100 ms and zero changes after the 500 ms stop margin. The backdrop is released and placement stopped before the first motion; the bar is absent from that first painted scroll frame. Fifteen direction changes respond within **15.2 ms**. With the bar initially hidden, first motion/paint is **1.031/7.954 ms**, maximum loop interval **18.473 ms**, with zero late changes. Real first scrollbar-press dismissal is also covered by the six isolated installed marker/selection tests.

[Final native cache/invalidation counters](final-metrics/live-backdrop-impact.json) show **zero snapshot/changed/adapt/watch calls** for unchanged visible content and for the hidden bar. A deliberately programmatic adjustment that keeps the bar visible while changing its background costs **197.3%** of one logical CPU versus **33.1%** without it; this is a diagnostic condition, not native manual scrolling, which dismisses it first. After dismissal the same diagnostic adjustment costs **34.1%**, with zero bar calls. The expensive forced-visible result is retained rather than hidden.

Real interface/backdrop rendering uses **GTK/GSK**. Cairo is used by some headless checks, and the existing PangoCairo font-options interface measures pagination fonts. No Cairo backdrop renderer or custom periodic cache infrastructure is introduced.

## Sources and remaining limits

The [published corresponding-source archive](https://github.com/icfmp/Bible/releases/download/alpha-source-archives/Bible-d9c9791c509a3d51b334ddae5cbab2c2eebe9993-sources.tar.gz) matches SHA-256 `ee9d76fb76ef6aeb01bc099e2c367f406d0471654b3453d9f1abad2d49b15aed`. Independent audit compares all **389 project files** byte-for-byte against the actual merged commit and verifies the four pinned dependency archives against its manifest. All **41 previous source-archive records** are unchanged; the catalog now has 42. Existing numbered prereleases remain alpha.1, alpha.2 and alpha.3.

The managed local execution environment failed to start; final validation ran through GitHub Actions on actually installed Flatpaks. Xvfb/software rendering does not prove the client's GNOME/Wayland, fractional scaling, physical touchpad, hardware GPU or long-session behaviour. The measured CPU remains substantial during software-rendered gestures.

Changed mutable OpenBible reference/topic downloads are still correctly refused by existing integrity pins. Both comparable profiles reuse the same previously validated installed indexes without weakening production checks; fresh optional reference/topic downloads are not claimed as passing. Existing data and translations remain intact.
