"""One safe, local commentary view following the active reading tab."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango

from .i18n import tr
from .resource_details import details, plain
from .sword_provider import CommentaryReader, VersificationMismatch


class StudyPanel(Gtk.Box):
    def __init__(self, owner):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.owner = owner
        self.names = []
        self._syncing = False
        self._stamp = None
        self._readers = {}
        self._labels = []
        self.append(Gtk.Label(label=tr('Commentaries'), xalign=0,
                              margin_start=12, margin_top=12))
        self.choices = Gtk.DropDown(enable_search=True, margin_start=12, margin_end=12)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', lambda _, item: item.set_child(Gtk.Label(
            xalign=0, ellipsize=Pango.EllipsizeMode.END, width_chars=1, max_width_chars=32)))
        factory.connect('bind', lambda _, item: item.get_child().set_text(item.get_item().get_string()))
        self.choices.set_factory(factory)
        self.choices.set_list_factory(factory)
        self.choices.update_property([Gtk.AccessibleProperty.LABEL], [tr('Choose a commentary')])
        self.choices.connect('notify::selected', self.selection_changed)
        self.append(self.choices)
        self.passage = Gtk.Label(xalign=0, wrap=True, margin_start=12, margin_end=12)
        self.append(self.passage)
        self.source = Gtk.Label(xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR,
                                 margin_start=12, margin_end=12)
        self.append(self.source)
        self.info = Gtk.MenuButton(label=tr('Source and conditions'),
                                    margin_start=12, margin_end=12)
        popover = Gtk.Popover()
        self.metadata = Gtk.Label(xalign=0, yalign=0, wrap=True,
                                   wrap_mode=Pango.WrapMode.WORD_CHAR, selectable=True,
                                   max_width_chars=32, margin_start=12, margin_end=12,
                                   margin_top=12, margin_bottom=12)
        info_scroll = Gtk.ScrolledWindow(min_content_width=260, max_content_width=300,
                                         propagate_natural_width=True,
                                         max_content_height=350, propagate_natural_height=True,
                                         hscrollbar_policy=Gtk.PolicyType.NEVER)
        info_scroll.set_child(self.metadata)
        popover.set_child(info_scroll)
        self.info.set_popover(popover)
        self.append(self.info)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True,
                                 margin_start=12, margin_end=12)
        self.append(self.status)
        self.text = Gtk.TextView(editable=False, cursor_visible=False,
                                 wrap_mode=Gtk.WrapMode.WORD_CHAR, left_margin=12,
                                 right_margin=12, top_margin=8, bottom_margin=12)
        self.text.update_property([Gtk.AccessibleProperty.LABEL], [tr('Commentary text')])
        self.scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.scroll.set_child(self.text)
        self.append(self.scroll)
        hint = Gtk.Label(label=tr('Click a verse in the Bible to follow it here.'),
                          wrap=True, margin_start=12, margin_end=12)
        self.append(hint)
        download = Gtk.Button(label=tr('Download a commentary'), margin_start=12,
                              margin_end=12, margin_bottom=12)
        download.connect('clicked', lambda *_: owner.open_library('commentary'))
        self.append(download)

    def refresh(self, force=False):
        tab = self.owner.active_tab
        if tab is None:
            return
        installed = self.owner.library.installed('commentary')
        stamp = (id(tab), tab.state.commentary, tab.state.reference,
                 tab.state.resource, id(tab.reader), tuple(installed))
        if not force and stamp == self._stamp:
            return
        self._stamp = stamp
        self._syncing = True
        self.names = [None] + installed
        if tab.state.commentary and tab.state.commentary not in installed:
            self.names.append(tab.state.commentary)
        labels = [tr('Choose a commentary')]
        for name in self.names[1:]:
            if name in installed:
                resource = self.owner.library.resource(name)
                labels.append(f'{plain(resource.description)} ({name})')
            else:
                labels.append(f'{name} ({tr("Missing commentary")})')
        if labels != self._labels:
            self.choices.set_model(Gtk.StringList.new(labels))
            self._labels = labels
        self.choices.set_selected(self.names.index(tab.state.commentary))
        self._syncing = False
        self.render(tab, installed)

    def render(self, tab, installed):
        # Clear before every lookup, including failure, missing entry or resource.
        self.text.get_buffer().set_text('')
        self.scroll.get_vadjustment().set_value(0)
        self.source.set_text('')
        self.metadata.set_text('')
        self.info.set_sensitive(False)
        self.passage.set_text(tab.passage_title())
        name = tab.state.commentary
        if name is None:
            self.status.set_text(tr('Choose or download a commentary.'))
            return
        if name not in installed:
            self._readers.pop(name, None)
            self.status.set_text(tr('This commentary is no longer installed. Choose another or download it again.'))
            return
        try:
            resource = self.owner.library.resource(name)
            self.source.set_text(f'{plain(resource.description)} — {resource.source}')
            self.metadata.set_text(details(resource))
            self.info.set_sensitive(True)
            if tab.reader is None:
                self.status.set_text(tr('Open a Bible passage to read its commentary.'))
                return
            if name not in self._readers:
                self._readers[name] = CommentaryReader(self.owner.library.root / name, name)
            reader = self._readers[name]
            text = reader.entry(tab.state.reference, tab.reader.versification)
            if text is None:
                self.status.set_text(tr('No commentary for this passage.'))
            else:
                self.text.get_buffer().set_text(text)
                self.status.set_text('')
        except VersificationMismatch as error:
            self.status.set_text(tr('Different versifications. Automatic alignment is unavailable.') + f' ({error})')
        except Exception as error:
            self.status.set_text(tr('Unable to read this commentary.') + f' {error}')

    def selection_changed(self, *_):
        if self._syncing or self.owner.active_tab is None:
            return
        index = self.choices.get_selected()
        if index < len(self.names):
            self.owner.active_tab.state.commentary = self.names[index]
            self.refresh()
            self.owner.schedule_save()
