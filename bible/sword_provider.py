"""Local SWORD access. No network operations or UI dependencies."""
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class Chapter:
    reference: str
    verses: tuple[tuple[str, str], ...]
    previous: str | None
    following: str | None


class Reader:
    def __init__(self, root: Path, name: str):
        import Sword
        self.sword = Sword
        self.manager = Sword.SWMgr(str(root))
        self.module = self.manager.getModule(name)
        if self.module is None:
            raise ValueError(f'SWORD cannot open {name}')
        self.versification = self.module.getConfigEntry('Versification') or 'KJV'

    def key(self, reference):
        if not isinstance(reference, str) or not re.fullmatch(
                r"[1-4]?[A-Za-z]+(?: [A-Za-z]+)*[ .]+[1-9][0-9]*(?:[.:][1-9][0-9]*)?", reference):
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

    def chapter(self, reference='Gen.1.1'):
        key = self.key(reference)
        key.setVerse(1)
        first = key.getOSISRef()
        verses = []
        for verse in range(1, key.getVerseMax() + 1):
            key.setVerse(verse)
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
