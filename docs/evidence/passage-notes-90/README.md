# Passage Notes cards (#90)

The right Passage study Notes tab now uses one list of compact native annotation cards. Three independent notes and one actual highlight remain four independent records. Notes retain their original range, labels, IDs and origin context; rendering performs no writes. No storage format or migration was introduced. References remain available in their dedicated tab, without the duplicated Notes teaser.

Cards show locally resolved Scripture and its actual source, a distinct three-line Markdown note preview, an explicit opening affordance and an in-card localized modification date. Only actual highlights receive a narrow colored border and faint tint, with a textual color label. High contrast uses the system foreground and surface instead of color alone.

Clicking personal text opens the existing editor in the panel. Its buffer, Markdown preview, labels, citation previews and save/discard/cancel handling are shared with the full editor. Expansion reparents the same document. Draft targets are captured independently of subsequent passage/tab changes, and drafts survive hiding the panel and failed saves. A single Highlight menu offers highlight-only, highlight-and-annotate and standalone note creation. The palette captures the deliberate selection; cancelling returns to the creation choices. Removing/recoloring marks does not alter notes.

## Actual GTK captures

Baseline: `044d81ea09b0bbd4eaf1b0f4b88fa24d1f557691`. Same 1440 × 1000 Xvfb display, GTK scale 1, Ubuntu 24.04 GTK 4.14/libadwaita 1.5, French UI, same installed FreSegond1910 source and disposable annotation data. No Bible text was generated. Personal text explicitly identifies validation data. Narrow/default/wide preferred panel widths are 360/430/560 px (allocated content 352/422/552 px). Large system text emulates 150% through GTK font DPI, without reducing the application's fonts. Small windows are 360 × 700 px; black outside them is the unchanged Xvfb desktop.

| View | Before | After |
| --- | --- | --- |
| Light, narrow panel | [PNG](before-light-narrow.png) | [PNG](after-light-narrow.png) |
| Light, default panel | [PNG](before-light-default.png) | [PNG](after-light-default.png) |
| Light, wide panel | [PNG](before-light-wide.png) | [PNG](after-light-wide.png) |
| Light, 150% system text | [PNG](before-light-large-text.png) | [PNG](after-light-large-text.png) |
| Dark, narrow panel | [PNG](before-dark-narrow.png) | [PNG](after-dark-narrow.png) |
| Dark, default panel | [PNG](before-dark-default.png) | [PNG](after-dark-default.png) |
| Dark, wide panel | [PNG](before-dark-wide.png) | [PNG](after-dark-wide.png) |
| Dark, 150% system text | [PNG](before-dark-large-text.png) | [PNG](after-dark-large-text.png) |
| Light, small window | [PNG](before-light-small-window.png) | [PNG](after-light-small-window.png) |
| Dark, small window | [PNG](before-dark-small-window.png) | [PNG](after-dark-small-window.png) |
| Light, small + 150% text | [PNG](before-light-small-large-text.png) | [PNG](after-light-small-large-text.png) |
| Dark, small + 150% text | [PNG](before-dark-small-large-text.png) | [PNG](after-dark-small-large-text.png) |
| Light, high contrast | [PNG](before-light-high-contrast.png) | [PNG](after-light-high-contrast.png) |
| Dark, high contrast | [PNG](before-dark-high-contrast.png) | [PNG](after-dark-high-contrast.png) |

Inline editor: [light](after-light-inline-editor.png), [dark](after-dark-inline-editor.png), small window with 150% text [light](after-light-inline-small-large-text.png) / [dark](after-dark-inline-small-large-text.png). These views have no equivalent in the baseline. High-contrast notifications use the existing test-only libadwaita settings override; this does not prove a real GNOME portal connection. The capture script and measured panel widths are included here.

## Verification

- Full local suite: 235 tests passed, one conditionally skipped, before the final empty-draft case was added. Final targeted French card/citation suite: 9 passed, including the additional case.
- Actual X11 pointer/keyboard checks in English and French: citation hit targets preview without editing/navigation, personal-text click opens inline, keyboard expansion preserves the buffer, cancelled palettes reset, highlight-and-annotate preserves independent records, removing a mark preserves both notes. A mapped 360 px editor with 150% text keeps commands inside the panel.
- Existing pre-change SQLite note, labels, actual highlight, explicit preferences, primary/comparison session and 36 installed-resource file digests compared after opening the new Notes panel: unchanged. See `profile-preservation.json` for the actual digest count.
- Existing tests cover note backup/restore format, safe Markdown, verified versification and unavailable resources. Added tests cover bounded read-only rendering, independent overlapping records, missing resources, empty-draft save rejection, save errors, switching notes with cancel/discard, and draft survival across passage/tab/tool/panel changes and expansion.
- CI additionally runs the native card scenario and the card/citation tests against the installed Flatpak, asserting that application imports come from `/app/`. Signed public installation/update verification remains mandatory for delivery.

These are automated actual GTK/X11 checks and visually inspected captures, not manual validation on the client's GNOME desktop. Legacy initial-layout warnings can occur in Xvfb while pre-existing views are being allocated; the final settled card captures and native card checks have no clipped editor commands.

Delivery uses the existing signed alpha channel. The client's explicit pause of numbered release #87 takes precedence over the standing numbered-prerelease instruction. No numbered release is part of this batch. Global Notes #75 and sync #76 remain outside scope.
