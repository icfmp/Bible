"""Scoped reader palettes; libadwaita remains responsible for native widgets."""
import gi

gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk
from .reading_metrics import SPACING, WIDTHS, line_spacing

# background, text, link, selection background, selection text; opaque colors.
PALETTES = {
    'white': ('#ffffff', '#202020', '#003f87', '#004a99', '#ffffff'),
    'paper': ('#f4ecd8', '#302719', '#003f87', '#004a99', '#ffffff'),
    'dark': ('#282828', '#eeeeee', '#9fc5ff', '#b3d4ff', '#101010'),
    'black': ('#000000', '#eeeeee', '#9fc5ff', '#b3d4ff', '#101010'),
    'contrast-day': ('#ffffff', '#000000', '#003f87', '#004a99', '#ffffff'),
    'contrast-night': ('#000000', '#ffffff', '#9fc5ff', '#ffdf00', '#000000'),
}


def apply_direction(view,reader,preferences=None):
    """Resource direction affects the content, not the application's controls."""
    view.set_direction(Gtk.TextDirection.RTL if reader.rtl else Gtk.TextDirection.LTR)
    view.set_justification(Gtk.Justification.FILL if preferences and preferences.alignment=='justified' else
                           Gtk.Justification.RIGHT if reader.rtl else Gtk.Justification.LEFT)


def effective_palette(preferences, dark, high_contrast):
    if high_contrast:
        return 'contrast-night' if dark else 'contrast-day'
    return preferences.night_palette if dark else preferences.day_palette


class ReadingStyle:
    def __init__(self, owner):
        self.owner = owner
        self.initial_palette=self.palette_settings()
        from weakref import WeakSet
        self.views = WeakSet()
        self.manager = Adw.StyleManager.get_default()
        self.scope = 'bible-content-' + str(id(owner))
        owner.add_css_class(self.scope+'-window')
        self.provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(owner.get_display(), self.provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.handlers = [self.manager.connect('notify::'+name, self.changed)
                         for name in ['dark', 'high-contrast']]
        self.apply_mode()

    def palette_settings(self):
        return {k:getattr(self.owner.preferences.value,k) for k in ('mode','day_palette','night_palette')}

    def remember_tab_palettes(self):
        for tab in self.owner.tabs():
            if not tab.state.reading_palette:tab.state.reading_palette=self.palette_settings()

    def activate_tab(self,tab):
        for key,value in tab.state.reading_palette.items():setattr(self.owner.preferences.value,key,value)
        self.apply_mode()
        self.owner.appearance.sync()

    def apply_mode(self):
        mode=self.owner.preferences.value.mode
        if mode=='system':
            mode={'light':'day','dark':'night','system':'system'}[self.owner.application_settings.value['interface_appearance']]
        self.dark = mode=='night' or (mode=='system' and self.manager.get_dark())
        self.manager.set_color_scheme({'system':Adw.ColorScheme.DEFAULT,
                                      'day':Adw.ColorScheme.FORCE_LIGHT,
                                      'night':Adw.ColorScheme.FORCE_DARK}[mode])
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
        view.set_pixels_inside_wrap(line_spacing(preferences))
        view.set_pixels_below_lines(line_spacing(preferences) + 4)
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
        if hasattr(self.owner,'queue_layout'):self.owner.queue_layout()
        mode=self.owner.preferences.value.mode
        base=self.owner.application_settings.value['interface_appearance']
        self.dark=(mode=='night' or mode=='system' and (base=='dark' or base=='system' and self.manager.get_dark()))
        self.palette = effective_palette(self.owner.preferences.value,self.dark,self.manager.get_high_contrast())
        bg, fg, link, selection, selected = PALETTES[self.palette]
        selector = 'textview.' + self.scope
        focus_width = 3 if self.manager.get_high_contrast() else 2
        from .verse_typography import NUMBER_COLORS
        marker_color=NUMBER_COLORS[self.palette]
        import json
        study_family=json.dumps(self.owner.preferences.value.study_font,ensure_ascii=False)
        action_background='#101010' if self.manager.get_high_contrast() else 'rgba(12,12,14,.84)'
        self.css = f'''
.{self.scope}-surface {{ background-color: {bg}; color: {fg}; }}
textview.{self.scope} button.inline-marker {{ color: {marker_color}; min-width: 18px; min-height: 18px; padding: 0 1px; margin: 0 1px; border-radius: 4px; }}
textview.{self.scope} button.inline-marker image {{ -gtk-icon-size: 12px; }}
.passage-actions {{ border-radius: 16px; padding: 0; background-color: transparent; color: #ffffff; }}
.passage-actions button {{ color: #ffffff; background: transparent; box-shadow: none; }}
.passage-actions button:hover {{ background-color: rgba(255,255,255,.12); }}
.passage-actions button:active {{ background-color: rgba(255,255,255,.22); }}
.passage-actions button:focus-visible {{ outline: 2px solid #ffffff; outline-offset: -2px; }}
.passage-actions popover contents, .passage-actions popover arrow {{ background-color: #202020; color: #ffffff; }}
.passage-actions-content {{ background-color: {action_background}; color: white; border-radius: 16px; padding: 12px; }}
.passage-actions button {{ min-width: 36px; min-height: 36px; padding: 0; }}
{selector}, {selector} text {{ background-color: {bg}; color: {fg}; }}
{selector} text selection {{ background-color: {selection}; color: {selected}; }}
{selector} text link {{ color: {link}; }}
{selector}.study-reader, {selector}.study-reader text {{ background-color: transparent; color: @sidebar_fg_color; }}
.{self.scope}-window .study-drawer .study-content,
.{self.scope}-window .study-drawer .study-content text {{ font-family: {study_family}; }}
/* GTK owns focus-visible/modality. Draw on the text CSS node so its opaque
   background cannot cover the focus mark. Inset shadows do not change layout. */
{selector}:not(.immersive-page):focus-visible text {{ box-shadow: inset {focus_width}px 0 0 {link}; }}
{selector}:not(.immersive-page):dir(rtl):focus-visible text {{ box-shadow: inset -{focus_width}px 0 0 {link}; }}
.{self.scope}-focus-cue {{ box-shadow: inset {focus_width}px 0 0 {link}; }}
.{self.scope}-focus-cue.rtl-reading {{ box-shadow: inset -{focus_width}px 0 0 {link}; }}
'''
        window='.'+self.scope+'-window'
        if not self.manager.get_high_contrast():
            sidebar={'paper':'#e5dcc3','black':'#121212','white':'#f0f0f0','dark':'#303030'}[self.palette]
            chrome={'paper':'#eee4cb','black':'#080808','white':'#fafafa','dark':'#242424'}[self.palette]
            # Scope native surfaces to this owner; leave tags, images and semantic
            # accents to their existing renderers. Transparent controls inherit.
            self.css+=f"""
{window}, {window} .background:not(popover), {window} .view, {window} .card,
{window} popover contents, {window} dialog {{ background-color: {bg}; color: {fg}; }}
{window} headerbar, {window} tabbar, {window} tabbar tabbox {{ background-color: {chrome}; color: {fg}; }}
{window} .sidebar, {window} .sidebar-pane, {window} .study-panel, {window} .study-divider {{ background-color: {sidebar}; color: {fg}; }}
{window} textview.study-reader, {window} textview.study-reader text {{ color: {fg}; }}
{window} .study-drawer headerbar, {window} .study-drawer headerbar .title,
{window} .study-drawer headerbar .start, {window} .study-drawer headerbar .end {{ background-color: {sidebar}; color: {fg}; }}
{window} popover {{ background: transparent; }}
{window} popover arrow {{ background-color: {bg}; }}
{window} .passage-actions {{ background-color: transparent; color: white; }}
{window} .passage-actions popover contents, {window} .passage-actions popover arrow {{ background-color: #202020; color: white; }}
"""
        for name,(background,foreground,*_) in PALETTES.items():
            if name.startswith('contrast'):continue
            self.css+=f'.{self.scope}-window .palette-preview-{name} {{ background-color: {background}; color: {foreground}; border-radius: 6px; padding: 6px 14px; border: 1px solid alpha(currentColor,.3); }}\n'
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
