"""Local SWORD access. No network operations or UI dependencies."""
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
import re

from .book_names import canonical_input


@dataclass(frozen=True)
class Chapter:
    reference: str
    verses: tuple[tuple[str, str], ...]
    previous: str | None
    following: str | None


@dataclass(frozen=True)
class Book:
    code: str
    name: str
    chapters: dict[int, tuple[int, ...]]


class Reader:
    drivers = {'zText', 'RawText', 'RawText4', 'zText4'}

    def __init__(self, root: Path, name: str):
        import Sword
        self.sword = Sword
        self.manager = Sword.SWMgr(str(root))
        from .providers import module_name
        self.module = self.manager.getModule(module_name(name))
        if self.module is None:
            raise ValueError(f'SWORD cannot open {name}')
        if self.module.getConfigEntry('ModDrv') not in self.drivers:
            raise ValueError('Unsupported resource type')
        self.versification = self.module.getConfigEntry('Versification') or 'KJV'
        probe = Sword.VerseKey()
        probe.setVersificationSystem(self.versification)
        if probe.getVersificationSystem() != self.versification:
            raise ValueError(f'Unsupported versification: {self.versification}')

    @property
    def rtl(self):
        # SWIG exposes SWORD's char direction as a one-character Python str.
        value=self.module.getDirection()
        return value in (self.sword.DIRECTION_RTL,chr(self.sword.DIRECTION_RTL))

    def key(self, reference):
        if isinstance(reference, str):
            reference = canonical_input(reference)
        if not isinstance(reference, str) or not re.fullmatch(
                r"(?:[1-4]\s*)?[A-Za-z][A-Za-z0-9]*(?: [A-Za-z]+)*[ .]+[1-9][0-9]*(?:[.:][1-9][0-9]*)?", reference):
            raise ValueError(f'Invalid reference: {reference}')
        key = self.sword.VerseKey()
        key.setAutoNormalize(False)
        key.setVersificationSystem(self.versification)
        key.setText(reference)
        if (key.popError() != '\x00' or not 1 <= key.getChapter() <= key.getChapterMax()
                or not 1 <= key.getVerse() <= key.getVerseMax()):
            raise ValueError(f'Invalid reference: {reference}')
        key.setAutoNormalize(True)
        return key

    @cached_property
    def books(self):
        """Discover actual indexed entries in the module's own versification.

        hasEntry checks the SWORD index without decoding the entire translation.
        No assumptions about OT/NT scope, first book, chapters, or missing verses.
        """
        key = self.sword.VerseKey()
        key.setVersificationSystem(self.versification)
        key.setTestament(1)
        key.setBook(1)
        key.setChapter(1)
        key.setVerse(1)
        entries = {}
        while True:
            if self.module.hasEntry(key):
                code = key.getOSISBookName()
                if code not in entries:
                    entries[code] = (key.getBookName(), {})
                entries[code][1].setdefault(key.getChapter(), []).append(key.getVerse())
            key.increment()
            if key.popError() != '\x00':
                break
        return tuple(Book(code, name, {chapter: tuple(verses) for chapter, verses in chapters.items()})
                     for code, (name, chapters) in entries.items())

    def has_reference(self, reference):
        return bool(self.module.hasEntry(self.key(reference)))

    def first_reference(self):
        if not self.books:
            raise ValueError('No readable indexed passage in resource')
        book = self.books[0]
        chapter = next(iter(book.chapters))
        return f'{book.code}.{chapter}.{book.chapters[chapter][0]}'

    def neighbours(self, reference):
        chapter = self.key(reference).getOSISRef().rsplit('.', 1)[0]
        passages = [(f'{book.code}.{number}', f'{book.code}.{number}.{verses[0]}')
                    for book in self.books for number, verses in book.chapters.items()]
        indexes = [item[0] for item in passages]
        if chapter not in indexes:
            return None, None
        index = indexes.index(chapter)
        return (passages[index - 1][1] if index > 0 else None,
                passages[index + 1][1] if index + 1 < len(passages) else None)

    def chapter(self, reference='Gen.1.1'):
        key = self.key(reference)
        key.setVerse(1)
        first = key.getOSISRef()
        verses = []
        for verse in range(1, key.getVerseMax() + 1):
            key.setVerse(verse)
            if not self.module.hasEntry(key):
                continue
            self.module.setKey(key)
            # SWORD strips source markup. GTK receives plain text only.
            text = self.module.stripText()
            if not isinstance(text, str):
                text = text.c_str()
            verses.append((key.getOSISRef(), text))
        key.setText(first)
        key.decrement()
        previous = key.getOSISRef() if key.popError() == '\x00' else None
        if previous:
            key.setVerse(1)
            previous = key.getOSISRef()
        key.setText(first)
        key.setVerse(key.getVerseMax())
        key.increment()
        following = key.getOSISRef() if key.popError() == '\x00' else None
        return Chapter(first.rsplit('.', 1)[0], tuple(verses), previous, following)


    def structured_chapter(self, chapter):
        from .structured_text import extract
        source_type = self.module.getConfigEntry('SourceType') or 'Plaintext'
        result = {}
        for reference, plain in chapter.verses:
            self.module.setKey(self.key(reference))
            raw = self.module.getRawEntry()
            raw = raw if isinstance(raw,str) else raw.c_str()
            result[reference] = extract(raw,plain,source_type)
        return result


class VersificationMismatch(ValueError):
    """An explicit mapping is required before two verse systems can be aligned."""


class CommentaryReader(Reader):
    @cached_property
    def index(self):
        from .commentary_index import CommentaryIndex
        return CommentaryIndex(self)

    drivers = {'RawCom', 'RawCom4', 'zCom', 'zCom4'}

    def entry(self, reference, bible_versification):
        if bible_versification != self.versification:
            raise VersificationMismatch(f'{bible_versification} / {self.versification}')
        key = self.key(reference)
        # Do not use SWORD's nearest previous entry when this exact index is empty.
        if not self.module.hasEntry(key):
            return None
        self.module.setKey(key)
        text = self.module.stripText()
        if not isinstance(text, str):
            text = text.c_str()
        return text if text.strip() else None
