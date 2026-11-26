"""Whole-verse highlights with stable identity and recoverable local migration.

The passage index enforces one mark per numbering system/reference. UUIDs are
independent of that index, colors and resource context; notes remain separate.
"""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from .notes import now, parts
from .providers import RESOURCE_ID

COLORS = {'yellow': ('#f6cd45', 'Yellow'), 'green': ('#79c793', 'Green'), 'blue': ('#7bb2e8', 'Blue')}
SCHEMA_VERSION = 2
BACKUP_VERSION = 2
MAX_BYTES = 8 * 1024 * 1024
LEGACY_NAMESPACE = uuid.UUID('993f333f-8054-4d1a-87b2-d26fe52206fa')
LEGACY_FIELDS = {'system', 'reference', 'color', 'resource'}
FIELDS = LEGACY_FIELDS | {'id', 'created', 'modified', 'revision', 'origin_resource'}


def decode(value):
    """Validate a complete standalone payload before normalizing legacy marks.

    Legacy IDs depend only on the numbering system and canonical reference.
    Null legacy dates mean unknown, never the time of migration or import.
    Unknown fields/versions are rejected so an older writer cannot erase them.
    """
    if (not isinstance(value, dict) or set(value) != {'version', 'marks'}
            or type(value['version']) is not int or value['version'] not in (1, BACKUP_VERSION)
            or not isinstance(value['marks'], list)):
        raise ValueError('Unsupported highlights file')
    if len(value['marks']) > 50000:
        raise ValueError('Too many highlights')
    result = {}; ids = set()
    for item in value['marks']:
        expected = LEGACY_FIELDS if value['version'] == 1 else FIELDS
        if not isinstance(item, dict) or set(item) != expected:
            raise ValueError('Invalid highlight')
        mark = dict(item)
        if not all(isinstance(mark[k], str) for k in LEGACY_FIELDS):
            raise ValueError('Invalid highlight')
        parts(mark['reference'])
        if (not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', mark['system']) or mark['color'] not in COLORS
                or len(mark['resource']) > 256 or not re.fullmatch(RESOURCE_ID, mark['resource'])):
            raise ValueError('Invalid highlight')
        key = (mark['system'], mark['reference'])
        if value['version'] == 1:
            mark.update(id=str(uuid.uuid5(LEGACY_NAMESPACE, json.dumps(key))), created=None,
                        modified=None, revision=1, origin_resource=mark['resource'])
        try:
            if str(uuid.UUID(mark['id'])) != mark['id']:
                raise ValueError('Invalid highlight identifier')
            if type(mark['revision']) is not int or mark['revision'] < 1:
                raise ValueError('Invalid highlight revision')
            stamps = []
            for stamp in (mark['created'], mark['modified']):
                if stamp is None:
                    stamps.append(None)
                elif isinstance(stamp, str) and datetime.fromisoformat(stamp).utcoffset() is not None:
                    stamps.append(datetime.fromisoformat(stamp))
                else:
                    raise ValueError('Invalid highlight date')
            if stamps[0] is not None and (stamps[1] is None or stamps[1] < stamps[0]):
                raise ValueError('Invalid highlight date order')
            if (not isinstance(mark['origin_resource'], str) or len(mark['origin_resource']) > 256
                    or not re.fullmatch(RESOURCE_ID, mark['origin_resource'])):
                raise ValueError('Invalid highlight origin')
        except (TypeError, AttributeError) as error:
            raise ValueError('Invalid highlight metadata') from error
        if key in result or mark['id'] in ids:
            raise ValueError('Duplicate highlight passage or identifier')
        result[key] = mark; ids.add(mark['id'])
    return result


def read_bytes(path):
    """Read a bounded payload; the original file is never repaired implicitly."""
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Highlights file is too large')
    return data


def payload(path):
    """Return validated current records from a supported standalone format."""
    return decode(json.loads(read_bytes(path)))


def encoded(marks):
    """Serialize and validate the current portable highlight format."""
    value = dict(version=BACKUP_VERSION, marks=list(marks.values()))
    validated = decode(value)
    if validated != marks:
        raise ValueError('Invalid highlight passage index')
    data = json.dumps(value, ensure_ascii=False).encode()
    if len(data) > MAX_BYTES:
        raise ValueError('Highlights file is too large')
    return data


def sync_directory(path):
    """Persist a completed rename on POSIX; Windows has no directory fsync."""
    if os.name == 'nt':
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def private_backup(path, data):
    """Persist an immutable private safety copy, verifying any existing copy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.highlight-backup-', delete=False) as out:
            temporary = Path(out.name)
            out.write(data); out.flush(); os.fsync(out.fileno())
        if temporary.read_bytes() != data:
            raise ValueError('Unable to verify private highlight backup')
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    if path.read_bytes() != data or (os.name != 'nt' and path.stat().st_mode & 0o077):
        raise ValueError('Unable to verify private highlight backup')
    sync_directory(path.parent)
    sync_directory(path.parent.parent)
    return path


def write(path, marks):
    """Atomically write validated v2 records; callers serialize live edits."""
    data = encoded(marks)
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); temporary = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.highlights-', delete=False) as out:
            temporary = Path(out.name)
            out.write(data); out.flush(); os.fsync(out.fileno())
        os.replace(temporary, path); sync_directory(path.parent)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def merge(current, imported):
    """Keep local values on ID/passage collisions and return rejected records.

    Legacy imports identical to a current mark's original four fields are
    idempotent even after a new-format restore assigned another UUID. Other
    divergent IDs, content or revisions are recoverable conflicts, not winners
    inferred from timestamps. No distributed ordering is implemented.
    """
    merged = dict(current); ids = {m['id']: m for m in current.values()}; conflicts = {}
    for key, mark in imported.items():
        local = ids.get(mark['id']) or merged.get(key)
        if local is not None:
            legacy_id = str(uuid.uuid5(LEGACY_NAMESPACE, json.dumps(key)))
            identical_legacy = (mark['id'] == legacy_id and mark['created'] is None
                                and mark['modified'] is None
                                and all(mark[k] == local[k] for k in LEGACY_FIELDS))
            if mark != local and not identical_legacy:
                conflicts[key] = mark
            continue
        merged[key] = mark; ids[mark['id']] = mark
    return merged, conflicts


class HighlightStore:
    """Serialize local edits, reject stale writers and migrate only after backup.

    A nonblocking advisory lock prevents concurrent app instances from replacing
    each other's files. Lock order is SQLite transaction, then this lock when a
    combined restore touches both stores. A pending restore blocks ordinary
    edits/exports; startup recovery alone may replace that state.
    """
    def __init__(self, path):
        self.path = Path(path); self.entries = {}; self.error = ''; self._disk = None
        try:
            with self.locked():
                self._disk = self.disk_bytes()
                if self._disk is not None:
                    value = json.loads(self._disk); self.entries = decode(value)
                    if value['version'] == 1 and not self.pending.exists():
                        digest = hashlib.sha256(self._disk).hexdigest()
                        private_backup(self.path.parent / 'backups' / f'highlights-before-schema-2-{digest}.json', self._disk)
                        write(self.path, self.entries); self.accept_disk()
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
            self.error = str(error)

    @property
    def pending(self):
        """The existing two-store recovery marker, shared with notes."""
        return self.path.parent / 'annotation-restore.pending.json'

    @contextmanager
    def locked(self):
        """Take a short nonblocking cross-process lock without a retry loop."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path) + '.lock', os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if os.name == 'nt':
                import msvcrt
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b'\0'); os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def disk_bytes(self):
        """Return current bytes or None for a genuinely absent file."""
        try:
            return read_bytes(self.path)
        except FileNotFoundError:
            return None

    def accept_disk(self):
        """Refresh the write token only after this instance's successful write."""
        self._disk = self.disk_bytes()

    def check_current(self):
        """Reject stale or unreadable state instead of overwriting other edits."""
        self.ensure_recovered()
        if self.error:
            raise ValueError('Original highlights file preserved; repair it before saving')
        data = self.disk_bytes()
        if data != self._disk or (data is not None and decode(json.loads(data)) != self.entries):
            raise ValueError('Highlights changed elsewhere. Reopen Bible before continuing.')

    def ensure_recovered(self):
        """Block normal annotation writes while two-store recovery is pending."""
        if self.pending.exists():
            raise ValueError('Annotation restore recovery is pending. Reopen Bible before editing or exporting annotations.')

    def commit(self, marks):
        """Commit a complete validated state without losing a concurrent edit."""
        with self.locked():
            self.check_current(); write(self.path, marks)
            self.entries = marks; self.accept_disk()

    def set(self, system, references, color, resource):
        """Recolor in place, create UUIDs for new marks, or remove whole verses.

        No-op edits retain revision/date. Recreating a deleted mark gets a new
        UUID. Resource is the current context; origin_resource never changes.
        """
        if color is not None and color not in COLORS:
            raise ValueError('Invalid highlight color')
        if (not isinstance(system, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', system)
                or not isinstance(resource, str) or len(resource) > 256 or not re.fullmatch(RESOURCE_ID, resource)):
            raise ValueError('Invalid highlight')
        marks = dict(self.entries)
        for reference in references:
            parts(reference); key = (system, reference)
            if color is None:
                marks.pop(key, None)
            elif key in marks:
                old = marks[key]
                if old['color'] != color or old['resource'] != resource:
                    marks[key] = dict(old, color=color, resource=resource, modified=now(), revision=old['revision'] + 1)
            else:
                stamp = now()
                marks[key] = dict(system=system, reference=reference, color=color, resource=resource,
                                  origin_resource=resource, id=str(uuid.uuid4()), created=stamp, modified=stamp, revision=1)
        self.commit(marks)

    def backup(self, path):
        """Export current highlights to a separate, private v2 backup."""
        path = Path(path)
        if path.resolve() == self.path.resolve():
            raise ValueError('Choose a separate backup file')
        with self.locked():
            self.check_current(); write(path, self.entries)

    def restore(self, path):
        """Merge an old/current backup; retain rejected values in a private file."""
        imported = payload(path)
        with self.locked():
            self.check_current(); merged, conflicts = merge(self.entries, imported)
            recovery = None
            if conflicts:
                data = encoded(imported)
                recovery = private_backup(self.path.parent / 'backups' / ('highlight-conflicts-' + hashlib.sha256(data).hexdigest() + '.json'), data)
            write(self.path, merged); self.entries = merged; self.accept_disk()
        return dict(conflicts=len(conflicts), backup=str(recovery) if recovery else '')
