# Offline continuation — 22 October 2026

Base commit: **884591cd194bd7c07e3534a9b652c154a578dd34**. Work is isolated
on `feat/24-offline-preparation` for the pagination/worker architecture review.
Implementation and source-test evidence are committed locally in **fa2bfa0**.
The client explicitly authorized offline implementation and local commits;
remote CI, push and publication are deferred. Existing integrations are retained,
not rebuilt or merged again. No user-data schema, resource installation, signing
key, channel configuration, release metadata or public website is changed.

## Recovered evidence and execution limits

`docs/STABILIZATION_NIGHT_56_57.md` and its original candidate logs are recovered.
They record 161 local tests and seven resource installations/offline checks on
source-candidate code. `tools/check_resource_installation.py` now expects at least
nine resources, but that assertion is not an executed nine-installation result.
No saved eight-configuration comparison result was located. No verification note
is attached locally to 884591c. The previously announced green CI, nine
installations, eight comparisons and signed publication for 884591c therefore
remain **unverified**, rather than being inferred from source or old logs.

The latest *saved* signed-publication proof is still
`evidence/alpha-6560dc4-provenance.json`: source 6560dc4, revision 39674239853-2,
fingerprint `47A17230403EA4953745E6E020EB9FFCCECAFD8F`. This is historical evidence,
not a fresh check of the remote channel. No new alpha is announced.

The executor can run commands and native Pango/PangoCairo. It lacks GTK 4,
libadwaita, SWORD Python bindings, Babel in `/usr/bin/python3`, Xvfb, Flatpak and
flatpak-builder. No `mods.d/*.conf` was recovered in accessible `/workspace` or
`/tmp`; the old `/tmp/bible-night-*` profiles, build tree and builder cache are
absent there. The historical `bible-night` container could not be inspected:
the Docker socket call was denied, then the explicitly permitted diagnostic
did not complete before interruption. No further Docker or network attempt is
made. This does not establish that the old container or client resources were
deleted. Inventory: `evidence/offline-2026-10-22-readiness.json`.

## #24 implemented locally

- The worker retains one private SWORD reader and one private Pango font map,
  separate from GTK's visible reader/context. Completed book documents survive
  geometry/font/spacing changes. Number visibility invalidates the document;
  typography, geometry and canonical partition invalidate the page plan. Both
  caches are bounded to three entries and pruned to the current/adjacent books.
  Nothing is persisted to the user's profile.
- Superseding work signals cooperative cancellation, including active work.
  Checkpoints cover index discovery, verse extraction, structured content,
  chapter composition, style construction and shaped-line traversal. Queued
  work is cancelled and obsolete prefetch is pruned. Cancellation is not a
  resource error, and obsolete results cannot replace the current request.
  Closing cancels and joins the worker before releasing backing files.
  An individual native SWORD/Pango call cannot be interrupted mid-call; there
  is no claim of a hard cancellation-latency bound.
- UTF-8 style offsets are computed from successive slices once instead of
  repeatedly encoding entire book prefixes. Verse-number rise is measured once
  per layout. GTK allocations settle for 80 ms before scheduling page work,
  limiting repeated preparation during resize or Aa changes.
- Chapter and source headings, consecutive headings and intervening blank lines
  stay with the first shaped body line whenever the combined block fits on a
  page. Verse-marker/first-word metadata also protects page boundaries where
  the group fits. Oversized titles/groups make progress without empty-page
  loops or dropped text. Canonical body anchors, exact display/copy partitions
  and original source text are retained. An anchor inside a heading gap may
  move the partition back to that heading to prevent an orphan title.
- Existing pointer-versus-keyboard focus handling and the shared exit/Aa
  controls are retained. Empty/preparing pages now discard stale study ranges.
  Actual GTK allocation, click-frame, popover and exit checks remain pending
  in the constructed/installed package; no cloud desktop acceptance is claimed.

Actual source-only validation: **34 tests pass, 5 GTK/display tests skip**.
This includes 13 new headless tests using **real native Pango** with explicitly
synthetic Unicode text, 24 font/height/number combinations, cache reuse,
supersession, cancellation, worker shutdown, and existing notes/session/
highlight preservation checks. Command and raw output:
`evidence/offline-24-tests.txt`. Compilation and `git diff --check` pass.

A separate dependency probe ran 40 existing tests: 31 passed and nine errored
because SWORD (eight) or Babel (one) is unavailable. These errors are not test
passes or product regressions established with the required runtime. Details:
`evidence/offline-blocked-tests.txt`. The full suite has not been validated.

One native Pango timing sample on 1,500 synthetic verses (321,054 characters)
measured 2.758 s on 884591c versus 1.436 s on this candidate. The baseline's
SPACING import alone was redirected to the identical GTK-independent constants
to load it without GTK. Both partitions reconstruct the exact text; heading
grouping changes the count from 506 to 507 pages. This is one source/Pango sample,
not installed-resource preparation, GTK heartbeat or desktop responsiveness
evidence. Raw measurement: `evidence/offline-24-pango-timing.json`.

## #57 — local inspection; exact outstanding inputs

Inspected local `bible/reference_resolution.py`, `bible/sword_provider.py`,
`bible/comparison_sync.py`, `tests/test_reference_resolution.py`, the pinned
SWORD manifest and the saved AndBible installation investigation. The runtime
uses destination `VerseKey.positionFrom(source)`, preserves the target system,
and explicitly rejects differing systems outside the shipped-mapping allowlist.
`Luther` is not added to that list; no module/provider-name exception or
same-number fallback is introduced.

The saved investigation states SWORD 1.9 registers Luther without a mapping;
the upstream C++ source itself is absent here and was not re-inspected offline.
The package manifest pins `sword_1.9.0+dfsg.orig.tar.xz`, SHA-256
`a1687b8ade230d9b30a9991b76c12920daac865f1c25bd4be3cb897b90f007d9`.
Only its URL/hash and prior conclusions are available, not the archive.

The saved JSword pin is **6ebd10a005fa7761e611c048ececea1430e22546**. The cited
`src/main/java/org/crosswire/jsword/book/install/sword/AbstractSwordInstaller.java`
was examined for ZIP installation, not reference alignment. No AndBible/JSword
checkout, Java mapping implementation, mapping data, registration files or
mapping tests are tracked or recovered in this executor. The AndBible pin
7e73c11508f32e4f531d531f6d5b110dd2a1f204 in the provider review documents repository
discovery; it must not be presented as a verified alignment implementation.

Required before implementing #57:

1. Recover the exact AndBible superproject revision and JSword gitlink used by
   the reported working comparison, with the source tree for the JSword pin.
2. Locate and inspect its versification registry, reference/range conversion
   implementation and *all* mapping tables/transitive routes covering Luther
   and the other installed systems. Record actual file paths, revisions and
   hashes after obtaining them; filenames are not guessed here.
3. Recover corresponding tests/data for forward and reverse conversion,
   Psalms/superscriptions, chapter shifts, split/merged/omitted verses, ranges
   and canon differences. Verify which cases are exact, unsupported or ambiguous.
4. Recover the pinned SWORD C++ archive to inspect native fallback and mapping
   registration directly; confirm how an explicit shared mapping can integrate
   without silently invoking identity fallback.
5. Recover representative installed modules and original configuration/metadata,
   including actual Luther resources beyond a Darby-only case and mapped-system
   controls. Verify text and both scroll directions offline, then verify in the
   actual package. Inspect applicable upstream licenses before copying any data.

Until these inputs exist, #57 remains pending. No approximate alignment is made.

## #53–56 and package verification prepared, not executed

The existing native sidebar surface (#53), single shared Header Bar/immersive
Aa (#54), safe-margin navigation (#55) and generated-date-only notice rule (#56)
are retained. Resource/conditions code and signed-distribution files are unchanged.
Do not repeat the previously saved seven source installations as new evidence.

New `tools/check_book_preparation.py` reads existing resources only: direct SWORD
word fidelity, exact display/copy partitions, heading grouping, document/plan
reuse, canonical reflow and superseded requests. Default real-resource
reproducers are Genesis, Mark 7→8 and Luke 13→14 in FreSegond1910. It never opens
a window, downloads, installs, resets preferences or writes sessions. Its report
states source versus installed-package code and whether GUI validation occurred.
`--require-packaged` checks the paths of every relevant imported application
class. The existing GTK continuous-book checker now also has this guard.

Once a genuine candidate Flatpak and a disposable test profile with the saved
resources are recovered, run outside the checkout (for example from `/tmp`),
with `/app/lib/bible-python` **before** the read-only tools/tests checkout on
PYTHONPATH. Use an isolated candidate installation/ref, never replace the
existing signed `//alpha` to run these checks. Record the source commit,
Flatpak ref/commit and bundle SHA-256 before testing. An overlay in a GNOME
runtime is source-candidate evidence, not installed-package evidence.

1. Build offline only if GNOME 49 SDK/runtime, source archives and builder cache
   are present. They are absent here. Distinguish builder-tree smoke tests from
   tests of an installed bundle. Do not regenerate a key or alter channel URLs.
2. In the installed candidate, disable networking and run
   `tools.check_book_preparation TEST_PROFILE --require-packaged --output OUTPUT`.
   Mount the existing resource profile read-only for this read-only checker.
3. With a separate writable **disposable** copy of that profile, run
   `tools.check_continuous_books TEST_PROFILE --require-packaged` and
   `tools.check_stabilized_ui TEST_PROFILE CAPTURE_PREFIX --require-packaged`
   under GTK/Xvfb. Check native sidebar pixels, shared Aa, safe margins,
   pointer frame, F10, Escape/popover precedence and exit during preparation.
4. Run the affected full native suites (book preparation/pagination/immersion,
   UI/provider UI/library, reference resolution, notes/session/highlights),
   including `tools.check_passage_actions` for exact native selection/copy.
   Record all application import paths under `/app/lib/bible-python`.
5. Run `tools.check_resource_installation TEST_PROFILE --offline
   --require-packaged` only if the saved `resource-check.json` and corresponding
   installed modules are recovered. This proves reopening/fidelity, not fresh
   installation. Fresh nine-resource UI installation and conditions/error
   regressions remain separate package gates once their inputs are available.
6. Recover the actual eight-comparison evidence or define and execute the matrix
   explicitly. Unsupported Luther comparisons must still show the honest
   limitation until #57 has verified tables; do not count them as aligned.
7. Resume remote CI/push/publication only after connectivity returns. Require
   matching public provenance, unchanged signing fingerprint, successful signed
   update and profile-data hashes before announcing availability.

No package has been built or installed during this offline continuation.
Client GNOME/Wayland/accessibility acceptance remains separate and open.
