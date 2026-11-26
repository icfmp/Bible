"""Bounded, on-demand chapter/entry sources for the native paginated reader."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, replace
from itertools import groupby
from .pagination import (
    Anchor as Anchor,
    Document,
    PassageSpan,
    StyleSpan,
    paginate,
    paragraph_spaces,
)
from .book_names import display_name
from .i18n import LANGUAGE
from .verse_typography import first_word_length
from .preparation import checkpoint


class BiblePages:
    """Build source-aware chapter documents for native pagination without storing rendered page state."""

    kind = "bible"

    def __init__(self, reader, resource) -> None:
        self.reader = reader
        self.resource = resource

    def key(self, reference):
        return self.reader.key(reference).getOSISRef().rsplit(".", 1)[0]

    def document(self, key, preferences, *, cancelled=None):
        """Project actual chapter units into display/copy text and canonical style spans.

        Generated headings/numbers follow preferences; source editorial material
        retains its role. Display-only nonbreaking spaces do not alter copied text.
        """
        checkpoint(cancelled)
        chapter = self.reader.chapter(
            key if getattr(self.reader, "addresses", None) else key + ".1", cancelled=cancelled
        )
        structured = self.reader.structured_chapter(chapter, cancelled=cancelled)
        native = self.reader.key(
            chapter.verses[0][0] if getattr(self.reader, "addresses", None) else key + ".1"
        )
        title = display_name(native.getOSISBookName(), native.getBookName(), LANGUAGE)
        if preferences.chapter_numbers:
            title += " " + (
                self.reader.chapter_label(key)
                if hasattr(self.reader, "chapter_label")
                else str(native.getChapter())
            )
        # This switch controls the whole generated heading, not source-supplied
        # editorial titles or the independent passage selector.
        prefix = title + "\n\n" if preferences.chapter_numbers else ""
        pieces = [prefix]
        styles = [StyleSpan("chapter", 0, len(title))] if prefix else []
        spans = []
        offset = len(prefix)
        bases = {}
        for unit in chapter.display_units:
            reference, _plain = unit.reference, unit.text
            checkpoint(cancelled)
            start = offset if spans else 0
            segments = structured[unit.native_reference or reference]
            for kind, group in groupby(segments, key=lambda segment: segment.kind):
                group = tuple(group)
                if kind in ("heading", "editorial"):
                    # Inline emphasis/reference nodes do not create new titles.
                    original_title = "".join(segment.text for segment in group)
                    text = original_title.strip()
                    if not text:
                        continue
                    if pieces and not pieces[-1].endswith("\n"):
                        pieces.append("\n")
                        offset += 1
                    trimmed = len(original_title) - len(original_title.lstrip())
                    position = 0
                    for segment in group:
                        first = max(0, position - trimmed)
                        last = min(len(text), position + len(segment.text) - trimmed)
                        if last > first:
                            styles.extend(
                                StyleSpan(style, offset + first, offset + last)
                                for style in segment.styles
                            )
                        position += len(segment.text)
                    text += "\n"
                    pieces.append(text)
                    styles.append(StyleSpan(kind, offset, offset + len(text)))
                    offset += len(text)
                elif kind == "preface":
                    for segment in group:
                        pieces.append(segment.text)
                        styles.extend(
                            StyleSpan(style, offset, offset + len(segment.text))
                            for style in segment.styles
                        )
                        offset += len(segment.text)
            body = "".join(
                s.text for s in segments if s.kind not in ("heading", "editorial", "preface")
            )
            source_leading = len(body) - len(body.lstrip())
            leading = body[:source_leading]
            if "\n" in leading:
                # Boundaries surrounding prefixed headings belong to that
                # heading, rather than several empty body paragraphs.
                trailing = len(pieces[-1]) - len(pieces[-1].rstrip("\n")) if pieces else 0
                leading = "\n" * max(0, min(2, leading.count("\n")) - trailing)
            if leading:
                pieces.append(leading)
                offset += len(leading)
            body = body[source_leading:]
            members = unit.members
            label = unit.label
            printed = label if label is not None else reference.rsplit(".", 1)[-1]
            number = printed + " " if preferences.verse_numbers and printed else ""
            if number:
                styles.append(StyleSpan("number", offset, offset + len(number)))
            pieces.append(number)
            offset += len(number)
            body_start = offset
            position = 0
            for segment in segments:
                if segment.kind in ("heading", "editorial", "preface"):
                    continue
                first = max(position, source_leading) - source_leading
                last = position + len(segment.text) - source_leading
                if last > first:
                    styles.extend(
                        StyleSpan(kind, body_start + first, body_start + last)
                        for kind in segment.styles
                    )
                position += len(segment.text)
            pieces.append(body)
            offset += len(body)
            if number:
                styles.append(
                    StyleSpan(
                        "verse-start",
                        body_start - len(number),
                        body_start + first_word_length(body),
                    )
                )
            spans.append(
                PassageSpan(
                    reference,
                    start,
                    body_start,
                    offset,
                    members[1:],
                    label,
                    tuple(bases.get(ref, 0) for ref in members),
                )
            )
            count = sum(not c.isspace() for c in body)
            for ref in members:
                bases[ref] = bases.get(ref, 0) + count
            if not body.endswith("\n"):
                pieces.append(" ")
                offset += 1
        original = "".join(pieces)
        styles.extend(paragraph_spaces(original))
        display = list(original)
        for style in styles:
            if style.kind == "verse-start":
                for index in range(style.start, style.end):
                    if display[index].isspace():
                        display[index] = "\u00a0"
        return Document(key, "".join(display), tuple(spans), tuple(styles), original)

    def neighbour(self, key, direction):
        before, after = self.reader.neighbours(key)
        reference = before if direction < 0 else after
        return self.key(reference) if reference else None

    @property
    def rtl(self):
        return self.reader.rtl


class BibleBookPages(BiblePages):
    """Load one actual book on demand; chapters share a continuous document."""

    book_pages = True

    def key(self, reference):
        return self.reader.key(reference).getOSISBookName()

    def clone(self):
        from .sword_provider import Reader

        return BibleBookPages(Reader(self.reader.root, self.reader.name), self.resource)

    def document(self, key, preferences, *, cancelled=None):
        """Combine actual chapters into one cancellable book document while retaining source/copy anchors."""
        checkpoint(cancelled)
        code = key.split(".")[0]
        if "books" not in self.reader.__dict__:
            self.reader.__dict__["books"] = self.reader.discover_books(cancelled)
        book = next((b for b in self.reader.books if b.code == code), None)
        if book is None:
            raise ValueError("Book unavailable: " + code)
        pieces = []
        copies = []
        spans = []
        styles = []
        offset = 0
        for number in book.chapters:
            checkpoint(cancelled)
            doc = super().document(f"{code}.{number}", preferences, cancelled=cancelled)
            prefix = offset
            if pieces:
                pieces.append("\n\n")
                copies.append("\n\n")
                offset += 2
            pieces.append(doc.text)
            copies.append(doc.copy(0, len(doc.text)))
            for index, span in enumerate(doc.spans):
                spans.append(
                    replace(
                        span,
                        start=prefix if index == 0 else span.start + offset,
                        body=span.body + offset,
                        end=span.end + offset,
                    )
                )
            styles.extend(
                replace(style, start=style.start + offset, end=style.end + offset)
                for style in doc.styles
            )
            offset += len(doc.text)
        text = "".join(pieces)
        styles = [s for s in styles if s.kind != "paragraph-space"] + list(paragraph_spaces(text))
        return Document(code, text, tuple(spans), tuple(styles), "".join(copies))

    def neighbour(self, key, direction):
        codes = [b.code for b in self.reader.books]
        position = codes.index(key) + direction
        return codes[position] if 0 <= position < len(codes) else None


class CommentaryPages:
    """Expose indexed commentary entries and real source prefaces as paginated documents."""

    kind = "commentary"

    def __init__(self, reader, resource) -> None:
        self.reader = reader
        self.resource = resource

    def key(self, reference):
        return self.reader.index.locate(reference)

    def document(self, key, preferences: object):
        """Build one actual commentary section with separate UI-context and source style roles."""
        section = self.reader.index.sections[key]
        text = self.reader.index.text(key)
        from .commentary_format import format_entry, preverse_layout

        raw = self.reader.index.raw(key)
        source_type = str(self.reader.module.getConfigEntry("SourceType"))
        text, inline, titles = format_entry(raw, text, source_type)
        context = self.reader.index.label(key) + "\n"
        prefix = context + "".join(title + "\n" for title in titles)
        styles = [StyleSpan("ui-context", 0, len(context))]
        if len(prefix) > len(context):
            styles.append(StyleSpan("heading", len(context), len(prefix)))
        styles.extend(paragraph_spaces(prefix + text))
        styles.extend(
            StyleSpan(kind, first + len(prefix), last + len(prefix)) for kind, first, last in inline
        )
        reference = section.start if not section.introduction else "@" + str(section.index)
        document = Document(
            key,
            prefix + text,
            (PassageSpan(reference, 0, len(prefix), len(prefix) + len(text)),),
            tuple(styles),
        )
        document.has_preface = source_type == "OSIS" and bool(preverse_layout(raw)[0].strip())
        document.context_length = len(context)
        return document

    def preface(self, key):
        """Return the retained source preface as a separately styled document."""
        from .commentary_format import preverse_layout

        text, styles, _ = preverse_layout(self.reader.index.raw(key))
        return Document(
            ("preverse", key),
            text,
            (),
            tuple(StyleSpan(*s) for s in styles) + paragraph_spaces(text),
        )

    def neighbour(self, key, direction):
        return self.entry_neighbour(key, direction)

    def entry_neighbour(self, key, direction):
        position = key + direction
        return position if 0 <= position < len(self.reader.index.sections) else None

    @property
    def rtl(self):
        return self.reader.rtl


@dataclass(frozen=True)
class PageAddress:
    """An entry/book key and zero-based page position within its measured plan."""

    key: object
    index: int


class PagedStream:
    """Navigate a bounded on-demand cache of native page plans and canonical anchors."""

    def __init__(self, widget, source, preferences) -> None:
        self.widget = widget
        self.source = source
        self.preferences = preferences
        self.width = 400
        self.height = 500
        self.cache = OrderedDict()
        self.partitions = {}
        self.cursor = None

    def plan(self, key):
        """Build a missing plan synchronously and retain at most five recent plans."""
        if key not in self.cache:
            document = self.source.document(key, self.preferences)
            self.cache[key] = paginate(
                self.widget,
                document,
                self.preferences,
                self.width,
                self.height,
                self.partitions.get(key),
            )
            while len(self.cache) > 5:
                self.cache.popitem(last=False)
        self.cache.move_to_end(key)
        return self.cache[key]

    def configure(self, width, height, anchor, key) -> None:
        self.width = max(20, width)
        self.height = max(20, height)
        self.cache.clear()
        self.partitions.clear()
        self.partitions[key] = anchor
        plan = self.plan(key)
        self.cursor = PageAddress(key, plan.page_for_anchor(anchor))

    def step(self, address, direction):
        """Return an adjacent page address across real source boundaries, or None at the end."""
        plan = self.plan(address.key)
        index = address.index + direction
        if 0 <= index < len(plan.pages):
            return PageAddress(address.key, index)
        key = self.source.neighbour(address.key, direction)
        if key is None:
            return None
        return PageAddress(key, len(self.plan(key).pages) - 1 if direction < 0 else 0)

    def spread(self, count):
        addresses = [self.cursor]
        for _ in range(count - 1):
            after = self.step(addresses[-1], 1)
            if after is None:
                break
            addresses.append(after)
        return addresses

    def turn(self, direction, count):
        """Move the cursor by the requested spread, returning whether another spread is available."""
        if direction < 0:
            address = self.cursor
            for _ in range(count):
                before = self.step(address, -1)
                if before is None:
                    break
                address = before
            if address == self.cursor:
                return False
        else:
            address = self.step(self.spread(count)[-1], 1)
            if address is None:
                return False
        self.cursor = address
        return True

    def anchor(self):
        plan = self.plan(self.cursor.key)
        page = plan.pages[self.cursor.index]
        return plan.document.anchor(page.start)
