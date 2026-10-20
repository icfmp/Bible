"""Immediate passage selector: searchable books beside a chapter grid."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gdk, GLib, Gtk, Pango

from .book_names import display_name, normalized
from .providers import module_name
from .i18n import LANGUAGE, tr
from .sword_provider import Reader


class PassagePopover(Gtk.Popover):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.add_css_class('passage-selector')
        self._reveal_id = 0
        self.reader = None
        self._updating = False
        self._stamp = None
        self._layout_stamp = None
        self._resize_id = 0
        self.names, self.chapters, self.verses = [], [], []
        self.books = ()
        self.book_index, self.chapter_number = 0, None
        self.book_rows, self.chapter_buttons = {}, {}
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        top = Gtk.Box(spacing=8)
        top.append(Gtk.Label(label=tr('Version')))
        self.version = self.dropdown('Version', self.version_changed)
        top.append(self.version)
        self.download_button=Gtk.Button(icon_name='folder-download-symbolic',tooltip_text=tr('Download a translation'))
        self.download_button.add_css_class('flat')
        self.download_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Download a translation')])
        self.download_button.connect('clicked',self.open_library)
        top.append(self.download_button)
        self.close_button = Gtk.Button(icon_name='window-close-symbolic', tooltip_text=tr('Close'))
        self.close_button.add_css_class('flat')
        self.close_button.update_property([Gtk.AccessibleProperty.LABEL], [tr('Close')])
        self.close_button.connect('clicked', lambda *_: self.popdown())
        top.append(self.close_button)
        self.content.append(top)
        self.columns = Gtk.Box(spacing=16)
        self.left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.left.add_css_class('navigation-books')
        self.search = Gtk.SearchEntry(placeholder_text=tr('Search books'))
        self.search.update_property([Gtk.AccessibleProperty.LABEL], [tr('Search books')])
        self.search.connect('search-changed', self.filter_books)
        self.left.append(self.search)
        self.book_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE,
                                     activate_on_single_click=True)
        self.book_list.add_css_class('navigation-sidebar')
        self.book_list.connect('row-activated', self.book_changed)
        book_keys = Gtk.EventControllerKey()
        book_keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        book_keys.connect('key-released', self.book_key_released)
        self.book_list.add_controller(book_keys)
        self.book_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                              vexpand=True, propagate_natural_height=True)
        self.book_scroll.set_child(self.book_list)
        self.left.append(self.book_scroll)
        self.no_books = Gtk.Label(label=tr('No matching book.'), wrap=True, visible=False)
        self.left.append(self.no_books)
        self.columns.append(self.left)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, hexpand=True)
        self.book_title = Gtk.Label(xalign=0, wrap=True, max_width_chars=22)
        self.book_title.add_css_class('title-1')
        right.append(self.book_title)
        self.chapter_grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                                         min_children_per_line=2, max_children_per_line=5,
                                         column_spacing=8, row_spacing=8,
                                         homogeneous=True, valign=Gtk.Align.START)
        self.chapter_grid.update_property([Gtk.AccessibleProperty.LABEL], [tr('Chapters')])
        self.chapter_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                                 min_content_height=120, max_content_height=300,
                                                 propagate_natural_height=True, vexpand=True)
        self.chapter_scroll.set_child(self.chapter_grid)
        right.append(self.chapter_scroll)
        verse_expander = Gtk.Expander(label=tr('Verse'))
        self.verse = self.dropdown('Verse', self.verse_changed)
        verse_expander.set_child(self.verse)
        right.append(verse_expander)
        self.columns.append(right)
        self.pages=Gtk.Stack()
        books_page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        books_page.append(self.columns)
        self.pages.add_titled(books_page,'books',tr('Books'))
        self.history_list=Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        history_scroll=Gtk.ScrolledWindow(min_content_height=220,max_content_height=380,propagate_natural_height=True)
        history_scroll.set_child(self.history_list)
        self.pages.add_titled(history_scroll,'history',tr('History'))
        switcher=Gtk.StackSwitcher(stack=self.pages,halign=Gtk.Align.CENTER)
        self.content.append(switcher)
        self.content.append(self.pages)
        self.direct_expander = Gtk.Expander(label=tr('Direct reference'))
        self.direct = Gtk.Entry(placeholder_text=tr('Reference (e.g. John 1:1)'),
                                width_chars=12, max_width_chars=24)
        self.direct.update_property([Gtk.AccessibleProperty.LABEL], [tr('Direct reference')])
        self.direct.connect('activate', lambda *_: self.commit())
        self.direct_expander.set_child(self.direct)
        self.content.append(self.direct_expander)
        self.status = Gtk.Label(wrap=True, xalign=0, visible=False, max_width_chars=32)
        self.content.append(self.status)
        self.scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                         propagate_natural_width=True,
                                         propagate_natural_height=True)
        self.scroll.set_child(self.content)
        self.set_child(self.scroll)
        self.connect('notify::visible', self.visibility_changed)

    def dropdown(self, label, callback):
        dropdown = Gtk.DropDown(enable_search=True, hexpand=True)
        dropdown.update_property([Gtk.AccessibleProperty.LABEL], [tr(label)])
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', lambda _, item: item.set_child(Gtk.Label(
            xalign=0, ellipsize=Pango.EllipsizeMode.END, width_chars=1, max_width_chars=26)))
        factory.connect('bind', lambda _, item: item.get_child().set_text(item.get_item().get_string()))
        dropdown.set_factory(factory)
        dropdown.set_list_factory(factory)
        dropdown.connect('notify::selected', callback)
        return dropdown

    def refresh_history(self):
        child=self.history_list.get_first_child()
        while child:
            next_child=child.get_next_sibling();self.history_list.remove(child);child=next_child
        tab=self.owner.active_tab
        if not tab:return
        from .notes_window import passage_label
        if not tab.state.history:
            self.history_list.append(Gtk.Label(label=tr('No passage history yet.'),margin_top=16,margin_bottom=16))
        for index in range(len(tab.state.history)-1,-1,-1):
            entry=tab.state.history[index]
            label=passage_label(entry['reference'])+' — '+module_name(entry['resource'])
            button=Gtk.Button(label=label,halign=Gtk.Align.FILL)
            button.add_css_class('flat')
            button.connect('clicked',lambda *_,i=index:self.open_history(i))
            self.history_list.append(button)

    def open_history(self,index):
        if self.owner.active_tab.travel(index):self.sync(force=True)
        self.refresh_history()

    def visibility_changed(self, *_):
        if self.get_visible():
            self.pages.set_visible_child_name('books')
            self.refresh_history()
            self.search.set_text('')
            self.sync(force=True)
            self.adapt()
            if not self._resize_id:
                self._resize_id = GLib.timeout_add(150, self.adapt)
        elif self._resize_id:
            GLib.source_remove(self._resize_id)
            self._resize_id = 0

    def adapt(self):
        if not self.get_visible():
            self._resize_id = 0
            return False
        size = (self.owner.get_width(), self.owner.get_height())
        if size != self._layout_stamp:
            self._layout_stamp = size
            narrow = size[0] < 600
            self.columns.set_orientation(Gtk.Orientation.VERTICAL if narrow else Gtk.Orientation.HORIZONTAL)
            self.left.set_size_request(-1 if narrow else 210, -1)
            self.book_scroll.set_max_content_height(-1)
            self.book_scroll.set_min_content_height(100 if narrow else 260)
            self.book_scroll.set_max_content_height(120 if narrow else 300)
            self.content.set_size_request(min(680, max(280, size[0] - 64)), -1)
            self.scroll.set_max_content_height(min(540, max(160, size[1] - 140)))
        return True

    def sync(self, force=False):
        tab = self.owner.active_tab
        if tab is None or self._updating:
            return
        installed = self.owner.library.installed('bible')
        stamp = (id(tab), tab.state.resource, tab.state.reference, tuple(installed))
        if not force and stamp == self._stamp:
            return
        self._stamp = stamp
        self._updating = True
        self.names = installed[:]
        if tab.state.resource and tab.state.resource not in installed:
            self.names.insert(0, tab.state.resource)
        self.version.set_model(Gtk.StringList.new([
            name if name in installed else f'{name} ({tr("Missing translation")})' for name in self.names]))
        self.version.set_sensitive(bool(self.names))
        self.version.set_selected(self.names.index(tab.state.resource) if tab.state.resource in self.names else 0)
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
        self.reader, self.books = None, ()
        try:
            name = self.selected_resource()
            if name in self.owner.library.installed('bible'):
                tab = self.owner.active_tab
                self.reader = tab.reader if tab and tab.state.resource == name and tab.reader else Reader(
                    self.owner.library.root / name, name)
                self.books = self.reader.books
                self.message('' if self.books else tr('No readable passage in this translation.'))
            else:
                self.message(tr('Choose a translation') if not name else tr('Missing translation'))
        except Exception as error:
            self.message(f'{tr("Unable to read this passage.")} {error}')
        try:
            canonical = self.reader.key(reference).getOSISRef() if self.reader else reference
            code, chapter, verse = canonical.split('.')
            chapter, verse = int(chapter), int(verse)
        except (ValueError, AttributeError):
            code, chapter, verse = '', 1, 1
        codes = [book.code for book in self.books]
        self.book_index = codes.index(code) if code in codes else 0
        self.filter_books()
        self.populate_chapters(chapter, verse)
        self._updating = False
        self.update_direct()
        self.direct.set_sensitive(bool(self.books))

    def book_name(self, book):
        return display_name(book.code, book.name, LANGUAGE)

    def filter_books(self, *_):
        previous, self._updating = self._updating, True
        while row := self.book_list.get_first_child():
            self.book_list.remove(row)
        self.book_rows = {}
        query = normalized(self.search.get_text())
        testament = None
        for index, book in enumerate(self.books):
            if query not in normalized(f'{self.book_name(book)} {book.name} {book.code}'):
                continue
            chapter = next(iter(book.chapters))
            current = self.reader.key(f'{book.code}.{chapter}.{book.chapters[chapter][0]}').getTestament()
            current = ord(current) if isinstance(current, str) else int(current)
            if current != testament:
                heading = Gtk.Label(label=tr('Old Testament' if current == 1 else 'New Testament'),
                                    xalign=0, margin_top=8, margin_bottom=4, wrap=True)
                heading.add_css_class('heading')
                row = Gtk.ListBoxRow(selectable=False, activatable=False, focusable=False, child=heading)
                self.book_list.append(row)
                testament = current
            label = Gtk.Label(label=self.book_name(book), xalign=0, ellipsize=Pango.EllipsizeMode.END)
            row = Gtk.ListBoxRow(child=label)
            row.book_index = index
            self.book_list.append(row)
            self.book_rows[book.code] = row
            if index == self.book_index:
                self.book_list.select_row(row)
        self.no_books.set_visible(not self.book_rows)
        self._updating = previous
        self.reveal_book()

    def reveal_book(self):
        if self._reveal_id:
            return
        frames = 0
        def reveal(*_):
            nonlocal frames
            frames += 1
            if frames < 3:
                return True
            if self.books:
                book = self.book_rows.get(self.books[self.book_index].code)
                if book is not None:
                    self.book_list.select_row(book)
                chapter = self.chapter_buttons.get(self.chapter_number)
                for widget, container, scroll in ((book, self.book_list, self.book_scroll),
                                                    (chapter, self.chapter_grid, self.chapter_scroll)):
                    if widget is not None and widget.get_mapped():
                        found, bounds = widget.compute_bounds(container)
                        if found:
                            scroll.get_vadjustment().clamp_page(
                                bounds.origin.y, bounds.origin.y + bounds.size.height)
            self._reveal_id = 0
            return False
        self._reveal_id = self.add_tick_callback(reveal)

    def populate_chapters(self, preferred=1, verse=1):
        while child := self.chapter_grid.get_first_child():
            self.chapter_grid.remove(child.get_child())
        self.chapter_buttons = {}
        book = self.books[self.book_index] if self.book_index < len(self.books) else None
        self.book_title.set_text(self.book_name(book) if book else tr('Choose a passage'))
        self.chapters = list(book.chapters) if book else []
        self.chapter_number = preferred if preferred in self.chapters else (self.chapters[0] if self.chapters else None)
        for chapter in self.chapters:
            button = Gtk.ToggleButton(label=str(chapter), height_request=42)
            button.update_property([Gtk.AccessibleProperty.LABEL], [f'{tr("Chapter")} {chapter}'])
            button.connect('clicked', lambda _, number=chapter: self.chapter_changed(number))
            self.chapter_buttons[chapter] = button
            self.chapter_grid.append(button)
        self.populate_verses(verse)
        self.mark_chapter()
        self.reveal_book()

    def mark_chapter(self):
        tab = self.owner.active_tab
        code = self.books[self.book_index].code if self.books else ''
        for chapter, button in self.chapter_buttons.items():
            selected = bool(tab and tab.state.resource == self.selected_resource() and
                            tab.state.reference.rsplit('.', 1)[0] == f'{code}.{chapter}')
            button.set_active(selected)
            if selected:
                button.add_css_class('suggested-action')
            else:
                button.remove_css_class('suggested-action')

    def populate_verses(self, preferred=1):
        self.verses = list(self.books[self.book_index].chapters[self.chapter_number]) if self.chapters else []
        self.verse.set_model(Gtk.StringList.new([str(number) for number in self.verses]))
        self.verse.set_sensitive(bool(self.verses))
        self.verse.set_selected(self.verses.index(preferred) if preferred in self.verses else 0)

    def selected_reference(self):
        verse = self.verse.get_selected()
        if self.book_index < len(self.books) and self.chapter_number and verse < len(self.verses):
            return f'{self.books[self.book_index].code}.{self.chapter_number}.{self.verses[verse]}'
        return ''

    def update_direct(self):
        self.direct.set_text(self.selected_reference())

    def apply_reference(self, reference):
        if not self.reader or not self.reader.has_reference(reference):
            raise ValueError(tr('This passage is not available in this translation.'))
        reference = self.reader.key(reference).getOSISRef()
        self._updating = True
        try:
            if not self.owner.navigate_selection(self.selected_resource(), reference):
                raise ValueError(tr('Unable to read this passage.'))
            tab = self.owner.active_tab
            self._stamp = (id(tab), tab.state.resource, tab.state.reference,
                           tuple(self.owner.library.installed('bible')))
        finally:
            self._updating = False
            self.mark_chapter()

    def apply_selected(self):
        self.update_direct()
        try:
            self.apply_reference(self.selected_reference())
            self.message()
        except Exception as error:
            self.message(f'{tr("Unable to read this passage.")} {error}')

    def version_changed(self, *_):
        if self._updating:
            return
        tab = self.owner.active_tab
        reference, previous_reader = tab.state.reference, tab.reader
        if self.selected_resource() == tab.state.resource:
            return
        try:
            self.load_version(reference)
            if not self.reader:
                raise ValueError(tr('Missing translation'))
            if previous_reader and previous_reader.versification != self.reader.versification:
                self.message(tr('Different versifications. Automatic alignment is unavailable.') + '\n' +
                             tr('Choose a chapter in this translation to start reading.'))
                return
            message = ''
            if not self.reader.has_reference(reference):
                self.message(tr('This passage is not available in this translation.') + '\n' +
                             tr('Choose a chapter in this translation to start reading.'))
                return
            self.apply_reference(reference)
            self.message(message)
        except Exception as error:
            # Keep the dropdown model alive during its selected notification.
            # Replacing that model from inside this signal crashes older GTK.
            self._updating = True
            self.version.set_selected(self.names.index(tab.state.resource)
                                      if tab.state.resource in self.names else Gtk.INVALID_LIST_POSITION)
            self.load_version(reference)
            self._updating = False
            self.message(str(error))

    def book_changed(self, _, row):
        if (not self._updating and row and row.get_parent() is self.book_list
                and hasattr(row, 'book_index') and row.book_index != self.book_index):
            self._updating = True
            self.book_list.select_row(row)
            self.book_index = row.book_index
            self.populate_chapters()
            self._updating = False
            self.apply_selected()

    def book_key_released(self, _, keyval, keycode, state):
        if keyval in (Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Home, Gdk.KEY_End,
                      Gdk.KEY_Page_Up, Gdk.KEY_Page_Down):
            self.book_changed(self.book_list, self.book_list.get_selected_row())

    def chapter_changed(self, number):
        if not self._updating:
            self._updating = True
            self.chapter_number = number
            self.populate_verses()
            self._updating = False
            self.apply_selected()

    def verse_changed(self, *_):
        if not self._updating:
            self.apply_selected()

    def commit(self):
        try:
            self.apply_reference(self.direct.get_text())
            self.sync(force=True)
            self.message()
        except Exception as error:
            self.message(f'{tr("Unable to read this passage.")} {error}')

    def open_library(self, *_):
        self.popdown()
        self.owner.open_library('bible')
