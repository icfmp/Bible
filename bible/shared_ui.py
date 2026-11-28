"""Native confirmation and passive text widgets shared across application surfaces."""

from gi.repository import Adw, Gtk

from .i18n import tr


class MetadataLabel(Gtk.Label):
    """Keep native selection/copy, without GtkLabel's focus-time Select All."""

    def do_grab_focus(self):
        result = Gtk.Label.do_grab_focus(self)
        self.select_region(0, 0)
        return result


def message(parent, heading, body, accepted, canceled=None):
    """Present an explicit destructive confirmation, defaulting cancellation and retaining owner styling."""
    dialog = Adw.MessageDialog.new(parent, tr(heading), tr(body))
    if hasattr(parent, "reading_style"):
        dialog.add_css_class(parent.reading_style.scope + "-window")
    dialog.add_response("cancel", tr("Cancel"))
    dialog.add_response("confirm", tr("Confirm"))
    dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_default_response("cancel")
    dialog.set_close_response("cancel")
    dialog.connect(
        "response",
        lambda _, response: accepted()
        if response == "confirm"
        else canceled()
        if canceled
        else None,
    )
    dialog.present()
    return dialog
