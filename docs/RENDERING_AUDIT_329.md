# Rendering audit — issue 329

Audit date: 25 November 2026. Related to #329 and PR #330. This is a capability
inventory and a measured paragraph correction, not a claim of complete support
for every SWORD markup vocabulary. No resource content or provider was added.

## Shared paths and boundaries

The application uses public SWORD `getRawEntry`, `stripText`, native verse keys,
linked entries and module metadata. It does not render provider HTML in a web
engine. `Reader.chapter` supplies the verified body; `structured_text.extract`
adds OSIS/ThML structure only if its non-whitespace body agrees with that
projection. A mismatch retains the native plain body rather than guessing words.
Imported source-addressed OSIS also uses its previously verified source-unit map.

`BiblePages.document` is shared by ordinary reading, comparison and Bible
immersion; `bible_render.render` applies the native GTK tags. Commentary Study and
commentary immersion both use `CommentaryPages.document` and
`commentary_format.format_entry`. These share a document/copy model but do not
have interchangeable offset contracts: the Bible's native-emphasis probe now
explicitly requests `preserve_offsets=True`; it must not inherit commentary
whitespace insertions. Search/excerpt surfaces deliberately consume the same
reader's verse text, rather than reparsing raw source markup independently.

| Actual surface | Consumer and current behavior | Audit result / limit |
| --- | --- | --- |
| Main Bible | `BiblePages`, `bible_render`; source headings, paragraphs, notes/markers, verse identity | PASS for sampled real OSIS editions; not universal vocabulary coverage |
| Parallel Bible | Same document/render path for each original reader; shared resolution handles numbering separately | Shared parser/offset contracts checked; real synchronization remains part of normal CI |
| Bible immersion | Same `BiblePages`, paginated `Document` and copy projection | Existing native immersion checks pass; no new renderer |
| Commentary Study | `CommentaryPages` -> `StudyPanel.rebuild` -> native text tags | PASS: exact HMCC 0.1.0 case in a 408 px sidebar, actual selection/copy |
| Commentary immersion | Same `CommentaryPages`, paginated GTK rendering | Real HMCC entry opens/closes; existing native consumer checks pass |
| Source prefaces/introductions | `preverse_layout`, `editorial_view.fill_introduction` | Source-owned content remains separate; native layout regression passes with pre-existing runner allocation warnings |
| Cross-reference/theme preview | `reference_targets.local_excerpt`, `ReferencePreview` | Uses verified edition/numbering and plain verse excerpts; full editorial layout is NOT APPLICABLE to an excerpt |
| Search and result cards | `text_search`, `StudySearch`, `passage_card` | Search indexes the reader's body; excerpts are plain native text. Rich source-document layout is NOT IMPLEMENTED in snippets |
| Note/highlight/linked cards | `annotation_card`, `passage_card`, `passage_verses` | Same card renderer and original-edition excerpts; native note-preview citations retain their existing preview actions |
| Library details | `resource_details`, `resource_profile`, native labels | Approved Markdown profile or exact original About; escaped/inert native text, no HTML execution. NOT a Scripture renderer |
| Original-text/word study | `word_study`, `step_data` | STEP's identified tokens/senses in native controls; NOT a generic SWORD dictionary renderer; no silent translation |
| Generic dictionaries/lexicons | `DictionaryReader.verify_readable` | Native installation/readability verification exists; the general dictionary reading UI is NOT IMPLEMENTED. Curated dictionary integration remains explicitly deferred |
| General books | `GeneralBookReader.verify_readable` | Native tree-key installation verification exists; a general-book reading UI is NOT IMPLEMENTED |
| Copy/export | `Document.copy`, `bible_render.bind_copy`; personal Markdown/backup export is a separate path | PASS for actual HMCC GTK clipboard and existing native immersion/copy regressions. Authorial characters retained; generated UI context/decorations omitted |
| Accessibility | Native GTK text, buttons, labels and accessible action names | Code paths inspected. Screen-reader speech order and the client's GNOME/Wayland setup are NOT TESTED here |

## Source vocabulary inventory

PASS below means the listed path has code and bounded tests, not that every
possible tag combination or edition has been visually accepted.

| Feature | Bible OSIS | Bible ThML | Commentary OSIS / ThML | Other source types |
| --- | --- | --- | --- | --- |
| Exact body fallback | PASS, verified projection | PASS, native SWORD body | PASS, native SWORD body | Native plain fallback; no invented rich formatting |
| Paragraph/block boundaries | PASS: p/div milestones, line breaks | Implemented p/lg/div and line breaks; real ThML Bible NOT TESTED | PASS: verified block/line boundary insertion, paired milestones | TEI/GBF rich block restoration NOT IMPLEMENTED |
| Source headings | PASS, separate from generated chapter title | h1–h4 handled; real ThML Bible NOT TESTED | OSIS titles and ThML h1–h6 handled after verification | No custom heading interpretation |
| Emphasis | hi/transChange/divineName and supported native decorations | Generic HTML i/b styles NOT IMPLEMENTED in the Bible path | Supported hi and i/em/b/strong/super/sub, after native-text verification | Native text fallback only |
| Poetry | l/lg and source line boundaries | Basic line boundaries; no full vocabulary claim | Supported line/poetry spans | Rich poetry layouts NOT IMPLEMENTED |
| Lists / quotations | Dedicated list/quote presentation NOT IMPLEMENTED | Dedicated list/quote presentation NOT IMPLEMENTED | item/li, blockquote/block q supported and indented | Native words only |
| Notes / Strong's / morphology | Existing verified markers/lookup paths; source identities retained | Edition-dependent, no generic completeness claim | Source note bodies are excluded from ordinary body; generic interactive source-note/link UI NOT IMPLEMENTED | Depends on implemented tool, not inferred from metadata |
| References/links | Existing source-note/reference preview paths | Provider-dependent; real generic ThML link coverage NOT TESTED | Literal source citation retained; clickable inline commentary references NOT IMPLEMENTED | No guessed destinations |
| RTL/bidi | Existing reader direction + native GTK shaping | Same direction path | Same reader direction path | Actual real RTL resource visual replay NOT TESTED in this audit |
| Tables, media, figures | Dedicated layout NOT IMPLEMENTED | Dedicated layout NOT IMPLEMENTED | Dedicated layout NOT IMPLEMENTED | No fabricated alt text, image or table reconstruction |

OSIS and ThML real samples are listed below. Plain-text fallback and markup safety
have fixture coverage. No suitable real TEI or GBF verse resource was installed;
those real-source checks are **NOT TESTED**, not PASS or absent-data claims.
A dictionary using TEI is not evidence that a verse-reading UI supports TEI.

## Measured correction and PR review

The reviewed PR #330 contributes the verified paragraph insertion and offset
remapping. Its original authorship/history is retained. Integration preserves
newer protections already on main: native inline titles appear once; prefaces,
source-authored asterisks and verified numeric-entity behavior are not stripped
heuristically. The Bible emphasis-only caller keeps native offsets. Style remaps
use prefix sums and binary search rather than rescanning all insertions per span.
PR #330's earlier CI failure was the old live-Library fixture wait, already
corrected on main; this does not replace testing the integrated code.

The exact published **HMCCModern 0.1.0** archive has SHA-256
`dd1940b3bf85cc09659b634dc74c9a9d8810816bc2f8316a8293f893c3eb94ee`.
Genesis 10:8–14 contains 21 source paragraph starts, 21 ends and four bold phrases.
The old signed alpha.38 was compared with this branch on the same staged real
module, GTK 4.20.4/GNOME 49, software OpenGL, French UI, 1180×900 window,
**408 px sidebar / 400 px text view**.

| Observation | Installed alpha.38 | Integrated correction |
| --- | --- | --- |
| GTK clipboard newlines in selected entry body | 5 | 42 |
| Seven measured joins such as `day.Before` / `households.Nimrod` | Present | Absent |
| Native generated emphasis markers displayed/copied | Already suppressed | Still suppressed |
| Source bold ranges | 4 | 4 |
| Raw entry, native StripText output and installed module bytes | Baseline | Unchanged |
| Copied non-whitespace authorial characters, in order | Baseline | Identical |
| Source Genesis 6:4 citation | Retained as native text | Retained as native text; no new click action claimed |

Before/after captures are actual GTK screen grabs. The historical packages were
obtained from existing published releases and staged through the normal installer
with their published catalogue checksums; this is not a claim that the current
catalogue still distributes those versions. The current feed's HMCCModern 1.0.0 was separately downloaded through the normal
checksum-checked installer and its Genesis 10:8–14 document verified: 42 copy
newlines, heading/bold/hidden-marker styles, without replacing the historical
comparison module.
Diatheke/Xiphos were not installed: **NOT TESTED** as an independent reference
client. SWORD's raw/native output and an independent XML event counter provided
the source comparison; neither is misreported as an external-client replay.

Additional real native projection/copy checks preserved the sampled body units:
KJV 3.1 (Psalm 119, 176 units), CrossWire FreSegond1910 4.0 (Genesis 11, 32),
BDS/YV21 (Mark 11, 33), NBS/YV104 (Psalm 12, 9), Martin 1707 1.1.1 (Genesis 14,
24), and Bible Resources Segond 1.0.2 (Genesis 10, 32). Real commentary documents
were also exercised with Wesley 1.1/ThML, Bible Resources MHC 1.0.0/OSIS and
historical HMCCModern 0.1.0/OSIS. These are samples, not whole-corpus certification.

## Explicit gaps and next validation

The audit records the generic dictionary/general-book reading interfaces,
TEI/GBF rich layouts, Bible list/quotation/ThML emphasis, table/media rendering,
interactive commentary references, real RTL replay and assistive-technology
validation as gaps. They are not implemented by this paragraph fix and must not
be silently advertised as supported. Any future work needs an assigned scope and
existing legitimate source data; no data is authored or reconstructed to fill it.

Local targeted renderer/consumer checks: 38 pass. Three additional source-unit
checks cannot be claimed green in this local installed-runtime wrapper: one
needs the non-runtime test dependency `lxml`; two annotation fixture checks also
fail identically on unchanged installed alpha.38. Their assertions were retained,
not weakened. Normal CI remains a separate required gate and will determine
whether these runner-specific failures reproduce in its supported test setup.
Cloud X11/software rendering does not prove the client's hardware/Wayland or
screen reader behavior. Merge, signed update, numbered release and final client
acceptance must be reported separately; this document alone is not publication.
