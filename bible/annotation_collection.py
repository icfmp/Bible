"""Read-only unified annotation projection; existing records keep their identity."""
from dataclasses import dataclass
from .book_names import FRENCH,normalized
from .notes import BOOK_ORDER,parts,label_key
from .markdown import render


@dataclass(frozen=True)
class Annotation:
    key: tuple
    system: str
    start: str
    end: str
    origin: str
    note: object = None
    mark: object = None

    @property
    def labels(self):return self.note.labels if self.note else ()
    @property
    def body(self):return self.note.body if self.note else ''
    @property
    def modified(self):return self.note.modified if self.note else ''
    @property
    def color(self):return self.mark['color'] if self.mark else None


def records(notes,marks):
    """One row per note UUID or stored (versification, verse) highlight key."""
    return [Annotation(('note',n.id),n.versification,n.start,n.end,n.origin_translation,note=n) for n in notes]+[
        Annotation(('highlight',m['system'],m['reference']),m['system'],m['reference'],m['reference'],m['resource'],mark=dict(m)) for m in marks]


def bible_order(item):
    book,chapter,verse=parts(item.start)
    return BOOK_ORDER.get(book,10000),book,chapter,verse,parts(item.end),item.key


def filter_records(items,query='',labels=(),category='all',book='',color='',order='recent',reference_names=None):
    words=[normalized(word) for word in query.split() if normalized(word)]
    wanted={label_key(label) for label in labels};result=[]
    for item in items:
        if category=='notes' and not item.note or category=='highlights' and not item.mark:continue
        code,chapter,verse=parts(item.start)
        if book and code!=book or color and item.color!=color:continue
        if not wanted <= {label_key(label) for label in item.labels}:continue
        text=normalized(' '.join((render(item.body)[0],item.start,item.end,FRENCH.get(code,code),
                                  f'{chapter}:{verse}',(reference_names or {}).get(code,''),item.origin,item.system,item.color or '',*item.labels)))
        if not all(word in text for word in words):continue
        result.append(item)
    result.sort(key=bible_order)
    # Highlight storage has no timestamps. Do not invent modification dates:
    # keep those in Bible order after the dated notes.
    if order in ('recent','oldest'):
        dated=[item for item in result if item.modified];undated=[item for item in result if not item.modified]
        dated.sort(key=lambda item:(item.modified,item.key),reverse=order=='recent')
        result=dated+undated
    return result
