"""Shared native passage card for reference and theme results."""
from gi.repository import Gtk,Pango


def passage_card():
    button=Gtk.Button()
    for name in ('card','annotation-card','reference-card'):button.add_css_class(name)
    content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
    title=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
    title.add_css_class('study-content')
    weight=Pango.AttrList();weight.insert(Pango.attr_weight_new(Pango.Weight.SEMIBOLD));title.set_attributes(weight)
    text=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,
                   ellipsize=Pango.EllipsizeMode.END,lines=3,width_chars=1)
    text.add_css_class('reference-excerpt');text.add_css_class('study-content')
    content.append(title);content.append(text);button.set_child(content)
    button._reference_labels=(title,text)
    return button
