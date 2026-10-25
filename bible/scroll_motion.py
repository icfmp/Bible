"""Short, interruptible adjustment motion; never synthesizes user input."""
from gi.repository import Gtk


class ScrollMotion:
    def __init__(self, scroll):
        self.scroll = scroll
        self.tick = 0
        self.target = None
        scroll.connect('unmap', lambda *_: self.cancel())
        for controller, signal in (
                (Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES), 'scroll'),
                (Gtk.EventControllerKey(), 'key-pressed'),
                (Gtk.GestureClick(button=1), 'pressed')):
            controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            controller.connect(signal, lambda *_: self.cancel() or False)
            scroll.add_controller(controller)

    @property
    def running(self):
        return bool(self.tick)

    def cancel(self):
        if self.tick:
            self.scroll.remove_tick_callback(self.tick)
            self.tick = 0
        self.target = None

    def move(self, target, *, animate=True, valid=lambda: True):
        adjustment = self.scroll.get_vadjustment()
        target = max(adjustment.get_lower(), min(target, adjustment.get_upper() - adjustment.get_page_size()))
        if self.running and self.target == target:
            return
        self.cancel()
        start = adjustment.get_value()
        settings = self.scroll.get_settings()
        if (not animate or not settings.get_property('gtk-enable-animations')
                or not self.scroll.get_mapped() or abs(target - start) < 1
                or abs(target - start) > max(1, adjustment.get_page_size()) * 3):
            if valid():
                adjustment.set_value(target)
            return
        self.target = target
        geometry = (self.scroll.get_width(), self.scroll.get_height(), adjustment.get_upper())
        begun = None

        def frame(widget, clock):
            nonlocal begun
            if (not valid() or not widget.get_mapped()
                    or geometry != (widget.get_width(), widget.get_height(), adjustment.get_upper())):
                self.tick = 0; self.target = None
                return False
            now = clock.get_frame_time()
            if begun is None:
                begun = now
            progress = min(1, (now - begun) / 200000)
            adjustment.set_value(start + (target - start) * (1 - (1 - progress) ** 3))
            if progress >= 1:
                self.tick = 0; self.target = None
                return False
            return True

        self.tick = self.scroll.add_tick_callback(frame)
