# Verified scrolling-regression alpha delivery

Related to [#125](https://github.com/icfmp/Bible/issues/125), reviewed in [PR #131](https://github.com/icfmp/Bible/pull/131). The client explicitly authorized merging and signed-alpha delivery after the required checks. The PR is merged; the implementation issue remains OPEN for client acceptance. Numbered publication #87 remains PAUSED; no numbered prerelease was created.

Application source: `7a633f3281d0a6086cb822a1ac9f055beb53445b`. [Green main CI 40220519597](https://github.com/icfmp/Bible/actions/runs/40220519597); [successful signed publication 40221899923](https://github.com/icfmp/Bible/actions/runs/40221899923). Canonical alpha revision: **40221899923-2**. [Install/update channel](https://icfmp.github.io/Bible/alpha/Bible.flatpakref). Existing installation: `flatpak update --user io.github.icfmp.Bible//alpha`.

## What was verified

The native reader previously announced every viewport adjustment as a semantic source/passage change, repeatedly rediscovering installed resources and rebuilding navigation controls. In the unprofiled failing developer run, reader frames stopped during eight seconds of input and the adjustment continued catching up for 3.158 seconds afterward, including with one Bible, Study closed and no selection toolbar. The first cProfile run amplified the stall; its timing is not used as the decisive result. Its counts identified the expensive metadata/configuration path. An older same-resource/settings source remained responsive.

The focused application change persists viewport position through the existing session-save debounce without running the semantic update path. Passage/source changes and existing following remain active. No feature is permanently disabled; no data migration, appearance reset or resource deletion is introduced. [Actual GTK before/after videos, diagnosis and raw measurements](https://github.com/icfmp/Bible/blob/7a633f3281d0a6086cb822a1ac9f055beb53445b/docs/captures/regression-125/README.md).

Final main checks: **316 source tests, 143 French UI tests, 122 installed-Flatpak tests and 11 installed immersion tests**. These counts overlap and must not be summed as unique tests. Actual installed imports come from `/app/lib/bible-python`. Eight seconds of independent ~100 Hz XTest input with repeated reversals are followed by four seconds of observation. All four installed cases pass:

| State | Reader frame-clock callbacks during input | Maximum heartbeat gap | Worst reversal latency | Movement later than 500 ms |
| --- | ---: | ---: | ---: | ---: |
| Single Bible, Study closed | 681 | 13.7 ms | 11.2 ms | 0 |
| Shared comparison | 660 | 14.8 ms | 10.8 ms | 0 |
| Wesley study open | 172 | 150.1 ms | 132.9 ms | 0 |
| Selection toolbar visible | 685 | 13.3 ms | 9.8 ms | 0 |

[Installed results](main-verification.json), [single](packaged-scroll-single.json), [comparison](packaged-scroll-comparison.json), [study](packaged-scroll-study.json), [toolbar](packaged-scroll-toolbar.json). Source and packaged regressions also verify saved session position and preserved semantic navigation. The local Docker host denies Flatpak namespaces; actual installed tests run in the established CI environment, without weakened application confinement. These are developer Linux/X11/Xvfb checks, not the client's GNOME/Wayland or physical-device acceptance.

## Public update and preservation

[Final public verification](final-verification.json) matches the HTTPS public provenance to the exact green CI bundle and corresponding source archive. [Install receipt](public-install-check.json) verifies commit and summary GPG signatures and GTK startup. [Update receipt](public-update-check.json) verifies a real public update changes the installed OSTree commit and preserves all three validation sentinels (note, preference and local-resource files). This is not a claim to have inspected private client data.

Separately, a disposable profile from the older alpha was opened with the new application without network. Its actual note record, highlight, original preference bytes, selected tab/passages, SQLite schema and all 36 module-file hashes remained unchanged: [legacy-profile preservation](legacy-profile-preservation.json). The installed real-resource checks also preserve the existing note/schema and installed modules: [online](packaged-study-online.json), [offline](packaged-study-offline.json). Relevant note/draft/persistence regressions pass.

Stable identity retained: `app/io.github.icfmp.Bible/x86_64/alpha`, remote `bible-alpha`, signing fingerprint `47A17230403EA4953745E6E020EB9FFCCECAFD8F`. Canonical installed OSTree commit: `56d9a5cb2c52d41f7218ec4345aca46530787b5b5974bb56c652cdad7a9013b6`.

Bundle SHA-256: `c31ece2a487e61eecb7fbf0d158ce859501b589fffccd8754d2c21f193031a57`. [Corresponding original-source archive](https://github.com/icfmp/Bible/releases/download/alpha-source-archives/Bible-7a633f3281d0a6086cb822a1ac9f055beb53445b-sources.tar.gz), SHA-256 `5f9a8588851b5f86431c14e8cd48ee8e412350f72ebf295d8d1d64774062a36f`. All 330 project files and 3 original dependency source archives were verified. All 37 historical source records are unchanged (38 total). Source payloads remain outside Pages; managed Pages payload is 15392081 bytes. Numbered prereleases remain unchanged.

The two internal signed deployment revisions verify one application batch. This evidence-only branch does not rebuild or republish the application. Project 5 still returns `Resource not accessible by integration`; manual status requested is **In review** while numbered #87 remains paused under the current workflow. Only the client moves #125 to Done.
