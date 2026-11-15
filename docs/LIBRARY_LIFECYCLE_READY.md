# Source-safe Library lifecycle

Related to #253, #233, #255 and #256. Only the Bible application repository is
changed. The application consumes published resources; no dataset, resource
content, publisher pipeline or external repository is created or modified.

## Separate issue scopes

- #253: optional existing Bible Resources JSON plus standard SWORD metadata in
  the existing Library categories, language/source filters and details. Explicit
  first installation verifies exact advertised size/SHA-256, edition identity,
  driver, version, versification, legal metadata and native readability. Source
  edition/profile approval metadata is attributed to the publisher; draft profile
  prose is not turned into application claims. Automatic source defaults remain.
- #233: manual installed-versus-curated checking and explicit same-edition update,
  serial update-all and previous-version restoration, using that same catalogue,
  cache and installer. No automatic replacement or background polling is added.
- #255: source-qualified confirmed removal, cancellation and Download again in
  Library, including after restart/offline. Personal notes, highlights, history
  and chosen passages survive. An explicit removal never silently chooses a new
  Bible, including after a later commentary/tool installation; existing fallback for unrelated missing legacy sessions is preserved.
- #256: reuse the same actions and checks for existing directly sourced CrossWire,
  eBible and AndBible Extra (the current Xiphos-labelled mirror). The existing
  mirror does not establish ownership of an unrelated xiphos.org installation.
  Installed dictionary/lexicon/general-book lifecycle is supported without
  implementing unassigned dictionary-discovery work #236 or a new content viewer.

The former separate update dialog now reports local/external module information
read-only, without a second network updater. Module operations live in resource
details and adapt vertically in small windows.

## Identity and file safety

A SWORD ID, title or larger version alone never proves edition identity. Curated
canonical identity/edition and original direct-provider TextSource/attribution
are compared. Changed source, verse numbering, uncertain version, encrypted
credentials, same-version repacks and unverified local files block replacement.
Original installer file receipts are required; today's local bytes are never
rehash-enrolled as supposed originals. Missing evidence stays unavailable.

Candidates use the existing installer in private staging. Atomic directory
exchange, a recoverable journal and the latest previous-version backup retain a
complete source until commit. Recovery restores the version current before an
uncommitted update or rollback. Failed removal commit writes restore immediately.
Changed/unknown stored copies are preserved with an explicit cleanup error.
Ownership of publisher companion files comes from original receipts plus hashes,
never edition-specific filenames. User annotations/preferences/reference registries
are outside removed resource roots. Encrypted modules remain unchanged.

Each native reader owns one lifetime shared directory lease. A retained consumer
prevents mutation; there is no per-verse or per-scroll locking/timer. The GTK
bridge releases affected readers on its main thread, cancels stale positioning
and resumes the same reading context. Commentary text/raw caches now follow the
reader lifetime; class-method LRU keys previously retained a real MHCC reader.
Open note editors keep their exact buffer, unsaved text/labels and autosave state;
only their read-only Scripture excerpt refreshes after resource changes.

RawLD/RawLD4/zLD index APIs and RawGenBook TreeKey navigation were proved with
actual bindings. The packaged SWIG setPosition(SW_POSITION(...)) call stopped a
native verification process, so the proven index/tree APIs are used instead.
New native tool verification is a bounded subprocess; malformed decoding cannot
terminate GTK. Synthetic test fixtures are never shipped resource content.

## Validation and current delivery status

Native GNOME49 development-runtime checks cover atomic switch/rollback, both
interruption directions, failed journal writes, cancellation, corrupt packages,
source collisions, missing original fingerprints, local changes, concurrent/native
consumers, removal/restart and serial update-all stop/retry. Relevant suites
passed55 integrated checks,17 GUI batch/recovery checks,15 native/recovery checks,
32 commentary/lifecycle checks,49 final four-format/source checks,24 affected note/lifecycle checks and separate
workspace draft/label preservation. They overlap and must not be added as a
fictitious unique total. The isolated native immersion-click check also passed.

Real public Segond0.1.0, MHCC0.1.0, Easton2.0.1 and Didache1.0 were downloaded and
read into an isolated profile. All four passed actual FR/EN GTK cancellation,
confirmed removal and Download-button reinstall, light/dark and360px, with exact
source hashes and personal data retained. RawGenBook uses the same verified controls.
Current live catalogues report the installed versions current; synthetic1.0→1.1
checks are not presented as live published upgrades.

The first branch CI failed on three test-integration assumptions: a held-download
proxy did not forward the new cancellation option, an old catalogue expectation
excluded dictionaries, and a test implicitly treated the last provider as
YouVersion. Explicit option/identity forwarding preserves those assertions;32
targeted reproduction checks passed. The native click test's nested xvfb-run is
unavailable inside the local sandbox, so it passed in a fresh composited session
with the same isolated flag used by packaged CI. Final CI is still mandatory.

PR266 remains unmerged/unpublished at this checkpoint. Development source with
an installed runtime is not evidence that the signed application includes it.
Final review, packaged checks, actual signed update/data verification and a
numbered alpha release are delivery gates. Keep each issue OPEN for client review.

## Material limits

Atomic exchange currently requires Linux and a supporting filesystem. Unsupported
platforms/filesystems refuse without unsafe rename fallbacks. External, shared or
non-owned roots are information-only. Legacy installs without original receipts
and ambiguous/unadvertised versions cannot be automatically replaced. New source
providers, unavailable data and unsupported key formats are never guessed. Cloud
X11/software rendering is separate from client Wayland/GPU/accessibility acceptance.

Direct-provider staging is tested independently for CrossWire, eBible and the
existing AndBible Extra mirror, including exact package URL, source namespace and
byte-for-byte previous-version restoration. Curated packages have advertised
SHA-256/size; direct repositories may not advertise a cryptographic digest, so
their HTTPS transport, exact source/configuration/version/legal metadata and
native readability are verified and the received bytes are fingerprinted. A
computed receipt is not represented as a publisher signature. Native tool probes
are bounded to32 dictionary entries or256 tree nodes and20seconds.

Final active-consumer checks found two more lifetime owners: closed immersion
page sources and an idle metadata worker's last completed callable/result. Closed
immersion now retains only immutable exit coordinates/section data; annotation
follow callbacks are cancelled before native collection, and idle workers drop
completed work references. No reader lease is weakened. A deliberately retained
closed GTK widget now passes active removal; actual real-module immersion and
STEP original-text dialogues close before switching, with exact reinstall and
unchanged notes/STEP data.29 combined native immersion/lifecycle/startup checks
pass, including the idle-reference regression and commentary exit restoration.
