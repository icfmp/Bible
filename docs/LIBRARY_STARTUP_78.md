# Responsive Library startup (#78)

## Reproduced freeze

The published signed alpha from source `f16e99cde40f0580b5f7ca0bac419d79b1267e65`,
Flatpak commit `3994122172977460e560c1d5bd1a83510adf0c274cc7ad744f039a48f585fe57`,
was measured using actual five-provider caches: 1,941 resources and 1,324 language
codes. Immediately opening Library during reader scroll restoration blocked its
constructor for about 2.8 seconds in an unprofiled installed-package run. Its first
paint arrived around 2.9 seconds; the Library heartbeat gap was about 2.8 seconds.
This is an actual synchronous main-thread freeze, independent of network success.

A separately instrumented run identified repeated unsuccessful Babel native-locale
lookups for ISO 639-3 languages without CLDR locales. These repeatedly normalize
Babel's whole locale inventory. Profiling amplified the original constructor to
12.6 seconds; this profiled number is not an unprofiled before/after comparison.
The constructor also synchronously validated JSON caches and installed metadata,
then created language/model data. Online refresh exposed another blocking path:
replacing unchanged language lists repeatedly caused expensive native row rebinding.

**The reported single crash was not reproduced.** No historical traceback/core is
available and no crash mechanism is claimed. The freeze correction and safe worker
lifecycle are verified separately from that unknown incident.

## Implementation and ownership

One plain-data catalogue session belongs to each reading window and survives
Library close/reopen. A serial metadata worker validates caches, scans installed
configuration and study indexes, prepares language names and normalized search
terms. Parallel provider refresh publishes coalesced, generation-guarded snapshots;
reopening reuses preparation and deduplicates refresh. Installed metadata is
rescanned when reopening, so installations in another window remain visible.
Cache/source failure retains successful results and reports errors; preparation
failure produces a visible, retryable state rather than an endless busy state.

GTK objects are created and changed on GTK's thread through idle callbacks.
Resource and language models append at most 16 objects per idle, retaining the selected
resource while rebuilding. Identical refresh snapshots update status without
replacing native models or selection. Labels/search terms are reused. Babel is
only asked for native locale names when a CLDR base locale exists; ISO/CLDR French
and English names, exact provider codes, variants and notices remain unchanged.

Disposable metadata workers are daemon futures without the interpreter-exit join
registered by ThreadPoolExecutor. Closing unsubscribes/drops stale results and
cancels queued work; an in-flight bounded socket does not hold application exit.
Only metadata and atomic catalogue-cache writers use this executor. Existing
resource installation completion/atomicity policy is unchanged. No worker handles
a GTK object or mutable native SWORD reader. No new dependency, schema migration,
cache deletion, profile reset or network-policy workaround is introduced.

## Verification boundaries

Receipts under `docs/evidence/library-78` distinguish source tests, locally built
installed Flatpak tests and the original published-package observation. The tracked
`tools/check_library_startup.py` records application-constructor time separately
from the Library action/first paint and a real GLib heartbeat. These local timings
are observations on one software-rendered validation machine, not performance
guarantees for every desktop.

Regression coverage includes an 8,000-entry valid cache, slow preparation, GTK
owner-thread model creation, heartbeat, stable selection, repeated close/reopen,
deduplicated progressive refresh, visible failure/retry, another window's installed
resources, unchanged native models and process exit with a blocked network worker.
Actual installed-package checks cover existing notes/modules/tabs, empty profiles,
cold/warm metadata and offline namespaces. A native pointer activates Library and
the real eBible Download button; source identity, French filtering, installation
state/notices and exact local SWORD text are checked. This is X11/Xvfb input, not
a claim about the client's personal GNOME session. Portal/display warnings are
retained in logs. Deep accessibility is deferred and has not been tested.

Publication remains a distinct final gate: exact-head review/CI, merge/main CI,
signed alpha provenance, ordinary update of the controlled existing installation,
source-byte audit and preservation of annotations, modules, preferences, study data
and catalogue caches. Publication results are recorded on the PR/issue after these
gates actually pass. No candidate installation is requested from the client.

The complete **228 source tests** and **46 affected installed Flatpak tests** pass.
All **84 packaged files** match source; all 14 canonical mapping tables/notices
remain. In the final private-package runs, first paint is 0.07–0.11 s, with a
0.34 s maximum heartbeat gap during a real cold five-source refresh and about
0.07 s for the warm-cache run. Existing-profile offline startup and native reopen
preserve notes, installed resources and reading history. The original published
alpha baseline remains separately identified above.
