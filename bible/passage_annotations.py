"""Map annotation identity to the current reader, without migrating annotations."""
from collections import OrderedDict
import weakref
from .reference_resolution import resolve
from .notes import parts


class PassageAnnotations:
    def __init__(self):
        self.cache = OrderedDict()
        self._reader=None

    def positions(self, reader, system, start, end):
        # Providers can share a numbering-system name but use distinct native
        # address maps. Never reuse another reader's native positions or keep
        # its SWORD handles alive through this metadata cache.
        if self._reader is None or self._reader() is not reader:
            self.cache.clear();self._reader=weakref.ref(reader)
        key = (reader.versification, system, start, end)
        if key in self.cache:return self.cache[key]
        # Enumerate the source range before mapping: a source chapter can
        # overlap two target chapters, and legacy ranges must not be reduced
        # to their printed endpoints. This never changes stored ranges.
        intervals = []
        try:
            from .reference_resolution import _span
            resolve(start, system, reader, require_entry=False)
            resolve(end, system, reader, require_entry=False)
            source=(reader.reference_range(start,end) if system==reader.versification and getattr(reader,'addresses',None)
                    else _span(start,end,system))
            for reference in dict.fromkeys(source):
                # SWORD traversal includes native chapter introductions.
                if reference.rsplit('.',1)[-1]=='0':continue
                mapped = resolve(reference, system, reader, require_entry=False)
                intervals.append((reader.key(mapped.start).getIndex(), reader.key(mapped.end).getIndex(),
                                  mapped.start, mapped.end))
        except ValueError:
            intervals = []
        result = tuple(intervals)
        self.cache[key] = result
        if len(self.cache) > 4096:self.cache.popitem(last=False)
        return result

    def matches(self, reader, start, end, system, first, last):
        if system==reader.versification and getattr(reader,'addresses',None):
            try:return bool(set(reader.reference_range(start,end))&set(reader.reference_range(first,last)))
            except ValueError:return False
        low, high = reader.key(start).getIndex(), reader.key(end).getIndex()
        return any(left <= high and right >= low for left, right, _, _ in
                   self.positions(reader, system, first, last))

    def notes(self, reader, start, end, store):
        return [note for note in store.all() if any(self.matches(reader,start,end,
            link.versification,link.start,link.end) for link in note.passages)]

    def highlights(self, reader, start, end, store):
        return [mark for mark in store.entries.values() if self.matches(reader, start, end,
                mark['system'], mark['reference'], mark['reference'])]
