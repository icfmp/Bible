"""Scoped reader palettes; libadwaita remains responsible for native widgets."""
import gi

gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk
from .reading_metrics import SPACING, WIDTHS

# background, text, link, selection background, selection text; opaque colors.
PALETTES = {
    'white': ('#ffffff', '#202020', '#003f87', '#004a99', '#ffffff'),
    'paper': ('#f4ecd8', '#302719', '#003f87', '#004a99', '#ffffff'),
    'dark': ('#282828', '#eeeeee', '#9fc5ff', '#b3d4ff', '#101010'),
    'black': ('#000000', '#eeeeee', '#9fc5ff', '#b3d4ff', '#101010'),
    'contrast-day': ('#ffffff', '#000000', '#003f87', '#004a99', '#ffffff'),
    'contrast-night': ('#000000', '#ffffff', '#9fc5ff', '#ffdf00', '#000000'),
}


def apply_direction(view,reader):
    """Resource direction affects the content, not the application's controls."""
    view.set_direction(Gtk.TextDirection.RTL if reader.rtl else Gtk.TextDirection.LTR)
    view.set_justification(Gtk.Justification.RIGHT if reader.rtl else Gtk.Justification.LEFT)


def effective_palette(preferences, dark, high_contrast):
    if high_contrast:
        return 'contrast-night' if dark else 'contrast-day'
    return preferences.night_palette if dark else preferences.day_palette


class ReadingStyle:
    def __init__(self, owner):
        self.owner = owner
        from weakref import WeakSet
        self.views = WeakSet()
        self.manager = Adw.StyleManager.get_default()
        self.scope = 'bible-content-' + str(id(owner))
        self.provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(owner.get_display(), self.provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.handlers = [self.manager.connect('notify::'+name, self.changed)
                         for name in ['dark', 'high-contrast']]
        self.apply_mode()

    def apply_mode(self):
        self.manager.set_color_scheme({'system':Adw.ColorScheme.DEFAULT,
                                      'day':Adw.ColorScheme.FORCE_LIGHT,
                                      'night':Adw.ColorScheme.FORCE_DARK}[self.owner.preferences.value.mode])
        self.changed()

    def decorate(self, view):
        self.views.add(view)
        view._reading_palette = self.palette
        from .verse_typography import NUMBER_COLORS
        for name in ['verse-number', 'page-number']:
            tag = view.get_buffer().get_tag_table().lookup(name)
            if tag:tag.props.foreground = NUMBER_COLORS[self.palette]
        view.add_css_class(self.scope)
        self.apply_text(view)

    def apply_text(self, view, preserve=True):
        # GtkTextMarks retain selection/body positions across tag-only reflow.
        if preserve and view.get_mapped() and not getattr(view,'_reader_reflow_tick',0):
            rect=view.get_visible_rect();_,iterator=view.get_iter_at_location(rect.x,rect.y)
            mark=view.get_buffer().create_mark(None,iterator,True)
            frames=[0]
            def restore(widget,*_):
                frames[0]+=1
                if widget.get_mapped() and not self.owner.closed:
                    if frames[0]<3:return True
                    target=widget.get_iter_location(widget.get_buffer().get_iter_at_mark(mark))
                    visible=widget.get_visible_rect()
                    adjustment=widget.get_parent().get_vadjustment()
                    adjustment.set_value(adjustment.get_value()+target.y-visible.y)
                    if frames[0]<5:return True
                widget.get_buffer().delete_mark(mark);widget._reader_reflow_tick=0
                return False
            view._reader_reflow_tick=view.add_tick_callback(restore)
        preferences = self.owner.preferences.value
        view.set_pixels_inside_wrap(SPACING[preferences.line_spacing])
        view.set_pixels_below_lines(SPACING[preferences.line_spacing] + 4)
        buffer = view.get_buffer()
        tag = buffer.get_tag_table().lookup('reader-typography')
        if tag is None:
            tag = buffer.create_tag('reader-typography')
        tag.props.family = preferences.font
        tag.props.size_points = preferences.size
        buffer.apply_tag(tag, buffer.get_start_iter(), buffer.get_end_iter())
        from .verse_typography import configure
        for name in ['verse-number','page-number','source-number']:
            number=buffer.get_tag_table().lookup(name)
            if number:configure(number,view,preferences,self.palette)

    def changed(self, *_):
        self.palette = effective_palette(self.owner.preferences.value,
                                         self.manager.get_dark(), self.manager.get_high_contrast())
        bg, fg, link, selection, selected = PALETTES[self.palette]
        selector = 'textview.' + self.scope
        self.css = f'''
.{self.scope}-surface {{ background-color: {bg}; color: {fg}; }}
.passage-actions {{ border-radius: 12px; padding: 3px; }}
.passage-actions button {{ min-width: 26px; min-height: 26px; padding: 2px; }}
{selector}, {selector} text {{ background-color: {bg}; color: {fg}; }}
{selector} text selection {{ background-color: {selection}; color: {selected}; }}
{selector} text link {{ color: {link}; }}
{selector}.study-reader, {selector}.study-reader text {{ background-color: transparent; color: @sidebar_fg_color; }}
{selector}:focus-visible {{ outline: 2px solid {fg}; outline-offset: -2px; }}
'''
        self.provider.load_from_data(self.css.encode())
        from .verse_typography import NUMBER_COLORS
        for view in self.views:
            view._reading_palette = self.palette
            for name in ['verse-number', 'page-number', 'source-number']:
                tag = view.get_buffer().get_tag_table().lookup(name)
                if tag:tag.props.foreground = NUMBER_COLORS[self.palette]
        appearance = getattr(self.owner, 'appearance', None)
        if appearance:
            appearance.sync_system()
        if hasattr(self.owner,'view') and hasattr(self.owner,'highlights'):self.owner.refresh_highlights()

    def close(self):
        for handler in self.handlers:
            self.manager.disconnect(handler)
        Gtk.StyleContext.remove_provider_for_display(self.owner.get_display(), self.provider)
