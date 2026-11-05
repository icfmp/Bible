"""One action: choose a second translation, or leave parallel reading."""
from gi.repository import Gtk


class ComparisonButton(Gtk.Button):
    def __init__(self,owner):
        super().__init__(icon_name='view-dual-symbolic')
        self.owner=owner;self.popover=None
        self.connect('clicked',lambda *_:self.popup())

    def set_popover(self,popover):
        self.popover=popover;popover.set_parent(self)

    def popup(self):
        if self.owner.active_tab and self.owner.active_tab.state.comparison:
            self.owner.end_comparison()
        else:self.popover.popup()

    def popdown(self):self.popover.popdown()
