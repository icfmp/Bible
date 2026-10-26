"""Native GTK divider for the existing animated/adaptive Adwaita drawer."""
from gi.repository import Adw, Gdk, Gtk
from .i18n import tr


class StudyDivider(Gtk.Box):
    def __init__(self, owner, settings):
        super().__init__(width_request=8, focusable=True, hexpand=False)
        self.owner, self.settings = owner, settings
        self.active = False
        self.add_css_class('study-divider')
        self.set_cursor_from_name('col-resize')
        self.set_tooltip_text(tr('Resize study panel: drag or use Left/Right arrow keys'))
        self.update_property([Gtk.AccessibleProperty.LABEL], [tr('Resize study panel')])
        self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL, vexpand=True))
        drag = Gtk.GestureDrag(button=1)
        drag.connect('drag-begin', self.begin)
        drag.connect('drag-update', self.update)
        drag.connect('drag-end', self.end)
        drag.connect('cancel', self.end)
        self.add_controller(drag)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self.key)
        self.add_controller(keys)
        owner.split.set_sidebar_width_unit(Adw.LengthUnit.PX)
        owner.split.connect('notify::collapsed', lambda *_: self.apply())
        owner.split.connect('notify::show-sidebar', self.sidebar_changed)
        self.geometry = None
        self._adapt_id=0;self._adapt_frames=0

    def queue_adapt(self,*_):
        if not self.owner.get_mapped():return
        self._adapt_frames=3
        if not self._adapt_id:self._adapt_id=self.owner.add_tick_callback(self._settle_layout)

    def cancel_adapt(self,*_):
        if self._adapt_id:self.owner.remove_tick_callback(self._adapt_id)
        self._adapt_id=0;self._adapt_frames=0

    def _settle_layout(self,*_):
        self.adapt();self._adapt_frames-=1
        if self._adapt_frames>0:return True
        self._adapt_id=0
        return False

    def adapt(self, *_):
        geometry = (self.owner.get_width(), self.owner.split.get_collapsed())
        if geometry != self.geometry:
            self.geometry = geometry
            self.apply()
        return not self.owner.closed

    def effective(self, requested=None):
        width = self.owner.get_width() or self.owner.get_default_size()[0]
        return max(320, min(requested or self.settings.width, max(320, width-480)))

    def apply(self):
        split = self.owner.split
        collapsed = split.get_collapsed()
        self.set_visible(not collapsed)
        if collapsed:
            minimum, maximum = 280, max(280, min(560, self.owner.get_width()))
        else:
            minimum = maximum = self.effective()
        # Keep the two property bounds valid while updating either direction.
        if minimum > split.get_max_sidebar_width():split.set_max_sidebar_width(maximum)
        split.set_min_sidebar_width(minimum)
        split.set_max_sidebar_width(maximum)
        split.set_sidebar_width_fraction(1.0 if collapsed else .5)

    def begin(self, gesture=None, *_):
        self.active = True
        self.origin = self.owner.split.get_sidebar().get_width()
        self.pointer_origin = None
        if gesture:
            event = gesture.get_current_event()
            if event:self.pointer_origin = (event.get_surface(), event.get_position()[-2])
        self.owner._study_resizing = True
        coordinator = self.owner.reading_sync
        coordinator.driver = None; coordinator.needs_sync = False
        coordinator.forced_position = None; coordinator.armed_until = 0
        tab = self.owner.active_tab
        self.bible_anchor = None
        if tab and tab.reader:
            rect = tab.text.get_visible_rect()
            _, iterator = tab.text.get_iter_at_location(rect.x, rect.y)
            self.bible_anchor = tab.position_anchor(iterator.get_offset())
            tab.comparison_sync.driver = None
        self.commentary_anchor = self.owner.study.anchor()

    def update(self, gesture, x, y):
        if not self.active:return
        # The divider moves as the right sidebar grows. Gesture offsets in
        # its changing local coordinates would halve the pointer movement.
        # Native surface coordinates remain stable on both Wayland and X11.
        if gesture and self.pointer_origin:
            event = gesture.get_current_event()
            if event and event.get_surface() == self.pointer_origin[0]:
                x = event.get_position()[-2] - self.pointer_origin[1]
        requested = max(280, min(2000, round(self.origin-x)))
        self.settings.width = self.effective(requested)
        self.apply()

    def end(self, *_):
        if not self.active:return
        self.active = False
        self.owner._study_resizing = False
        tab = self.owner.active_tab
        if tab and self.bible_anchor:
            tab._appearance_anchor = self.bible_anchor
            tab._jump_reference = None; tab.schedule_scroll_restore()
        if self.commentary_anchor:self.owner.study.reveal(*self.commentary_anchor, force=True)
        self.save()

    def sidebar_changed(self, *_):
        # Adwaita may clip a closed sidebar while retaining mapped children.
        # Finish a held divider gesture even when GTK does not unmap it.
        if not self.owner.split.get_show_sidebar():self.end()

    def key(self, _, key, code, state):
        if key not in (Gdk.KEY_Left, Gdk.KEY_Right, Gdk.KEY_Home):return False
        self.begin()
        target = 420 if key == Gdk.KEY_Home else self.origin+(32 if key == Gdk.KEY_Left else -32)
        self.update(None, self.origin-target, 0)
        self.end()
        return True

    def save(self):
        try:self.settings.save()
        except (OSError, ValueError) as error:
            self.owner.report_session_error(tr('Unable to save study preferences.'), error)
