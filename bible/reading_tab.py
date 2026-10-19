"""One independent local reader, including its scroll position and translation."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from .i18n import tr
from .sword_provider import Reader
from .book_names import display_name
from .i18n import LANGUAGE


class ReadingTab(Gtk.Box):
    def __init__(self, library, state, changed, jump_to_reference=False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6, vexpand=True)
        self.library, self.state, self.changed = library, state, changed
        self.reader = None
        self.current = None
        self._restoring_scroll = True
        self._tick_id = 0
        self._scroll_frames = 0
        self._verse_offsets = {}
        self._jump_reference = None
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True,
                                margin_start=12, margin_end=12)
        self.append(self.status)
        self.scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.text = Gtk.TextView(editable=False, cursor_visible=False,
                                 wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                 left_margin=24, right_margin=24,
                                 top_margin=16, bottom_margin=24)
        self.text.add_css_class('reading')
        self.text.set_tooltip_text(tr('Click a verse to select it. Alt+Up/Down selects the previous/next verse.'))
        self._selected_tag = self.text.get_buffer().create_tag(None, weight=700)
        self.verse_click = Gtk.GestureClick(button=1)
        self.verse_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.verse_click.connect('released', self.verse_clicked)
        self.text.add_controller(self.verse_click)
        self._target_mark = self.text.get_buffer().create_mark(
            None, self.text.get_buffer().get_start_iter(), True)
        self.scroll.set_child(self.text)
        self.append(self.scroll)
        self.scroll.get_vadjustment().connect('value-changed', self.scroll_changed)
        self.connect('map', self.on_map)
        self.load_resource(jump_to_reference)

    def passage_title(self):
        if self.reader:
            try:
                key = self.reader.key(self.state.reference)
                name = display_name(key.getOSISBookName(), key.getBookName(), LANGUAGE)
                return f'{name} {key.getChapter()}:{key.getVerse()}'
            except ValueError:
                pass
        return self.state.reference if self.state.resource else tr('Choose a passage')

    def title(self):
        return f'{self.passage_title()} — {self.state.resource}' if self.state.resource else tr('New tab')

    def navigate(self, resource, reference):
        try:
            reader = self.reader if resource == self.state.resource and self.reader else Reader(
                self.library.root / resource, resource)
            if not reader.has_reference(reference):
                raise ValueError(tr('This passage is not available in this translation.'))
            previous_reader, previous_resource = self.reader, self.state.resource
            self.reader = reader
            self.state.resource = resource
            if self.show(reference):
                return True
            self.reader, self.state.resource = previous_reader, previous_resource
            self.changed(self)
            return False
        except Exception as error:
            self.status.set_text(f'{tr("Unable to read this passage.")} {error}')
            self.status.set_visible(True)
            return False

    def load_resource(self, jump_to_reference=False):
        self._verse_offsets = {}
        self._jump_reference = None
        self.reader = None
        self.current = None
        self.text.get_buffer().set_text('')
        if not self.state.resource:
            self.status.set_text(tr('No translation installed. Load the catalogue to choose one.')
                                 if not self.library.installed('bible') else tr('Choose a translation'))
        elif self.state.resource not in self.library.installed('bible'):
            self.status.set_text(tr('This translation is no longer installed. Download it again or choose another translation.'))
        else:
            try:
                self.reader = Reader(self.library.root / self.state.resource, self.state.resource)
                available = self.reader.has_reference(self.state.reference)
                reference = self.state.reference if available else self.reader.first_reference()
                if not available:
                    self.state.scroll = 0.0
                self.show(reference, restore=not jump_to_reference)
                if not available:
                    self.status.set_text(tr('This passage is unavailable. Opened the first available passage.'))
                    self.status.set_visible(True)
            except Exception as error:
                self.status.set_text(f'{tr("Unable to read this passage.")} {error}')
                self.status.set_visible(True)
        if self.reader is None:
            self.status.set_visible(True)

    def show(self, reference, restore=False):
        if not self.reader or not reference:
            return
        try:
            if not self.reader.has_reference(reference):
                raise ValueError(tr('This passage is not available in this translation.'))
            chapter = self.reader.chapter(reference)
            canonical = self.reader.key(reference).getOSISRef()
            self._restoring_scroll = True
            self.current = chapter
            self.state.reference = canonical
            self._jump_reference = canonical if not restore else None
            if not restore:
                self.state.scroll = 0.0
            parts, offset = [], 0
            self._verse_offsets = {}
            for ref, text in chapter.verses:
                self._verse_offsets[ref] = offset
                part = f'{ref.rsplit(".", 1)[-1]}  {text}\n\n'
                parts.append(part)
                offset += len(part)
            self.text.get_buffer().set_text(''.join(parts))
            self.highlight_selection()
            self.status.set_text(tr('Ready'))
            self.status.set_visible(False)
            self.schedule_scroll_restore()
            self.changed(self)
            return True
        except Exception as error:
            self.status.set_text(f'{tr("Unable to read this passage.")} {error}')
            self.status.set_visible(True)
            return False

    def highlight_selection(self):
        buffer = self.text.get_buffer()
        buffer.remove_tag(self._selected_tag, buffer.get_start_iter(), buffer.get_end_iter())
        if self.state.reference in self._verse_offsets:
            start = self._verse_offsets[self.state.reference]
            buffer.apply_tag(self._selected_tag, buffer.get_iter_at_offset(start),
                             buffer.get_iter_at_offset(start + len(self.state.reference.rsplit('.', 1)[-1])))
        self.text.update_property([Gtk.AccessibleProperty.LABEL], [self.passage_title()])

    def select_verse(self, reference):
        if reference not in self._verse_offsets:
            return False
        self.state.reference = reference
        self.highlight_selection()
        self.changed(self)
        return True

    def verse_clicked(self, gesture, count, x, y):
        if self.text.get_buffer().get_has_selection():
            return
        bx, by = self.text.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(x), int(y))
        found, iterator = self.text.get_iter_at_location(bx, by)
        if found:
            candidates = [ref for ref, offset in self._verse_offsets.items() if offset <= iterator.get_offset()]
            if candidates:
                self.select_verse(candidates[-1])

    def step_verse(self, direction):
        references = list(self._verse_offsets)
        if self.state.reference in references:
            index = references.index(self.state.reference) + direction
            if 0 <= index < len(references):
                self.select_verse(references[index])
                iterator = self.text.get_buffer().get_iter_at_offset(self._verse_offsets[references[index]])
                self.text.scroll_to_iter(iterator, 0.1, False, 0, 0)

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
            self.text.get_buffer().move_mark(self._target_mark, iterator)
            # Mapping can invalidate GTK's first pending scroll. Keep the request
            # until a subsequent layout frame confirms the verse is visible.
            target = self.text.get_iter_location(iterator)
            visible = self.text.get_visible_rect()
            if not (visible.y <= target.y < visible.y + visible.height):
                self.text.scroll_to_mark(self._target_mark, 0.0, True, 0.0, 0.0)
                return True
        else:
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
