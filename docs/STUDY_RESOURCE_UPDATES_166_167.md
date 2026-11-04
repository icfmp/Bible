# Durable study data and independently maintained topic names

Related to #166 and #167. Descriptions and every current comment were read before implementation. This is implementation/review evidence; publication and installed Flatpak validation remain pending.

## Demonstrated failures

The real upstream cross-reference ZIP returned HTTP 200 with generation 2026-11-02, 1,984,180 bytes and SHA-256 `24f07bcd61280f9dc0c5a451151fc9c9d0d2e45fe0cf3c903b5db4ca6b878878`. Topics returned HTTP 200 with generation 2026-11-02, 418,746 bytes and SHA-256 `b20499362abe0c71c45bb18cca1dcf386b8caf50381e6246cc531fa7a69aa2cf`. Both installed-baseline operations rejected the changed checksums; direct parsing then independently rejected the changed date against the old 2026-10-19 header. Working test-profile database digests remained identical after those failures.

Keeping the schema/reference/bounds checks while supplying the actual generation date validated 344,799 reference relationships and 71,377 topic relationships. Actual new local SQLite indexes reopen with those dates/hashes; John 3:16 has 23 cross-reference results, and forgiveness has 13 topic results. The source contains 6,712 topic identifiers; all 50 existing reviewed names are present. The four `pardon` concepts remain distinct. These are data-parser/local offline checks, not installed Library proof.

## Checked snapshots instead of executable weekly pins

Applications read a bounded versioned catalogue from the project's existing GitHub hosting. Each known resource record declares a compatible parser format, actual generation date, revision, exact byte size and SHA-256, pointing to an immutable asset in `study-resource-archives`. Archive/schema/reference/canon/score/size checks remain mandatory. Dates are actual compatible metadata, not a substitute for schema validation. The application never accepts an unchecked rolling upstream archive as an update.

`tools.study_resource_updates` validates complete upstream archives before preparing snapshots. Its reviewed publication path appends immutable assets, verifies GitHub's size/digest, and then advances `data/study-resources` without forcing it. Existing assets/tags are never overwritten/moved, and concurrent data-branch edits stop stale publication. The initial checked catalogue and files are bundled as a safe known fallback; no complete Bible translation is included.

A small existing-hosting workflow can refresh compatible snapshots weekly or on request. It does not rebuild or publish the application. Only an actual incompatible schema/capability change requires new executable support. Update failures retain the previously published snapshots and installed working data.

Library > Study tools refreshes only the small catalogue through the existing metadata workers. No network runs in GTK callbacks; no periodic application refresh worker is added. Installed older indexes remain marked installed and available offline while offering an update. A malformed catalogue cannot replace the known metadata cache. When metadata is unavailable, a working differing installed version is preserved instead of being overwritten using an older fallback.

## Independent vocabulary and exact source identity

The original 50 identifiers, French labels and synonym sets are preserved byte-for-value in reviewed JSON, alongside English labels, revision, attribution and project license. Python contains validation/search logic, with a packaged fallback resource. Each profile can install a newer checked vocabulary independently of the index or application. UI-string translation stays separate.

Maintain the data branch's `topic-vocabulary.json` through a reviewed content change, retain stable source identifiers and attribution, and bump the `YYYY-MM-DD.counter` revision. Run the workflow in vocabulary-only mode. Index revisions/bytes remain unchanged. The same reader accepts that data update; no Python edit or application alpha is required.

The index retains all source topics. Suggestions expose the exact-ID intersection of reviewed vocabulary and actual installed source identifiers. New source topics remain outside the curated list until their names are reviewed; removed/renamed identifiers hide unmatched names without blocking the entire valid index or attaching them to another concept. A reviewed entry without French wording uses its explicit English label. Current shipped coverage is 50 reviewed names out of 6,712 source topics, not full source localization. No runtime AI or network translation is required.

Both new payloads are validated before committing a combined update. Index and vocabulary files are individually replaced atomically; ordinary commit errors restore the prior vocabulary. Their exact-ID join remains valid across independent versions and an interrupted update. Malformed/truncated/incompatible payloads preserve working files. Notes, preferences, translations and sessions are not rewritten.

## Verification state

Thirteen focused catalogue/update/parser tests and 36 affected local GTK/data tests pass. They exercise changed generation/content, malformed manifests, checksum/schema rejection, old index preservation, index updates with partial vocabulary, English fallback, offline readback and a vocabulary-only update with identical index bytes. French/English `pardon` behavior remains covered. Snapshot preparation validates the two full real archives; no Scripture corpus/profile is exported to Git.

The remote catalogue branch/technical assets are prepared and still need actual publication before these download URLs are usable. Full CI, installed Flatpak Library downloads, offline restart, native captures, signed application deployment and the matching numbered application release remain pending. Existing issues stay open for client acceptance. Cloud/Xvfb checks do not establish acceptance on the client's GNOME desktop.
