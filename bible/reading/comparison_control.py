"""One action: choose a second translation, or leave parallel reading."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ui import Window

from gi.repository import Gtk


class ComparisonButton(Gtk.Button):
    """Choose a second translation in simple reading or exit parallel reading directly."""

    def __init__(self, owner: Window) -> None:
        super().__init__(icon_name="view-dual-symbolic")
        self.owner = owner
        self.popover: Gtk.Popover | None = None
        self.connect("clicked", lambda *_: self.popup())

    def set_popover(self, popover: Gtk.Popover) -> None:
        self.popover = popover
        popover.set_parent(self)

    def popup(self) -> None:
        """Leave active comparison directly, otherwise open the configured chooser."""
        if self.owner.active_tab and self.owner.active_tab.state.comparison:
            self.owner.end_comparison()
        elif self.popover is not None:
            self.popover.popup()

    def popdown(self) -> None:
        if self.popover is not None:
            self.popover.popdown()
