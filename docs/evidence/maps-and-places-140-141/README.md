# Maps and place detail — issues 140 and 141

The existing libshumate raster renderer, native download/cache and lifecycle are
retained. OpenStreetMap France's FR raster style provides French and available
international/Latin names. Actual Babylon-area tiles demonstrate the difference
from OSM Standard and HOT, whose useful local labels remain Arabic. English UI
uses the available Latin/French fallback; English translations of every map name
are **not** claimed. There is no OCR, text overlay, new map engine, account, key
or mandatory application server.

Source/style: https://www.openstreetmap.fr/fonds-de-carte/ ; technical definition:
https://wiki.openstreetmap.org/wiki/FR:Serveurs/tile.openstreetmap.fr ; service
conditions: https://www.openstreetmap.fr/usage/ (checked 2 November 2026).
The service permits identified, free/nonprofit, moderate use; availability is not
guaranteed. The existing identifying user agent and native caching remain in use.
The native map now keeps the OSM copyright link visible in its corner, with the
tile-provider link below. A new native source identity separates the style cache.

Place detail follows place → supplied location description → secondary spatial
qualification/context → map. Established confidence is not used as a decorative
badge. Probable/disputed/unknown identification and distinct numbered candidate
locations remain explicit. Underlying scores/coordinates/source identities are
unchanged and are not exposed as technical reader controls.

The pinned real Shinar record describes **Babylonia**, with a representative
coordinate whose modern basis is Babylon. The UI therefore shows **Babylonie**
in French and **Localisation approximative**, rather than equating the region
with the city or inventing a region boundary. Jerusalem supplies a precise point
comparison. Existing map navigation and reference-preview behavior remain.

Local GTK 4.18.6/libshumate 1.5.5 tests pass with the default Vulkan renderer,
including native cache reuse, no requests after close, failed image handling and
place/reference lifecycle. The local Cairo renderer did not load these maps;
this is a local runtime limitation, not successful map validation. Installed
Flatpak/default-renderer evidence and actual themed captures remain final batch
gates. Both issues stay open; numbered release 87 remains paused.
