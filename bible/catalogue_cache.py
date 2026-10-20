"""Versioned, atomic metadata caches, isolated from installed modules and notes."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
import time


class CatalogueCache:
    def __init__(self, root):self.root=Path(root)

    def read(self, provider):
        from .library import Resource
        try:
            path=self.root/(provider.id+'.json')
            if path.stat().st_size>16*1024*1024:return None
            value=json.loads(path.read_text())
            if value['version']!=1 or value['provider']!=provider.id or value['url']!=provider.catalogue_url:return None
            if not isinstance(value['updated'],(float,int)) or value['updated']>time.time()+300:return None
            if not isinstance(value['resources'],list):return None
            resources=[]
            for item in value['resources']:
                if not isinstance(item,dict):return None
                resource=Resource(**item)
                if (resource.provider_id!=provider.id or resource.source_url!=provider.url
                        or resource.source!=provider.name or type(resource.locked) is not bool
                        or any(not isinstance(v,str) for k,v in asdict(resource).items() if k!='locked')):return None
                resource.id  # Validate the provider-specific identity.
                resources.append(resource)
            return tuple(resources),value['updated']
        except (OSError,ValueError,KeyError,TypeError):return None

    def write(self,provider,resources):
        self.root.mkdir(parents=True,exist_ok=True)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile('w',dir=self.root,prefix='.'+provider.id,delete=False) as out:
                temporary=Path(out.name)
                json.dump(dict(version=1,provider=provider.id,url=provider.catalogue_url,
                               updated=time.time(),resources=[asdict(r) for r in resources]),out)
                out.flush();os.fsync(out.fileno())
            os.replace(temporary,self.root/(provider.id+'.json'))
        finally:
            if temporary:temporary.unlink(missing_ok=True)
