# Sustained scrolling regression #125

[Before: actual GTK recording](before.mp4) · [After: actual GTK recording](after.mp4). These are twelve-second Xvfb recordings, captured by a separate process at 15 fps. An independent XTest process supplies eight seconds of repeated opposite-direction wheel input at approximately 100 events/s; the final four seconds show release/settling. No screenshots or Scripture text were synthesized. Virtual-display checks do not establish acceptance on the client's GNOME desktop or their unknown physical input device.

## Reproduction before changing application code

Source `48b8148e682741d137c2d0c6f189dcdd6bef95c9`, real installed FreSegond1910 Psalm 119, 1170×770 client area, default 14 pt DejaVu Serif / narrow column / very-airy spacing, six installed Bible/commentary resources, system animations enabled, Cairo renderer. Single Bible, comparison absent, Study closed and selection toolbar hidden. Tests use disposable profiles and identical immutable resource files/settings; no client data or preferences were reset.

At 25 wheel events/s, unprofiled runs remained responsive. At approximately 100/s, the **unprofiled** current source produced zero GTK reader frame-clock callbacks during eight seconds of input and continued changing its adjustment **3.158 s** after input stopped. [Raw failing measurement](current-high-plain.json). A same-resource/settings run at older source `275fe84` (before the pane-local version controls) produced 220 callbacks during input, with no adjustment changes after 500 ms: [older comparison](old-high-plain.json). This is an observed developer baseline, not a claim about the client's exact last-good build.

The first cProfile run amplified the slowdown; its timing is excluded from the decisive comparison. Its call counts identify the path: 168 `ReadingTab.scroll_changed` calls triggered 168 `Window.tab_changed` / `update_navigation` refreshes, **10,248 resource metadata reads**, four version-chooser synchronizations per viewport notification, plus hidden comparison/study discovery. [Profile](current-single.profile.txt). Resource configuration parsing and filesystem scans occupied the Python callback. GTK input continued updating adjustments but paint frames were starved, and obsolete native input accumulated. Neither an open study panel, comparison nor a visible blurred selection toolbar was necessary.

## Focused correction

A viewport-only callback now persists the latest scroll fraction through the existing session-save debounce. It no longer announces a semantic source/passage change. Actual source/passage changes still call the existing `changed` handler; synchronization, correspondence groups, selection actions, chapter commentary/Notes and all appearance controls remain active. There is no resource-metadata cache with new invalidation rules, no performance preference and no data migration.

| Unprofiled corrected scenario | Reader frame-clock callbacks during input | Maximum GTK heartbeat gap | Adjustment changes later than 500 ms |
| --- | ---: | ---: | ---: |
| Original long down/up/down gesture | 527 | 15.8 ms | 0 |
| Repeated reversals, single Bible | 563 | 44.9 ms | 0 |
| Shared comparison | 525 | 29.3 ms | 0 |
| Wesley commentary open | 174 | 158.5 ms | 0 |
| Selection toolbar visible | 529 | 18.4 ms | 0 |

[Original corrected run](fixed-high-plain.json), [reversal/single](fixed-reverse-single.json), [comparison](fixed-reverse-comparison.json), [study](fixed-reverse-study.json), [toolbar](fixed-toolbar.json). The later study/toolbar measurements also record each reversal's latency: worst observed 194 ms with study and 9 ms with the toolbar. Earlier files predate the reversal-latency field and do not claim that extra metric. The recording pair uses a repeated-reversal gesture with matched capture overhead; its data are [before](record-before.json) / [after](record-after.json). Recording adds overhead and the failing run still had queued input when observation ended; do not substitute that run for the unprofiled 3.158 s timing.

## Regression and installed validation

`tests.test_scroll_position` drives the actual native adjustment, checks zero resource metadata/navigation rebuilds for viewport movement, verifies the saved session fraction and confirms that a real verse change still updates navigation. Eight focused viewport/comparison/commentary checks passed locally.

`tools.check_sustained_scroll` uses a separate input process, records exact input timestamps, adjustment/visible-position samples, frame-clock callbacks and 10 ms heartbeat gaps. It checks movement throughout input, each reversal within 400 ms, at least 80 callbacks during the gesture, no adjustment changes after 500 ms and no main-loop gap over 500 ms. CI runs it against `/app` imports in the actually installed Flatpak, using real resources, for single Bible, comparison, study and visible selection toolbar. Installed results and the final source/build/publication receipt must be read from the delivery report; these source captures alone do not prove a packaged build.

The local Docker host denies Flatpak's namespace creation; installed verification uses the established GitHub Actions Flatpak environment instead of weakening application confinement. Physical touchpad and Wayland acceptance remain client checks. Numbered release #87 remains paused by the client's standing instruction; implementation issue #125 stays OPEN.
