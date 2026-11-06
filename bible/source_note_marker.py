"""Native, keyboard-accessible source-note actions, separate from personal data."""
from gi.repository import Gtk,Pango
from .i18n import tr
from .reference_preview import passage_title


def source_note_marker(owner,reader,reference,note,number):
    caption=note.locator or str(number)
    label=Gtk.Label(label=caption)
    attrs=Pango.AttrList();attrs.insert(Pango.attr_scale_new(.7))
    attrs.insert(Pango.attr_rise_new(6*Pango.SCALE));label.set_attributes(attrs)
    button=Gtk.MenuButton(child=label,halign=Gtk.Align.CENTER,valign=Gtk.Align.CENTER)
    button.add_css_class('flat');button.add_css_class('inline-marker');button.add_css_class('source-note-marker')
    button.set_cursor_from_name('pointer')
    title=tr('Translation notes')+' · '+passage_title(reference,system=reader.versification)
    button.update_property([Gtk.AccessibleProperty.LABEL],[title+' · '+caption])
    button._marker_reference=reference;button._marker_kind='translation-note'
    button.set_has_tooltip(True)
    def tooltip(_button,x,y,keyboard,tip):
        preview=Gtk.Label(label=note.text if len(note.text)<=220 else note.text[:220]+'…',
            wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,max_width_chars=42,
            margin_top=4,margin_bottom=4,margin_start=4,margin_end=4)
        # GTK owns the tooltip lifetime; scope the dark surface to this tooltip
        # and remove its class before the native window is reused elsewhere.
        roots=[]
        def mapped(widget):
            root=widget.get_root()
            if root:root.add_css_class('source-note-tooltip');roots.append(root)
        def unmapped(*_):
            for root in roots:root.remove_css_class('source-note-tooltip')
            roots.clear()
        preview.connect('map',mapped);preview.connect('unmap',unmapped)
        tip.set_custom(preview);return True
    button.connect('query-tooltip',tooltip)
    pop=Gtk.Popover();pop.add_css_class('source-note-popover')
    box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,
        margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
    heading=Gtk.Label(label=title,xalign=0,wrap=True,max_width_chars=34);heading.add_css_class('caption')
    box.append(heading)
    text=Gtk.Label(label=note.text,xalign=0,selectable=True,wrap=True,
        wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,max_width_chars=38)
    box.append(text)
    resource=owner.library.resource(reader.name)
    credit=Gtk.Label(label=resource.description,xalign=0,wrap=True,width_chars=1,max_width_chars=38)
    credit.add_css_class('caption');box.append(credit)
    scroll=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,propagate_natural_height=True,
        min_content_width=max(180,min(340,owner.get_width()-64)),max_content_height=max(100,min(360,owner.get_height()-120)))
    scroll.set_child(box);pop.set_child(scroll);button.set_popover(pop)
    def visibility(*_):
        if pop.get_visible():
            if pop not in owner._reading_popovers:owner._reading_popovers.append(pop)
            from .popover_dismissal import fit_reader_popover
            fit_reader_popover(pop,owner)
        elif pop in owner._reading_popovers:owner._reading_popovers.remove(pop)
    pop.connect('notify::visible',visibility)
    button.connect('unmap',lambda *_:pop.popdown())
    return button
