"""The Library's neutral placeholder shapes, without pretend resource content."""

from gi.repository import Gtk


def placeholder(area, cr, width, height):
    cr.set_source_rgba(0.5, 0.5, 0.5, 0.25)
    cr.rectangle(0, 0, width, height)
    cr.fill()


class LoadingCards(Gtk.Box):
    def __init__(self, label, count=3):
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
        self._settings = None
        self._settings_handler = 0

    def root_changed(self, *_):
        if self._settings_handler:
            self._settings.disconnect(self._settings_handler)
        self._settings_handler = 0
        self._settings = self.get_settings() if self.get_root() else None
        if self._settings:
            self._settings_handler = self._settings.connect(
                "notify::gtk-enable-animations", self.animate
            )

    def animate(self, *_):
        self.stop()
        if not self.get_mapped() or not self.get_settings().get_property("gtk-enable-animations"):
            return

        def pulse(widget, clock):
            import math

            widget.set_opacity(0.7 + 0.25 * math.sin(clock.get_frame_time() / 1000000 * 3))
            return True

        self._tick = self.add_tick_callback(pulse)

    def stop(self, *_):
        if self._tick:
            self.remove_tick_callback(self._tick)
            self._tick = 0
        self.set_opacity(1)
