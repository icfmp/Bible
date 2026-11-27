"""Explicit source chapter identities over a bounded native storage index.

Some editions declare multiple canonical chapter sections with the same printed
number. Keep their distinct source IDs and flags. Native storage coordinates are
private implementation details, never a substitute for the source reference.
This module does not interpret headings, infer verse equivalence, or store text.
"""

from collections.abc import Iterable
from typing import Any, Literal, Self, TypedDict, cast

from dataclasses import dataclass
import re


class SourceChapterRecord(TypedDict):
    """Serialized section metadata; storage is absent for introductions."""

    reference: str
    human: str
    canonical: bool
    storage: str | None


class SectionData(TypedDict):
    """Existing version-one section sidecar, without resource text."""

    schema: Literal[1]
    chapters: list[SourceChapterRecord]


BOOK = r"[1-5]?[A-Za-z][A-Za-z0-9]{0,15}"
SECTION = r"[1-9][0-9]{0,5}(?:_[1-9][0-9]{0,5})?"
CHAPTER = re.compile(rf"({BOOK})\.({SECTION}|INTRO[1-9][0-9]{{0,2}})")
ADDRESS = re.compile(rf"({BOOK}\.{SECTION})(?:\.(0|[1-9][0-9]{{0,3}}))?")
NATIVE_CHAPTER = re.compile(rf"({BOOK})\.([1-9][0-9]{{0,2}})")


@dataclass(frozen=True)
class SourceChapter:
    """Explicit source chapter-section identity, printed label and supplied canonical flag."""

    reference: str
    human: str
    canonical: bool

    def __post_init__(self) -> None:
        match = CHAPTER.fullmatch(self.reference) if isinstance(self.reference, str) else None
        if not match or type(self.canonical) is not bool:
            raise ValueError("Invalid source chapter identity")
        if self.canonical == match[2].startswith("INTRO"):
            raise ValueError("Source chapter role differs from its identity")
        if (
            not isinstance(self.human, str)
            or not self.human.strip()
            or len(self.human) > 256
            or any(ord(c) < 32 for c in self.human)
        ):
            raise ValueError("Invalid source chapter label")

    @property
    def book(self) -> str:
        return self.reference.split(".")[0]


class SectionIndex:
    """One-to-one canonical sections; introduction metadata stays explicit."""

    def __init__(self, chapters: Iterable[SourceChapter], storage: Iterable[str | None]) -> None:
        self.chapters = tuple(chapters)
        self.storage = tuple(storage)
        if not 1 <= len(self.chapters) <= 10000 or len(self.storage) != len(self.chapters):
            raise ValueError("Invalid source section inventory")
        self.forward: dict[str, str] = {}
        self.reverse: dict[str, str] = {}
        self.labels: dict[str, str] = {}
        self.order: dict[str, list[str]] = {}
        seen = set()
        for chapter, native in zip(self.chapters, self.storage):
            if not isinstance(chapter, SourceChapter) or chapter.reference in seen:
                raise ValueError("Duplicate or invalid source section")
            seen.add(chapter.reference)
            if not chapter.canonical:
                if native is not None:
                    raise ValueError("An introduction cannot acquire a canonical storage verse")
                continue
            match = NATIVE_CHAPTER.fullmatch(native) if isinstance(native, str) else None
            if (
                not match
                or match[1] != chapter.book
                or int(match[2]) > 255
                or native in self.reverse
            ):
                raise ValueError("Invalid or overlapping source storage coordinate")
            native = cast("str", native)  # The full-match guard above proved a string.
            self.forward[chapter.reference] = native
            self.reverse[native] = chapter.reference
            self.labels[chapter.reference] = chapter.human
            self.order.setdefault(chapter.book, []).append(chapter.reference)
        if not self.forward or len(self.order) > 100:
            raise ValueError("Invalid canonical source inventory")

    @classmethod
    def allocate(cls, chapters: Iterable[SourceChapter]) -> Self:
        """Assign private per-book slots in the explicit metadata order."""
        chapters = tuple(chapters)
        counts: dict[str, int] = {}
        storage: list[str | None] = []
        for chapter in chapters:
            if not isinstance(chapter, SourceChapter):
                raise ValueError("Invalid source chapter")
            if not chapter.canonical:
                storage.append(None)
                continue
            counts[chapter.book] = counts.get(chapter.book, 0) + 1
            storage.append(f"{chapter.book}.{counts[chapter.book]}")
        return cls(chapters, storage)

    def transform(self, reference: str, *, inverse: bool = False, allow_zero: bool = False) -> str:
        """Map checked source/storage chapter identities while preserving the explicit verse number.

        Indexed books reject unknown sections; this storage transform establishes
        no equivalence to another edition or numbering convention.
        """
        match = ADDRESS.fullmatch(reference) if isinstance(reference, str) else None
        if not match:
            raise ValueError("Invalid source section reference")
        chapter, verse = match.groups()
        if verse is not None and not (0 if allow_zero else 1) <= int(verse) <= 2000:
            raise ValueError("Invalid source verse number")
        table = self.reverse if inverse else self.forward
        book = chapter.split(".")[0]
        if book in self.order:
            if chapter not in table:
                raise ValueError("Unindexed source chapter section")
            chapter = table[chapter]
        elif "_" in chapter:
            raise ValueError("Unindexed source chapter section")
        return chapter + ("." + verse if verse is not None else "")

    def to_native(self, reference: str, *, allow_zero: bool = False) -> str:
        return self.transform(reference, allow_zero=allow_zero)

    def to_source(self, reference: str, *, allow_zero: bool = False) -> str:
        return self.transform(reference, inverse=True, allow_zero=allow_zero)

    def data(self) -> SectionData:
        return dict(
            schema=1,
            chapters=[
                dict(reference=c.reference, human=c.human, canonical=c.canonical, storage=n)
                for c, n in zip(self.chapters, self.storage)
            ],
        )

    @classmethod
    def from_data(cls, value: Any) -> Self:
        """Validate the versioned source-section inventory and construct its checked bidirectional index."""
        if (
            not isinstance(value, dict)
            or set(value) != {"schema", "chapters"}
            or type(value["schema"]) is not int
            or value["schema"] != 1
        ):
            raise ValueError("Unsupported source section index")
        rows = value["chapters"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
            raise ValueError("Invalid source section inventory")
        chapters = []
        storage: list[str | None] = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "reference",
                "human",
                "canonical",
                "storage",
            }:
                raise ValueError("Invalid source section record")
            chapters.append(SourceChapter(row["reference"], row["human"], row["canonical"]))
            storage.append(row["storage"])
        return cls(chapters, storage)
