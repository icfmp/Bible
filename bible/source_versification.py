"""Small source-specific native indexes; no Scripture cache or inferred mapping."""
import ctypes
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re


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
