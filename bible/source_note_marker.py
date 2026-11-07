"""Native, keyboard-accessible source-note actions, separate from personal data."""
from gi.repository import Gtk,Pango,Gdk,GLib
from .i18n import tr
from .reference_preview import passage_title


def source_note_marker(markers,view,reader,reference,note,number):
    caption=note.locator or str(number)
    # Some supported GNOME runtimes do not ship talking-symbolic. Use the
    # native information glyph there, retaining the exact source locator below.
    theme=Gtk.IconTheme.get_for_display(view.get_display())
    icon='talking-symbolic' if theme.has_icon('talking-symbolic') else 'dialog-information-symbolic'
    image=Gtk.Image(icon_name=icon,pixel_size=10,valign=Gtk.Align.START,margin_bottom=6)
    button=Gtk.Button(child=image,halign=Gtk.Align.CENTER,valign=Gtk.Align.CENTER)
    button.add_css_class('flat');button.add_css_class('inline-marker');button.add_css_class('source-note-marker')
    button.set_cursor_from_name('pointer')
    title=tr('Translation notes')+' · '+passage_title(reference,system=reader.versification)
    button.update_property([Gtk.AccessibleProperty.LABEL],[title+' · '+caption])
    button._marker_reference=reference;button._marker_kind='translation-note'
    # Let GTK own tooltip text, wrapping and lifetime; replacing a custom
    # tooltip widget during repeated queries can invalidate its native surface.
    button.set_tooltip_text(note.text if len(note.text)<=220 else note.text[:220]+'…')
    button._source_note_popover=None
    def create(*_):
        # The first chapter can render before the tab is bound to its window.
        # Resolve the action owner when activated, as other marker kinds do.
        owner=markers.owner
        if not owner or owner.closed or not button.get_mapped() or owner.active_tab is not markers.tab:return
        previous=button._source_note_popover
        if previous and previous.get_visible():previous.popdown();return
        tab=markers.tab
        anchor=tab.comparison_overlay if view is tab.comparison_text else tab.reading_overlay
        found,bounds=button.compute_bounds(anchor)
        if not found:return
        pop=Gtk.Popover(autohide=False);pop.add_css_class('source-note-popover');pop.set_parent(anchor)
        rect=Gdk.Rectangle();rect.x=round(bounds.origin.x);rect.y=round(bounds.origin.y)
        rect.width=round(bounds.size.width);rect.height=round(bounds.size.height);pop.set_pointing_to(rect)
        button._source_note_popover=pop
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,
            margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        heading=Gtk.Label(label=title+' · '+caption,xalign=0,wrap=True,max_width_chars=34);heading.add_css_class('caption')
        box.append(heading)
        text=Gtk.Label(label=note.text,xalign=0,selectable=True,wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,max_width_chars=38)
        box.append(text)
        try:source=owner.library.resource(reader.name).description
        except (OSError,ValueError):source=reader.short_name
        credit=Gtk.Label(label=source,xalign=0,wrap=True,width_chars=1,max_width_chars=38)
        credit.add_css_class('caption');box.append(credit)
        scroll=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,propagate_natural_height=True,
            min_content_width=max(180,min(340,owner.get_width()-64)),max_content_height=max(100,min(360,owner.get_height()-120)))
        scroll.set_size_request(max(180,min(340,owner.get_width()-64)),-1)
        scroll.set_child(box);pop.set_child(scroll)
        def visibility(*_):
            if pop.get_visible():
                scroll.set_min_content_width(max(160,min(340,owner.get_width()-64)))
                scroll.set_size_request(max(160,min(340,owner.get_width()-64)),-1)
                scroll.set_max_content_height(max(100,min(360,owner.get_height()-120)))
                if pop not in owner._reading_popovers:owner._reading_popovers.append(pop)
                from .popover_dismissal import fit_reader_popover
                fit_reader_popover(pop,owner)
            elif pop in owner._reading_popovers:owner._reading_popovers.remove(pop)
        pop.connect('notify::visible',visibility)
        def closed(*_):
            if pop in owner._reading_popovers:owner._reading_popovers.remove(pop)
            if button._source_note_popover is pop:button._source_note_popover=None
            GLib.idle_add(lambda:pop.unparent() or False)
        pop.connect('closed',closed);pop.popup()
    button.connect('clicked',create)
    def hidden(*_):
        pop=button._source_note_popover
        if pop:pop.popdown()
    button.connect('unmap',hidden)
    return button
