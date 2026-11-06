# Local notes and linked passages

Related to #202 and the compatibility requirements in #126. This increment does not implement synchronization, a relationship graph, highlight identifiers or the broader pre-beta migration work in #126.

## Identity and references

A note retains its existing UUID, primary `versification`, `start` and `end`, original translation/language, Markdown body, labels, creation/modification timestamps and optimistic revision. Adding or removing a relationship does not create a second note or change its primary passage. Secondary relationships contain `versification`, `start` and `end`; duplicate triples and a repeated primary triple are removed. Up to 200 secondary relationships are supported. Ranges are ordered within one book. Relationships with different numbering systems are never equated by their printed numbers.

SQLite schema 2 adds `note_passages`, keyed by note UUID and presentation ordinal, with a unique constraint on the note/reference triple and cascading deletion. Existing annotation views share the verified reference mapper. An unavailable or unmappable relationship remains stored; it cannot manufacture a Bible equivalence. Manual entry works without an installed Bible and validates reference structure. Resource availability and verified alignment are checked when displaying/opening a reference. Body citations remain independent and never create relationships automatically.

## Upgrade safety

Before upgrading a valid schema-1 database, Bible validates its existing notes and SQLite integrity, takes a private SQLite backup under a write lock, and verifies its schema/application IDs, integrity and logical contents. The backup is flushed and retained as `backups/notes-before-schema-2-<id>.sqlite3` before the schema transaction begins making changes. SQLite atomically commits the additional table and schema version; interruption rolls that transaction back. Backup or schema failures prevent editing and retain the original data. Future or unrelated databases are rejected without modification.

An older alpha that only understands schema 1 cannot edit schema 2. The pre-migration snapshot is retained for recovery; ordinary updates must retain the current database and must not substitute that snapshot for newer notes.

## Portable backups

`bible-notes` and `bible-personal-annotations` version 2 add a `links` array to each note. Version-1 note and combined backups remain readable with no secondary relationships. Version-1 standalone highlight backups retain their established validator and do not change format. Unsupported versions, malformed relationships or duplicate UUIDs are rejected before mutation.

Combined exports still contain notes, labels and highlights only. They exclude Bible translations, preferences, account credentials and migration snapshots. The existing verified pre-restore backup, durable recovery journal, all-input validation and repeatable two-store restore apply to linked passages too. Conflict copies retain all relationships under their new note UUID; repeated imports are idempotent.

## Editing

Both note editors use native GTK text tags over the existing Markdown source. Formatting delimiters are hidden in the editor; persistence includes them verbatim. Viewing a note or changing labels/relationships does not rewrite its body. Bold, italic and list commands are explicit undoable edits. Links and raw HTML remain inert; no embedded content is executed. The quick editor retains explicit Save and unsaved-change guards. The Notes workspace coalesces autosave, reports failures, and preserves the draft on navigation or close when writing fails.

Legacy Markdown list prefixes are presented as bullets. An unchanged editing buffer retains its exact original source, including after a full undo; editing the body may normalize list markers to visible Unicode bullets, which remain readable in older alpha previews. The clipboard uses native plain text rather than an HTML/rich-text exchange engine. Bible citations remain available with Ctrl+click or Ctrl+Enter while ordinary clicks and Enter keep their editing roles; they reuse the existing verified reference preview and unsaved-navigation guard.
