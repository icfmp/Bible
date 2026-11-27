"""Native keys whose public reference retains an explicit source section ID."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Self, cast
import re
from .source_sections import SECTION

if TYPE_CHECKING:
    import Sword
    from .source_units import AddressIndex, ChapterUnits
    from .source_sections import SectionIndex

    class PublicVerseKey(Sword.VerseKey):
        """Static view of the existing native subclass with public source chapter IDs."""

        # This existing Python projection deliberately widens chapter IDs to
        # retain source sections. C++ still reads the ordinary integer fields.
        def getChapter(self) -> int | str: ...  # type: ignore[override]
        def getUpperBound(self) -> Self: ...
        def getLowerBound(self) -> Self: ...


class VerseKeyBindings(Protocol):
    """Native key constructor supplied by the already loaded SWORD binding."""

    @property
    def VerseKey(self) -> type[Sword.VerseKey]: ...


def key_type(
    sword: VerseKeyBindings, index: SectionIndex | AddressIndex, system: str
) -> type[PublicVerseKey]:
    """Build once per verified index; do not replace SWORD's global key class.

    C++ receives the ordinary native storage fields. Python callers receive the
    original section reference. Both conversions use the same explicit table.
    """

    import Sword

    class SourceKey(Sword.VerseKey):
        _public_alias: str | None

        def __init__(self, value: str | Sword.SWKey | None = None) -> None:
            if value is None or isinstance(value, str):
                super().__init__()
                self.setVersificationSystem(system)
                self.setAutoNormalize(False)
                if self.getVersificationSystem() != system:
                    raise ValueError("Source numbering unavailable")
                if isinstance(value, str):
                    self.setText(value)
            else:
                super().__init__(value)
                if self.getVersificationSystem() != system:
                    raise ValueError("Source key context differs")
                self._public_alias = value.getOSISRef() if isinstance(value, SourceKey) else None

        def setText(self, value: str) -> None:
            match = (
                re.fullmatch(rf"(.+?)[ .]+({SECTION})(?:[.:](0|[1-9][0-9]{{0,3}}))?", value.strip())
                if isinstance(value, str)
                else None
            )
            if not match:
                raise ValueError("Invalid source reference")
            book, chapter, verse = match.groups()
            # Resolve only the book spelling here. Parsing the source's chapter
            # through native storage first could clamp or reinterpret its ID.
            probe = sword.VerseKey()
            probe.setVersificationSystem(system)
            probe.setAutoNormalize(False)
            probe.setText(book + ".1.1")
            if probe.popError() != "\x00":
                raise ValueError("Invalid source book")
            source = (
                probe.getOSISBookName() + "." + chapter + ("." + verse if verse is not None else "")
            )
            if verse is None:
                chapters: dict[str, ChapterUnits] = getattr(index, "chapters", {})
                description = chapters.get(source)
                if description:
                    source = description.units[0].members[0]
            super().setText(index.to_native(source, allow_zero=True))
            self._public_alias = source if source.count(".") == 2 else source + ".1"

        def getOSISRef(self) -> str:
            native = super().getOSISRef()
            alias: str | None = getattr(self, "_public_alias", None)
            if native.split(".")[1] == "0":
                return native
            if alias and index.to_native(alias, allow_zero=True) == native:
                return alias
            return index.to_source(native, allow_zero=True)

        def getChapter(self) -> int | str:  # type: ignore[override]
            # Preserve the public section ID; never replace it with a storage slot.
            chapter = self.getOSISRef().split(".")[1]
            return chapter if "_" in chapter else int(chapter)

        def getVerse(self) -> int:
            return int(self.getOSISRef().split(".")[2])

        def getVerseMax(self) -> int:
            chapter = self.getOSISRef().rsplit(".", 1)[0]
            chapters: dict[str, ChapterUnits] = getattr(index, "chapters", {})
            units = chapters.get(chapter)
            return (
                max(int(ref.rsplit(".", 1)[1]) for ref in units.inventory)
                if units
                else super().getVerseMax()
            )

        def setVerse(self, number: int | str) -> None:
            self.setText(self.getOSISRef().rsplit(".", 1)[0] + "." + str(number))

        def setChapter(self, number: int | str) -> None:
            if number == 0:
                self._public_alias = None
                super().setChapter(0)
                return
            self.setText(self.getOSISBookName() + "." + str(number) + ".1")

        def getUpperBound(self) -> Self:
            return type(self)(super().getUpperBound())

        def getLowerBound(self) -> Self:
            return type(self)(super().getLowerBound())

    # Both classes describe the same native subclass API; the public view
    # exists only for typing and registers no additional native class.
    return cast("type[PublicVerseKey]", SourceKey)
