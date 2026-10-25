"""Verified correspondence groups; display padding never becomes Scripture."""
from dataclasses import dataclass, replace
from .reference_resolution import resolve, _span
from .pagination import Document, StyleSpan


@dataclass(frozen=True)
class Correspondence:
    primary: tuple
    secondary: tuple


def correspondences(primary, secondary, left, right):
    """Connected mappings preserve merged/split source blocks exactly once.

    Both directions are checked. Unavailable mapping raises, rather than being
    confused with an absent module entry. Input lists contain actual entries.
    """
    left=tuple(left);right=tuple(right)
    nodes={(0,r):{(0,r)} for r in left}
    nodes.update({(1,r):{(1,r)} for r in right})
    def connect(side, reference, mapped):
        own=nodes[(side,reference)]
        for ref in mapped:
            other=nodes.get((1-side,ref))
            if other is not None and other is not own:
                own.update(other)
                for n in other:nodes[n]=own
    for side,reader,target,refs in ((0,primary,secondary,left),(1,secondary,primary,right)):
        for ref in refs:
            mapped=resolve(ref,reader.versification,target,require_entry=False)
            connect(side,ref,_span(mapped.start,mapped.end,target.versification))
    unique={id(group):group for group in nodes.values()}
    def order(group):
        own=[primary.key(ref).getIndex() for side,ref in group if side==0]
        if own:return min(own)
        ref=next(ref for _,ref in group)
        return primary.key(resolve(ref,secondary.versification,primary,require_entry=False).start).getIndex()
    groups=sorted(unique.values(),key=order)
    result=[];last=(-1,-1)
    for group in groups:
        a=tuple(sorted((r for s,r in group if s==0),key=lambda r:primary.key(r).getIndex()))
        b=tuple(sorted((r for s,r in group if s==1),key=lambda r:secondary.key(r).getIndex()))
        positions=(min((primary.key(r).getIndex() for r in a),default=last[0]),
                   min((secondary.key(r).getIndex() for r in b),default=last[1]))
        if any(p<q for p,q in zip(positions,last)):
            raise ValueError('Non-monotonic correspondence; shared alignment unavailable')
        last=positions
        result.append(Correspondence(a,b))
    return tuple(result)


def row_document(document, rows, side, gap):
    """Reuse source words/styles, add paragraph boundaries only in comparison."""
    pieces=[];copies=[];spans=[];styles=[];bounds=[];offset=0
    source={s.reference:(i,s) for i,s in enumerate(document.spans)}
    for row in rows:
        start=offset
        refs=row.primary if side==0 else row.secondary
        if not refs:
            text=gap+'\n'
            pieces.append(text);copies.append(text)
            styles.append(StyleSpan('hidden',offset,offset+len(text)))
            offset+=len(text)
        else:
            for ref in refs:
                index,span=source[ref]
                end=document.spans[index+1].start if index+1<len(document.spans) else len(document.text)
                text=document.text[span.start:end]
                pieces.append(text);copies.append((document.copy_text or document.text)[span.start:end])
                spans.append(replace(span,start=offset,body=offset+span.body-span.start,end=offset+span.end-span.start))
                for style in document.styles:
                    low,high=max(span.start,style.start),min(end,style.end)
                    if high>low:styles.append(replace(style,start=offset+low-span.start,end=offset+high-span.start))
                offset+=len(text)
            if not pieces[-1].endswith('\n'):
                pieces.append('\n');copies.append('\n');offset+=1
        bounds.append((start,offset))
    return Document(document.key,''.join(pieces),tuple(spans),tuple(styles),''.join(copies)),tuple(bounds)
