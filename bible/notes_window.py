"""Native local note editor, labels, central list, and file-portal backups."""
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, Pango

from .book_names import display_name
from .i18n import LANGUAGE, tr
from .markdown import render
from .notes import clean_labels, parts


def passage_label(start, end=None, versification=None):
    code, chapter, verse = parts(start)
    name = code
    try:
        import Sword
        key = Sword.VerseKey()
        key.setVersificationSystem(versification or 'KJV')
        key.setAutoNormalize(False)
        key.setText(start)
        if key.popError() == '\x00' and key.getOSISBookName() == code:
            name = key.getBookName()
    except Exception:
        pass
    result = f'{display_name(code, name, LANGUAGE)} {chapter}:{verse}'
    if end and end != start:
        result += '–' + str(parts(end)[2])
    return result


def buffer_text(view):
    buffer = view.get_buffer()
    return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)


def message(parent, heading, body, accepted, canceled=None):
    dialog = Adw.MessageDialog.new(parent, tr(heading), tr(body))
    dialog.add_response('cancel', tr('Cancel'))
    dialog.add_response('confirm', tr('Confirm'))
    dialog.set_response_appearance('confirm', Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_default_response('cancel')
    dialog.set_close_response('cancel')
    dialog.connect('response', lambda _, response: accepted() if response == 'confirm'
                   else canceled() if canceled else None)
    dialog.present()
    return dialog


class Labels(Gtk.Box):
    def __init__(self, existing, changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.values = []
        self.changed = changed
        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=False,
                                 min_children_per_line=1, max_children_per_line=8)
        self.append(self.flow)
        row = Gtk.Box(spacing=6)
        self.entry = Gtk.Entry(hexpand=True, placeholder_text=tr('Add a label'))
        self.entry.update_property([Gtk.AccessibleProperty.LABEL], [tr('Labels')])
        self.entry.connect('activate', lambda *_: self.add())
        row.append(self.entry)
        button = Gtk.Button(icon_name='list-add-symbolic', tooltip_text=tr('Add a label'))
        button.connect('clicked', lambda *_: self.add())
        row.append(button)
        self.append(row)
        self.error = Gtk.Label(xalign=0, wrap=True)
        self.append(self.error)
        self.set_suggestions(existing)

    def set_suggestions(self, existing):
        model = Gtk.ListStore(str)
        for label in existing:
            model.append([label])
        completion = Gtk.EntryCompletion(model=model, text_column=0, inline_completion=True)
        self.entry.set_completion(completion)

    def add(self):
        try:
            self.set_values(clean_labels([*self.values, self.entry.get_text()]))
            self.entry.set_text('')
            self.error.set_text('')
            self.changed()
        except ValueError as error:
            self.error.set_text(tr(str(error)))

    def set_values(self, values):
        self.values = list(values)
        child = self.flow.get_first_child()
        while child:
            following = child.get_next_sibling()
            self.flow.remove(child)
            child = following
        for label in self.values:
            button = Gtk.Button(tooltip_text=tr('Remove label') + ': ' + label)
            button.set_child(Gtk.Label(label=f'{label} ×', ellipsize=Pango.EllipsizeMode.END,
                                        max_width_chars=20, width_chars=1))
            button.connect('clicked', lambda _, value=label: self.remove(value))
            self.flow.append(button)

    def remove(self, label):
        self.set_values([value for value in self.values if value != label])
        self.changed()


class NoteEditor(Adw.Window):
    def __init__(self, owner, note=None, context=None, explanation=''):
        super().__init__(transient_for=owner, modal=True, title=tr('Passage note'),
                         default_width=700, default_height=700)
        self.set_size_request(360, 360)
        self.owner, self.note = owner, note
        self.context = context if context else {
            key: getattr(note, key) for key in ('versification', 'start', 'end', 'origin_translation', 'origin_language')}
        self.closed = False
        self._discard = False
        self._confirmation = None
        self.after_close = None
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=tr('Passage note')))
        self.save_button = Gtk.Button(label=tr('Save'))
        self.save_button.add_css_class('suggested-action')
        self.save_button.connect('clicked', lambda *_: self.save())
        header.pack_start(self.save_button)
        layout.append(header)
        context_text = (f'{passage_label(self.context["start"], self.context["end"], self.context["versification"])} '
                        f'[{self.context["versification"]}]\n{tr("Original context")}: '
                        f'{self.context["origin_translation"]} ({self.context["origin_language"]})')
        layout.append(Gtk.Label(label=context_text, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, selectable=True, margin_start=12, margin_end=12))
        self.status = Gtk.Label(label=explanation, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, selectable=True,
                                 xalign=0, margin_start=12, margin_end=12)
        layout.append(self.status)
        commands = Gtk.Box(spacing=4, margin_start=12, margin_end=12)
        for label, prefix, suffix in [('Bold', '**', '**'), ('Italic', '*', '*'),
                                      ('List', '- ', ''), ('Link', '[', '](https://)')]:
            button = Gtk.Button(label=tr(label))
            button.connect('clicked', lambda _, before=prefix, after=suffix: self.format(before, after))
            commands.append(button)
        layout.append(commands)
        self.stack = Gtk.Stack(vexpand=True)
        switcher = Gtk.StackSwitcher(stack=self.stack, halign=Gtk.Align.CENTER)
        layout.append(switcher)
        self.body = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, monospace=True,
                                 left_margin=12, right_margin=12, top_margin=12, bottom_margin=12)
        self.body.update_property([Gtk.AccessibleProperty.LABEL], [tr('Note in Markdown')])
        self.body.get_buffer().set_text(note.body if note else '')
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.body)
        self.stack.add_titled(scroll, 'edit', tr('Write'))
        self.preview = Gtk.TextView(editable=False, cursor_visible=False,
                                    wrap_mode=Gtk.WrapMode.WORD_CHAR, left_margin=12,
                                    right_margin=12, top_margin=12, bottom_margin=12)
        self.preview.update_property([Gtk.AccessibleProperty.LABEL], [tr('Safe preview')])
        buffer = self.preview.get_buffer()
        self.tags = {'bold': buffer.create_tag(None, weight=700),
                     'italic': buffer.create_tag(None, style=Pango.Style.ITALIC),
                     'link': buffer.create_tag(None, underline=Pango.Underline.SINGLE)}
        preview_scroll = Gtk.ScrolledWindow(vexpand=True)
        preview_scroll.set_child(self.preview)
        self.stack.add_titled(preview_scroll, 'preview', tr('Preview'))
        layout.append(self.stack)
        layout.append(Gtk.Label(label=tr('Links are displayed as text and never opened automatically.'),
                                wrap=True, margin_start=12, margin_end=12))
        self.labels = Labels(owner.notes_store.labels(), lambda: None)
        self.labels.set_margin_start(12)
        self.labels.set_margin_end(12)
        self.labels.set_values(note.labels if note else [])
        layout.append(self.labels)
        if note:
            delete = Gtk.Button(label=tr('Delete note'), margin_start=12, margin_end=12, margin_bottom=12)
            delete.add_css_class('destructive-action')
            delete.connect('clicked', self.ask_delete)
            layout.append(delete)
        self.set_content(layout)
        self._initial = (buffer_text(self.body), tuple(self.labels.values))
        self.body.get_buffer().connect('changed', lambda *_: self.update_preview())
        self.update_preview()

    def update_preview(self):
        text, spans = render(buffer_text(self.body))
        buffer = self.preview.get_buffer()
        buffer.set_text(text)
        for kind, start, end in spans:
            buffer.apply_tag(self.tags[kind], buffer.get_iter_at_offset(start), buffer.get_iter_at_offset(end))

    def format(self, prefix, suffix):
        buffer = self.body.get_buffer()
        selection = buffer.get_selection_bounds()
        if selection:
            start, end = selection
        else:
            start = buffer.get_iter_at_mark(buffer.get_insert())
            end = start.copy()
        text = buffer.get_text(start, end, False)
        formatted = (''.join('- ' + line for line in text.splitlines(keepends=True))
                     if prefix == '- ' and '\n' in text else prefix + text + suffix)
        offset = start.get_offset()
        buffer.begin_user_action()
        buffer.delete(start, end)
        buffer.insert(buffer.get_iter_at_offset(offset), formatted)
        buffer.end_user_action()
        self.stack.set_visible_child_name('edit')
        self.body.grab_focus()

    @property
    def dirty(self):
        return (buffer_text(self.body), tuple(self.labels.values)) != self._initial or bool(self.labels.entry.get_text().strip())

    def save(self, close=True):
        if self.labels.entry.get_text().strip():
            self.labels.add()
            if self.labels.error.get_text():
                return False
        try:
            self.note = self.owner.notes_store.save(buffer_text(self.body), self.labels.values,
                                                    existing=self.note, **self.context)
            self._initial = (self.note.body, tuple(self.labels.values))
            self.owner.notes_changed()
            self.status.set_text(tr('Note saved.'))
            if close:
                self.close()
            return True
        except Exception as error:
            self.status.set_text(tr(str(error)))
            return False

    def ask_delete(self, *_):
        if self.note:
            self._confirmation = message(self, 'Delete this note permanently?',
                                          'This removes the note and its labels from this passage.', self.delete_confirmed)

    def delete_confirmed(self):
        try:
            self.owner.notes_store.delete(self.note)
            self.owner.notes_changed()
            self._discard = True
            self.close()
        except Exception as error:
            self.status.set_text(tr(str(error)))

    def on_close(self, *_):
        if self.dirty and not self._discard:
            if self._confirmation is None or not self._confirmation.get_visible():
                def discard():
                    self._discard = True
                    self.close()
                self._confirmation = message(self, 'Discard unsaved changes?',
                                              'Your note has not been saved.', discard,
                                              lambda: setattr(self, 'after_close', None))
            return True
        self.closed = True
        if self.after_close:
            callback, self.after_close = self.after_close, None
            callback()
        return False


class NotesWindow(Adw.Window):
    def __init__(self, owner):
        super().__init__(transient_for=owner, title=tr('My notes'), default_width=720, default_height=700)
        self.set_size_request(360, 360)
        self.owner = owner
        self.closed = False
        self.passage_filter = None
        self.rows = []
        self._choosers = []
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=tr('My notes')))
        back = Gtk.Button(icon_name='go-previous-symbolic', tooltip_text=tr('Back to reading'))
        back.connect('clicked', lambda *_: self.close())
        header.pack_start(back)
        new = Gtk.Button(icon_name='document-new-symbolic', tooltip_text=tr('New passage note'))
        new.connect('clicked', lambda *_: owner.new_note(force_new=True))
        header.pack_start(new)
        menu = Gtk.MenuButton(icon_name='open-menu-symbolic', tooltip_text=tr('Backup and restore'))
        popover = Gtk.Popover()
        actions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_start=12,
                           margin_end=12, margin_top=12, margin_bottom=12)
        for label, save in [('Back up notes', True), ('Restore notes', False)]:
            button = Gtk.Button(label=tr(label))
            button.connect('clicked', lambda _, saving=save: self.choose_backup(saving))
            actions.append(button)
        popover.set_child(actions)
        menu.set_popover(popover)
        header.pack_end(menu)
        layout.append(header)
        self.search = Gtk.SearchEntry(placeholder_text=tr('Search notes or references'), margin_start=12, margin_end=12)
        self.search.update_property([Gtk.AccessibleProperty.LABEL], [tr('Search notes or references')])
        self.search.connect('search-changed', lambda *_: self.refresh())
        layout.append(self.search)
        self.sort = Gtk.DropDown(model=Gtk.StringList.new([tr('Most recent'), tr('Oldest first'), tr('Bible order')]),
                                 margin_start=12, margin_end=12)
        self.sort.update_property([Gtk.AccessibleProperty.LABEL], [tr('Sort notes')])
        self.sort.connect('notify::selected', lambda *_: self.refresh())
        layout.append(self.sort)
        self.labels = Labels(owner.notes_store.labels(), self.refresh)
        self.labels.set_margin_start(12)
        self.labels.set_margin_end(12)
        layout.append(self.labels)
        self.all_passages = Gtk.Button(label=tr('All passages'), visible=False, margin_start=12, margin_end=12)
        self.all_passages.connect('clicked', lambda *_: self.show_all())
        layout.append(self.all_passages)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True, margin_start=12, margin_end=12)
        layout.append(self.status)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.connect('row-activated', self.activate)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.list)
        layout.append(scroll)
        self.set_content(layout)
        self.refresh()

    def show_all(self):
        self.passage_filter = None
        self.refresh()

    def refresh(self):
        if self.closed:
            return
        try:
            notes = self.owner.notes_store.search(self.search.get_text(), self.labels.values,
                                                   ['recent', 'oldest', 'bible'][min(self.sort.get_selected(), 2)])
            if self.passage_filter:
                allowed = {n.id for n in self.owner.notes_store.passage(*self.passage_filter)}
                notes = [note for note in notes if note.id in allowed]
            child = self.list.get_first_child()
            while child:
                following = child.get_next_sibling()
                self.list.remove(child)
                child = following
            self.rows = notes
            for note in notes:
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=12,
                               margin_end=12, margin_top=8, margin_bottom=8)
                title = passage_label(note.start, note.end, note.versification) + f' [{note.versification}]'
                for text in [title, render(note.body)[0][:160].replace('\n', ' '),
                             ' · '.join(note.labels), f'{tr("Created")}: {note.created[:19]} · {tr("Modified")}: {note.modified[:19]}']:
                    box.append(Gtk.Label(label=text, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR))
                self.list.append(box)
            self.all_passages.set_visible(self.passage_filter is not None)
            self.status.set_text(tr('No matching note.') if not notes else f'{len(notes)} {tr("note") if len(notes) == 1 else tr("notes")}')
        except Exception as error:
            self.status.set_text(tr(str(error)))

    def activate(self, _, row):
        if 0 <= row.get_index() < len(self.rows):
            self.owner.open_saved_note(self.rows[row.get_index()])

    def choose_backup(self, save):
        chooser = Gtk.FileChooserNative.new(tr('Back up notes') if save else tr('Restore notes'), self,
            Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN, tr('Save') if save else tr('Open'), tr('Cancel'))
        filter = Gtk.FileFilter()
        filter.set_name(tr('Notes backup (JSON)'))
        filter.add_pattern('*.json')
        chooser.add_filter(filter)
        if save:
            chooser.set_current_name('bible-notes.json')
        def response(dialog, result):
            if result == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                path = file.get_path() if file else None
                if path:
                    self.backup_to(path) if save else self.restore_from(path)
                else:
                    self.status.set_text(tr('Choose a local file.'))
            dialog.destroy()
            self._choosers.remove(dialog)
        chooser.connect('response', response)
        self._choosers.append(chooser)
        chooser.show()

    def backup_to(self, path):
        try:
            self.owner.notes_store.export(path)
            self.status.set_text(tr('Notes backup saved.'))
            return True
        except Exception as error:
            self.status.set_text(tr(str(error)))
            return False

    def restore_from(self, path):
        try:
            added, skipped, conflicts = self.owner.notes_store.restore(path)
            self.owner.notes_changed()
            self.status.set_text(f'{tr("Restore complete. Added / already present / copies kept")}: {added} / {skipped} / {conflicts}')
            return True
        except Exception as error:
            self.status.set_text(tr(str(error)))
            return False

    def on_close(self, *_):
        self.closed = True
        for chooser in self._choosers[:]:
            chooser.destroy()
        return False
