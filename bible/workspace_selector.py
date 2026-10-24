"""The same real Bible/Notes space switch in each native application header."""
from gi.repository import Gtk
from .i18n import tr


class WorkspaceSelector(Gtk.DropDown):
    def __init__(self,owner,notes=False):
        super().__init__(model=Gtk.StringList.new([tr('Bible'),tr('Notes')]))
        self.owner=owner;self.syncing=False
        self.set_selected(1 if notes else 0)
        self.update_property([Gtk.AccessibleProperty.LABEL],[tr('Application space')])
        self.connect('notify::selected',self.changed)
        if hasattr(owner,'main_pages'):owner.main_pages.connect('notify::visible-child-name',lambda *_:self.sync())

    def sync(self):
        if not hasattr(self.owner,'main_pages'):return
        self.syncing=True
        self.set_selected(1 if self.owner.main_pages.get_visible_child_name()=='notes' else 0)
        self.syncing=False

    def changed(self,*_):
        if self.syncing:return
        if self.get_selected()==1:self.owner.open_notes()
        elif self.owner.notes_space:self.owner.notes_space.leave()
        else:self.owner.main_pages.set_visible_child_name('reading')
        self.sync()
