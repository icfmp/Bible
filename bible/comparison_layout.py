"""Verified correspondence groups; display padding never becomes Scripture."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING
from dataclasses import dataclass, replace

if TYPE_CHECKING:
    from .sword_provider import Reader
from .reference_resolution import resolve_readers as resolve, _span
from .pagination import Document, StyleSpan, PassageSpan


@dataclass(frozen=True)
class Correspondence:
    """One verified correspondence group with actual primary/secondary source members."""

    primary: tuple[str, ...]
    secondary: tuple[str, ...]


def correspondences(
    primary: Reader,
    secondary: Reader,
    left: Iterable[str],
    right: Iterable[str],
    linked: tuple[Iterable[Sequence[str]], Iterable[Sequence[str]]] = ((), ()),
) -> tuple[Correspondence, ...]:
    """Connected mappings preserve merged/split source blocks exactly once.

    Both directions are checked. Unavailable mapping raises, rather than being
    confused with an absent module entry. Input lists contain actual entries.
    """
    left = tuple(left)
    right = tuple(right)
    nodes = {(0, r): {(0, r)} for r in left}
    nodes.update({(1, r): {(1, r)} for r in right})

    def merge(first: tuple[int, str], second: tuple[int, str]) -> None:
        own = nodes[first]
        other = nodes.get(second)
        if other is not None and other is not own:
            own.update(other)
            for n in other:
                nodes[n] = own

    def connect(side: int, reference: str, mapped: Iterable[str]) -> None:
        for ref in mapped:
            merge((side, reference), (1 - side, ref))

    for side, linked_groups in enumerate(linked):
        for members in linked_groups:
            for reference in members[1:]:
                merge((side, members[0]), (side, reference))
    for side, reader, target, refs in (
        (0, primary, secondary, left),
        (1, secondary, primary, right),
    ):
        for ref in refs:
            mapped = resolve(ref, reader, target, require_entry=False)
            connect(side, ref, _span(mapped.start, mapped.end, target.versification, target))
    unique = {id(group): group for group in nodes.values()}

    def order(group: set[tuple[int, str]]) -> int:
        own = [primary.key(ref).getIndex() for side, ref in group if side == 0]
        if own:
            return min(own)
        ref = next(ref for _, ref in group)
        return primary.key(resolve(ref, secondary, primary, require_entry=False).start).getIndex()

    groups = sorted(unique.values(), key=order)
    result = []
    last = (-1, -1)
    for group in groups:
        a = tuple(sorted((r for s, r in group if s == 0), key=lambda r: primary.key(r).getIndex()))
        b = tuple(
            sorted((r for s, r in group if s == 1), key=lambda r: secondary.key(r).getIndex())
        )
        positions = (
            min((primary.key(r).getIndex() for r in a), default=last[0]),
            min((secondary.key(r).getIndex() for r in b), default=last[1]),
        )
        if any(p < q for p, q in zip(positions, last)):
            raise ValueError("Non-monotonic correspondence; shared alignment unavailable")
        last = positions
        result.append(Correspondence(a, b))
    return tuple(result)


def row_document(
    document: Document,
    rows: Iterable[Correspondence],
    side: int,
    gap: str,
) -> tuple[Document, tuple[tuple[int, int], ...]]:
    """Reuse source words/styles, add paragraph boundaries only in comparison."""
    pieces = []
    copies = []
    spans = []
    styles = []
    bounds = []
    offset = 0
    source: dict[str, list[tuple[int, PassageSpan]]] = {}
    for i, s in enumerate(document.spans):
        for ref in s.members:
            source.setdefault(ref, []).append((i, s))
    previous_index = -1
    for row in rows:
        start = offset
        refs = row.primary if side == 0 else row.secondary
        if not refs:
            text = gap + "\n"
            pieces.append(text)
            copies.append(text)
            styles.append(StyleSpan("hidden", offset, offset + len(text)))
            offset += len(text)
        else:
            selected = {}
            for ref in refs:
                for index, span in source[ref]:
                    selected[index] = span
            for index, span in sorted(selected.items()):
                # A shared row must never regroup interleaved source fragments
                # around another verse. The existing independent-pane fallback
                # retains reading/comparison instead of changing source order.
                if index <= previous_index:
                    raise ValueError("Non-monotonic source fragments; shared alignment unavailable")
                previous_index = index
                end = (
                    document.spans[index + 1].start
                    if index + 1 < len(document.spans)
                    else len(document.text)
                )
                text = document.text[span.start : end]
                pieces.append(text)
                copies.append((document.copy_text or document.text)[span.start : end])
                spans.append(
                    replace(
                        span,
                        start=offset,
                        body=offset + span.body - span.start,
                        end=offset + span.end - span.start,
                    )
                )
                for style in document.styles:
                    low, high = max(span.start, style.start), min(end, style.end)
                    if high > low:
                        styles.append(
                            replace(
                                style,
                                start=offset + low - span.start,
                                end=offset + high - span.start,
                            )
                        )
                offset += len(text)
            if not pieces[-1].endswith("\n"):
                pieces.append("\n")
                copies.append("\n")
                offset += 1
        bounds.append((start, offset))
    return Document(
        document.key, "".join(pieces), tuple(spans), tuple(styles), "".join(copies)
    ), tuple(bounds)
