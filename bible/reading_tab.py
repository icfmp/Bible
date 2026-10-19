"""One independent local reader, including its scroll position and translation."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango

from .i18n import tr
from .sword_provider import Reader


class ReadingTab(Gtk.Box):
    def __init__(self, library, state, changed, open_in_new, jump_to_reference=False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6, vexpand=True)
        self.library, self.state, self.changed = library, state, changed
        self.reader = None
        self.current = None
        self._updating = False
        self._restoring_scroll = True
        self._tick_id = 0
        self._scroll_frames = 0
        self._verse_offsets = {}
        self._jump_reference = None
        translation = Gtk.Box(spacing=6, margin_start=12, margin_end=12)
        self.translations = Gtk.DropDown(hexpand=True, tooltip_text=tr('Translations'))
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', lambda _, item: item.set_child(Gtk.Label(
            xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=24)))
        factory.connect('bind', lambda _, item: item.get_child().set_text(item.get_item().get_string()))
        self.translations.set_factory(factory)
        self.translations.set_list_factory(factory)
        self.translations.connect('notify::selected', self.select_translation)
        translation.append(self.translations)
        self.append(translation)
        navigation = Gtk.Box(spacing=6, margin_start=12, margin_end=12)
        self.previous = Gtk.Button(icon_name='go-previous-symbolic', sensitive=False,
                                   tooltip_text=tr('Previous chapter'))
        self.previous.connect('clicked', lambda *_: self.show(self.current.previous))
        navigation.append(self.previous)
        self.reference = Gtk.Entry(hexpand=True, width_chars=12,
                                   placeholder_text=tr('Reference (e.g. John 1:1)'))
        self.reference.connect('activate', lambda entry: self.show(entry.get_text()))
        navigation.append(self.reference)
        self.following = Gtk.Button(icon_name='go-next-symbolic', sensitive=False,
                                    tooltip_text=tr('Next chapter'))
        self.following.connect('clicked', lambda *_: self.show(self.current.following))
        navigation.append(self.following)
        self.new_passage = Gtk.Button(icon_name='tab-new-symbolic',
                                      tooltip_text=tr('Open passage in new tab'))
        self.new_passage.connect('clicked', lambda *_: open_in_new(
            self.state.resource, self.reference.get_text() or self.state.reference))
        navigation.append(self.new_passage)
        self.append(navigation)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True,
                                margin_start=12, margin_end=12)
        self.append(self.status)
        self.scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.text = Gtk.TextView(editable=False, cursor_visible=False,
                                 wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                 left_margin=24, right_margin=24,
                                 top_margin=16, bottom_margin=24)
        self.text.add_css_class('reading')
        self.scroll.set_child(self.text)
        self.append(self.scroll)
        self.scroll.get_vadjustment().connect('value-changed', self.scroll_changed)
        self.connect('map', self.on_map)
        self.refresh_resources()
        self.load_resource(jump_to_reference)

    def title(self):
        return f'{self.state.resource} — {self.state.reference.rsplit(".", 1)[0]}' if self.state.resource else tr('New tab')

    def refresh_resources(self):
        self._updating = True
        installed = self.library.installed()
        self.names = installed[:]
        if self.state.resource not in self.names:
            self.names.insert(0, self.state.resource)
        labels = [name if name in installed else (
            f'{name} ({tr("Missing translation")})' if name else tr('Choose a translation'))
                  for name in self.names]
        self.translations.set_model(Gtk.StringList.new(labels))
        self.translations.set_selected(self.names.index(self.state.resource))
        self.translations.set_sensitive(bool(installed))
        self._updating = False

    def select_translation(self, *_):
        if self._updating:
            return
        index = self.translations.get_selected()
        if index >= len(self.names):
            return
        self.state.resource = self.names[index]
        self.load_resource()
        self.changed(self)

    def load_resource(self, jump_to_reference=False):
        self._verse_offsets = {}
        self._jump_reference = None
        self.reader = None
        self.current = None
        self.previous.set_sensitive(False)
        self.following.set_sensitive(False)
        self.text.get_buffer().set_text('')
        self.reference.set_text(self.state.reference)
        if not self.state.resource:
            self.status.set_text(tr('No translation installed. Load the catalogue to choose one.')
                                 if not self.library.installed() else tr('Choose a translation'))
        elif self.state.resource not in self.library.installed():
            self.status.set_text(tr('This translation is no longer installed. Download it again or choose another translation.'))
        else:
            try:
                self.reader = Reader(self.library.root / self.state.resource, self.state.resource)
                self.show(self.state.reference, restore=not jump_to_reference)
            except Exception as error:
                self.status.set_text(f'{tr("Unable to read this passage.")} {error}')
        self.reference.set_sensitive(self.reader is not None)
        self.new_passage.set_sensitive(self.state.resource is not None)

    def show(self, reference, restore=False):
        if not self.reader or not reference:
            return
        try:
            chapter = self.reader.chapter(reference)
            canonical = self.reader.key(reference).getOSISRef()
            self._restoring_scroll = True
            self.current = chapter
            self.state.reference = canonical
            self._jump_reference = canonical if not restore else None
            if not restore:
                self.state.scroll = 0.0
            self.reference.set_text(chapter.reference)
            parts, offset = [], 0
            self._verse_offsets = {}
            for ref, text in chapter.verses:
                self._verse_offsets[ref] = offset
                part = f'{ref.rsplit(".", 1)[-1]}  {text}\n\n'
                parts.append(part)
                offset += len(part)
            self.text.get_buffer().set_text(''.join(parts))
            self.previous.set_sensitive(chapter.previous is not None)
            self.following.set_sensitive(chapter.following is not None)
            self.status.set_text(tr('Ready'))
            self.schedule_scroll_restore()
            self.changed(self)
        except Exception as error:
            self.status.set_text(f'{tr("Unable to read this passage.")} {error}')

    def on_map(self, *_):
        self.schedule_scroll_restore()

    def schedule_scroll_restore(self):
        self._restoring_scroll = True
        self._scroll_frames = 0
        if not self._tick_id:
            self._tick_id = self.add_tick_callback(self.restore_scroll)

    def restore_scroll(self, *_):
        # GTK needs layout frames after mapping or replacing a chapter.
        self._scroll_frames += 1
        if self._scroll_frames < 3:
            return True
        adjustment = self.scroll.get_vadjustment()
        maximum = max(0, adjustment.get_upper() - adjustment.get_page_size())
        desired = self.state.scroll * maximum
        if (self._jump_reference in self._verse_offsets
                and self._jump_reference.rsplit('.', 1)[-1] != '1'):
            iterator = self.text.get_buffer().get_iter_at_offset(self._verse_offsets[self._jump_reference])
            desired = max(0, self.text.get_iter_location(iterator).y)
        adjustment.set_value(min(desired, maximum))
        self._tick_id = 0
        self._jump_reference = None
        self._restoring_scroll = False
        self.scroll_changed()
        return False

    def scroll_changed(self, *_):
        if self._restoring_scroll or not self.get_mapped():
            return
        adjustment = self.scroll.get_vadjustment()
        maximum = adjustment.get_upper() - adjustment.get_page_size()
        if maximum > 0:
            self.state.scroll = max(0.0, min(1.0, adjustment.get_value() / maximum))
            self.changed(self)
