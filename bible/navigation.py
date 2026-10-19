"""Staged passage selector anchored to the active tab's Header Bar title."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango

from .book_names import display_name
from .i18n import LANGUAGE, tr
from .sword_provider import Reader


class PassagePopover(Gtk.Popover):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.reader = None
        self._updating = False
        self._stamp = None
        self.names = []
        self.books = ()
        self.chapters = []
        self.verses = []
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                          margin_start=12, margin_end=12, margin_top=12, margin_bottom=12)
        self.version = self.dropdown(content, 'Version', self.version_changed)
        self.book = self.dropdown(content, 'Book', self.book_changed)
        self.chapter = self.dropdown(content, 'Chapter', self.chapter_changed)
        self.verse = self.dropdown(content, 'Verse', self.verse_changed)
        self.direct_expander = Gtk.Expander(label=tr('Direct reference'))
        self.direct = Gtk.Entry(placeholder_text=tr('Reference (e.g. John 1:1)'))
        self.direct.update_property([Gtk.AccessibleProperty.LABEL], [tr('Direct reference')])
        self.direct.connect('activate', lambda *_: self.commit(False))
        self.direct_expander.set_child(self.direct)
        content.append(self.direct_expander)
        self.status = Gtk.Label(wrap=True, xalign=0, visible=False, max_width_chars=32)
        content.append(self.status)
        self.open_button = Gtk.Button(label=tr('Open in this tab'))
        self.open_button.add_css_class('suggested-action')
        self.open_button.connect('clicked', lambda *_: self.commit(False))
        content.append(self.open_button)
        self.new_button = Gtk.Button(label=tr('Open passage in new tab'))
        self.new_button.connect('clicked', lambda *_: self.commit(True))
        content.append(self.new_button)
        download = Gtk.Button(label=tr('Download a translation'))
        download.connect('clicked', self.open_library)
        content.append(download)
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                    min_content_width=280, max_content_height=500,
                                    propagate_natural_height=True)
        scroll.set_child(content)
        self.set_child(scroll)
        self.connect('notify::visible', self.visibility_changed)

    def dropdown(self, parent, label, callback):
        parent.append(Gtk.Label(label=tr(label), xalign=0))
        dropdown = Gtk.DropDown(enable_search=True, hexpand=True)
        dropdown.update_property([Gtk.AccessibleProperty.LABEL], [tr(label)])
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', lambda _, item: item.set_child(Gtk.Label(
            xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=26)))
        factory.connect('bind', lambda _, item: item.get_child().set_text(item.get_item().get_string()))
        dropdown.set_factory(factory)
        dropdown.set_list_factory(factory)
        dropdown.connect('notify::selected', callback)
        parent.append(dropdown)
        return dropdown

    def visibility_changed(self, *_):
        if self.get_visible():
            self.sync(force=True)

    def sync(self, force=False):
        tab = self.owner.active_tab
        if tab is None:
            return
        installed = self.owner.library.installed()
        stamp = (id(tab), tab.state.resource, tab.state.reference, tuple(installed))
        if not force and stamp == self._stamp:
            return
        self._stamp = stamp
        self._updating = True
        self.names = installed[:]
        if tab.state.resource and tab.state.resource not in installed:
            self.names.insert(0, tab.state.resource)
        labels = [name if name in installed else f'{name} ({tr("Missing translation")})'
                  for name in self.names]
        self.version.set_model(Gtk.StringList.new(labels))
        self.version.set_sensitive(bool(self.names))
        index = self.names.index(tab.state.resource) if tab.state.resource in self.names else 0
        self.version.set_selected(index)
        self._updating = False
        self.load_version(tab.state.reference)

    def message(self, text=''):
        self.status.set_text(text)
        self.status.set_visible(bool(text))

    def selected_resource(self):
        index = self.version.get_selected()
        return self.names[index] if index < len(self.names) else None

    def load_version(self, reference):
        self._updating = True
        self.reader = None
        self.books = ()
        try:
            name = self.selected_resource()
            if name in self.owner.library.installed():
                tab = self.owner.active_tab
                self.reader = tab.reader if tab and tab.state.resource == name and tab.reader else Reader(
                    self.owner.library.root / name, name)
                self.books = self.reader.books
                self.message('' if self.books else tr('No readable passage in this translation.'))
            else:
                self.message(tr('Choose a translation') if not name else tr('Missing translation'))
        except Exception as error:
            self.message(f'{tr("Unable to read this passage.")} {error}')
        self.book.set_model(Gtk.StringList.new([
            display_name(book.code, book.name, LANGUAGE) for book in self.books]))
        self.book.set_sensitive(bool(self.books))
        code, chapter, verse = self.reference_parts(reference)
        codes = [book.code for book in self.books]
        self.book.set_selected(codes.index(code) if code in codes else 0)
        self.populate_chapters(chapter, verse)
        self._updating = False
        self.update_direct()
        enabled = bool(self.books)
        self.open_button.set_sensitive(enabled)
        self.new_button.set_sensitive(enabled)
        self.direct.set_sensitive(enabled)

    def reference_parts(self, reference):
        try:
            if self.reader:
                reference = self.reader.key(reference).getOSISRef()
            code, chapter, verse = reference.split('.')
            return code, int(chapter), int(verse)
        except (ValueError, AttributeError):
            return '', 1, 1

    def populate_chapters(self, preferred=1, verse=1):
        index = self.book.get_selected()
        self.chapters = list(self.books[index].chapters) if index < len(self.books) else []
        self.chapter.set_model(Gtk.StringList.new([str(number) for number in self.chapters]))
        self.chapter.set_sensitive(bool(self.chapters))
        self.chapter.set_selected(self.chapters.index(preferred) if preferred in self.chapters else 0)
        self.populate_verses(verse)

    def populate_verses(self, preferred=1):
        book, chapter = self.book.get_selected(), self.chapter.get_selected()
        self.verses = list(self.books[book].chapters[self.chapters[chapter]]) if (
            book < len(self.books) and chapter < len(self.chapters)) else []
        self.verse.set_model(Gtk.StringList.new([str(number) for number in self.verses]))
        self.verse.set_sensitive(bool(self.verses))
        self.verse.set_selected(self.verses.index(preferred) if preferred in self.verses else 0)

    def selected_reference(self):
        book, chapter, verse = self.book.get_selected(), self.chapter.get_selected(), self.verse.get_selected()
        if book < len(self.books) and chapter < len(self.chapters) and verse < len(self.verses):
            return f'{self.books[book].code}.{self.chapters[chapter]}.{self.verses[verse]}'
        return ''

    def update_direct(self):
        self.direct.set_text(self.selected_reference())

    def version_changed(self, *_):
        if not self._updating:
            previous = self.selected_reference()
            self.load_version(previous)

    def book_changed(self, *_):
        if not self._updating:
            self._updating = True
            self.populate_chapters()
            self._updating = False
            self.update_direct()
            self.message()

    def chapter_changed(self, *_):
        if not self._updating:
            self._updating = True
            self.populate_verses()
            self._updating = False
            self.update_direct()
            self.message()

    def verse_changed(self, *_):
        if not self._updating:
            self.update_direct()
            self.message()

    def commit(self, new_tab):
        try:
            reference = self.direct.get_text() if self.direct_expander.get_expanded() else self.selected_reference()
            if not self.reader or not self.reader.has_reference(reference):
                raise ValueError(tr('This passage is not available in this translation.'))
            reference = self.reader.key(reference).getOSISRef()
            if self.owner.navigate_selection(self.selected_resource(), reference, new_tab):
                self.popdown()
        except Exception as error:
            self.message(f'{tr("Unable to read this passage.")} {error}')

    def open_library(self, *_):
        self.popdown()
        self.owner.open_library()
