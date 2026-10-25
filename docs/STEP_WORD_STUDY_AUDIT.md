# STEP word-study data audit

Related to #114. Pinned upstream: [`be4191f0082aeedddb0eff0c02c966292b2bd641`](https://github.com/STEPBible/STEPBible-Data/tree/be4191f0082aeedddb0eff0c02c966292b2bd641).
Exact paths, byte sizes and SHA-256 hashes are in `bible/step_sources.py`.
Read the repository README **and each file header** when changing this pin.

## Selected data and licensing

- TBESG: Greek Extended/Disambiguated Strong IDs, supplied lemma,
  transliteration, category, brief gloss and Abbott-Smith-based definition.
  Its own header identifies Tyndale House / STEPBible and CC BY 4.0.
- TAGNT: both NT files. Include only records whose **Editions field explicitly
  lists NA27**. Keep the supplied common Greek spelling and transliteration;
  the header says spellings generally follow NA28 and punctuation follows
  Tyndale. This is an identified **TAGNT NA27-membership corpus**, not a newly
  reconstructed NA27 critical text. Do not concatenate TR/Byz/other alternatives
  or infer that an installed translation follows these tokens.
- TAHOT: all four OT files, main records beginning L or Q (including Qere).
  Exclude R/X additions and other alternative readings. Retain segmentation,
  English brief word/lemma glosses, disambiguated IDs and morphology codes.
  This is **TAHOT's L/Q main reading**, not an unmodified Leningrad manuscript.
  The file headers explicitly license these data under CC BY 4.0.
- **TBESH is excluded.** In addition to a CC BY header, it states that permission
  should be obtained from Online Bible before applying its abridged-BDB
  definitions to a project. No such permission has been established. Hebrew
  lemma forms and brief glosses in this increment come from TAHOT's own fields;
  no TBESH definition is imported, served or downloaded by the app.
- **TTESV is excluded.** Its own filename **and header** specify CC BY-NC 4.0,
  despite the broader repository README's CC BY presentation. File-level terms
  apply to any future evaluation; it is neither needed nor used here.
- TIPNR, AI prose, people/place enrichment, interlinear views and textual
  criticism are excluded. SWORD remains the Bible/commentary provider.

Download only these seven pinned files directly from upstream after an explicit
request. Do not bundle their full texts with application packages or Git sources.
Keep upstream attribution, the file-header notices and transformation description
available offline. The original-data request to use upstream distribution is
honoured by downloading there directly. No message has been sent to upstream.

## Format and reference findings

TSV records follow substantial introductory headers. Parse data records by their
full reference/word/reading key, rather than assuming a fixed header line count.
The supplied primary English reference convention is NRSV; alternate Hebrew/KJV
and other references are retained in the source identity, not discarded.
Map through Bible's existing verified reference resolver, never by equal printed
verse numbers or token positions.

For example, `Gen.31.55(32.1)#01=L` retains its Hebrew alternative. Psalm headings
can contain two records with the **same English `.0` reference and word number**
but different Hebrew references. Deduplicating just English reference + word
number loses words. Preserve the entire source key. Verse-zero titles remain
honest source addresses; do not turn them into invented verse-one alignments.

Greek field 3 contains the disambiguated Strong ID and source grammar; field 5
is edition membership. Hebrew field 4 contains lexical/affix identifiers and
field 11 contains supplied lemma/gloss components. Affix tags are not silently
treated as ordinary lexical definitions. Distinct extended IDs stay distinct.
A basic `H1254` lookup yields explicit alternatives `H1254A` (to create) and
`H1254B` (to fatten), requiring a choice; it never merges their occurrence counts.

## Reproducible real-data proof before UI integration

Using the exact seven files and the provider's `install_files`:

- **137,992 Greek source tokens**, **305,465 Hebrew/Aramaic source tokens**.
- Index preparation: **10.88 seconds**, local SQLite **274,313,216 bytes**, including
  the original input-file headers/notices, in
  the managed developer container. Download total is the sum of pinned sizes
  in `step_sources.DOWNLOAD_BYTES`; allow additional temporary update space.
- `G3056`: supplied lemma **λόγος**, transliteration **logos**, gloss **word**;
  **330 source tokens in 317 distinct numeric verses**, TAGNT NA27 membership.
  John 1:1 source exploration returns 17 actual source tokens.
- `H1254A`: supplied lemma **בָּרָא**, brief TAHOT gloss **to create**;
  **53 source tokens in 45 distinct numeric verses**, TAHOT L/Q main reading.
  Genesis 1:1 source exploration returns seven actual segmented source words.

Counts refer to the selected corpus and exact disambiguated identifier. Tokens
and distinct verses are different units; title addresses are retained in results
but excluded from numeric-verse counts. Results use deterministic canonical
source order. Counts make no claim about translated-word frequency.

Installed-resource audit in the same disposable profile:

| Resource | Actual metadata | Safe claim |
| --- | --- | --- |
| FreSegond1910 | OSIS, Segond, French; `<w lemma="strong:…">` on actual words | Verified source-word Strong lexical lookup where full text alignment succeeds; no STEP inflection/sense alignment inferred |
| KJV | OSIS, KJV; grouped English `<w>` spans, sometimes several Strong IDs, TR lemma/morphology attributes | Show all supplied identifiers/ambiguities; TR metadata does not prove an exact NA27 token or sense |
| eBible Darby (`ebible~frajnd2024eb`) | OSIS, Luther, French; translation notes but no `<w>`/Strong tags in audited verses | Explore the mapped original source verse; do not guess a clicked word's lemma |
| FreLSN1872 | OSIS, Calvin, French; no proven token metadata in audited verses | Same explicit verse-exploration fallback |

The audit used real Genesis 1:1 and John 1:1 raw entries, not fixture metadata.
Raw notes/markup remain untrusted. Token-level alignment must validate the whole
rendered source text and selection boundaries before exposing a lexical match.
Strong identity alone never proves a specific STEP token, extended sense or
inflected form. English lexical content remains explicitly English in French UI.

Developer evidence is reproducible with `StepData.install_files`, `lookup`,
`verse` and `occurrences`. These findings do not constitute client GNOME desktop
acceptance, a delivered UI or permission to expand the selected datasets.

Basic Hebrew/Aramaic noun/verb labels were checked against the pinned repository's
`Morphology codes/TEHMC - Translators Expansion of Hebrew Morphology Codes - STEPBible.org CC BY.txt`
(394,580 bytes; SHA-256 `78779bea824b31d4467dec0161d547481c86f266bc39def12cd11dc7dcbe6da7`).
Only those basic function labels are used; raw source grammar remains available
in Details, without inferring tense or a passage-specific lexical sense.

Actual native GTK installation proof: cancelled after 278,528 bytes without a
partial installed index; retry downloaded all 105,074,789 pinned bytes and
prepared the index in 37.58 seconds including transfer. Maximum GTK heartbeat
gap was 0.063 seconds. This used a disposable fixture reader and real upstream
STEP data; reference/resource/empty-note state remained unchanged. Existing-data
rollback/cancellation and corrupt-update preservation are checked separately.
