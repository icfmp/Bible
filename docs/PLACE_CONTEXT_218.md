# Place cards: existing OpenBible data only

After the client-requested scope cleanup of PR250, place cards consume only the existing installed OpenBible index through `PlaceData`. The application retains the provider's ancient IDs, proposed modern IDs, coordinates, roles, uncertainty, evidence, bibliography and Bible references. Existing deterministic indexing/rendering and verified reference mapping do not create source facts.

Repeated evidence for the same supplied modern ID may share a presentation heading; every source proposal and map candidate is preserved. Coordinate-source links do not establish the identity of an ancient biblical place with a modern entity. Source descriptions remain source text, without runtime translation or generated summaries.

No historical-description or photograph resource is available in this scope. The generated context seed, optional context downloader and photo rendering are removed. The old authored/translated Jerusalem-only sample is not restored. Existing downloaded profile files, indexes and image caches are not deleted or migrated; the removed context paths no longer consume them.

Further sources must be proposed to the client before integration. Do not create a dataset or preparation/distribution pipeline to fill missing content. See [the cleanup inventory](SCOPE_CLEANUP_250.md). No completed #218 delivery or client acceptance is claimed.

## Existing native map investigation

The pre-existing libshumate patch in `packaging/shumate-load-notification.patch` remains unchanged. It addresses a previously measured lost one-shot map-render notification. This cleanup does not disable the map, introduce polling, remove its controls or weaken its existing readiness checks. Map validation still requires the actual packaged libshumate runtime; a host GTK test is not equivalent to the installed Flatpak.
