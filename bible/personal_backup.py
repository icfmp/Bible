"""Validated annotation-only snapshots and recoverable two-store merge restores.

The recovery record is scoped to a deliberate restore, independently of storage versions.
"""
from dataclasses import asdict,replace
import hashlib,json,os,tempfile,uuid
from pathlib import Path
from .notes import Note,validate,BACKUP_VERSION
from .highlights import (decode as decode_marks, write as write_marks, merge as merge_marks,
                         encoded as encode_marks, private_backup)

BACKUP_VERSION_COMBINED = 3
LIMIT=48*1024*1024


def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.annotation-backup-',delete=False) as f:
            temporary=Path(f.name);f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temporary,path)
        descriptor=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    finally:
        if temporary:temporary.unlink(missing_ok=True)


def retire(marker):
    # Persist the highlight rename before retiring the cross-store journal,
    # then persist its removal before allowing subsequent annotation edits.
    descriptor=os.open(marker.parent,os.O_RDONLY)
    try:
        os.fsync(descriptor);marker.unlink();os.fsync(descriptor)
    finally:os.close(descriptor)


def decode(data):
    """Validate supported note/highlight/combined backups without touching stores.

    Notes-only versions 1/2 retain their existing contract. Combined version 3
    carries highlight v2 metadata; combined 1/2 carries legacy highlight fields.
    """
    if len(data)>LIMIT:raise ValueError('Personal backup exceeds the size limit')
    value=json.loads(data)
    if isinstance(value,dict) and set(value)=={'format','version','notes'} and value['format']=='bible-notes':
        if len(data)>32*1024*1024:raise ValueError('Legacy notes backup exceeds the size limit')
        if type(value['version']) is not int or value['version'] not in (1,BACKUP_VERSION):
            raise ValueError('Unsupported notes backup format')
        value={**value,'format':'bible-personal-annotations','highlights':[]}
    elif isinstance(value,dict) and set(value)=={'version','marks'}:
        marks=decode_marks(value)
        return [],marks
    if (not isinstance(value,dict) or set(value)!={'format','version','notes','highlights'}
            or value['format']!='bible-personal-annotations' or type(value['version']) is not int
            or value['version'] not in (1,2,BACKUP_VERSION_COMBINED)
            or not isinstance(value['notes'],list) or not isinstance(value['highlights'],list)):
        raise ValueError('Unsupported personal backup format')
    try:notes=[validate(Note(**item)) for item in value['notes']]
    except (TypeError,KeyError) as error:raise ValueError('Invalid notes in personal backup') from error
    if len({n.id for n in notes})!=len(notes):raise ValueError('Duplicate note identifiers in backup')
    if value['version']==1 and any(n.links for n in notes):raise ValueError('Linked passages require backup version 2')
    marks=decode_marks(dict(version=2 if value['version']==3 else 1,marks=value['highlights']))
    return notes,marks


def _snapshot_locked(notes,highlights):
    """Serialize under the caller's SQLite write transaction and highlight lock."""
    notes.ensure_recovered();highlights.check_current()
    value=dict(format='bible-personal-annotations',version=BACKUP_VERSION_COMBINED,
               notes=[asdict(n) for n in notes.all()],highlights=list(highlights.entries.values()))
    data=json.dumps(value,ensure_ascii=False).encode();decode(data);return data


def snapshot(notes,highlights):
    """Take a consistent annotation-only snapshot, excluding resources/settings."""
    with notes.db:
        notes.db.execute('BEGIN IMMEDIATE')
        with highlights.locked():
            return _snapshot_locked(notes,highlights)


def export(notes,highlights,destination):
    """Write and validate a private combined v3 backup to a separate file."""
    destination=Path(destination)
    if destination.resolve() in (notes.path.resolve(),highlights.path.resolve()):raise ValueError('Choose a separate backup file')
    atomic(destination,snapshot(notes,highlights))
    decode(destination.read_bytes())


def recover(notes,highlights):
    """Repeatably restore both original stores after an interrupted restore.

    The durable marker remains until both stores and its retirement are synced.
    Normal note autosave and highlight writes refuse edits while it exists.
    """
    marker=notes.path.parent/'annotation-restore.pending.json'
    if not marker.exists():return False
    if highlights.error:raise ValueError('Highlights cannot be validated during recovery. Original file preserved.')
    with notes.db:
        notes.db.execute('BEGIN IMMEDIATE')
        with highlights.locked():
            if not marker.exists():return False
            record=json.loads(marker.read_text())
            if not isinstance(record,dict) or set(record)!={'backup','sha256'} or not isinstance(record['backup'],str) or not record['backup'].startswith('before-restore-') or '/' in record['backup'] or '\\' in record['backup']:raise ValueError('Invalid restore recovery record')
            backup=notes.path.parent/'backups'/record['backup']
            data=backup.read_bytes()
            if hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('Restore recovery backup changed')
            originals,marks=decode(data)
            notes.db.execute('DELETE FROM notes');notes.db.execute('DELETE FROM labels')
            for note in originals:notes._write(note)
            write_marks(highlights.path,marks)
        # Commit SQLite before retiring the marker. Other writers still refuse
        # edits during this gap, and a crash repeats this exact recovery.
    highlights.entries=marks;highlights.error='';highlights.accept_disk()
    retire(marker);notes.generation+=1;return True


def restore(notes,highlights,source):
    """Merge fully validated input, retaining all rejected highlight records.

    SQLite's write transaction excludes concurrent note autosave; the advisory
    highlight lock and stale-write token exclude other app instances. On a
    failure after journaling, recover both original stores before allowing edits.
    """
    source=Path(source)
    with source.open('rb') as f:imported,marks=decode(f.read(LIMIT+1))
    marker=notes.path.parent/'annotation-restore.pending.json'
    added=skipped=conflicts=0;conflict_backup=''
    def signature(n):return json.dumps({k:v for k,v in asdict(n).items() if k not in ('id','revision')},sort_keys=True)
    try:
        with notes.db:
            notes.db.execute('BEGIN IMMEDIATE')
            with highlights.locked():
                original=_snapshot_locked(notes,highlights)
                backup=notes.path.parent/'backups'/('before-restore-'+uuid.uuid4().hex+'.json')
                atomic(backup,original)
                if backup.read_bytes()!=original:raise ValueError('Unable to verify pre-restore backup')
                merged,rejected=merge_marks(highlights.entries,marks)
                if rejected:
                    data=encode_marks(marks)
                    conflict_backup=str(private_backup(notes.path.parent/'backups'/('highlight-conflicts-'+hashlib.sha256(data).hexdigest()+'.json'),data))
                conflicts=len(rejected)
                atomic(marker,json.dumps(dict(backup=backup.name,sha256=hashlib.sha256(original).hexdigest())).encode())
                existing=notes.all();ids={n.id for n in existing};signatures={signature(n) for n in existing}
                for note in imported:
                    sign=signature(note)
                    if sign in signatures:skipped+=1;continue
                    if note.id in ids:note=replace(note,id=str(uuid.uuid4()),revision=1);conflicts+=1
                    notes._write(note);ids.add(note.id);signatures.add(sign);added+=1
                write_marks(highlights.path,merged)
        highlights.entries=merged;highlights.accept_disk();notes.generation+=1;retire(marker)
    except Exception:
        if marker.exists():recover(notes,highlights)
        raise
    return dict(added_notes=added,skipped_notes=skipped,conflicts=conflicts,backup=str(backup),highlight_conflicts_backup=conflict_backup)
