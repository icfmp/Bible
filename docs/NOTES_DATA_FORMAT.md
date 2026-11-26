# Local annotations: notes, highlights and linked passages

Maintained local annotation contract for #202 and #126. This describes persisted records and portable backups, not synchronization or a relationship graph.

## Identity and references

A note retains its existing UUID, primary `versification`, `start` and `end`, original translation/language, Markdown body, labels, creation/modification timestamps and optimistic revision. Adding or removing a relationship does not create a second note or change its primary passage. Secondary relationships contain `versification`, `start` and `end`; duplicate triples and a repeated primary triple are removed. Up to 200 secondary relationships are supported. Ranges are ordered within one book. Relationships with different numbering systems are never equated by their printed numbers.

SQLite schema 2 adds `note_passages`, keyed by note UUID and presentation ordinal, with a unique constraint on the note/reference triple and cascading deletion. Existing annotation views share the verified reference mapper. An unavailable or unmappable relationship remains stored; it cannot manufacture a Bible equivalence. Manual entry works without an installed Bible and validates reference structure. Resource availability and verified alignment are checked when displaying/opening a reference. Body citations remain independent and never create relationships automatically.

## Upgrade safety

Before upgrading a valid schema-1 database, Bible validates its existing notes and SQLite integrity, takes a private SQLite backup under a write lock, and verifies its schema/application IDs, integrity and logical contents. The backup is flushed and retained as `backups/notes-before-schema-2-<id>.sqlite3` before the schema transaction begins making changes. SQLite atomically commits the additional table and schema version; interruption rolls that transaction back. Backup or schema failures prevent editing and retain the original data. Future or unrelated databases are rejected without modification.

An older alpha that only understands schema 1 cannot edit schema 2. The pre-migration snapshot is retained for recovery; ordinary updates must retain the current database and must not substitute that snapshot for newer notes.

## Portable backups

`bible-notes` and `bible-personal-annotations` version 2 add a `links` array to each note. Version-1 note and combined backups remain readable with no secondary relationships. Standalone highlight versions 1 and 2 remain readable. Combined version 3, described below, adds highlight identity/date metadata without changing notes-only version 2 or SQLite schema 2. Unsupported versions, malformed relationships or duplicate UUIDs are rejected before mutation.

Combined exports still contain notes, labels and highlights only. They exclude Bible translations, preferences, account credentials and migration snapshots. The existing verified pre-restore backup, durable recovery journal, all-input validation and repeatable two-store restore apply to linked passages too. Conflict copies retain all relationships under their new note UUID; repeated imports are idempotent.

## Editing

Both note editors use native GTK text tags over the existing Markdown source. Formatting delimiters are hidden in the editor; persistence includes them verbatim. Viewing a note or changing labels/relationships does not rewrite its body. Bold, italic and list commands are explicit undoable edits. Links and raw HTML remain inert; no embedded content is executed. The quick editor retains explicit Save and unsaved-change guards. The Notes workspace coalesces autosave, reports failures, and preserves the draft on navigation or close when writing fails.

Legacy Markdown list prefixes are presented as bullets. An unchanged editing buffer retains its exact original source, including after a full undo; editing the body may normalize list markers to visible Unicode bullets, which remain readable in older alpha previews. The clipboard uses native plain text rather than an HTML/rich-text exchange engine. Bible citations remain available with Ctrl+click or Ctrl+Enter while ordinary clicks and Enter keep their editing roles; they reuse the existing verified reference preview and unsaved-navigation guard.

Workspace autosave commits within a 600 ms write window while ordinary typing continues; it does not wait indefinitely for a pause. Leaving or closing flushes the draft. Abrupt process termination can still lose the pending window, and manual label/reference entries remain uncommitted until explicitly added. Failed writes keep the draft and navigation/close protection; there is no background retry loop when content is unchanged.

## Highlight identity and common annotation fields

Both annotation types have a canonical lowercase UUID (`id`), independent of
body/color and source module availability. They remain independent records:
multiple note UUIDs may share a passage, but only one active whole-verse mark
exists per exact `(system, reference)` pair. The UI's passage-based highlight
row key is a derived presentation index, not persisted identity. Overlapping
notes, highlights, inline indicators and collection filters do not create
stored relationships. Deleting a note never deletes its highlight, or vice
versa. Note links remain explicit relationships to passages, not to highlights.

| Field | Notes | Highlights |
| --- | --- | --- |
| Canonical passage | `versification`, ordered `start`/`end`, plus explicit `links` | `system`, one `reference` |
| Original context | `origin_translation`, `origin_language` | `origin_resource`; `resource` tracks the latest edit context |
| Content | Verbatim Markdown `body`, normalized `labels` | `color`: `yellow`, `green`, `blue` |
| Identity | Existing note UUID | New UUID4; legacy UUID5 described below |
| Dates | Existing timezone-aware ISO8601 `created`, `modified` | Timezone-aware ISO8601 or JSON `null` for unknown dates |
| Revision | Existing optimistic note revision | Positive integer, initially 1; increment on an actual color/context change |

References use canonical OSIS-style book/chapter/verse syntax, including supported
subchapter suffixes, and retain their numbering-system identity. Equal printed
references in different systems are not equivalent. The existing verified mapper
remains responsible for display/navigation; unknown systems and unavailable
modules remain stored, without guessed mappings or substituted passages.
No reference normalization/mapping is performed during persistence or import.

Recoloring retains the highlight UUID, creation date and original resource.
An unchanged color/context is a no-op for metadata. Deletion removes the active
record; a subsequent new mark gets a fresh UUID and recorded creation date.
Revision is local edit detection, not a distributed clock. No tombstones,
partial-text offsets, sync journal or grouped marks are introduced. A future
finer granularity requires an explicit new schema/backup migration; it must not
reinterpret existing whole-verse marks or conflate independent note identities.

## Highlight storage and migration

`highlights.json` uses storage schema **2**, currently also standalone portable
highlight version **2**. The versions are separate named constants even though
both currently equal 2. Its exact object keys are `version` and `marks`.
Each mark has the nine keys shown in this valid synthetic example:

```json
{"version":2,"marks":[{"id":"551fb15e-8b8c-44ed-8bb4-49f66947ad98","system":"KJV","reference":"Gen.1.1","color":"blue","resource":"ExampleModule","origin_resource":"ExampleModule","created":"2026-11-26T10:00:00+00:00","modified":"2026-11-26T10:01:00+00:00","revision":2}]}
```

Legacy schema 1 has only `system`, `reference`, `color`, `resource`. Migration
assigns UUID5 using the fixed namespace in `bible.highlights.LEGACY_NAMESPACE`
and the JSON-encoded exact `(system, reference)` pair. It does not depend on the
color, module, filesystem path or migration time. This assignment is deterministic
across restarts and repeated legacy imports; new marks use UUID4 instead.
Legacy `created`/`modified` are **null**, not migration time; revision starts at 1
without inventing an edit history. An actual subsequent recolor records only
`modified`, while `created` remains unknown. `origin_resource` initially equals
the original legacy resource.

Startup validates the entire bounded legacy payload, takes an exclusive
nonblocking advisory file lock and durably writes a private, byte-verified
`backups/highlights-before-schema-2-<sha256>.json` snapshot before replacing the
original atomically. The snapshot is immutable, mode0600 on POSIX, and retained
for recovery. A partial temporary write cannot replace the live file or the
verified snapshot. A failed backup/validation/migration blocks edits and export
instead of silently overwriting the original. On restart, a valid v2 file keeps
its IDs; a retained v1 file derives the same IDs and retries only after the
verified backup. Pending two-store recovery is handled before ordinary migration.
Older alphas reject v2; never restore the old snapshot over newer annotations
merely to downgrade the application.

Every live mutation/export checks the exact prior disk bytes under the same lock.
A stale app instance must reopen instead of overwriting a newer file. Combined
operations acquire the notes SQLite write transaction before the highlight lock;
ordinary autosave cannot interleave the protected snapshot/restore. Note mutations
and notes-only export/restore recheck the pending marker after obtaining the
SQLite write lock, including when they waited behind a restore transaction. Locks do not
run periodic work or block the main loop waiting for another app. POSIX flock is
exercised by a separate-process test; the Windows msvcrt counterpart still needs
native Windows acceptance. Notes continue using their existing SQLite contract.

## Backup compatibility and conflict policy

| Input | Supported versions | Contents |
| --- | --- | --- |
| `bible-notes` | 1, 2 | Existing notes-only format; v2 supports links |
| Standalone `version`/`marks` | 1, 2 | v1 four-field marks; v2 complete metadata |
| `bible-personal-annotations` | 1, 2, 3 | v1 notes without links/legacy marks; v2 linked notes/legacy marks; v3 linked notes/v2 marks |

Current combined exports use **version3**. This does not increase notes-only
backup version2 or SQLite schema2. Unsupported versions and unknown fields are
rejected before mutation; duplicate UUIDs or passage keys within a highlight
payload are invalid. This conservative policy preserves the unreadable input
rather than pretending to preserve future fields through an older writer.
Strict note/link validation remains. Highlight files are bounded at32MiB
(the historical8MiB payload gains identity/date/origin fields on migration);
combined backups remain bounded at48MiB and notes-only backups at32MiB. No preferences,
resource contents, caches or credentials are added to an annotation backup.

Note merge semantics remain: identical content is skipped, divergent content
with the same UUID becomes an independent conflict-copy UUID, preserving all
links/dates/labels/body; repeated import finds that copy and does not multiply it.
For highlights, exact records are skipped. Legacy records matching all four
original fields are also skipped even if a current UUID differs. Otherwise any
UUID or passage collision retains the local active record and saves the fully
validated incoming highlights in private
`backups/highlight-conflicts-<sha256>.json` **before** committing. This file is a
valid standalone v2 backup containing the rejected values and their identities.
No precedence is inferred from timestamps, no silent remapping is performed,
and no second active mark is created for that passage. The restore reports the
conflict count and recovery path to its caller. Repeated identical imports reuse
the same conflict file and do not duplicate active annotations. A client can
inspect/restore a recovery backup into a separate profile; no new conflict UI
is introduced in this increment.

Combined restores retain the existing private pre-restore combined snapshot and
durable `annotation-restore.pending.json` marker. All input is validated first;
the SQLite transaction and highlight lock cover the consistent snapshot and
writes. The marker is retired only after both stores commit durably. An error
replays the verified original snapshot; a crash leaves the marker so restart
repeats recovery. Legacy version1/2 recovery snapshots remain supported and get
deterministic highlight IDs. Edits and exports are refused while recovery is
pending; a failed recovery never authorizes autosave over partial state.
