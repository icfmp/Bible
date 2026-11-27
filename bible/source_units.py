"""Sparse reference-only descriptions of overlapping source verse fragments.

Units are in presentation order. One unit may belong to several public verses;
one verse may cover several units. This is deliberately not a linked-verse map:
partially shared text cannot be represented by identical complete entries.
No Scripture text is stored here or inferred from printed verse labels.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from os import PathLike
from typing import TYPE_CHECKING, Literal, Self, TypedDict, cast
from dataclasses import dataclass, replace

if TYPE_CHECKING:
    from .youversion_osis import Document, Node
    from .youversion_source import Edition
import re
from .source_sections import ADDRESS, SECTION, SectionData, SectionIndex


class _UnitRecord(TypedDict):
    members: list[str]
    label: str


class ChapterUnitData(TypedDict):
    """Existing reference-only fragment membership record; never resource text."""

    reference: str
    units: list[_UnitRecord]


class AddressData(TypedDict):
    """Existing version-one section and fragment index envelope."""

    schema: Literal[1]
    sections: SectionData | None
    chapters: list[ChapterUnitData]


def source_reference(value: str) -> str:
    """Convert an explicit supplied source book/address to the supported OSIS identity without guessing labels."""
    from .youversion_osis import BOOKS

    items = value.split(".")
    if len(items) not in (2, 3) or items[0] not in BOOKS:
        raise ValueError("Invalid explicit source reference")
    result = ".".join((BOOKS[items[0]], *items[1:]))
    if not ADDRESS.fullmatch(result):
        raise ValueError("Invalid explicit source reference")
    return result


@dataclass(frozen=True)
class SourceUnit:
    """One ordered source fragment with its actual member references and printed label."""

    members: tuple[str, ...]
    label: str


class ChapterUnits:
    """Ordered source fragments and their many-to-many memberships within an explicit source chapter."""

    def __init__(self, reference: str, units: Iterable[SourceUnit]) -> None:
        if not isinstance(reference, str) or not re.fullmatch(
            rf"[1-5]?[A-Za-z][A-Za-z0-9]{{0,15}}\.{SECTION}", reference
        ):
            raise ValueError("Invalid source unit chapter")
        self.reference = reference
        self.units = tuple(units)
        self.by_reference: dict[str, list[int]] = {}
        if not 1 <= len(self.units) <= 2000:
            raise ValueError("Invalid source unit count")
        for position, unit in enumerate(self.units, 1):
            if (
                not isinstance(unit, SourceUnit)
                or not 1 <= len(unit.members) <= 2000
                or len(set(unit.members)) != len(unit.members)
                or not isinstance(unit.label, str)
                or len(unit.label) > 256
                or any(ord(c) < 32 for c in unit.label)
            ):
                raise ValueError("Invalid source unit record")
            for member in unit.members:
                match = ADDRESS.fullmatch(member) if isinstance(member, str) else None
                if (
                    not match
                    or match[1] != reference
                    or match[2] is None
                    or not 1 <= int(match[2]) <= 2000
                ):
                    raise ValueError("Source unit crosses chapter or has invalid verse")
                self.by_reference.setdefault(member, []).append(position)
        self.inventory = tuple(
            sorted(self.by_reference, key=lambda ref: int(ref.rsplit(".", 1)[1]))
        )

    @property
    def overlaps(self) -> bool:
        """Report when one public verse belongs to several ordered source fragments."""
        return any(len(positions) > 1 for positions in self.by_reference.values())

    @staticmethod
    def verse_nodes(document: Document) -> Iterator[Node]:
        """Yield actual verse nodes in source document order, including those nested in supported structures."""
        from .youversion_osis import Node

        def walk(parts: Iterable[str | Node]) -> Iterator[Node]:
            for part in parts:
                if not isinstance(part, Node):
                    continue
                if part.kind == "verse":
                    yield part
                else:
                    yield from walk(part.parts)

        return walk(document.blocks)

    @classmethod
    def from_document(cls, document: Document) -> Self:
        """Collect consecutive source fragment memberships and labels without inferring them from visible text."""
        from .youversion_osis import Node, plain

        groups = []
        previous: tuple[str, ...] | None = None
        chapter = source_reference(document.reference)
        for node in cls.verse_nodes(document):
            source = node.attrs.get("data-usfm", "")
            members = tuple(source_reference(ref) for ref in source.split("+"))
            if members != previous:
                label = next(
                    (
                        plain(p).strip()
                        for p in node.parts
                        if isinstance(p, Node) and p.kind == "label"
                    ),
                    "",
                )
                groups.append(SourceUnit(members, label))
                previous = members
        return cls(chapter, groups)

    def storage_document(self, document: Document, native_chapter: str) -> Document:
        """Assign each contiguous unit once, retaining every ordered source node."""
        from .youversion_osis import Node, BOOKS

        # Native OSIS conversion consumes USFM book codes, not OSIS book names.
        inverse = {value: key for key, value in BOOKS.items()}
        book, number = native_chapter.split(".")
        if book != self.reference.split(".")[0] or not number.isdigit():
            raise ValueError("Invalid native unit chapter")
        native_source = inverse[book] + "." + number
        position = 0
        previous: tuple[str, ...] | None = None

        def clone(part: str | Node) -> str | Node:
            nonlocal position, previous
            if not isinstance(part, Node):
                return part
            attrs = dict(part.attrs)
            if part.kind == "verse":
                members = tuple(
                    source_reference(ref) for ref in attrs.get("data-usfm", "").split("+")
                )
                if members != previous:
                    position += 1
                    previous = members
                if position > len(self.units) or members != self.units[position - 1].members:
                    raise ValueError("Source units changed during conversion")
                attrs["data-usfm"] = native_source + "." + str(position)
            return Node(part.kind, attrs, [clone(child) for child in part.parts])

        value = replace(
            document,
            reference=native_source,
            blocks=[cast("Node", clone(block)) for block in document.blocks],
        )
        if position != len(self.units):
            raise ValueError("Incomplete source unit conversion")
        return value

    def data(self) -> ChapterUnitData:
        return dict(
            reference=self.reference,
            units=[dict(members=list(u.members), label=u.label) for u in self.units],
        )

    @classmethod
    def from_data(cls, value: object) -> Self:
        """Validate serialized fragment records before constructing their reference membership index."""
        if (
            not isinstance(value, dict)
            or set(value) != {"reference", "units"}
            or not isinstance(value["units"], list)
        ):
            raise ValueError("Invalid source units")
        units = []
        for row in value["units"]:
            if (
                not isinstance(row, dict)
                or set(row) != {"members", "label"}
                or not isinstance(row["members"], list)
            ):
                raise ValueError("Invalid source unit record")
            units.append(SourceUnit(tuple(row["members"]), row["label"]))
        return cls(value["reference"], units)


class AddressIndex:
    """Public chapter/verse IDs over private chapter and ordered-unit slots."""

    def __init__(
        self, sections: SectionIndex | None = None, chapters: Iterable[ChapterUnits] = ()
    ) -> None:
        if sections is not None and not isinstance(sections, SectionIndex):
            raise ValueError("Invalid source section index")
        self.sections = sections
        self.chapters: dict[str, ChapterUnits] = {}
        for chapter in chapters:
            if not isinstance(chapter, ChapterUnits) or chapter.reference in self.chapters:
                raise ValueError("Duplicate source unit chapter")
            self.chapters[chapter.reference] = chapter
        if len(self.chapters) > 10000:
            raise ValueError("Too many source unit chapters")

    def native_chapter(self, reference: str) -> str:
        book = reference.split(".")[0]
        if self.sections and book in self.sections.order:
            return self.sections.to_native(reference)
        # Disjoint physical parts retain the existing joined-chapter contract.
        return reference.split("_")[0]

    def source_chapter(self, reference: str) -> str:
        return self.sections.to_source(reference) if self.sections else reference

    def to_native(self, reference: str, *, allow_zero: bool = False) -> str:
        """Resolve an explicit source address to its first native storage unit, rejecting unindexed references."""
        match = ADDRESS.fullmatch(reference) if isinstance(reference, str) else None
        if not match:
            raise ValueError("Invalid source address")
        chapter, verse = match.groups()
        if verse is None:
            return self.native_chapter(chapter)
        if not (0 if allow_zero else 1) <= int(verse) <= 2000:
            raise ValueError("Invalid source verse")
        units = self.chapters.get(chapter)
        if units and verse != "0":
            if reference not in units.by_reference:
                raise ValueError("Unindexed source verse")
            verse = str(units.by_reference[reference][0])
        return self.native_chapter(chapter) + "." + verse

    def to_sources(self, reference: str, *, allow_zero: bool = False) -> tuple[str, ...]:
        """Return all explicit source members of a native storage unit without inventing one-to-one equivalence."""
        match = ADDRESS.fullmatch(reference) if isinstance(reference, str) else None
        if not match:
            raise ValueError("Invalid native address")
        chapter, verse = match.groups()
        chapter = self.source_chapter(chapter)
        if verse is None:
            return (chapter,)
        if not (0 if allow_zero else 1) <= int(verse) <= 2000:
            raise ValueError("Invalid native verse")
        units = self.chapters.get(chapter)
        if units and verse != "0":
            if not 1 <= int(verse) <= len(units.units):
                raise ValueError("Unindexed native source unit")
            return units.units[int(verse) - 1].members
        return (chapter + "." + verse,)

    def to_source(self, reference: str, *, allow_zero: bool = False) -> str:
        return self.to_sources(reference, allow_zero=allow_zero)[0]

    def storage_document(self, document: Document) -> Document:
        """Transform only indexing identities; leave content/roles and links intact."""
        from .youversion_osis import BOOKS, Node

        public = source_reference(document.reference)
        native = self.native_chapter(public)
        if public in self.chapters:
            return self.chapters[public].storage_document(document, native)
        if native == public:
            return document
        inverse = {value: key for key, value in BOOKS.items()}

        def usfm(reference: str) -> str:
            fields = reference.split(".")
            return ".".join((inverse[fields[0]], *fields[1:]))

        def clone(part: str | Node) -> str | Node:
            if not isinstance(part, Node):
                return part
            attrs = dict(part.attrs)
            if part.kind == "verse":
                attrs["data-usfm"] = "+".join(
                    usfm(self.to_native(source_reference(ref)))
                    for ref in attrs.get("data-usfm", "").split("+")
                )
            return Node(part.kind, attrs, [clone(child) for child in part.parts])

        return replace(
            document,
            reference=usfm(native),
            blocks=[cast("Node", clone(block)) for block in document.blocks],
        )

    def data(self) -> AddressData:
        return dict(
            schema=1,
            sections=self.sections.data() if self.sections else None,
            chapters=[c.data() for c in self.chapters.values()],
        )

    @classmethod
    def from_data(cls, value: object) -> Self:
        """Validate the versioned section/fragment envelope before constructing checked address maps."""
        if (
            not isinstance(value, dict)
            or set(value) != {"schema", "sections", "chapters"}
            or type(value["schema"]) is not int
            or value["schema"] != 1
            or not isinstance(value["chapters"], list)
        ):
            raise ValueError("Invalid source address index")
        return cls(
            SectionIndex.from_data(value["sections"]) if value["sections"] is not None else None,
            (ChapterUnits.from_data(c) for c in value["chapters"]),
        )

    @classmethod
    def load(cls, root: str | PathLike[str]) -> Self | None:
        """Read the bounded local address sidecar only when its receipt digest agrees.

        Return None when no index was declared; a missing declared sidecar or
        modified bytes fail explicitly instead of enabling guessed alignment.
        """
        import hashlib
        import json
        from pathlib import Path

        root = Path(root)
        path = root / ".source-addresses.json"
        receipt = root / ".verified.json"
        if not path.exists():
            if receipt.is_file() and json.loads(receipt.read_text()).get("source_addresses_sha256"):
                raise ValueError("Missing verified source address index")
            return None
        if (
            path.is_symlink()
            or path.stat().st_size > 8 * 1024 * 1024
            or receipt.is_symlink()
            or receipt.stat().st_size > 16384
        ):
            raise ValueError("Invalid source address index")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != json.loads(receipt.read_text()).get(
            "source_addresses_sha256"
        ):
            raise ValueError("Source address index changed")
        return cls.from_data(json.loads(raw))


def plan_addresses(archive: str | PathLike[str], edition: Edition) -> AddressIndex | None:
    """Preflight reference structure, retaining no chapter trees or source text."""
    from .youversion_source import archive_chapters, source_document
    from .source_sections import SourceChapter

    seen: dict[str, set[str]] = {}
    overlapping_books = set()
    units = []
    for chapter in archive_chapters(archive, edition, complete=True):
        if ".INTRO" in chapter["reference"]:
            continue
        doc = source_document(chapter, edition)
        inventory = ChapterUnits.from_document(doc)
        if inventory.overlaps:
            units.append(inventory)
        public = inventory.reference
        book, number = public.split(".")
        base = book + "." + number.split("_")[0]
        members = {ref.rsplit(".", 1)[1] for ref in inventory.by_reference}
        if seen.get(base, set()) & members:
            overlapping_books.add(book)
        seen.setdefault(base, set()).update(members)
    chapters = []
    for book in edition.metadata["books"]:
        from .youversion_osis import BOOKS

        if not book["text"] or BOOKS[book["usfm"]] not in overlapping_books:
            continue
        for entry in book["chapters"]:
            original = entry["usfm"]
            reference = BOOKS[book["usfm"]] + "." + original.split(".")[1]
            human = entry.get("human") or original.split(".")[1]
            chapters.append(SourceChapter(reference, human, entry["canonical"]))
    if not chapters and not units:
        return None
    return AddressIndex(SectionIndex.allocate(chapters) if chapters else None, units)
