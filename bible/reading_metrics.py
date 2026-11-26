"""Reader geometry shared by GTK and the independent Pango worker."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .preferences import ReadingPreferences

EDITORIAL_GAP = 5  # Extra space after a source-typed editorial reference block.
# Internal leading for Bible and immersive headings, including wrapped lines.
# Keep this in the Pango page plan as well as GtkTextTag allocation. The study
# sidebar/source preface already use a more generous 1.5 line height.
HEADING_LINE_HEIGHT = 1.15
WIDTHS = {"narrow": 580, "normal": 760, "wide": 960}
SPACING = {"tight": 1, "normal": 5, "airy": 10, "very-airy": 16}


def line_spacing(preferences: ReadingPreferences) -> int:
    """Return the explicit spacing override or the selected preset."""
    custom = getattr(preferences, "line_spacing_px", None)
    return custom if custom is not None else SPACING[preferences.line_spacing]


def paragraph_space_size(preferences: ReadingPreferences) -> float:
    """Reserve a small paragraph gap without inserting a full reading line."""
    # A paragraph boundary is spacing, not an additional full-sized text line.
    return max(1, preferences.size * 0.25)


def text_width(preferences: ReadingPreferences) -> int:
    """Return the explicit column width or the selected preset."""
    custom = getattr(preferences, "text_width_px", None)
    return custom if custom is not None else WIDTHS[preferences.column_width]


def side_margin(preferences: ReadingPreferences, default: int) -> int:
    """Use the saved margin when present, otherwise the caller’s layout minimum."""
    custom = getattr(preferences, "side_margin_px", None)
    return custom if custom is not None else default
