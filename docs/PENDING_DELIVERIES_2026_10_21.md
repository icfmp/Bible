# Reviewed pending deliveries — verified public alpha

The client authorized completion of the outstanding deliveries. The PRs were
reviewed and merged sequentially: **#41** page (`8029cf3`), **#38** eBible
(`3e1ec0d`), **#40** personal highlights (`56c0a6c`), **#39** continuous-book
pagination (`1e7613d`). The final focused integration fix is **`6560dc4`**.
No new OpenBible features or general code review were added. #26 remains excluded.

## Actual available package

- Source: `6560dc4a765a9c8a26388c7df1e9de4679e0c376`.
- Main CI **39673122687** and signed publication **39674239853**: green.
- Public revision: **39674239853-2**.
- Installed/public Flatpak commit: `f36e063db7004fc6a20aa8051234e2f488f8a09c5b6ce3e399d779c1e595452a`.
- Existing `bible-alpha`, `app/io.github.icfmp.Bible/x86_64/alpha` and public
  installation/update URLs are preserved. Signing fingerprint remains
  `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.
- The downloaded CI bundle SHA-256 matches actual public provenance:
  `a7edd82b97d921464bd474bd48f3538bcec57ad9ea516a4f728f5acf7c7b8b72`.
- Actual public HTTPS installation, GTK startup and first-to-second signed
  update pass, including commit/summary GPG verification and test-data retention.
  The existing system alpha client also updated from the preceding public build
  to this exact commit. Its real test-profile notes SQLite, session, preferences,
  personal highlights and highlight backup hashes were unchanged by the update.

Public page: **https://icfmp.github.io/Bible/**. Approved English presentation,
authentic signed-alpha screenshot (its capture version is explicitly labeled),
local assets, responsive desktop/mobile/dark layouts and keyboard access are
published. All installation/update/key/source/license links return successfully;
actual source-archive digest and dynamic package provenance match. Descriptors,
historical repository objects/archives, channel, Pages configuration and keys
are preserved. Public browser captures: [desktop](captures/website-37-public-desktop.png),
[mobile](captures/website-37-public-mobile.png), [dark](captures/website-37-public-dark.png).

## Integration corrections and actual tests

The first combined package exposed a real GTK 4.20.4 validation abort in the
final palette probe. Redundant personal painting during a primary-view adjustment
notification invalidated GTK layout while comparison rebuilt. This was diagnosed
with faulthandler, GDB and actual callback stacks; the delivered fix skips unchanged
paint and tag-property updates, while actual text replacement still repaints.
It does not disable highlights or synchronization. A stale immersive navigation
constructor is also corrected. See [native diagnosis](HIGHLIGHT_LAYOUT_INTEGRATION.md).

- **159** full local and CI tests; **70** additional French UI CI tests, native
  pointer/keyboard and real-resource offline CI checks pass.
- Final installed **/app** code, without source overlay: **28** affected unit tests
  plus the native click/note test on its own external Xvfb display pass. The latter
  is isolated externally because `xvfb-run` is deliberately not shipped inside
  Flatpak. An earlier harness invocation failed for that missing test utility;
  rerunning the actual case on its dedicated display passes.
- **16 actual pixel states** pass across every palette, emulated high contrast,
  open/closed study drawer, resizing and unavailable/restored comparison. Equal
  columns, canonical anchor and selection survive. [Actual GTK paper palette](captures/comparison-36-integrated-paper.png).
- Real offline Genesis: **211 pages**, **42** chapter headings continue within a
  page; exact document partition, ordinary-space Copy for generated marker gaps,
  unsplit marker/first-word spans and canonical reflow anchor pass. Preparation
  stabilized in **1.536 s**, 74 GTK heartbeat ticks, largest gap 0.424 s.
  [Actual installed-alpha GTK capture](captures/continuous-book-24-public.png).
- Native selection/partial Copy, frozen second-Bible note context/versification,
  mapped Compare and immersive actions/closing pass. Three personal colors,
  hide/show, unchanged scripture, backup/merge and the find list pass.
- The actual temporary MHC cue coexists with personal marks, remains when personal
  paint is hidden and follows real mapped references, including paginated reading.
  [Actual overlap capture](captures/highlights-27-public-overlap.png).
- Real MHC progressive loading stays bounded to 20 sections; native reverse/wheel,
  keyboard and long scrollbar drag, both synchronization directions, tab/source/
  hide cancellation and actual **Rev.22.20–22.21** end pass. Notes/session reopen
  pass. The client's previously accepted #51/#36 remain closed.

These are automated native GTK/Xvfb/browser checks, not client manual GNOME,
Wayland, physical trackpad, file-portal or screen-reader acceptance.

## eBible and personal-highlight clarification

eBible's official stable HTTPS source is integrated and appears in the source
registry/catalogue. Real **JND 2.17** was downloaded under the existing conditions
checks, installed and read offline; John 3:16 equals direct SWORD output (SHA-256
`0d5882a7e879e2693e30609ab17916fca88625d9e5b8362892e3cb534db2c2f1`).
Its catalogue advertises 2.7; this stale version is disclosed, not rewritten.
Current F10, FOB, FRANCL and SBL catalogue/package attribution or conditions
metadata differ and the unchanged guard refuses them. No condition check or
provider restriction is bypassed. [Current audit](evidence/ebible-34-current-audit.json).

The previously installed public `8d3a183` had the temporary commentary cue but
no personal-highlight module. The client's positive visual observation was not
remotely reinterpreted as a known local build. This delivered alpha now contains
reviewed **persistent personal marks** in `highlights.json`, separately from the
temporary cue. Application windows share one profile store; atomic persistence,
corrupt/future-file protection and explicit backup/merge remain in place.

## Remaining client acceptance

Keep **#34, #27 and #24 open** for GNOME acceptance. #37's approved presentation
and public deployment/install/update criteria are satisfied. General remaining
manual accessibility/Wayland acceptance stays in #52; no manual validation is
claimed here. Test the newly integrated eBible download/offline reopen, personal
highlight persistence/visibility/backup portal and continuous chapters/book
boundaries/reflow/Copy. #28 retains manual Do Not Disturb guidance.

Machine-readable proof: [verification](evidence/alpha-6560dc4-verification.json),
[provenance](evidence/alpha-6560dc4-provenance.json),
[public links](evidence/alpha-6560dc4-public-links.json),
[signed update](evidence/alpha-6560dc4-channel-update.json),
[actual profile preservation](evidence/alpha-6560dc4-profile-preserved.json).
Per-probe native logs are saved alongside these files with the same source prefix.
