"""Local, versioned passage notes. No resource files, GTK, or network access."""
from dataclasses import asdict, dataclass, replace
from contextlib import closing
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

SCHEMA_VERSION = 2
BACKUP_VERSION = 2
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
            r'[1-5]?[A-Za-z][A-Za-z0-9]{0,15}\.[1-9][0-9]{0,2}(?:_[1-9][0-9]{0,2})?\.[1-9][0-9]{0,3}', reference):
        raise NotesError('Invalid passage reference')
    book, chapter, verse = reference.split('.')
    if int(verse)>2000:raise NotesError('Invalid passage reference')
    return book, chapter if '_' in chapter else int(chapter), int(verse)


def passage_order(reference):
    book,chapter,verse=parts(reference)
    values=str(chapter).split('_')
    return book,(int(values[0]),int(values[1]) if len(values)>1 else 0),verse


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
class PassageLink:
    versification: str
    start: str
    end: str


def validate_link(link):
    if isinstance(link,dict):link=PassageLink(**link)
    if not isinstance(link,PassageLink):raise NotesError('Invalid linked passage')
    first,last=passage_order(link.start),passage_order(link.end)
    if first[0]!=last[0] or first[1:]>last[1:]:raise NotesError('A linked passage must be ordered within one book')
    if not isinstance(link.versification,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',link.versification):
        raise NotesError('Invalid linked passage numbering')
    return link


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
    links: tuple[PassageLink,...] = ()

    @property
    def passages(self):return (PassageLink(self.versification,self.start,self.end),*self.links)

    def covers(self, reference):
        book, chapter, verse = passage_order(reference)
        return any(link.versification==self.versification and book==passage_order(link.start)[0]==passage_order(link.end)[0]
                   and passage_order(link.start)[1:]<=(chapter,verse)<=passage_order(link.end)[1:] for link in self.passages)


def validate(note):
    try:
        if str(uuid.UUID(note.id)) != note.id:
            raise ValueError('Invalid note identifier')
        first, last = passage_order(note.start), passage_order(note.end)
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
        if not isinstance(note.links,(list,tuple)) or len(note.links)>200:raise ValueError('Too many linked passages')
        primary=PassageLink(note.versification,note.start,note.end)
        links=tuple(dict.fromkeys(validate_link(link) for link in note.links))
        return replace(note, labels=clean_labels(note.labels),links=tuple(link for link in links if link!=primary))
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
            self._schema=version
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
                    self._create_passages()
                    self.db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
                self._schema=SCHEMA_VERSION
            elif version not in (1,SCHEMA_VERSION) or app != APPLICATION_ID:
                raise NotesError('Unsupported notes database. The original file has been preserved.')
            else:
                required={'notes','labels','note_labels'}|({'note_passages'} if version>=2 else set())
                if not required<={row[0] for row in tables}:
                    raise NotesError('Unsupported notes database. The original file has been preserved.')
            self.db.execute('PRAGMA foreign_keys=ON')
            if (self.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok'
                    or self.db.execute('PRAGMA foreign_key_check').fetchone() is not None):
                raise NotesError('Invalid notes database')
            self.all()  # Validate persisted records before allowing edits.
            if self._schema==1:
                # SQLite rolls the schema transaction back after interruption.
                # Take and verify a durable private snapshot under a write lock
                # before touching any existing schema or record.
                with self.db:
                    self.db.execute('BEGIN IMMEDIATE');self.all()
                    self._backup_before_migration()
                    self._create_passages()
                    self.db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
                self._schema=SCHEMA_VERSION
        except Exception:
            self.db.close()
            raise

    def _create_passages(self):
        self.db.execute('''CREATE TABLE note_passages (
            note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL, versification TEXT NOT NULL,
            start TEXT NOT NULL, end TEXT NOT NULL, PRIMARY KEY(note_id,ordinal),
            UNIQUE(note_id,versification,start,end))''')

    def _backup_before_migration(self):
        directory=self.path.parent/'backups';directory.mkdir(parents=True,exist_ok=True)
        descriptor,temporary=tempfile.mkstemp(dir=directory,prefix='.notes-schema-')
        os.close(descriptor);temporary=Path(temporary)
        destination=directory/('notes-before-schema-2-'+uuid.uuid4().hex+'.sqlite3')
        try:
            with closing(sqlite3.connect(self.path)) as source,closing(sqlite3.connect(temporary)) as backup:
                source.execute('PRAGMA query_only=ON');source.backup(backup)
                if (backup.execute('PRAGMA quick_check').fetchone()[0]!='ok'
                        or backup.execute('PRAGMA user_version').fetchone()[0]!=1
                        or backup.execute('PRAGMA application_id').fetchone()[0]!=APPLICATION_ID
                        or list(backup.iterdump())!=list(self.db.iterdump())):
                    raise NotesError('Unable to verify the notes migration backup')
            with temporary.open('rb') as stream:os.fsync(stream.fileno())
            os.replace(temporary,destination)
            descriptor=os.open(directory,os.O_RDONLY)
            try:os.fsync(descriptor)
            finally:os.close(descriptor)
        finally:temporary.unlink(missing_ok=True)

    def all(self):
        result = []
        for row in self.db.execute('SELECT * FROM notes'):
            labels = tuple(r[0] for r in self.db.execute('''SELECT labels.name FROM labels
                JOIN note_labels ON labels.key=note_labels.label_key WHERE note_id=? ORDER BY labels.key''', (row['id'],)))
            links=(tuple(PassageLink(*r) for r in self.db.execute('''SELECT versification,start,end
                FROM note_passages WHERE note_id=? ORDER BY ordinal''',(row['id'],))) if self._schema>=2 else ())
            result.append(validate(Note(**dict(row), labels=labels,links=links)))
        return result

    def get(self, identifier):
        return next((note for note in self.all() if note.id == identifier), None)

    def labels(self):
        return [r[0] for r in self.db.execute('SELECT name FROM labels ORDER BY key')]

    def _write(self, note):
        record = asdict(note)
        record.pop('labels')
        record.pop('links')
        keys = tuple(record)
        self.db.execute(f'INSERT INTO notes ({",".join(keys)}) VALUES ({",".join("?" for _ in keys)})',
                        tuple(record.values()))
        for label in note.labels:
            key = label_key(label)
            self.db.execute('INSERT OR IGNORE INTO labels VALUES (?,?)', (key, label))
            self.db.execute('INSERT INTO note_labels VALUES (?,?)', (note.id, key))
        for ordinal,link in enumerate(note.links):
            self.db.execute('INSERT INTO note_passages VALUES (?,?,?,?,?)',
                (note.id,ordinal,link.versification,link.start,link.end))

    def ensure_recovered(self):
        if (self.path.parent/'annotation-restore.pending.json').exists():
            raise NotesError('Annotation restore recovery is pending. Reopen Bible before editing or exporting annotations.')

    def save(self, body, labels, *, existing=None, versification=None, start=None, end=None,
             origin_translation=None, origin_language=None,links=None):
        self.ensure_recovered()
        stamp = now()
        note = (replace(existing, body=body, labels=clean_labels(labels), modified=stamp,
                        revision=existing.revision + 1) if existing else
                Note(str(uuid.uuid4()), versification, start, end or start, origin_translation,
                     origin_language, body, clean_labels(labels), stamp, stamp))
        if links is not None:note=replace(note,links=links)
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
        first, last = passage_order(start), passage_order(end or start)
        return [note for note in self.all() if any(link.versification==versification
                and parts(link.start)[0] == first[0] == last[0] == parts(link.end)[0]
                and passage_order(link.start)[1:]<=last[1:] and passage_order(link.end)[1:]>=first[1:]
                for link in note.passages)]

    def search(self, query='', labels=(), order='recent'):
        keys = {label_key(value) for value in labels}
        words = [normalized(word) for word in query.split() if normalized(word)]
        result = []
        for note in self.all():
            book, chapter, verse = parts(note.start)
            haystack = normalized(' '.join((note.body, note.start, note.end,
                f'{FRENCH.get(book, book)} {chapter}:{verse}', note.origin_translation,
                note.versification, *note.labels, *(part for link in note.links for part in (link.start,link.end,link.versification)))))
            if keys <= {label_key(label) for label in note.labels} and all(word in haystack for word in words):
                result.append(note)
        if order == 'bible':
            result.sort(key=lambda n: (BOOK_ORDER.get(parts(n.start)[0], 10000), passage_order(n.start),
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
        content = json.dumps({'format': 'bible-notes', 'version': BACKUP_VERSION,
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
                    or type(value.get('version')) is not int or value['version'] not in (1,BACKUP_VERSION)
                    or not isinstance(value['notes'], list)):
                raise NotesError('Invalid notes backup format')
            notes = [validate(Note(**item)) for item in value['notes']]
            if value['version']==1 and any(note.links for note in notes):
                raise NotesError('Linked passages require backup version 2')
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
