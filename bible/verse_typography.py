"""Shared verse-marker geometry; display-only tags never alter source words."""

from __future__ import annotations

import re
import unicodedata
from gi.repository import Pango, GLib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gi.repository import Gtk
    from .preferences import ReadingPreferences

NUMBER_SCALE = 0.60
NUMBER_COLORS = {
    "white": "#626262",
    "paper": "#685e4d",
    "dark": "#aaaaaa",
    "black": "#aaaaaa",
    "contrast-day": "#000000",
    "contrast-night": "#ffffff",
}
_INDEPENDENT_BREAKS = frozenset(
    (
        GLib.UnicodeBreakType.IDEOGRAPHIC,
        GLib.UnicodeBreakType.COMPLEX_CONTEXT,
        GLib.UnicodeBreakType.HANGUL_L_JAMO,
        GLib.UnicodeBreakType.HANGUL_V_JAMO,
        GLib.UnicodeBreakType.HANGUL_T_JAMO,
        GLib.UnicodeBreakType.HANGUL_LV_SYLLABLE,
        GLib.UnicodeBreakType.HANGUL_LVT_SYLLABLE,
    )
)


def first_word_length(body: str) -> int:
    """Bound the verse-number joining span using actual script break behavior and complete combining clusters."""
    match = re.match(r"\s*\S+", body)
    if not match:
        return 0
    # A whitespace token can be an entire sentence in Chinese, Japanese or
    # Thai. Let the toolkit break that script normally after the first cluster;
    # the marker must not turn the whole sentence into an unbreakable span.
    for index, char in enumerate(body[: match.end()]):
        if char.isspace():
            continue
        if char.isascii() and char.isalpha():
            return match.end()
        if GLib.unichar_break_type(char) in _INDEPENDENT_BREAKS:
            end = index + 1
            while end < match.end() and unicodedata.category(body[end]).startswith("M"):
                end += 1
            return end
        if char.isalpha():
            return match.end()
    return match.end()


def number_rise(context: Pango.Context, preferences: ReadingPreferences) -> int:
    """Keep superscript rise proportional to the selected body font’s actual ascent."""
    font = Pango.FontDescription(f"{preferences.font} {preferences.size}")
    # A fixed 6000-unit rise could exceed the small glyph's line box. Keep the
    # scaled ascent plus rise safely inside the actual body font ascent.
    return int(context.get_metrics(font, context.get_language()).get_ascent() * 0.22)


def configure(
    tag: Gtk.TextTag, view: Gtk.Widget, preferences: ReadingPreferences, palette: str = "white"
) -> None:
    tag.props.scale = NUMBER_SCALE
    tag.props.rise = number_rise(view.get_pango_context(), preferences)
    tag.props.foreground = NUMBER_COLORS[palette]
