"""Versioned passage marks, isolated from notes, resources and sessions."""
import json
import os
from pathlib import Path
import re
import tempfile
from .notes import parts
from .providers import RESOURCE_ID

COLORS={'yellow':('#fff1a8','Yellow'),'green':('#c9edce','Green'),'blue':('#cce5ff','Blue')}
MAX_BYTES=8*1024*1024


def payload(path):
    path=Path(path)
    if path.stat().st_size>MAX_BYTES:raise ValueError('Highlights file is too large')
    value=json.loads(path.read_text())
    if (not isinstance(value,dict) or set(value)!={'version','marks'} or type(value.get('version')) is not int
            or value.get('version')!=1 or not isinstance(value.get('marks'),list)):
        raise ValueError('Unsupported highlights file')
    if len(value['marks'])>50000:raise ValueError('Too many highlights')
    result={}
    for mark in value['marks']:
        if not isinstance(mark,dict) or set(mark)!={'system','reference','color','resource'}:raise ValueError('Invalid highlight')
        if not all(isinstance(v,str) for v in mark.values()):raise ValueError('Invalid highlight')
        parts(mark['reference'])
        if (not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',mark['system']) or mark['color'] not in COLORS
                or len(mark['resource'])>256 or not re.fullmatch(RESOURCE_ID,mark['resource'])):raise ValueError('Invalid highlight')
        key=(mark['system'],mark['reference'])
        if key in result:raise ValueError('Duplicate highlight')
        result[key]=mark
    return result


def write(path,marks):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',dir=path.parent,prefix='.highlights-',delete=False) as out:
            temporary=Path(out.name)
            json.dump(dict(version=1,marks=list(marks.values())),out,ensure_ascii=False)
            out.flush();os.fsync(out.fileno())
        if temporary.stat().st_size>MAX_BYTES:raise ValueError('Highlights file is too large')
        os.replace(temporary,path)
    finally:
        if temporary:temporary.unlink(missing_ok=True)


class HighlightStore:
    def __init__(self,path):
        self.path=Path(path);self.entries={};self.error=''
        try:self.entries=payload(self.path)
        except FileNotFoundError:pass
        except (OSError,ValueError,TypeError,KeyError,RecursionError) as error:self.error=str(error)

    def ensure_recovered(self):
        if (self.path.parent/'annotation-restore.pending.json').exists():raise ValueError('Annotation restore recovery is pending. Reopen Bible before editing or exporting annotations.')

    def commit(self,marks):
        self.ensure_recovered()
        if self.error:raise ValueError('Original highlights file preserved; repair it before saving')
        if len(marks)>50000:raise ValueError('Too many highlights')
        write(self.path,marks);self.entries=marks

    def set(self,system,references,color,resource):
        if color is not None and color not in COLORS:raise ValueError('Invalid highlight color')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',system) or len(resource)>256 or not re.fullmatch(RESOURCE_ID,resource):raise ValueError('Invalid highlight')
        marks=dict(self.entries)
        for reference in references:
            parts(reference);key=(system,reference)
            if color is None:marks.pop(key,None)
            else:marks[key]=dict(system=system,reference=reference,color=color,resource=resource)
        self.commit(marks)

    def backup(self,path):
        self.ensure_recovered()
        if self.error:raise ValueError('Original highlights file preserved; cannot export an incomplete backup')
        write(path,self.entries)

    def restore(self,path):
        imported=payload(path)
        merged=dict(self.entries);merged.update(imported)
        self.commit(merged)
