"""Read-only installed/curated version discovery; never replaces a SWORD root."""
from dataclasses import dataclass
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import urllib.request
from urllib.error import HTTPError
from urllib.parse import urlsplit,urlunsplit
from .library import config
from .study_catalogue import atomic_write

CATALOGUE_URL='https://raw.githubusercontent.com/icfmp/Bible-Resources/main/catalog/v1/catalog.json'
MAX_CATALOGUE=2*1024*1024


@dataclass(frozen=True)
class InstalledModule:
    name:str
    version:str
    source:str
    root:Path
    versification:str
    title:str


def public_source(value):
    """Never display credentials from an InstallSource URL."""
    try:
        parts=urlsplit(value)
        if parts.scheme and parts.hostname:
            return urlunsplit((parts.scheme,parts.hostname+(':'+str(parts.port) if parts.port else ''),parts.path,'',''))
    except ValueError:return ''
    return value[:128] if re.fullmatch(r'[\w .()/-]{0,128}',value) else ''


def installed_modules(library_root,extra_roots=()):
    library_root=Path(library_root)
    roots=[p for p in library_root.iterdir() if p.is_dir() and (p/'.complete').is_file()] if library_root.exists() else []
    roots.extend(Path(p).expanduser() for p in (
        *os.environ.get('SWORD_PATH','').split(os.pathsep),str(Path.home()/'.sword'),
        '/usr/share/sword','/usr/local/share/sword',*map(str,extra_roots)) if p)
    result=[];errors=[];seen=set()
    for root in roots:
        try:
            for file in (root/'mods.d').glob('*.conf'):
                identity=file.resolve()
                if identity in seen:continue
                seen.add(identity)
                if file.stat().st_size>65536:raise ValueError('Module configuration exceeds safe limits')
                parser=config(file.read_bytes())
                for name in parser.sections():
                    section=parser[name]
                    source=section.get('InstallSource','')
                    if not source and (root/'.source.json').is_file():
                        if (root/'.source.json').stat().st_size>65536:raise ValueError('Source metadata exceeds safe limits')
                        metadata=json.loads((root/'.source.json').read_text())
                        source=metadata.get('source_url','')
                    result.append(InstalledModule(name,section.get('Version',''),public_source(source),
                        root,section.get('Versification','KJV'),section.get('Description',name)))
        except (OSError,ValueError,TypeError) as error:errors.append((str(root),str(error)))
    return tuple(result),tuple(errors)


def parse_catalogue(data):
    if len(data)>MAX_CATALOGUE:raise ValueError('Module catalogue exceeds safe limits')
    value=json.loads(data)
    if (not isinstance(value,dict) or type(value.get('schema_version')) is not int or value.get('schema_version')!=1
            or value.get('repository')!='Bible Resources'
            or value.get('repository_url')!='https://icfmp.github.io/Bible-Resources/'
            or not isinstance(value.get('modules'),list) or len(value['modules'])>10000):
        raise ValueError('Unsupported Bible Resources catalogue')
    for entry in value['modules']:
        if not isinstance(entry,dict):raise ValueError('Invalid curated module')
        for field in ('id','sword_id','version','edition'):
            if not isinstance(entry.get(field),str) or not 0<len(entry[field])<=128:raise ValueError('Invalid curated module identity')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',entry['sword_id']):raise ValueError('Invalid SWORD identifier')
        download=entry.get('download',{})
        if (not isinstance(download.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',download['sha256'])
                or type(download.get('size_bytes')) is not int or download['size_bytes']<=0):
            raise ValueError('Invalid curated module integrity metadata')
        if not download.get('url','').startswith('https://icfmp.github.io/Bible-Resources/sword/packages/'):
            raise ValueError('Unsupported curated module origin')
    return value


class ModuleCatalogue:
    def __init__(self,root):self.path=Path(root)/'module-catalogue.json'

    def saved(self):
        if self.path.is_symlink() or self.path.stat().st_size>MAX_CATALOGUE*2:raise ValueError('Invalid saved module catalogue')
        record=json.loads(self.path.read_text())
        if not isinstance(record,dict) or not isinstance(record.get('body'),str):raise ValueError('Invalid saved module catalogue')
        parse_catalogue(record['body'].encode())
        return record

    def check(self,opener=None):
        try:saved=self.saved()
        except (OSError,ValueError,TypeError,KeyError):saved=None
        headers={'User-Agent':'Bible module update check'}
        if saved:
            if saved.get('etag'):headers['If-None-Match']=saved['etag']
            if saved.get('last_modified'):headers['If-Modified-Since']=saved['last_modified']
        request=urllib.request.Request(CATALOGUE_URL,headers=headers)
        checked=datetime.now(timezone.utc).isoformat()
        try:
            try:
                with (opener or urllib.request.urlopen)(request,timeout=20) as response:
                    data=response.read(MAX_CATALOGUE+1);parse_catalogue(data)
                    saved=dict(body=data.decode(),etag=response.headers.get('ETag',''),
                        last_modified=response.headers.get('Last-Modified',''),checked=checked)
            except HTTPError as error:
                if error.code!=304 or not saved:raise
                saved=dict(saved,checked=checked)
            atomic_write(self.path,json.dumps(saved).encode())
            return dict(catalogue=parse_catalogue(saved['body'].encode()),cached=False,checked=checked,error='')
        except (OSError,ValueError,TypeError) as error:
            if not saved:raise
            return dict(catalogue=parse_catalogue(saved['body'].encode()),cached=True,
                        checked=saved['checked'],error=str(error))


def assessment(installed,catalogue):
    """An ID/title/Version coincidence is never sufficient edition evidence."""
    candidates=[entry for entry in catalogue['modules'] if entry['sword_id']==installed.name]
    return 'identity-unverified' if candidates else 'no-curated-edition'
