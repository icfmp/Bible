# Current alpha stabilization — resource installation and reading UI

Published baseline remains source **6560dc4**, revision **39674239853-2**,
unchanged signed fingerprint `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.
Main `8e94fd7` already contains reviewed page/eBible/highlights/pagination PRs;
none of those integrations is repeated. Current candidate work is separate.

## #56 — actual installation cause and targeted correction

Actual signed /app code fetched the five current French eBible packages.
FOB, F10, FRANCL and SBL fail the strict notice comparison; JND installs.
Detailed evidence shows **only generated terminal revision dates differ**:
About on all four, and CopyrightNotes also on FRANCL. Actual license, author,
rights prose, holders and restrictions are unchanged. These are not four
substantive conditions conflicts. The earlier delivery's broad metadata
rejection diagnosis is corrected by this direct field comparison.

Reviewed AndBible current-stable JSword submodule commit
`6ebd10a005fa7761e611c048ececea1430e22546`,
`src/main/java/org/crosswire/jsword/book/install/sword/AbstractSwordInstaller.java`
(install, lines 229–272): the configured package ZIP is downloaded, unpacked
into mods.d/modules and registered. It does not require catalogue/package About
byte equality. Bible retains its additional archive/identity/path/encryption,
actual capability, conditions and readable-content checks rather than copying
an unguarded extraction path.

The narrow compatibility correction recognizes a terminal date-only update in
otherwise identical About, with matching CopyrightNotes dates if present, only
for a package explicitly declaring Haiola auto-generation in its version history.
It never ignores CopyrightDate, license, holder, attribution wording, author or
restriction changes. Both the raw package configuration and original catalogue
notices are retained; installed details read actual package notices. This is a
generator-metadata capability rule, not an allowlist of Bible names/providers.
Regression tests still refuse genuine changed conditions, encryption and unsafe
archives. Failure remains resource-specific and visible after selection or
catalogue refresh, with Retry for the failed resource; transfer completion is
not reported as usable installation.

13 library tests and 8 affected GTK/provider tests pass, plus the French error-state
regression. Candidate UI installation immediately exposes all five French eBible
Bibles and two additional actual CrossWire Bibles (KJV and Crampon). Seven independent
SWORD John 3:16 comparisons pass. All seven reopen/read after restart inside an
isolated network namespace. Four systems are represented: NRSV, Luther, Catholic2,
NRSVA and KJV (five systems). Candidate resource code is not a final packaged
verification. Final full checks/build/actual Flatpak checks remain required.

Evidence: `evidence/stabilization-56-original-package.txt`,
`evidence/stabilization-56-candidate-install.txt`,
`evidence/stabilization-56-candidate-offline.txt`.
Reproducer: `python3 -m tools.check_resource_installation TEST_PROFILE`; restart
with `--offline` in an isolated network namespace, or Flatpak `--unshare=network`.
No resources are shipped with the application.

## Escalation requested by the client

The client requested notification before changes requiring higher-reasoning review
of versification or pagination mechanisms. The following two items were explicitly
reported to the client and remain pending that review:

- #57: eBible Darby declares **Luther**. Native SWORD 1.9 registers this system
  without a mapping table (`versificationmgr.cpp`, line 74); the current whitelist
  therefore blocks it. Simply deleting the whitelist would use native identity
  fallback, falsely claiming alignment (especially Psalms). Inspect verified
  AndBible/JSword mappings and the shared mechanism; do not patch individual names.
- #24: general heading keep-with-next, preparation/cache optimization and cancellation
  affect the pagination mechanism. Preserve accepted visual layout and current
  canonical anchors; Mark 7→8 and Luke 13→14 are reproducers.

Independent #53/#54/#55 controls/surface corrections may continue. No #26 or
OpenBible #47–50 work; no visual/functional issue is closed without client acceptance.
No candidate alpha is announced as available until actual build and publication
verification. Preserve notes/highlights/resources/sessions/preferences and signing.
