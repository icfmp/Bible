"""Small accessible source links; full attribution is separate from Bible text."""
from urllib.parse import urlsplit
from gi.repository import Gtk,GLib,Pango
from .i18n import tr


def source_credit(provenance):
    lines=provenance.splitlines();caption=lines[0] if lines else ''
    urls=[line for line in lines[1:] if urlsplit(line).scheme=='https' and urlsplit(line).netloc]
    credit=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
    credit.add_css_class('caption');credit.add_css_class('source-attribution')
    if urls:
        parts=caption.split(' · ')
        markup='<a href="'+GLib.markup_escape_text(urls[0])+'">'+GLib.markup_escape_text(parts[0])+'</a>'
        for part in parts[1:]:
            markup+=' · '+('<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>' if part=='CC BY 4.0' else GLib.markup_escape_text(part))
        credit.set_markup(markup)
    else:credit.set_text(caption)
    credit.set_tooltip_text(provenance);credit.update_property([Gtk.AccessibleProperty.LABEL],[tr('Source and license')+': '+caption])
    return credit
