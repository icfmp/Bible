# Library lifecycle work in progress

Related to #253, #233, #255 and #256. Application repository only.

The optional Bible Resources catalogue adapter consumes the existing public JSON
and standard SWORD metadata. Initial installation verifies the exact advertised
size/SHA-256, source identity, driver, versification, legal metadata and native
readability. It shares the existing installer and per-provider cache. It does
not introduce resource content or publisher infrastructure.

The common lifecycle stages candidates privately, checks original file receipts
and edition identity, then uses an atomic directory exchange with a recoverable
journal and a single previous-version backup. A native reader owns a lifetime
shared directory lease; mutation refuses rather than races a retained reader.
The GTK bridge releases affected readers on the main thread and resumes the same
reading context while retaining note buffers, annotations and history. Leaving
aligned rows can populate the editorial cache, so that cache is cleared afterward.

Current checks: 38 backend/installer/provider/metadata tests and two actual GTK
consumer-quiescence tests passed in the GNOME49 runtime. A disposable live public
LSG installation was independently hashed against the published package and read
through SWORD; FR/EN Library captures exist. These are development-runtime checks,
not evidence of this branch being in the installed signed application.

Still unfinished: actionable Library controls, explicit-removal restart behavior,
native dictionary lifecycle validation, complete cancellation/restart/permission
coverage, final source review/CI, signed installation verification and numbered
alpha publication. Legacy receipts without original fingerprints cannot prove
absence of local modifications and therefore do not permit automatic replacement.
Changed/missing edition identity or same-version content changes are not upgrades.
Atomic exchange currently requires Linux and a supporting filesystem; unsupported
platforms must refuse mutation without changing installed files.

The existing Xiphos-labelled source is AndBible Extra. Its mirror identity is not
proof that a module installed from xiphos.org belongs to that source. No new
provider is added without authorization. External/shared roots remain read-only.
No issue is complete or published by this checkpoint.

## Actionable controls checkpoint

The existing Library now has manual same-source update checking and per-resource
Update, Restore previous version and confirmed Remove actions. Verified update-all
runs serially and stops on failure/cancellation. The old separate dialog is local
module information only; copied/external roots stay read-only. No update polling
or automatic content replacement is introduced. Unknown/legacy receipts cannot
prove original files and never acquire fabricated baseline hashes.

Installed RawLD/RawLD4/zLD dictionaries appear under Study tools for lifecycle
actions only; this does not implement unassigned dictionary discovery #236.
RawGenBook is classified separately and remains unavailable for installation or
update pending verified native support. The native dictionary index API is proven
with real bindings. The SWIG SW_POSITION wrapper stops native SWLD, so it is not
used. Newly supported dictionary validation runs in a bounded subprocess: a bad
native decoder must not close GTK. Synthetic zLD fixture compressor ownership was
also corrected; fixtures are never application resource content.

Explicit removal leaves a journal intent so the legacy missing-module startup
fallback cannot silently select another Bible. Existing fallback for unrelated
missing/unreadable legacy sessions remains tested. Original notes, highlights,
history and chosen translation/reference survive removal and restart.

Latest checks:55 integrated native/backend/provider tests,12 focused removal/
comparison/lifecycle tests and5 update-offer/native-dictionary-safety tests passed
(they overlap). No library feature is merged or published yet. Live public Segond,
MHCC and CrossWire Easton were installed/read into a new disposable root. Easton's
package has a companion file outside its indexed basename: ownership must come
from the original installer file receipt and matching hash, not a per-edition
filename exception. Original source files remain unchanged.

Still required: full native GUI actions across real resources, batch/cancel/error
checks, final review/CI/Flatpak update verification and numbered alpha publication.
Actual public catalogues do not currently prove a newer same-edition version for
these test installs; synthetic1.0→1.1 proofs must not be presented as a live release.

## Real UI and recovery follow-ups

Actual native FR/EN Library walkthroughs now pass cancellation, confirmed removal
and exact reinstall of the real public Segond0.1.0, MHCC0.1.0 and Easton2.0.1.
The live catalogue reports those installed versions current; no live newer release
is invented. All source file hashes match after reinstall; notes/highlights remain.
The real MHCC check exposed class-level text/raw LRU caches retaining disposed
readers. Their20-entry caches now follow each reader lifetime; GC regression and
other commentary consumers are checked. An obsolete parallel-positioning callback
is cancelled when detaching its source.

Recovery separately tests update and rollback direction: an interrupted operation
restores the version current before its uncommitted switch. A failed removal commit
restores its source immediately, and cancellation leaves no false removal intent.
Removal records keep source attribution for Download again/offline listing without
adding general dictionary discovery. Narrow lifecycle actions stack vertically.

These remain developer-runtime checks. PR266 is draft and unmerged; final packaged
CI, actual signed update and numbered prerelease remain required.
