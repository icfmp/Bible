"""Validated annotation-only snapshots and recoverable two-store merge restores.

No schema migration: the recovery record is scoped to a deliberate restore.
"""
from dataclasses import asdict,replace
import hashlib,json,os,tempfile,uuid
from pathlib import Path
from .notes import Note,validate
from .highlights import payload as read_marks,write as write_marks

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


def decode(data):
    if len(data)>LIMIT:raise ValueError('Personal backup exceeds the size limit')
    value=json.loads(data)
    if isinstance(value,dict) and set(value)=={'format','version','notes'} and value['format']=='bible-notes':
        if len(data)>32*1024*1024:raise ValueError('Legacy notes backup exceeds the size limit')
        value={**value,'format':'bible-personal-annotations','highlights':[]}
    elif isinstance(value,dict) and set(value)=={'version','marks'}:
        value=dict(format='bible-personal-annotations',version=value['version'],notes=[],highlights=value['marks'])
    if (not isinstance(value,dict) or set(value)!={'format','version','notes','highlights'}
            or value['format']!='bible-personal-annotations' or type(value['version']) is not int or value['version']!=1
            or not isinstance(value['notes'],list) or not isinstance(value['highlights'],list)):
        raise ValueError('Unsupported personal backup format')
    try:notes=[validate(Note(**item)) for item in value['notes']]
    except (TypeError,KeyError) as error:raise ValueError('Invalid notes in personal backup') from error
    if len({n.id for n in notes})!=len(notes):raise ValueError('Duplicate note identifiers in backup')
    # Reuse the established strict highlight validator, never a permissive importer.
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'marks.json';path.write_text(json.dumps(dict(version=1,marks=value['highlights'])))
        marks=read_marks(path)
    return notes,marks


def snapshot(notes,highlights):
    if highlights.error:raise ValueError('Original highlights file preserved; cannot export an incomplete backup')
    with notes.db:
        notes.db.execute('BEGIN IMMEDIATE')
        value=dict(format='bible-personal-annotations',version=1,notes=[asdict(n) for n in notes.all()],highlights=list(highlights.entries.values()))
        if highlights.path.exists() and read_marks(highlights.path)!=highlights.entries:
            raise ValueError('Highlights changed elsewhere. Reopen Bible before continuing.')
        data=json.dumps(value,ensure_ascii=False).encode();decode(data);return data


def export(notes,highlights,destination):
    destination=Path(destination)
    if destination.resolve() in (notes.path.resolve(),highlights.path.resolve()):raise ValueError('Choose a separate backup file')
    atomic(destination,snapshot(notes,highlights))
    decode(destination.read_bytes())


def recover(notes,highlights):
    marker=notes.path.parent/'annotation-restore.pending.json'
    if not marker.exists():return False
    record=json.loads(marker.read_text())
    if not isinstance(record,dict) or set(record)!={'backup','sha256'} or not isinstance(record['backup'],str) or not record['backup'].startswith('before-restore-') or '/' in record['backup'] or '\\' in record['backup']:raise ValueError('Invalid restore recovery record')
    backup=notes.path.parent/'backups'/record['backup']
    if backup.name!=record['backup']:raise ValueError('Invalid restore recovery path')
    data=backup.read_bytes()
    if hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('Restore recovery backup changed')
    originals,marks=decode(data)
    with notes.db:
        notes.db.execute('BEGIN IMMEDIATE');notes.db.execute('DELETE FROM notes');notes.db.execute('DELETE FROM labels')
        for note in originals:notes._write(note)
        write_marks(highlights.path,marks)
    highlights.entries=marks;highlights.error='';marker.unlink();notes.generation+=1;return True


def restore(notes,highlights,source):
    # Validate *all* input before touching stores or creating a recovery record.
    source=Path(source)
    with source.open('rb') as f:imported,marks=decode(f.read(LIMIT+1))
    original=snapshot(notes,highlights)
    backup=notes.path.parent/'backups'/('before-restore-'+uuid.uuid4().hex+'.json')
    atomic(backup,original)
    if snapshot(notes,highlights)!=backup.read_bytes():raise ValueError('Unable to verify pre-restore backup')
    marker=notes.path.parent/'annotation-restore.pending.json'
    atomic(marker,json.dumps(dict(backup=backup.name,sha256=hashlib.sha256(original).hexdigest())).encode())
    added=skipped=conflicts=0
    def signature(n):return json.dumps({k:v for k,v in asdict(n).items() if k not in ('id','revision')},sort_keys=True)
    try:
        with notes.db:
            notes.db.execute('BEGIN IMMEDIATE');existing=notes.all();ids={n.id for n in existing}
            signatures={signature(n) for n in existing}
            for note in imported:
                sign=signature(note)
                if sign in signatures:skipped+=1;continue
                if note.id in ids:note=replace(note,id=str(uuid.uuid4()),revision=1);conflicts+=1
                notes._write(note);ids.add(note.id);signatures.add(sign);added+=1
            merged=dict(highlights.entries)
            for key,mark in marks.items():
                if key in merged and merged[key]!=mark:conflicts+=1
                else:merged[key]=mark
            write_marks(highlights.path,merged)
        highlights.entries=merged;notes.generation+=1;marker.unlink()
    except Exception:
        # Rollback is repeatable after a process interruption; retain marker
        # until both original stores have been recovered successfully.
        recover(notes,highlights)
        raise
    return dict(added_notes=added,skipped_notes=skipped,conflicts=conflicts,backup=str(backup))
