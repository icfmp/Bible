"""Shared native passage card for reference and theme results."""
from gi.repository import Gtk,Pango


def passage_card(*,compound=False):
    # Cards with embedded links need a native composite instead of nesting
    # competing interactive descendants inside a GtkButton.
    button=Gtk.Box(orientation=Gtk.Orientation.VERTICAL) if compound else Gtk.Button()
    for name in ('card','annotation-card','reference-card','action-card'):button.add_css_class(name)
    button.set_cursor_from_name('pointer')
    content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
    title=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
    title.add_css_class('study-content')
    weight=Pango.AttrList();weight.insert(Pango.attr_weight_new(Pango.Weight.SEMIBOLD));title.set_attributes(weight)
    text=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,
                   ellipsize=Pango.EllipsizeMode.END,lines=3,width_chars=1)
    text.add_css_class('reference-excerpt');text.add_css_class('study-content')
    header=Gtk.Box(spacing=8)
    title.set_hexpand(True);header.append(title)
    arrow=Gtk.Image(icon_name='go-next-symbolic',pixel_size=12,valign=Gtk.Align.START)
    arrow.add_css_class('dim-label');header.append(arrow)
    content.append(header);content.append(text)
    if compound:button.append(content)
    else:button.set_child(content)
    button._card_content=content
    button._reference_labels=(title,text)
    return button
