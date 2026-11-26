"""Exact capability-based bridge through KJVA; no missing-table identity guess.

Expanded JSword data retains verse parts and absent sections. The native SWORD
canon must match the pinned data before its implicit identities can be used.
Existing native-to-native resolution remains in reference_resolution.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict, cast
from functools import lru_cache
import json
from pathlib import Path


class _Convention(TypedDict):
    system: str
    books: list[str]


class _Identity(TypedDict):
    system: str
    chapters: dict[str, list[list[int]]]


class MappingTable(TypedDict):
    """Consumed fields of existing pinned/reference-only versification metadata."""

    canon: dict[str, list[int]]
    forward: NotRequired[dict[str, list[str]]]
    reverse: NotRequired[dict[str, list[str]]]
    declared_convention: NotRequired[_Convention]
    verified_identity: NotRequired[_Identity]
    explicit_only: NotRequired[bool]
    absent: NotRequired[list[str]]


@lru_cache(maxsize=None)
def table(system: str) -> MappingTable | None:
    """Load a registered mapping only when its complete canon matches native SWORD.

    Returns:
        Cached packaged mapping data, or None when capability is unavailable.
        A resource name or equal chapter size is never evidence of equivalence.
    """
    import Sword

    # Registry comes from packaged tables, never resource/provider names.
    path = next(
        (
            p
            for p in Path(__file__).with_name("versification_data").glob("*.json")
            if p.stem == system
        ),
        None,
    )
    if path is None:
        from .source_versification import reference_mapping

        indexed = reference_mapping(system)
        if indexed is None:
            return None
        data = cast(MappingTable, indexed)
    else:
        data = cast(MappingTable, json.loads(path.read_text()))
    key = Sword.VerseKey()
    key.setVersificationSystem(system)
    # Inspect the declared index, not normalized positions in the next
    # nonempty chapter (source canons can legitimately contain zero bounds).
    key.setAutoNormalize(False)
    if key.getVersificationSystem() != system:
        return None
    canon: dict[str, list[int]] = {}
    for testament in (1, 2):
        key.setTestament(testament)
        for book in range(1, key.getBookMax() + 1):
            key.setBook(book)
            name = key.getOSISBookName()
            chapters = []
            for chapter in range(1, key.getChapterMax() + 1):
                key.setChapter(chapter)
                chapters.append(key.getVerseMax())
            canon[name] = chapters
    if canon != data["canon"]:
        return None
    return data


def valid(reference: str, data: MappingTable) -> bool:
    """Check a numeric reference against a supplied verified canon, including verse0."""
    try:
        book, chapter_text, verse_text = reference.split(".")
        chapter, verse = int(chapter_text), int(verse_text)
        sizes = data["canon"][book]
        return 1 <= chapter <= len(sizes) and 0 <= verse <= sizes[chapter - 1]
    except (ValueError, KeyError):
        return False


def verified_identity(reference: str, data: MappingTable) -> bool:
    """Explicit text-audited verse intervals, never equal-size canon inference."""
    bridge = data.get("verified_identity", {})
    try:
        chapter, verse_text = reference.rsplit(".", 1)
        verse = int(verse_text)
        return any(
            first <= verse <= last for first, last in bridge.get("chapters", {}).get(chapter, ())
        )
    except (ValueError, TypeError):
        return False


def to_base(reference: str, system: str) -> list[str] | None:
    """Return qualified KJVA references, or None if capability is unavailable."""
    data = table(system)
    base = table("KJVA")
    if data is None or base is None:
        return None
    convention = data.get("declared_convention")
    if convention:
        return (
            to_base(reference, convention["system"])
            if reference.split(".")[0] in convention["books"]
            else []
        )
    bridge = data.get("verified_identity")
    if bridge:
        return to_base(reference, bridge["system"]) if verified_identity(reference, data) else []
    if reference in data.get("forward", {}):
        result = data["forward"][reference]
        # The pinned upstream cannot unmap a qualified multi-verse range
        # (it casts it to Verse). Do not truncate it at the first '!'.
        if any("!" in ref and "-" in ref for ref in result):
            return []
        return result
    return [reference] if not data.get("explicit_only") and valid(reference, base) else []


def from_base(qualified: str, system: str) -> list[str] | None:
    """Map one qualified KJVA address through verified reverse tables.

    Returns:
        Target addresses, an empty list for an unmapped/absent address, or None
        when the target mapping capability is unavailable. Psalm-title parts
        require an explicit mapping and never fall back to a verse body.
    """
    data = table(system)
    if data is None:
        return None
    convention = data.get("declared_convention")
    if convention:
        refs = from_base(qualified, convention["system"])
        return (
            refs if refs and all(ref.split(".")[0] in convention["books"] for ref in refs) else []
        )
    bridge = data.get("verified_identity")
    if bridge:
        refs = from_base(qualified, bridge["system"])
        return refs if refs and all(verified_identity(ref, data) for ref in refs) else []
    reverse = data.get("reverse", {})
    # An ordinary numbered source verse denotes its body, not an aggregate
    # that also contains separately numbered titles in the destination.
    if "!" not in qualified and qualified + "!v" in reverse:
        return reverse[qualified + "!v"]
    if qualified in reverse:
        return reverse[qualified]
    whole = qualified.split("!", 1)[0]
    # A Psalm title may only use an explicit title mapping, never a fallback
    # onto the whole verse's body.
    if "!pv" in qualified:
        return []
    if whole in reverse:
        return reverse[whole]
    if qualified.startswith("?") or whole in data.get("absent", ()):
        return []
    return [whole] if not data.get("explicit_only") and valid(whole, data) else []
