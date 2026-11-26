"""Map annotation identity to the current reader, without migrating annotations."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .highlights import Highlight, HighlightStore
    from .library import Library
    from .notes import Note, NoteStore
    from .sword_provider import Reader
import weakref
from .reference_resolution import resolve
from .notes import parts as parts


type ProjectionSpan = tuple[int, int, str, str]
type Projection = tuple[ProjectionSpan, ...]
type ProjectionKey = tuple[str, str, str, str, str | None, weakref.ReferenceType[Reader] | None]
type ProjectionCache = OrderedDict[ProjectionKey, Projection]
type OriginReaders = OrderedDict[str, tuple[tuple[int, int], Reader]]


class PassageAnnotations:
    """Cache verified display projections separately from persisted annotation identity."""

    def __init__(self, library: Library | None = None) -> None:
        self.cache: ProjectionCache = OrderedDict()
        self._reader_caches: weakref.WeakKeyDictionary[Reader, ProjectionCache] = (
            weakref.WeakKeyDictionary()
        )
        self._reader: weakref.ReferenceType[Reader] | None = None
        self.library = library
        self._notes_token: tuple[int, int, int] | None = None
        self._notes_snapshot: tuple[Note, ...] = ()

    def clear(self) -> None:
        """Release cached readers, projections and note snapshots without deleting annotations."""
        self.cache.clear()
        self._reader_caches.clear()
        self._reader = None
        self._notes_token = None
        self._notes_snapshot = ()

    def source_reader(self, reader: Reader | None, origin: str) -> Reader:
        """Reuse a bounded pool of validated installed origin readers, or raise if unavailable."""
        if reader is not None and origin == reader.name:
            return reader
        if not self.library:
            raise ValueError("Original translation is unavailable")
        import re
        from .providers import RESOURCE_ID

        if not re.fullmatch(RESOURCE_ID, origin):
            raise ValueError("Invalid annotation origin")
        root = self.library.root / origin
        info = (root / ".complete").stat()
        token = (root.stat().st_ino, info.st_mtime_ns)
        pool: OriginReaders | None = getattr(self.library, "_annotation_readers", None)
        if pool is None:
            self.library._annotation_readers = pool = OrderedDict()
        if origin not in pool or pool[origin][0] != token:
            from .sword_provider import Reader

            self.library.resource(origin)  # Existing installed-source validation.
            pool[origin] = (token, Reader(root, origin))
            if len(pool) > 4:
                pool.popitem(last=False)
        pool.move_to_end(origin)
        return pool[origin][1]

    def stored_notes(self, store: NoteStore) -> tuple[Note, ...]:
        """Refresh the cached validated notes only when store identity or SQLite data changes."""
        version: int = (
            store.db.execute("PRAGMA data_version").fetchone()[0] if hasattr(store, "db") else 0
        )
        token = (id(store), store.generation, version)
        if token != self._notes_token:
            self._notes_snapshot = tuple(store.all())
            self._notes_token = token
        return self._notes_snapshot

    def positions(
        self,
        reader: Reader,
        system: str,
        start: str,
        end: str,
        origin: str | None = None,
    ) -> Projection:
        # Providers can share a numbering-system name but use distinct native
        # address maps. Never reuse another reader's native positions or keep
        # its SWORD handles alive through this metadata cache.
        """Return independently verified target intervals without rewriting saved anchors.

        Unmappable gaps are omitted locally rather than filled by guessed endpoint
        correspondence. Cache entries belong to reader instances and do not keep
        replaced native resource handles alive.
        """
        if self._reader is None or self._reader() is not reader:
            self.cache = self._reader_caches.setdefault(reader, OrderedDict())
            self._reader = weakref.ref(reader)
        source = None
        if origin:
            try:
                source = self.source_reader(reader, origin)
            except (OSError, ValueError):
                return ()
            if source.versification != system:
                return ()
        key = (
            reader.versification,
            system,
            start,
            end,
            origin,
            weakref.ref(source) if source else None,
        )
        if key in self.cache:
            return self.cache[key]
        # Enumerate the source range before mapping: a source chapter can
        # overlap two target chapters, and legacy ranges must not be reduced
        # to their printed endpoints. This never changes stored ranges.
        intervals: list[ProjectionSpan] = []
        try:
            from .reference_resolution import _span
            from .reference_targets import Canon

            context = source or (
                reader
                if system == reader.versification and getattr(reader, "addresses", None)
                else Canon(system)
            )
            references: Iterable[str]
            if getattr(context, "addresses", None):
                # Fragment slots can interleave: physical indices cannot prove
                # public verse ordering. The source index validates this range.
                references = cast("Reader", context).reference_range(start, end)
            else:
                if context.key(start).getIndex() > context.key(end).getIndex():
                    raise ValueError("Reversed annotation range")
                references = _span(start, end, system)
            for reference in dict.fromkeys(references):
                # SWORD traversal includes native chapter introductions.
                if reference.rsplit(".", 1)[-1] == "0":
                    continue
                try:
                    if source and source is not reader:
                        from .reference_resolution import resolve_readers

                        mapped = resolve_readers(reference, source, reader, require_entry=False)
                    else:
                        mapped = resolve(reference, system, reader, require_entry=False)
                        if not source and hasattr(reader, "can_align_reference"):
                            if not all(
                                reader.can_align_reference(ref)
                                for ref in _span(
                                    mapped.start, mapped.end, reader.versification, reader
                                )
                            ):
                                raise ValueError("Annotation target correspondence is not verified")
                except ValueError:
                    # An unmapped title/gap must not erase the independently
                    # verified bodies later in the same saved annotation.
                    continue
                intervals.append(
                    (
                        reader.key(mapped.start).getIndex(),
                        reader.key(mapped.end).getIndex(),
                        mapped.start,
                        mapped.end,
                    )
                )
        except ValueError:
            intervals = []
        result = tuple(intervals)
        self.cache[key] = result
        if len(self.cache) > 4096:
            self.cache.popitem(last=False)
        return result

    def matches(
        self,
        reader: Reader,
        start: str,
        end: str,
        system: str,
        first: str,
        last: str,
        origin: str | None = None,
    ) -> bool:
        """Test overlap through explicit source units or verified annotation projection, retaining unavailable mappings."""
        if (
            (not origin or origin == reader.name)
            and system == reader.versification
            and getattr(reader, "addresses", None)
        ):
            try:
                return bool(
                    set(reader.reference_range(start, end))
                    & set(reader.reference_range(first, last))
                )
            except ValueError:
                return False
        if getattr(reader, "addresses", None):
            try:
                requested = set(reader.reference_range(start, end))
            except ValueError:
                return False
            spans = self.positions(reader, system, first, last, origin)
            return bool(requested & self.source_members(reader, spans))
        low, high = reader.key(start).getIndex(), reader.key(end).getIndex()
        return any(
            left <= high and right >= low
            for left, right, _, _ in self.positions(reader, system, first, last, origin)
        )

    @staticmethod
    def source_members(reader: Reader, spans: Iterable[ProjectionSpan]) -> set[str]:
        """Expand verified target spans through public IDs, never shared storage slots."""
        members: set[str] = set()
        for _, _, first, last in spans:
            if first == last:
                # positions() already validated this public identity. Avoid a
                # complete canon scan for every point in a long annotation.
                members.add(first)
                continue
            try:
                members.update(reader.reference_range(first, last))
            except ValueError:
                # One unavailable span must not erase other verified mappings.
                continue
        return members

    def notes(self, reader: Reader, start: str, end: str, store: NoteStore) -> list[Note]:
        """Select independent notes whose explicit links overlap the current source passage."""
        return [
            note
            for note in self.stored_notes(store)
            if any(
                self.matches(
                    reader,
                    start,
                    end,
                    link.versification,
                    link.start,
                    link.end,
                    note.origin_translation if link.versification == note.versification else None,
                )
                for link in note.passages
            )
        ]

    def highlights(
        self, reader: Reader, start: str, end: str, store: HighlightStore
    ) -> list[Highlight]:
        """Select saved marks with verified overlap, keeping their original identities unchanged."""
        return [
            mark
            for mark in store.entries.values()
            if self.matches(
                reader,
                start,
                end,
                mark["system"],
                mark["reference"],
                mark["reference"],
                mark["resource"],
            )
        ]

    @staticmethod
    def mark_priority(reader: Reader, mark: Highlight) -> tuple[int, str, str, str, str]:
        """Prefer current-resource then same-system paint projections with a stable deterministic tie-breaker."""
        return (
            0
            if mark["resource"] == reader.name
            else 1
            if mark["system"] == reader.versification
            else 2,
            mark["resource"],
            mark["system"],
            mark["reference"],
            mark["color"],
        )

    def colors(
        self, reader: Reader, references: Iterable[str], store: HighlightStore
    ) -> dict[str, Highlight]:
        """Project deterministic colors without conflating public references and storage.

        Addressed sources may share/interleave slots. Native index intervals
        remain the fast path only for ordinary modules without source maps.
        """
        from bisect import bisect_left, bisect_right

        if getattr(reader, "addresses", None):
            requested = set(references)
            for ref in requested:
                _ = reader.key(ref)  # Preserve validation without comparing storage slots.
            result: dict[str, Highlight] = {}
            for mark in sorted(store.entries.values(), key=lambda m: self.mark_priority(reader, m)):
                spans = self.positions(
                    reader, mark["system"], mark["reference"], mark["reference"], mark["resource"]
                )
                for ref in requested & self.source_members(reader, spans):
                    result.setdefault(ref, mark)
            return result
        indexed = sorted((reader.key(ref).getIndex(), ref) for ref in references)
        indices = [index for index, ref in indexed]
        result = {}
        if not indices:
            return result
        for mark in sorted(store.entries.values(), key=lambda m: self.mark_priority(reader, m)):
            try:
                candidate = resolve(mark["reference"], mark["system"], reader, require_entry=False)
                if (
                    reader.key(candidate.end).getIndex() < indices[0]
                    or reader.key(candidate.start).getIndex() > indices[-1]
                ):
                    continue
            except ValueError:
                continue
            spans = self.positions(
                reader, mark["system"], mark["reference"], mark["reference"], mark["resource"]
            )
            for left, right, _, _ in spans:
                for index, ref in indexed[
                    bisect_left(indices, left) : bisect_right(indices, right)
                ]:
                    result.setdefault(ref, mark)
        return result

    def note_map(
        self, reader: Reader, references: Iterable[str], store: NoteStore
    ) -> dict[str, list[Note]]:
        """Associate each requested reader reference with independently stored notes through verified link projections."""
        indices = {ref: reader.key(ref).getIndex() for ref in references}
        result: dict[str, list[Note]] = {}
        for note in self.stored_notes(store):
            for link in note.passages:
                spans = self.positions(
                    reader,
                    link.versification,
                    link.start,
                    link.end,
                    note.origin_translation if link.versification == note.versification else None,
                )
                members = (
                    self.source_members(reader, spans)
                    if getattr(reader, "addresses", None)
                    else None
                )
                for ref, index in indices.items():
                    covered = (
                        ref in members
                        if members is not None
                        else any(a <= index <= b for a, b, _, _ in spans)
                    )
                    if covered and note not in result.get(ref, ()):
                        result.setdefault(ref, []).append(note)
        return result
