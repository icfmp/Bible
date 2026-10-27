"""Native local note editor, labels, central list, and file-portal backups."""
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, Pango, Gio, GObject, GLib

from .book_names import display_name
from .i18n import LANGUAGE, tr
from .markdown import render
from .notes import clean_labels, parts
from .highlights import COLORS


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
        final=parts(end)
        result+='–'+(str(final[2]) if final[:2]==(code,chapter) else f'{final[1]}:{final[2]}' if final[0]==code else passage_label(end,versification=versification))
    return result


def buffer_text(view):
    buffer = view.get_buffer()
    return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)


def message(parent, heading, body, accepted, canceled=None):
    dialog = Adw.MessageDialog.new(parent, tr(heading), tr(body))
    if hasattr(parent,'reading_style'):dialog.add_css_class(parent.reading_style.scope+'-window')
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
    def __init__(self, owner, note=None, context=None, explanation='', embedded=False, compact=False):
        super().__init__(transient_for=owner, modal=True, title=tr('Passage note'),
                         default_width=700, default_height=700)
        self.set_size_request(360, 360)
        self.owner, self.note = owner, note
        self.embedded=embedded;self.compact=compact;self.embedded_host=None
        self.dialog_parent=owner if embedded else self
        self.context = context if context else {
            key: getattr(note, key) for key in ('versification', 'start', 'end', 'origin_translation', 'origin_language')}
        if hasattr(owner,'reading_style'):self.add_css_class(owner.reading_style.scope+'-window')
        self.closed = False
        self._discard = False
        self._confirmation = None
        self.after_close = None
        self.autosave = False
        self._autosave_id = 0
        self._saving = False
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header = Adw.HeaderBar();self.header=header
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
        reference.add_css_class('heading' if compact else 'title-2');layout.append(reference)
        origin=self.context['origin_translation']
        try:origin=owner.library.resource(origin).description
        except (ValueError,OSError):pass
        from .languages import language_name
        context_text=tr('Note created with')+' '+origin+' — '+language_name(self.context['origin_language'])
        context_label=Gtk.Label(label=context_text,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,xalign=0,margin_start=20,margin_end=20)
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
        self.body.add_css_class('study-content')
        self.body.update_property([Gtk.AccessibleProperty.LABEL], [tr('Note in Markdown')])
        self.body.get_buffer().set_text(note.body if note else '')
        scroll = Gtk.ScrolledWindow(vexpand=not compact, min_content_height=180 if compact else 0,
                                    max_content_height=240 if compact else -1,propagate_natural_height=compact)
        self.body_scroll=scroll
        self.stack.set_vexpand(not compact)
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
        if compact:
            expander=Gtk.Expander(label=tr('Labels'));expander.set_child(self.labels);layout.append(expander)
        else:layout.append(self.labels)
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

    def enable_autosave(self):
        """Coalesce writes on GTK's owner thread; optimistic revisions still apply."""
        if self.autosave:return
        self.autosave=True
        self.body.get_buffer().connect('changed',lambda *_:self.queue_autosave())
        self.labels.changed=self.queue_autosave
        self.labels.entry.connect('changed',lambda *_:self.queue_autosave())

    def cancel_autosave(self):
        if self._autosave_id:
            GLib.source_remove(self._autosave_id);self._autosave_id=0

    def queue_autosave(self):
        if self.closed or self._discard or self._saving:return
        self.cancel_autosave()
        self.status.set_text(tr('Saving…'))
        self._autosave_id=GLib.timeout_add(600,self.autosave_pending)

    def autosave_pending(self):
        self._autosave_id=0
        if self.closed or self._discard or not self.dirty:return False
        # Typing a label is not an implicit Add-label action. Keep the whole
        # draft and normal leave/save guards until the label is committed.
        if self.labels.entry.get_text().strip():
            self.status.set_text(tr('Press Enter to add the label before saving.'));return False
        self.save(close=False)
        return False

    def save(self, close=True):
        if self.closed or self._discard:return False
        self.cancel_autosave()
        self._saving=True
        if self.labels.entry.get_text().strip():
            self.labels.add()
            if self.labels.error.get_text():
                self._saving=False
                return False
        try:
            self.note = self.owner.notes_store.save(buffer_text(self.body), self.labels.values,
                                                    existing=self.note, **self.context)
            self._initial = (self.note.body, tuple(self.labels.values))
            host=self.embedded_host
            if host and hasattr(host,'note_saved'):host.note_saved(self)
            self.owner.notes_changed()
            self.status.set_text(tr('Note saved.'))
            if close:
                self.close()
            return True
        except Exception as error:
            self.status.set_text((tr('Unable to save this note. Your draft is kept.')+'\n' if self.autosave else '')+tr(str(error)))
            return False
        finally:self._saving=False

    def ask_delete(self, *_):
        if self.note:
            self._confirmation = message(self.dialog_parent, 'Delete this note permanently?',
                                          'This removes the note and its labels from this passage.', self.delete_confirmed)

    def delete_confirmed(self):
        self.cancel_autosave()
        try:
            self.owner.notes_store.delete(self.note)
            self._discard = True
            self.owner.notes_changed()
            self.close()
        except Exception as error:
            self.status.set_text(tr(str(error)))

    def present(self):
        if self.embedded:self.owner.present()
        else:super().present()

    def close(self):
        if not self.embedded:return super().close()
        if not self.on_close():
            host=self.embedded_host or getattr(self.owner,'notes_space',None)
            if host:host.editor_closed(self)
            self.destroy()

    def on_close(self, *_):
        if self.autosave and self.dirty and not self._discard:
            self.save(close=False)
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
        self.cancel_autosave()
        self.closed = True
        if self.embedded_host and not self.embedded:self.embedded_host.editor_closed(self)
        if self.after_close:
            callback,self.after_close=self.after_close,None;callback()
        return False


class NotesWindow(Adw.Window):
    def __init__(self, owner):
        super().__init__(transient_for=owner, title=tr('My notes'), default_width=720, default_height=700)
        self.add_css_class(owner.reading_style.scope+'-window')
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
            caption=button.get_child()
            if isinstance(caption,Gtk.Label):
                caption.set_wrap(True);caption.set_wrap_mode(Pango.WrapMode.WORD_CHAR);caption.set_width_chars(1);caption.set_max_width_chars(24)
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


class AnnotationItem(GObject.Object):
    def __init__(self,annotation):super().__init__();self.annotation=annotation


class NotesSpace(Gtk.Box):
    """Adaptive projection over the existing note database and highlight file."""
    def __init__(self,owner):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.owner=owner;self.closed=False;self.rows=[];self._choosers=[];self.passage_filter=None
        self.editor=None;self.selected_key=None;self.selected_annotation=None;self.category='all';self._detail_requested=False
        self._syncing=False;self._wide=None;self._reader_cache={};self._excerpt_cache={};self._version=None
        header=Adw.HeaderBar();header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        from .workspace_selector import WorkspaceSelector
        self.space_selector=WorkspaceSelector(owner,notes=True);header.pack_start(self.space_selector)
        self.workspace_title=Gtk.Label(label=tr('Notes and highlights'),ellipsize=Pango.EllipsizeMode.END,width_chars=1,max_width_chars=24,visible=owner.get_width()>=760)
        self.workspace_title.add_css_class('heading');header.set_title_widget(self.workspace_title)
        self.filter_button=Gtk.ToggleButton(icon_name='bible-filter-symbolic',tooltip_text=tr('Filters'))
        self.filter_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Filters')]);self.filter_button.add_css_class('flat')
        menu=Gtk.MenuButton(icon_name='view-more-symbolic',tooltip_text=tr('Annotation actions'))
        popover=Gtk.Popover();commands=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,margin_top=8,margin_bottom=8,margin_start=8,margin_end=8)
        self.save_button=Gtk.Button(label=tr('Save'),sensitive=False);self.save_button.add_css_class('flat')
        self.save_button.connect('clicked',lambda *_:self.editor.save(close=False) if self.editor else None);commands.append(self.save_button)
        for label,callback in [('Back up notes',lambda:self.choose_backup(True)),('Restore notes',lambda:self.choose_backup(False)),
                               ('Back up highlights',lambda:self.choose_highlight_backup(False)),('Restore highlights',lambda:self.choose_highlight_backup(True)),
                               ('Delete note…',lambda:self.editor.ask_delete() if self.editor and self.editor.note else None)]:
            button=Gtk.Button(label=tr(label));button.add_css_class('flat');button.connect('clicked',lambda _,fn=callback:fn());commands.append(button)
            if label=='Delete note…':self.delete_button=button;button.set_visible(False)
        popover.set_child(commands);menu.set_popover(popover)
        from .application_surfaces import application_menu
        self.main_menu=application_menu();header.pack_end(self.main_menu);header.pack_end(menu);self.append(header)
        self.filters=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_top=12,margin_bottom=12,margin_start=12,margin_end=12)
        self.categories={}
        for key,title in [('all','All'),('notes','Notes'),('highlights','Highlights')]:
            button=Gtk.ToggleButton()
            if self.categories:button.set_group(next(iter(self.categories.values())))
            button.connect('clicked',lambda widget,value=key:self.set_category(value) if widget.get_active() else None)
            self.categories[key]=button;self.filters.append(button)
        self.categories['all'].set_active(True)
        self.count_hint=Gtk.Label(label=tr('Each note and each saved verse highlight counts once. Related records stay separate.'),wrap=True,xalign=0,max_width_chars=1)
        self.count_hint.add_css_class('caption');self.count_hint.add_css_class('dim-label');self.filters.append(self.count_hint)
        self.books=[''];self.book=Gtk.DropDown(model=Gtk.StringList.new([tr('All books')]))
        self.book.update_property([Gtk.AccessibleProperty.LABEL],[tr('Book')]);self.book.connect('notify::selected',lambda *_:self.refresh() if not self._syncing else None);self.filters.append(self.book)
        self.labels=LabelFilter(owner.notes_store.labels(),self.refresh);self.filters.append(self.labels)
        self.color=Gtk.DropDown(model=Gtk.StringList.new([tr('All colors'),*[tr(label) for _,label in COLORS.values()]]))
        self.color.update_property([Gtk.AccessibleProperty.LABEL],[tr('Highlight color')]);self.color.connect('notify::selected',lambda *_:self.refresh() if not self._syncing else None);self.filters.append(self.color)
        filters_scroll=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER);filters_scroll.set_child(self.filters)
        self.side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        tools=Gtk.Box(spacing=6,margin_start=12,margin_end=12,margin_top=12)
        self.search=Gtk.SearchEntry(placeholder_text=tr('Search annotations'),hexpand=True)
        self.search.connect('search-changed',lambda *_:self.refresh());tools.append(self.search)
        self.sort=Gtk.DropDown(model=Gtk.StringList.new([tr('Most recent'),tr('Oldest first'),tr('Bible order')]))
        from .version_chooser import bounded_choices
        for control in (self.book,self.color,self.sort):bounded_choices(control)
        self.sort.update_property([Gtk.AccessibleProperty.LABEL],[tr('Sort annotations')]);self.sort.connect('notify::selected',lambda *_:self.refresh());tools.append(self.sort);tools.append(self.filter_button);self.side.append(tools)
        self.sort.set_tooltip_text(tr('Date sorting uses note modification dates. Highlights without dates follow in Bible order.'))
        self.new_button=Gtk.Button(child=Gtk.Label(label=tr('New passage note'),wrap=True),margin_start=12,margin_end=12)
        self.new_button.connect('clicked',lambda *_:self.create_note());self.side.append(self.new_button)
        self.status=Gtk.Label(xalign=0,wrap=True,margin_start=12,margin_end=12);self.side.append(self.status)
        self.model=Gio.ListStore.new(AnnotationItem);self.selection=Gtk.SingleSelection(model=self.model,autoselect=False)
        factory=Gtk.SignalListItemFactory();factory.connect('setup',self.row_setup);factory.connect('bind',self.row_bind)
        self.list=Gtk.ListView(model=self.selection,factory=factory,single_click_activate=True);self.list.connect('activate',self.activate)
        self.scroll=Gtk.ScrolledWindow(vexpand=True);self.scroll.set_child(self.list);self.side.append(self.scroll)
        self.editor_panel=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,vexpand=True)
        detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.detail_back=Gtk.Button(label=tr('Back to annotations'),visible=False,halign=Gtk.Align.START,margin_start=12,margin_top=8)
        self.detail_back.connect('clicked',lambda *_:self.back_to_list());detail.append(self.detail_back)
        self.detail_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.detail_scroll.set_overflow(Gtk.Overflow.HIDDEN)
        self.detail_scroll.set_child(self.editor_panel)
        viewport=self.detail_scroll.get_child()
        if isinstance(viewport,Gtk.Viewport):viewport.set_scroll_to_focus(True)
        detail.append(self.detail_scroll)
        self.context_panel=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6,margin_start=12,margin_end=12,margin_top=8,visible=False)
        self.open_button=Gtk.Button(label=tr('Open in Bible'),halign=Gtk.Align.START);self.open_button.connect('clicked',lambda *_:self.open_passage());self.context_panel.append(self.open_button)
        self.versions=Gtk.DropDown();bounded_choices(self.versions);self.versions.update_property([Gtk.AccessibleProperty.LABEL],[tr('Excerpt translation')]);self.versions.connect('notify::selected',self.version_changed);self.context_panel.append(self.versions)
        self.excerpt=Gtk.Label(wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,xalign=0,selectable=True,max_width_chars=1)
        excerpt_scroll=Gtk.ScrolledWindow(overflow=Gtk.Overflow.HIDDEN,hscrollbar_policy=Gtk.PolicyType.NEVER,max_content_height=150,propagate_natural_height=True);excerpt_scroll.set_child(self.excerpt);self.context_panel.append(excerpt_scroll)
        self.related=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        related_scroll=Gtk.ScrolledWindow(overflow=Gtk.Overflow.HIDDEN,hscrollbar_policy=Gtk.PolicyType.NEVER,max_content_height=150,propagate_natural_height=True);related_scroll.set_child(self.related)
        self.related_expander=Gtk.Expander(label=tr('Related annotations'),visible=False);self.related_expander.set_child(related_scroll);self.context_panel.append(self.related_expander)
        self.editor_panel.append(self.context_panel)
        self.placeholder=Adw.StatusPage(title=tr('Choose an annotation'),description=tr('Your annotations remain available offline.'),icon_name='bible-notes-symbolic');self.editor_panel.append(self.placeholder)
        self.highlight_detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_start=12,margin_end=12,margin_top=12,visible=False);self.editor_panel.append(self.highlight_detail)
        self.split=Adw.OverlaySplitView(sidebar=self.side,content=detail,min_sidebar_width=280,max_sidebar_width=380,sidebar_width_unit=Adw.LengthUnit.PX,sidebar_position=Gtk.PackType.START,show_sidebar=True,collapsed=True)
        self.outer=Adw.OverlaySplitView(sidebar=filters_scroll,content=self.split,min_sidebar_width=210,max_sidebar_width=240,sidebar_width_unit=Adw.LengthUnit.PX,sidebar_position=Gtk.PackType.START,collapsed=True,show_sidebar=False)
        self.filter_button.connect('toggled',lambda widget:self.outer.set_show_sidebar(widget.get_active()))
        self.outer.connect('notify::show-sidebar',lambda *_:self.filter_button.set_active(self.outer.get_show_sidebar()))
        self.append(self.outer);self.add_tick_callback(self.adapt);self.refresh()

    def adapt(self,*_):
        if self.closed:return False
        wide=self.get_width()>=1120
        if wide!=self._wide:
            self._wide=wide;self.outer.set_collapsed(not wide);self.outer.set_show_sidebar(wide)
        collapsed=self.split.get_width()<760
        self.workspace_title.set_visible(self.get_width()>=760)
        if self.split.get_collapsed()!=collapsed:
            self.split.set_collapsed(collapsed);self.split.set_show_sidebar(not self._detail_requested if collapsed else True)
        self.detail_back.set_visible(collapsed and (self.editor is not None or self._detail_requested))
        return True

    def row_setup(self,_,item):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,margin_start=12,margin_end=12,margin_top=10,margin_bottom=10)
        for index in range(4):
            label=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,max_width_chars=36)
            if index==0:label.add_css_class('heading')
            if index==1:label.set_lines(2);label.set_ellipsize(Pango.EllipsizeMode.END)
            if index>=2:label.add_css_class('dim-label');label.add_css_class('caption')
            box.append(label)
        item.set_child(box)

    def row_bind(self,_,item):
        from .highlights import COLORS
        a=item.get_item().annotation
        snippet=render(a.body)[0][:240].replace('\n',' ') if a.note else self.excerpt_for(a,limit=1)[0][:240]
        kind=tr('Note') if a.note else tr('Highlight annotation')+' · '+tr(COLORS[a.color][1])
        date,exact=readable_date(a.modified) if a.modified else ('','')
        strings=[passage_label(a.start,a.end,a.system),snippet,kind+((' · '+' · '.join(a.labels)) if a.labels else ''),date]
        label=item.get_child().get_first_child()
        for value in strings:label.set_text(value);label=label.get_next_sibling()
        item.get_child().set_tooltip_text((tr('Modified')+': '+exact+'\n' if exact else '')+tr('Original source')+': '+a.origin+' · '+a.system)

    def set_category(self,key):
        if self._syncing or key not in self.categories:return
        self.category=key;self._syncing=True;self.categories[key].set_active(True);self._syncing=False;self.refresh()

    def show_all(self):self.passage_filter=None;self.set_category('all')

    def reveal(self,key):
        """An explicit passage-to-collection route reveals its actual record."""
        self._syncing=True;self.passage_filter=None;self.category='all'
        self.search.set_text('');self.labels.set_values([]);self.book.set_selected(0);self.color.set_selected(0)
        self.categories['all'].set_active(True);self._syncing=False;self.refresh()
        current=next((a for a in self.all_records if a.key==key),None)
        if current:self.open_annotation(current)
        def scroll():
            if not self.closed and self.selected_key==key:
                index=next((i for i,a in enumerate(self.rows) if a.key==key),None)
                if index is not None:self.list.scroll_to(index,0,None)
            return False
        GLib.idle_add(scroll)

    def refresh(self):
        if self.closed:return
        from .annotation_collection import records,filter_records
        from .highlights import COLORS
        from .notes import BOOK_ORDER
        try:
            items=records(self.owner.notes_store.all(),self.owner.highlights.entries.values());self.all_records=items
            if self.selected_key and not any(a.key==self.selected_key for a in items) and (not self.editor or self.editor._discard):
                self.selected_key=None;self.selected_annotation=None;self._detail_requested=False;self.context_panel.set_visible(False);self.highlight_detail.set_visible(False);self.placeholder.set_visible(True)
            current_book=self.books[min(self.book.get_selected(),len(self.books)-1)]
            books=['']+sorted({parts(a.start)[0] for a in items},key=lambda code:(BOOK_ORDER.get(code,10000),code))
            names={parts(a.start)[0]:passage_label(a.start,versification=a.system).rsplit(' ',1)[0] for a in items}
            self._syncing=True
            if books!=self.books:
                self.books=books;self.book.set_model(Gtk.StringList.new([tr('All books')]+[names[code] for code in books[1:]]));self.book.set_selected(books.index(current_book) if current_book in books else 0)
            note_count=sum(a.note is not None for a in items)
            for key,title,count in [('all','All',str(note_count)+' + ?' if self.owner.highlights.error else len(items)),('notes','Notes',note_count),('highlights','Highlights','?' if self.owner.highlights.error else sum(a.mark is not None for a in items))]:
                self.categories[key].set_child(Gtk.Label(label=f'{tr(title)} ({count})',wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1))
            self._syncing=False
            if self.passage_filter:
                system,first,last=self.passage_filter
                items=[a for a in items if a.system==system and parts(a.start)<=parts(last) and parts(a.end)>=parts(first)]
            rows=filter_records(items,self.search.get_text(),self.labels.values,self.category,self.books[min(self.book.get_selected(),len(self.books)-1)],(['']+list(COLORS))[min(self.color.get_selected(),len(COLORS))],['recent','oldest','bible'][min(self.sort.get_selected(),2)],names)
            self.refresh_versions()
            position=self.scroll.get_vadjustment().get_value();self.rows=rows
            self.model.splice(0,self.model.get_n_items(),[AnnotationItem(a) for a in rows])
            selected=next((i for i,a in enumerate(rows) if a.key==self.selected_key),Gtk.INVALID_LIST_POSITION);self.selection.set_selected(selected)
            def restore():
                if not self.closed:self.scroll.get_vadjustment().set_value(position)
                return False
            GLib.idle_add(restore)
            self.status.set_text(tr('No matching annotations.') if not rows and self.all_records else tr('No annotations yet.') if not rows else '')
            if self.owner.highlights.error:self.status.set_text(tr('Highlights unavailable. The original file is preserved.')+' '+self.owner.highlights.error)
            self.new_button.set_sensitive(bool(self.owner.active_tab and self.owner.active_tab.reader))
            self.delete_button.set_visible(bool(self.editor and self.editor.note));self.refresh_versions()
        except Exception as error:self._syncing=False;self.status.set_text(str(error))

    def refresh_versions(self):
        available=self.owner.library.installed('bible')
        if available==getattr(self,'_available_names',None):return
        current=self._version or (self.owner.active_tab.state.resource if self.owner.active_tab else None)
        # Keep an unavailable explicit choice visible, rather than silently
        # showing a different translation after its removal.
        self._syncing=True;self._available_names=available
        names=([current] if current and current not in available else [])+available
        self.version_names=names;self._version=current or (names[0] if names else None)
        labels=[self.owner.library.resource(name).description if name in available else name+' ('+tr('Missing translation')+')' for name in names]
        self.versions.set_model(Gtk.StringList.new(labels or [tr('No installed Bible')]))
        self.versions.set_selected(names.index(self._version) if self._version else 0);self.versions.set_sensitive(bool(available));self._syncing=False

    def version_changed(self,*_):
        if self._syncing:return
        index=self.versions.get_selected()
        self._version=self.version_names[index] if index<len(self.version_names) else None
        self._excerpt_cache.clear()
        if self.selected_annotation:self.update_context(self.selected_annotation)
        # Rebind visible highlight snippets with the deliberately chosen version.
        if self.model.get_n_items():self.model.items_changed(0,self.model.get_n_items(),self.model.get_n_items())

    def reader(self):
        name=self._version
        if not name or name not in self.owner.library.installed('bible'):return None
        if name not in self._reader_cache:
            from .sword_provider import Reader
            self._reader_cache[name]=Reader(self.owner.library.root/name,name)
        return self._reader_cache[name]

    def mapped_references(self,a,reader):
        from .reference_resolution import resolve,_span
        # Imported annotations can contain structurally valid but unavailable
        # references. Validate in the established resolver before enumerating.
        resolve(a.start,a.system,reader)
        if a.end!=a.start:resolve(a.end,a.system,reader)
        refs=[]
        for source in dict.fromkeys(_span(a.start,a.end,a.system)):
            if source.rsplit('.',1)[-1]=='0':continue
            mapped=resolve(source,a.system,reader)
            for reference in _span(mapped.start,mapped.end,reader.versification):
                if reference not in refs:refs.append(reference)
        return refs

    def excerpt_for(self,a,limit=6):
        key=(self._version,a.system,a.start,a.end,limit)
        if key in self._excerpt_cache:return self._excerpt_cache[key]
        try:
            reader=self.reader()
            if not reader:raise ValueError(tr('Install a Bible to display this passage. Your annotation is kept.'))
            refs=self.mapped_references(a,reader)
            from .sword_provider import passage_verses
            text=[value for _,value in passage_verses(reader,refs[:limit])]
            from .reference_resolution import _span
            mapped_label=(passage_label(refs[0],refs[-1],reader.versification) if _span(refs[0],refs[-1],reader.versification)==refs else '; '.join(passage_label(ref,versification=reader.versification) for ref in refs))
            description=tr('Displayed in')+' '+self.owner.library.resource(self._version).description+' · '+mapped_label
            if len(refs)>limit:description+=' · '+tr('Excerpt')
            result=('\n'.join(text),description,True)
        except (ValueError,OSError,IndexError) as error:result=(tr('Passage unavailable or no verified alignment.')+' '+str(error),tr('Original source')+': '+a.origin+' · '+a.system,False)
        self._excerpt_cache[key]=result
        if len(self._excerpt_cache)>512:self._excerpt_cache.pop(next(iter(self._excerpt_cache)))
        return result

    def update_context(self,a):
        if self.selected_key!=a.key:self.related_expander.set_expanded(False)
        self.selected_key=a.key;self.selected_annotation=a;self.context_panel.set_visible(True);self.placeholder.set_visible(False)
        text,description,available=self.excerpt_for(a);self.excerpt.set_text(description+'\n'+text);self.open_button.set_sensitive(available)
        while self.related.get_first_child():self.related.remove(self.related.get_first_child())
        try:reader=self.reader()
        except (ValueError,OSError):reader=None
        self.related_expander.set_visible(False)
        if not reader:return
        from .passage_annotations import PassageAnnotations
        matching=PassageAnnotations()
        try:
            spans=matching.positions(reader,a.system,a.start,a.end)
            related=[other for other in self.all_records if other.key!=a.key and any(matching.matches(reader,start,end,other.system,other.start,other.end) for _,_,start,end in spans)]
        except ValueError:related=[]
        if related:
            self.related_expander.set_label(tr('Related annotations')+f' ({len(related)})');self.related_expander.set_visible(True)
            for other in related[:20]:
                button=Gtk.Button(child=Gtk.Label(label=passage_label(other.start,other.end,other.system)+' · '+(render(other.body)[0][:80] if other.note else tr('Highlight annotation')),wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,xalign=0))
                button.add_css_class('flat');button.connect('clicked',lambda _,value=other:self.open_annotation(value));self.related.append(button)
            if len(related)>20:self.related.append(Gtk.Label(label=tr('More related records are available in the list.'),wrap=True))

    def guard(self,action):
        editor=self.owner.note_editor
        if editor and not editor.closed:editor.after_close=action;editor.close()
        else:action()

    def activate(self,_,index):
        if 0<=index<len(self.rows):self.open_annotation(self.rows[index])

    def open_annotation(self,a):
        if a.note:return self.open_note(a.note)
        def show():
            self._detail_requested=True;self.update_context(a);self.highlight_detail.set_visible(True)
            while self.highlight_detail.get_first_child():self.highlight_detail.remove(self.highlight_detail.get_first_child())
            from .highlights import COLORS
            self.highlight_detail.append(Gtk.Label(label=tr('Original source')+': '+a.origin+' · '+a.system,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,xalign=0))
            color_group=None
            for color,(_,title) in COLORS.items():
                button=Gtk.ToggleButton(label=tr(title))
                if color_group:button.set_group(color_group)
                else:color_group=button
                button.set_active(a.color==color)
                button.connect('clicked',lambda widget,value=color:self.change_highlight(a,value) if widget.get_active() and value!=a.color else None);self.highlight_detail.append(button)
            delete=Gtk.Button(label=tr('Remove highlight'));delete.add_css_class('destructive-action');delete.connect('clicked',lambda *_:message(self.owner,'Remove this highlight?','The related notes are kept.',lambda:self.change_highlight(a,None)));self.highlight_detail.append(delete)
            if self.split.get_collapsed():self.split.set_show_sidebar(False)
        self.guard(show)

    def change_highlight(self,a,color):
        try:
            key=(a.system,a.start)
            if self.owner.highlights.entries.get(key)!=a.mark:raise ValueError(tr('This highlight changed elsewhere. Reopen it before editing.'))
            self.owner.highlights.set(a.system,[a.start],color,a.origin);self.owner.refresh_highlights();self.refresh()
            if color:
                current=next(item for item in self.all_records if item.key==a.key);self.open_annotation(current)
            else:
                self.selected_key=None;self.selected_annotation=None;self._detail_requested=False;self.context_panel.set_visible(False);self.highlight_detail.set_visible(False);self.placeholder.set_visible(True);self.split.set_show_sidebar(True)
        except (ValueError,OSError) as error:self.status.set_text(str(error))

    def open_note(self,note):
        if self.editor and not self.editor.closed and self.editor.note and self.editor.note.id==note.id:return self.editor
        self.guard(lambda:self.mount(note=self.owner.notes_store.get(note.id)))
        return self.editor

    def mount(self,note=None,context=None):
        if note is None and context is None:return
        editor=NoteEditor(self.owner,note=note,context=context,embedded=True);editor.embedded_host=self
        editor.body_scroll.set_min_content_height(180)
        self.editor=editor;self.owner.note_editor=editor;self._detail_requested=True;editor.enable_autosave()
        self.highlight_detail.set_visible(False);self.placeholder.set_visible(False);self.editor_panel.append(editor.embedded_content)
        if note:
            from .annotation_collection import records
            self.update_context(records([note],[])[0])
        else:self.context_panel.set_visible(False);self.selected_key=None;self.selected_annotation=None
        self.save_button.set_sensitive(True);self.delete_button.set_visible(bool(note))
        if self.split.get_collapsed():self.split.set_show_sidebar(False)
        self.detail_back.set_visible(self.split.get_collapsed())
        def focus():
            if self.editor is editor and not editor.closed and editor.body.get_mapped():
                # Start at the detail's context, keeping its first controls
                # visible instead of scrolling a short window to the editor.
                (self.detail_back if self.split.get_collapsed() else self.open_button).grab_focus()
                self.detail_scroll.get_vadjustment().set_value(0)
            return False
        GLib.idle_add(focus);return editor

    def editor_closed(self,editor):
        parent=editor.embedded_content.get_parent()
        if parent:parent.remove(editor.embedded_content)
        if self.editor is editor:
            self.editor=None;self.save_button.set_sensitive(False);self.delete_button.set_visible(False)
            if not editor.note:self._detail_requested=False;self.placeholder.set_visible(True)

    def note_saved(self,editor):
        if self.editor is editor and editor.note:
            from .annotation_collection import records
            self.update_context(records([editor.note],[])[0])

    def create_note(self):
        def create():
            tab=self.owner.active_tab
            if not tab or not tab.reader:return
            start,end=tab.selected_passage();self.mount(context=dict(versification=tab.reader.versification,start=start,end=end,origin_translation=tab.state.resource,origin_language=self.owner.library.resource(tab.state.resource).language))
        self.guard(create)

    def leave(self):self.guard(self.owner.return_to_reading)
    def back_to_list(self):
        def show():self._detail_requested=False;self.split.set_show_sidebar(True)
        self.guard(show)

    def open_passage(self):
        if not self.selected_annotation:return
        a=self.selected_annotation
        def go():
            try:
                reader=self.reader();refs=self.mapped_references(a,reader)
                tab=self.owner.active_tab
                same=tab and tab.state.resource==self._version and tab.state.reference==refs[0]
                if same or self.owner.navigate_selection(self._version,refs[0],new_tab=True):self.owner.main_pages.set_visible_child_name('reading')
            except (ValueError,OSError,AttributeError) as error:self.status.set_text(str(error))
        self.guard(go)

    def present(self):
        self.owner.main_pages.set_visible_child_name('notes');self.owner.present()
        if self._detail_requested and self.selected_key and not self.editor:
            current=next((a for a in self.all_records if a.key==self.selected_key),None)
            if current:self.open_annotation(current)
    def close(self):self.leave()
    def set_default_size(self,width,height):self.owner.set_default_size(width,height)
    def flush_for_backup(self):
        if self.editor and not self.editor.closed and self.editor.dirty and not self.editor.save(close=False):
            self.status.set_text(self.editor.status.get_text());return False
        return True

    def choose_backup(self,save):
        if self.flush_for_backup():return NotesWindow.choose_backup(self,save)

    def backup_to(self,path):
        return bool(self.flush_for_backup() and NotesWindow.backup_to(self,path))

    def restore_from(self,path):
        return bool(self.flush_for_backup() and NotesWindow.restore_from(self,path))

    def choose_highlight_backup(self,restore):
        chooser=Gtk.FileChooserNative.new(tr('Restore highlights') if restore else tr('Back up highlights'),self.owner,Gtk.FileChooserAction.OPEN if restore else Gtk.FileChooserAction.SAVE,tr('Open') if restore else tr('Save'),tr('Cancel'))
        if not restore:chooser.set_current_name('Bible-highlights.json')
        self._choosers.append(chooser)
        def response(dialog,result):
            if result==Gtk.ResponseType.ACCEPT:
                file=dialog.get_file();path=file.get_path() if file else None
                def apply():
                    try:
                        if not path:raise ValueError(tr('Choose a local file.'))
                        if restore:self.owner.highlights.restore(path);self.owner.refresh_highlights();self.refresh()
                        else:self.owner.highlights.backup(path)
                        self.status.set_text(tr('Done'))
                    except (ValueError,OSError) as error:self.status.set_text(str(error))
                if restore:message(self.owner,'Restore highlights?','Merge the backup with existing highlights. Notes and translations are unchanged.',apply)
                else:apply()
            dialog.destroy();self._choosers.remove(dialog)
        chooser.connect('response',response);chooser.show()
