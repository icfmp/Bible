# Reader chrome — issue 118

The tab and passage selector show the localized book and chapter, while the
stored verse remains unchanged. The single-reader translation selector and the
three existing reading actions are in the native Header Bar. Comparison has one
full-name selector per pane, without the previous static pane headings; the
existing comparison chooser still provides “No comparison”.

At widths up to 760 px, the passage and single-reader version controls move into
a full-width native row immediately below the Header Bar. The reading actions
move into its “Reading tools” popover. At up to 420 px the study toggle joins
that popover; Bible/Notes, new tab and the main menu remain reachable. This is an
explicit fallback for widths where full translation names and the fixed header
actions cannot fit together. No floating row overlays the text. Comparison keeps
its existing horizontal scrolling and readable minimum column width.

Wrapped menu captions use GTK measurements after geometry/font/content changes,
with a bounded settling callback which stops at idle. Titles are not ellipsized.
The native test checks long titles (including “with”), 360/1200 px, increased
system font, chapter-only labels, retained verse and the actual appearance popup.
Existing comparison, persisted-session and idle-layout checks also pass locally.

Local GTK 4.18.6/Xvfb captures and the installed Flatpak validation will be linked
in the final batch delivery. Local source execution alone is not installed
Flatpak or client GNOME acceptance. Issue 118 stays open; numbered release 87
remains paused.

Header breakpoints follow GNOME text scaling through native SP units and adjust
on an explicit custom GTK font-size change. They retain the same native fallback
instead of wrapping a long translation into an excessively tall wide-window
header. This invalidation is event-driven and adds no idle polling.
