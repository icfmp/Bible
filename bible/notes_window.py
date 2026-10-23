"""Native local note editor, labels, central list, and file-portal backups."""
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, Pango, Gio, GObject, GLib

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
    def __init__(self, owner, note=None, context=None, explanation='', embedded=False):
        super().__init__(transient_for=owner, modal=True, title=tr('Passage note'),
                         default_width=700, default_height=700)
        self.set_size_request(360, 360)
        self.owner, self.note = owner, note
        self.embedded=embedded
        self.dialog_parent=owner if embedded else self
        self.context = context if context else {
            key: getattr(note, key) for key in ('versification', 'start', 'end', 'origin_translation', 'origin_language')}
        self.closed = False
        self._discard = False
        self._confirmation = None
        self.after_close = None
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header = Adw.HeaderBar()
        header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        header.set_title_widget(Adw.WindowTitle(title=tr('Passage note')))
        self.save_button = Gtk.Button(label=tr('Save'))
        self.save_button.add_css_class('suggested-action')
        self.save_button.connect('clicked', lambda *_: self.save())
        header.pack_end(self.save_button)
        if embedded:
            header.set_show_start_title_buttons(False);header.set_show_end_title_buttons(False)
            header.set_visible(False)
        layout.append(header)
        reference=Gtk.Label(label=passage_label(self.context['start'],self.context['end'],self.context['versification']),
                            wrap=True,xalign=0,margin_start=20,margin_end=20,margin_top=12)
        reference.add_css_class('title-2');layout.append(reference)
        origin=self.context['origin_translation']
        try:origin=owner.library.resource(origin).description
        except (ValueError,OSError):pass
        from .languages import language_name
        context_text=tr('Note created with')+' '+origin+' — '+language_name(self.context['origin_language'])
        context_label=Gtk.Label(label=context_text,wrap=True,xalign=0,margin_start=20,margin_end=20)
        context_label.add_css_class('dim-label');context_label.set_tooltip_text(self.context['origin_translation']+' · '+self.context['versification'])
        layout.append(context_label)
        self.status = Gtk.Label(label=explanation, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, selectable=True,
                                 xalign=0, margin_start=12, margin_end=12)
        layout.append(self.status)
        commands = Gtk.Box(spacing=4, margin_start=12, margin_end=12)
        for label,prefix,suffix,glyph,icon in [('Bold','**','**','B',None),('Italic','*','*','I',None),
                                             ('List','- ','',None,'view-list-symbolic'),('Link','[','](https://)',None,'insert-link-symbolic')]:
            button=Gtk.Button(tooltip_text=tr(label))
            button.add_css_class('flat')
            if icon:button.set_icon_name(icon)
            else:
                title=Gtk.Label();title.set_markup('<b>B</b>' if glyph=='B' else '<i>I</i>');button.set_child(title)
            button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
            button.connect('clicked',lambda _,before=prefix,after=suffix:self.format(before,after))
            commands.append(button)
        layout.append(commands)
        self.stack = Gtk.Stack(vexpand=True)
        switcher=Gtk.ToggleButton(label=tr('Preview'),tooltip_text=tr('Write / Preview'))
        switcher.connect('toggled',lambda button:self.stack.set_visible_child_name('preview' if button.get_active() else 'edit'))
        commands.append(switcher)
        self.body = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, monospace=False,
                                 left_margin=20, right_margin=20, top_margin=16, bottom_margin=20,pixels_inside_wrap=5)
        self.body.update_property([Gtk.AccessibleProperty.LABEL], [tr('Note in Markdown')])
        self.body.get_buffer().set_text(note.body if note else '')
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.body)
        self.stack.add_titled(scroll, 'edit', tr('Write'))
        from .note_preview import NotePreview
        self.preview = NotePreview(owner=owner,system=self.context['versification'],navigation_guard=self.guard_navigation)
        self.tags = self.preview.tags
        preview_scroll = Gtk.ScrolledWindow(vexpand=True)
        preview_scroll.set_child(self.preview)
        self.stack.add_titled(preview_scroll, 'preview', tr('Preview'))
        layout.append(self.stack)
        self.labels = Labels(owner.notes_store.labels(), lambda: None)
        self.labels.set_margin_start(12)
        self.labels.set_margin_end(12)
        self.labels.set_values(note.labels if note else [])
        layout.append(self.labels)
        if note:
            menu=Gtk.MenuButton(icon_name='open-menu-symbolic',tooltip_text=tr('Note actions'))
            popover=Gtk.Popover();actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
            delete=Gtk.Button(label=tr('Delete note…'));delete.add_css_class('flat')
            delete.connect('clicked',self.ask_delete);actions.append(delete)
            help_text=Gtk.Label(label=tr('Links are displayed as text and never opened automatically.'),wrap=True,max_width_chars=30)
            actions.append(help_text);popover.set_child(actions);menu.set_popover(popover);header.pack_end(menu)
        if embedded:self.embedded_content=layout
        else:self.set_content(layout)
        self._initial = (buffer_text(self.body), tuple(self.labels.values))
        self.body.get_buffer().connect('changed', lambda *_: self.update_preview())
        self.update_preview()

    def guard_navigation(self,action):
        self.after_close=action;self.close()

    def update_preview(self):
        self.preview.set_source(buffer_text(self.body))

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
        if text:
            buffer.select_range(buffer.get_iter_at_offset(offset+len(prefix)),buffer.get_iter_at_offset(offset+len(formatted)-len(suffix)))
        else:buffer.place_cursor(buffer.get_iter_at_offset(offset+len(prefix)))
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
            self._confirmation = message(self.dialog_parent, 'Delete this note permanently?',
                                          'This removes the note and its labels from this passage.', self.delete_confirmed)

    def delete_confirmed(self):
        try:
            self.owner.notes_store.delete(self.note)
            self.owner.notes_changed()
            self._discard = True
            self.close()
        except Exception as error:
            self.status.set_text(tr(str(error)))

    def present(self):
        if self.embedded:self.owner.present()
        else:super().present()

    def close(self):
        if not self.embedded:return super().close()
        if not self.on_close():
            if getattr(self.owner,'notes_space',None):self.owner.notes_space.editor_closed(self)
            self.destroy()

    def on_close(self, *_):
        if self.dirty and not self._discard:
            if self._confirmation is None or not self._confirmation.get_visible():
                dialog=Adw.MessageDialog.new(self.dialog_parent,tr('Unsaved changes'),tr('Save this note before leaving?'))
                dialog.add_response('cancel',tr('Keep editing'))
                dialog.add_response('discard',tr('Discard'))
                dialog.add_response('save',tr('Save'))
                dialog.set_response_appearance('discard',Adw.ResponseAppearance.DESTRUCTIVE)
                dialog.set_response_appearance('save',Adw.ResponseAppearance.SUGGESTED)
                dialog.set_default_response('save');dialog.set_close_response('cancel')
                def response(_,choice):
                    if choice in ('discard','confirm'):self._discard=True;self.close()
                    elif choice=='save':
                        if self.save(close=False):self.close()
                    else:self.after_close=None
                dialog.connect('response',response);dialog.present();self._confirmation=dialog
            return True
        self.closed = True
        if self.after_close:
            callback,self.after_close=self.after_close,None;callback()
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
        header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
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
        chooser = Gtk.FileChooserNative.new(tr('Back up notes') if save else tr('Restore notes'), self.owner,
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


class LabelFilter(Gtk.Box):
    """Existing labels only: consultation never creates or mutates a label."""
    def __init__(self,existing,changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        self.values=[];self.existing=list(existing);self.changed=changed;self._updating=False
        self.button=Gtk.MenuButton(label=tr('Filter by label'))
        popover=Gtk.Popover()
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        self.entry=Gtk.SearchEntry(placeholder_text=tr('Search labels'))
        self.entry.connect('search-changed',lambda *_:self.rebuild())
        self.entry.connect('activate',lambda *_:self.add())
        box.append(self.entry)
        self.list=Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        scroll=Gtk.ScrolledWindow(min_content_height=160,max_content_height=300,propagate_natural_height=True)
        scroll.set_child(self.list);box.append(scroll);popover.set_child(box);self.button.set_popover(popover)
        self.append(self.button)
        self.chips=Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,max_children_per_line=6)
        self.append(self.chips);self.rebuild()

    def set_suggestions(self,existing):self.existing=list(existing);self.rebuild()

    def set_values(self,values):
        from .notes import label_key
        known={label_key(v):v for v in self.existing}
        self.values=[known[label_key(v)] for v in values if label_key(v) in known]
        self.rebuild()

    def add(self):
        self.set_values(self.values+[self.entry.get_text()]);self.changed()

    def remove(self,label):self.set_values([v for v in self.values if v!=label]);self.changed()

    def rebuild(self):
        from .book_names import normalized
        self._updating=True
        for container in [self.list,self.chips]:
            child=container.get_first_child()
            while child:
                after=child.get_next_sibling();container.remove(child);child=after
        for label in self.existing:
            if normalized(self.entry.get_text()) not in normalized(label):continue
            button=Gtk.CheckButton(label=label,active=label in self.values)
            def toggle(widget,value=label):
                if self._updating:return
                self.values=list(dict.fromkeys(self.values+[value])) if widget.get_active() else [v for v in self.values if v!=value]
                GLib.idle_add(self.rebuild);self.changed()
            button.connect('toggled',toggle);self.list.append(button)
        for label in self.values:
            button=Gtk.Button(label=label+' ×',tooltip_text=tr('Remove filter'))
            button.connect('clicked',lambda _,value=label:self.remove(value));self.chips.append(button)
        self._updating=False


class NoteItem(GObject.Object):
    def __init__(self,note):super().__init__();self.note=note


def readable_date(value):
    from datetime import datetime,timedelta
    from babel.dates import format_date,format_datetime
    local=datetime.fromisoformat(value).astimezone()
    today=datetime.now().astimezone().date()
    label=tr('Today') if local.date()==today else tr('Yesterday') if local.date()==today-timedelta(days=1) else format_date(local.date(),format='long',locale='fr' if LANGUAGE.startswith('fr') else 'en')
    exact=format_datetime(local,format='long',locale='fr' if LANGUAGE.startswith('fr') else 'en')
    return label,exact


class NotesSpace(Gtk.Box):
    """Main-window notes workspace; keeps the reader and list context alive."""
    def __init__(self,owner):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.owner=owner;self.closed=False;self.rows=[];self._choosers=[];self.passage_filter=None
        self.editor=None
        header=Adw.HeaderBar();header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        self.workspace_title=Gtk.Label(label=tr('My notes'),ellipsize=Pango.EllipsizeMode.END,
                                       width_chars=1,max_width_chars=18)
        self.workspace_title.add_css_class('heading');header.set_title_widget(self.workspace_title)
        reading=Gtk.Button(label=tr('Reading'),tooltip_text=tr('Back to reading'))
        reading.connect('clicked',lambda *_:self.leave());header.pack_start(reading)
        self.save_button=Gtk.Button(icon_name='document-save-symbolic',tooltip_text=tr('Save'),sensitive=False)
        self.save_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Save')])
        self.save_button.add_css_class('suggested-action')
        self.save_button.connect('clicked',lambda *_:self.editor.save(close=False) if self.editor else None)
        menu=Gtk.MenuButton(icon_name='open-menu-symbolic',tooltip_text=tr('Notes and commands'))
        popover=Gtk.Popover();commands=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6,margin_top=12,margin_bottom=12,margin_start=12,margin_end=12)
        for label,callback in [('Back up notes',lambda:self.choose_backup(True)),('Restore notes',lambda:self.choose_backup(False)),
                               ('Delete note…',lambda:self.editor.ask_delete() if self.editor and self.editor.note else None)]:
            button=Gtk.Button(label=tr(label));button.add_css_class('flat');button.connect('clicked',lambda _,fn=callback:fn());commands.append(button)
            if label=='Delete note…':self.delete_button=button;button.set_visible(False)
        popover.set_child(commands);menu.set_popover(popover)
        header.pack_end(menu);header.pack_end(self.save_button);self.append(header)
        self.side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        tools=Gtk.Box(spacing=6,margin_start=12,margin_end=12,margin_top=12)
        self.search=Gtk.SearchEntry(placeholder_text=tr('Search notes or references'),hexpand=True)
        self.search.connect('search-changed',lambda *_:self.refresh());tools.append(self.search)
        self.sort=Gtk.DropDown(model=Gtk.StringList.new([tr('Most recent'),tr('Oldest first'),tr('Bible order')]))
        self.sort.update_property([Gtk.AccessibleProperty.LABEL],[tr('Sort notes')]);self.sort.connect('notify::selected',lambda *_:self.refresh())
        tools.append(self.sort);self.side.append(tools)
        self.labels=LabelFilter(owner.notes_store.labels(),self.refresh)
        self.labels.set_margin_start(12);self.labels.set_margin_end(12);self.side.append(self.labels)
        new=Gtk.Button(label=tr('New passage note'),margin_start=12,margin_end=12)
        new.connect('clicked',lambda *_:self.create_note());self.side.append(new)
        self.new_button=new
        self.status=Gtk.Label(xalign=0,wrap=True,margin_start=12,margin_end=12)
        self.side.append(self.status)
        self.model=Gio.ListStore.new(NoteItem);self.selection=Gtk.SingleSelection(model=self.model)
        factory=Gtk.SignalListItemFactory();factory.connect('setup',self.row_setup);factory.connect('bind',self.row_bind)
        self.list=Gtk.ListView(model=self.selection,factory=factory,single_click_activate=True)
        self.list.connect('activate',self.activate)
        self.scroll=Gtk.ScrolledWindow(vexpand=True);self.scroll.set_child(self.list);self.side.append(self.scroll)
        self.editor_panel=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,vexpand=True)
        self.detail_back=Gtk.Button(label=tr('Back to notes'),visible=False,halign=Gtk.Align.START,margin_start=12,margin_top=8)
        self.detail_back.connect('clicked',lambda *_:self.back_to_list());self.editor_panel.append(self.detail_back)
        self.placeholder=Adw.StatusPage(title=tr('Choose a note'),description=tr('Your notes remain available offline.'),icon_name='bible-notes-symbolic')
        self.editor_panel.append(self.placeholder)
        self.split=Adw.OverlaySplitView(sidebar=self.side,content=self.editor_panel,min_sidebar_width=280,max_sidebar_width=380,sidebar_position=Gtk.PackType.START,show_sidebar=True,collapsed=True)
        self.append(self.split)
        self.add_tick_callback(self.adapt)
        self.refresh()

    def adapt(self,*_):
        collapsed=self.get_width()<760
        self.workspace_title.set_visible(not collapsed)
        if self.split.get_collapsed()!=collapsed:
            self.split.set_collapsed(collapsed);self.split.set_show_sidebar(not self.editor if collapsed else True)
        self.detail_back.set_visible(collapsed and self.editor is not None)
        return True

    def row_setup(self,_,item):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,margin_start=12,margin_end=12,margin_top=10,margin_bottom=10)
        for index in range(4):
            label=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,max_width_chars=36)
            if index==0:label.add_css_class('heading')
            if index==1:label.set_lines(2);label.set_ellipsize(Pango.EllipsizeMode.END)
            if index>=2:label.add_css_class('dim-label');label.add_css_class('caption')
            box.append(label)
        item.set_child(box)

    def row_bind(self,_,item):
        note=item.get_item().note
        date,exact=readable_date(note.modified)
        strings=[passage_label(note.start,note.end,note.versification),render(note.body)[0][:240].replace('\n',' '),' · '.join(note.labels),date]
        label=item.get_child().get_first_child()
        for value in strings:label.set_text(value);label=label.get_next_sibling()
        item.get_child().set_tooltip_text(tr('Modified')+': '+exact)

    def show_all(self):self.passage_filter=None;self.refresh()

    def refresh(self):
        if self.closed:return
        try:
            notes=self.owner.notes_store.search(self.search.get_text(),self.labels.values,['recent','oldest','bible'][min(self.sort.get_selected(),2)])
            if self.passage_filter:
                valid={n.id for n in self.owner.notes_store.passage(*self.passage_filter)}
                notes=[note for note in notes if note.id in valid]
            self.rows=notes
            position=self.scroll.get_vadjustment().get_value()
            self.model.splice(0,self.model.get_n_items(),[NoteItem(n) for n in notes])
            self.scroll.get_vadjustment().set_value(position)
            self.status.set_text(tr('No matching note.') if not notes and self.owner.notes_store.all() else tr('No notes yet.') if not notes else '')
            self.new_button.set_sensitive(bool(self.owner.active_tab and self.owner.active_tab.reader))
            self.delete_button.set_visible(bool(self.editor and self.editor.note))
        except Exception as error:self.status.set_text(str(error))

    def guard(self,action):
        editor=self.owner.note_editor
        if editor and not editor.closed:
            editor.after_close=action;editor.close()
        else:action()

    def activate(self,_,index):
        if 0<=index<len(self.rows):self.open_note(self.rows[index])

    def open_note(self,note):
        if self.editor and not self.editor.closed and self.editor.note and self.editor.note.id==note.id:return
        self.guard(lambda:self.mount(note=note))

    def mount(self,note=None,context=None):
        editor=NoteEditor(self.owner,note=note,context=context,embedded=True)
        self.editor=editor;self.owner.note_editor=editor
        self.placeholder.set_visible(False)
        self.editor_panel.append(editor.embedded_content)
        passage=Gtk.Button(label=tr('Open passage'),halign=Gtk.Align.START,margin_start=20)
        passage.connect('clicked',lambda *_:self.open_passage())
        editor.embedded_content.prepend(passage)
        self.save_button.set_sensitive(True);self.delete_button.set_visible(bool(note))
        if self.split.get_collapsed():self.split.set_show_sidebar(False)
        self.detail_back.set_visible(self.split.get_collapsed())
        return editor

    def editor_closed(self,editor):
        parent=editor.embedded_content.get_parent()
        if parent:parent.remove(editor.embedded_content)
        if self.editor is editor:
            self.editor=None;self.placeholder.set_visible(True);self.save_button.set_sensitive(False);self.delete_button.set_visible(False)

    def create_note(self):
        def create():
            tab=self.owner.active_tab
            if not tab or not tab.reader:return
            start,end=tab.selected_passage()
            self.mount(context=dict(versification=tab.reader.versification,start=start,end=end,origin_translation=tab.state.resource,origin_language=self.owner.library.resource(tab.state.resource).language))
        self.guard(create)

    def leave(self):self.guard(lambda:self.owner.main_pages.set_visible_child_name('reading'))

    def back_to_list(self):self.guard(lambda:self.split.set_show_sidebar(True))

    def open_passage(self):
        if not self.editor:return
        note=self.editor.note
        if not note:
            if not self.editor.save(close=False):return
            note=self.editor.note
        def go():
            if self.owner.open_saved_note(note,edit=False):
                self.owner.main_pages.set_visible_child_name('reading')
            else:
                self.status.set_text(tr('No compatible translation installed. The note remains available.'))
                self.split.set_show_sidebar(True)
        self.guard(go)

    def present(self):self.owner.main_pages.set_visible_child_name('notes');self.owner.present()
    def close(self):self.leave()
    def set_default_size(self,width,height):self.owner.set_default_size(width,height)
    choose_backup=NotesWindow.choose_backup
    backup_to=NotesWindow.backup_to
    restore_from=NotesWindow.restore_from
