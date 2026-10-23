"""Verified dataset convention and bounded exact local passage excerpts."""
from dataclasses import dataclass
from .reference_data import reference_key,reference_span
from .reference_resolution import resolve, VersificationMismatch


class Canon:
    """SWORD's canonical key space only, never a claimed installed translation."""
    def __init__(self, system):self.versification=system

    def key(self, reference):
        import Sword
        key=Sword.VerseKey();key.setVersificationSystem(self.versification);key.setAutoNormalize(False)
        if key.getVersificationSystem()!=self.versification:raise VersificationMismatch(self.versification)
        key.setText(reference)
        if (key.popError()!='\x00' or not 1<=key.getChapter()<=key.getChapterMax()
                or not 1<=key.getVerse()<=key.getVerseMax()):raise ValueError('Invalid canonical reference: '+reference)
        key.setAutoNormalize(True)
        return key


def source_references(reader, start, end):
    """Project every selected verse into actual OpenBible source addresses."""
    key=reader.key(start);last=reader.key(end).getIndex();result=set();count=0
    while key.getIndex()<=last:
        reference=key.getOSISRef();count+=1
        if count>1000:raise ValueError('Select at most 1000 verses')
        if key.getOSISBookName()=='3John':
            from .versification_mapping import to_base,from_base
            qualified=to_base(reference,reader.versification)
            if not qualified:raise VersificationMismatch('No verified source alignment: '+reference)
            mapped=[]
            for part in qualified:
                values=from_base(part,'NRSV')
                if not values:raise VersificationMismatch('No verified source alignment: '+reference)
                mapped.extend(values)
            result.update(mapped)
        else:
            mapped=resolve(reference,reader.versification,Canon('KJV'),require_entry=False)
            target=Canon('KJV').key(mapped.start);upper=Canon('KJV').key(mapped.end).getIndex()
            while target.getIndex()<=upper:
                result.add(target.getOSISRef());target.increment()
                if target.popError()!='\x00':break
        key.increment()
        if key.popError()!='\x00':break
    for reference in result:reference_key(reference)
    return sorted(result,key=reference_key)


def destination(reference, reader, *, require_entry=True):
    reference_key(reference)
    if reference.startswith('3John.'):
        from .versification_mapping import table
        if table(reader.versification) is None:
            raise VersificationMismatch('No verified split-verse alignment for '+reader.versification)
        return resolve(reference,'NRSV',reader,require_entry=require_entry)
    return resolve(reference,'KJV',reader,require_entry=require_entry)


def local_target_ranges(reader,start,end):
    """Complete verified target, independently of the bounded excerpt preview.

    Coalesce only consecutive mapped addresses, never fill a mapping gap or
    infer an end from the excerpt. Missing module entries do not erase targets.
    """
    ranges=[];seen=set();count=0
    for reference in reference_span(start,end):
        count+=1
        if count>1000:raise ValueError('Reference range exceeds preview limits')
        mapped=destination(reference,reader,require_entry=False)
        key=reader.key(mapped.start);last=reader.key(mapped.end).getIndex()
        while key.getIndex()<=last:
            target=key.getOSISRef()
            if target not in seen:
                previous=reader.key(ranges[-1][1]) if ranges else None
                if previous:previous.increment()
                if previous and previous.popError()=='\x00' and previous.getOSISRef()==target:ranges[-1]=(ranges[-1][0],target)
                else:ranges.append((target,target))
                seen.add(target)
            key.increment()
            if key.popError()!='\x00':break
    return tuple(ranges)


@dataclass(frozen=True)
class LocalExcerpt:
    start: str
    end: str
    verses: tuple
    more: bool

    @property
    def text(self):return '\n'.join(text for _,text in self.verses)


def local_excerpt(reader, start, end=None, *, source_system='openbible', limit=6, chapter_cache=None):
    """Map each source verse; never bridge discontinuities using only endpoints."""
    end=end or start
    def native_span():
        source=Canon(source_system);key=source.key(start);upper=source.key(end).getIndex()
        if key.getIndex()>upper:raise ValueError('Reversed passage')
        while key.getIndex()<=upper:
            yield key.getOSISRef();key.increment()
            if key.popError()!='\x00':break
    source=reference_span(start,end) if source_system=='openbible' else native_span()
    refs=[];seen=set();more=False
    for reference in source:
        mapped=destination(reference,reader) if source_system=='openbible' else resolve(reference,source_system,reader)
        target=reader.key(mapped.start);last=reader.key(mapped.end).getIndex()
        while target.getIndex()<=last:
            ref=target.getOSISRef()
            if ref not in seen:
                if len(refs)>=limit:more=True;break
                if not reader.has_reference(ref):raise ValueError('Passage unavailable: '+ref)
                refs.append(ref);seen.add(ref)
            target.increment()
            if target.popError()!='\x00':break
        if more:break
    if not refs:raise ValueError('Passage unavailable')
    chapters={} if chapter_cache is None else chapter_cache;verses=[]
    for reference in refs:
        chapter=reference.rsplit('.',1)[0]
        if chapter not in chapters:
            chapters[chapter]=dict(reader.chapter(reference).verses)
            if len(chapters)>64:chapters.pop(next(iter(chapters)))
        text=chapters[chapter].get(reference)
        if not text:raise ValueError('Passage unavailable: '+reference)
        verses.append((reference,text))
    return LocalExcerpt(refs[0],refs[-1],tuple(verses),more)
