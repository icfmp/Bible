# Contextual place cards (#49)

The source/map/dependency proposal was committed and reviewed in PR #77 before
implementation. The implementation follows that reviewed approach and the shared
References and note-preview deliveries; publication remains a separate gate.

## Audited inputs and coverage

OpenBible's Bible-Geocoding-Data is pinned to
`7eb18a5ee62f27b9b93bd6689ea272d76dd23b8f`:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `data/ancient.jsonl` | 11,550,193 | `b8187aa4737e8517ccc090f765d2be11da4c548cd2a59d3cdcb62e952cb8c0f2` |
| `data/modern.jsonl` | 3,224,520 | `da731f6e110bac4ea66a9f037a0a31cfb11c4f1efc1206aa9e109092b2c60087` |
| `data/source.jsonl` | 225,544 | `b93709cfd947430a3befe3a02a82787ef589c3223c903f4f234adaa46727856a` |

Immutable URLs use
`https://raw.githubusercontent.com/openbibleinfo/Bible-Geocoding-Data/<commit>/<path>`.
The actual JSON Lines contain **1,342 ancient places**, **1,596 modern locations**,
and **5,616 distinct associated verse addresses**. Fifty-seven auxiliary ancient
records have no direct verse association; retain them for identification context,
without inventing Bible links. Coverage is the publisher's Protestant/English
source project, not a claim of complete geographical coverage for every canon.
All recorded addresses validate in the audited OpenBible address space; none is
in 3 John. Canon validation alone is not evidence of installed Bible text.

The publisher README and schema distinguish ancient places from candidate modern
locations, source votes, identification paths, special/unknown resolutions,
coordinate roles and representative points for regions/rivers. Use the supplied
verse relationships, never naive matching of translated place names.

## Native map and exact dependency decision

Use **Gtk.DrawingArea with the Cairo binding already present** in the native
validation environment (1.27.0) and the actual GNOME 49 app runtime (1.29.1).
`import cairo; gi.require_foreign('cairo')` was checked in both. No Node/webview,
map service, account, API key, new Python dependency, libshumate dependency or
new runtime is proposed.

Download the real Natural Earth **1:50m coastline** with the place resource:

- Repository: `nvkelso/natural-earth-vector`.
- Commit: `ca96624a56bd078437bca8184e78163e5039ad19`.
- File: `geojson/ne_50m_coastline.geojson`, 1,640,858 bytes.
- SHA-256: `271f1c4c1908312bac6b29d158ea1356544beafc129f260005300913aa5ea283`.
- Actual collection: 1,428 LineString/MultiLineString features.
- Natural Earth identifies its map dataset as public domain; preserve source and
  [terms](https://www.naturalearthdata.com/about/terms-of-use/) in the resource.

The small map is a **simplified geographical overview using modern coastlines**,
not a street basemap or reconstructed historical terrain. Show all candidate
locations with corresponding numbered entries. Preserve coordinate roles and
uncertainty/radius descriptions; a representative point is not an exact settlement
pin or a drawn ancient boundary. Fit a readable regional extent, clip actual
source lines, and make latitude/longitude and candidate identities available as
text. Do not add country borders, historical routes, Google imagery, photos or
unreviewed tiles. Unknown places get an explicit useful no-identified-location
state, never a fabricated pin.

Map and metadata will work offline after this explicit resource installation.
There is no live tile service, tile prefetching, history/notes disclosure or
promise of street-level/offline atlas coverage. Failed map loading must leave
candidate metadata/evidence and local references usable.

## Licenses and transformations

The actual OpenBible README licenses the data **CC BY 4.0**, identifies
OpenStreetMap components as **ODbL 1.0**, and says image licenses vary. Preserve
those credits, source identity and license links. Exclude all images, thumbnails,
image URLs, `extra` thumbnail payloads and OpenStreetMap polygon/path geometry
from the imported representation. Preserve coordinate-source/geometry credit
when present and retain an OSM/ODbL notice for derived components; do not relabel
those components as public domain or covered solely by CC BY. Natural Earth
coastlines remain a separate credited public-domain input.

Only place/reference relationships, candidate coordinates/roles, source
identification evidence and bibliographic facts are proposed. No English Bible
quotation, scholarly book contents or image is imported. Original downloaded
notices and a reproducible transformation/source manifest must be retained.
Validate pinned hashes, bounded file/row sizes, identifiers, every reference and
finite coordinate bounds. Build a separate indexed SQLite resource including
map data, check integrity and atomically replace that one database only after
success. Failed/corrupt updates keep the previous usable resource; no personal
annotation/session format changes.

## Truthful identification and language

Retain all candidate identifications and their source scores/tags, including
negative/rejected and unknown alternatives where recorded. Source scores are
not new archaeological conclusions or user-facing probabilities. The README's
high-confidence threshold is a vote/path score of 500. Classification must first
check for actual modern candidates: **Nod has an unambiguous unknown-location
resolution with a score of 500**, so score alone must never label it known.
A well-attested single modern identification can be Known; likely source evidence
can be Probable; competing credible identifications remain Disputed; no identified
location remains Unknown. Document the actual deterministic rules and show the
underlying evidence/limits rather than hiding alternatives behind one pin.

Initial acceptance examples are real **Jerusalem** (`a15257a`, one modern
identification), **Emmaus** (`ae7274b`, six candidates) and **Nod** (`a1ad8e1`,
unknown; Genesis 4:16). Provide curated conventional French names and FR/EN status/
coordinate labels; keep the publisher's original names and English-translation
aliases in clearly identified source detail. Do not fabricate unknown French
names or imply a complete French historical gazetteer.

## Study interaction and acceptance gates

Expose an explicit **Places in this passage** action from study, without a
permanent map panel or another tool tab. A native adaptive dialog lists the
actual place associations for the verse/intentional range and opens a compact
card: localized name, source alternatives, status/evidence, small map, candidates,
related Bible references, attribution. Reuse the one local preview and its
explicit current/new-tab actions; preserve the reading anchor and unsaved guards.
Missing data uses the existing Library → Study resources flow.

Before closure: real pinned downloads/schema/coordinate audit; all three status
examples and multiple candidates; exact French/English local previews including
an actual numbering difference; actual native pointer/keyboard/dismissal,
narrow/themes, asynchronous stale-result guards, corrupt-update preservation,
offline restart and map fallback. Then source tests, installed Flatpak/byte audit,
review, exact-head CI, merge and the existing signed alpha with a real ordinary
update/profile-preservation check. Client GNOME/Wayland acceptance and in-depth
assistive technologies remain deferred and must not be claimed as tested.
Bible.com/BDS, full atlas features and photos remain outside this increment.

Source/CI dependency detail: native Ubuntu checks explicitly install the existing
Cairo Python/foreign-converter packages (`python3-cairo`, `python3-gi-cairo`).
The GNOME 49 application runtime already provides these bindings; the Flatpak
manifest and runtime/dependency versions are unchanged.

## Implemented behavior and current verification

The on-demand study action captures its actual verse/range and installed
translation. The adaptive dialog preserves this context until closed, queries a
separate optional SQLite resource and lists actual relationships. A card uses
curated conventional French names (approximately 80 entries), with publisher
names/aliases retained under source detail. This is partial name localization,
not a complete translated gazetteer. Scores and candidates remain source facts.
The deterministic status uses no coordinates → Unknown; multiple credible modern
IDs → Disputed; a single credible ID with path score >=500 → Known; otherwise
positive supplied confidence tags → Probable, else Disputed. Rejected and unknown
alternatives remain listed. Scores are explicitly not probabilities.

Native Cairo draws the audited coastlines and numbered candidates with an
aspect-correct regional extent. Nearby marker groups retain their numbers (or
an explicit alternative count); candidates, coordinate roles, source modifiers
and uncertainty radii remain individually readable below. No map pin is invented
for unknown locations. Missing map/binding/data leaves factual metadata and
references available. Context references are prioritized before canonical order;
View all uses virtualized results. Exact excerpts and navigation reuse #47/#50,
including the note-save guard. Escape dismisses a preview before its containing
Adw.Dialog; the dialog's original close policy is restored on dismissal.

The importer bounds all five hash-pinned inputs, validates IDs, references,
finite coordinates and candidate evidence, retains original license/manifest in
the resource, builds an integrity-checked staged database and atomically replaces
only that resource. Failed updates leave the old database unchanged. No note,
highlight, session or module migration is introduced.

Real-source checks imported 1,342 ancient places, 1,596 modern locations and 442
bibliographic sources in 0.549 s in the validation container. Actual native
Library download completed in 9.881 s. Real pointer/keyboard source checks pass
online and in an isolated network namespace: Jerusalem, all six Emmaus candidates,
unknown Nod, actual source coordinates, exact installed KJV text, French
FreSegond Ps 42:7 resolved from source Ps 42:6, preview/current/new tab, Escape,
failed-update retention, narrow/light/dark/emulated-high-contrast and restart.
Source tests: 212 pass before final presentation refinements; the final affected
suites pass 24 source / 32 installed tests. All 78 packaged application files
match source, with 14 verified canonical mappings and required notices. Actual
Flatpak Library download (9.956 s) and network-isolated restart/native checks
pass; committed receipts and captures record these separately from publication.
These are automated native GTK/Xvfb checks. Deep accessibility and personal
GNOME/Wayland acceptance have not been tested.
