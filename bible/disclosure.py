"""Native expandable details with focus-local keyboard activation."""
from gi.repository import Gdk,Gtk


def activate_focused(widget,arguments):
    # Do not consume Enter/Space from links or controls inside expanded content.
    return widget.activate() if widget.has_focus() else False


def disclosure(**kwargs):
    widget=Gtk.Expander(**kwargs)
    shortcuts=Gtk.ShortcutController(propagation_phase=Gtk.PropagationPhase.CAPTURE)
    for key in (Gdk.KEY_space,Gdk.KEY_Return,Gdk.KEY_KP_Enter):
        shortcuts.add_shortcut(Gtk.Shortcut(trigger=Gtk.KeyvalTrigger.new(key,0),action=Gtk.CallbackAction.new(activate_focused)))
    widget.add_controller(shortcuts)
    return widget
