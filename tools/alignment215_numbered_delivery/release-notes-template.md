This alpha restores comparison and commentary following for verified books in installed French YouVersion editions, including the PDV2017, S21 and NFC cases reported in #215. It keeps source identities, text, annotations, preferences and installed resource files unchanged.

The shared capability gate previously rejected a whole edition when an unrelated book differed from the declared convention or contained private source-address transformations. It now confines the capability to compatible, unchanged whole books, still requiring the explicit supported declaration and verified source/index metadata. Native index inspection also disables automatic normalization so NFC's legitimate empty chapter slots retain their real zero bounds. Existing SWORD and pinned mapping tables still handle actual numbering differences; no edition-ID/title/sample-passage branches or inferred identities were added.

Stronger viewport checks also found that an obsolete GTK edge rebound could overwrite a correct new commentary position or a gesture in another parallel pane. Shared motion and handoff code now stops that old native movement and synchronously restores the original kinetic setting. It adds no scrolling engine and does not disable native scrolling or change preferences.

Delivered through [PR #234](https://github.com/icfmp/Bible/pull/234), source `{{SOURCE}}`.

Verification:

- Reproduced all three failures on the unchanged, installed signed alpha.25, with LSG/MHC as a working control. Candidate and final signed checks reuse retained profiles and actual downloaded resources.
- Nine Bibles across CrossWire and YouVersion: LSG 1910, KJV, Darby, Semeur, YouVersion LSG, NBS, PDV2017, S21 and NFC. Each complete matrix checks 72 ordered pairs and 294 independently expected reference vectors, native chapter openings, source switching, real wheel input in both panels, four keyboard-activated chooser changes and MHC/Wesley switching. Passages include Genesis 1/11, John 3, Psalm numbering and the Genesis 31:55/32:1 boundary shift. Superscription verse-part ranges are preserved.
- An additional independent installed matrix compares rendered verse bodies with independently opened readers for the requested resources, detecting stale text even when printed labels match. Repeated Bible ↔ MHC gestures are checked separately with LSG, KJV and all three reported editions, in French and English. The actual target range must intersect the viewport; current-entry state alone is insufficient. Nine transfers at scroll boundaries also check that an old rebound cannot erase the new gesture. A native input regression preserves both initial kinetic settings.
- The same French/English physical following and nine-handoff matrix also passes with [native GTK animations explicitly enabled](https://github.com/icfmp/Bible/actions/runs/{{ANIMATIONS_RUN}}); the exact candidate Flatpak is reused without rebuilding the application. The English process runs without network access, with data/preferences/resource hashes preserved.
- Full main CI [{{CI}}](https://github.com/icfmp/Bible/actions/runs/{{CI}}); [signed deployment](https://github.com/icfmp/Bible/actions/runs/{{PUBLICATION}}); [actual retained signed update and offline checks](https://github.com/icfmp/Bible/actions/runs/{{SIGNED_RUN}}). Linked notes, unavailable original references, exact reading preferences, highlights and resource/reference-index hashes are preserved. Canonical reference consumers are checked in both directions for all nine Bibles.

Download **Bible-alpha26-GTK-evidence.zip**, extract it and open **overview.html** for original native light/dark French/English captures, before/after results, test receipts, source/build provenance and checksums. Captures identify the actual tested source and the selected translations; no complete Bible modules, private customer profile or annotation database is included.

Material limits:

- A mismatched or transformed book remains unverified as a whole until documented mapping evidence exists. In the measured editions this includes S21 Numbers, PDV Zechariah and PDV/NFC Acts, as well as additional/sectioned deuterocanonical material without a verified map. Available-chapter independent reading remains supported; no equivalence or fallback passage is invented. This release does not claim universal alignment of every verse in every edition.
- Checks use Linux x86_64, GTK 4.20.4, composited X11 and software OpenGL. They do not certify the client's GNOME/Wayland or hardware GPU, or other operating systems. These are functional checks, not hardware-independent performance benchmarks.
- The existing annotation storage formats and their alpha.25 limitations are unchanged. No resource reinstallation or profile reset is required for already verified supported indexes. The broader #126 and #137 audit work is outside this correction.

Install/update through the existing signed channel:

```sh
flatpak install --user https://icfmp.github.io/Bible/alpha/Bible.flatpakref
flatpak update --user io.github.icfmp.Bible//alpha
```

Source `{{SOURCE}}`; main CI `{{CI}}`; signed packaging revision `{{REVISION}}`; OSTree `{{OSTREE}}`; remote `bible-alpha`; ref `app/io.github.icfmp.Bible/x86_64/alpha`; signing fingerprint `47A17230403EA4953745E6E020EB9FFCCECAFD8F`. The numbered tag records this verified source; the continuous signed channel may later advance.

Issue #215 remains open for client acceptance. Project integration access is refused (`Resource not accessible by integration`); after this verified publication its manual status is **In validation**. No automatic issue closure is performed.
