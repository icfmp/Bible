# Reading controls, navigation and notes — current alpha increment

The three ordinary reading controls now belong to the active Bible viewport:
Compare, Aa, Fullscreen, in that order. They stay fixed while text scrolls and
move with the active tab. The viewport reserves clearance above its scrolling
content, rather than painting an opaque bar over the text. Header Bar end
actions remain Study, My notes, Library and the main menu, followed by native
window controls. History remains inside the passage selector; no history arrows
were added to the Header Bar.

New profiles, missing preferences and Reset use 14 **points**, Airy spacing and
Narrow width. Explicit old preferences remain unchanged. Very airy adds a
fourth spacing choice (16 px between wrapped lines versus Airy's 10 px),
persisted through the existing atomic preference file. GTK text tags use
`size_points`; Pango pagination uses point font descriptions. This does not
change scripture words, paragraph structure, reference mapping or note storage.

The notebook and library icons are the actual approved GNOME Icon Development
Kit 16 px SVGs by Jakub Steiner, copied unchanged with their embedded CC0
metadata. They replace the earlier approximate drawings. They work offline;
the source and license are recorded in THIRD_PARTY_NOTICES.md.

## #31 — completed and deliberately deferred

Manual reference entry is always visible at the top, with its local error next
to the field. The redundant bottom Direct reference expander and the selector's
download action are removed. Books, chapters, graphical verse selection and
per-tab History remain functional.

**Product decision still needed:** no alternate active-translation chooser has
been approved or implemented elsewhere. Removing the existing version dropdown
would remove an essential function. In accordance with the client's overnight
instruction, that dropdown is retained until the product manager chooses its
replacement location. This is partial #31 delivery, not a claim that its removal
criterion is complete. No alternative fourth reading-overlay control was
silently invented. Downloading remains in Library.

## Existing features preserved, not rebuilt

History already coalesces deliberate navigation, stays independent per tab and
does not record commentary following. The main-window My notes workspace,
readable localized dates, combined label filtering, compact B/I/list/link
commands, safe Markdown preview, Save/Discard/Continue guards, deletion
confirmation and note backups were already implemented. The notes Header Bar
title is made visible. Their existing tests are reused; no data migration is
introduced. Structured SWORD presentation and exact copy/reference checks are
also retained rather than replaced by invented headings or paragraphs.

## Validation limits

Virtual-display checks cover pointer/keyboard controls, active-tab ownership,
default/old preference retention, Very airy persistence, reference errors,
selection/anchors, notes guards and live emulated style changes. They do not
establish manual GNOME/Wayland, screen-reader or real desktop high-contrast
acceptance. Those issue criteria remain open for the client.
