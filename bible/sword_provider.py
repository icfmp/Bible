"""Local SWORD access. No network operations or UI dependencies."""
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
import re

from .book_names import canonical_input
from .reference_resolution import VersificationMismatch, resolve


@dataclass(frozen=True)
class Chapter:
    reference: str
    verses: tuple[tuple[str, str], ...]
    previous: str | None
    following: str | None
    links: tuple[tuple[str,str], ...] = ()

    @cached_property
    def primary_references(self):
        return dict(self.links)

    @cached_property
    def text_by_reference(self):
        return dict(self.verses)

    def primary(self,reference):
        return self.primary_references.get(reference,reference) if self.links else reference

    def members(self,reference):
        if not self.links:return (reference,)
        primary=self.primary(reference)
        return (primary,*(alias for alias,target in self.links if target==primary))

    def unique_verses(self,references=None):
        """One native linked entry, preserving genuinely repeated source text."""
        if references is None and not self.links:return self.verses
        rows=self.verses if references is None else ((ref,self.text_by_reference[ref]) for ref in references)
        seen=set();result=[]
        for ref,text in rows:
            primary=self.primary(ref)
            if primary not in seen:result.append((ref,text));seen.add(primary)
        return tuple(result)

    def label(self,reference):
        members=self.members(reference)
        values=[int(ref.rsplit('.',1)[-1]) for ref in members]
        if len(values)==1:return str(values[0])
        if values==list(range(values[0],values[-1]+1)):return f'{values[0]}–{values[-1]}'
        return ','.join(str(v) for v in values)


@dataclass(frozen=True)
class Book:
    code: str
    name: str
    chapters: dict[int, tuple[int, ...]]


def passage_verses(reader,references,chapter_cache=None):
    """Resolve every requested reference, emitting each native linked unit once."""
    chapters={} if chapter_cache is None else chapter_cache
    seen=set();result=[]
    for reference in references:
        name=reference.rsplit('.',1)[0]
        if name not in chapters:
            chapters[name]=reader.chapter(reference)
            if len(chapters)>64:chapters.pop(next(iter(chapters)))
        chapter=chapters[name];identity=chapter.primary(reference)
        if identity in seen:continue
        value=chapter.text_by_reference.get(reference)
        if value is None:raise ValueError('Passage unavailable: '+reference)
        result.append((reference,value));seen.add(identity)
    return tuple(result)


class Reader:
    drivers = {'zText', 'RawText', 'RawText4', 'zText4'}

    def __init__(self, root: Path, name: str):
        self.root,self.name=Path(root),name
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
        short=self.module.getConfigEntry('Abbreviation') or module_name(name)
        self.short_name=short if isinstance(short,str) and len(short)<=40 and not any(ord(c)<32 for c in short) else module_name(name)
        self._source_osis=name.startswith('youversion~') and self.module.getConfigEntry('BibleSource')=='YouVersion'
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
        return self.discover_books()

    def discover_books(self, cancelled=None):
        """Discover actual indexed entries in the module's own versification.

        hasEntry checks the SWORD index without decoding the entire translation.
        No assumptions about OT/NT scope, first book, chapters, or missing verses.
        """
        from .preparation import checkpoint
        checkpoint(cancelled)
        key = self.sword.VerseKey()
        key.setVersificationSystem(self.versification)
        key.setTestament(1)
        key.setBook(1)
        key.setChapter(1)
        key.setVerse(1)
        entries = {}
        while True:
            checkpoint(cancelled)
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

    def chapter(self, reference='Gen.1.1', *, cancelled=None):
        from .preparation import checkpoint
        checkpoint(cancelled)
        key = self.key(reference)
        key.setVerse(1)
        first = key.getOSISRef()
        verses = []
        source_entries=[]
        links=[];previous_entry=None;primary=None;previous_text=None
        for verse in range(1, key.getVerseMax() + 1):
            checkpoint(cancelled)
            key.setVerse(verse)
            if not self.module.hasEntry(key):
                continue
            self.module.setKey(key)
            reference=key.getOSISRef()
            if previous_entry is not None and self.module.isLinked(previous_entry,key):
                links.append((reference,primary));verses.append((reference,previous_text))
                continue
            # SWORD strips source markup. GTK receives plain text only.
            text = self.module.getRawEntry() if self._source_osis else self.module.stripText()
            if not isinstance(text, str):
                text = text.c_str()
            if self._source_osis:source_entries.append((reference,text));text=''
            verses.append((reference,text))
            previous_entry=self.sword.VerseKey(key);primary=reference;previous_text=text
        if self._source_osis:
            # Native StripText applies presentation transforms (emphasis marks,
            # divine-name casing, parallel-reference text). Our generated OSIS
            # has already passed full readback: project its actual verse bodies
            # without changing text or including editorial material. A complete
            # chapter also respects markup crossing native entry boundaries.
            from .youversion_content import parse,project
            intro=self.sword.VerseKey();intro.setVersificationSystem(self.versification)
            intro.setAutoNormalize(False);intro.setIntros(True);intro.setText(first.rsplit('.',1)[0]+'.0')
            self.module.setKey(intro);prefix=self.module.getRawEntry()
            prefix=prefix if isinstance(prefix,str) else prefix.c_str()
            raw='<root><?source-unit '+first.rsplit('.',1)[0]+'.0?>'+prefix+''.join('<?source-unit '+ref+'?>'+value for ref,value in source_entries)+'</root>'
            bodies=project(parse(raw),normalize=False,editorial=False)[0]
            aliases=dict(links)
            verses=[(ref,bodies.get(aliases.get(ref,ref),'')) for ref,_ in verses]
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
        return Chapter(first.rsplit('.', 1)[0],tuple(verses),previous,following,tuple(links))


    def structured_chapter(self, chapter, *, cancelled=None):
        from .structured_text import extract
        from .preparation import checkpoint
        checkpoint(cancelled)
        source_type = self.module.getConfigEntry('SourceType') or 'Plaintext'
        result = {}
        parser=None;prefix=()
        if source_type=='OSIS' and (self.versification=='Original' or self.module.getConfigEntry('BibleSource')=='YouVersion'):
            from .structured_text import Segment,SourceParser,checked_segments
            parser=SourceParser()
            key=self.sword.VerseKey();key.setVersificationSystem(self.versification)
            key.setIntros(True);key.setAutoNormalize(False);key.setText(chapter.reference+'.0')
            self.module.setKey(key);raw=self.module.getRawEntry()
            parser.feed(raw if isinstance(raw,str) else raw.c_str())
            prefix=tuple(Segment(segment.text,'heading',segment.styles)
                         for segment in parser.segments if segment.kind in ('heading','text') and segment.text.strip())
            parser.segments=[]
        for reference, plain in chapter.unique_verses():
            checkpoint(cancelled)
            self.module.setKey(self.key(reference))
            raw = self.module.getRawEntry()
            raw = raw if isinstance(raw,str) else raw.c_str()
            if parser is None:result[reference] = extract(raw,plain,source_type)
            else:
                parser.feed(raw)
                result[reference]=prefix+checked_segments(parser.segments,plain)
                prefix=();parser.segments=[]
        for alias,primary in chapter.links:result[alias]=result[primary]
        return result

    def introduction(self, book):
        """Actual book introduction, outside canonical passage/personal-note IDs."""
        if not re.fullmatch(r'[1-4]?[A-Za-z]+',book):raise ValueError('Invalid book')
        from .youversion_content import parse
        key=self.sword.VerseKey();key.setVersificationSystem(self.versification)
        key.setIntros(True);key.setAutoNormalize(False);key.setText(book+'.0.0')
        if key.popError()!='\x00' or not self.module.hasEntry(key):return None
        self.module.setKey(key);raw=self.module.getRawEntry()
        raw=raw if isinstance(raw,str) else raw.c_str()
        return parse('<root>'+raw+'</root>') if raw.strip() else None

    def editorial_notes(self, reference):
        """Only the requested chapter; no corpus scan or persistent native cache."""
        if self.module.getConfigEntry('SourceType')!='OSIS':return ()
        from .youversion_content import native_chapter,project
        chapter=self.chapter(reference)
        key=self.sword.VerseKey();key.setVersificationSystem(self.versification)
        key.setIntros(True);key.setAutoNormalize(False)
        root=native_chapter(self.module,key,chapter.reference,[ref for ref,_ in chapter.unique_verses()])
        return project(root)[1]


class CommentaryReader(Reader):
    @cached_property
    def index(self):
        from .commentary_index import CommentaryIndex
        return CommentaryIndex(self)

    drivers = {'RawCom', 'RawCom4', 'zCom', 'zCom4'}

    def entry(self, reference, bible_versification):
        try:
            resolved = resolve(reference, bible_versification, self, require_entry=False)
        except VersificationMismatch:
            raise
        except ValueError:
            return None
        key = self.key(resolved.start)
        # Do not use SWORD's nearest previous entry when this exact index is empty.
        if not self.module.hasEntry(key):
            return None
        self.module.setKey(key)
        text = self.module.stripText()
        if not isinstance(text, str):
            text = text.c_str()
        return text if text.strip() else None
