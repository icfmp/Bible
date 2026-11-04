# Selection, study and download feedback — issues 150–160

Signed alpha `41782176034-2` is published and its actual Flatpak update is verified.
[PR #161](https://github.com/icfmp/Bible/pull/161) is merged. Issues remain OPEN
for client validation; #151 is unconfirmed and #153 is partial (NBS delivered,
NFC still unsupported). Numbered release #87 remains paused.
PR #154 was already published in the baseline and is preserved.

## Baseline and evidence

The baseline is source `be7eeb8f0511fd2c6b5b77ef31554bd8de7d9289`, published as
signed alpha `41584806903-2`. The exact verified CI Flatpak bundle from run
[41582452296](https://github.com/icfmp/Bible/actions/runs/41582452296) was installed
in an isolated Flatpak directory. Checks imported Bible from `/app`, with GTK
4.20.4 and software OpenGL. These are actual native GTK screenshots, not mockups,
web rendering or edited composites.

The complete baseline visual run
[41692356499](https://github.com/icfmp/Bible/actions/runs/41692356499) produced 75
original PNGs. The download screenshots below come from the additional normal
Library pointer run [41698786237](https://github.com/icfmp/Bible/actions/runs/41698786237),
which selected the actual YouVersion edition row and clicked its real download
button and source acknowledgement. No publisher agreement is submitted or claimed.

Baseline reproduction confirmed:

- NBS 104 fails conversion; NFC 2367 fails indexed-chapter validation.
- BDS → LSG switches from the tested Genesis/Psalm passages reset to Genesis 1.
- Direct YouVersion LSG Genesis 1 has no verified MHC alignment.
- Study References exposes 5 of 19 actual Genesis 11:3 relationships initially.
- The previous word-study surface replaces the active study tool.

## Scope and limits

The update uses direct existing highlight colors, a native lexical window,
flat public-code Header Bar selectors with one-line titles and the existing
main menu retaining tools at minimum widths, full reference lists, one virtualized
place body and simplified native search results. Exact verse correspondence is
kept separate from an available-chapter fallback during explicit source opening.
A reference-only content audit verifies 31,098 LSG verses; 72 remain unmapped.
The new logo already merged through #162 is retained. Its non-square scalable
icon blocked Flatpak export on main; the application SVG now has a square canvas
with transparent horizontal padding, preserving every drawing element.

NBS's complete local native conversion/readback and independent HTML/DOM audit
verified 1,189 chapters, 56 introductions, 31,169 verse units and 27,682 notes.
The final installed run acquired NBS through the real Library button and
reopened it with network access unshared at Genesis 1, Numbers 1, Judges 1,
Psalm 119 and Revelation 22. The source archive matches the independent audit;
all 1,245 worker entries are verified and 55 installed resource files are unchanged.

NFC is **still unsupported as a complete lossless installation**: its Sirach
prologue/chapter sections overlap verse identities, and chapter 43 interleaves
fragments of verse 17 around verse 16. No source text is discarded, reassigned or
partially installed to manufacture success. Its issue remains open.

The reported #151 crash is **not confirmed fixed**. There were no crashes or
Python exceptions in 51 actual pointer activations on the installed baseline,
including complete OSIS lexical units, multi-verse selections, BDS and missing/
present STEP data. In KJV, `was`, `the Word` and `the beginning` supply actual
lexical identifiers; the partial selection `beginning` correctly does not.
The client-specific trigger/build is still needed. The popup redesign is not
proof of a root-cause fix. A separate captured-selection mismatch was reproduced
and corrected without guessing lexical associations; regression checks verify
that captured text cannot receive a later selection’s identifiers. Opening all
lemma occurrences keeps focus in the search entry.

At the minimum width with large UI text, passage titles can ellipsize; their
complete reference remains in the existing tooltip and accessible name. Very
short public translation codes receive their native minimum width;
longer labels can ellipsize while retaining their full accessible name.

The reference/topic indices are the existing, previously validated pinned
snapshots. This test does not validate fresh acquisition of today's mutable
OpenBible archives, which no longer match the unchanged source pins.

These automated X11 checks do not establish behavior on the client's GNOME
session, graphics driver or private profile. No private user profile, raw corpus,
SQL database, native trace or diagnostic dump is published here.

## Published source and retained update

- Merged source: `39449e0743c8e8b6fb03fbfc30a7d259046502f3`.
- [Green main CI](https://github.com/icfmp/Bible/actions/runs/41779503655): source
  tests, 169 French tests, 234 installed GTK tests, real/offline resources,
  sustained native scrolling and OpenGL checks. The source run has 410 tests,
  including 10 expected skips; native map requirements are enforced in the package.
- [Signed publication](https://github.com/icfmp/Bible/actions/runs/41782176034),
  final revision `41782176034-2`.
- [Corresponding software source archive](https://github.com/icfmp/Bible/releases/download/alpha-source-archives/Bible-39449e0743c8e8b6fb03fbfc30a7d259046502f3-sources.tar.gz), SHA-256
  `38b282c6a84d692f55364bcad07236010e6d9ea40799ff09eb58b1a60140a9b5`.
- Verified CI bundle SHA-256: `01e67ec08f8061f3a142d3e505a63122f61229a9ac23543dc1570a522afa432a`.
- Installed Flatpak commit:
  `cc68b9d2eb9d79ba7dafe7f544247a19dea9f64c2387352364196a2d125fdd28`.
- Stable signing fingerprint:
  `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.
- [Actual retained-profile update](https://github.com/icfmp/Bible/actions/runs/41778559731):
  origin `bible-alpha` and ref `app/io.github.icfmp.Bible/x86_64/alpha` are unchanged;
  the installed commit advances from
  `8ef2f00c20238804805c5d2bcd542481903fd4e361463016a9ff06ed0cfa8308`.
  One existing note, an existing highlight, reading preferences, all 55 resource
  files and the installed study databases pass preservation checks. No client
  profile was accessed. The disposable validation profile was kept across update.
- All 44 historical source records remain unchanged; the new source makes 45.
  Existing numbered alpha tags are unchanged. No numbered prerelease was created.

The final candidate also passed 75 original screenshots, 24 lexical activations
with STEP present/absent, native book/chapter/keyboard/narrow-menu interactions,
NBS acquisition through the real Library action, and offline reopening. The
source archive installed for NBS matches the independent audit:
`ef1994bc91039b972c157c50f577ec4cf3b8a1d392f5fcbb1f872dd9035fc694`.

## Scroll measurements and limits

The signed comparison uses the same retained profile and real resources:
FreSegond1910 at Psalm 119, KJV in parallel and Wesley in Study. Geometry is
1180 × 780 logical pixels, scale 2, on a four-vCPU runner with a **software Vulkan
renderer**. Each signed version receives four native scrollbar cycles with
changes of direction and idle periods. These are single paired runs, not a
statistical benchmark or a measurement of the client's graphics driver. CPU is
process CPU: **100% means one logical core** (divide by four for this runner's
total CPU capacity). No renderer ablation, forced GC or memory trim is used.

| Signed version | Ready RSS (MiB) | Peak RSS (MiB) | Scroll CPU (% of one core) | Post-scroll CPU (% of one core) | First movement / paint (ms) | Changes >500 ms after stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Previous 41584806903-2 | 438.9 | 464.2 | 111.7 | 5.9 | 2.58 / 4.98 | 0 |
| Updated 41782176034-2 | 426.3 | 452.2 | 114.2 | 4.8 | 2.53 / 4.17 | 0 |

The updated combined-mode idle RSS after each cycle is **451.4, 451.7, 452.1,
452.2 MiB**; the previous version's values are **459.8, 461.4, 464.1, 462.8 MiB**.
The largest observed scroll heartbeat gap is 96.9 ms updated versus 141.7 ms
previous (the heartbeat itself runs every 50 ms). No delayed adjustment is
observed after stop. Four cycles do not prove the absence of a long-session
leak. CPU during software rendering remains high and is not evidence of low
CPU use on the client's machine; the small before/after difference should not
be treated as statistically significant.

Two native wheel cycles per additional updated mode also pass:

| Mode | Ready / peak RSS (MiB) | Scroll CPU (% of one core) | First movement / paint (ms) | Changes >500 ms after stop |
| --- | ---: | ---: | ---: | ---: |
| Single | 398.0 / 400.4 | 94.9 | 1.14 / 19.89 | 0 |
| Comparison | 405.0 / 407.9 | 105.5 | 0.71 / 21.95 | 0 |
| Study | 419.6 / 436.2 | 114.6 | 1.13 / 10.10 | 0 |

Every signed mode ends with the selection toolbar hidden, its backdrop released
and its placement callback stopped. Its installed `ui.py` hash matches the
merged source.

The separate installed **OpenGL** check on main disables Mesa's shader disk
cache and begins with the selection toolbar visible. The first native wheel
event begins dismissal at **0.173 ms**, completes it in **0.264 ms**, moves text at
**0.982 ms**, and produces the first GTK paint at **18.14 ms**. The bar is already
hidden in that first scroll paint and there are zero adjustments more than
500 ms after stop.

The OpenGL backdrop diagnostic uses six seconds per phase. It records zero
`do_snapshot`, `changed`, `adapt` and `watch` calls both with an unchanged visible
background and after dismissal, including subsequent programmatic motion. The
bar is recaptured only when its visible background changes (359 snapshots in
that deliberate moving-background diagnostic). This diagnostic uses a profiling
observer; its CPU figures are not presented as normal wheel consumption.
The blur effect uses GTK/GSK without a custom Cairo paint loop. A separate
scroll check uses CairoRenderer as a test backend; the real blur checks use
OpenGL and the signed performance comparison uses Vulkan. Screenshots use software OpenGL, independently of the Vulkan benchmark.

## Install or update

[Signed alpha installation](https://icfmp.github.io/Bible/alpha/Bible.flatpakref).
For an existing user installation, run
`flatpak update --user io.github.icfmp.Bible//alpha`; use `--system` for a system
installation. Keep the existing application profile and downloaded resources.

## Original before/after screenshots

Every linked PNG is an unchanged root-window capture from the installed Flatpak.
The candidate source is `9f8076207e8e1b444637d5b36c4714fb62aa8076`, verified by
[CI 41743945233](https://github.com/icfmp/Bible/actions/runs/41743945233) and
[installed run 41778556261](https://github.com/icfmp/Bible/actions/runs/41778556261).
Its complete Git source tree is identical to the merged application at
`39449e0743c8e8b6fb03fbfc30a7d259046502f3` (tree
`64a97efb7e3e3a7ea50914e1814e475938a70632`). Both screenshot runs use GTK 4.20.4
and software OpenGL. Full original runs also include high contrast and multi-verse
selection; the gallery below retains 35 original captures from each version.

| Surface | Light, 1280 px | Dark, 1280 px | Light, 560 px | Dark, 560 px |
| --- | --- | --- | --- | --- |
| Header | [Before](before/light-1280-header.png) · [After](after/light-1280-header.png) | [Before](before/dark-1280-header.png) · [After](after/dark-1280-header.png) | [Before](before/light-560-header.png) · [After](after/light-560-header.png) | [Before](before/dark-560-header.png) · [After](after/dark-560-header.png) |
| Selection toolbar | [Before](before/light-1280-selection.png) · [After](after/light-1280-selection.png) | [Before](before/dark-1280-selection.png) · [After](after/dark-1280-selection.png) | [Before](before/light-560-selection.png) · [After](after/light-560-selection.png) | [Before](before/dark-560-selection.png) · [After](after/dark-560-selection.png) |
| Word study | [Before](before/light-1280-word-study.png) · [After](after/light-1280-word-study.png) | [Before](before/dark-1280-word-study.png) · [After](after/dark-1280-word-study.png) | [Before](before/light-560-word-study.png) · [After](after/light-560-word-study.png) | [Before](before/dark-560-word-study.png) · [After](after/dark-560-word-study.png) |
| Text search | [Before](before/light-1280-text-results.png) · [After](after/light-1280-text-results.png) | [Before](before/dark-1280-text-results.png) · [After](after/dark-1280-text-results.png) | [Before](before/light-560-text-results.png) · [After](after/light-560-text-results.png) | [Before](before/dark-560-text-results.png) · [After](after/dark-560-text-results.png) |
| Topics | [Before](before/light-1280-topic-results.png) · [After](after/light-1280-topic-results.png) | [Before](before/dark-1280-topic-results.png) · [After](after/dark-1280-topic-results.png) | [Before](before/light-560-topic-results.png) · [After](after/light-560-topic-results.png) | [Before](before/dark-560-topic-results.png) · [After](after/dark-560-topic-results.png) |
| Study References | [Before](before/light-1280-references.png) · [After](after/light-1280-references.png) | [Before](before/dark-1280-references.png) · [After](after/dark-1280-references.png) | [Before](before/light-560-references.png) · [After](after/light-560-references.png) | [Before](before/dark-560-references.png) · [After](after/dark-560-references.png) |
| Place | [Before](before/light-1280-place.png) · [After](after/light-1280-place.png) | [Before](before/dark-1280-place.png) · [After](after/dark-1280-place.png) | [Before](before/light-560-place.png) · [After](after/light-560-place.png) | [Before](before/dark-560-place.png) · [After](after/dark-560-place.png) |
| Last place reference | [Before](before/light-1280-place-last-reference.png) · [After](after/light-1280-place-last-reference.png) | [Before](before/dark-1280-place-last-reference.png) · [After](after/dark-1280-place-last-reference.png) | [Before](before/light-560-place-last-reference.png) · [After](after/light-560-place-last-reference.png) | [Before](before/dark-560-place-last-reference.png) · [After](after/dark-560-place-last-reference.png) |

Additional pairs: [360 px / large text — before](before/narrow-360-large-text.png),
[after](after/narrow-360-large-text.png); [NBS — before](before/download-104.png),
[after](after/download-104.png); [NFC — before](before/download-2367.png),
[after](after/download-2367.png). The NBS is installed; the NFC pair records an
explicit remaining failure, not a successful installation.
