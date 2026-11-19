# Secondary dialog headers — #263

Bible keeps native libadwaita headers, navigation and close controls. Secondary
headers now use their dialog surface instead of the reading window's separate
chrome color. The old scoped `headerbar` background caused the visible strip;
removing a title alone did not remove it. The override applies only to dialogs
marked `bible-secondary-dialog`; the reading header is unchanged.

| Surface | Header and context |
| --- | --- |
| Passage note editor | Native New/Edit note title and Close; passage/source stays in the content. Autosave replaces the former Save action (#281). |
| Library | Library title, Back and catalogue actions remain functional. |
| Preferences | Native page navigation and Close remain available. |
| Keyboard shortcuts | Native title, search and Close remain available. |
| Study passage | Original text / Map navigation, Close and one passage reference; unavailable placeholder pages are removed (#293). |

This convention changes chrome, not source text or persistence. The main Notes
workspace and independent source-introduction/detail dialogs retain their
existing navigation. Client desktop acceptance remains pending; actual captures
and verification receipts are recorded with the delivery evidence, separately
from implementation and package publication.
