"""Map annotation identity to the current reader, without migrating annotations."""
from collections import OrderedDict
from .reference_resolution import resolve
from .notes import parts


class PassageAnnotations:
    def __init__(self):
        self.cache = OrderedDict()

    def positions(self, reader, system, start, end):
        key = (reader.versification, system, start, end)
        if key in self.cache:return self.cache[key]
        # Stored notes are bounded to one chapter. Map every source verse;
        # endpoint-only conversion could fill a discontinuous mapped interval.
        first, last = parts(start), parts(end)
        if first[:2] != last[:2]:return ()
        intervals = []
        try:
            for verse in range(first[2], last[2]+1):
                mapped = resolve(f'{first[0]}.{first[1]}.{verse}', system, reader, require_entry=False)
                intervals.append((reader.key(mapped.start).getIndex(), reader.key(mapped.end).getIndex(),
                                  mapped.start, mapped.end))
        except ValueError:
            intervals = []
        result = tuple(intervals)
        self.cache[key] = result
        if len(self.cache) > 4096:self.cache.popitem(last=False)
        return result

    def matches(self, reader, start, end, system, first, last):
        low, high = reader.key(start).getIndex(), reader.key(end).getIndex()
        return any(left <= high and right >= low for left, right, _, _ in
                   self.positions(reader, system, first, last))

    def notes(self, reader, start, end, store):
        return [note for note in store.all() if self.matches(reader, start, end, note.versification, note.start, note.end)]

    def highlights(self, reader, start, end, store):
        return [mark for mark in store.entries.values() if self.matches(reader, start, end,
                mark['system'], mark['reference'], mark['reference'])]
