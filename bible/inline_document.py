"""Native child-anchor slots excluded from Scripture copy and canonical offsets."""
from dataclasses import replace
from .pagination import StyleSpan


def decorate(document, markers):
    slots=sorted((s.body,ref,kind,payload) for s in document.spans
                 for ref in (s.reference,) for kind,payload in markers.get(ref,()))
    if not slots:return document
    def shifted(offset,after=False):
        return offset+sum(position<offset or (after and position==offset) for position,*_ in slots)
    pieces=[];copies=[];inline={};previous=0;offset=0;hidden=[]
    for position,ref,kind,payload in slots:
        text=document.text[previous:position];pieces.append(text);offset+=len(text)
        copies.append((document.copy_text or document.text)[previous:position])
        inline[offset]=(ref,kind,payload)
        hidden.append(StyleSpan('hidden',offset,offset+1))
        pieces.append('\ufffc');copies.append('\ufffc');offset+=1;previous=position
    pieces.append(document.text[previous:]);copies.append((document.copy_text or document.text)[previous:])
    value=replace(document,text=''.join(pieces),copy_text=''.join(copies),
                  spans=tuple(replace(s,start=shifted(s.start),body=shifted(s.body,True),end=shifted(s.end)) for s in document.spans),
                  styles=tuple(replace(s,start=shifted(s.start),end=shifted(s.end,True)) for s in document.styles)+tuple(hidden))
    value.inline=inline
    value.source_shift=shifted
    return value
