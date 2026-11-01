# Issue 26: YouVersion catalogue by language

Status: implemented on the feature branch, packaging and signed delivery pending. This expands the earlier [seven-edition pilot](../youversion-26/README.md) following the client's clarification. Issue #26 stays OPEN; numbered release #87 remains paused.

## Result

Library discovers YouVersion’s actual text-language inventory and loads the selected language’s edition list, using the same language/source filters as other Bible sources. The observed inventory contains 2,469 text languages; French returns 20 editions, English 88, Spanish 30 and Arabic 14. These are dated observations, not permanent availability claims. Browsing downloads metadata only. Full edition metadata and current conditions are obtained before permission acknowledgement and actual offline acquisition.

New edition IDs are accepted without a fixed allowlist. The seven existing IDs retain their exact previous identities and reference systems. Each new edition gets a source-specific SWORD index derived from its actual books, chapters and numbered source units. Partial canons and deuterocanonical books are supported without imposing 66 books or inventing verses. The small native extension loads reference bounds only; it does not contain Scripture, claim cross-edition alignment or change existing notes. Independent parallel reading remains available when alignment is unverified.

Language lists use bounded, atomically replaced metadata caches and a fifteen-minute freshness window. Switching languages uses the existing metadata worker and cancels obsolete queued requests. There is no new recurring timer, startup corpus loading or bulk fetch of every language. Unknown source structures fail before registration and retain the archive for a corrected retry. Only complete native readback can mark an edition installed.

## Measured conversion cases

[Local receipts](local-conversion.json) record actual anonymous acquisition through the returned offline URLs, private conversion and complete native text/notes/headings verification. No downloaded corpus or generated module is published.

| Edition | ID | Books | Indexed chapters/introductions |
| --- | ---: | ---: | ---: |
| Crampon 1923 | 504 | 73 | 1,334 |
| Reina Valera 1960 | 149 | 66 | 1,255 |
| Chinese Contemporary Bible | 36 | 66 | 1,189 |
| Arabic Van Dyck | 13 | 66 | 1,189 |
| Sacy, Matthew 1855 | 2599 | 1 | 28 |
| Darby 1890, English | 478 | 66 | 1,189 |

These cases exposed and now cover unnumbered text after a leading section heading, chapter-scoped notes before verse one, additional explicit USFM editorial roles, nullable source agreement/version fields, RTL text, and the Chinese catalogue’s `zho` versus offline `cmn` identity. Only maintained CLDR language aliases qualify; the original offline language is retained in source receipts. Chinese Isaiah 38 places verses 21–22 before 7; a sparse, hashed reference-order sidecar preserves that order in application reading instead of renumbering or sorting the source text. Normal numeric chapters need no order sidecar.

Reference indexes reject malformed bounds and conflicting replacement while native keys may be live. Their reference-only copies survive resource removal. Notes, reading preferences, existing resources and previous verified mappings are not migrated or reset.

## Actual local GTK captures

[Capture receipt](local-gtk/verification.json): source application with GTK 4.18.6, libadwaita 1.7 and Cairo under Xvfb; these are unedited root-window images, **not installed Flatpak or client GNOME evidence**. The black area is the virtual desktop outside the window. The narrow window is 350 × 590 content pixels (360 × 600 including its frame); the study panel collapses responsively. This GTK version emits a one-pixel GtkStack minimum-width warning at that size; controls remain visible in the captures.

| View | Light | Dark |
| --- | --- | --- |
| Spanish catalogue, 30 editions | [image](local-gtk/catalogue-es-white.png) | [image](local-gtk/catalogue-es-dark.png) |
| French catalogue, 20 editions | [image](local-gtk/catalogue-fr-white.png) | [image](local-gtk/catalogue-fr-dark.png) |
| Arabic catalogue, 14 editions | [image](local-gtk/catalogue-ar-white.png) | [image](local-gtk/catalogue-ar-dark.png) |
| Crampon, Tobit | [image](local-gtk/edition-504-white.png) | [image](local-gtk/edition-504-dark.png) |
| Chinese, Isaiah 38 | [image](local-gtk/edition-36-white.png) | [image](local-gtk/edition-36-dark.png) |
| Arabic reading and translation notes | [image](local-gtk/edition-13-white.png) | [image](local-gtk/edition-13-dark.png) |
| Partial Sacy edition | [image](local-gtk/edition-2599-white.png) | [image](local-gtk/edition-2599-dark.png) |
| Narrow window | [image](local-gtk/edition-small-white.png) | [image](local-gtk/edition-small-dark.png) |

Local targeted checks currently pass: 57 source/native tests and 30 GTK/catalogue tests. New tests exercise asynchronous metadata, cache preservation, exact generic conversion, NT-only canons, moved verses, absent/linked verses, unnumbered notes, RTL, tamper/conflict refusal, metadata hydration and acknowledgement before any archive request. The installed proof additionally reruns all seven historical editions.

## Limits and remaining verification

The legacy metadata/offline interfaces are observed working without keys or impersonation; they are not a supported public API guarantee. An edition without a returned offline URL cannot be downloaded. Source refusal, an unknown book/semantic structure or a failed fidelity check ends installation explicitly. Discovery of thousands of editions does not prove every one has been converted. Each user remains responsible for the actual source permissions and agreement requirements; local acknowledgement does not submit or assert a provider agreement.

The complete independent DOM comparison passes for all six new editions: see [source-versus-OSIS/native/application receipts](independent-local.json). Ordinary CI, installed Flatpak conversion/GTK, signed publication and retained-profile update verification remain pending. Developer Xvfb checks do not establish behavior on the client's Wayland/GNOME hardware or on Windows/macOS. No numbered release is authorized while #87 is paused.
