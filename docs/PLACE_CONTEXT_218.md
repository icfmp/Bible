# Offline place context and optional photographs (#218, #238)

The OpenBible index, its source IDs, coordinates and references are unchanged. A separately prepared resource supplies source-identified context. The renderer uses `bible/study_data/place_context_v2.json` as a small generated offline seed; its exact origin is in `place_context_v2.origin.json`. The obsolete schema-1 application-authored Jerusalem excerpt is no longer shipped. Existing downloaded indexes, photographs, notes and preferences are untouched.

Preparation and maintenance live in [Bible-Resources](https://github.com/icfmp/Bible-Resources/blob/main/docs/PLACE_CONTEXT.md). That process records explicit source identities, revisions, native languages, licenses, file credits, bounded image sizes and SHA-256. It acquires complete source-service introductory extracts without authoring summaries or translating them. French and English Wikipedia articles are checked independently against the supplied Wikidata ID. Missing or mismatched language coverage remains unavailable; the renderer labels the source language it actually displays.

| OpenBible evidence | Presentation and preservation |
| --- | --- |
| Ancient ID, source name and uncertainty | Exact ID/name agreement; conservative identification label retained |
| Proposed modern IDs, coordinates, roles and modifiers | Native map; all original proposals retained |
| Multiple resolutions of one modern ID | One site heading, every distinct source proposal and its qualification still shown |
| Translation names and aliases | Compact source-name disclosure; conventional UI labels do not rewrite source prose |
| Coordinate provenance and bibliography | Accessible Sources and evidence disclosure; no book content imported |
| Evidence paths and scores | Retained in the index; no numerical archaeological probability invented |
| Unknown resolutions | No invented coordinate, photo or historical equivalence |

## Identity and actual sample

A Wikidata **coordinate source** establishes provenance for a coordinate; it does not establish the ancient place's identity. Related introductions and photographs are explicitly qualified by that scope. The source's proposed site name remains separate from the Wikidata label. Direct ancient-place context requires documented evidence in the resource project's identity registry.

The 8 November sample requests 12 ancient IDs: 10 have direct or explicitly qualified related context, involving 11 coordinate-source entities and 8 verified photographs. It is not universal coverage. Moreh 1 has three distinct proposals for modern ID m657590, Tell Balatah, using coordinate-source entity Q7951237 (Shechem). None is silently discarded or promoted to proof that Moreh equals Shechem. Moreh 2 (Judges 7:1) has a different modern ID and source entity. Emmaus keeps six disputed proposals and separate related entities. Nod and Bethlehem 2 have no vetted enrichment; Nod remains without a pin/photo/history.

## Independent distribution and offline rendering

The existing Library offers the optional **Place descriptions and photographs** resource. Its discovery manifest is published as reviewed Git data at `https://raw.githubusercontent.com/icfmp/Bible-Resources/main/datasets/place-context-catalogue.json`. Each payload URL pins a full immutable resource commit. GitHub Pages is not enabled for that repository; its failed Pages run is not claimed as a deployment. The committed Git distribution is independently available and tested.

An explicit Library metadata refresh can discover a newer revision without an application update. Installation checks size, checksum, format, revision and source metadata before atomically replacing only `study-data/place-context.json`. Loading reuses validated JSON while its file signature remains unchanged, with the bundled seed as a fallback for unavailable/corrupt optional data. Ordinary cross-reference/topic installation remains independent of the optional context endpoint. Opening a place never queries Wikipedia, Wikidata or Commons.

Photographs are downloaded only through an explicit action, bounded to 2 MiB and checked against the prepared hash. The image-only cache retains at most ten files (20 MiB). Cached files reopen offline; missing network or failed verification leaves local information/map/references available. Generation checks prevent a closed or changed card from receiving stale photo completions. Native movement/tiles remain libshumate's responsibility; leaving the Map tab removes the native layer and its pending tile work.

## Attribution and checks

OpenBible data retains CC BY 4.0 and applicable OpenStreetMap-derived database terms (ODbL 1.0). Wikidata metadata is CC0 1.0. Wikipedia extracts retain CC BY-SA 4.0 and permanent source-revision links. Every Commons file carries its own author, source, revision, license and derivative notice; one photo's license is never assumed for another. No photographs are bundled. For example, Jerusalem's contemporary photo is by askii, Commons page 154641343, CC BY-SA 2.0; the verified 960px derivative SHA-256 is `4fcf697ce4d9605241f5412b6951823546f688b52ec890a5a7804e98092cb501`.

The developer sample has passed actual download/hash/native-GTK decoding for all eight files, source-language/identity checks and multi-place native navigation. Publication evidence must separately identify the exact installed Flatpak, source, signing identity, release and retained-profile verification. These development checks are not client GNOME/Wayland/touch acceptance.

## Native first-frame loading follow-up

An installed-candidate test exposed an intermittent map left on Loading. A
controlled local HTTP failure also reproduced it: the mapped541×260 native
canvas emitted no tile request. A trace-only libshumate1.5.5 build identified
the exact layer: its deferred callback ran in the same frame which requested
deferral, kept `deferring` true, and removed its only callback. No tile existed
and no future callback remained. The existing vendored load-notification patch
now rearms that missing one-shot GTK tick. Native movement deferral and tile
cache remain intact; no application polling or separate map engine is added.
The controlled HTTP fixture retains the original timeout and checks actual
requests, error state, metadata, references and reading context. Repeated native
checks and the installed Flatpak must verify the revised exact source before
publication is claimed.
