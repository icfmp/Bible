# Notes, references and contextual interface — developer evidence

Related to #281, #280, #278, #279, #274, #292, #293, #263 and #291.
These are unedited captures of the real Python/GTK application, not mockups.

| Issues | Change and evidence |
| --- | --- |
| #281 / #280 | One existing autosaving passage-note popup replaces the Study inline editor. [Before](before-notes-popup.png), [after FR](after-notes-popup.png), [EN narrow/high contrast](after-en-notes-popup.png), [scrolled bottom](after-en-notes-popup-bottom.png). Explicit embedded global Notes editing is preserved. |
| #278 / #279 | Neutral whole-card outline feedback, real highlight color accent, separate overflow/citation actions. [Notes before](before-notes-green-hover.png), [after](after-notes-green-hover.png); [References before](before-notes-references-hover.png), [after](after-notes-references-hover.png). Same drawer: old Notes width 388 vs References 360; new both 388, x=12. |
| #279 scrollbar cases | [Notes with conventional scrollbar](cards-native-scrollbar-notes.png), [References](cards-native-scrollbar-references.png); [Notes without overflow](cards-no-scrollbar-notes.png), [References](cards-no-scrollbar-references.png). A 412px drawer yields equal 364px cards with the 24px scrollbar, equal 388px cards without it; no negative offsets or removed scrollbar. Native scrollbar animation was disabled for settled-allocation measurement (an earlier sample taken during its transition differed by 2px). Real KJV/OpenBible passages and disposable personal notes, with original query/membership logic unchanged. |
| #274 | [Installed before video](before-references-navigation.mp4), [development after video](after-references-navigation.mp4). Eight scripted passage changes, same real KJV and existing OpenBible database, controlled 180ms query latency to expose pending states. Old cards/context stay visible and inert; only the latest completion commits. This is an interaction comparison, not a speed benchmark. |
| #292 | [Library menu](after-ui-fr-ui-main-menu.png) uses the exact GNOME Web books glyph; existing workspace symbolics remain. All production names resolve from app assets/GTK in a standalone theme with no desktop search paths, LTR/RTL. Minimal-theme FR/EN native app dialog flows also pass. [Inventory and licenses](../../ICON_INVENTORY_292.md). |
| #293 | [Original text](after-ui-fr-ui-dialog-study.png), [Map](after-ui-fr-ui-dialog-study-map.png): only implemented pages, natural-width navigation, legacy placeholder modes normalize to Original text. No missing source content is manufactured. |
| #263 | Native dialog headers share the dialog surface; [Library](after-ui-fr-ui-dialog-library.png), [Preferences](after-ui-fr-ui-dialog-preferences.png), [Shortcuts](after-ui-fr-ui-dialog-shortcuts.png), plus Note and Study above. Titles, close controls and navigation remain native. [Convention review](../../SECONDARY_DIALOG_REVIEW_263.md). |
| #291 | [Installed baseline FR](baseline-ui-fr-ui-selection.png), [after FR](after-ui-fr-ui-selection.png), [formats](after-ui-fr-ui-copy-formats.png), [EN](after-ui-en-ui-selection.png), [360px/large/high contrast](after-ui-en-ui-selection-narrow-large-high-contrast.png). Copy immediately uses the frozen selected text with real source attribution. Chevron has three independently actionable formats. |

Before Notes/References captures: installed alpha.34 (`8beb2b0`); before selection
capture: installed alpha.35 (`e39d98f`). After captures: source-first development
application in the same installed GNOME 49 Flatpak runtime, GTK 4.20.4,
X11/software OpenGL, scale 100%, existing genuine KJV/French Darby and checked
OpenBible resources, disposable copies of retained profiles. Validation notes
are test annotations only. Original retained profiles are not reset or modified.
JSON receipts identify imports, geometry and controlled query timing.

Focused native checks cover autosave coalescing/immediate close/reopen, failed
save keep/discard/retry, fixed source context across tabs/passage changes,
pending-delete non-resurrection, actual citation/overflow/card mouse and keyboard
activation, global Notes reuse and old backup/link restoration; reference
out-of-order completion, stale/cancelled work and first-load/error/reduced-motion
states; selection formats/clipboard fidelity, alternate versification, exact
partial selections, sentinel Unicode/RTL/cross-chapter strings, native drag,
keyboard extension, nested Escape/outside dismissal, comparison and immersion;
hidden-work/idle guards and five secondary dialogs in FR/EN. Broad regression
and actual merged-package delivery remain CI/publication gates.

No Plasma/KDE, client Wayland/GPU, physical touch device or assistive-technology
session is available here. Standalone minimal-theme lookup and native hicolor
app checks are not claimed as KDE desktop acceptance. No rich clipboard format
is offered; all three supported formats write honest plain text. Cross-chapter
string formatting is unit-tested; the native drag campaign covers same-chapter
real/fixture selections rather than claiming a cross-chapter pointer gesture.
Issues remain open. Implementation, developer validation and published installed
application status must be read separately in the PR/release delivery receipt.
