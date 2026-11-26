"""Conservative SWORD markup extraction; no HTML execution or invented headings."""

from dataclasses import dataclass
from html.parser import HTMLParser
import re


@dataclass(frozen=True)
class Segment:
    """Actual source text with an inert presentation role and optional inline styles."""

    text: str
    kind: str = "text"
    styles: tuple[str, ...] = ()


class SourceParser(HTMLParser):
    # OSIS/ThML titles contain inline XML. Recent HTMLParser releases give
    # HTML title/textarea RCDATA semantics, which would expose those tags.
    """Extract a conservative supported markup structure without executing HTML or adding headings."""

    CDATA_CONTENT_ELEMENTS = ("script", "style")
    RCDATA_CONTENT_ELEMENTS = ()

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.segments = []
        self.hidden = 0
        self.heading = 0
        self.heading_kinds = []
        self.divisions = []
        self.paragraph_ids = set()
        self.inline = []

    def handle_starttag(self, tag, attrs):
        """Track supported inline/block milestones while excluding script/style/note bodies from prose."""
        attrs = dict(attrs)
        # HTMLParser normalizes attribute names, including OSIS sID/eID.
        # A closing milestone is a boundary, never a new enclosing block.
        if attrs.get("eid"):
            if self.hidden:
                return
            if tag == "l":
                self.segments.append(Segment("\n", "poetry", ("poetry",)))
            elif (
                tag == "lg"
                or tag == "div"
                and (
                    attrs.get("type") in {"paragraph", "x-p"} or attrs["eid"] in self.paragraph_ids
                )
            ):
                self.segments.append(Segment("\n\n", "break"))
                self.paragraph_ids.discard(attrs["eid"])
            return
        if tag in {"script", "style", "note"}:
            self.hidden += 1
        if self.hidden:
            return
        styles = []
        if tag == "hi":
            styles = {
                "italic": ["italic"],
                "emphasis": ["italic"],
                "bold": ["bold"],
                "bolditalic": ["bold", "italic"],
                "x-bold-italic": ["bold", "italic"],
                "small-caps": ["small-caps"],
                "super": ["superscript"],
            }.get(attrs.get("type"), [])
        elif tag == "transchange" and attrs.get("type") == "added":
            styles = ["italic"]
        elif tag == "divinename":
            styles = ["small-caps"]
        if tag in ("hi", "transchange", "divinename"):
            self.inline.append((tag, tuple(styles)))
        if tag in {"title", "h1", "h2", "h3", "h4"}:
            self.heading += 1
            self.heading_kinds.append(
                "editorial" if tag == "title" and attrs.get("type") == "parallel" else "heading"
            )
        if tag == "div":
            paragraph = attrs.get("type") in {"paragraph", "x-p"}
            if paragraph and attrs.get("sid"):
                self.paragraph_ids.add(attrs["sid"])
            if not attrs.get("sid"):
                self.divisions.append(paragraph)
        else:
            paragraph = tag in {"p", "lg"}
        if tag == "milestone" and attrs.get("type") == "x-source-blank-line":
            self.segments.append(Segment("\n\n", "blank-line"))
        elif paragraph or (tag == "milestone" and attrs.get("type") in {"x-p", "paragraph"}):
            self.segments.append(Segment("\n\n", "break"))
        elif tag in {"lb", "br"}:
            self.segments.append(Segment("\n", "line-break", ("poetry",)))
        elif tag == "l":
            self.segments.append(Segment("\n", "poetry", ("poetry",)))

    def handle_endtag(self, tag):
        """Close supported source roles and retain actual paragraph/poetry boundaries."""
        if tag in {"script", "style", "note"}:
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag in ("hi", "transchange", "divinename"):
            for index in range(len(self.inline) - 1, -1, -1):
                if self.inline[index][0] == tag:
                    del self.inline[index:]
                    break
        if tag in {"title", "h1", "h2", "h3", "h4"}:
            self.heading = max(0, self.heading - 1)
            self.segments.append(Segment("\n", "break"))
            if self.heading_kinds:
                self.heading_kinds.pop()
        paragraph = self.divisions.pop() if tag == "div" and self.divisions else tag in {"p", "lg"}
        if paragraph:
            self.segments.append(Segment("\n\n", "break"))

    def handle_startendtag(self, tag, attrs):
        # Empty ThML p and OSIS start/end milestones each mark a boundary.
        # Do not synthesize a second end event, or retain an empty title/note.
        """Apply empty source milestones without incorrectly closing paired start/end markers."""
        self.handle_starttag(tag, attrs)
        if (
            not dict(attrs).get("sid")
            and not dict(attrs).get("eid")
            and tag in {"note", "script", "style", "title", "h1", "h2", "h3", "h4", "div"}
        ):
            self.handle_endtag(tag)

    def handle_data(self, text):
        """Retain visible source text with current heading/inline roles."""
        if not self.hidden:
            self.segments.append(
                Segment(
                    text,
                    self.heading_kinds[-1] if self.heading_kinds else "text",
                    tuple(dict.fromkeys(style for _, styles in self.inline for style in styles)),
                )
            )


def extract(raw, plain, source_type):
    """Use structure only when its body words agree with SWORD's own plain text.

    A mismatch falls back to exact plain text: unknown markup cannot rewrite the
    resource or leak notes/commands into a purported faithful Bible rendering.
    """
    if source_type not in {"OSIS", "ThML"}:
        return (Segment(plain),)
    parser = SourceParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        return (Segment(plain),)
    segments = parser.segments
    if source_type == "OSIS":
        segments = native_emphasis(segments, raw, plain)
    return checked_segments(segments, plain)


def native_emphasis(segments, raw, plain):
    """Reuse verified SWORD decoration detection; retain authored literal stars."""
    normalize = lambda value: re.sub(r"\s+", "", value)
    source = "".join(s.text for s in segments if s.kind == "text")
    if normalize(source) == normalize(plain):
        return segments
    from .commentary_format import format_entry

    # Only native marker indices are consumed here. SourceParser already owns
    # the Bible's structural segments; display insertion must not shift these.
    _, styles, _ = format_entry(raw, plain, "OSIS", preserve_offsets=True)
    hidden = {i for kind, first, last in styles if kind == "hidden" for i in range(first, last)}
    if not hidden or normalize(source) != normalize(
        "".join(c for i, c in enumerate(plain) if i not in hidden)
    ):
        return segments
    boundaries = {}
    position = 0
    for index, char in enumerate(plain):
        if index in hidden:
            boundaries.setdefault(position, []).append(char)
        elif not char.isspace():
            position += 1
    total = position
    position = 0
    result = []
    for segment in segments:
        if segment.kind != "text":
            result.append(segment)
            continue
        run = []

        def decoration():
            if run:
                result.append(Segment("".join(run), "text", segment.styles))
                run.clear()
            result.append(
                Segment("".join(boundaries.pop(position)), "text", ("native-decoration",))
            )

        for char in segment.text:
            if not char.isspace():
                if position in boundaries:
                    decoration()
                position += 1
            run.append(char)
            if position == total and position in boundaries:
                decoration()
        if run:
            result.append(Segment("".join(run), "text", segment.styles))
    return result if not boundaries else segments


def checked_segments(segments, plain):
    """Accept markup roles only when non-whitespace body text matches the supplied plain source.

    Mismatch falls back to the exact plain text. Accepted structural separators
    are coalesced without introducing new words or inferred editorial headings.
    """
    body = "".join(s.text for s in segments if s.kind == "text")
    normalize = lambda v: re.sub(r"\s+", "", v)
    if normalize(body) != normalize(plain):
        # Some StripText filters retain editorial titles. Do not guess which
        # words belong to verses; use the original plain output in that case.
        return (Segment(plain),)
    result = []
    pending = []

    def flush(next_segment=None):
        if not pending:
            return next_segment
        boundaries = [
            s for s in pending if s.kind in {"break", "poetry", "line-break", "blank-line"}
        ]
        if boundaries:
            # Formatting whitespace between paired milestones is not an extra
            # paragraph. Retain the strongest authored boundary exactly once.
            kind = (
                "break" if any(s.kind in {"break", "blank-line"} for s in boundaries) else "poetry"
            )
            count = max(
                2 if kind == "break" else 1,
                sum(s.kind == "line-break" for s in boundaries),
                1 + sum(s.kind == "blank-line" for s in boundaries)
                if any(s.kind == "blank-line" for s in boundaries)
                else 0,
            )
            if result:
                previous = result[-1]
                result[-1] = Segment(previous.text.rstrip(), previous.kind, previous.styles)
            result.append(Segment("\n" * count, kind, ("poetry",) if kind == "poetry" else ()))
            if next_segment is not None:
                next_segment = Segment(
                    next_segment.text.lstrip(), next_segment.kind, next_segment.styles
                )
        else:
            for item in pending:
                if result and (result[-1].kind, result[-1].styles) == (item.kind, item.styles):
                    previous = result.pop()
                    item = Segment(previous.text + item.text, item.kind, item.styles)
                result.append(item)
        pending.clear()
        return next_segment

    for segment in segments:
        if (
            segment.kind in {"break", "poetry", "line-break", "blank-line"}
            or segment.text.isspace()
        ):
            pending.append(segment)
            continue
        segment = flush(segment)
        if result and (result[-1].kind, result[-1].styles) == (segment.kind, segment.styles):
            previous = result.pop()
            segment = Segment(previous.text + segment.text, segment.kind, segment.styles)
        result.append(segment)
    flush()
    return tuple(s for s in result if s.text) or (Segment(plain),)
