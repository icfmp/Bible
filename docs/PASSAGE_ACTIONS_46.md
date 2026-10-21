# Deliberate passage selection actions (#46)

A compact native action bar appears at the bottom of the selected Bible viewport
after a verse click, completed pointer selection or keyboard extension. It never
opens from an anchor change, temporary commentary cue, programmatic selection or
restoration. Pointer dragging is observed without claiming the native selection
gesture; the bar remains hidden until release. Shift navigation enables a caret
for native keyboard selection, including pagination; pointer reading stays quiet.

The frozen target contains the actual resource, reader/versification, canonical
verse range, selected text and exact full verse text. A changed tab, resource,
document or selection invalidates it. Opening an action/menu does not erase the
selection or silently retarget another translation. Escape closes nested menus,
then the bar; outside clicks and the dismissal button also work. Reflow and the
working study/comparison coordinators retain their independent contracts.

- Copy keeps the exact selected characters, restoring original characters in
  place of presentation-only spaces. A verse click copies that verse's exact
  source text. Secondary options retain complete verses, reference/translation
  attribution and reference-only copying. Partial copy and whole-verse note/
  annotation scope are deliberately distinct.
- Note reuses the existing editor, matching notes and unsaved-change protection,
  passing the selected source system and original resource explicitly. Selection
  in Lausanne records Calvin/Lausanne, not the main Segond source by accident.
- Compare maps the selected start into the existing Bible pair and opens its
  chooser. It neither creates a tab nor promotes the secondary translation or
  silently replaces the main one. Existing whole-chapter comparison remains the
  presentation; the full intended passage stays selected.
- **Highlight is conditional on the reviewed PR40 implementation.** The current
  main build does not expose an inert Highlight control. On that candidate the
  existing color store/backup rules and exact selected source are reused. This
  remaining review dependency is explicit; PR40 is not merged to unblock it.

Both comparison panes and the paginated Bible bind their own source/document
context. The bar takes no focus when shown and keeps selected content clear with
a minimal viewport adjustment only when its active endpoint would be covered.
Native palettes, focus and localized tooltips apply. No new user-data format,
source, account, server, signing key or publication channel is introduced.

Validation: 143 full local tests passed, plus focused final immersion/action
checks. `tools/check_passage_actions.py` uses real offline FreSegond/Lausanne and
actual X11 input: single verse, completed drag with no mid-drag bar, exact partial
Copy, retained selection, keyboard extension without focus theft, nested Escape
and outside dismissal, actual comparison note identity, mapped Compare, immersive
selection and closure. These are not manual GNOME/Wayland/accessibility checks.

Actual GTK captures: [single verse](captures/actions-46-single.png),
[partial selection](captures/actions-46-partial.png),
[comparison source](captures/actions-46-comparison.png),
[pagination](captures/actions-46-immersion.png).

Final public availability requires green CI/publication and an actual update of
the existing signed alpha. Keep #46 open for the PR40 Highlight dependency and
manual client acceptance; #26 stays excluded and #28 remains manual guidance.
