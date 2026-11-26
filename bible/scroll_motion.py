"""Short, interruptible adjustment motion; never synthesizes user input."""

from __future__ import annotations

from collections.abc import Callable
from gi.repository import Gtk, Gdk


def stop_native_scroll(scroll: Gtk.ScrolledWindow) -> None:
    """Cancel an old GTK deceleration without changing its kinetic setting."""
    # GtkScrolledWindow otherwise ignores external adjustment changes while
    # decelerating and can overwrite a new target with its old edge rebound.
    kinetic = scroll.get_kinetic_scrolling()
    scroll.set_kinetic_scrolling(not kinetic)
    scroll.set_kinetic_scrolling(kinetic)


class ScrollMotion:
    """Own one short cancellable native-adjustment movement, separate from actual user input."""

    def __init__(self, scroll: Gtk.ScrolledWindow) -> None:
        self.scroll = scroll
        self.tick = 0
        self.target: float | None = None
        scroll.connect("unmap", lambda *_: self.cancel())
        for controller, signal in (
            (Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES), "scroll"),
            (Gtk.EventControllerKey(), "key-pressed"),
            (Gtk.GestureClick(button=1), "pressed"),
        ):
            controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            controller.connect(signal, self.cancel_input)
            scroll.add_controller(controller)

    def cancel_input(self, *_: object) -> bool:
        """Cancel animation without consuming the user’s scroll, key or click event."""
        self.cancel()
        return False

    @property
    def running(self) -> bool:
        return bool(self.tick)

    def cancel(self) -> None:
        """Remove the frame callback without moving the adjustment to the old target."""
        if self.tick:
            self.scroll.remove_tick_callback(self.tick)
            self.tick = 0
        self.target = None

    def move(
        self, target: float, *, animate: bool = True, valid: Callable[[], bool] = lambda: True
    ) -> None:
        """Move within native adjustment bounds, respecting reduced motion and context/geometry validity.

        Long jumps, hidden widgets or disabled animations set the position directly.
        An active animation stops when its source validity or geometry changes.
        """
        adjustment = self.scroll.get_vadjustment()
        target = max(
            adjustment.get_lower(), min(target, adjustment.get_upper() - adjustment.get_page_size())
        )
        if self.running and self.target == target:
            return
        self.cancel()
        if not valid():
            return
        stop_native_scroll(self.scroll)
        start = adjustment.get_value()
        settings = self.scroll.get_settings()
        if (
            not animate
            or not settings.get_property("gtk-enable-animations")
            or not self.scroll.get_mapped()
            or abs(target - start) < 1
            or abs(target - start) > max(1, adjustment.get_page_size()) * 3
        ):
            if valid():
                adjustment.set_value(target)
            return
        self.target = target
        geometry = (self.scroll.get_width(), self.scroll.get_height(), adjustment.get_upper())
        begun: int | None = None

        def frame(widget: Gtk.Widget, clock: Gdk.FrameClock) -> bool:
            nonlocal begun
            if (
                not valid()
                or not widget.get_mapped()
                or geometry != (widget.get_width(), widget.get_height(), adjustment.get_upper())
            ):
                self.tick = 0
                self.target = None
                return False
            now = clock.get_frame_time()
            if begun is None:
                begun = now
            progress = min(1, (now - begun) / 200000)
            if not settings.get_property("gtk-enable-animations"):
                progress = 1
            adjustment.set_value(start + (target - start) * (1 - (1 - progress) ** 3))
            if progress >= 1:
                self.tick = 0
                self.target = None
                return False
            return True

        self.tick = self.scroll.add_tick_callback(frame)
