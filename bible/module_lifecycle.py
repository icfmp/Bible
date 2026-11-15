"""Journaled, source-preserving operations on one application-owned SWORD root.

Resource bytes come exclusively from the existing Library installer. Native
directory exchange keeps the old complete tree available until the new complete
tree replaces it. Unsupported filesystems/platforms refuse replacement safely.
"""
from contextlib import contextmanager
import ctypes
import errno
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time
import uuid
import weakref
from .providers import module_name
from .study_catalogue import atomic_write

LEASE_TIMEOUT=5
_changing=set()


def changing(root,value):
    root=Path(root).resolve()
    if value:_changing.add(root)
    else:_changing.discard(root)


def reader_lease(reader,root):
    """One lifetime lease, with no per-verse/scroll work or permanent timer."""
    if Path(root).resolve() in _changing:raise ValueError('This resource is being changed. Try again shortly.')
    try:import fcntl
    except ImportError:return
    try:fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
    except OSError as error:raise ValueError('SWORD resource directory is unavailable') from error
    try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
    except OSError as error:
        os.close(fd)
        if error.errno in (errno.ENOSYS,errno.EOPNOTSUPP):return
        raise ValueError('This resource is being changed. Try again shortly.') from error
    weakref.finalize(reader,os.close,fd)


@contextmanager
def mutation_lease(root,cancelled=lambda:False,*,timeout=None):
    """A still-running native consumer prevents replacement instead of racing it."""
    import fcntl
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY);deadline=time.monotonic()+(LEASE_TIMEOUT if timeout is None else timeout)
    try:
        while True:
            if cancelled():raise InterruptedError('Module operation cancelled')
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=deadline:
                    raise ValueError('The resource is still in use. Its installed files were preserved; try again after the current operation finishes.') from None
                time.sleep(.025)
        yield
    finally:os.close(fd)


def collect_readers(*_):
    # Headless callers have no GTK owners. GUI callers supply a main-thread
    # quiescence callback, which also collects disposed native-reader cycles.
    import gc
    gc.collect()


def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


@contextmanager
def operation_lock(root):
    try:import fcntl
    except ImportError:raise OSError('Native module-operation locking is unavailable on this platform') from None
    root=Path(root)
    if root.stat().st_uid!=os.getuid():
        raise ValueError('Shared or externally managed libraries cannot be changed safely')
    # Lock the existing directory inode: no stale lock file, unsafe unlink
    # race or additional user-profile file on a cancelled initial install.
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another module operation is already running') from None
        yield
    finally:os.close(fd)


def exchange(left,right):
    """Linux renameat2(RENAME_EXCHANGE): no missing or half-installed interval."""
    library=ctypes.CDLL(None,use_errno=True)
    function=getattr(library,'renameat2',None)
    if function is None:raise OSError('Atomic module replacement is unavailable on this platform')
    function.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    function.restype=ctypes.c_int
    if function(-100,os.fsencode(left),-100,os.fsencode(right),2)!=0:
        code=ctypes.get_errno()
        raise OSError(code,'Atomic module replacement failed; the installed module was retained')
    sync_directory(Path(left).parent);sync_directory(Path(right).parent)


def tree_manifest(root):
    from .library import file_sha256
    result={}
    if root.is_symlink() or not root.is_dir():raise ValueError('Invalid module directory')
    for path in root.rglob('*'):
        mode=path.lstat().st_mode
        if stat.S_ISDIR(mode):continue
        if not stat.S_ISREG(mode):raise ValueError('Module contains links or special files')
        result[str(path.relative_to(root))]=file_sha256(path)
    return result


class ModuleLifecycle:
    def __init__(self,library):
        self.library=library;self.root=library.root;self.transactions=self.root/'.transactions'

    def owned(self,identifier,*,unchanged=False):
        from .library import config,safe_path,source_fingerprints
        module_name(identifier)
        if self.root.is_symlink():raise ValueError('An aliased/shared library cannot be changed safely')
        root=self.root/identifier
        if root.is_symlink() or not root.is_dir():raise ValueError('External or missing module cannot be changed safely')
        marker=root/'.complete';receipt=root/'.source.json'
        if marker.is_symlink() or marker.stat().st_size>200 or marker.read_text()!=identifier:
            raise ValueError('This module has no verified application ownership marker')
        if receipt.exists() and (receipt.is_symlink() or receipt.stat().st_size>4*1024*1024):
            raise ValueError('Invalid module source receipt; files were preserved')
        resource=self.library.resource(identifier)
        files=list((root/'mods.d').glob('*.conf'))
        if len(files)!=1:raise ValueError('Module configuration is ambiguous')
        section=config(files[0].read_bytes())[resource.name]
        data=safe_path(section.get('DataPath',''))
        if not data.parts or data.parts[0]!='modules':raise ValueError('Unsafe module data path')
        relative_conf=str(files[0].relative_to(root));prefix=str(data)
        directory=(root.joinpath(*data.parts)).is_dir()
        manifest=tree_manifest(root)
        original=json.loads(receipt.read_text()).get('files_sha256',{}) if receipt.is_file() else {}
        if not isinstance(original,dict):original={}
        # Existing YouVersion installs carry application verification/reference
        # sidecars. Their separate retained reference registry is never removed.
        sidecars={'.source-index.json','.verified.json','.source-versification','.source-addresses.json'} if resource.provider_id=='youversion' else set()
        for relative in manifest:
            if relative in {'.complete','.source.json',relative_conf}:continue
            if relative in sidecars:continue
            # Some standard dictionary packages include companion files beside
            # the indexed basename. Accept only files actually recorded by the
            # original installer, with unchanged bytes; never a name exception.
            if original.get(relative)==manifest[relative]:continue
            if directory and relative.startswith(prefix+'/'):continue
            path=Path(relative)
            if not directory and str(path.parent)==str(data.parent) and path.name.startswith(data.name+'.'):continue
            raise ValueError('Additional local files prevent safe module management')
        if unchanged:
            receipt=root/'.source.json'
            if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size>4*1024*1024:
                raise ValueError('Original package fingerprints are unavailable; the installed module was preserved')
            expected=json.loads(receipt.read_text()).get('files_sha256')
            if not isinstance(expected,dict) or not expected:
                raise ValueError('Original package fingerprints are unavailable; the installed module was preserved')
            if expected!=source_fingerprints(root):
                raise ValueError('Local module changes were detected; the installed module was preserved')
        return resource,manifest

    def journal(self,folder,record):
        atomic_write(folder/'journal.json',json.dumps(record).encode())
        sync_directory(folder)

    def begin(self,identifier,operation,before):
        self.transactions.mkdir(exist_ok=True)
        if self.transactions.is_symlink():raise ValueError('Invalid transaction directory')
        folder=self.transactions/uuid.uuid4().hex;folder.mkdir()
        record=dict(format=1,resource=identifier,operation=operation,state='staging',before=before,
                    created=datetime.now(timezone.utc).isoformat())
        self.journal(folder,record)
        return folder,record

    def switch(self,folder,record,active,backup,*,rollback=False,cancelled=lambda:False):
        original=record['after'] if rollback else record['before']
        target=record['before'] if rollback else record['after']
        # Lease both directory inodes. A fresh reader cannot enter the new
        # path between exchange and journal commit/recovery either.
        with mutation_lease(active,cancelled),mutation_lease(backup,cancelled):
            if tree_manifest(active)!=original or tree_manifest(backup)!=target:
                raise ValueError('Module files changed before the atomic switch; both copies were preserved')
            try:
                exchange(active,backup)
                record['state']='rolled-back' if rollback else 'committed'
                self.journal(folder,record)
            except BaseException:
                actual=tree_manifest(active);saved=tree_manifest(backup)
                if actual==target and saved==original:exchange(active,backup)
                elif not (actual==original and saved==target):
                    raise ValueError('Module recovery found local changes; both copies were preserved')
                record['state']='committed' if rollback else 'recovered'
                self.journal(folder,record)
                raise

    def records(self):
        if not self.transactions.exists():return
        if self.transactions.is_symlink():raise ValueError('Invalid transaction directory')
        for folder in self.transactions.iterdir():
            if not re.fullmatch('[0-9a-f]{32}',folder.name) or folder.is_symlink() or not folder.is_dir():
                raise ValueError('Unrecognized module transaction; files were preserved')
            path=folder/'journal.json'
            if path.is_symlink() or path.stat().st_size>4*1024*1024:raise ValueError('Invalid module journal')
            record=json.loads(path.read_text())
            if not isinstance(record,dict) or type(record.get('format')) is not int or record['format']!=1:raise ValueError('Invalid module journal')
            module_name(record['resource'])
            if record.get('operation') not in ('update','remove'):raise ValueError('Invalid module operation')
            yield folder,record

    def prune(self,identifier,keep=None):
        errors=[]
        for folder,record in list(self.records() or ()):
            if folder==keep or record['resource']!=identifier or record['state'] in ('staging','prepared','rollback-prepared'):continue
            try:
                if any(p.name not in ('journal.json','backup','candidate') for p in folder.iterdir()):
                    raise ValueError('Additional local transaction files were preserved')
                backup=folder/'backup'
                if backup.exists() and tree_manifest(backup) not in (record['before'],record.get('after')):
                    raise ValueError('A locally changed stored version was preserved')
                candidate=folder/'candidate'
                if candidate.exists() and any(candidate.iterdir()):
                    raise ValueError('Unexpected staging files were preserved')
                shutil.rmtree(folder)
            except (OSError,ValueError) as error:errors.append(str(error))
        return tuple(errors)

    def update(self,resource,progress=lambda done,total:None,*,cancelled=lambda:False,installing=lambda:None,before_switch=collect_readers):
        from .library import Library
        from .module_updates import applicable_update
        with operation_lock(self.root):
            self.ready()
            old,before=self.owned(resource.id,unchanged=True)
            state=applicable_update(old,resource)
            if state!='available':raise ValueError('No verified same-edition update: '+state)
            folder,record=self.begin(resource.id,'update',before)
            active=self.root/resource.id;backup=folder/'backup'
            try:
                stage=Library(folder/'candidate')
                stage.install(resource,progress,installing=installing,cancelled=cancelled)
                self.verify_references(old,resource,stage.root/resource.id)
                os.rename(stage.root/resource.id,backup)
                record.update(state='prepared',after=tree_manifest(backup));self.journal(folder,record)
                if cancelled():raise InterruptedError('Module update cancelled')
                if tree_manifest(active)!=before:raise ValueError('Installed module changed during download')
                before_switch(resource.id)
                self.switch(folder,record,active,backup,cancelled=cancelled)
            except BaseException:
                self.recover_record(folder,record)
                if record['state'] in ('staging','recovered') and folder.exists():shutil.rmtree(folder)
                raise
            record['cleanup_errors']=self.prune(resource.id,folder)
            return record

    def verify_references(self,old,new,candidate):
        from .sword_provider import Reader,CommentaryReader
        # The shared installer already validated the dictionary in a bounded
        # native subprocess; it has no verse-address coverage to migrate.
        if old.kind in ('dictionary','general'):return
        factory=CommentaryReader if old.kind=='commentary' else Reader
        previous=factory(self.root/old.id,old.name);next_reader=factory(candidate,new.name)
        # A resource update must not silently remove/renumber existing Bible
        # addresses. Commentary sections can legitimately be expanded; their
        # native versification has already been checked against the catalogue.
        if old.kind=='bible':
            expected=[(b.code,b.chapters) for b in previous.books]
            actual={b.code:b.chapters for b in next_reader.books}
            for code,chapters in expected:
                if code not in actual or any(not set(verses)<=set(actual[code].get(chapter,())) for chapter,verses in chapters.items()):
                    raise ValueError('Candidate changes existing reference coverage; no automatic migration is available')

    def rollback_candidate(self,identifier):
        for folder,record in sorted(self.records() or (),key=lambda item:item[1].get('created',''),reverse=True):
            if record['resource']==identifier and record['operation']=='update' and record['state']=='committed':
                return folder,record
        return None

    def ready(self):
        """An incomplete/unknown ledger cannot authorize another mutation."""
        try:records=list(self.records() or ())
        except (OSError,ValueError,TypeError,KeyError):
            raise ValueError('Module recovery metadata is unavailable. Installed files were preserved.') from None
        if any(record.get('state') not in ('staging','prepared','rollback-prepared','committed','rolled-back','recovered')
               or not isinstance(record.get('before'),dict)
               or record['operation']=='update' and record.get('state')!='staging' and not isinstance(record.get('after'),dict)
               for _,record in records):
            raise ValueError('Module recovery metadata is invalid. Installed files were preserved.')
        if any(record.get('state') in ('staging','prepared','rollback-prepared') for _,record in records):
            raise ValueError('An interrupted module operation requires recovery. Installed files were preserved.')

    def was_removed(self,identifier):
        """Explicit app removal must not trigger the legacy missing-file fallback."""
        if not identifier or (self.root/identifier/'.complete').is_file():return False
        try:
            return any(record['resource']==identifier and record['operation']=='remove' and record['state']=='committed'
                       for _,record in self.records() or ())
        except (OSError,ValueError,TypeError,KeyError):
            # Do not guess another Bible when an interrupted operation's intent
            # cannot be read. Keep the saved missing resource/reference.
            return True

    def removed_resources(self):
        """Retain source attribution for an explicit offline Download again."""
        from .library import Resource
        from .providers import BY_ID
        result={}
        try:records=sorted(self.records() or (),key=lambda item:item[1].get('created',''))
        except (OSError,ValueError,TypeError,KeyError):return result
        for _,record in records:
            if record['operation']!='remove' or record['state']!='committed':continue
            if (self.root/record['resource']/'.complete').exists():continue
            metadata=record.get('resource_metadata')
            if not isinstance(metadata,dict):continue
            try:
                resource=Resource(**metadata);provider=BY_ID[resource.provider_id]
                if resource.id==record['resource'] and (resource.source,resource.source_url)==(provider.name,provider.url):
                    result[resource.id]=resource
            except (KeyError,TypeError,ValueError):continue
        return result

    def rollback(self,identifier,*,before_switch=collect_readers):
        with operation_lock(self.root):
            self.ready()
            self.owned(identifier)
            value=self.rollback_candidate(identifier)
            if value is None:raise ValueError('No previous version is available')
            folder,record=value;active=self.root/identifier;backup=folder/'backup'
            if tree_manifest(active)!=record['after'] or tree_manifest(backup)!=record['before']:
                raise ValueError('Local changes prevent a safe rollback; files were preserved')
            record['state']='rollback-prepared';self.journal(folder,record)
            try:
                before_switch(identifier)
                self.switch(folder,record,active,backup,rollback=True)
            except BaseException:
                self.recover_record(folder,record);raise
            return record

    def remove(self,identifier,*,before_switch=collect_readers):
        with operation_lock(self.root):
            self.ready()
            resource,before=self.owned(identifier)
            if resource.locked:
                raise ValueError('Encrypted-module credentials cannot be removed safely by this version; the module was preserved')
            folder,record=self.begin(identifier,'remove',before)
            from dataclasses import asdict
            record['resource_metadata']=asdict(resource)
            active=self.root/identifier;backup=folder/'backup'
            record['state']='prepared';self.journal(folder,record)
            try:
                if tree_manifest(active)!=before:raise ValueError('Module changed during removal')
                before_switch(identifier)
                with mutation_lease(active):
                    os.rename(active,backup);sync_directory(self.root);sync_directory(folder)
                record['state']='committed';self.journal(folder,record)
            except BaseException:
                # A failed commit write/fsync must restore the still-owned
                # source now, not leave it absent until application restart.
                record['state']='prepared'
                self.recover_record(folder,record)
                if record['state']=='recovered' and folder.exists():shutil.rmtree(folder)
                raise
            error=''
            try:shutil.rmtree(backup)
            except OSError as failure:error=str(failure)
            if active.exists():raise ValueError('The selected module is still installed')
            errors=self.prune(identifier,folder)
            return dict(removed=True,cleanup_error='\n'.join((error,*errors)).strip())

    def recover_record(self,folder,record):
        active=self.root/record['resource'];backup=folder/'backup';state=record['state']
        if state=='staging':
            tree_manifest(folder)  # Reject links/special files before discarding private staging.
            shutil.rmtree(folder);return
        if record['operation']=='remove':
            if state=='prepared':
                if backup.exists():
                    if active.exists():raise ValueError('A different module now occupies the removed path; recovery preserved both copies')
                    if tree_manifest(backup)!=record['before']:raise ValueError('Recovery copy changed; manual recovery is required')
                    os.rename(backup,active);sync_directory(self.root)
                elif not active.exists() or tree_manifest(active)!=record['before']:
                    raise ValueError('Removal recovery found changed or missing files; manual recovery is required')
                record['state']='recovered';self.journal(folder,record)
            return
        if state not in ('prepared','rollback-prepared'):return
        if not active.is_dir() or not backup.is_dir():raise ValueError('Module recovery requires both complete copies; files were preserved')
        actual=tree_manifest(active);saved=tree_manifest(backup)
        original=record['after'] if state=='rollback-prepared' else record['before']
        target=record['before'] if state=='rollback-prepared' else record['after']
        if actual==target and saved==original:
            with mutation_lease(active,timeout=0),mutation_lease(backup,timeout=0):exchange(active,backup)
        elif not (actual==original and saved==target):
            raise ValueError('Module recovery found local changes; both copies were preserved')
        record['state']='committed' if state=='rollback-prepared' else 'recovered'
        self.journal(folder,record)

    def recover(self):
        if not self.transactions.exists():return ()
        errors=[]
        try:
            with operation_lock(self.root):
                for folder,record in self.records():
                    try:self.recover_record(folder,record)
                    except (OSError,ValueError,KeyError,TypeError) as error:errors.append(str(error))
        except (OSError,ValueError,KeyError,TypeError) as error:errors.append(str(error))
        return tuple(errors)
