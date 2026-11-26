"""Source-faithful SWORD commentary entries, including disjoint native links."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, replace
from functools import lru_cache


@dataclass(frozen=True)
class Segment:
    """One contiguous set of verse keys belonging to a native entry."""

    index: int
    last_index: int
    start: str
    end: str

    def contains_index(self, index):
        return self.index <= index <= self.last_index


@dataclass(frozen=True)
class Section:
    """One actual native commentary entry, retaining disjoint linked ranges separately."""

    index: int
    last_index: int
    start: str
    end: str
    introduction: bool = False
    segments: tuple[Segment, ...] = ()

    def contains_index(self, index):
        return (
            any(part.contains_index(index) for part in self.segments)
            if self.segments
            else (self.index <= index <= self.last_index)
        )

    @property
    def passages(self):
        """Separate ranges, never a single fictitious range over intervening notes."""
        return (
            tuple((part.start, part.end) for part in self.segments)
            if self.segments
            else ((self.start, self.end),)
        )


class CommentaryIndex:
    """Index native entry identity and introduction boundaries without grouping entries by matching text.

    Construction scans the mutable reader; keep its owning native manager
    alive and serialize reader use. Disjoint links remain separate passage
    ranges even when one physical entry supplies their common content.
    """

    def __init__(self, reader) -> None:
        self.reader = reader
        self.sections = []
        self._section_by_native_index = {}
        key = reader.sword.VerseKey()
        key.setVersificationSystem(reader.versification)
        key.setIntros(True)
        key.setIndex(0)

        previous = None
        previous_position = None
        previous_chapter = None
        chapter = None
        # Keep only this chapter's authored section anchors. Their native
        # isLinked() identity, not the visible text, distinguishes sections.
        chapter_origins = []

        while True:
            if reader.module.hasEntry(key):
                index, reference = key.getIndex(), key.getOSISRef()
                intro = key.getVerse() == 0
                # Module/testament introductions have book 0. Asking SWORD
                # for that non-existent book's name can abort in native code.
                current_chapter = (key.getTestament(), key.getBook(), key.getChapter())
                if current_chapter != chapter:
                    chapter = current_chapter
                    chapter_origins = []
                position = None
                if (
                    previous is not None
                    and (previous_chapter == current_chapter or intro)
                    and previous_position is not None
                    and self.sections[previous_position].introduction == intro
                    and previous.getIndex() + 1 == index
                    and reader.module.isLinked(previous, key)
                ):
                    position = previous_position
                elif not intro:
                    # A native section may resume after an independently
                    # authored passage (e.g. two disjoint Bible ranges).
                    # Restrict comparison to this chapter; never group simply
                    # because two different sections have identical words.
                    position = next(
                        (
                            existing
                            for existing, anchor in chapter_origins
                            if reader.module.isLinked(anchor, key)
                        ),
                        None,
                    )

                part = Segment(index, index, reference, reference)
                if position is None:
                    position = len(self.sections)
                    self.sections.append(
                        Section(index, index, reference, reference, intro, (part,))
                    )
                    if not intro:
                        chapter_origins.append((position, reader.sword.VerseKey(key)))
                else:
                    old = self.sections[position]
                    parts = old.segments
                    if parts[-1].last_index + 1 == index:
                        last = parts[-1]
                        parts = (*parts[:-1], replace(last, last_index=index, end=reference))
                    else:
                        parts = (*parts, part)
                    self.sections[position] = replace(
                        old, last_index=max(old.last_index, index), end=reference, segments=parts
                    )
                self._section_by_native_index[index] = position
                previous = reader.sword.VerseKey(key)
                previous_position = position
                previous_chapter = current_chapter
            key.increment()
            if key.popError() != "\x00":
                break
        self.starts = [s.index for s in self.sections]
        # Cache lifetime follows this native reader. A decorator on the class
        # method would keep old index/reader instances alive through its keys,
        # preventing safe module removal after the GTK owners release them.
        self.text = lru_cache(maxsize=20)(self.text)
        self.raw = lru_cache(maxsize=20)(self.raw)

    def locate(self, reference):
        # A binary search on first-section indices cannot find a later
        # disjoint segment when an independent section occurs between them.
        index = self.reader.key(reference).getIndex()
        return self._section_by_native_index.get(index)

    def near(self, reference):
        return bisect_left(self.starts, self.reader.key(reference).getIndex())

    def text(self, position):
        """Read stripped native text at the indexed entry, changing the reader module key."""
        section = self.sections[position]
        key = self.reader.sword.VerseKey()
        key.setVersificationSystem(self.reader.versification)
        key.setIntros(True)
        key.setIndex(section.index)
        self.reader.module.setKey(key)
        text = self.reader.module.stripText()
        return text if isinstance(text, str) else text.c_str()

    def raw(self, position):
        """Read actual raw markup at the indexed entry, changing the reader module key."""
        section = self.sections[position]
        key = self.reader.sword.VerseKey()
        key.setVersificationSystem(self.reader.versification)
        key.setIntros(True)
        key.setIndex(section.index)
        self.reader.module.setKey(key)
        text = self.reader.module.getRawEntry()
        return text if isinstance(text, str) else text.c_str()

    def label(self, position):
        """Label only the entry introduction or its explicit disjoint passage ranges."""
        section = self.sections[position]
        if section.introduction:
            from .i18n import tr

            return tr("Introduction") + (" — " + section.start if section.start else "")
        from .notes_window import passage_label

        return "; ".join(
            passage_label(first, last, self.reader.versification)
            for first, last in section.passages
        )
