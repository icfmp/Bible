"""Read-only unified annotation projection; existing records keep their identity."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import cast
from .highlights import Highlight
from .notes import Note
from .book_names import FRENCH, normalized
from .notes import BOOK_ORDER, parts, label_key, passage_order
from .markdown import render


# Historical callers may project four-field highlights before migration. The
# current store supplies Highlight records, including nullable legacy dates.
type _Mark = Highlight | Mapping[str, str]
type AnnotationKey = tuple[str, ...]
type BibleOrder = tuple[
    int, str, tuple[int, int], int, tuple[str, tuple[int, int], int], AnnotationKey
]


@dataclass(frozen=True)
class Annotation:
    """A read-only note/highlight projection; overlap never creates persisted associations.

    records() supplies exactly one underlying note or highlight.
    """

    key: AnnotationKey
    system: str
    start: str
    end: str
    origin: str
    note: Note | None = None
    mark: _Mark | None = None

    @property
    def labels(self) -> tuple[str, ...]:
        return self.note.labels if self.note else ()

    @property
    def body(self) -> str:
        return self.note.body if self.note else ""

    @property
    def modified(self) -> str:
        return self.note.modified if self.note else (cast("_Mark", self.mark).get("modified") or "")

    @property
    def color(self) -> str | None:
        return self.mark["color"] if self.mark else None


def records(notes: Iterable[Note], marks: Iterable[_Mark]) -> list[Annotation]:
    """One row per note UUID or stored (versification, verse) highlight key."""
    return [
        Annotation(("note", n.id), n.versification, n.start, n.end, n.origin_translation, note=n)
        for n in notes
    ] + [
        Annotation(
            ("highlight", m["system"], m["reference"]),
            m["system"],
            m["reference"],
            m["reference"],
            m["resource"],
            mark=cast("_Mark", dict(m)),  # Copy preserves the proven source field types.
        )
        for m in marks
    ]


def bible_order(item: Annotation) -> BibleOrder:
    """Build a deterministic display sort key without conflating numbering systems."""
    book, chapter, verse = passage_order(item.start)
    return BOOK_ORDER.get(book, 10000), book, chapter, verse, passage_order(item.end), item.key


def filter_records(
    items: Iterable[Annotation],
    query: str = "",
    labels: Iterable[str] = (),
    category: str = "all",
    book: str = "",
    color: str = "",
    order: str = "recent",
    reference_names: Mapping[str, str] | None = None,
) -> list[Annotation]:
    """Filter annotation projections without mutating their underlying stored records.

    Date sorting retains unknown-date legacy highlights after dated records in
    canonical order. Labels match notes only; missing resources remain searchable.
    """
    words = [normalized(word) for word in query.split() if normalized(word)]
    wanted = {label_key(label) for label in labels}
    result = []
    for item in items:
        if category == "notes" and not item.note or category == "highlights" and not item.mark:
            continue
        code, chapter, verse = parts(item.start)
        links = item.note.passages if item.note else ()
        if (
            book
            and code != book
            and not any(parts(link.start)[0] == book for link in links)
            or color
            and item.color != color
        ):
            continue
        if not wanted <= {label_key(label) for label in item.labels}:
            continue
        text = normalized(
            " ".join(
                (
                    render(item.body)[0],
                    item.start,
                    item.end,
                    FRENCH.get(code, code),
                    f"{chapter}:{verse}",
                    (reference_names or {}).get(code, ""),
                    item.origin,
                    item.system,
                    item.color or "",
                    *item.labels,
                    *(
                        value
                        for link in links
                        for value in (
                            link.start,
                            link.end,
                            FRENCH.get(parts(link.start)[0], parts(link.start)[0]),
                        )
                    ),
                )
            )
        )
        if not all(word in text for word in words):
            continue
        result.append(item)
    result.sort(key=bible_order)
    # Legacy highlights have unknown dates; keep them in Bible order after
    # records with actual recorded modification dates.
    if order in ("recent", "oldest"):
        dated = [item for item in result if item.modified]
        undated = [item for item in result if not item.modified]
        dated.sort(key=lambda item: (item.modified, item.key), reverse=order == "recent")
        result = dated + undated
    return result
