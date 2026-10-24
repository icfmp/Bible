# Library, welcome and application-menu evidence (#63/#71/#108)

Actual GTK 4.14/libadwaita 1.5 windows under Xvfb, at GTK scale 1. Images are unedited screen captures; black outside the application is the unmanaged Xvfb desktop. Before source: `f69de06e730445da634b5a3866084c3fce97171d`. After: the feature source committed with this gallery. Captures are automated native GTK validation, not manual acceptance on the client's GNOME desktop.

French pairs cover normal/narrow windows, light/dark, Bibles/commentaries, the global menu, version chooser and initial empty/welcome state. Additional pairs use 150% system font DPI and high contrast. Before had no welcome page: those images show its ordinary empty reader. After-only images cover Skip, Notes menu at large font, actual eBible transfer/explicit Read and English network-disabled first use, installed browsing, settings, shortcuts and About.

The Library uses real catalogues from the five configured providers (1,941 supported entries), with actual installed FreSegond1910/KJV/FreLSN1872/eBible resources. No sample translation names, fabricated sizes or invented Scripture are used. Resource selection differs intentionally where the default changed: the approved French default shows a short relevant list; All languages is captured separately and remains explicitly selectable. Some small captions ellipsize at 150%; full values remain in accessible names/tooltips or their chooser. New Tab moves to the native tab bar in narrow windows; Notes and Study remain available by pointer.

## Before / after

| Scenario | Before | After |
| --- | --- | --- |
| dark-library-large-text | [PNG](before-dark-library-large-text.png) | [PNG](after-dark-library-large-text.png) |
| dark-menu-large-text | [PNG](before-dark-menu-large-text.png) | [PNG](after-dark-menu-large-text.png) |
| dark-normal-all-commentaries | [PNG](before-dark-normal-all-commentaries.png) | [PNG](after-dark-normal-all-commentaries.png) |
| dark-normal-bibles | [PNG](before-dark-normal-bibles.png) | [PNG](after-dark-normal-bibles.png) |
| dark-normal-commentaries | [PNG](before-dark-normal-commentaries.png) | [PNG](after-dark-normal-commentaries.png) |
| dark-normal-menu | [PNG](before-dark-normal-menu.png) | [PNG](after-dark-normal-menu.png) |
| dark-normal-version | [PNG](before-dark-normal-version.png) | [PNG](after-dark-normal-version.png) |
| dark-small-all-commentaries | [PNG](before-dark-small-all-commentaries.png) | [PNG](after-dark-small-all-commentaries.png) |
| dark-small-bibles | [PNG](before-dark-small-bibles.png) | [PNG](after-dark-small-bibles.png) |
| dark-small-commentaries | [PNG](before-dark-small-commentaries.png) | [PNG](after-dark-small-commentaries.png) |
| dark-small-menu | [PNG](before-dark-small-menu.png) | [PNG](after-dark-small-menu.png) |
| dark-small-version | [PNG](before-dark-small-version.png) | [PNG](after-dark-small-version.png) |
| dark-welcome-large-text | [PNG](before-dark-welcome-large-text.png) | [PNG](after-dark-welcome-large-text.png) |
| dark-welcome-small | [PNG](before-dark-welcome-small.png) | [PNG](after-dark-welcome-small.png) |
| dark-welcome | [PNG](before-dark-welcome.png) | [PNG](after-dark-welcome.png) |
| high-contrast-library | [PNG](before-high-contrast-library.png) | [PNG](after-high-contrast-library.png) |
| high-contrast-menu | [PNG](before-high-contrast-menu.png) | [PNG](after-high-contrast-menu.png) |
| light-library-large-text | [PNG](before-light-library-large-text.png) | [PNG](after-light-library-large-text.png) |
| light-menu-large-text | [PNG](before-light-menu-large-text.png) | [PNG](after-light-menu-large-text.png) |
| light-normal-all-commentaries | [PNG](before-light-normal-all-commentaries.png) | [PNG](after-light-normal-all-commentaries.png) |
| light-normal-bibles | [PNG](before-light-normal-bibles.png) | [PNG](after-light-normal-bibles.png) |
| light-normal-commentaries | [PNG](before-light-normal-commentaries.png) | [PNG](after-light-normal-commentaries.png) |
| light-normal-menu | [PNG](before-light-normal-menu.png) | [PNG](after-light-normal-menu.png) |
| light-normal-version | [PNG](before-light-normal-version.png) | [PNG](after-light-normal-version.png) |
| light-small-all-commentaries | [PNG](before-light-small-all-commentaries.png) | [PNG](after-light-small-all-commentaries.png) |
| light-small-bibles | [PNG](before-light-small-bibles.png) | [PNG](after-light-small-bibles.png) |
| light-small-commentaries | [PNG](before-light-small-commentaries.png) | [PNG](after-light-small-commentaries.png) |
| light-small-menu | [PNG](before-light-small-menu.png) | [PNG](after-light-small-menu.png) |
| light-small-version | [PNG](before-light-small-version.png) | [PNG](after-light-small-version.png) |
| light-welcome-large-text | [PNG](before-light-welcome-large-text.png) | [PNG](after-light-welcome-large-text.png) |
| light-welcome-small | [PNG](before-light-welcome-small.png) | [PNG](after-light-welcome-small.png) |
| light-welcome | [PNG](before-light-welcome.png) | [PNG](after-light-welcome.png) |

## Additional actual captures

- [after-dark-notes-large-text.png](after-dark-notes-large-text.png)
- [after-dark-skipped.png](after-dark-skipped.png)
- [after-light-notes-large-text.png](after-light-notes-large-text.png)
- [after-light-skipped.png](after-light-skipped.png)
- [native-direct-download.png](native-direct-download.png)
- [native-explicit-reading.png](native-explicit-reading.png)
- [native-global-menu.png](native-global-menu.png)
- [native-installed-awaiting-read.png](native-installed-awaiting-read.png)
- [offline-en-about.png](offline-en-about.png)
- [offline-en-dark-installed-library.png](offline-en-dark-installed-library.png)
- [offline-en-dark-welcome.png](offline-en-dark-welcome.png)
- [offline-en-first-use-unavailable.png](offline-en-first-use-unavailable.png)
- [offline-en-light-installed-library.png](offline-en-light-installed-library.png)
- [offline-en-light-welcome.png](offline-en-light-welcome.png)
- [offline-en-notes-global-menu.png](offline-en-notes-global-menu.png)
- [offline-en-preferences.png](offline-en-preferences.png)
- [offline-en-shortcuts.png](offline-en-shortcuts.png)

## Evidence and limits

- `native-fr.json`: actual eBible download via the row action, unchanged reading until explicit Read, exact local SWORD text, Notes Library route, actual Ctrl+, / Ctrl+? / Return and Escape input.
- `native-offline-en.json`: Docker network disabled, genuine first use, skip/restart, truthful failed refresh, pre-existing readable resource precedence and offline installed metadata/session preservation. The initial profile and resource profile are separate disposable test profiles.
- `profile-preservation.json`: actual SQLite note/labels, highlight, explicit reading preferences, primary/comparison session and all 36 resource file digests preserved from before source. These are test profiles; no personal client profile was accessed.
- `metadata-measurements.json`: measured cold/warm/selected-eBible metadata refreshes. Bytes count response bodies, excluding HTTP/TLS overhead. Cold providers expose global metadata archives. Language/type filtering is local; no claim that it reduces first-fetch archive bytes. Fresh cache skips network; explicit eBible validation returned HTTP 304 with zero body bytes.
- `startup-cold.json` / `startup-warm.json`: real native first populated frame and settled-list times, with no installed Bibles in the cold profile. Both select French. `startup-before.json` / `startup-after.json` additionally exercise a restored real-resource profile with an explicit All languages choice. Timings are local observations, not universal guarantees; pointer reopen totals include automated input delays.
- High contrast uses the existing test-only style-manager override, not a claim of a real client portal setting. Deep specialist accessibility remains deferred. Native focus, symbolic labels and keyboard actions are exercised.
- Synthetic SWORD text in unit/HTTPS transfer fixtures is test data; it is distinct from the actual resource/capture checks above. Original installation validation, provider identity, notices and package guards are retained.
- Included harnesses are evidence of how these runs were made; hard-coded `/work` paths refer to disposable test profiles. They are not a user setup procedure. Main CI records the exact final source and installed-package checks.
