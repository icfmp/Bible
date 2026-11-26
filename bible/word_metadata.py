"""Conservative OSIS lexical evidence; no inferred STEP token alignment."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypedDict
from html.parser import HTMLParser

if TYPE_CHECKING:
    from .passage_actions import Target
import re


class _NumberedSource(Protocol):
    versification: str


class LexicalEvidence(TypedDict):
    """Explicit identifiers and source attributes for one verified word span."""

    identifiers: tuple[str, ...]
    source_lemma: str
    source_morphology: str | None


class WordParser(HTMLParser):
    """Collect explicit source word spans and attributes for conservative lexical alignment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.characters: list[str] = []
        self.words: list[tuple[int, int, dict[str, str | None]]] = []
        self.current: list[tuple[int, dict[str, str | None]]] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("note", "title", "script", "style"):
            self.hidden += 1
        if not self.hidden and tag == "w":
            self.current.append((len(self.characters), dict(attrs)))

    def handle_endtag(self, tag: str) -> None:
        if tag in ("note", "title", "script", "style"):
            self.hidden = max(0, self.hidden - 1)
            return
        if not self.hidden and tag == "w" and self.current:
            start, attrs = self.current.pop()
            self.words.append((start, len(self.characters), attrs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, text: str) -> None:
        if not self.hidden:
            self.characters.extend(c for c in text if not c.isspace())


def aligned_identifiers(
    raw: str, source_body: str, prefix: str, selected: str
) -> LexicalEvidence | None:
    """Return recorded Strong identifiers only for one exact word span in a verified source text.

    Compare non-whitespace source characters first. Missing, ambiguous or
    mismatching evidence returns None rather than inferring token alignment.
    """
    parser = WordParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        return None
    plain = lambda value: "".join(c for c in value if not c.isspace())
    if "".join(parser.characters) != plain(source_body):
        return None
    start = len(plain(prefix))
    end = start + len(plain(selected))
    matches = [attrs for a, b, attrs in parser.words if a == start and b == end and b > a]
    if len(matches) != 1:
        return None
    attrs = matches[0]
    ids: list[str] = []
    lemma = attrs.get("lemma") or ""
    for language, number, suffix in re.findall(r"\bstrong:([GH])(\d{1,5})([A-Z]?)(?!\w)", lemma):
        value = language + f"{int(number):04d}" + suffix
        if value not in ids:
            ids.append(value)
    if not ids:
        return None
    return dict(
        identifiers=tuple(ids),
        source_lemma=lemma,
        source_morphology=attrs.get("morph", ""),
    )


def selected_metadata(target: Target) -> LexicalEvidence | None:
    """Read explicit OSIS lexical evidence for a native selection contained in one source verse.

    This accesses the mutable native reader position; callers must respect
    the reader lifetime and serialized-use contract.
    """
    if not target.native_selection or len(target.references) != 1:
        return None
    source = target.source
    reader = source.reader
    document = source.document
    if reader.module.getConfigEntry("SourceType") != "OSIS":
        return None
    reference = target.references[0]
    span = next((s for s in document.spans if s.reference == reference), None)
    bounds = getattr(target, "selection", None)
    if not span or not bounds:
        return None
    first, last = bounds
    if first < span.body or last > span.end:
        return None
    reader.module.setKey(reader.key(reference))
    raw = reader.module.getRawEntry()
    raw = raw if isinstance(raw, str) else raw.c_str()
    return aligned_identifiers(
        raw,
        document.copy(span.body, span.end),
        document.copy(span.body, first),
        document.copy(first, last),
    )


def source_verse_references(reference: str, reader: _NumberedSource) -> tuple[str, ...]:
    """Keep Psalm superscriptions separate from a source verse's body words.

    Prefer existing pinned verse-part mappings. Native SWORD can collapse a
    numbered title onto a body verse; require unambiguous reciprocal coverage
    when the pinned bridge is unavailable. No introduction becomes verse one.
    """
    from .reference_targets import Canon
    from .reference_resolution import resolve, _span, VersificationMismatch
    from .versification_mapping import to_base, from_base

    source = Canon(reader.versification)
    target = Canon("NRSV")
    source.key(reference)
    parts = to_base(reference, reader.versification)
    if parts is not None:
        projected: set[str] = set()
        for part in parts:
            # JSword's !pv is a Psalm title; !v denotes the verse body.
            # A whole-verse fallback must never erase that distinction.
            if "!pv" in part or part.startswith("?"):
                raise VersificationMismatch("No source-body alignment for heading: " + reference)
            mapped = from_base(part, "NRSV")
            if not mapped:
                raise VersificationMismatch("No source-verse alignment: " + reference)
            projected.update(mapped)
        if not projected:
            raise VersificationMismatch("No source-verse alignment: " + reference)
        ordered = sorted(projected, key=lambda ref: target.key(ref).getIndex())
        if _span(ordered[0], ordered[-1], "NRSV") != ordered:
            raise VersificationMismatch("Non-contiguous source-verse alignment: " + reference)
        return tuple(ordered)
    mapped = resolve(reference, reader.versification, target, require_entry=False)
    refs = _span(mapped.start, mapped.end, "NRSV")
    key = source.key(reference)
    index = key.getIndex()
    verse = key.getVerse()
    for ref in refs:
        reverse = resolve(ref, "NRSV", source, require_entry=False)
        if not source.key(reverse.start).getIndex() <= index <= source.key(reverse.end).getIndex():
            raise VersificationMismatch("No reciprocal source-verse alignment: " + reference)
    for neighbour in (verse - 1, verse + 1):
        if not 1 <= neighbour <= key.getVerseMax():
            continue
        key.setVerse(neighbour)
        other = resolve(key.getOSISRef(), reader.versification, target, require_entry=False)
        if set(refs).intersection(_span(other.start, other.end, "NRSV")):
            raise VersificationMismatch("Ambiguous source-verse alignment: " + reference)
    return tuple(refs)
