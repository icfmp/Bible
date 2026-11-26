"""Source-verified SWORD styling and structural display-offset remapping."""

from bisect import bisect_left, bisect_right
from itertools import accumulate
from html.parser import HTMLParser
from html import unescape
import re
from collections import defaultdict


class PreverseParts(HTMLParser):
    """Keep SWORD's preverse region separate from its stripped verse body."""

    CDATA_CONTENT_ELEMENTS = ("script", "style")
    RCDATA_CONTENT_ELEMENTS = ()

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.body = []
        self.prefix = []
        self.region = None
        self.hidden = 0

    def append(self, text):
        (self.prefix if self.region else self.body).append(text)

    def start(self, tag, attrs, raw, empty):
        """Retain raw source markup while tracking explicit preverse regions outside hidden content."""
        values = dict(attrs)
        if not self.hidden and tag == "div":
            if values.get("subtype") == "x-preverse" and values.get("sid"):
                self.region = values["sid"]
            if self.region and values.get("eid") == self.region:
                self.append(raw)
                self.region = None
                return
        self.append(raw)
        if not empty and tag in {"script", "style", "note"}:
            self.hidden += 1

    def handle_starttag(self, tag, attrs):
        self.start(tag, attrs, self.get_starttag_text(), False)

    def handle_startendtag(self, tag, attrs):
        self.start(tag, attrs, self.get_starttag_text(), True)

    def handle_endtag(self, tag):
        self.append("</" + tag + ">")
        if tag in {"script", "style", "note"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, text):
        self.append(text)

    def handle_entityref(self, name):
        self.append("&" + name + ";")

    def handle_charref(self, name):
        self.append("&#" + name + ";")


def split_preverse(raw):
    parser = PreverseParts()
    parser.feed(raw)
    parser.close()
    return "".join(parser.body), "".join(parser.prefix)


def preverse_layout(raw):
    """Real preverse prose/headings, outside legacy native body offsets."""
    if len(raw) > 2 * 1024 * 1024:
        return "", (), 0
    from .structured_text import SourceParser, checked_segments

    _, prefix = split_preverse(raw)
    parser = SourceParser()
    parser.feed(prefix)
    parser.close()
    native = "".join(s.text for s in parser.segments if s.kind == "text")
    parts = []
    styles = []
    offset = 0
    focus = 0
    for segment in checked_segments(parser.segments, native):
        text = segment.text
        if segment.kind in ("heading", "editorial"):
            # Same escaped-inline-title handling as InlineOSIS below.
            from .resource_details import PlainMetadata

            clean = PlainMetadata()
            clean.feed(text)
            text = "".join(clean.parts)
            if text.strip():
                styles.append((segment.kind, offset, offset + len(text)))
                focus = offset
        styles.extend(
            (kind, offset, offset + len(text)) for kind in segment.styles if kind != "poetry"
        )
        parts.append(text)
        offset += len(text)
    return "".join(parts), tuple(styles), focus


class InlineOSIS(HTMLParser):
    """Parse supported source roles and native emphasis decorations for later plain-text verification."""

    CDATA_CONTENT_ELEMENTS = ("script", "style")
    RCDATA_CONTENT_ELEMENTS = ()

    def __init__(self, source_type="OSIS", *, inline_titles=False, native_numeric_entities=False):
        super().__init__(convert_charrefs=not native_numeric_entities)
        self.source_type = source_type
        self.inline_titles = inline_titles
        self.native_numeric_entities = native_numeric_entities
        self.parts = []
        self.length = 0
        self.emphasis = []
        self.stack = []
        self.paragraphs = []
        self.title = 0
        self.title_parts = []
        self.titles = []
        self.hidden = 0
        self.structural = []
        self.structure_stack = []
        self.divisions = []
        self.paragraph_ids = set()

    def append(self, text):
        self.parts.append(text)
        self.length += len(text)

    def handle_starttag(self, tag, attrs):
        """Track actual source titles, inline emphasis and paragraph/list roles without executing markup."""
        values = dict(attrs)
        if tag in {"script", "style", "note"}:
            self.hidden += 1
            return
        if self.hidden:
            return
        if values.get("eid"):
            if tag == "div":
                if (
                    values.get("type") in {"paragraph", "x-p"}
                    or values["eid"] in self.paragraph_ids
                ):
                    self.paragraphs.append((self.length, 2))
                    self.paragraph_ids.discard(values["eid"])
                return
            self.handle_endtag(tag)
            return
        if tag == "title" and self.source_type == "OSIS":
            if self.inline_titles:
                self.structure_stack.append((tag, "heading", self.length))
            else:
                self.title += 1
            return
        if self.title:
            return
        if tag == "div":
            paragraph = values.get("type") in {"paragraph", "x-p"}
            if values.get("sid"):
                if paragraph:
                    self.paragraph_ids.add(values["sid"])
            else:
                self.divisions.append(paragraph)
        if tag == "hi":
            start = self.length
            self.append("* ")
            self.stack.append((values.get("type", ""), start, self.length))
        if tag in {"p", "lg"} or (tag == "div" and values.get("type") in {"paragraph", "x-p"}):
            self.paragraphs.append((self.length, 2))
            self.append("\n\n")
        elif tag in {"l", "lb", "br", "item", "li"}:
            self.paragraphs.append((self.length, 1))
            self.append("\n")
        kind = (
            "poetry"
            if tag == "l"
            else "quotation"
            if tag == "blockquote" or tag == "q" and values.get("type") == "block"
            else "list-item"
            if tag in {"item", "li"}
            else {
                "i": "italic",
                "em": "italic",
                "b": "bold",
                "strong": "bold",
                "sup": "superscript",
                "sub": "subscript",
            }.get(tag)
        )
        if self.source_type == "ThML" and re.fullmatch("h[1-6]", tag):
            kind = "heading"
        if kind and not values.get("eid"):
            self.structure_stack.append((tag, kind, self.length))

    def handle_startendtag(self, tag, attrs):
        values = dict(attrs)
        self.handle_starttag(tag, attrs)
        if not values.get("sid") and not values.get("eid"):
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        """Close supported style/structure ranges and preserve native decoration positions for verification."""
        if tag in {"script", "style", "note"}:
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag == "title" and self.source_type == "OSIS" and not self.inline_titles:
            self.title = max(0, self.title - 1)
            if not self.title:
                value = "".join(self.title_parts).strip()
                self.title_parts = []
                # Some SWORD OSIS titles contain entity-escaped inline tags.
                # Keep their words, never display or execute that markup.
                from .resource_details import PlainMetadata

                parser = PlainMetadata()
                parser.feed(value)
                value = "".join(parser.parts).strip()
                if value:
                    self.titles.append(value)
            return
        if self.title:
            return
        paragraph = self.divisions.pop() if tag == "div" and self.divisions else tag in {"p", "lg"}
        if paragraph:
            self.paragraphs.append((self.length, 2))
        elif tag in {"l", "item", "li"}:
            self.paragraphs.append((self.length, 1))
        for index in range(len(self.structure_stack) - 1, -1, -1):
            element, kind, start = self.structure_stack[index]
            if element == tag:
                self.structural.append((kind, start, self.length))
                self.structure_stack.pop(index)
                break
        if tag == "hi" and self.stack:
            kind, first, body = self.stack.pop()
            end = self.length
            self.append(" *")
            self.emphasis.append((kind, first, body, end, self.length - 1))

    def handle_data(self, text):
        if self.hidden:
            return
        if self.title:
            self.title_parts.append(text)
        else:
            self.append(text)

    def handle_entityref(self, name):
        self.handle_data(unescape("&" + name + ";"))

    def handle_charref(self, name):
        # SWORD OSISPlain drops numeric entity tokens, unlike named XML
        # entities. Verify this native form without repairing missing text or
        # treating an authored literal "&amp;#...;" as a numeric token.
        if not self.native_numeric_entities:
            self.handle_data(unescape("&#" + name + ";"))


def format_entry(raw, plain, source_type, *, preserve_offsets=False):
    """Return verified body, typed ranges and real source headings.

    SWORD OSISPlain inserts stars around hi elements. Validate source characters,
    literal stars and bounded generated markers before hiding decorations.
    Unknown conversions fall back to native text.
    """
    if source_type not in {"OSIS", "ThML"} or len(raw) > 2 * 1024 * 1024:
        return plain, (), ()
    try:
        body, _ = split_preverse(raw) if source_type == "OSIS" else (raw, "")
    except Exception:
        return plain, (), ()
    variants = [(body, False)]
    # OSISPlain may include or exclude titles according to the module's
    # registered heading filters. Accept only a complete source/native match;
    # an inline source title must not be mistaken for unknown body content.
    if source_type == "OSIS":
        variants.append((body, True))
    if source_type == "OSIS" and body != raw:
        # Other modules retain the complete source preface in native output.
        # Style it only if every character/marker verifies against that output.
        variants.append((raw, True))
    modes = [(False, False)]
    if source_type == "OSIS" and re.search(r"&#(?:[0-9]+|[xX][0-9a-fA-F]+);", raw):
        modes.append((True, False))
    if source_type == "OSIS" and re.search(r"&amp;#(?:[0-9]+|[xX][0-9a-fA-F]+);", raw):
        modes.append((True, True))
    for native_entities, nested_amp in modes:
        for source, inline_titles in variants:
            result = _verified_entry(
                source,
                plain,
                source_type,
                inline_titles=inline_titles,
                native_numeric_entities=native_entities,
                nested_amp=nested_amp,
                preserve_offsets=preserve_offsets,
            )
            if result is not None:
                return result
    return plain, (), ()


def _verified_entry(
    raw,
    plain,
    source_type,
    *,
    inline_titles=False,
    native_numeric_entities=False,
    nested_amp=False,
    preserve_offsets=False,
):
    """Map verified raw-source characters onto native plain text and return only evidenced display styles.

    Return None on parsing/content/decorations mismatch. Literal asterisks
    remain source content; only verified native decoration/padding is hidden.
    Optional paragraph insertions remap every style offset consistently.
    """
    if nested_amp:
        # Some native filter pipelines also process a nested numeric escape's
        # ampersand. This is only a verification candidate: accept it solely
        # when the complete unchanged native output matches. Never decode or
        # reconstruct the absent accented character in displayed/copy text.
        raw = re.sub(r"&amp;(?=\#(?:[0-9]+|[xX][0-9a-fA-F]+);)", "&#38;", raw)
    parser = InlineOSIS(
        source_type, inline_titles=inline_titles, native_numeric_entities=native_numeric_entities
    )
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        return None
    expected = "".join(parser.parts)
    generated = {marker for _, first, _, _, last in parser.emphasis for marker in (first, last)}
    # Native OSISPlain has one suspension buffer for nested hi elements, so
    # their generated stars can collect at a different emphasis boundary.
    # Verify every source character and literal star; permit only the exact
    # number of generated decorations, at actual source emphasis boundaries.
    left = [i for i, c in enumerate(expected) if not c.isspace() and c != "*"]
    right = [i for i, c in enumerate(plain) if not c.isspace() and c != "*"]
    if "".join(expected[i] for i in left) != "".join(plain[i] for i in right):
        return None
    literals = defaultdict(list)
    decorations = defaultdict(list)
    actual = defaultdict(list)
    boundaries = set()
    position = 0
    for index, char in enumerate(expected):
        if char.isspace():
            continue
        if char == "*":
            if index in generated:
                boundaries.add(position)
                decorations[position].append(index)
            else:
                literals[position].append(index)
        else:
            position += 1
    position = 0
    for index, char in enumerate(plain):
        if char.isspace():
            continue
        if char == "*":
            actual[position].append(index)
        else:
            position += 1
    if sum(map(len, actual.values())) != sum(map(len, literals.values())) + len(generated):
        return None
    mapping = dict(zip(left, right))
    hidden = set()
    for slot in actual.keys() | literals.keys():
        authored = literals[slot]
        native = actual[slot]
        if len(native) < len(authored) or len(native) > len(authored) and slot not in boundaries:
            return None
        # Literal stars keep their order relative to opening/closing hi
        # decorations. Mapping every literal to the first native star can
        # otherwise move its authored whitespace across an emphasis boundary.
        selected = [
            native[i + min(len(native) - len(authored), bisect_left(decorations[slot], source))]
            for i, source in enumerate(authored)
        ]
        mapping.update(zip(authored, selected))
        hidden.update(set(native) - set(selected))
    left = sorted(mapping)
    right = [mapping[i] for i in left]
    # OSISPlain emits "* " and " *" around hi. Removing just the stars
    # leaves double word gaps and a space before punctuation. At verified
    # emphasis boundaries only, hide surplus ASCII padding that is absent
    # from the source. Never collapse authored whitespace or rewrite text;
    # native offsets (also used by Bible projections) remain unchanged.
    padding = {i for _, first, _, _, last in parser.emphasis for i in (first + 1, last - 1)}
    gaps = {bisect_left(left, i) for i in padding}
    for gap in gaps:
        first = left[gap - 1] + 1 if gap else 0
        last = left[gap] if gap < len(left) else len(expected)
        start = right[gap - 1] + 1 if gap else 0
        end = right[gap] if gap < len(right) else len(plain)
        authored = "".join(
            expected[i] for i in range(first, last) if expected[i].isspace() and i not in padding
        )
        cursor = 0
        extra = []
        for i in range(start, end):
            if i in hidden:
                continue
            char = plain[i]
            if cursor < len(authored) and char == authored[cursor]:
                cursor += 1
            elif char == " ":
                extra.append(i)
            else:
                break
        else:
            if cursor == len(authored) and len(extra) <= sum(
                i in hidden and plain[i] == "*" for i in range(start, end)
            ):
                hidden.update(extra)
    styles = []
    for i in sorted(hidden):
        if styles and styles[-1][2] == i:
            styles[-1] = ("hidden", styles[-1][1], i + 1)
        else:
            styles.append(("hidden", i, i + 1))
    display = list(plain)
    for kind, first, body, end, last in parser.emphasis:
        content = right[bisect_left(left, body) : bisect_left(left, end)]
        style = {
            "italic": "italic",
            "bold": "bold",
            "super": "number",
            "small-caps": "small-caps",
        }.get(kind)
        if content and style:
            styles.append((style, content[0], content[-1] + 1))
    for kind, begin, end in parser.structural:
        content = right[bisect_left(left, begin) : bisect_left(left, end)]
        if content:
            styles.append((kind, content[0], content[-1] + 1))
    insertions = {}
    for boundary, count in parser.paragraphs:
        position = bisect_left(left, boundary)
        if not 0 < position < len(right):
            continue
        first = right[position - 1] + 1
        last = right[position]
        whitespace = [i for i in range(first, last) if display[i].isspace()]
        if len(whitespace) >= count or (
            last > first and all(c.isspace() for c in display[first:last])
        ):
            for index in whitespace[:count]:
                display[index] = "\n"
            if not preserve_offsets and len(whitespace) < count:
                insertions[last] = max(insertions.get(last, 0), count - len(whitespace))
        elif not preserve_offsets:
            # SWORD may omit every separator between source-authored blocks.
            # Insert before decorations, keeping all native characters intact.
            insertions[first] = max(insertions.get(first, 0), count)
    if insertions:
        positions = sorted(insertions)
        totals = [0, *accumulate(insertions[p] for p in positions)]
        original = "".join(display)
        pieces = []
        previous = 0
        for position in positions:
            pieces.extend((original[previous:position], "\n" * insertions[position]))
            previous = position
        pieces.append(original[previous:])
        display = "".join(pieces)

        def shift(offset, include_at):
            return totals[(bisect_right if include_at else bisect_left)(positions, offset)]

        styles = [
            (kind, start + shift(start, True), end + shift(end, False))
            for kind, start, end in styles
        ]
    return "".join(display), tuple(styles), tuple(parser.titles)


def apply(view, styles, preferences, palette):
    """Apply native tags for already-verified character spans without rewriting the buffer or source."""
    from gi.repository import Pango
    from .verse_typography import configure

    buffer = view.get_buffer()
    table = buffer.get_tag_table()
    for kind, first, last in styles:
        name = "source-" + kind
        tag = table.lookup(name) or buffer.create_tag(name)
        # Keep native visible-byte indices aligned with the buffer. GTK 4.20
        # can abort in pixel-to-iterator conversion with invisible inline tags.
        # Zero-scale source decorations have no ink/advance; Document.copy()
        # still omits precisely these verified generated markers.
        if kind in ("hidden", "native-decoration"):
            tag.props.scale = 0
        elif kind == "italic":
            tag.props.style = Pango.Style.ITALIC
        elif kind == "bold":
            tag.props.weight = 700
        elif kind == "small-caps":
            tag.props.variant = Pango.Variant.SMALL_CAPS
        elif kind == "number":
            configure(tag, view, preferences, palette)
        elif kind == "superscript":
            configure(tag, view, preferences, palette)
        elif kind == "subscript":
            tag.props.scale = 0.8
            tag.props.rise = -3000
        elif kind == "editorial":
            from .verse_typography import NUMBER_COLORS
            from .reading_metrics import line_spacing, EDITORIAL_GAP

            tag.props.scale = 0.9
            tag.props.foreground = NUMBER_COLORS[palette]
            tag.props.pixels_below_lines = line_spacing(preferences) + EDITORIAL_GAP
        elif kind == "heading":
            tag.props.weight = 700
            tag.props.scale = 1.12
        elif kind == "ui-context":
            tag.props.weight = 400
            tag.props.scale = 0.85
        elif kind in {"poetry", "quotation", "list-item"}:
            tag.props.left_margin = 16
            tag.props.right_margin = 8
            tag.props.indent = -8 if kind == "list-item" else 0
        elif kind == "paragraph-space":
            from .reading_metrics import paragraph_space_size

            tag.props.size_points = paragraph_space_size(preferences)
            tag.props.pixels_above_lines = 0
            tag.props.pixels_below_lines = 0
            tag.props.pixels_inside_wrap = 0
        buffer.apply_tag(tag, buffer.get_iter_at_offset(first), buffer.get_iter_at_offset(last))


def show_preface(owner, reader, resource, position):
    """Read actual source preverse material without changing the verse anchor."""
    from gi.repository import Adw, Gtk
    from .paged_sources import CommentaryPages
    from .bible_render import bind_copy
    from .i18n import tr
    from .preferences import ReadingPreferences

    document = CommentaryPages(reader, resource).preface(position)
    if not document.text.strip():
        return None
    old = getattr(owner, "commentary_preface", None)
    if old:
        old.close()
    window = Adw.Window(
        transient_for=owner,
        modal=True,
        title=tr("Read source preface"),
        default_width=640,
        default_height=600,
    )
    window.set_destroy_with_parent(True)
    window.add_css_class(owner.reading_style.scope + "-window")
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    header = Adw.HeaderBar()
    header.set_title_widget(
        Adw.WindowTitle(title=tr("Read source preface"), subtitle=resource.description)
    )
    box.append(header)
    view = Gtk.TextView(
        editable=False,
        cursor_visible=False,
        wrap_mode=Gtk.WrapMode.WORD_CHAR,
        left_margin=24,
        right_margin=24,
        top_margin=20,
        bottom_margin=24,
    )
    view.add_css_class(owner.reading_style.scope)
    from .reading_style import apply_direction

    apply_direction(view, reader)
    buffer = view.get_buffer()
    buffer.set_text(document.text)
    body = buffer.create_tag(
        "preface-body", family=owner.preferences.value.study_font, size_points=12, line_height=1.5
    )
    buffer.apply_tag(body, buffer.get_start_iter(), buffer.get_end_iter())
    apply(
        view,
        [(s.kind, s.start, s.end) for s in document.styles],
        ReadingPreferences(font=owner.preferences.value.study_font, size=12),
        owner.reading_style.palette,
    )
    bind_copy(view, document)
    scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
    scroll.set_child(view)
    box.append(scroll)
    window.set_content(box)
    window.text = view
    window.source_document = document
    owner.commentary_preface = window

    def closed(*_):
        if getattr(owner, "commentary_preface", None) is window:
            owner.commentary_preface = None
        return False

    window.connect("close-request", closed)
    window.present()
    return window
