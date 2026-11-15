# Secondary dialog header review — #263

This is a deliberately limited application of the native GNOME convention, not
a redesign of the entire window system.

| Surface | Decision | Reason |
| --- | --- | --- |
| Passage note editor (quick and expanded hosts of the same native widget) | **Updated** | The excerpt's passage reference is the meaningful in-content heading. A second visible `Edit note` title in the native header competes with it. |
| Library | Retained | `Library` names a catalogue/list/detail flow and native back navigation; its header remains useful. |
| Book introduction | Retained | The book name in the native header identifies the source introduction when no inline heading is supplied. |
| Study passage | Deferred to #259 | Its in-header four-view navigation is being handled separately; no competing changes here. |
| Word study and place/detail dialogs | Unchanged | These have specific navigation and context needs requiring their own review. |
| Notes and highlights workspace | Out of scope | It is a main workspace rather than a secondary modal dialog. |

The shared passage note editor remains an `Adw.Window` with a real
`Adw.HeaderBar`, the platform-provided close control, the existing Save
button and the note-actions menu. The window retains its accessible title,
while the visible passage reference anchors the content. No custom close
button, window chrome, shortcut or navigation behavior has been introduced.
The independent top/bottom scroll-viewport correction belongs to #262; the
embedded workspace margins belong to #273.

The client explicitly authorized correction and publication of PR #277 after
review. Targeted GTK/SWORD regression checks and matched FR/EN light/dark and
high-contrast note captures cover the shared editor, smaller windows, linked
passages and buffer preservation. Full CI, packaged validation and the signed
installed update remain release gates; publication evidence belongs in the PR
and numbered release. Client desktop and assistive-technology acceptance remain
separate from cloud validation.
