# Coordinated reader polish — #64, #66, #69 and icon-only #67

The latest issue comments and the client's batch instruction define this scope.
The existing Header Bar action order and Library/Notes entry points are retained.
The #71 welcome/Library redesign and #75 Notes workspace are outside this batch.
The current client instruction pauses #87: no numbered prerelease is created.

## Delivered presentation

- One shared Aa in the primary reader overlay, with native round action surfaces.
  The compact appearance popup shows only the effective light/dark palette pair,
  while preserving the other saved choice. It retains both font choices, custom
  saved font identity, all four spacing levels, three widths and 12–64 pt bounds.
  Native switches control visibility; reset only affects reading appearance.
  First-use/reset defaults remain 14 pt / Very airy / Narrow.
- Installed-version pills act on their own panes. The primary chooser changes
  the current tab through the verified resolver; it does not create another tab.
  The replaced version dropdown no longer appears in the passage selector.
  Passage search, history and navigation retain their existing source model.
- Comparison has matched source headings and a right-pane version chooser.
  The left comparison action offers a clear stop action; the menu/selection
  Compare command reaches the right chooser when already comparing. Aa applies
  to both Bibles; Bible immersion buttons are hidden during comparison.
- Chapter arrows retain their round targets and vertical viewport anchoring;
  horizontal text clearance increases by 10 logical pixels, including narrow panes.
- The bottom selection surface has a full passage heading, secondary actual source,
  and Copy / Highlight / Add note / Compare / Close actions with 20 px glyphs and
  native 36 px targets. It moves above a lower selection where space permits,
  without scrolling the passage. Frozen source, exact partial Copy, canonical
  annotation targets and existing nested menus are reused.
- Header Bar icons use native 16 px rendering. Notes uses the standard text-editor
  symbol, Study the right-sidebar symbol, and Library the existing licensed books
  asset. Native hit targets and the active Study state are retained.
- A long commentary download label wraps so a hidden study pane cannot force
  a very narrow window wider when system text is enlarged.

No storage format, migration, resource corpus, comparison resolver or reflow worker
is changed. The immersive header reuses the same primary version control and Aa
popup and restores them on exit. Docked commentary typography is unchanged.

## Verification

Actual GTK 4.14 / libadwaita 1.5 / SWORD 1.9 under Xvfb, using disposable profiles:

- Full unittest suite, affected palette/session/annotation/selection tests, native
  pointer/keyboard checks, popup dismissal and nested spacing choices.
- Real Segond, eBible Darby and KJV in all six primary/comparison roles: source
  fidelity and native wheel following in both directions; Darby Gen.32.1 ↔ KJV
  Gen.31.55; per-pane chooser changes, tab switching and immersion round-trip.
- Matched before/after captures in French/English, light/dark, System notifications,
  normal and 350 × 590 content areas; study open/closed. French captures also use
  scale 2. System theme/high-contrast notifications use the existing test override,
  rather than claiming validation of a real GNOME settings portal.
- Additional 150% system-text captures and native high-contrast controls.

Representative unretouched captures are in
[evidence/reader-polish-64-66-69-67](evidence/reader-polish-64-66-69-67).
The complete captures and test reports accompany the delivery. These are actual
GTK captures, not mockups; Xvfb has no desktop compositor, so popup shadow areas
can appear black. This does not establish manual GNOME/Wayland, screen-reader,
Windows or macOS acceptance.

CI, Flatpak build, signed-channel publication and update/data-preservation checks
must be green for the exact merged source before reporting delivery complete.
The existing publication workflow's two signed verification revisions represent
one application batch. No numbered release or new channel is part of this batch.
