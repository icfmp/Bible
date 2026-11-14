"""The Library's neutral placeholder shapes, without pretend resource content."""
from gi.repository import Gtk


def placeholder(area,cr,width,height):
    cr.set_source_rgba(.5,.5,.5,.25);cr.rectangle(0,0,width,height);cr.fill()


class LoadingCards(Gtk.Box):
    def __init__(self,label,count=3):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=14,
                         margin_start=12,margin_end=12,margin_top=12,margin_bottom=12,
                         accessible_role=Gtk.AccessibleRole.STATUS)
        self.update_property([Gtk.AccessibleProperty.LABEL],[label])
        self.set_can_target(False);self._tick=0
        for _ in range(count):
            card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,
                         accessible_role=Gtk.AccessibleRole.PRESENTATION)
            card.add_css_class('card')
            for width in (150,220):
                line=Gtk.DrawingArea(height_request=12,width_request=width,halign=Gtk.Align.START,
                                     margin_start=12,margin_end=12,margin_top=4,margin_bottom=4,
                                     accessible_role=Gtk.AccessibleRole.PRESENTATION)
                line.set_draw_func(placeholder);card.append(line)
            self.append(card)
        self.connect('map',self.animate);self.connect('unmap',self.stop)
        self.connect('notify::root',self.root_changed)
        self._settings=None;self._settings_handler=0

    def root_changed(self,*_):
        if self._settings_handler:self._settings.disconnect(self._settings_handler)
        self._settings_handler=0;self._settings=self.get_settings() if self.get_root() else None
        if self._settings:
            self._settings_handler=self._settings.connect('notify::gtk-enable-animations',self.animate)

    def animate(self,*_):
        self.stop()
        if not self.get_mapped() or not self.get_settings().get_property('gtk-enable-animations'):return
        def pulse(widget,clock):
            import math
            widget.set_opacity(.7+.25*math.sin(clock.get_frame_time()/1000000*3))
            return True
        self._tick=self.add_tick_callback(pulse)

    def stop(self,*_):
        if self._tick:self.remove_tick_callback(self._tick);self._tick=0
        self.set_opacity(1)
