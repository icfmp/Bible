"""Native child-anchor slots excluded from Scripture copy and canonical offsets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from .pagination import Document, InlineMarker, StyleSpan


def decorate(document: Document, markers: Mapping[str, Iterable[tuple[str, object]]]) -> Document:
    # Keep trailing paragraph separators after the compact metadata group.
    """Insert native marker slots and consistently shift spans, styles and source-offset mapping.

    Keep the original source document and copy projection so child anchors
    do not become Scripture content. Return the input unchanged without slots.
    """
    last = {ref: index for index, s in enumerate(document.spans) for ref in s.members}
    slots = sorted(
        (s.body + len(document.text[s.body : s.end].rstrip()), ref, kind, payload)
        for index, s in enumerate(document.spans)
        if last[s.reference] == index
        for ref in (s.reference,)
        for kind, payload in markers.get(ref, ())
    )
    if not slots:
        return document

    def shifted(offset: int, after: bool = False) -> int:
        return offset + sum(
            position < offset or (after and position == offset) for position, *_ in slots
        )

    pieces = []
    copies = []
    inline: dict[int, InlineMarker] = {}
    previous = 0
    offset = 0
    hidden = []
    for position, ref, kind, payload in slots:
        text = document.text[previous:position]
        pieces.append(text)
        offset += len(text)
        copies.append((document.copy_text or document.text)[previous:position])
        inline[offset] = (ref, kind, payload)
        hidden.append(StyleSpan("hidden", offset, offset + 1))
        pieces.append("\ufffc")
        copies.append("\ufffc")
        offset += 1
        previous = position
    pieces.append(document.text[previous:])
    copies.append((document.copy_text or document.text)[previous:])
    value = replace(
        document,
        text="".join(pieces),
        copy_text="".join(copies),
        spans=tuple(
            replace(
                s,
                start=shifted(s.start, True),
                body=shifted(s.body, True),
                end=shifted(s.end, True),
            )
            for s in document.spans
        ),
        styles=tuple(
            replace(s, start=shifted(s.start), end=shifted(s.end, True)) for s in document.styles
        )
        + tuple(hidden),
    )
    value.inline = inline
    value.source_shift = shifted
    value.source_document = document
    return value
