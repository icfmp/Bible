# eBible source addition — review required

This branch adds one stable source. It does not enable beta repositories or
change the signed distribution channel. The registry addition requires review
under AGENTS.md and is not yet in the published alpha.

## Verified source

AndBible's official `app/src/main/res/raw/repositories.txt` at commit
`7e73c11508f32e4f531d531f6d5b110dd2a1f204` lists HTTPS host `ebible.org`,
catalogue directory `/sword`, package directory `/sword/zip`.
The normal Bible HTTP client retrieves `/sword/mods.d.tar.gz`. Resource package
names come from that catalogue, not UI abbreviations. A guessed `F10.zip`
returned 404; this was an identity mistake, not an unavailable French Bible.

| Client label | Actual eBible module | Language | Versification | Stated terms |
| --- | --- | --- | --- | --- |
| F10 | fraLSG1910eb | fr | NRSV | Public Domain |
| FOB | fraFOB1744eb | fr | NRSV | Public Domain |
| FRANCL | francl2022eb | fr | Catholic2 | Creative Commons: by-sa |
| JND | frajnd2024eb | fr | Luther | Public Domain |
| SBL | frasbl2022eb | fr | NRSVA | Public Domain |

These five exact identities were absent from the four previously enabled
catalogues because the eBible source was absent. Similar translations in other
sources are not asserted to be identical editions. Their descriptions and full
source terms remain visible; no license whitelist filters them out. Unlocked
supported drivers are installable; encrypted/unsupported content retains its
existing honest limitation. Fordata `frd2018eb` (`frd`) is not French and is
never merged into the `fr` filter. Other original codes/variants remain intact.

New IDs use `ebible~<module>`; historical CrossWire IDs and installed attribution
remain unchanged. The per-provider cache and progressive refresh introduced in
20361ce also apply to this source. A failed source cannot replace another
source's cache or remove installed modules.

## Sources deliberately not enabled

CrossWire Beta and AndBible Beta are testing repositories. IBT, Wycliffe and
Lockman require separate verification of their endpoints, metadata, packages
and any access restrictions; they are not enabled merely because AndBible
lists them. No access control is bypassed. The withdrawn Xiphos catalogue audit
has not been restarted. Bible.com/YouVersion (#26) remains excluded.

## Reproduction

`python3 -m tools.check_ebible <temporary-profile>` checks the five catalogue
identities and installs `ebible~frajnd2024eb`. `--offline` reopens it without any
network and checks John 3:16 against direct SWORD output, including attribution
and a text hash. The checker does not commit downloaded scripture.

Review/publication and manual GNOME acceptance are separate from these source
and offline-reader checks. Do not announce eBible as available in the public
alpha until this source-policy PR is reviewed, merged and published.

The F10 catalogue currently describes version 90.0 while the actual package
contains 99.0 and a different About notice. Installation rejects that mismatch
with `Resource conditions changed. Reload the catalogue before downloading.`
The guard is deliberately unchanged. This source inconsistency remains a
limitation; listing a source is not a claim that every package is installable.

Validation on this branch: 133 local tests passed, including source collisions,
partial failures, cache retention and GTK installed-state checks. JND package
2.17 installed with unchanged conditions checks and reopened offline at John
3:16, exactly matching direct SWORD text (SHA-256
`0d5882a7e879e2693e30609ab17916fca88625d9e5b8362892e3cb534db2c2f1`).
Catalogue and reader screenshots are in `docs/captures/ebible-34-*-fr.png`.
These are candidate-source Xvfb checks; a packaged candidate and manual GNOME
validation are separate, still outstanding checks.


## Final source review and integration

The client authorized completing the source review and integration. Current main,
including #51/#36 corrections and the approved website, is merged. The current
official AndBible repository file (blob `54e501d47f071e4f0991b3da8b6522bf3ec82dc7`)
still names HTTPS ebible.org /sword and /sword/zip. Only this stable source is
added; identity/collision, language, cache and archive/conditions guards are kept.
No beta, restricted source or Bible.com access is introduced.

The five current catalogue/package pairs were inspected through the normal
bounded HTTPS downloader. [Exact audit](evidence/ebible-34-current-audit.json):

| Resource | Catalogue/package version | Current guarded metadata |
| --- | --- | --- |
| F10 | 90.0 / 99.0 | About differs: installation refused |
| FOB | 61.0 / 71.0 | About differs: installation refused |
| FRANCL | 498.0 / 1234.0 | About and conditions differ: installation refused |
| JND | 2.7 / 2.17 | Guarded terms/type match: installs as actual version 2.17 |
| SBL | 112.0 / 170.0 | About differs: installation refused |

The four refused installations return the unchanged `Resource conditions changed`
guard. JND's stale catalogue version is disclosed too; the installer already
compares actual source/type/versification and complete guarded legal fields,
not a separate version equality rule. No guard was weakened for any resource.
This audit covers those five requested examples, not every eBible module.

147 integrated local tests pass. A fresh real JND download/install and a separate
offline GTK reopen pass; John 3:16 still matches direct SWORD output and the
previous SHA-256. Updated French catalogue/reader captures are real GTK/Xvfb.
The source-policy review is complete for this addition. Public availability and
manual GNOME acceptance are recorded separately after final publication.
