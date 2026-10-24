"""Local, versioned passage notes. No resource files, GTK, or network access."""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import unicodedata
import uuid

from .book_names import FRENCH, normalized

SCHEMA_VERSION = 1
APPLICATION_ID = 0x424E4F54
MAX_BACKUP = 32 * 1024 * 1024
MAX_BODY = 200_000
BOOK_ORDER = {book: index for index, book in enumerate((
    'Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh '
    '1Esd 2Esd Tob Jdt Esth AddEsth 1Macc 2Macc 3Macc 4Macc Job Ps Ps151 PrMan '
    'Prov Eccl Song Wis Sir Isa Jer Lam Bar EpJer Ezek Dan AddDan PrAzar Sus Bel '
    'Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John '
    'Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb '
    'Jas 1Pet 2Pet 1John 2John 3John Jude Rev').split())}


class NotesError(ValueError):
    pass


class NoteConflict(NotesError):
    pass


def parts(reference):
    if not isinstance(reference, str) or not re.fullmatch(
            r'[1-4]?[A-Za-z][A-Za-z0-9]{0,15}\.[1-9][0-9]{0,2}\.[1-9][0-9]{0,2}', reference):
        raise NotesError('Invalid passage reference')
    book, chapter, verse = reference.split('.')
    return book, int(chapter), int(verse)


def label_key(value):
    if not isinstance(value, str):
        raise NotesError('Invalid label')
    value = unicodedata.normalize('NFC', value.strip())
    if not value or len(value) > 80 or any(ord(c) < 32 for c in value):
        raise NotesError('Invalid label')
    return value.casefold()


def clean_labels(values):
    if not isinstance(values, (list, tuple)) or len(values) > 32:
        raise NotesError('Invalid labels')
    found = {}
    for value in values:
        key = label_key(value)
        found.setdefault(key, unicodedata.normalize('NFC', value.strip()))
    return tuple(found[key] for key in sorted(found))


@dataclass(frozen=True)
class Note:
    id: str
    versification: str
    start: str
    end: str
    origin_translation: str
    origin_language: str
    body: str
    labels: tuple[str, ...]
    created: str
    modified: str
    revision: int = 1

    def covers(self, reference):
        book, chapter, verse = parts(reference)
        first, last = parts(self.start), parts(self.end)
        return book==first[0]==last[0] and first[1:]<=(chapter,verse)<=last[1:]


def validate(note):
    try:
        if str(uuid.UUID(note.id)) != note.id:
            raise ValueError('Invalid note identifier')
        first, last = parts(note.start), parts(note.end)
        if first[0] != last[0] or first[1:] > last[1:]:
            raise ValueError('A note passage must be ordered within one book')
        for value in (note.versification, note.origin_translation, note.origin_language):
            if not isinstance(value, str) or not value or len(value) > 128 or any(ord(c) < 32 for c in value):
                raise ValueError('Invalid origin context')
        if not isinstance(note.body, str) or not note.body.strip() or len(note.body) > MAX_BODY or '\x00' in note.body:
            raise ValueError('A note must contain text (maximum 200000 characters)')
        if type(note.revision) is not int or note.revision < 1:
            raise ValueError('Invalid note revision')
        for stamp in (note.created, note.modified):
            if not isinstance(stamp, str) or datetime.fromisoformat(stamp).utcoffset() is None:
                raise ValueError('Invalid note date')
        return replace(note, labels=clean_labels(note.labels))
    except (ValueError, TypeError, AttributeError) as error:
        raise NotesError(str(error)) from error


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


class NoteStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        if new:
            # Create privately before SQLite opens it; sqlite3 uses this mode for journals too.
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
        self.generation = 0
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        try:
            version = self.db.execute('PRAGMA user_version').fetchone()[0]
            tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            app = self.db.execute('PRAGMA application_id').fetchone()[0]
            if version == 0 and not tables and app == 0:
                # Explicit migration 0 -> 1 applies only to a genuinely empty database.
                with self.db:
                    self.db.execute('BEGIN IMMEDIATE')
                    self.db.execute('''CREATE TABLE notes (
                        id TEXT PRIMARY KEY, versification TEXT NOT NULL,
                        start TEXT NOT NULL, end TEXT NOT NULL,
                        origin_translation TEXT NOT NULL, origin_language TEXT NOT NULL,
                        body TEXT NOT NULL, created TEXT NOT NULL, modified TEXT NOT NULL,
                        revision INTEGER NOT NULL)''')
                    self.db.execute('CREATE TABLE labels (key TEXT PRIMARY KEY, name TEXT NOT NULL)')
                    self.db.execute('''CREATE TABLE note_labels (
                        note_id TEXT REFERENCES notes(id) ON DELETE CASCADE,
                        label_key TEXT REFERENCES labels(key), PRIMARY KEY(note_id, label_key))''')
                    self.db.execute(f'PRAGMA application_id={APPLICATION_ID}')
                    self.db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
            elif version != SCHEMA_VERSION or app != APPLICATION_ID:
                raise NotesError('Unsupported notes database. The original file has been preserved.')
            self.db.execute('PRAGMA foreign_keys=ON')
            if (self.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok'
                    or self.db.execute('PRAGMA foreign_key_check').fetchone() is not None):
                raise NotesError('Invalid notes database')
            self.all()  # Validate persisted records before allowing edits.
        except Exception:
            self.db.close()
            raise

    def all(self):
        result = []
        for row in self.db.execute('SELECT * FROM notes'):
            labels = tuple(r[0] for r in self.db.execute('''SELECT labels.name FROM labels
                JOIN note_labels ON labels.key=note_labels.label_key WHERE note_id=? ORDER BY labels.key''', (row['id'],)))
            result.append(validate(Note(**dict(row), labels=labels)))
        return result

    def get(self, identifier):
        return next((note for note in self.all() if note.id == identifier), None)

    def labels(self):
        return [r[0] for r in self.db.execute('SELECT name FROM labels ORDER BY key')]

    def _write(self, note):
        record = asdict(note)
        record.pop('labels')
        keys = tuple(record)
        self.db.execute(f'INSERT INTO notes ({",".join(keys)}) VALUES ({",".join("?" for _ in keys)})',
                        tuple(record.values()))
        for label in note.labels:
            key = label_key(label)
            self.db.execute('INSERT OR IGNORE INTO labels VALUES (?,?)', (key, label))
            self.db.execute('INSERT INTO note_labels VALUES (?,?)', (note.id, key))

    def ensure_recovered(self):
        if (self.path.parent/'annotation-restore.pending.json').exists():
            raise NotesError('Annotation restore recovery is pending. Reopen Bible before editing or exporting annotations.')

    def save(self, body, labels, *, existing=None, versification=None, start=None, end=None,
             origin_translation=None, origin_language=None):
        self.ensure_recovered()
        stamp = now()
        note = (replace(existing, body=body, labels=clean_labels(labels), modified=stamp,
                        revision=existing.revision + 1) if existing else
                Note(str(uuid.uuid4()), versification, start, end or start, origin_translation,
                     origin_language, body, clean_labels(labels), stamp, stamp))
        note = validate(note)
        with self.db:
            if existing:
                count = self.db.execute('DELETE FROM notes WHERE id=? AND revision=?',
                                        (existing.id, existing.revision)).rowcount
                if count != 1:
                    raise NoteConflict('This note changed elsewhere. Your draft has been preserved.')
            self._write(note)
            self._prune_labels()
            written = self.get(note.id)
        self.generation += 1
        return written

    def delete(self, note):
        self.ensure_recovered()
        with self.db:
            if self.db.execute('DELETE FROM notes WHERE id=? AND revision=?',
                               (note.id, note.revision)).rowcount != 1:
                raise NoteConflict('This note changed elsewhere. Your draft has been preserved.')
            self._prune_labels()
        self.generation += 1

    def _prune_labels(self):
        self.db.execute('DELETE FROM labels WHERE key NOT IN (SELECT label_key FROM note_labels)')

    def passage(self, versification, start, end=None):
        first, last = parts(start), parts(end or start)
        return [note for note in self.all() if note.versification == versification
                and parts(note.start)[0] == first[0] == last[0] == parts(note.end)[0]
                and parts(note.start)[1:] <= last[1:] and parts(note.end)[1:] >= first[1:]]

    def search(self, query='', labels=(), order='recent'):
        keys = {label_key(value) for value in labels}
        words = [normalized(word) for word in query.split() if normalized(word)]
        result = []
        for note in self.all():
            book, chapter, verse = parts(note.start)
            haystack = normalized(' '.join((note.body, note.start, note.end,
                f'{FRENCH.get(book, book)} {chapter}:{verse}', note.origin_translation,
                note.versification, *note.labels)))
            if keys <= {label_key(label) for label in note.labels} and all(word in haystack for word in words):
                result.append(note)
        if order == 'bible':
            result.sort(key=lambda n: (BOOK_ORDER.get(parts(n.start)[0], 10000), parts(n.start),
                                       n.versification, n.created, n.id))
        elif order in {'recent', 'oldest'}:
            result.sort(key=lambda n: (datetime.fromisoformat(n.modified), n.id), reverse=order == 'recent')
        else:
            raise NotesError('Invalid notes sort order')
        return result

    def export(self, destination):
        self.ensure_recovered()
        destination = Path(destination)
        if destination.resolve() == self.path.resolve() or (destination.exists() and os.path.samefile(destination, self.path)):
            raise NotesError('Choose a backup file different from the notes database')
        content = json.dumps({'format': 'bible-notes', 'version': 1,
                              'notes': [asdict(note) for note in self.all()]}, ensure_ascii=False).encode('utf-8')
        if len(content) > MAX_BACKUP:
            raise NotesError('Notes backup exceeds the 32 MiB limit')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.notes-backup-', delete=False) as output:
                temporary = Path(output.name)
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def restore(self, source):
        self.ensure_recovered()
        with Path(source).open('rb') as stream:
            data = stream.read(MAX_BACKUP + 1)
        if len(data) > MAX_BACKUP:
            raise NotesError('Notes backup exceeds the 32 MiB limit')
        try:
            value = json.loads(data)
            if (not isinstance(value, dict) or value.get('format') != 'bible-notes'
                    or type(value.get('version')) is not int or value['version'] != 1
                    or not isinstance(value['notes'], list)):
                raise NotesError('Invalid notes backup format')
            notes = [validate(Note(**item)) for item in value['notes']]
            if len({note.id for note in notes}) != len(notes):
                raise NotesError('Duplicate note identifiers in backup')
        except (ValueError, TypeError, KeyError, RecursionError) as error:
            raise NotesError(f'Invalid notes backup: {error}') from error
        def signature(note):
            return tuple((key, json.dumps(value, ensure_ascii=False, sort_keys=True))
                         for key, value in asdict(note).items() if key not in {'id', 'revision'})
        added = skipped = conflicts = 0
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            existing = self.all()
            identifiers = {note.id for note in existing}
            signatures = {signature(note) for note in existing}
            for note in notes:
                sign = signature(note)
                if sign in signatures:
                    skipped += 1
                    continue
                if note.id in identifiers:
                    note = replace(note, id=str(uuid.uuid4()), revision=1)
                    conflicts += 1
                self._write(note)
                identifiers.add(note.id)
                signatures.add(sign)
                added += 1
        self.generation += 1
        return added, skipped, conflicts

    def close(self):
        self.db.close()
