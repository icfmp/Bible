"""Contextual notes/highlights reusing the existing stores, editor and actions."""
from gi.repository import Gtk, Pango
from .i18n import tr
from .highlights import COLORS
from .notes_window import passage_label, readable_date
from .note_preview import NotePreview
from .passage_annotations import PassageAnnotations


class PassageNotes(Gtk.Box):
    def __init__(self, owner):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_start=16, margin_end=16, margin_top=12, margin_bottom=20)
        self.owner = owner
        self.annotations = PassageAnnotations()
        self.context = None; self._stamp = None; self.rows = []; self.marks = []
        self.note_limit = 20
        self.heading = Gtk.Label(xalign=0, wrap=True); self.heading.add_css_class('heading')
        self.append(self.heading)
        commands = Gtk.Box(spacing=6)
        self.add = Gtk.Button(label=tr('Add note'))
        self.add.connect('clicked', self.add_note); commands.append(self.add)
        all_notes = Gtk.Button(icon_name='bible-notes-symbolic', tooltip_text=tr('My notes'), action_name='win.notes')
        all_notes.add_css_class('flat'); commands.append(all_notes); self.append(commands)
        self.status = Gtk.Label(wrap=True, xalign=0, visible=False)
        self.status.connect('notify::label',lambda *_:self.status.set_visible(bool(self.status.get_text())))
        self.status.add_css_class('dim-label'); self.append(self.status)
        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); self.append(self.list)
        label = Gtk.Label(label=tr('Highlights'), xalign=0); label.add_css_class('heading'); self.append(label)
        self.highlight_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); self.append(self.highlight_list)
        self.add_highlight = Gtk.MenuButton(label=tr('Add highlight'))
        self.append(self.add_highlight)

    def clear(self, box):
        while box.get_first_child():box.remove(box.get_first_child())

    def refresh(self, force=False):
        tab = self.owner.active_tab
        if not tab or not tab.reader:
            self.context = None; self.add.set_sensitive(False); self.add_highlight.set_sensitive(False)
            self.status.set_text(tr('Open a Bible passage before creating a note.'))
            self.heading.set_text(tr('Passage notes')); self.clear(self.list); self.clear(self.highlight_list)
            return
        reader = tab.reader; start, end = tab.selected_passage()
        store = self.owner.notes_store
        stamp = (id(tab), id(reader), start, end, store.generation if store else -1,
                 tuple((m['system'], m['reference'], m['color']) for m in self.owner.highlights.entries.values()))
        if not force and stamp == self._stamp:return
        self._stamp = stamp
        self.context = dict(versification=reader.versification, start=start, end=end,
                            origin_translation=tab.state.resource,
                            origin_language=self.owner.library.resource(tab.state.resource).language)
        self.heading.set_text(tr('Notes on')+' '+passage_label(start, end, reader.versification))
        self.add.set_sensitive(store is not None)
        self.add_highlight.set_sensitive(not self.owner.highlights.error)
        self.rows = self.annotations.notes(reader, start, end, store) if store else []
        self.marks = self.annotations.highlights(reader, start, end, self.owner.highlights)
        self.status.set_text(tr('Notes unavailable. The original file has been preserved.') if store is None else
                             tr('No notes for this passage.') if not self.rows else '')
        self.clear(self.list)
        for note in self.rows[:self.note_limit]:
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            header = Gtk.Box(spacing=4)
            title = Gtk.Label(label=passage_label(note.start, note.end, note.versification),
                              xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END, width_chars=1)
            title.set_tooltip_text(note.origin_translation+' · '+note.versification)
            header.append(title)
            edit = Gtk.Button(icon_name='document-edit-symbolic', tooltip_text=tr('Edit note'))
            edit.add_css_class('flat'); edit.connect('clicked', lambda _, value=note:self.owner.edit_note(note=value))
            header.append(edit); row.append(header)
            preview = NotePreview(vexpand=False); preview.add_css_class('study-note-preview')
            preview.set_source(note.body[:2000]+('…' if len(note.body)>2000 else ''))
            viewport = Gtk.ScrolledWindow(max_content_height=180, propagate_natural_height=True, vexpand=False,
                                         hscrollbar_policy=Gtk.PolicyType.NEVER)
            viewport.set_child(preview); row.append(viewport)
            date, exact = readable_date(note.modified)
            meta = Gtk.Label(label=tr('Modified')+': '+date+((' · '+' · '.join(note.labels)) if note.labels else ''),
                             xalign=0, wrap=True); meta.add_css_class('dim-label'); meta.add_css_class('caption')
            meta.set_tooltip_text(exact)
            row.append(meta); self.list.append(row)
        if len(self.rows)>self.note_limit:
            more=Gtk.Button(label=tr('Show more notes'))
            def show_more(*_):self.note_limit+=20; self.refresh(force=True)
            more.connect('clicked',show_more); self.list.append(more)
        self.clear(self.highlight_list)
        for mark in self.marks:
            row = Gtk.Box(spacing=6)
            swatch = Gtk.Label(); swatch.set_markup(f'<span foreground="{COLORS[mark["color"]][0]}">●</span>')
            row.append(swatch)
            intervals = self.annotations.positions(reader, mark['system'], mark['reference'], mark['reference'])
            ref = intervals[0][2]
            text = dict(reader.chapter(ref).verses).get(ref, '')
            label = Gtk.Label(label=passage_label(ref)+' — '+text, xalign=0, wrap=True, hexpand=True,
                              wrap_mode=Pango.WrapMode.WORD_CHAR, width_chars=1)
            label.set_tooltip_text(passage_label(mark['reference'], versification=mark['system'])+' · '+mark['resource'])
            row.append(label)
            menu = Gtk.MenuButton(icon_name='view-more-symbolic', tooltip_text=tr('Highlight actions'))
            self.colors(menu, mark=mark); row.append(menu); self.highlight_list.append(row)
        if not self.marks:
            self.highlight_list.append(Gtk.Label(label=tr('No highlights for this passage.'), xalign=0, wrap=True))
        self.colors(self.add_highlight, context=dict(self.context), reader=reader)

    def add_note(self, *_):
        if self.context:self.owner.edit_note(context=dict(self.context))

    def colors(self, menu, *, mark=None, context=None, reader=None):
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                      margin_start=8, margin_end=8, margin_top=8, margin_bottom=8)
        for color in [*COLORS, None] if mark else COLORS:
            button = Gtk.Button(label=tr(COLORS[color][1] if color else 'Remove highlight'))
            def choose(_, value=color, snapshot=dict(mark) if mark else dict(context)):
                try:
                    if mark:
                        system, refs, resource = snapshot['system'], [snapshot['reference']], snapshot['resource']
                    else:
                        system, resource = snapshot['versification'], snapshot['origin_translation']
                        key = reader.key(snapshot['start']); last = reader.key(snapshot['end']).getIndex(); refs = []
                        while key.getIndex() <= last:
                            if reader.has_reference(key.getOSISRef()):refs.append(key.getOSISRef())
                            if len(refs) > 1000:raise ValueError('Select at most 1000 verses')
                            key.increment()
                            if key.popError() != '\x00':break
                    self.owner.highlights.set(system, refs, value, resource)
                    popover.popdown(); self.owner.refresh_highlights()
                except (OSError, ValueError) as error:self.status.set_text(str(error))
            button.connect('clicked', choose); box.append(button)
        popover.set_child(box); menu.set_popover(popover)
