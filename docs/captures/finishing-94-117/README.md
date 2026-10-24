# Native GTK before/after gallery

Actual GTK/Xvfb captures on Linux; no mockups or generated Scripture. Baseline:
`07af242d523a9fcc92576e2752da71dab9abc107`. Disposable profiles contain real
FreSegond1910, KJV and attributed French resources; RTL uses public-domain HebNTFD.
Ordinary captures use scale 1; accessibility captures use GTK scale 2 and 150% text.
The latter narrow window has a 350 × 690 client area and a reachable New Tab button.
This does not claim acceptance on the client's GNOME/Wayland desktop.

| View | Before | After |
|---|---|---|
| Reading, light | [Before](before-reader-day.png) | [After](after-reader-day.png) |
| Reading, dark | [Before](before-reader-night.png) | [After](after-reader-night.png) |
| Single-tab hover instruction, light | [Before](before-hover-day.png) | [After](after-hover-day.png) |
| Single-tab hover instruction, dark | [Before](before-hover-night.png) | [After](after-hover-night.png) |
| Two reading tabs, light | [Before](before-two-tabs-day.png) | [After](after-two-tabs-day.png) |
| Two reading tabs, dark | [Before](before-two-tabs-night.png) | [After](after-two-tabs-night.png) |
| Direct versions, light | [Before](before-versions-day.png) | [After](after-versions-day.png) |
| Direct versions, dark | [Before](before-versions-night.png) | [After](after-versions-night.png) |
| Selection actions, light | [Before](before-actions-normal-day.png) | [After](after-actions-normal-day.png) |
| Selection actions, dark | [Before](before-actions-normal-night.png) | [After](after-actions-normal-night.png) |
| Comparison actions, light | [Before](before-actions-comparison-day.png) | [After](after-actions-comparison-day.png) |
| Comparison actions, dark | [Before](before-actions-comparison-night.png) | [After](after-actions-comparison-night.png) |
| Immersive actions, light | [Before](before-actions-immersion-day.png) | [After](after-actions-immersion-day.png) |
| Immersive actions, dark | [Before](before-actions-immersion-night.png) | [After](after-actions-immersion-night.png) |
| Small window, light | [Before](before-narrow-day.png) | [After](after-narrow-day.png) |
| Small window, dark | [Before](before-narrow-night.png) | [After](after-narrow-night.png) |
| Immersive spread | [Before](before-immersion.png) | [After](after-immersion.png) |

Whole-window palettes with two tabs, comparison and study: [Paper](after-two-tabs-paper.png), [Black](after-two-tabs-black.png).

Whole-window palettes: [Paper](after-palette-paper.png), [Black](after-palette-black.png),
[Paper comparison + study](after-comparison-study-paper.png),
[Black comparison + study](after-comparison-study-black.png),
[Paper Notes](after-notes-paper.png), [Black Notes](after-notes-black.png).
Accessibility: [small/150%/scale 2](accessibility-narrow-150-percent.png),
[high-contrast light](accessibility-high-contrast-day.png),
[high-contrast dark](accessibility-high-contrast-night.png),
[preferences at 150%](accessibility-preferences-150-percent.png).
Welcome: [first launch](after-welcome-launch-1.png),
[second launch with no Bible](after-welcome-launch-2.png).

## Motion and real network

- [Baseline idle, 23 seconds](before-immersion-stability.mp4).
- [Corrected stable idle, reveal, keyboard/menu and dismissal, 25 seconds](settled-immersion-stability.mp4), with [instrumentation](settled-immersion-stability.json).
- [Two-page forward/back and rapid turns](after-page-turns.mp4).
- [One-page forward/back](extra-single-page-turns.mp4).
- [Chapter boundary](extra-chapter-boundary.mp4), [Acts → Romans](extra-book-boundary.mp4).
- [Real Hebrew RTL](extra-rtl-page-turns.mp4), [RTL capture](extra-rtl.png).
- [Skeleton pulse](after-catalogue-skeleton.mp4).
- [Actual five-provider retrieval](live-network-loading.mp4), [actual result](live-network-result.png), [network report](live-network-loading.json). A recorded 1.5-second diagnostic delay precedes real requests; 1,941 entries were returned without errors.

## Controlled Library-state captures

These are native GTK views driven by controlled snapshots. They establish the
presentation, not a claim that the network returned empty or failed.

| State | Light | Dark |
|---|---|---|
| No usable rows, loading | [Light](after-catalogue-loading-day.png) | [Dark](after-catalogue-loading-night.png) |
| Covered, completed empty result | [Light](after-catalogue-empty-day.png) | [Dark](after-catalogue-empty-night.png) |
| Failure without usable rows | [Light](after-catalogue-error-day.png) | [Dark](after-catalogue-error-night.png) |
| Refresh retaining actual installed rows | [Light](after-catalogue-refresh-day.png) | [Dark](after-catalogue-refresh-night.png) |

## Native annotation backup and blur diagnostics

Native GTK fallback chooser: [Preferences actions](backup-preferences-backups.png),
[export selection](backup-native-export.png), [export feedback](backup-export-success.png),
[confirmation](backup-restore-confirmation.png), [restore feedback](backup-restore-success.png),
[round-trip report](backup-result.json). The local test disables portal IPC; installed
checks cover the chooser response boundary and actual storage, not a desktop portal.

Blur: [radius 0 diagnostic](blur-radius-0.png), [radius 8](blur-radius-8.png),
[pixel report](blur-proof.json). Only an internal diagnostic radius differs; neither
image is edited and there is no user-facing blur setting. The opaque high-contrast
fallback is shown separately above.
