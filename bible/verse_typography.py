"""Shared verse-marker geometry; display-only tags never alter source words."""
import re
from gi.repository import Pango

NUMBER_SCALE = .60
NUMBER_COLORS = {'white':'#626262', 'paper':'#685e4d', 'dark':'#aaaaaa',
                 'black':'#aaaaaa', 'contrast-day':'#000000', 'contrast-night':'#ffffff'}


def first_word_length(body):
    match = re.match(r'\s*\S+', body)
    return match.end() if match else 0


def number_rise(context, preferences):
    font = Pango.FontDescription(f'{preferences.font} {preferences.size}')
    # A fixed 6000-unit rise could exceed the small glyph's line box. Keep the
    # scaled ascent plus rise safely inside the actual body font ascent.
    return int(context.get_metrics(font, context.get_language()).get_ascent() * .22)


def configure(tag, view, preferences, palette='white'):
    tag.props.scale = NUMBER_SCALE
    tag.props.rise = number_rise(view.get_pango_context(), preferences)
    tag.props.foreground = NUMBER_COLORS[palette]
