# Frozen optional study data for performance comparisons

This is the previously validated OpenBible.info topic index used by the 25 October developer study-navigation profile. It contains topic identifiers, verse relationships and quality scores, without Scripture quotations or user annotations. It is an optional diagnostic fixture, not an application download or a translation bundled with Bible.

Source: [OpenBible.info Topics](https://www.openbible.info/topics/), source snapshot 2026-10-19, [original download](https://a.openbible.info/data/topic-scores.zip). Attribution: OpenBible.info and its contributors. License: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).

The supplied relationships were validated and converted to a local SQLite index. Exact duplicate ranges use their maximum score and canonical order. The original source metadata, transformation description and source archive digest are preserved inside the database and in `topic-provenance.json`; gzip compression is the only additional transformation here. The original upstream archive SHA-256 is `47bc1cb1defe5b8f0f65ca9966cd99ff151b7f22cab18ef9c99eda6a244df7cc`.

Database SHA-256: `90db0daa43b1981a82d66481dc07211e395eba5ab56c15a8ee57cdb06d1ec209`. Performance workflows must pin this evidence commit, verify the database bytes after decompression, and retain the same index across version switches and repeated cycles. This preserves the previously installed dataset when the live upstream weekly archive changes; it does not bypass or weaken the application's download checksum validation. Existing client data is not accessed.
