# NFC source sections and verse fragments — issue 153

Published delivery: [Bible 0.1.0-alpha.23](https://github.com/icfmp/Bible/releases/tag/0.1.0-alpha.23). The signed channel, actual retained-profile upgrade and numbered prerelease are verified. Issue 153 remains open for client acceptance.

## Implementation

PR [178](https://github.com/icfmp/Bible/pull/178) is merged as application source
`7c76aaaa14ee605d71c45ec3e634ed14c787678c`. Its complete tree matches tested candidate
`a24daa9ee7d4647b3efac30b34104182b0edb162`.

The actual NFC index declares both `SIR.1` and `SIR.1_1` canonical, with printed
label 1 and different content. Its heading does not justify reclassifying the
translator preface as an introduction. `SIR.INTRO1` remains separately
noncanonical. Sirach 43 presents `17a, 16, 17b`; Sirach 44 has a shared `22+23`
unit followed by the continuation of 23.

A bounded reference-only adapter preserves those source identities and assigns
private native storage coordinates. It stores no Scripture and is about 6 KiB
for the demonstrated edition. Native coordinates do not become annotation or
session IDs. Ordinary chapters retain their existing storage path. Complete
compiler inventory, text, note, heading and semantic-role checks remain required.
No edition-ID or chapter-specific bypass is used.

Reading, exact search, all copy/excerpt routes, highlights, note markers and
ordinary/immersive anchors consume the source identities and ordered units.
Logical verse actions retain their requested verse; explicit shared-text
selection retains its members. Notes use actual indexed bounds even when verse
1 is absent. Existing numeric references and SQLite schema remain unchanged.
Reference metadata is retained when a resource is removed. Older applications
can reject backups containing the new section IDs; private slots are never
substituted for those IDs.

No NFC/NBS verse mapping is claimed. Comparison remains available through
independent panes when a verified mapping or a shared-row layout preserving
source order is unavailable. NBS has no Sirach: the test establishes Genesis 11
in both resources, then retains the independent NBS passage when NFC opens
Sirach 43.

## Installed Flatpak verification

| Check | Previous alpha 22 | Final candidate |
| --- | --- | --- |
| Application source | `583b734a3f65385e7aedc469729753bbd5676e19` | `a24daa9ee7d4647b3efac30b34104182b0edb162` |
| Ordinary package CI | [41979075066](https://github.com/icfmp/Bible/actions/runs/41979075066) | [42004507539](https://github.com/icfmp/Bible/actions/runs/42004507539) |
| Specific installed check | [41997610947](https://github.com/icfmp/Bible/actions/runs/41997610947) | [42028018231](https://github.com/icfmp/Bible/actions/runs/42028018231) |
| Actual Library NBS action | installed, 33.397 s | installed, 38.365 s |
| Actual Library NFC action | refuses overlapping `SIR.1` / `SIR.1_1`, 8.511 s | complete verified installation, 21.180 s |
| Runtime | GTK 4.20.4, OpenGL, packaged `/app` code | GTK 4.20.4, OpenGL, packaged `/app` code |

The timings include network, conversion and verification on separate disposable
cloud runners. A failed conversion duration is not a performance baseline for a
successful installation.

The final candidate's 15 native reference/fragment tests pass without skips.
They cover actual SWORD compilation, distinct source sections, public/native
keys, partial aliases, search, clipboard, exact anchors, highlights, note markers,
comparison order, annotation backup/restore and note-panel behavior. The full
local suite passes 446 tests with 2 skipped; distro-SWORD CI has additional skips,
which do not replace these packaged native checks.

The real installed Library downloads NBS 104 and NFC 2367 independently. The
complete NFC compiler checks 1,424 physical files represented by 1,416 logical
chapter/introduction documents. An independent DOM oracle verifies 1,340
canonical chapters, 76 introductions, 35,277 ordered units, 9,417
canonical-chapter notes with locators and 4,021 canonical-chapter headings.
Introduction editorial content is also covered by the complete compiler check.
A separate reader/body audit finds no mismatch across 4,160,340 non-whitespace
characters and checks 11,606 exact positions in four sensitive sections.

NFC archive SHA256:
`ba907f83af7826abf134da92dba4e8cbbc5e12f4c2a45ad511270ce04c072fd0`.
Native reference-index SHA256:
`d1c85e6e4e734bc1a2c90d8931fd64ecdffc9bda3448b403f65f4d13e944bc4a`.
Source-address metadata SHA256:
`cc3d878a686a61b797db593aa369be5f1b3b640333a7580c52021fe7a13a3c81`.

The same installed profile is restarted with network removed. It retains all
three resources/30 module files and the sentinel note. Beginning, middle, end,
the two source sections, Sirach 43/44, source notes, independent comparison and
whole-verse clipboard are checked in both themes, including 360-pixel windows.
Reading preferences stay unchanged during both installations; theme changes are
intentional capture actions. Installed UI SHA256 is
`09bbca63a9310b370ef1d08a79dc44c5a5a8e27cd68569b3d9d428414adf20d6`.

Candidate proof artifact 13414638576 ZIP SHA256:
`c7cfc9cdae9d361b8b5eae4e12c23bdbd81b3aa89c3a2fbcd11df4bdf0199339`.
Baseline proof artifact 13401351321 ZIP SHA256:
`eed7afa21025b63f7a48e5376646e4c0198d66237ee6b4609d42c910753aa806`.

## Actual signed delivery

[Main CI](https://github.com/icfmp/Bible/actions/runs/42029199570),
[automatic signed publication](https://github.com/icfmp/Bible/actions/runs/42032893926)
and [actual retained-profile upgrade](https://github.com/icfmp/Bible/actions/runs/42029279575)
all succeed. Publication revision is `42032893926-1`.

The installed alpha moves from
`3d75ababcea529b637a43e6cb3c6d478e2ee807eeccb5fb84bfd7b0892612a86`
to `8dc631d055bf9a77192b3e6a6ef37e526381a62a5fd10f1703f2152a110ff0e8`.
Origin `bible-alpha`, ref `app/io.github.icfmp.Bible/x86_64/alpha`, and signing
fingerprint `47A17230403EA4953745E6E020EB9FFCCECAFD8F` remain unchanged.
The same retained profile preserves seven real resources/65 module files, four
study datasets, one sentinel note, highlights and reading preferences. No profile
reset is used. The publisher's separate public-client check verifies commit and
summary signatures, startup, an actual old-to-new update and three data sentinels.
Fresh public provenance matches the source and publication receipts.

Source archive SHA256 is
`c6a1e9f3bec569f8938aa3542d07c293fa1d2a7277a80e9bf69d5edba7aaec68`;
the authenticated release-asset metadata matches it. CI bundle SHA256 is
`04f1929ca7a8569fc5cbca3c708c95c1f2ee2be83256929b7545a3d809b684f5`.
Public verification artifact 13417361231 ZIP SHA256 is
`9926c670908fd3fd9facbf8333cc3f87920963f9f12f414e8b75aac78cd581a3`;
retained-upgrade artifact 13417766000 ZIP SHA256 is
`67241c7253d0177995d7c074c24b83aee6b0ae91c6a16159b6eebfdcb920cf8f`.
Both are downloaded and their JSON receipts inspected.

Short retained-profile scrolling checks use FreSegond1910/Psalm 119, the same
settings/profile, Vulkan/software rendering, scale 2 and four logical CPUs:

| Combined reading | Alpha 22 | Alpha 23 |
| --- | --- | --- |
| RSS at startup / final idle | 438.6 / 457.9 MiB | 419.6 / 447.3 MiB |
| CPU during scrolling, percent of one core | 116.6–121.2% | 116.2–118.5% |
| First scroll / first paint | 2.500 / 4.259 ms | 2.720 / 4.548 ms |
| Maximum sampled main-loop gap | 118.9 ms | 88.5 ms |
| Adjustments later than 500 ms after stopping | 0 | 0 |

Four combined scrollbar cycles and two wheel cycles each in simple, comparison
and study modes pass after update. The hidden menu releases its backdrop and
has no placement tick. The CPU figures still represent about one core during
scrolling; these short cloud measurements are not a performance improvement
claim or proof of long-session memory stability on the client's computer.

## Captures and limits

Originals are supplied privately in
`Bible-NFC-captures-privees-20261105.zip`, SHA256
`e7478136ae884a59bce998bac637bf6c17f498f5cfd733a48a50eadd320f3236`.
The archive contains 22 unedited PNGs: four baseline and eighteen after. The
four after-Library images show actual online installation; the fourteen reading
images come from the network-unshared second pass, which replaces the same-name
first-pass images. Three JSON receipts and a hash manifest explain their origin.
No original media, private profile or translation corpus is committed publicly.

The original client recording for issue 168 was not attached or examined.
Linux Flatpak/Xvfb verification does not establish acceptance on the client's
GNOME desktop, Windows or macOS, or long-session hardware-specific performance.
Only the existing provider access paths and explicit local source-condition
acknowledgement are used. Bible does not submit a provider agreement or imply
provider approval.

Keep issue 153 OPEN for client validation. Project 5 status writes remain
unavailable: the integration returns `Resource not accessible by integration`.
The required manual status is **In validation**: the signed update and numbered prerelease are now verified and published. Only the client moves Done.
