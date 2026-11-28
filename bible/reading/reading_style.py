"""Scoped reader palettes; libadwaita remains responsible for native widgets."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from weakref import WeakSet

if TYPE_CHECKING:
    from ..ui import Window
    from .reading_tab import ReadingTab
    from ..sword_provider import Reader
    from ..preferences import ReadingPreferences

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
from .reading_metrics import SPACING as SPACING, WIDTHS as WIDTHS, line_spacing

# background, text, link, selection background, selection text; opaque colors.
PALETTES = {
    "white": ("#ffffff", "#202020", "#003f87", "#004a99", "#ffffff"),
    "paper": ("#f4ecd8", "#302719", "#003f87", "#004a99", "#ffffff"),
    "dark": ("#282828", "#eeeeee", "#9fc5ff", "#b3d4ff", "#101010"),
    "black": ("#000000", "#eeeeee", "#9fc5ff", "#b3d4ff", "#101010"),
    "contrast-day": ("#ffffff", "#000000", "#003f87", "#004a99", "#ffffff"),
    "contrast-night": ("#000000", "#ffffff", "#9fc5ff", "#ffdf00", "#000000"),
}


def apply_direction(
    view: Gtk.TextView, reader: Reader, preferences: ReadingPreferences | None = None
) -> None:
    """Resource direction affects the content, not the application's controls."""
    view.set_direction(Gtk.TextDirection.RTL if reader.rtl else Gtk.TextDirection.LTR)
    view.set_justification(
        Gtk.Justification.FILL
        if preferences and preferences.alignment == "justified"
        else Gtk.Justification.RIGHT
        if reader.rtl
        else Gtk.Justification.LEFT
    )


def effective_palette(preferences: ReadingPreferences, dark: bool, high_contrast: bool) -> str:
    """Resolve content colors without changing the system interface appearance."""
    if high_contrast:
        return "contrast-night" if dark else "contrast-day"
    return preferences.night_palette if dark else preferences.day_palette


class ReadingStyle:
    """Apply owner-scoped reading palettes/content typography while GTK owns interface font inheritance."""

    def __init__(self, owner: Window) -> None:
        self.owner = owner
        self.initial_palette = self.palette_settings()
        self.views: WeakSet[Gtk.TextView] = WeakSet()
        self.manager = Adw.StyleManager.get_default()
        self.scope = "bible-content-" + str(id(owner))
        owner.add_css_class(self.scope + "-window")
        self.provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            owner.get_display(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.handlers = [
            self.manager.connect("notify::" + name, self.changed)
            for name in ["dark", "high-contrast"]
        ]
        self.apply_mode()

    def palette_settings(self) -> dict[str, str]:
        """Snapshot only the per-tab palette keys, leaving typography shared."""
        return {
            k: getattr(self.owner.preferences.value, k)
            for k in ("mode", "day_palette", "night_palette")
        }

    def remember_tab_palettes(self) -> None:
        """Initialize missing tab palettes without overwriting saved choices."""
        for tab in self.owner.tabs():
            if not tab.state.reading_palette:
                tab.state.reading_palette = self.palette_settings()

    def activate_tab(self, tab: ReadingTab) -> None:
        """Restore a tab palette and synchronize appearance controls on GTK."""
        for key, value in tab.state.reading_palette.items():
            setattr(self.owner.preferences.value, key, value)
        self.apply_mode()
        self.owner.appearance.sync()

    def apply_mode(self) -> None:
        """Resolve the saved reading/interface mode through libadwaita and refresh the effective palette."""
        mode = self.owner.preferences.value.mode
        if mode == "system":
            mode = {"light": "day", "dark": "night", "system": "system"}[
                self.owner.application_settings.value["interface_appearance"]
            ]
        self.dark = mode == "night" or (mode == "system" and self.manager.get_dark())
        self.manager.set_color_scheme(
            {
                "system": Adw.ColorScheme.DEFAULT,
                "day": Adw.ColorScheme.FORCE_LIGHT,
                "night": Adw.ColorScheme.FORCE_DARK,
            }[mode]
        )
        self.changed()

    def decorate(self, view: Gtk.TextView) -> None:
        """Register a reading view and apply content typography/number colors within its owner scope."""
        self.views.add(view)
        setattr(view, "_reading_palette", self.palette)
        from ..verse_typography import NUMBER_COLORS

        for name in ["verse-number", "page-number", "verse-editorial", "source-editorial"]:
            tag = view.get_buffer().get_tag_table().lookup(name)
            if tag:
                tag.props.foreground = NUMBER_COLORS[self.palette]
        view.add_css_class(self.scope)
        self.apply_text(view)

    def apply_text(self, view: Gtk.TextView, preserve: bool = True) -> None:
        # GtkTextMarks retain selection/body positions across tag-only reflow.
        """Apply reading text tags while retaining a native viewport mark through bounded reflow frames."""
        if preserve and view.get_mapped() and not getattr(view, "_reader_reflow_tick", 0):
            rect = view.get_visible_rect()
            _, iterator = view.get_iter_at_location(rect.x, rect.y)
            mark = view.get_buffer().create_mark(None, iterator, True)
            frames = [0]

            def restore(native_widget: Gtk.Widget, *_: object) -> bool:
                # GTK returns the same TextView registered below.
                widget = cast("Gtk.TextView", native_widget)
                frames[0] += 1
                if widget.get_mapped() and not self.owner.closed:
                    if frames[0] < 3:
                        return True
                    target = widget.get_iter_location(widget.get_buffer().get_iter_at_mark(mark))
                    visible = widget.get_visible_rect()
                    adjustment = cast("Gtk.ScrolledWindow", widget.get_parent()).get_vadjustment()
                    adjustment.set_value(adjustment.get_value() + target.y - visible.y)
                    if frames[0] < 5:
                        return True
                widget.get_buffer().delete_mark(mark)
                setattr(widget, "_reader_reflow_tick", 0)
                return False

            setattr(view, "_reader_reflow_tick", view.add_tick_callback(restore))
        preferences = self.owner.preferences.value
        view.set_pixels_inside_wrap(line_spacing(preferences))
        view.set_pixels_below_lines(line_spacing(preferences) + 4)
        buffer = view.get_buffer()
        tag = buffer.get_tag_table().lookup("reader-typography")
        if tag is None:
            tag = buffer.create_tag("reader-typography")
        tag.props.family = preferences.font
        tag.props.size_points = preferences.size
        buffer.apply_tag(tag, buffer.get_start_iter(), buffer.get_end_iter())
        from ..verse_typography import configure

        for name in ["verse-number", "page-number", "source-number"]:
            number = buffer.get_tag_table().lookup(name)
            if number:
                configure(number, view, preferences, self.palette)

    def changed(self, *_: object) -> None:
        """Refresh scoped palette CSS and content accents after mode/contrast changes.

        Reading/study prose may use explicit saved content families; interface
        labels retain native GTK family/size inheritance. This does not start
        periodic repaint or source-discovery work.
        """
        if hasattr(self.owner, "queue_layout"):
            self.owner.queue_layout()
        mode = self.owner.preferences.value.mode
        base = self.owner.application_settings.value["interface_appearance"]
        self.dark = (
            mode == "night"
            or mode == "system"
            and (base == "dark" or base == "system" and self.manager.get_dark())
        )
        self.palette = effective_palette(
            self.owner.preferences.value, self.dark, self.manager.get_high_contrast()
        )
        bg, fg, link, selection, selected = PALETTES[self.palette]
        selector = "textview." + self.scope
        focus_width = 3 if self.manager.get_high_contrast() else 2
        from ..verse_typography import NUMBER_COLORS

        marker_color = NUMBER_COLORS[self.palette]
        import json

        study_family = json.dumps(self.owner.preferences.value.study_font, ensure_ascii=False)
        study_size = self.owner.preferences.value.study_size
        study_size_css = f"font-size: {study_size}pt;" if study_size is not None else ""
        action_background = "#101010" if self.manager.get_high_contrast() else "rgba(12,12,14,.84)"
        from ..highlights import COLORS

        swatches = "".join(
            ".passage-actions .highlight-"
            + color
            + ", .highlight-swatch.highlight-"
            + color
            + " { background-color: "
            + rgb
            + "; color: #202020; border-radius: 999px; border: 1px solid rgba(255,255,255,.6); }"
            for color, (rgb, _) in COLORS.items()
        )
        study_accents = "".join(
            "."
            + self.scope
            + "-window .study-action-card.annotation-card.highlight-"
            + color
            + " { border-left: 3px solid "
            + rgb
            + "; }"
            for color, (rgb, _) in COLORS.items()
        )
        self.css = f"""
{swatches}
{study_accents}
.workspace-selector > button {{ padding: 4px 14px; min-height: 28px; font-weight: 500; }}
.workspace-selector.compact > button {{ padding-left: 8px; padding-right: 8px; min-width: 24px; }}
.resource-updates {{ color: @warning_color; background-color: alpha(@warning_bg_color,.14); border: 1px solid alpha(@warning_color,.3); }}
.resource-updates:hover {{ background-color: alpha(@warning_bg_color,.24); }}
/* Native edge glow can synchronously JIT-compile a radial-gradient program
   on software OpenGL during wheel reversal. Keep native scrolling without it. */
scrolledwindow.reading-scroll > overshoot {{ background: none; box-shadow: none; }}
button.reference-card {{ padding: 10px; margin-top: 4px; margin-bottom: 4px; }}
button.reference-card:hover {{ background-image: image(alpha(currentColor,.05)); }}
.{self.scope}-window .action-card {{ background-color: {bg}; color: {fg}; border: 1px solid alpha(currentColor,.14); border-radius: 10px; box-shadow: none; padding: 12px; }}
.{self.scope}-window .action-card:hover {{ background-color: mix({bg},{fg},.06); }}
.{self.scope}-window .action-card:focus-visible, .{self.scope}-window .action-card:focus-within {{ outline: 2px solid @accent_color; outline-offset: -2px; }}
.{self.scope}-window .action-card .card-primary {{ padding: 0; min-height: 0; background: transparent; box-shadow: none; }}
/* Study cards have one neutral surface; row wrappers and child buttons do
   not paint another hover layer or consume an extra horizontal inset. */
.study-card-list > row {{ padding: 0; margin: 0; background: none; box-shadow: none; }}
.study-card-list > row:hover, .study-card-list > row:selected {{ background: none; }}
.study-card-list > row:focus-visible {{ outline: none; }}
.annotation-list > row:focus-visible .study-action-card {{ outline: 2px solid @accent_color; outline-offset: -2px; }}
.{self.scope}-window .study-action-card:hover {{ background-color: {bg}; background-image: none; border-color: alpha(currentColor,.32); }}
.{self.scope}-window .annotation-list > row:selected .study-action-card {{ background-color: {bg}; background-image: none; border-color: alpha(currentColor,.45); }}
.{self.scope}-window .study-action-card:focus-within,
.study-card-list > row:focus-within > .study-action-card {{ outline: 2px solid @accent_color; outline-offset: -2px; }}
.{self.scope}-window button.study-action-card:active {{ background-color: {bg}; background-image: none; border-color: @accent_color; }}
.{self.scope}-window .study-action-card .card-primary:hover,
.{self.scope}-window .study-action-card .card-primary:active {{ background: transparent; box-shadow: none; }}
.{self.scope}-window .study-action-card .card-primary:focus-visible {{ outline: none; }}
.{self.scope}-window .note-scripture-context {{ background-color: mix({bg},{fg},.035); border-radius: 8px; padding: 12px; }}
.{self.scope}-surface {{ background-color: {bg}; color: {fg}; }}
textview.{self.scope} button.inline-marker {{ color: {marker_color}; min-width: 18px; min-height: 18px; padding: 0 1px; margin: 0 1px; border-radius: 4px; }}
textview.{self.scope} button.inline-marker image {{ -gtk-icon-size: 12px; }}
.passage-actions {{ border-radius: 16px; padding: 0; background-color: transparent; color: #ffffff; }}
.passage-actions button {{ color: #ffffff; background: transparent; box-shadow: none; }}
.passage-actions button:hover {{ background-color: rgba(255,255,255,.12); }}
.passage-actions button:active {{ background-color: rgba(255,255,255,.22); }}
.passage-actions button:focus-visible {{ outline: 2px solid #ffffff; outline-offset: -2px; }}
.source-note-popover contents, .source-note-popover arrow,
.{self.scope}-window tooltip, .{self.scope}-window tooltip label {{ background-color: #101010; color: #ffffff; }}
.source-note-popover label {{ color: #ffffff; }}
textview.{self.scope} button.source-note-marker {{ color: {marker_color}; min-width: 12px; min-height: 0; padding: 0; margin: 0; }}
.passage-actions popover contents, .passage-actions popover arrow {{ background-color: #202020; color: #ffffff; }}
.passage-actions-content {{ background-color: {action_background}; color: white; border-radius: 16px; padding: 16px; }}
.{self.scope}-window headerbar.immersive-header {{ background: transparent; color: {fg}; box-shadow: none; border: none; }}
.{self.scope}-window .highlight-swatch {{ border-radius: 50%; border: 1px solid currentColor; }}
.{self.scope}-window .highlight-color-action .highlight-swatch {{ border-color: transparent; }}
.highlight-color-action > button {{ min-width: 32px; min-height: 32px; padding: 0; }}
.references-pending:disabled, .references-pending button:disabled {{ opacity: 1; color: inherit; }}
.passage-actions button {{ min-width: 36px; min-height: 36px; padding: 0; }}
.passage-actions flowboxchild {{ padding: 0; background: none; }}
{selector}, {selector} text {{ background-color: {bg}; color: {fg}; }}
{selector} text selection {{ background-color: {selection}; color: {selected}; }}
{selector} text link {{ color: {link}; }}
{selector}.study-reader, {selector}.study-reader text {{ background-color: transparent; color: @view_fg_color; }}
.{self.scope}-window .study-content,
.{self.scope}-window .study-content text {{ font-family: {study_family}; {study_size_css} }}
/* Reference headings are interface labels. Only their weight is explicit;
   GTK/libadwaita owns their family and size, independently of study prose. */
.{self.scope}-window .passage-card-title {{ font-weight: 500; }}
/* GTK owns focus-visible/modality. Draw on the text CSS node so its opaque
   background cannot cover the focus mark. Inset shadows do not change layout. */
{selector}:not(.immersive-page):focus-visible text {{ box-shadow: inset {focus_width}px 0 0 {link}; }}
{selector}:not(.immersive-page):dir(rtl):focus-visible text {{ box-shadow: inset -{focus_width}px 0 0 {link}; }}
.{self.scope}-focus-cue {{ box-shadow: inset {focus_width}px 0 0 {link}; }}
.{self.scope}-focus-cue.rtl-reading {{ box-shadow: inset -{focus_width}px 0 0 {link}; }}
"""
        window = "." + self.scope + "-window"
        if not self.manager.get_high_contrast():
            sidebar = {
                "paper": "#e5dcc3",
                "black": "#121212",
                "white": "#f0f0f0",
                "dark": "#303030",
            }[self.palette]
            chrome = {
                "paper": "#eee4cb",
                "black": "#080808",
                "white": "#fafafa",
                "dark": "#242424",
            }[self.palette]
            # Scope native surfaces to this owner; leave tags, images and semantic
            # accents to their existing renderers. Transparent controls inherit.
            self.css += f"""
{window}, {window} .background:not(popover), {window} .view, {window} .card,
{window} popover contents, {window} dialog {{ background-color: {bg}; color: {fg}; }}
{window} headerbar, {window} tabbar, {window} tabbar tabbox {{ background-color: {chrome}; color: {fg}; }}
{window} .sidebar, {window} .sidebar-pane, {window} .study-panel, {window} .study-divider {{ background-color: {sidebar}; color: {fg}; }}
{window} .annotation-navigation {{ background-color: {sidebar}; color: {fg}; }}
{window} .annotation-sidebar, {window} .annotation-list {{ background-color: {chrome}; color: {fg}; }}
{window} .annotation-detail {{ background-color: {bg}; color: {fg}; }}
{window} textview.study-reader, {window} textview.study-reader text {{ color: {fg}; }}
{window} .study-drawer headerbar, {window} .study-drawer headerbar .title,
{window} .study-drawer headerbar .start, {window} .study-drawer headerbar .end {{ background-color: {sidebar}; color: {fg}; }}
{window} popover {{ background: transparent; }}
{window} popover > arrow {{ background-color: {bg}; }}
{window} popover.source-note-popover contents, {window} popover.source-note-popover arrow {{ background-color: #101010; color: white; }}
{window} .passage-actions {{ background-color: transparent; color: white; }}
{window} .passage-actions popover contents, {window} .passage-actions popover arrow {{ background-color: #202020; color: white; }}
"""
        # Override the owner-scoped reading background on the native tooltip
        # surface too, including its padding around the text.
        self.css += f"""
/* The reader keeps its distinct chrome. Secondary dialogs use one continuous
   native surface; the old owner-wide chrome rule must not repaint a gray band. */
{window}.bible-secondary-dialog headerbar,
{window} .bible-secondary-dialog headerbar {{ background: transparent; color: inherit; border: none; box-shadow: none; }}
.{self.scope}-window tooltip.background, .{self.scope}-window tooltip.background label {{ background-color: #101010; color: #ffffff; }}
"""
        for name, (background, foreground, *_remaining_colors) in PALETTES.items():
            if name.startswith("contrast"):
                continue
            self.css += f".{self.scope}-window .palette-preview-{name} {{ background-color: {background}; color: {foreground}; border-radius: 6px; padding: 6px 14px; border: 1px solid alpha(currentColor,.3); }}\n"
        self.provider.load_from_data(self.css.encode())
        from ..verse_typography import NUMBER_COLORS

        for view in self.views:
            setattr(view, "_reading_palette", self.palette)
            for name in [
                "verse-number",
                "page-number",
                "source-number",
                "verse-editorial",
                "source-editorial",
            ]:
                tag = view.get_buffer().get_tag_table().lookup(name)
                if tag:
                    tag.props.foreground = NUMBER_COLORS[self.palette]
        appearance = getattr(self.owner, "appearance", None)
        if appearance:
            appearance.sync_system()
        if hasattr(self.owner, "view") and hasattr(self.owner, "highlights"):
            self.owner.refresh_highlights()

    def close(self) -> None:
        """Disconnect native theme notifications and remove this window’s CSS."""
        for handler in self.handlers:
            self.manager.disconnect(handler)
        Gtk.StyleContext.remove_provider_for_display(self.owner.get_display(), self.provider)
