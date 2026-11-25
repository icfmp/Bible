# Interface and reading fonts

Audit for the 25 November 2026 client feedback on #328, alongside #332 and #334.

## Root cause and correction

Shared passage-card headings incorrectly carried `study-content`. Its scoped CSS
applies the saved study-content family, whose default is `sans-serif`. That is a
Fontconfig generic family, not GTK's system interface font. In the installed
alpha.39 validation environment it resolves to DejaVu Sans, where a request for
500 resolves to the same Regular face as 400. Setting a Pango weight alone did
not repair the inherited family.

Changing GTK's interface font demonstrated the distinction: native controls
changed to Adwaita Sans Medium or Cantarell Medium, while the card title stayed
DejaVu Sans. The corrected heading inherits family and size from GTK/libadwaita;
only its requested Medium weight is specified. There is no application-selected
interface fallback family. If the user's actual interface font lacks a weight,
Pango retains its normal native matching behavior.

The Book/Simple mode labels and font-family names in Reading Settings also
previously received reading-font Pango attributes. These are interface controls,
so those attributes are removed. Native font chooser previews remain GTK-owned.

## Application audit

| Surface | Font ownership |
| --- | --- |
| Header, workspace selector, navigation, Search/Aa/Library/Preferences, study tabs and contextual controls | Native GTK/libadwaita inheritance; no application family setting |
| Passage references in shared Notes/Highlights/References/related cards | Native inheritance with a semantic 500 weight; no `study-content` class |
| Bible body, generated/source headings, verse typography, parallel reading and immersion/pagination | Existing saved reading fonts, sizes and native text tags; unchanged |
| Commentary body/prefaces, Bible excerpts, note text/editor/previews | Existing saved study-content family/size and source styles; unchanged |
| Original-language and place displays | Native interface labels and Pango's glyph fallback; no generated font substitution |
| Application icons | Existing artwork; embedded SVG text is artwork, not a GTK interface font rule |

Family-setting sites were audited across `reading_style`, `bible_render`,
`verse_typography`, `pagination`, `book_stream`, `immersion`, `study_panel`,
`commentary_format`, `appearance`, and `reading_preferences`. The remaining
explicit families apply to reading content. No preference/schema/data migration
is necessary, and saved font choices must not be reset.

## Flatpak

The GNOME 49 manifest and launcher do not set `gtk-font-name`, install GTK
settings or Fontconfig aliases, or override system font settings through an
environment variable. Packaged DejaVu/Roboto files make reader fonts available;
installing them does not make their names the system interface setting. Keep
these files for existing reading preferences and reproducible reading metrics.
No extra D-Bus permissions or application font-selection service are needed.

The actual installed GNOME 49/libadwaita 1.8.8 runtime was checked under the
cloud X11 test display. It had neither a desktop Settings portal nor XSettings
manager, so GTK received its fallback `Sans 10`; unstyled native controls also
resolved to DejaVu. This is distinct from the application CSS bug. Tests change
the process-local GtkSettings font to verify inheritance and live changes, then
restore it. They do not install a system setting or alter a user profile.

The client's physical GNOME/Wayland portal and actual system font have not been
observed here. A normal desktop supplies settings through GTK's native settings
integration; the application must neither guess the family nor override it.
