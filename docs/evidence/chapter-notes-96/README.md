# Native chapter Notes evidence — #96

Before: workspace source `74d784ed29f0f6ae247d5ac9b46427496140cbdb`, before #96;
the subsequent #75 window-close fix has no layout change. After: this PR; exact
source and installed application imports are independently recorded by CI.

Actual GTK/Xvfb with disposable profiles, real installed French SWORD resources
and saved developer notes/highlights. No personal client profile was accessed.
Normal windows: 1280/360 decorated pixels; small client width is 350 pixels.
Short windows: 360 × 600, 150% text. Existing reader preferences are retained.
Native forward/back captures use actual X11 wheel input on the real resource.
Synthetic native checker content is explicitly test data, separate from these
real-resource captures. Screenshots and automated input are not client desktop
acceptance or a Wayland/touchpad claim.

| View | Before | After |
| --- | --- | --- |
| dark-small-comparison-notes | [PNG](before-dark-small-comparison-notes.png) | [PNG](after-dark-small-comparison-notes.png) |
| dark-small-comparison-reader | [PNG](before-dark-small-comparison-reader.png) | [PNG](after-dark-small-comparison-reader.png) |
| dark-small-short-large-text-notes | [PNG](before-dark-small-short-large-text-notes.png) | [PNG](after-dark-small-short-large-text-notes.png) |
| dark-small-single-notes | [PNG](before-dark-small-single-notes.png) | [PNG](after-dark-small-single-notes.png) |
| dark-small-single-reader | [PNG](before-dark-small-single-reader.png) | [PNG](after-dark-small-single-reader.png) |
| dark-wide-comparison-notes | [PNG](before-dark-wide-comparison-notes.png) | [PNG](after-dark-wide-comparison-notes.png) |
| dark-wide-comparison-reader | [PNG](before-dark-wide-comparison-reader.png) | [PNG](after-dark-wide-comparison-reader.png) |
| dark-wide-single-notes | [PNG](before-dark-wide-single-notes.png) | [PNG](after-dark-wide-single-notes.png) |
| dark-wide-single-reader | [PNG](before-dark-wide-single-reader.png) | [PNG](after-dark-wide-single-reader.png) |
| light-small-comparison-notes | [PNG](before-light-small-comparison-notes.png) | [PNG](after-light-small-comparison-notes.png) |
| light-small-comparison-reader | [PNG](before-light-small-comparison-reader.png) | [PNG](after-light-small-comparison-reader.png) |
| light-small-short-large-text-notes | [PNG](before-light-small-short-large-text-notes.png) | [PNG](after-light-small-short-large-text-notes.png) |
| light-small-single-notes | [PNG](before-light-small-single-notes.png) | [PNG](after-light-small-single-notes.png) |
| light-small-single-reader | [PNG](before-light-small-single-reader.png) | [PNG](after-light-small-single-reader.png) |
| light-wide-comparison-notes | [PNG](before-light-wide-comparison-notes.png) | [PNG](after-light-wide-comparison-notes.png) |
| light-wide-comparison-reader | [PNG](before-light-wide-comparison-reader.png) | [PNG](after-light-wide-comparison-reader.png) |
| light-wide-single-notes | [PNG](before-light-wide-single-notes.png) | [PNG](after-light-wide-single-notes.png) |
| light-wide-single-reader | [PNG](before-light-wide-single-reader.png) | [PNG](after-light-wide-single-reader.png) |

Additional captures:

- [after-dark-small-short-large-text-paused.png](after-dark-small-short-large-text-paused.png)
- [after-light-small-short-large-text-paused.png](after-light-small-short-large-text-paused.png)
- [after-native-bible-wheel-back.png](after-native-bible-wheel-back.png)
- [after-native-bible-wheel-forward.png](after-native-bible-wheel-forward.png)

`native-follow.json` and `native-offline.json` record actual Bible wheel input in
both directions, manual Notes browsing and Resume, stable cards/history/focus,
marker reveal without editing and a retained captured draft. The offline Docker
container has networking disabled. `native-cards.json` proves contextual creation,
preview/edit/expansion, independent mark removal and 360 px/150% commands.
`profile-preservation.json` verifies existing note/labels/highlight/preferences,
primary/comparison session and all 36 installed-resource hashes.
