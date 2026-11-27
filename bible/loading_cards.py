"""The Library's neutral placeholder shapes, without pretend resource content."""

from __future__ import annotations

from typing import Protocol
from gi.repository import Gtk, Gdk


class _DrawingContext(Protocol):
    """Only the existing Cairo operations needed by the neutral loading bars."""

    def set_source_rgba(self, red: float, green: float, blue: float, alpha: float) -> None: ...
    def rectangle(self, x: float, y: float, width: float, height: float) -> None: ...
    def fill(self) -> None: ...


def placeholder(area: object, cr: _DrawingContext, width: int, height: int) -> None:
    cr.set_source_rgba(0.5, 0.5, 0.5, 0.25)
    cr.rectangle(0, 0, width, height)
    cr.fill()


class LoadingCards(Gtk.Box):
    """Show neutral accessible loading shapes, animating only while mapped and animations are enabled."""

    def __init__(self, label: str, count: int = 3) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=12,
            accessible_role=Gtk.AccessibleRole.STATUS,
        )
        self.update_property([Gtk.AccessibleProperty.LABEL], [label])
        self.set_can_target(False)
        self._tick = 0
        for _ in range(count):
            card = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=8,
                accessible_role=Gtk.AccessibleRole.PRESENTATION,
            )
            card.add_css_class("card")
            # Inset the *whole* skeleton content, like real passage cards.
            # A single inner box keeps bars aligned without stacked margins.
            content = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=8,
                margin_start=16,
                margin_end=16,
                margin_top=12,
                margin_bottom=12,
            )
            for width in (112, 164):
                line = Gtk.DrawingArea(
                    height_request=12,
                    width_request=width,
                    halign=Gtk.Align.START,
                    accessible_role=Gtk.AccessibleRole.PRESENTATION,
                )
                line.set_draw_func(placeholder)
                content.append(line)
            card.append(content)
            self.append(card)
        self.connect("map", self.animate)
        self.connect("unmap", self.stop)
        self.connect("notify::root", self.root_changed)
        self._settings: Gtk.Settings | None = None
        self._settings_handler = 0

    def root_changed(self, *_: object) -> None:
        """Reconnect animation settings to the current root without retaining the old settings handler."""
        if self._settings_handler and self._settings is not None:
            self._settings.disconnect(self._settings_handler)
        self._settings_handler = 0
        self._settings = self.get_settings() if self.get_root() else None
        if self._settings:
            self._settings_handler = self._settings.connect(
                "notify::gtk-enable-animations", self.animate
            )

    def animate(self, *_: object) -> None:
        """Replace the pulse callback only when mapped and native animation settings permit it."""
        self.stop()
        if not self.get_mapped() or not self.get_settings().get_property("gtk-enable-animations"):
            return

        def pulse(widget: Gtk.Widget, clock: Gdk.FrameClock) -> bool:
            import math

            widget.set_opacity(0.7 + 0.25 * math.sin(clock.get_frame_time() / 1000000 * 3))
            return True

        self._tick = self.add_tick_callback(pulse)

    def stop(self, *_: object) -> None:
        """Remove the frame callback and restore full opacity when loading is hidden or animations stop."""
        if self._tick:
            self.remove_tick_callback(self._tick)
            self._tick = 0
        self.set_opacity(1)
