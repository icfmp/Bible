"""Resolve verified native/table capabilities without guessing verse identities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, cast, overload
from dataclasses import dataclass

if TYPE_CHECKING:
    import Sword
    from .source_section_key import PublicVerseKey
    from .sword_provider import Reader


class VersificationMismatch(ValueError):
    """A source/target correspondence could not be established with verified data."""

    pass


MAPPED_SYSTEMS = frozenset(
    {"KJV", "KJVA", "Segond", "DarbyFr", "Calvin", "NRSV", "Synodal", "Vulg"}
)


@dataclass(frozen=True)
class ResolvedPassage[T: str | None]:
    """A verified range whose endpoints are non-null in ordinary verse resolution.

    Explicit introduction projection may return two null endpoints while
    retaining the actual introduction references separately.
    """

    start: T
    end: T
    introductions: tuple[str, ...] = ()


class ReferenceSpace(Protocol):
    """A numbered key space; a canon alone does not claim installed entries."""

    versification: str

    def key(self, reference: str) -> Sword.VerseKey | PublicVerseKey: ...


class _EntrySpace(ReferenceSpace, Protocol):
    def has_reference(self, reference: str) -> bool: ...


class _IndexedSpace(ReferenceSpace, Protocol):
    def reference_range(self, start: str, end: str) -> tuple[str, ...]: ...


def resolve_readers(
    reference: str, source_reader: Reader, target_reader: Reader, require_entry: bool = True
) -> ResolvedPassage[str]:
    """A registry transform alone cannot attest an edition's source numbering."""
    same = source_reader.root == target_reader.root and source_reader.name == target_reader.name
    if not same and not source_reader.can_align_reference(reference):
        raise VersificationMismatch("Source numbering is not verified: " + reference)
    result = resolve(reference, source_reader.versification, target_reader, require_entry=False)
    references = _span(result.start, result.end, target_reader.versification, target_reader)
    if not same and not all(target_reader.can_align_reference(ref) for ref in references):
        raise VersificationMismatch("Target numbering is not verified: " + reference)
    if require_entry and any(not target_reader.has_reference(ref) for ref in references):
        raise ValueError("Passage unavailable: " + result.start)
    return result


@overload
def resolve(
    reference: str,
    source_system: str,
    target_reader: ReferenceSpace,
    require_entry: bool = True,
    *,
    include_introductions: Literal[False] = False,
) -> ResolvedPassage[str]: ...


@overload
def resolve(
    reference: str,
    source_system: str,
    target_reader: ReferenceSpace,
    require_entry: bool = True,
    *,
    include_introductions: bool,
) -> ResolvedPassage[str | None]: ...


def resolve(
    reference: str,
    source_system: str,
    target_reader: ReferenceSpace,
    require_entry: bool = True,
    *,
    include_introductions: bool = False,
) -> ResolvedPassage[str | None]:
    """Resolve one source reference using verified native or packaged capabilities.

    Never equate numbering by label alone or truncate a noncontiguous result.
    When requested, introductions are returned separately from numbered verses.

    Args:
        reference: Canonical or supported book/chapter/verse input.
        source_system: Declared numbering system of the input.
        target_reader: Target key space. With require_entry, supply a reader
            exposing installed-entry availability, not a bare canon.
        require_entry: Require each mapped target entry to exist locally.
        include_introductions: Retain explicitly mapped introduction contexts.

    Returns:
        A ResolvedPassage in the target numbering system.

    Raises:
        VersificationMismatch: Verified correspondence is unavailable or incomplete.
        ValueError: The input is invalid or a required target entry is absent.
    """
    import re
    import Sword
    from .book_names import canonical_input

    reference = canonical_input(reference)
    target_system = target_reader.versification
    # Entry availability is required only on the require_entry path. Bare
    # canonical spaces deliberately expose no installed-resource capability.
    entries = cast("_EntrySpace", target_reader)
    if source_system == target_system and getattr(target_reader, "addresses", None):
        key = target_reader.key(reference)
        public = key.getOSISRef()
        if require_entry and not entries.has_reference(public):
            raise ValueError("Passage unavailable: " + public)
        return ResolvedPassage(public, public)
    if "_" in reference:
        raise VersificationMismatch(
            f"No verified source section alignment: {source_system} {reference} / {target_system}"
        )
    if not re.fullmatch(
        r"(?:[1-5]\s*)?[A-Za-z][A-Za-z0-9]*(?: [A-Za-z]+)*[ .]+[1-9][0-9]*(?:[.:][1-9][0-9]*)?",
        reference,
    ):
        raise ValueError(f"Invalid source reference: {reference}")
    source = Sword.VerseKey()
    source.setVersificationSystem(source_system)
    if source.getVersificationSystem() != source_system:
        raise VersificationMismatch(source_system)
    source.setAutoNormalize(False)
    source.setText(reference)
    if (
        source.popError() != "\x00"
        or not 1 <= source.getChapter() <= source.getChapterMax()
        or not 1 <= source.getVerse() <= source.getVerseMax()
    ):
        raise ValueError(f"Invalid source reference: {reference}")
    # Native SWORD can collapse numbered Psalm titles onto verse one and lose
    # split verse parts. Prefer the existing qualified tables when their
    # complete canons match this runtime; retain native-only capabilities.
    pinned = False
    if source_system != target_system:
        from .versification_mapping import table

        pinned = table(source_system) is not None and table(target_system) is not None
    if source_system != target_system and (
        pinned or not {source_system, target_system} <= MAPPED_SYSTEMS
    ):
        from .versification_mapping import to_base, from_base

        reference = source.getOSISRef()
        intermediate = to_base(reference, source_system)
        if intermediate is None and source_system in MAPPED_SYSTEMS:
            intermediate = _native_refs(source, "KJVA")
        if not intermediate:
            raise VersificationMismatch(
                f"No verified alignment: {source_system} {reference} / {target_system}"
            )
        references = []
        for qualified in intermediate:
            mapped = from_base(qualified, target_system)
            if (
                mapped is None
                and target_system in MAPPED_SYSTEMS
                and not qualified.startswith("?")
                and "!" not in qualified
            ):
                base = Sword.VerseKey()
                base.setVersificationSystem("KJVA")
                base.setAutoNormalize(False)
                base.setText(qualified)
                mapped = _native_refs(base, target_system)
            # A partially mapped result is not an exact alignment either.
            if not mapped:
                raise VersificationMismatch(
                    f"No verified alignment: {source_system} {reference} / {target_system}"
                )
            references.extend(mapped)
        introductions: tuple[str, ...] = ()
        if include_introductions:
            contexts = []
            verses = []
            for ref in references:
                if ref.endswith(".0"):
                    introduction_key(
                        ref, target_reader
                    )  # Validate a real native context, never clamp it.
                    contexts.append(ref)
                else:
                    verses.append(ref)
            introductions = tuple(dict.fromkeys(contexts))
            references = verses
            if not references:
                return ResolvedPassage(None, None, introductions)
        try:
            ordered = sorted(set(references), key=lambda ref: target_reader.key(ref).getIndex())
            if _span(ordered[0], ordered[-1], target_system) != ordered:
                raise VersificationMismatch(
                    f"Non-contiguous alignment: {source_system} {reference} / {target_system}"
                )
        except ValueError as error:
            raise VersificationMismatch(str(error)) from error
        if require_entry and any(not entries.has_reference(ref) for ref in ordered):
            raise ValueError(f"Passage unavailable: {ordered[0]}–{ordered[-1]}")
        return ResolvedPassage(ordered[0], ordered[-1], introductions)
    target = Sword.VerseKey()
    target.setVersificationSystem(target_system)
    target.setAutoNormalize(False)
    # positionFrom preserves the destination system and invokes translateVerse.
    # copy construction/copyFrom instead copies the source system.
    target.positionFrom(source)
    native_error = target.popError()
    if (
        native_error == "\x00"
        and target.getVerse() == 0
        and include_introductions
        and not target.isBoundSet()
    ):
        context = f"{target.getOSISBookName()}.{target.getChapter()}.0"
        introduction_key(context, target_reader)
        return ResolvedPassage(None, None, (context,))
    if native_error != "\x00" or target.getVerse() < 1:
        raise VersificationMismatch(f"No verse alignment: {reference}")
    start = target.getOSISRef()
    end = target.getUpperBound().getOSISRef() if target.isBoundSet() else start
    target_reader.key(start)
    target_reader.key(end)
    if require_entry and (not entries.has_reference(start) or not entries.has_reference(end)):
        raise ValueError(f"Passage unavailable: {start}" + (f"–{end}" if end != start else ""))
    return ResolvedPassage(start, end)


def _span(start: str, end: str, system: str, reader: ReferenceSpace | None = None) -> list[str]:
    """Enumerate actual consecutive verses, excluding introductions."""
    if reader is not None and system == reader.versification and getattr(reader, "addresses", None):
        return list(cast("_IndexedSpace", reader).reference_range(start, end))
    import Sword

    key = Sword.VerseKey()
    key.setVersificationSystem(system)
    key.setText(start)
    refs = []
    for _ in range(100000):
        reference = key.getOSISRef()
        if key.getVerse() > 0:
            refs.append(reference)
        if reference == end:
            return refs
        key.increment()
        if key.popError() != "\x00":
            break
    raise VersificationMismatch(f"Invalid alignment range: {start}–{end}")


def _native_refs(source: Sword.VerseKey, system: str) -> list[str]:
    """Return only complete native verse ranges; failed mappings stay unavailable."""
    import Sword

    target = Sword.VerseKey()
    target.setVersificationSystem(system)
    target.setAutoNormalize(False)
    target.positionFrom(source)
    if target.popError() != "\x00" or target.getVerse() < 1:
        return []
    start = target.getOSISRef()
    end = target.getUpperBound().getOSISRef() if target.isBoundSet() else start
    return _span(start, end, system)


def available_chapter(reference: str, reader: Reader) -> str | None:
    """Explicit opening only: printed chapter availability is not verse alignment."""
    from .book_names import canonical_input

    parts = canonical_input(reference).split(".")
    if len(parts) != 3:
        return None
    book, chapter_text, _ = parts
    try:
        chapter: str | int = chapter_text if "_" in chapter_text else int(chapter_text)
    except ValueError:
        return None
    entry = next((item for item in reader.books if item.code == book), None)
    verses = entry.chapters.get(chapter) if entry else None
    if not verses:
        return None
    order = reader.source_verse_order.get(f"{book}.{chapter}", verses)
    return f"{book}.{chapter}.{order[0]}"


def introduction_key(reference: str, reader: ReferenceSpace) -> Sword.VerseKey:
    """Validate explicitly mapped chapter context independently of ordinary verses."""
    import re
    import Sword

    match = re.fullmatch(r"([1-5]?[A-Za-z][A-Za-z0-9]*)\.([1-9][0-9]*)\.0", reference)
    if not match:
        raise VersificationMismatch("Unsupported introduction context: " + reference)
    key = Sword.VerseKey()
    key.setVersificationSystem(reader.versification)
    key.setIntros(True)
    key.setAutoNormalize(False)
    key.setText(reference)
    if (
        key.popError() != "\x00"
        or key.getOSISBookName() != match[1]
        or key.getChapter() != int(match[2])
        or key.getVerse() != 0
    ):
        raise VersificationMismatch("Invalid introduction context: " + reference)
    return key
