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


## Implemented vocabulary and verification

The supported selection is **50 topics**, explicitly enumerated in
`topic_vocabulary.py`. Both interface languages use the same scope. The reviewed
labels/synonyms distinguish Pardon, Pardon des péchés, Pardonner aux autres and
Réconciliation. Examples include Grâce, Foi, Espérance, Inquiétude, Paix,
Miséricorde, Prière, Amitié, Maîtrise de soi and Vie éternelle. English identifiers
remain visible as source detail; all 6,712 identifiers are indexed, while only
these 50 are offered for browsing. Changes to this selection require an explicit
vocabulary edit and an importer check that every identifier exists upstream.

The existing passage/history widgets and keyboard reference shortcut remain;
compact linked native mode buttons fit a 360-pixel window. Text search returns
at most 500 matches and reports the total; literal SWORD search runs in a child
with a 30-second timeout. Superseded queued work is cancelled and generation
guards discard stale completions. Separate Reader instances prevent mutation
of active reading. No stored annotation/session/module format changes.

Validation receipts and actual installed Flatpak captures are in
`docs/evidence/study-48` and `docs/captures/topics-48-*`. All **219 source tests**
pass; **50 affected installed Flatpak tests** pass. Every one of the **82 packaged
application files** matches source, and all 14 mapping tables/notices remain.
Real native online/offline checks cover FR/EN source vocabulary, four distinct
pardon suggestions, accents/synonyms, missing vocabulary, exact French/English
OT/NT excerpts, explicit current/new-tab, keyboard/Escape, history preservation,
literal phrase/metacharacter handling, failed-update retention and restart.
Actual FreSegond Psalm 34:5 is verified from source Psalm 34:4. Both installed
literal searches for “light of the world” / “lumière du monde” return Matthew
5:14, John 8:12 and John 9:5. A 10 ms GLib heartbeat continues during the native
search (approximately 247 callbacks during the measured interaction).

Observed indexing: 0.399 s directly, 0.513 s source Library run, 0.672 s packaged.
Actual packaged Library download/index completed in 2.961 s. Of 250 representative
queries, median 0.146 ms and p95 0.198 ms (cold maximum 11.394 ms). These are
container observations, not desktop guarantees.

Narrow/light/dark/emulated-high-contrast checks pass. Resizing with the separate
study drawer closed can emit an Adwaita/GTK zero-allocation diagnostic for that
hidden drawer's existing tool stack; the actual visible search controls fit and
remain usable. The diagnostic was traced to `StudyPanel.tools`, not a search
result or invented data, and is not suppressed. No visual/user-data failure was
observed in the real-module probes. Deep accessibility and client GNOME/Wayland
acceptance have **not** been tested. Signed publication and actual ordinary
update/profile/study-cache preservation remain separate gates after review/CI.
