"""Small source-specific native indexes; no Scripture cache or inferred mapping."""
import ctypes
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

# Declared Paratext source conventions. These are not guesses from a title,
# language or the shape of a canon. A verified source index must independently
# match the complete declared convention before this capability is registered.
SOURCE_CONVENTIONS={'org':'Original','eng':'KJV'}
_reference_conventions={}


def reference_convention(system):
    return _reference_conventions.get(system)


def declared_convention(path,receipt):
    convention=SOURCE_CONVENTIONS.get(receipt.get('source_numbering'))
    if (not convention or receipt.get('source_addresses_sha256')
            or receipt.get('all_text_notes_headings_verified') is not True):return
    lines=path.read_text('ascii').splitlines();system=lines[0].removeprefix('BIBLE-VRS-1 ')
    if receipt.get('storage_numbering')!=system:return
    canon={}
    for line in lines[1:]:
        _,book,count,*maxima=line.split();canon[book]=list(map(int,maxima))
        if int(count)!=len(maxima):return
    from .versification_mapping import table
    declared=table(convention)
    if declared is None or canon!=declared['canon']:return
    return convention


def register_convention(path,receipt):
    system=path.read_text('ascii').splitlines()[0].removeprefix('BIBLE-VRS-1 ')
    convention=declared_convention(path,receipt)
    if _reference_conventions.get(system)==convention:return
    if convention:_reference_conventions[system]=convention
    else:_reference_conventions.pop(system,None)
    from .versification_mapping import table
    table.cache_clear()


def write_index(path,system,canon,testaments):
    if not re.fullmatch(r'YouVersion[1-9][0-9]{0,8}',system):raise ValueError('Invalid source index identity')
    rows=['BIBLE-VRS-1 '+system]
    if not 1<=len(canon)<=100:raise ValueError('Invalid source book count')
    for book,maxima in canon.items():
        if not re.fullmatch(r'[1-5]?[A-Za-z][A-Za-z0-9]{1,15}',book) or not 1<=len(maxima)<=255:
            raise ValueError('Invalid source book index')
        if any(type(n) is not int or not 0<=n<=2000 for n in maxima):raise ValueError('Invalid source verse count')
        rows.append(f'{testaments[book]} {book} {len(maxima)} '+' '.join(map(str,maxima)))
    data=('\n'.join(rows)+'\n').encode('ascii')
    if len(data)>262144:raise ValueError('Source reference index too large')
    Path(path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=1)
def native_loader():
    import Sword
    candidates=[str(Path(Sword.__file__).parent.parent/'libsword.so'),'libsword.so','libsword.so.1.9.0']
    for candidate in candidates:
        try:
            # Retain the Python GIL while mutating the shared SWORD registry.
            library=ctypes.PyDLL(candidate)
            function=library.bible_register_source_index
            function.argtypes=[ctypes.c_char_p];function.restype=ctypes.c_int
            return library,function
        except (OSError,AttributeError):continue
    raise ValueError('Packaged source reference-index support is required')


def register_index(path,*,verified=True):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>262144:raise ValueError('Invalid source reference index')
    data=path.read_bytes()
    if verified:
        receipt=path.parent/'.verified.json'
        if receipt.stat().st_size>16384:raise ValueError('Invalid source verification receipt')
        expected=json.loads(receipt.read_text()).get('reference_index_sha256')
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Source reference index changed')
    _,function=native_loader()
    if function(str(path).encode())!=0:raise ValueError('Source reference index is invalid or conflicts with an open edition')
    if verified:
        register_convention(path,json.loads(receipt.read_text()))
