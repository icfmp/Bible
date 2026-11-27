"""Verified dataset convention and bounded exact local passage excerpts."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Protocol, cast
from dataclasses import dataclass

if TYPE_CHECKING:
    import Sword
    from .sword_provider import Chapter, Reader
from .reference_data import reference_key, reference_span, source_system as dataset_system
from .reference_resolution import (
    ReferenceSpace,
    ResolvedPassage,
    resolve,
    VersificationMismatch,
    _span,
    checked_verse_key,
)


class _AlignmentSource(Protocol):
    def can_align_reference(self, reference: str) -> bool: ...


class _AlignedEntries(_AlignmentSource, Protocol):
    def has_reference(self, reference: str) -> bool: ...


class Canon:
    """SWORD's canonical key space only, never a claimed installed translation."""

    def __init__(self, system: str) -> None:
        self.versification = system

    def key(self, reference: str) -> Sword.VerseKey:
        """Validate a native canonical key without normalizing invalid input into another verse."""
        return checked_verse_key(reference, self.versification)


def _dataset_system(reference: str, paired_system: str) -> str:
    """Select the documented dataset numbering and require qualified split support."""
    system = dataset_system(reference.split(".", 1)[0])
    if system != dataset_system(""):
        from .versification_mapping import table

        if table(paired_system) is None:
            raise VersificationMismatch("No verified dataset alignment for " + paired_system)
    return system


def source_references(reader: ReferenceSpace, start: str, end: str) -> list[str]:
    """Project every selected verse into actual OpenBible source addresses."""
    source = reader.versification
    first, last = reader.key(start).getOSISRef(), reader.key(end).getOSISRef()
    result = set()
    for count, reference in enumerate(_span(first, last, source, reader), 1):
        if count > 1000:
            raise ValueError("Select at most 1000 verses")
        if hasattr(reader, "can_align_reference") and not cast(
            "_AlignmentSource", reader
        ).can_align_reference(reference):
            raise VersificationMismatch("Source numbering is not verified: " + reference)
        system = _dataset_system(reference, source)
        resolved = resolve(reference, source, Canon(system), require_entry=False)
        result.update(_span(resolved.start, resolved.end, system))
    for reference in result:
        reference_key(reference)
    return sorted(result, key=reference_key)


def destination(
    reference: str, reader: ReferenceSpace, *, require_entry: bool = True
) -> ResolvedPassage[str]:
    """Map an OpenBible-convention address and verify edition-specific target capability."""
    reference_key(reference)
    system = _dataset_system(reference, reader.versification)
    mapped = resolve(reference, system, reader, require_entry=require_entry)
    if hasattr(reader, "can_align_reference"):
        # Readers advertising alignment also expose actual-entry availability;
        # bare canons deliberately do not claim either resource capability.
        entries = cast("_AlignedEntries", reader)
        for target in _span(mapped.start, mapped.end, reader.versification, reader):
            if entries.has_reference(target) and not entries.can_align_reference(target):
                raise VersificationMismatch("Target numbering is not verified: " + target)
    return mapped


def local_target_ranges(
    reader: ReferenceSpace, start: str, end: str
) -> tuple[tuple[str, str], ...]:
    """Complete verified target, independently of the bounded excerpt preview.

    Coalesce only consecutive mapped addresses, never fill a mapping gap or
    infer an end from the excerpt. Missing module entries do not erase targets.
    """
    ranges: list[tuple[str, str]] = []
    seen = set()
    count = 0
    for reference in reference_span(start, end):
        count += 1
        if count > 1000:
            raise ValueError("Reference range exceeds preview limits")
        mapped = destination(reference, reader, require_entry=False)
        key = reader.key(mapped.start)
        last = reader.key(mapped.end).getIndex()
        while key.getIndex() <= last:
            target = key.getOSISRef()
            if target not in seen:
                previous = reader.key(ranges[-1][1]) if ranges else None
                if previous:
                    previous.increment()
                if previous and previous.popError() == "\x00" and previous.getOSISRef() == target:
                    ranges[-1] = (ranges[-1][0], target)
                else:
                    ranges.append((target, target))
                seen.add(target)
            key.increment()
            if key.popError() != "\x00":
                break
    return tuple(ranges)


@dataclass(frozen=True)
class LocalExcerpt:
    """A bounded local excerpt whose actual displayed range may be shorter than its target."""

    start: str
    end: str
    verses: tuple[tuple[str, str], ...]
    more: bool

    @property
    def text(self) -> str:
        return "\n".join(text for _, text in self.verses)


def local_excerpt(
    reader: Reader,
    start: str,
    end: str | None = None,
    *,
    source_system: str = "openbible",
    limit: int = 6,
    chapter_cache: dict[tuple[str, str], Chapter] | None = None,
) -> LocalExcerpt:
    """Map each source verse; never bridge discontinuities using only endpoints."""
    end = end or start

    def native_span() -> Iterator[str]:
        if source_system == reader.versification and getattr(reader, "addresses", None):
            yield from reader.reference_range(start, end)
            return
        source = Canon(source_system)
        key = source.key(start)
        upper = source.key(end).getIndex()
        if key.getIndex() > upper:
            raise ValueError("Reversed passage")
        while key.getIndex() <= upper:
            yield key.getOSISRef()
            key.increment()
            if key.popError() != "\x00":
                break

    source = reference_span(start, end) if source_system == "openbible" else native_span()
    refs: list[str] = []
    seen = set()
    more = False
    for reference in source:
        mapped = (
            destination(reference, reader)
            if source_system == "openbible"
            else resolve(reference, source_system, reader)
        )
        if getattr(reader, "addresses", None):
            for ref in reader.reference_range(mapped.start, mapped.end):
                if ref not in seen:
                    if len(refs) >= limit:
                        more = True
                        break
                    if not reader.has_reference(ref):
                        raise ValueError("Passage unavailable: " + ref)
                    refs.append(ref)
                    seen.add(ref)
            if more:
                break
            continue
        target = reader.key(mapped.start)
        last = reader.key(mapped.end).getIndex()
        while target.getIndex() <= last:
            ref = target.getOSISRef()
            if ref not in seen:
                if len(refs) >= limit:
                    more = True
                    break
                if not reader.has_reference(ref):
                    raise ValueError("Passage unavailable: " + ref)
                refs.append(ref)
                seen.add(ref)
            target.increment()
            if target.popError() != "\x00":
                break
        if more:
            break
    if not refs:
        raise ValueError("Passage unavailable")
    from .sword_provider import passage_verses

    verses = passage_verses(reader, refs, chapter_cache)
    if any(not text for _, text in verses):
        raise ValueError("Passage unavailable")
    return LocalExcerpt(refs[0], refs[-1], verses, more)
