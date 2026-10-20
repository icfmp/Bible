"""Resolve verses with SWORD 1.9's native VerseKey mapping, never text reparsing.

Only systems for which SWORD ships mapping data (or the KJV base) are
accepted across systems. Other pairs keep an explicit local limitation.
"""
from dataclasses import dataclass


class VersificationMismatch(ValueError):
    pass


MAPPED_SYSTEMS = frozenset({'KJV', 'KJVA', 'Segond', 'DarbyFr', 'Calvin',
                            'NRSV', 'Synodal', 'Vulg'})


@dataclass(frozen=True)
class ResolvedPassage:
    start: str
    end: str


def resolve(reference, source_system, target_reader, require_entry=True):
    import Sword
    from .book_names import canonical_input
    reference=canonical_input(reference)
    target_system = target_reader.versification
    if source_system != target_system and not {source_system, target_system} <= MAPPED_SYSTEMS:
        raise VersificationMismatch(f'{source_system} / {target_system}')
    source = Sword.VerseKey()
    source.setVersificationSystem(source_system)
    if source.getVersificationSystem() != source_system:
        raise VersificationMismatch(source_system)
    source.setAutoNormalize(False)
    source.setText(reference)
    if source.popError() != '\x00':
        raise ValueError(f'Invalid source reference: {reference}')
    target = Sword.VerseKey()
    target.setVersificationSystem(target_system)
    target.setAutoNormalize(False)
    # positionFrom preserves the destination system and invokes translateVerse.
    # copy construction/copyFrom instead copies the source system.
    target.positionFrom(source)
    if target.popError() != '\x00' or target.getVerse() < 1:
        raise VersificationMismatch(f'No verse alignment: {reference}')
    start = target.getOSISRef()
    end = target.getUpperBound().getOSISRef() if target.isBoundSet() else start
    target_reader.key(start);target_reader.key(end)
    if require_entry and (not target_reader.has_reference(start) or not target_reader.has_reference(end)):
        raise ValueError(f'Passage unavailable: {start}' + (f'–{end}' if end != start else ''))
    return ResolvedPassage(start, end)
