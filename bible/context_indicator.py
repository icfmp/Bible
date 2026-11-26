"""Paint-only dotted study coverage; never selection, tags or saved highlights."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import cast

import gi

gi.require_version("Graphene", "1.0")
from gi.repository import Gdk, Graphene, Gtk
from .verse_typography import NUMBER_COLORS
from .reading_style import PALETTES


type IndicatorSegment = tuple[float, float, float, str]


@dataclass(slots=True)
class _IndicatorRow:
    """Mutable bounds and glyph intervals belonging to one visible display row."""

    top: int
    bottom: int
    intervals: list[tuple[int, int, str]]


class ContextTextView(Gtk.TextView):
    """Paint transient study coverage without changing selection, text tags or saved highlights."""

    _verse_fragments: Sequence[tuple[str, int, int]]
    _verse_labels: dict[str, str]

    def set_study_ranges(self, ranges: Iterable[tuple[int, int]]) -> None:
        """Replace half-open buffer offsets and redraw only when coverage changes.

        Call on the GTK owner thread after projecting references into this view.
        The immutable snapshot prevents later caller mutations affecting paint.
        """
        value = tuple(ranges)
        if value != getattr(self, "study_ranges", ()):
            self.study_ranges = value
            self.queue_draw()

    def indicator_segments(self) -> list[IndicatorSegment]:
        """Measure only visible covered glyphs and merge underline intervals with selection/highlight colors."""
        ranges = getattr(self, "study_ranges", ())
        if not ranges or not self.get_mapped():
            return []
        buffer = self.get_buffer()
        visible = self.get_visible_rect()
        _, first = self.get_iter_at_location(visible.x, visible.y)
        _, last = self.get_iter_at_location(visible.x + visible.width, visible.y + visible.height)
        self.backward_display_line_start(first)
        self.forward_display_line_end(last)
        low, high = first.get_offset(), min(buffer.get_char_count(), last.get_offset() + 1)
        selection = buffer.get_selection_bounds()
        selected = tuple(i.get_offset() for i in selection)
        palette = getattr(self, "_reading_palette", "white")
        neutral = NUMBER_COLORS[palette]
        rows: list[_IndicatorRow] = []
        for start, end in ranges:
            iterator = buffer.get_iter_at_offset(max(start, low))
            while iterator.get_offset() < min(end, high):
                rect = self.get_iter_location(iterator)
                if rect.width:
                    x, y = self.buffer_to_window_coords(Gtk.TextWindowType.WIDGET, rect.x, rect.y)
                    left, right = sorted((x, x + rect.width))
                    bottom = y + rect.height
                    if bottom > 0 and y < self.get_height():
                        color = neutral
                        if selected and selected[0] <= iterator.get_offset() < selected[1]:
                            color = PALETTES[palette][4]
                        else:
                            for tag in iterator.get_tags():
                                if (tag.props.name or "").startswith(
                                    "highlight-"
                                ) and tag.props.foreground_set:
                                    # A set foreground is exposed by GTK as an RGBA value.
                                    color = cast(Gdk.RGBA, tag.props.foreground_rgba).to_string()
                        row = next((r for r in rows if max(y, r.top) < min(bottom, r.bottom)), None)
                        if row is None:
                            row = _IndicatorRow(y, bottom, [])
                            rows.append(row)
                        row.top = min(row.top, y)
                        row.bottom = max(row.bottom, bottom)
                        row.intervals.append((left, right, color))
                if not iterator.forward_char():
                    break
        segments: list[IndicatorSegment] = []
        for row in rows:
            for segment_left, segment_right, color in sorted(row.intervals):
                underline_y = (
                    row.bottom - 0.5 + min(2, max(0, (self.get_pixels_inside_wrap() - 1) / 2))
                )
                if (
                    segments
                    and segments[-1][2:] == (underline_y, color)
                    and segment_left <= segments[-1][1] + 1
                ):
                    previous = segments.pop()
                    segments.append(
                        (previous[0], max(segment_right, previous[1]), underline_y, color)
                    )
                else:
                    segments.append((segment_left, segment_right, underline_y, color))
        return segments

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        """Append clipped GSK coverage dots after the native text snapshot; retain no periodic worker."""
        Gtk.TextView.do_snapshot(self, snapshot)
        segments = self.indicator_segments()
        if not segments:
            return
        clip = Graphene.Rect()
        clip.init(0, 0, self.get_width(), self.get_height())
        snapshot.push_clip(clip)
        for left, right, y, value in segments:
            color = Gdk.RGBA()
            color.parse(value)
            x = left
            while x < right:
                dot = Graphene.Rect()
                dot.init(x, y, min(1, right - x), 1)
                snapshot.append_color(color, dot)
                x += 3
        snapshot.pop()
