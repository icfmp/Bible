"""One action: choose a second translation, or leave parallel reading."""

from __future__ import annotations

from gi.repository import Gtk


class ComparisonButton(Gtk.Button):
    """Choose a second translation in simple reading or exit parallel reading directly."""

    def __init__(self, owner) -> None:
        super().__init__(icon_name="view-dual-symbolic")
        self.owner = owner
        self.popover = None
        self.connect("clicked", lambda *_: self.popup())

    def set_popover(self, popover) -> None:
        self.popover = popover
        popover.set_parent(self)

    def popup(self) -> None:
        if self.owner.active_tab and self.owner.active_tab.state.comparison:
            self.owner.end_comparison()
        else:
            self.popover.popup()

    def popdown(self) -> None:
        self.popover.popdown()
