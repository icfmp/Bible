"""Small reviewed place enrichments, separate from downloaded geocoding indexes."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from .i18n import LANGUAGE


BUNDLED=Path(__file__).with_name('study_data')/'place_context_v2.json'
RESOURCE_ID='place-context'
MAX_DATA=4*1024*1024


def parse(data):
    """Validate the bounded resource before installing or rendering it."""
    import re
    from urllib.parse import urlsplit
    if len(data)>MAX_DATA:raise ValueError('Place context is too large')
    value=json.loads(data)
    if value.get('schema')!=2:raise ValueError('Unsupported place context schema')
    from datetime import date
    date.fromisoformat(value['generation'])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}',value['revision']):raise ValueError('Invalid place context revision')
    for identifier,place in value['places'].items():
        if not re.fullmatch(r'a[0-9a-f]{6}',identifier) or not isinstance(place['openbible_name'],str):raise ValueError('Invalid ancient identity')
        if any(not re.fullmatch(r'm[0-9a-f]{6}',m) for m in place['modern_ids']):raise ValueError('Invalid modern identity')
    for scope,entries in (('ancient-place',value['ancient_contexts']),('coordinate-source-entity',value['sites'])):
        for identifier,entry in entries.items():
            if entry['scope']!=scope or not re.fullmatch(r'Q[1-9][0-9]*',entry['wikidata']):raise ValueError('Invalid context identity')
            if scope=='ancient-place' and identifier not in value['identity_registry']['ancient_places']:raise ValueError('Ancient identity has no evidence')
            for language,intro in entry['introductions'].items():
                if language not in ('en','fr') or intro['language']!=language or not isinstance(intro['text'],str):raise ValueError('Invalid source language')
                if not re.fullmatch('https://'+language+r'\.wikipedia\.org/w/index\.php\?oldid=[0-9]+',intro['url']):raise ValueError('Invalid source revision')
                if intro['license_url']!='https://creativecommons.org/licenses/by-sa/4.0/':raise ValueError('Unsupported introduction license')
            for image in entry['images']:
                if not re.fullmatch('[0-9a-f]{64}',image['sha256']) or type(image['bytes']) is not int or not 0<image['bytes']<=2*1024*1024:raise ValueError('Invalid photo digest/size')
                url=urlsplit(image['url'])
                if url.scheme!='https' or url.hostname not in ('upload.wikimedia.org','thumb.wikimedia.org'):raise ValueError('Unsupported image source')
                license=urlsplit(image['license_url'])
                if license.scheme!='https' or license.netloc not in ('creativecommons.org','www.creativecommons.org') or not re.fullmatch(r'/(?:licenses/(?:by|by-sa)/(?:1\.0|2\.0|2\.5|3\.0|4\.0)|publicdomain/zero/1\.0)/?',license.path) or not image['author']:raise ValueError('Unsupported photo license/credit')
    return value


class PlaceContexts:
    """Independent optional dataset. Opening a place never contacts a server."""
    def __init__(self,root=None):
        self.root=Path(root) if root is not None else None
        self.path=self.root/'place-context.json' if self.root else None
        self._signature=None;self._value=None

    def read(self):
        path=self.path if self.path and self.path.is_file() and not self.path.is_symlink() else BUNDLED
        info=path.stat();signature=(str(path),info.st_ino,info.st_size,info.st_mtime_ns)
        if signature==self._signature:return self._value
        try:
            if info.st_size>MAX_DATA:raise ValueError('Place context is too large')
            value=parse(path.read_bytes())
        except (ValueError,KeyError,TypeError,RecursionError):
            if path==BUNDLED:raise
            value=parse(BUNDLED.read_bytes())
        self._signature,self._value=signature,value
        return value

    def metadata(self):
        value=self.read()
        return dict(revision=value['revision'],source_date=value['generation'],coverage=value['coverage'])

    def install(self,progress=lambda *_:None,installing=lambda:None):
        from .study_catalogue import StudyCatalogue,atomic_write
        if not self.root:raise ValueError('No place context installation directory')
        revision=StudyCatalogue(self.root).load()[RESOURCE_ID]
        self.root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.place-context-',dir=self.root) as tmp:
            path=Path(tmp)/'context.json'
            StudyCatalogue(self.root).download(RESOURCE_ID,path,progress,revision=revision)
            installing();data=path.read_bytes();value=parse(data)
            if value['revision']!=revision.revision or value['generation']!=revision.generation:raise ValueError('Place context revision mismatch')
            atomic_write(self.path,data)
        return self.metadata()

    def entries(self,place):
        value=self.read();record=value['places'].get(place['id'])
        if not record or record['openbible_name']!=place['name']:return None,[]
        direct=value['ancient_contexts'].get(place['id'])
        # Match both supplied IDs. A coordinate source is never promoted to an
        # ancient-place identity, even if its label resembles the place name.
        candidates={}
        for candidate in place.get('candidates',[]):
            modern=candidate.get('modern_id');entry=value['sites'].get(modern)
            if modern in record['modern_ids'] and entry and candidate.get('coordinate_source',{}).get('id')==entry['wikidata']:
                candidates.setdefault(modern,dict(entry=entry,name=candidate['name'],proposals=[]))['proposals'].append(candidate)
        return direct,list(candidates.values())


def context(place,root=None):
    direct,_=PlaceContexts(root).entries(place)
    return direct


def localized(value):
    language=LANGUAGE.split('_')[0].split('-')[0]
    return value.get(language) or value.get('en') or next(iter(value.values()),'')


def introduction(entry):
    language=LANGUAGE.split('_')[0].split('-')[0]
    values=entry['introductions']
    selected=language if language in values else 'en' if 'en' in values else next(iter(values),None)
    return values[selected] if selected else None


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
