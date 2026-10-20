"""Real native reading controls, persisted immediately and applied to all tabs."""
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk, Pango
from .i18n import tr


class AppearancePopover(Gtk.Popover):
    def __init__(self, owner):
        super().__init__()
        self.owner=owner
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_top=16,margin_bottom=16,margin_start=16,margin_end=16)
        title=Gtk.Label(label=tr('Reading appearance'));title.add_css_class('heading');box.append(title)
        self.font=Gtk.FontButton(use_font=True,use_size=False,title=tr('Reading font'))
        self.font.set_font(f'{owner.preferences.value.font} {owner.preferences.value.size}')
        self.font.set_tooltip_text(tr('Reading font'))
        self.font.connect('font-set',self.font_changed);box.append(self.font)
        row=Gtk.Box(spacing=12)
        row.append(Gtk.Label(label=tr('Text size'),hexpand=True,xalign=0))
        self.size=Gtk.SpinButton.new_with_range(12,40,1);self.size.set_value(owner.preferences.value.size)
        self.size.update_property([Gtk.AccessibleProperty.LABEL],[tr('Text size')])
        self.size.connect('value-changed',lambda widget:self.update('size',widget.get_value_as_int()))
        row.append(self.size);box.append(row)
        for attr,label in [('chapter_numbers','Chapter numbers'),('verse_numbers','Verse numbers')]:
            button=Gtk.CheckButton(label=tr(label),active=getattr(owner.preferences.value,attr))
            button.connect('toggled',lambda widget,key=attr:self.update(key,widget.get_active()))
            setattr(self,attr,button);box.append(button)
        self.status=Gtk.Label(wrap=True,max_width_chars=30,xalign=0,label=owner.preferences.error)
        box.append(self.status)
        if not owner.preferences.writable:
            for widget in [self.font,self.size,self.chapter_numbers,self.verse_numbers]:widget.set_sensitive(False)
        self.set_child(box)

    def font_changed(self, widget):
        self.update('font',Pango.FontDescription.from_string(widget.get_font()).get_family())

    def update(self,key,value):
        setattr(self.owner.preferences.value,key,value)
        try:
            self.owner.preferences.save()
            self.owner.apply_appearance()
            self.status.set_text('')
        except (OSError,ValueError) as error:self.status.set_text(str(error))
