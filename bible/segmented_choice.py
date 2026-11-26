"""Direct, mutually exclusive native choices without a popup or hidden options."""

from __future__ import annotations

from collections.abc import Iterable
from gi.repository import Gtk, GObject


class SegmentedChoice(Gtk.Box):
    """Expose direct mutually exclusive native buttons and emit one logical changed signal per selection."""

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_LAST, None, ())}

    def __init__(self, labels: Iterable[str], selected: int = 0) -> None:
        super().__init__(spacing=0)
        self.add_css_class("linked")
        self.buttons: list[Gtk.ToggleButton] = []
        self._selected = selected
        self._syncing = False
        for index, label in enumerate(labels):
            button = Gtk.ToggleButton(label=label)
            if self.buttons:
                button.set_group(self.buttons[0])
            button.set_active(index == selected)
            button.connect("toggled", self._toggled, index)
            self.append(button)
            self.buttons.append(button)

    def get_selected(self) -> int:
        """Return the logical choice index, independent of individual toggle signals."""
        return self._selected

    def set_selected(self, index: int) -> None:
        if index == self._selected:
            return
        self._syncing = True
        self._selected = index
        self.buttons[index].set_active(True)
        self._syncing = False
        self.emit("changed")

    def _toggled(self, button: Gtk.ToggleButton, index: int) -> None:
        if self._syncing or not button.get_active():
            return
        if self._selected != index:
            self._selected = index
            self.emit("changed")
