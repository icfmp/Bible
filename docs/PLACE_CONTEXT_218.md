# Reviewed place context and optional photographs (#218)

The OpenBible index and its references are unchanged. Enrichments live separately
in `bible/study_data/place_context.json`, keyed by the stable ancient-place ID and
checked source name. The shared reader never matches an enrichment by translated
name or assigns coordinates from Wikipedia or a photograph.

| Existing OpenBible field | Previous presentation | Current presentation |
| --- | --- | --- |
| Name, identification status | Name and conservative certainty | Preserved; repeated identical heading omitted |
| Candidate names, coordinates, roles, modifiers | Map, candidate labels, approximation | Preserved, including rejected/uncertain alternatives |
| Translation name counts / aliases | Stored, omitted from card | Compact expandable source-name line; no claim all names are strict synonyms |
| Coordinate evidence links / Wikidata IDs | Stored, omitted | Accessible links under Sources and evidence |
| Bibliographic source titles | Stored, omitted | Source titles under Sources and evidence; no copyrighted book contents imported |
| Original evidence paths, source scores | Stored | Retained; no raw scores presented as archaeological probabilities |
| Unknown resolutions | No fabricated pin | Preserved; Nod has no historical enrichment or photograph |

## Reviewed Jerusalem enrichment

OpenBible `a15257a` identifies Jerusalem; its candidate `m66c5b8` cites the Old
City of Jerusalem article. Wikidata `Q1218` identifies the city and supplies the
reviewed P18 photograph. The JSON records the fetched Wikidata revision.

The historical introduction quotes the first two sentences of Wikipedia's
*History of Jerusalem*, revision `1382952817`. The French text is a translation
of that excerpt. Both are attributed to Wikipedia contributors under CC BY-SA
4.0, with permanent revision and history links. This is historical context,
not Scripture or an invented explanation of a biblical passage.

The Commons file *Dome of the Rock seen from the Mount of Olives (12395649153)
(cropped).jpg*, page ID `154641343`, is by **askii**, dated 30 November 2013.
File metadata was inspected directly: **CC BY-SA 2.0**, attribution required,
no additional restrictions. The original image SHA-1 is
`dcfad854858bd512e69c3c0c82da2aaf8f28b861`; the reviewed Commons upload timestamp
is `2024-11-07T21:16:43Z`. Its 960 px Wikimedia derivative is 230,592 bytes,
SHA-256 `4fcf697ce4d9605241f5412b6951823546f688b52ec890a5a7804e98092cb501`.
The source page, author and license are accessible with the image. Captioning
explicitly identifies a contemporary view (2013), not biblical-era scenery.
The Commons crop and Wikimedia thumbnail are identified in the JSON. The file
is displayed with its aspect ratio preserved; there is no image editing tool.

No picture is bundled. A clear download action requests only this pinned static
file, with a 2 MiB bound and checksum verification. Cached images reopen without
a network request. The dedicated image cache retains at most ten images (20 MiB
maximum); partial downloads never replace a verified image. Missing network,
failed verification or absent enrichment leaves the map and local references
available. A stale/closed window cannot receive a completed photo update, and
metadata workers do not keep application shutdown waiting for a remote socket.
No live Wikipedia/Wikidata/Commons API call occurs when a place is opened.

Emmaus retains all source candidates and the disputed label. No single candidate
gets promoted by a photograph. Nod remains unidentified, without a map pin,
photo or invented historical summary. Other places use existing structured facts;
adding a new reviewed enrichment is a data change, not a place-specific code path.

Native map architecture has since moved to libshumate (see its current module
and packaging). The original #49 design document records the earlier reviewed
coastline prototype; it is historical, not the current renderer specification.

Developer GTK checks, actual packaged checks, screenshots and client acceptance
must be reported separately. This document does not itself assert publication.
