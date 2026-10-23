# Curated local topic search (#48)

## Audited source and proposed scope

The actual [OpenBible topics page](https://www.openbible.info/topics/) links
`https://a.openbible.info/data/topic-scores.zip` and licenses its non-Scripture
content under CC BY 4.0. The inspected 2026-10-19 ZIP is 418,767 bytes, SHA-256
`47bc1cb1defe5b8f0f65ca9966cd99ff151b7f22cab18ef9c99eda6a244df7cc`.
Its one `topic-scores.txt` is 2,019,879 bytes: a four-field dated header, then
71,358 three-field rows (topic identifier, OSIS range, integer quality score),
6,712 distinct English topic identifiers. Actual scores range from 2 to 100.
All source references validate against the separately audited OpenBible address
space, including its split 3 John ending. No website ESV quotations are imported.

First supported vocabulary: the explicit curated FR/EN entries and synonyms in
`bible/topic_vocabulary.py`. Both languages use this same limited selection;
other downloaded English identifiers remain indexed for source reproducibility
but are not silently exposed as translated topics. Forgiveness received,
forgiving others and reconciliation remain distinct. Search normalizes accents,
case and punctuation, with exact/prefix/token matching; no sentence understanding,
AI interpretation, account or provider. The UI must identify partial coverage.

Import the entire audited relationship file into a bounded, separately indexed
SQLite study resource with source/date/checksum/license/transformation metadata.
Strict ZIP/schema/reference/score validation, integrity check, fsync and atomic
replacement retain working data after failure. Deduplicate exact destination
ranges per topic using maximum source score, then canonical order. Never combine
different topic identifiers into a fabricated theological conclusion.

## Existing search and literal text

Source inspection found an actual passage selector with direct reference,
book-name filtering, version selection and history, but **no implemented text
search** to preserve. Extend this same surface with Passage / Text / Topics,
retaining the existing passage/history widgets. Add an explicit literal phrase
search of the selected installed SWORD Bible. Actual SWORD 1.9 bindings expose
`SWModule.doSearch(query, -1, 2)` (phrase, case-insensitive); real KJV returned
Matthew 5:14, John 8:12 and John 9:5 for “light of the world” in 1.58 s.
Run that mutable native search in a bounded isolated child process, not on the
GTK reader or main thread; timeout, stale-result and result-count guards apply.
No regular expressions, online text or unsolicited module download.

Both result types reuse the shared exact local passage preview and explicit
current/new-tab actions. Merely browsing results preserves reading/history;
source and translation changes dismiss stale previews. Missing data uses Library
Study resources; missing translation, unsupported numbering, no topic and no
text results remain explicit. There is no new drawer tab or search window.

## Required validation before publication

Actual source import and reproducibility; every supported vocabulary identifier;
French/English synonyms, accents and ambiguous forgiveness themes; exact installed
French/English OT/NT excerpts and numbering; genuine phrase search and unchanged
passage/history; no-network restart, corrupt update retention, stale jobs and
GTK responsiveness; native pointer/keyboard, narrow/light/dark/emulated high
contrast; indexing/search timings; source and installed Flatpak tests and byte
audit. Then review, exact-head CI, ordered merge, signed alpha and a real ordinary
update retaining annotations, modules, preferences and all installed study data.
Deep accessibility and personal GNOME/Wayland acceptance are not claimed.
Bible.com/BDS and AI interpretation remain outside this increment.
