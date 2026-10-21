"""Reading popup lifetime without a parent modal grab surviving nested choices.

Nested native dropdowns keep their own grabs. The reading popup itself uses
parent-surface dismissal, so selecting a nested item cannot strand its grab.
"""
from gi.repository import Gdk, Gtk


def install(owner, popovers):
    for popover in popovers:
        popover.set_autohide(False)

    def close():
        opened = [p for p in popovers if p.get_visible()]
        for popover in opened:popover.popdown()
        return bool(opened)

    gesture = Gtk.GestureClick(button=1)
    gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

    def pressed(controller, count, x, y):
        event = controller.get_current_event()
        # Coordinates on a nested native popup are not window coordinates.
        if not event or event.get_surface() != owner.get_surface():
            return
        opened = [popover for popover in popovers if popover.get_visible()]
        if not opened:
            return
        target = owner.pick(x, y, Gtk.PickFlags.DEFAULT)
        if target and any(target is p or target.is_ancestor(p) for p in opened):
            return
        for popover in opened:
            popover.popdown()
        # Do not reopen a trigger or select a verse from the dismissal click.
        controller.set_state(Gtk.EventSequenceState.CLAIMED)

    gesture.connect('pressed', pressed)
    owner.add_controller(gesture)
    keys = Gtk.EventControllerKey()
    keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
    def key(controller, value, *_):
        if value != Gdk.KEY_Escape:return False
        event = controller.get_current_event()
        surfaces = [owner.get_surface()] + [p.get_surface() for p in popovers if p.get_visible()]
        # Let an inner dropdown process Escape before the outer reading popup.
        return close() if event and event.get_surface() in surfaces else False
    keys.connect('key-pressed', key)
    owner.add_controller(keys)
    return gesture
