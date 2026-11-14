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
