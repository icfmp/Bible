# Native GTK evidence — annotation workspace #75

Before: delivered source `53aa59357013f5b2a6cd9be9e65a8bc29acd02ec`.
After: this PR; exact packaged source is recorded by CI and publication receipts.

Actual Xvfb captures from disposable profiles with installed French SWORD resources,
existing SQLite notes and highlights. No personal client profile was accessed.
Windows are 1280/360 pixels decorated; small client width is 350 pixels. Large-text
captures use 150% font DPI; short windows are 360 × 600 decorated. Labels-focused
captures demonstrate the scrollable detail. High contrast uses a test-only native
style-manager override. Old-layout minimum-height warnings remain visible in the
before evidence; screenshots are not desktop acceptance.

| View | Before | After |
| --- | --- | --- |
| dark-small-detail | [PNG](before-dark-small-detail.png) | [PNG](after-dark-small-detail.png) |
| dark-small-large-text-detail | [PNG](before-dark-small-large-text-detail.png) | [PNG](after-dark-small-large-text-detail.png) |
| dark-small-large-text-list | [PNG](before-dark-small-large-text-list.png) | [PNG](after-dark-small-large-text-list.png) |
| dark-small-list | [PNG](before-dark-small-list.png) | [PNG](after-dark-small-list.png) |
| dark-small-short-large-text-detail | [PNG](before-dark-small-short-large-text-detail.png) | [PNG](after-dark-small-short-large-text-detail.png) |
| dark-small-short-large-text-list | [PNG](before-dark-small-short-large-text-list.png) | [PNG](after-dark-small-short-large-text-list.png) |
| dark-wide-detail | [PNG](before-dark-wide-detail.png) | [PNG](after-dark-wide-detail.png) |
| dark-wide-large-text-detail | [PNG](before-dark-wide-large-text-detail.png) | [PNG](after-dark-wide-large-text-detail.png) |
| dark-wide-large-text-list | [PNG](before-dark-wide-large-text-list.png) | [PNG](after-dark-wide-large-text-list.png) |
| dark-wide-list | [PNG](before-dark-wide-list.png) | [PNG](after-dark-wide-list.png) |
| high-contrast-detail | [PNG](before-high-contrast-detail.png) | [PNG](after-high-contrast-detail.png) |
| light-small-detail | [PNG](before-light-small-detail.png) | [PNG](after-light-small-detail.png) |
| light-small-large-text-detail | [PNG](before-light-small-large-text-detail.png) | [PNG](after-light-small-large-text-detail.png) |
| light-small-large-text-list | [PNG](before-light-small-large-text-list.png) | [PNG](after-light-small-large-text-list.png) |
| light-small-list | [PNG](before-light-small-list.png) | [PNG](after-light-small-list.png) |
| light-small-short-large-text-detail | [PNG](before-light-small-short-large-text-detail.png) | [PNG](after-light-small-short-large-text-detail.png) |
| light-small-short-large-text-list | [PNG](before-light-small-short-large-text-list.png) | [PNG](after-light-small-short-large-text-list.png) |
| light-wide-detail | [PNG](before-light-wide-detail.png) | [PNG](after-light-wide-detail.png) |
| light-wide-large-text-detail | [PNG](before-light-wide-large-text-detail.png) | [PNG](after-light-wide-large-text-detail.png) |
| light-wide-large-text-list | [PNG](before-light-wide-large-text-list.png) | [PNG](after-light-wide-large-text-list.png) |
| light-wide-list | [PNG](before-light-wide-list.png) | [PNG](after-light-wide-list.png) |

Additional actual captures:

- [after-dark-small-large-text-filters.png](after-dark-small-large-text-filters.png)
- [after-dark-small-large-text-labels.png](after-dark-small-large-text-labels.png)
- [after-dark-small-short-large-text-filters.png](after-dark-small-short-large-text-filters.png)
- [after-dark-small-short-large-text-labels.png](after-dark-small-short-large-text-labels.png)
- [after-dark-wide-large-text-labels.png](after-dark-wide-large-text-labels.png)
- [after-light-small-large-text-filters.png](after-light-small-large-text-filters.png)
- [after-light-small-large-text-labels.png](after-light-small-large-text-labels.png)
- [after-light-small-short-large-text-filters.png](after-light-small-short-large-text-filters.png)
- [after-light-small-short-large-text-labels.png](after-light-small-short-large-text-labels.png)
- [after-light-wide-large-text-labels.png](after-light-wide-large-text-labels.png)
- [native-workspace-content-search.png](native-workspace-content-search.png)
- [native-workspace-saved.png](native-workspace-saved.png)
- [native-workspace-write-error-draft-kept.png](native-workspace-write-error-draft-kept.png)
