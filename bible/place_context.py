"""Small reviewed place enrichments, separate from downloaded geocoding indexes."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from .i18n import LANGUAGE


def context(place):
    path=Path(__file__).with_name('study_data')/'place_context.json'
    value=json.loads(path.read_text(encoding='utf-8'))
    entry=value['places'].get(place['id']) if value['schema']==1 else None
    # Match stable source identity, never an ambiguous translated place name.
    if entry and entry['identity']['openbible_name']==place['name']:return entry
    return None


def localized(value):
    return value.get(LANGUAGE.split('_')[0].split('-')[0],value['en'])


def cached_image(root,image,download=False,*,cancelled=lambda:False):
    """Only explicit downloads; bounded, verified files in a dedicated image cache."""
    from .library import download as fetch
    def check_cancelled(*_):
        if cancelled():raise InterruptedError('Photograph request cancelled')
    check_cancelled()
    root=Path(root)/'place-images';digest=image['sha256']
    if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('Invalid photo checksum')
    path=root/(digest+'.jpg');limit=2*1024*1024
    if path.is_file() and path.stat().st_size<=limit and hashlib.sha256(path.read_bytes()).hexdigest()==digest:return path
    if not download:return None
    root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.download-',dir=root) as temporary:
        candidate=Path(temporary)/'photo.jpg'
        with candidate.open('wb') as output:fetch(image['url'],output,limit=limit,progress=check_cancelled)
        check_cancelled()
        if hashlib.sha256(candidate.read_bytes()).hexdigest()!=digest:raise ValueError('Photo checksum mismatch')
        # Ten files, at most 2 MiB each, in this image-only cache. No study index,
        # profile preferences, annotations or other application caches are touched.
        old=sorted(root.glob('*.jpg'),key=lambda p:p.stat().st_mtime)
        for previous in old[:-9]:previous.unlink()
        with candidate.open('rb') as source:os.fsync(source.fileno())
        os.replace(candidate,path)
    return path
