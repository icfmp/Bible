# Annotation snapshot review

Related to #94. This increment targets the coordinated finishing branch; it does
not publish an intermediate alpha. The numbered-release work in #87 remains paused.

The new format contains validated notes (including labels, Markdown, canonical
ranges, versification, original source and timestamps) and personal highlights.
It excludes Bible packages, application preferences and credentials. It is plain
JSON and the Preferences page explicitly says that it is unencrypted. Legacy
note-only and highlight-only exports remain accepted and their existing routes
remain unchanged.

Export saves pending drafts through the existing editor guard, reads notes in a
SQLite transaction, verifies that the shared highlight snapshot still matches its
file, validates the complete payload and atomically replaces the chosen output.
Restore validates all input before creating any recovery record. It merges without
overwriting existing highlights; notes with colliding identifiers and different
contents receive new identifiers. Identical notes are skipped. Confirmation states
these semantics. A verified pre-restore annotation snapshot precedes all writes.

The two stores do not share a database transaction. A durable, hashed recovery
record therefore remains until both writes commit. Startup and failed restore
recover the previous full annotation snapshot before allowing ordinary editing.
If recovery itself fails, the marker and snapshot remain, and Notes reports the
error instead of silently accepting a partly restored state. No schema migration
or new synchronization engine is involved. Recovery deliberately returns to the
pre-restore annotations after a process interruption.

Developer checks: complete Unicode/Markdown/label/range snapshots, missing source
modules, conflicting notes and colors, duplicate import, malformed/newer formats,
safety-backup write failure, second-store write failure, interrupted recovery and
legacy imports; native file-chooser cancellation and declined confirmation. Existing
note/highlight storage tests also pass. Installed-runtime checks run in CI.
