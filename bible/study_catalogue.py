"""Small checked study-resource metadata; network refresh belongs to a worker."""
from dataclasses import dataclass
from datetime import date
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

CATALOGUE_URL='https://raw.githubusercontent.com/icfmp/Bible/data/study-resources/catalogue.json'
BUNDLED=Path(__file__).with_name('study_data')/'catalogue.json'
MAX_CATALOGUE=65536
FORMATS={'openbible-cross-references':('openbible-cross-references-v1',8*1024*1024),
         'openbible-topics':('openbible-topics-v1',4*1024*1024),
         'topic-vocabulary':('bible-topic-vocabulary-v1',1024*1024)}


@dataclass(frozen=True)
class ResourceRevision:
    revision: str
    generation: str
    sha256: str
    size: int
    format: str
    url: str

    def verify(self,path):
        path=Path(path)
        if path.is_symlink() or path.stat().st_size!=self.size or hashlib.sha256(path.read_bytes()).hexdigest()!=self.sha256:
            raise ValueError('Study resource checksum or size mismatch; installed data was preserved')


def parse(data):
    if len(data)>MAX_CATALOGUE:raise ValueError('Study catalogue is too large')
    try:value=json.loads(data)
    except (ValueError,UnicodeError,RecursionError) as error:raise ValueError('Invalid study catalogue JSON') from error
    if not isinstance(value,dict) or type(value.get('schema')) is not int or value.get('schema')!=1 or not isinstance(value.get('resources'),dict):
        raise ValueError('Unsupported study catalogue')
    resources=value['resources']
    if len(resources)>32 or not FORMATS.keys()<=resources.keys():raise ValueError('Incomplete study catalogue')
    result={}
    for identifier,(format_name,limit) in FORMATS.items():
        item=resources[identifier]
        if not isinstance(item,dict) or set(item)!={'revision','generation','sha256','size','format','url'}:raise ValueError('Invalid study resource metadata')
        if not all(isinstance(item[k],str) for k in ('revision','generation','sha256','format','url')):raise ValueError('Invalid study resource metadata')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}',item['revision']):raise ValueError('Invalid study resource revision')
        if date.fromisoformat(item['generation']).isoformat()!=item['generation']:raise ValueError('Invalid generation date')
        if not re.fullmatch('[0-9a-f]{64}',item['sha256']) or type(item['size']) is not int or not 0<item['size']<=limit:
            raise ValueError('Invalid study resource digest/size')
        url=urlsplit(item['url'])
        if (url.scheme!='https' or url.netloc!='github.com' or url.query or url.fragment or
                not re.fullmatch(r'/icfmp/Bible/releases/download/study-resource-archives/[A-Za-z0-9._-]+',url.path)):
            raise ValueError('Unsupported study resource origin')
        if item['format']!=format_name:raise ValueError('Unsupported study resource format')
        result[identifier]=ResourceRevision(**item)
    return result


def atomic_write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,prefix='.study-resource-',delete=False) as output:
            temporary=Path(output.name);output.write(data);output.flush();os.fsync(output.fileno())
        os.replace(temporary,path)
    finally:
        if temporary:temporary.unlink(missing_ok=True)


class StudyCatalogue:
    def __init__(self,root):self.root=Path(root);self.path=self.root/'resource-catalogue.json'

    def load(self):
        try:
            if self.path.is_symlink() or self.path.stat().st_size>MAX_CATALOGUE:raise ValueError('Invalid saved study catalogue')
            return parse(self.path.read_bytes())
        except (OSError,ValueError,TypeError,KeyError):return parse(BUNDLED.read_bytes())

    def refresh(self):
        from .library import download
        output=io.BytesIO();download(CATALOGUE_URL,output,limit=MAX_CATALOGUE)
        data=output.getvalue();value=parse(data)
        atomic_write(self.path,data)
        return value

    def download(self,identifier,destination,progress=lambda done,total:None,*,revision=None):
        from .library import download
        item=revision or self.load()[identifier]
        with Path(destination).open('wb') as output:download(item.url,output,progress,limit=item.size)
        item.verify(destination)
        return item
