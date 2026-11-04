"""Resolve verified native/table capabilities without guessing verse identities."""
from dataclasses import dataclass


class VersificationMismatch(ValueError):
    pass


MAPPED_SYSTEMS = frozenset({'KJV', 'KJVA', 'Segond', 'DarbyFr', 'Calvin',
                            'NRSV', 'Synodal', 'Vulg'})


@dataclass(frozen=True)
class ResolvedPassage:
    start: str | None
    end: str | None
    introductions: tuple[str, ...] = ()


def resolve(reference, source_system, target_reader, require_entry=True, *, include_introductions=False):
    import re
    import Sword
    from .book_names import canonical_input
    reference=canonical_input(reference)
    if not re.fullmatch(r'(?:[1-5]\s*)?[A-Za-z][A-Za-z0-9]*(?: [A-Za-z]+)*[ .]+[1-9][0-9]*(?:[.:][1-9][0-9]*)?',reference):
        raise ValueError(f'Invalid source reference: {reference}')
    target_system = target_reader.versification
    source = Sword.VerseKey()
    source.setVersificationSystem(source_system)
    if source.getVersificationSystem() != source_system:
        raise VersificationMismatch(source_system)
    source.setAutoNormalize(False)
    source.setText(reference)
    if (source.popError() != '\x00' or not 1 <= source.getChapter() <= source.getChapterMax()
            or not 1 <= source.getVerse() <= source.getVerseMax()):
        raise ValueError(f'Invalid source reference: {reference}')
    # Native SWORD loses the split final verse of 3 John in some registered
    # systems. Use the already pinned verse-part tables where both canons match.
    split_john = False
    if source_system != target_system and source.getOSISBookName() == '3John':
        from .versification_mapping import table
        split_john = table(source_system) is not None and table(target_system) is not None
    if source_system != target_system and (split_john or not {source_system, target_system} <= MAPPED_SYSTEMS):
        from .versification_mapping import to_base, from_base
        reference = source.getOSISRef()
        intermediate = to_base(reference, source_system)
        if intermediate is None and source_system in MAPPED_SYSTEMS:
            intermediate = _native_refs(source, 'KJVA')
        if not intermediate:
            raise VersificationMismatch(f'No verified alignment: {source_system} {reference} / {target_system}')
        references = []
        for qualified in intermediate:
            mapped = from_base(qualified, target_system)
            if mapped is None and target_system in MAPPED_SYSTEMS and not qualified.startswith('?') and '!' not in qualified:
                base = Sword.VerseKey()
                base.setVersificationSystem('KJVA'); base.setAutoNormalize(False); base.setText(qualified)
                mapped = _native_refs(base, target_system)
            # A partially mapped result is not an exact alignment either.
            if not mapped:
                raise VersificationMismatch(f'No verified alignment: {source_system} {reference} / {target_system}')
            references.extend(mapped)
        introductions=()
        if include_introductions:
            contexts=[];verses=[]
            for ref in references:
                if ref.endswith('.0'):
                    introduction_key(ref,target_reader)  # Validate a real native context, never clamp it.
                    contexts.append(ref)
                else:verses.append(ref)
            introductions=tuple(dict.fromkeys(contexts));references=verses
            if not references:
                return ResolvedPassage(None,None,introductions)
        try:
            ordered = sorted(set(references), key=lambda ref: target_reader.key(ref).getIndex())
            if _span(ordered[0], ordered[-1], target_system) != ordered:
                raise VersificationMismatch(f'Non-contiguous alignment: {source_system} {reference} / {target_system}')
        except ValueError as error:
            raise VersificationMismatch(str(error)) from error
        if require_entry and any(not target_reader.has_reference(ref) for ref in ordered):
            raise ValueError(f'Passage unavailable: {ordered[0]}–{ordered[-1]}')
        return ResolvedPassage(ordered[0], ordered[-1],introductions)
    target = Sword.VerseKey()
    target.setVersificationSystem(target_system)
    target.setAutoNormalize(False)
    # positionFrom preserves the destination system and invokes translateVerse.
    # copy construction/copyFrom instead copies the source system.
    target.positionFrom(source)
    error=target.popError()
    if error == '\x00' and target.getVerse()==0 and include_introductions and not target.isBoundSet():
        context=f'{target.getOSISBookName()}.{target.getChapter()}.0'
        introduction_key(context,target_reader)
        return ResolvedPassage(None,None,(context,))
    if error != '\x00' or target.getVerse() < 1:
        raise VersificationMismatch(f'No verse alignment: {reference}')
    start = target.getOSISRef()
    end = target.getUpperBound().getOSISRef() if target.isBoundSet() else start
    target_reader.key(start);target_reader.key(end)
    if require_entry and (not target_reader.has_reference(start) or not target_reader.has_reference(end)):
        raise ValueError(f'Passage unavailable: {start}' + (f'–{end}' if end != start else ''))
    return ResolvedPassage(start, end)


def _span(start, end, system):
    """Enumerate actual consecutive verses, excluding introductions."""
    import Sword
    key = Sword.VerseKey(); key.setVersificationSystem(system); key.setText(start)
    refs = []
    for _ in range(100000):
        reference = key.getOSISRef()
        if key.getVerse()>0:refs.append(reference)
        if reference == end:
            return refs
        key.increment()
        if key.popError() != '\x00':break
    raise VersificationMismatch(f'Invalid alignment range: {start}–{end}')


def _native_refs(source, system):
    import Sword
    target = Sword.VerseKey(); target.setVersificationSystem(system); target.setAutoNormalize(False)
    target.positionFrom(source)
    if target.popError() != '\x00' or target.getVerse() < 1:
        return []
    start = target.getOSISRef()
    end = target.getUpperBound().getOSISRef() if target.isBoundSet() else start
    return _span(start, end, system)


def available_chapter(reference,reader):
    """Explicit opening only: printed chapter availability is not verse alignment."""
    from .book_names import canonical_input
    parts=canonical_input(reference).split('.')
    if len(parts)!=3:return None
    book,chapter,_=parts
    try:chapter=int(chapter)
    except ValueError:return None
    entry=next((item for item in reader.books if item.code==book),None)
    verses=entry.chapters.get(chapter) if entry else None
    if not verses:return None
    order=reader.source_verse_order.get(f'{book}.{chapter}',verses)
    return f'{book}.{chapter}.{order[0]}'


def introduction_key(reference,reader):
    """Validate explicitly mapped chapter context independently of ordinary verses."""
    import re
    import Sword
    match=re.fullmatch(r'([1-5]?[A-Za-z][A-Za-z0-9]*)\.([1-9][0-9]*)\.0',reference)
    if not match:raise VersificationMismatch('Unsupported introduction context: '+reference)
    key=Sword.VerseKey();key.setVersificationSystem(reader.versification)
    key.setIntros(True);key.setAutoNormalize(False);key.setText(reference)
    if (key.popError()!='\x00' or key.getOSISBookName()!=match[1]
            or key.getChapter()!=int(match[2]) or key.getVerse()!=0):
        raise VersificationMismatch('Invalid introduction context: '+reference)
    return key
