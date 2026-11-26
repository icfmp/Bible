"""Local SWORD access. No network operations or UI dependencies."""

from __future__ import annotations

from typing import ClassVar
from os import PathLike
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
import re

from .book_names import canonical_input
from .reference_resolution import VersificationMismatch, resolve


@dataclass(frozen=True)
class ChapterUnit:
    """One actual display unit and its canonical members, retaining a native storage address."""

    reference: str
    text: str
    members: tuple[str, ...]
    label: str | None = None
    native_reference: str | None = None


@dataclass(frozen=True)
class Chapter:
    """Source chapter text, linked native entries and optional edition-specific display units."""

    reference: str
    verses: tuple[tuple[str, str], ...]
    previous: str | None
    following: str | None
    links: tuple[tuple[str, str], ...] = ()
    units: tuple[ChapterUnit, ...] = ()

    @property
    def display_units(self):
        """Return preserved source units, or deduplicated native linked-entry units."""
        return self.units or tuple(
            ChapterUnit(
                ref,
                text,
                self.members(ref),
                self.label(ref) if len(self.members(ref)) > 1 else None,
            )
            for ref, text in self.unique_verses()
        )

    @cached_property
    def primary_references(self):
        return dict(self.links)

    @cached_property
    def text_by_reference(self):
        return dict(self.verses)

    def primary(self, reference):
        return self.primary_references.get(reference, reference) if self.links else reference

    def members(self, reference):
        """Return the primary native reference and aliases sharing the same stored entry."""
        if not self.links:
            return (reference,)
        primary = self.primary(reference)
        return (primary, *(alias for alias, target in self.links if target == primary))

    def unique_verses(self, references=None):
        """One native linked entry, preserving genuinely repeated source text."""
        if references is None and not self.links:
            return self.verses
        rows = (
            self.verses
            if references is None
            else ((ref, self.text_by_reference[ref]) for ref in references)
        )
        seen = set()
        result = []
        for ref, text in rows:
            primary = self.primary(ref)
            if primary not in seen:
                result.append((ref, text))
                seen.add(primary)
        return tuple(result)

    def label(self, reference):
        """Render contiguous linked verse numbers as a range, keeping disjoint members explicit."""
        members = self.members(reference)
        values = [int(ref.rsplit(".", 1)[-1]) for ref in members]
        if len(values) == 1:
            return str(values[0])
        if values == list(range(values[0], values[-1] + 1)):
            return f"{values[0]}–{values[-1]}"
        return ",".join(str(v) for v in values)


@dataclass(frozen=True)
class Book:
    """An installed canon book with its actual chapter/address inventory."""

    code: str
    name: str
    chapters: dict[int | str, tuple[int, ...]]


def passage_verses(reader, references, chapter_cache=None):
    """Resolve every requested reference, emitting each native linked unit once."""
    references = tuple(references)
    chapters = {} if chapter_cache is None else chapter_cache
    seen = set()
    result = []
    requested = set(references)
    for reference in references:
        name = reference.rsplit(".", 1)[0]
        cache_key = (reader.name, name)
        if cache_key not in chapters:
            chapters[cache_key] = reader.chapter(reference)
            if len(chapters) > 64:
                chapters.pop(next(iter(chapters)))
        chapter = chapters[cache_key]
        identity = chapter.primary(reference)
        if chapter.units:
            if reference not in chapter.text_by_reference:
                raise ValueError("Passage unavailable: " + reference)
            if name in seen:
                continue
            for unit in chapter.units:
                matches = [ref for ref in unit.members if ref in requested]
                if matches:
                    result.append((matches[0], unit.text))
            seen.add(name)
            continue
        if identity in seen:
            continue
        value = chapter.text_by_reference.get(reference)
        if value is None:
            raise ValueError("Passage unavailable: " + reference)
        result.append((reference, value))
        seen.add(identity)
    return tuple(result)


class NativeToolReader:
    """Native handles for installed non-verse tools; no invented resource data."""

    drivers: ClassVar[set[str]]

    def __init__(self, root: str | PathLike[str], name: str) -> None:
        import Sword
        from .module_lifecycle import reader_lease
        from .providers import module_name

        self.root = Path(root)
        reader_lease(self, self.root)
        self.manager = Sword.SWMgr(str(root))
        module = self.manager.getModule(module_name(name))
        self.sword = Sword
        if module is None or module.getConfigEntry("ModDrv") not in self.drivers:
            raise ValueError("Unsupported native tool module")
        self.module = module


class DictionaryReader(NativeToolReader):
    """Native dictionary handles used for bounded readability verification."""

    drivers = {"RawLD", "RawLD4", "zLD"}

    def __init__(self, root, name) -> None:
        super().__init__(root, name)
        self.dictionary = self.sword.SWLD.castTo(self.module)
        if self.dictionary is None:
            raise ValueError("Native dictionary access is unavailable")

    def verify_readable(self) -> None:
        # The packaged SWIG setPosition(SW_POSITION(...)) call stopped native
        # verification. Use the proven dictionary index API instead.
        """Find a nonempty indexed entry within32 positions, or reject native readability."""
        for position in range(min(self.dictionary.getEntryCount(), 32)):
            text = self.dictionary.getKeyForEntry(position)
            if not text:
                continue
            self.key = self.sword.SWKey(text)
            self.module.setKey(self.key)
            if text.strip() and self.module.stripText().strip():
                return
        raise ValueError("No readable dictionary entry in resource")


class GeneralBookReader(NativeToolReader):
    """Native tree-key access for supported installed general-book resources."""

    drivers = {"RawGenBook"}

    def verify_readable(self) -> None:
        """Probe at most256 tree positions without inventing a verse-address interface."""
        key = self.sword.TreeKey.castTo(self.module.getKey())
        if key is None:
            raise ValueError("This general-book key format is unsupported")
        key.root()
        for _ in range(256):
            if key.getText().strip() and self.module.stripText().strip():
                return
            if key.firstChild():
                continue
            while not key.nextSibling():
                if not key.parent():
                    raise ValueError("No readable general-book entry in resource")
        raise ValueError("No readable general-book entry within the native verification limit")


class Reader:
    """Mutable local SWORD handles with source-aware canonical address projection.

    Keep each reader on its owning execution path; search/preparation workers
    open independent handles. The resource lease prevents switching backing
    files while a native consumer still owns them.
    """

    drivers = {"zText", "RawText", "RawText4", "zText4"}

    def __init__(self, root: Path, name: str) -> None:
        self.root, self.name = Path(root), name
        from .module_lifecycle import reader_lease

        reader_lease(self, self.root)
        import Sword

        self.sword = Sword
        if name.startswith("youversion~") and (self.root / ".source-versification").exists():
            from .source_versification import register_index

            register_index(self.root / ".source-versification")
        self.manager = Sword.SWMgr(str(root))
        from .providers import module_name

        module = self.manager.getModule(module_name(name))
        if module is None:
            raise ValueError(f"SWORD cannot open {name}")
        if module.getConfigEntry("ModDrv") not in self.drivers:
            raise ValueError("Unsupported resource type")
        self.module = module
        self.versification = self.module.getConfigEntry("Versification") or "KJV"
        short = self.module.getConfigEntry("Abbreviation") or module_name(name)
        self.short_name = (
            short
            if isinstance(short, str) and len(short) <= 40 and not any(ord(c) < 32 for c in short)
            else module_name(name)
        )
        self._source_osis = (
            name.startswith("youversion~")
            and self.module.getConfigEntry("BibleSource") == "YouVersion"
        )
        from .source_units import AddressIndex

        self.addresses = AddressIndex.load(self.root) if self._source_osis else None
        if self.addresses:
            from .source_section_key import key_type

            self._source_key = key_type(Sword, self.addresses, self.versification)
        probe = Sword.VerseKey()
        probe.setVersificationSystem(self.versification)
        if probe.getVersificationSystem() != self.versification:
            raise ValueError(f"Unsupported versification: {self.versification}")

    @property
    def rtl(self):
        # SWIG exposes SWORD's char direction as a one-character Python str.
        value = self.module.getDirection()
        return value in (self.sword.DIRECTION_RTL, chr(self.sword.DIRECTION_RTL))

    def can_align_reference(self, reference):
        """Check edition-specific evidence before allowing a numbering-system correspondence."""
        if not self._source_osis:
            return self.native_alignment_issue(reference) is None
        from .source_versification import reference_mapping, SOURCE_CONVENTIONS

        receipt = self._numbering_receipt
        if (
            receipt.get("all_text_notes_headings_verified") is not True
            or receipt.get("storage_numbering") != self.versification
        ):
            return False
        if SOURCE_CONVENTIONS.get(receipt.get("source_numbering")) == self.versification:
            return True
        from .versification_mapping import table, verified_identity

        data = reference_mapping(self.versification) or table(self.versification)
        if not data:
            return False
        convention = data.get("declared_convention")
        if convention:
            return reference.split(".")[0] in convention["books"]
        return verified_identity(reference, data)

    def native_alignment_issue(self, reference):
        """Read-only, passage-scoped evidence from ordinary SWORD indexing.

        Following requires an actual native entry and no contradictory source
        identity. Explicit approximate numbering and a title in a body slot
        limit local capabilities. Missing verses alone are not evidence that
        neighbouring entries have been renumbered.
        No language, provider or module ID is used as a numbering exception.
        """
        from collections import OrderedDict

        cache = getattr(self, "_alignment_evidence", None)
        if cache is None:
            self._alignment_evidence = cache = OrderedDict()
        token = reference
        if token in cache:
            return cache[token]
        issue = None
        try:
            key = self.key(reference)
            public = key.getOSISRef()
            if not self.module.hasEntry(key):
                raise ValueError("No indexed native entry: " + public)
            if self._approximate_numbering:
                # Some upstream configurations explicitly call this the
                # "closest" standard system. Keep only registry-invariant
                # positions; this is not an attested shifted source mapping.
                from .reference_resolution import resolve, MAPPED_SYSTEMS
                from .reference_targets import Canon

                for system in MAPPED_SYSTEMS:
                    mapped = resolve(public, self.versification, Canon(system), require_entry=False)
                    if (mapped.start, mapped.end) != (public, public):
                        raise ValueError(
                            "Source declares approximate numbering; correspondence is not invariant here: "
                            + public
                        )
            if (self.module.getConfigEntry("SourceType") or "") == "OSIS":
                old = self.sword.VerseKey(self.module.getKey())
                try:
                    self.module.setKey(key)
                    raw = str(self.module.getRawEntry())
                    identifiers = re.findall(
                        r"<verse\b[^>]*\b(?:osisID|sID)=[\"\x27]([^\"\x27]+)", raw, re.I
                    )
                    if identifiers and not any(public in value.split() for value in identifiers):
                        raise ValueError(
                            "Source verse identity contradicts the native entry: " + public
                        )
                    # Heading-only first units are genuine in title-counting
                    # canons, but cannot be treated as a numbered body verse.
                    chapter_token = ("chapter", key.getOSISBookName(), key.getChapter())
                    if chapter_token not in cache:
                        cache[chapter_token] = None
                        first = self.key(f"{key.getOSISBookName()}.{key.getChapter()}.1")
                        if self.module.hasEntry(first):
                            self.module.setKey(first)
                            from .structured_text import SourceParser

                            parser = SourceParser()
                            parser.feed(str(self.module.getRawEntry()))
                            parser.close()
                            title = any(
                                s.kind == "heading" and s.text.strip() for s in parser.segments
                            )
                            body = any(s.kind == "text" and s.text.strip() for s in parser.segments)
                            if title and not body:
                                from .reference_resolution import resolve
                                from .reference_targets import Canon
                                from .versification_mapping import table, to_base

                                data = table(self.versification)
                                ref = first.getOSISRef()
                                parts = to_base(ref, self.versification)
                                known_title = (
                                    data is not None
                                    and ref in data.get("forward", {})
                                    and (
                                        not parts
                                        or all(
                                            "!pv" in part or part.endswith(".0") for part in parts
                                        )
                                    )
                                )
                                try:
                                    if not known_title:
                                        mapped = resolve(
                                            ref,
                                            self.versification,
                                            Canon("KJV"),
                                            require_entry=False,
                                            include_introductions=True,
                                        )
                                        if not mapped.introductions:
                                            raise ValueError(
                                                "A source heading occupies a declared body-verse slot: "
                                                + ref
                                            )
                                except ValueError as error:
                                    cache[chapter_token] = str(error)
                    if cache[chapter_token]:
                        raise ValueError(cache[chapter_token])
                finally:
                    self.module.setKey(old)
        except ValueError as error:
            issue = str(error)
        cache[token] = issue
        if len(cache) > 2048:
            cache.popitem(last=False)
        return issue

    @cached_property
    def _approximate_numbering(self):
        from .providers import module_name

        for path in (self.root / "mods.d").glob("*.conf"):
            data = path.read_text(encoding="utf-8", errors="replace")
            if not re.search(r"(?m)^\[" + re.escape(module_name(self.name)) + r"\]\s*$", data):
                continue
            declaration = re.search(r"(?im)((?:[ \t]*#[^\n]*\n)+)[ \t]*Versification\s*=", data)
            if declaration and re.search(
                r"\b(closest|approximate|approximative)\b", declaration[1], re.I
            ):
                return True
        return False

    @cached_property
    def _numbering_receipt(self):
        import json

        path = self.root / ".verified.json"
        try:
            if path.is_symlink() or path.stat().st_size > 16384:
                return {}
            value = json.loads(path.read_text())
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def key(self, reference):
        """Validate a reference in the actual reader system before enabling native key normalization.

        Use explicit source-address indices where present; unsupported or
        out-of-range inputs raise ValueError instead of silently normalizing
        to a different passage.
        """
        if isinstance(reference, str):
            reference = canonical_input(reference)
        if self.addresses:
            key = self._source_key(reference)
            native = self.sword.VerseKey(key)
            if (
                key.popError() != "\x00"
                or not 1 <= native.getChapter() <= native.getChapterMax()
                or not 1 <= native.getVerse() <= native.getVerseMax()
            ):
                raise ValueError(f"Invalid reference: {reference}")
            return key
        if not isinstance(reference, str) or not re.fullmatch(
            r"(?:[1-4]\s*)?[A-Za-z][A-Za-z0-9]*(?: [A-Za-z]+)*[ .]+[1-9][0-9]*(?:[.:][1-9][0-9]*)?",
            reference,
        ):
            raise ValueError(f"Invalid reference: {reference}")
        key = self.sword.VerseKey()
        key.setAutoNormalize(False)
        key.setVersificationSystem(self.versification)
        key.setText(reference)
        if (
            key.popError() != "\x00"
            or not 1 <= key.getChapter() <= key.getChapterMax()
            or not 1 <= key.getVerse() <= key.getVerseMax()
        ):
            raise ValueError(f"Invalid reference: {reference}")
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
            if key.popError() != "\x00":
                break
        result = []
        for code, (name, chapters) in entries.items():
            mapped = {}
            for chapter, verses in chapters.items():
                public = (
                    self.addresses.source_chapter(f"{code}.{chapter}")
                    if self.addresses
                    else f"{code}.{chapter}"
                )
                number = public.split(".")[1]
                number = number if "_" in number else int(number)
                units = self.addresses.chapters.get(public) if self.addresses else None
                mapped[number] = (
                    tuple(
                        dict.fromkeys(
                            int(ref.rsplit(".", 1)[1])
                            for unit in units.units
                            for ref in unit.members
                        )
                    )
                    if units
                    else tuple(verses)
                )
            result.append(Book(code, name, mapped))
        return tuple(result)

    def has_reference(self, reference):
        try:
            return bool(self.module.hasEntry(self.key(reference)))
        except ValueError:
            return False

    def first_reference(self):
        if not self.books:
            raise ValueError("No readable indexed passage in resource")
        book = self.books[0]
        chapter = next(iter(book.chapters))
        verse = self.source_verse_order.get(f"{book.code}.{chapter}", book.chapters[chapter])[0]
        return f"{book.code}.{chapter}.{verse}"

    def chapter_label(self, reference):
        reference = reference if reference.count(".") == 1 else reference.rsplit(".", 1)[0]
        if self.addresses and self.addresses.sections:
            label = self.addresses.sections.labels.get(reference)
            if label:
                return label
        return reference.split(".")[1]

    def reference_range(self, start, end):
        """Canonical source addresses, independent of fragment presentation order."""
        start = self.key(start).getOSISRef()
        end = self.key(end).getOSISRef()
        refs = []
        active = False
        for book in self.books:
            if not active and book.code != start.split(".")[0]:
                continue
            for chapter, verses in book.chapters.items():
                if not active and f"{book.code}.{chapter}" != start.rsplit(".", 1)[0]:
                    continue
                for verse in sorted(verses):
                    reference = f"{book.code}.{chapter}.{verse}"
                    if reference == start:
                        active = True
                    if active:
                        refs.append(reference)
                        if len(refs) > 100000:
                            raise ValueError("Source reference range too large")
                        if reference == end:
                            return tuple(refs)
        raise ValueError("Invalid source reference range")

    def reference_sort_key(self, reference):
        key = self.key(reference)
        verse = key.getVerse()
        native = self.sword.VerseKey(key)
        native.setVerse(1)
        return native.getIndex(), verse

    def neighbours(self, reference):
        """Return adjacent actual source chapters, or empty endpoints for an unknown chapter."""
        chapter = self.key(reference).getOSISRef().rsplit(".", 1)[0]
        passages = [
            (f"{book.code}.{number}", f"{book.code}.{number}.{verses[0]}")
            for book in self.books
            for number, verses in book.chapters.items()
        ]
        indexes = [item[0] for item in passages]
        if chapter not in indexes:
            return None, None
        index = indexes.index(chapter)
        return (
            passages[index - 1][1] if index > 0 else None,
            passages[index + 1][1] if index + 1 < len(passages) else None,
        )

    @cached_property
    def source_verse_order(self):
        """Sparse, verified reference-only exceptions to numeric verse order."""
        if not self._source_osis:
            return {}
        import hashlib
        import json

        path = self.root / ".source-verse-order.json"
        receipt = self.root / ".verified.json"
        if not path.exists() and not receipt.exists():
            return {}
        if receipt.is_symlink() or receipt.stat().st_size > 16384:
            raise ValueError("Invalid source verification receipt")
        expected = json.loads(receipt.read_text()).get("source_verse_order_sha256")
        if not expected and not path.exists():
            return {}
        if path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("Invalid source verse order")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Source verse order changed")
        value = json.loads(raw)
        if not isinstance(value, dict) or len(value) > 10000:
            raise ValueError("Invalid source verse order")
        for ref, numbers in value.items():
            if (
                not re.fullmatch(r"[1-5]?[A-Za-z][A-Za-z0-9]{0,15}\.[1-9][0-9]{0,2}", ref)
                or not isinstance(numbers, list)
                or not 1 <= len(numbers) <= 2000
                or any(type(n) is not int or not 1 <= n <= 2000 for n in numbers)
                or len(set(numbers)) != len(numbers)
            ):
                raise ValueError("Invalid source verse order")
        return value

    def chapter(self, reference="Gen.1.1", *, cancelled=None):
        """Read a chapter using preserved source units/links and cooperative cancellation.

        Source-address sidecars determine public references when present; native
        storage numbering is not exposed as an invented source equivalence.
        """
        from .preparation import checkpoint

        checkpoint(cancelled)
        if not getattr(self, "addresses", None):
            return self._native_chapter(reference, cancelled=cancelled)
        public = self.key(reference).getOSISRef().rsplit(".", 1)[0]
        native = self._native_chapter(
            self.addresses.native_chapter(public) + ".1", cancelled=cancelled
        )
        description = self.addresses.chapters.get(public)
        if description:
            units = []
            combined = {ref: [] for ref in description.inventory}
            for position, source in enumerate(description.units, 1):
                storage = native.reference + "." + str(position)
                text = native.text_by_reference[storage]
                for ref in source.members:
                    combined[ref].append(text)
                units.append(
                    ChapterUnit(source.members[0], text, source.members, source.label, storage)
                )
            verses = tuple((ref, "".join(parts)) for ref, parts in combined.items())
            links = ()
        else:
            units = []
            verses = tuple((self.addresses.to_source(ref), text) for ref, text in native.verses)
            links = tuple(
                (self.addresses.to_source(alias), self.addresses.to_source(primary))
                for alias, primary in native.links
            )
        before, after = self.neighbours(public)
        return Chapter(public, verses, before, after, links, tuple(units))

    def _native_chapter(self, reference="Gen.1.1", *, cancelled=None):
        """Read real native entries, preserve links and project verified OSIS bodies without rewriting text."""
        from .preparation import checkpoint

        checkpoint(cancelled)
        if self.addresses:
            key = self.sword.VerseKey()
            key.setVersificationSystem(self.versification)
            key.setAutoNormalize(False)
            key.setText(reference)
        else:
            key = self.key(reference)
        key.setVerse(1)
        first = key.getOSISRef()
        verses = []
        source_entries = []
        links = []
        previous_entry = None
        primary = None
        previous_text = None
        numbers = self.source_verse_order.get(first.rsplit(".", 1)[0])
        if numbers is not None:
            present = set()
            for verse in range(1, key.getVerseMax() + 1):
                key.setVerse(verse)
                if self.module.hasEntry(key):
                    present.add(verse)
            if set(numbers) != present:
                raise ValueError("Source verse order differs from native entries")
        for verse in numbers if numbers is not None else range(1, key.getVerseMax() + 1):
            checkpoint(cancelled)
            key.setVerse(verse)
            if not self.module.hasEntry(key):
                continue
            self.module.setKey(key)
            reference = key.getOSISRef()
            if previous_entry is not None and self.module.isLinked(previous_entry, key):
                links.append((reference, primary))
                verses.append((reference, previous_text))
                continue
            # SWORD strips source markup. GTK receives plain text only.
            text = self.module.getRawEntry() if self._source_osis else self.module.stripText()
            if not isinstance(text, str):
                text = text.c_str()
            if self._source_osis:
                source_entries.append((reference, text))
                text = ""
            verses.append((reference, text))
            previous_entry = self.sword.VerseKey(key)
            primary = reference
            previous_text = text
        if self._source_osis:
            # Native StripText applies presentation transforms (emphasis marks,
            # divine-name casing, parallel-reference text). Our generated OSIS
            # has already passed full readback: project its actual verse bodies
            # without changing text or including editorial material. A complete
            # chapter also respects markup crossing native entry boundaries.
            from .youversion_content import parse, project

            intro = self.sword.VerseKey()
            intro.setVersificationSystem(self.versification)
            intro.setAutoNormalize(False)
            intro.setIntros(True)
            intro.setText(first.rsplit(".", 1)[0] + ".0")
            self.module.setKey(intro)
            prefix = self.module.getRawEntry()
            prefix = prefix if isinstance(prefix, str) else prefix.c_str()
            raw = (
                "<root><?source-unit "
                + first.rsplit(".", 1)[0]
                + ".0?>"
                + prefix
                + "".join("<?source-unit " + ref + "?>" + value for ref, value in source_entries)
                + "</root>"
            )
            bodies = project(parse(raw), normalize=False, editorial=False)[0]
            aliases = dict(links)
            verses = [(ref, bodies.get(aliases.get(ref, ref), "")) for ref, _ in verses]
        key.setText(first)
        key.decrement()
        previous = key.getOSISRef() if key.popError() == "\x00" else None
        if previous:
            key.setVerse(1)
            previous = key.getOSISRef()
        key.setText(first)
        key.setVerse(key.getVerseMax())
        key.increment()
        following = key.getOSISRef() if key.popError() == "\x00" else None
        return Chapter(first.rsplit(".", 1)[0], tuple(verses), previous, following, tuple(links))

    def structured_chapter(self, chapter, *, cancelled=None):
        """Project markup roles against actual text, retaining source prefaces and linked aliases."""
        from .structured_text import extract
        from .preparation import checkpoint

        checkpoint(cancelled)
        source_type = self.module.getConfigEntry("SourceType") or "Plaintext"
        result = {}
        parser = None
        prefix = ()
        if source_type == "OSIS" and (
            self.versification == "Original"
            or self.module.getConfigEntry("BibleSource") == "YouVersion"
        ):
            from .structured_text import Segment, SourceParser, checked_segments

            parser = SourceParser()
            key = self.sword.VerseKey()
            key.setVersificationSystem(self.versification)
            native_chapter = (
                self.addresses.native_chapter(chapter.reference)
                if self.addresses
                else chapter.reference
            )
            key.setIntros(True)
            key.setAutoNormalize(False)
            key.setText(native_chapter + ".0")
            self.module.setKey(key)
            raw = self.module.getRawEntry()
            parser.feed(raw if isinstance(raw, str) else raw.c_str())
            # Ordinary unnumbered source prose is outside the verse body, but
            # is not an editorial heading. Keep its own styling and breaks.
            if any(
                s.kind in ("heading", "editorial", "text") and s.text.strip()
                for s in parser.segments
            ):
                plain = "".join(s.text for s in parser.segments if s.kind == "text")
                prefix = tuple(
                    Segment(
                        s.text,
                        s.kind if s.kind in ("heading", "editorial") else "preface",
                        s.styles,
                    )
                    for s in checked_segments(parser.segments, plain)
                )
            parser.segments = []
        for unit in chapter.display_units:
            reference, plain = unit.native_reference or unit.reference, unit.text
            checkpoint(cancelled)
            if unit.native_reference:
                key = self.sword.VerseKey()
                key.setVersificationSystem(self.versification)
                key.setText(unit.native_reference)
            else:
                key = self.key(reference)
            self.module.setKey(key)
            raw = self.module.getRawEntry()
            raw = raw if isinstance(raw, str) else raw.c_str()
            if parser is None:
                result[reference] = extract(raw, plain, source_type)
            else:
                parser.feed(raw)
                result[reference] = prefix + checked_segments(parser.segments, plain)
                prefix = ()
                parser.segments = []
        for alias, primary in chapter.links:
            result[alias] = result[primary]
        return result

    def introduction(self, book):
        """Actual book introduction, outside canonical passage/personal-note IDs."""
        if not re.fullmatch(r"[1-4]?[A-Za-z]+", book):
            raise ValueError("Invalid book")
        from .youversion_content import parse

        key = self.sword.VerseKey()
        key.setVersificationSystem(self.versification)
        key.setIntros(True)
        key.setAutoNormalize(False)
        key.setText(book + ".0.0")
        if key.popError() != "\x00" or not self.module.hasEntry(key):
            return None
        self.module.setKey(key)
        raw = self.module.getRawEntry()
        raw = raw if isinstance(raw, str) else raw.c_str()
        return parse("<root>" + raw + "</root>") if raw.strip() else None

    def editorial_notes(self, reference):
        """Only the requested chapter; no corpus scan or persistent native cache."""
        if self.module.getConfigEntry("SourceType") != "OSIS":
            return ()
        from .youversion_content import native_chapter, project

        chapter = self.chapter(reference)
        if self.addresses:
            from dataclasses import replace

            native = self._native_chapter(self.addresses.native_chapter(chapter.reference) + ".1")
        else:
            native = chapter
        key = self.sword.VerseKey()
        key.setVersificationSystem(self.versification)
        key.setIntros(True)
        key.setAutoNormalize(False)
        root = native_chapter(
            self.module, key, native.reference, [ref for ref, _ in native.unique_verses()]
        )
        notes = project(root)[1]
        if not self.addresses:
            return notes
        return tuple(
            replace(
                note,
                reference=" ".join(
                    dict.fromkeys(
                        ref
                        for word in note.reference.split()
                        for ref in self.addresses.to_sources(word, allow_zero=True)
                    )
                ),
            )
            for note in notes
        )


class CommentaryReader(Reader):
    """A local commentary reader retaining exact-entry availability and numbering checks."""

    @cached_property
    def index(self):
        from .commentary_index import CommentaryIndex

        return CommentaryIndex(self)

    drivers = {"RawCom", "RawCom4", "zCom", "zCom4"}

    def entry(self, reference, bible_versification):
        """Return an exact mapped commentary body, or None for absent/empty entries.

        VersificationMismatch propagates when correspondence is unverified;
        SWORD's nearest preceding entry is never substituted for a missing entry.
        """
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
