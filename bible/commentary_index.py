"""SWORD-native commentary sections: group only adjacent, linked index records."""
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Section:
    index: int
    last_index: int
    start: str
    end: str
    introduction: bool = False

    def contains_index(self, index):
        return self.index <= index <= self.last_index


class CommentaryIndex:
    def __init__(self, reader):
        self.reader = reader
        self.sections = []
        key = reader.sword.VerseKey()
        key.setVersificationSystem(reader.versification)
        key.setIntros(True)
        key.setIndex(0)
        previous = None
        while True:
            if reader.module.hasEntry(key):
                index, reference = key.getIndex(), key.getOSISRef()
                intro = key.getVerse() == 0
                if (previous is not None and self.sections[-1].last_index + 1 == index
                        and self.sections[-1].introduction == intro
                        and reader.module.isLinked(previous, key)):
                    old = self.sections[-1]
                    self.sections[-1] = Section(old.index,index,old.start,reference,intro)
                else:
                    self.sections.append(Section(index,index,reference,reference,intro))
                previous = reader.sword.VerseKey(key)
            key.increment()
            if key.popError() != '\x00':break
        self.starts = [s.index for s in self.sections]

    def locate(self, reference):
        index = self.reader.key(reference).getIndex()
        pos = bisect_left(self.starts,index)
        if pos < len(self.sections) and self.sections[pos].index == index:return pos
        if pos and self.sections[pos-1].contains_index(index):return pos-1
        return None

    def near(self, reference):
        return bisect_left(self.starts,self.reader.key(reference).getIndex())

    @lru_cache(maxsize=20)
    def text(self, position):
        section = self.sections[position]
        key = self.reader.sword.VerseKey()
        key.setVersificationSystem(self.reader.versification)
        key.setIntros(True);key.setIndex(section.index)
        self.reader.module.setKey(key)
        text = self.reader.module.stripText()
        return text if isinstance(text,str) else text.c_str()

    def label(self, position):
        section = self.sections[position]
        if section.introduction:
            from .i18n import tr
            return tr('Introduction') + (' — '+section.start if section.start else '')
        from .notes_window import passage_label
        return passage_label(section.start,section.end,self.reader.versification)
