# Bible.com offline editions — issue #26

Status: **implementation in draft PR #134; expanded seven-edition package validation pending**. No issue is closed. Numbered release #87 remains paused. The client has requested validation and signed-alpha publication of #26, followed by the separately assigned feedback issues.

## Implemented scope

Library offers exactly these reviewed editions. It downloads translation metadata when requested; it never acquires a Bible during startup or merely opening its details.

| Edition | Source ID | Language | Native reference index | Indexed entries |
| --- | ---: | --- | --- | ---: |
| La Bible du Semeur 2015 | 21 | French | Original | 1,255 |
| La Sainte Bible par Louis Segond 1910 | 93 | French | YouVersion93 | 1,255 |
| Bible J.N. Darby | 64 | French | Original | 1,189 |
| Ostervald | 131 | French | YouVersion131 | 1,189 |
| King James Version | 1 | English | KJV | 1,189 |
| American Standard Version | 12 | English | KJV | 1,189 |
| Berean Standard Bible | 3034 | English | KJV | 1,189 |

Acquisition uses the current JSON metadata and its returned `offline.url`. No guessed archive suffix, website scraping, extracted app key, account impersonation or remote agreement submission is involved. Identity, language, returned HTTPS host/path, bounded ZIP inventory/CRC and source references are checked. Official project-key API access is not claimed; these observed legacy endpoints are not represented as a supported public API contract.

Before downloading, Library displays source attribution/conditions and requires a local acknowledgement bound to the exact metadata. Anonymously reachable content is not treated as provider approval. The source email-agreement requirement is stated explicitly; each user must satisfy applicable source requirements. The application does not assert or submit that agreement. Missing copyright notices remain absent, rather than being invented as a Public Domain declaration. Actual supplied notices and all agreement/redownload/update fields are retained offline.

The seven metadata requests use two workers; one refusal retains other editions and the failed edition's cached record. Download revalidates metadata, supports validated Range/If-Range resume, honours bounded Retry-After, and stops on authentication refusal. Completed archives are reused. Cache receipts are atomic; a damaged completed package restarts without treating its corrupt bytes as a resumable prefix.

A separate cancellable process streams source chapters into OSIS, invokes the packaged compiler without a shell, then checks **every** indexed chapter/introduction, source unit, bridge, note, heading and semantic role through native SWORD. Cancellation terminates its process group. Failed staging never becomes installed; existing resources are not overwritten. Registration is atomic. Original metadata, acquisition context, parser version, archive and individual source hashes remain on the user's machine. No Scripture, source HTML, complete OSIS or compiled resource is included in the application or public artifacts.

## Fidelity and reference behavior

The codec preserves ordered fragments, Unicode, paragraph/poetry structure, explicit inline roles, footnotes, source headings, introductions and tables. Unknown structures fail instead of being silently flattened. Verse bridges use native links; all reference members remain selectable, while their body is rendered/copied/indexed once. Genuinely repeated independently stored text remains distinct. Derived search indexes rebuild lazily; personal notes and preferences do not migrate or reset.

Do not infer numbering from language or the raw `vrs` label. All four French editions return `org`, but their actual indexes differ. Semeur and current Darby match every SIL Original chapter maximum. Original has a distinct native registration, preserving German unchanged. The mapping uses pinned SIL English/Original OT definitions and the existing JSword German UBS/GNT NT rules, with every NT chapter maximum checked against SIL Original. Unsupported split rules remain explicitly unmapped. An unnumbered Psalm heading is not assigned to a fabricated verse zero or to a neighboring verse.

LSG's returned index differs from native Segond in Job 34 and Mark 10; Ostervald differs in 23 chapter maxima. Their exact publisher indexes are registered separately and retained, without truncating or renumbering content. **Automatic cross-edition verse alignment is unavailable for these two indexes.** Independent parallel reading remains available; their annotations retain their original source context, but automatic display across other numbering systems requires a verified correspondence. The UI states this limitation. Equal-looking labels are not silently treated as verified equivalence.

The four-line SWORD entity-fidelity correction prevents loss of entity text or following separators. Full application readback also exposed native StripText presentation transforms: inserted emphasis asterisks, divine-name capitalization, and leaked editorial reference markup. Generated Bible.com modules now project their verified raw OSIS verse bodies directly, preserving text while GTK renders explicit styling and separate headings. This is restricted to the namespaced modules produced by this installer; existing SWORD resources retain their previous behavior. A chapter is parsed once for its body; no complete corpus or repeating background computation is retained.

Translation notes are a separate read-only study tool; personal notes remain separate. Only the visible chapter is read, and selecting another verse in the same chapter reuses the view. Opening the previously selected tool after changing chapters while hidden also refreshes correctly. Hidden tools do no source reading and have no timer. Actual book introductions open from passage navigation without changing the reading passage or inventing personal-note references. Unindexed poetry headings, empty note-bearing verses, Selah, inline ordinals and table column labels have dedicated coverage.

## Verification evidence and limits

Local source-environment checks include:

- The complete native GTK suite passes: **358 tests**. Catalogue auto-loading is mocked only in unrelated UI fixtures, preventing real network timing from leaking into local-file cancellation tests; production catalogue loading remains enabled.

- Independent DOM versus generated OSIS, native raw readback and application Reader output for **8,323 chapters, 132 introductions, 217,907 source units and 28,324 translation notes**, across all seven editions. Comparison normalizes NFC and semantic whitespace only; it does not fold case, remove punctuation or change words.
- All **8,455 individual OSIS documents** validate against OSIS 2.1.1.
- All seven editions reopen in GTK, with real parallel content, translation notes and small-window checks. A retained disposable profile preserves its seven existing resources, actual personal-note database and reading preferences byte-for-byte while checking later editions. These tests do not reset a client profile.
- Semeur's streaming conversion/readback previously took about **11.3 s**, with a **46,292 KiB** child-process peak locally. Other local native conversion/readback observations range approximately **7–37 s**. These are tooling figures, not client startup RAM or installed-package throughput; final packaged receipts record their own results.

Earlier exact source commits `f3e7399`, `7d87c23` and `3c2aea4` passed their ordinary and installed Flatpak checks. In particular [CI 40413750585](https://github.com/icfmp/Bible/actions/runs/40413750585) and [installed proof 40413750652](https://github.com/icfmp/Bible/actions/runs/40413750652) are green for the Semeur installer at `3c2aea4`. They do **not** validate the later expanded seven-edition implementation.

The final workflow downloads the six additional editions through the actual installed application's downloader, validates complete source/native/application fidelity, and then launches each edition with Flatpak `--unshare=network`. It preserves a shared test profile and uploads only count/hash receipts. Source files and modules stay private in runner temporary storage. Final source/installed checks, review, signed-alpha deployment and retained-data update verification remain required before delivery.

GTK source tests use the available local runtime; installed checks use the packaged GTK/SWORD/Python stack. Xvfb/software-rendering CI is not a manual test on the client's GNOME desktop. Linux/Flatpak process cancellation is tested; Windows/macOS behavior is not claimed. Numbered release #87 stays paused, and #26 remains open for client validation.

## Reproducibility

`tools/versification/original.py --check` reproduces the compact Original table from checksum-pinned MIT SIL files and existing JSword data. `tools/versification/youversion.py` checks the two reference-only publisher indexes against the native patch. Sources, original licenses and provenance are included; no Bible text is present in those tables.

The source adapter and semantic writer are in `bible/youversion_source.py` and `bible/youversion_osis.py`; earlier research imports remain compatibility wrappers. `tools/research/check_yves_fidelity.py` is an independent development-only DOM oracle. Its optional lxml dependency is not an application dependency.
