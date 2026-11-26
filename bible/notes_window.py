"""Native local note editor, labels, central list, and file-portal backups."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Gdk, Pango, Gio, GObject, GLib

from .book_names import display_name
from .i18n import LANGUAGE, tr
from .markdown import render
from .notes import clean_labels, parts, passage_order
from .highlights import COLORS


def passage_label(start, end=None, versification=None):
    """Format a canonical saved range for display without requiring the original module to be installed."""
    code, chapter, verse = parts(start)
    name = code
    try:
        import Sword

        key = Sword.VerseKey()
        key.setVersificationSystem(versification or "KJV")
        key.setAutoNormalize(False)
        key.setText(start)
        if key.popError() == "\x00" and key.getOSISBookName() == code:
            name = key.getBookName()
    except Exception:
        pass
    result = f"{display_name(code, name, LANGUAGE)} {chapter}:{verse}"
    if end and end != start:
        final = parts(end)
        result += "–" + (
            str(final[2])
            if final[:2] == (code, chapter)
            else f"{final[1]}:{final[2]}"
            if final[0] == code
            else passage_label(end, versification=versification)
        )
    return result


def buffer_text(view):
    if callable(getattr(view, "source", None)):
        return view.source()
    buffer = view.get_buffer()
    return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)


def message(parent, heading, body, accepted, canceled=None):
    """Present an explicit destructive confirmation, defaulting cancellation and retaining owner styling."""
    dialog = Adw.MessageDialog.new(parent, tr(heading), tr(body))
    if hasattr(parent, "reading_style"):
        dialog.add_css_class(parent.reading_style.scope + "-window")
    dialog.add_response("cancel", tr("Cancel"))
    dialog.add_response("confirm", tr("Confirm"))
    dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_default_response("cancel")
    dialog.set_close_response("cancel")
    dialog.connect(
        "response",
        lambda _, response: accepted()
        if response == "confirm"
        else canceled()
        if canceled
        else None,
    )
    dialog.present()
    return dialog


def metadata_row(title, icon):
    row = Adw.ActionRow(title=tr(title), use_markup=False)
    row.add_prefix(Gtk.Image(icon_name=icon))
    box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
    box.add_css_class("boxed-list")
    box.append(row)
    return row, box


class Labels(Gtk.Box):
    """Native label entry with explicit add/remove and normalized duplicate handling."""

    def __init__(self, existing, changed) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.values = []
        self.changed = changed
        self.flow = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            homogeneous=False,
            min_children_per_line=1,
            max_children_per_line=8,
        )
        self.row, header = metadata_row("Labels", "view-list-symbolic")
        self.flow.set_hexpand(True)
        self.append(header)
        self.append(self.flow)
        row = Gtk.Box(spacing=6)
        self.entry = Gtk.Entry(hexpand=True, placeholder_text=tr("Add a label"))
        self.entry.update_property([Gtk.AccessibleProperty.LABEL], [tr("Labels")])
        self.entry.connect("activate", lambda *_: self.add())
        row.append(self.entry)
        button = Gtk.Button(icon_name="list-add-symbolic", tooltip_text=tr("Add a label"))
        button.connect("clicked", lambda *_: self.add())
        row.append(button)
        self.add_menu = Gtk.MenuButton(
            label=tr("Add"),
            direction=Gtk.ArrowType.NONE,
            tooltip_text=tr("Add a label"),
            valign=Gtk.Align.CENTER,
        )
        self.add_menu.update_property([Gtk.AccessibleProperty.LABEL], [tr("Add a label")])
        pop = Gtk.Popover()
        row.set_margin_top(8)
        row.set_margin_bottom(8)
        row.set_margin_start(8)
        row.set_margin_end(8)
        choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        choices.append(row)
        self.suggestion_rows = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            margin_start=8,
            margin_end=8,
            margin_bottom=8,
        )
        choices.append(self.suggestion_rows)
        pop.set_child(choices)
        self.add_menu.set_popover(pop)
        self.row.add_suffix(self.add_menu)
        self.entry.connect("changed", lambda *_: self.refresh_suggestions())
        self.error = Gtk.Label(xalign=0, wrap=True)
        self.error.connect(
            "notify::label", lambda label, *_: label.set_visible(bool(label.get_text()))
        )
        self.error.set_visible(False)
        self.append(self.error)
        self.set_suggestions(existing)

    def set_suggestions(self, existing) -> None:
        self.suggestions = tuple(dict.fromkeys(label for label in existing if label.strip()))
        self.refresh_suggestions()

    def refresh_suggestions(self) -> None:
        """Show at most eight real unselected matching labels, without committing typed text."""
        from .book_names import normalized

        while self.suggestion_rows.get_first_child():
            self.suggestion_rows.remove(self.suggestion_rows.get_first_child())
        query = normalized(self.entry.get_text().strip())
        selected = {normalized(value) for value in self.values}
        for label in [
            s
            for s in self.suggestions
            if normalized(s).startswith(query) and normalized(s) not in selected
        ][:8]:
            button = Gtk.Button(label=label, halign=Gtk.Align.FILL)
            button.add_css_class("flat")
            button.connect(
                "clicked", lambda _, value=label: (self.entry.set_text(value), self.add())
            )
            self.suggestion_rows.append(button)

    def add(self) -> None:
        """Validate and explicitly commit a typed label, retaining an error instead of losing invalid input."""
        try:
            self.set_values(clean_labels([*self.values, self.entry.get_text()]))
            self.entry.set_text("")
            self.error.set_text("")
            self.changed()
            self.add_menu.popdown()
        except ValueError as error:
            self.error.set_text(tr(str(error)))

    def set_values(self, values) -> None:
        """Rebuild removable label chips and suggestions from the supplied editor values."""
        self.values = list(values)
        self.refresh_suggestions()
        self.flow.set_visible(bool(self.values))
        child = self.flow.get_first_child()
        while child:
            following = child.get_next_sibling()
            self.flow.remove(child)
            child = following
        for label in self.values:
            button = Gtk.Button(tooltip_text=tr("Remove label") + ": " + label)
            button.set_child(
                Gtk.Label(
                    label=f"{label} ×",
                    ellipsize=Pango.EllipsizeMode.END,
                    max_width_chars=20,
                    width_chars=1,
                )
            )
            button.connect("clicked", lambda _, value=label: self.remove(value))
            self.flow.append(button)

    def remove(self, label) -> None:
        self.set_values([value for value in self.values if value != label])
        self.changed()


class NoteEditor(Adw.Window):
    """Share the live Markdown editor between the popup and embedded Notes workspace.

    Widget access and autosave run on GTK's owner thread. Failed saves retain
    the draft; popup close/navigation remains guarded until save or discard.
    """

    def __init__(
        self,
        owner,
        note=None,
        context=None,
        explanation="",
        embedded: bool = False,
        compact: bool = False,
        open_passage=None,
    ) -> None:
        super().__init__(
            transient_for=owner,
            modal=True,
            title=tr("Edit note") if note else tr("New note"),
            default_width=700,
            default_height=600,
        )
        self.set_size_request(360, 360)
        self.owner, self.note = owner, note
        self.embedded = embedded
        self.compact = compact
        self.embedded_host = None
        self.dialog_parent = owner if embedded else self
        self.context = (
            dict(context)
            if context
            else {
                key: getattr(note, key)
                for key in (
                    "versification",
                    "start",
                    "end",
                    "origin_translation",
                    "origin_language",
                )
            }
        )
        if hasattr(owner, "reading_style"):
            from .application_surfaces import secondary_dialog

            secondary_dialog(self, owner)
        self.closed = False
        self._discard = False
        self._confirmation = None
        self.after_close = None
        self.autosave = False
        self._autosave_id = 0
        self._saved_status_id = 0
        self._saving = False
        self.connect("close-request", self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        header = Adw.HeaderBar()
        self.header = header
        header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        header.set_title_widget(
            Adw.WindowTitle(title=self.get_title()) if not embedded else Gtk.Box()
        )
        self.save_button = Gtk.Button(label=tr("Save"), visible=embedded)
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", lambda *_: self.save())
        if embedded:
            header.pack_end(self.save_button)
        if embedded:
            header.set_show_start_title_buttons(False)
            header.set_show_end_title_buttons(False)
            header.set_visible(False)
        layout.append(header)
        reference = Gtk.Label(
            label=passage_label(
                self.context["start"], self.context["end"], self.context["versification"]
            ),
            wrap=True,
            xalign=0,
            margin_start=16,
            margin_end=16,
            margin_top=8,
        )
        reference.add_css_class("heading")
        reference.set_hexpand(True)
        self.reference_row = Gtk.Box(spacing=8, margin_start=4, margin_end=12)
        self.reference_row.append(reference)
        layout.append(self.reference_row)
        self.open_button = None
        if open_passage is not None:
            self.open_button = Gtk.Button(
                icon_name="go-jump-symbolic",
                tooltip_text=tr("Open in Bible"),
                valign=Gtk.Align.CENTER,
            )
            self.open_button.add_css_class("flat")
            self.open_button.update_property([Gtk.AccessibleProperty.LABEL], [tr("Open in Bible")])
            self.open_button.connect("clicked", lambda *_: open_passage())
            self.reference_row.append(self.open_button)
        origin = self.context["origin_translation"]
        try:
            origin = owner.library.resource(origin).description
        except (ValueError, OSError):
            pass
        from .languages import language_name

        context_text = (
            origin + " · " + language_name(self.context["origin_language"]) + " · " + tr("Excerpt")
        )
        context_label = Gtk.Label(
            label=context_text,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            width_chars=1,
            xalign=0,
            margin_start=20,
            margin_end=20,
        )
        context_label.add_css_class("dim-label")
        context_label.set_tooltip_text(
            self.context["origin_translation"] + " · " + self.context["versification"]
        )
        context_label.add_css_class("caption")
        layout.append(context_label)
        excerpt_text = self.source_excerpt()
        self.excerpt = Gtk.Label(
            label=excerpt_text,
            xalign=0,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            width_chars=1,
            lines=2,
            ellipsize=Pango.EllipsizeMode.END,
            selectable=True,
            margin_start=16,
            margin_end=16,
        )
        self.excerpt.add_css_class("study-content")
        layout.append(self.excerpt)
        self.scripture_context = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
            margin_start=12,
            margin_end=12,
            margin_top=4,
        )
        self.scripture_context.add_css_class("note-scripture-context")
        for widget in (self.reference_row, context_label, self.excerpt):
            layout.remove(widget)
            widget.set_margin_start(0)
            widget.set_margin_end(0)
            widget.set_margin_top(0)
            self.scripture_context.append(widget)
        reference.set_margin_start(0)
        reference.set_margin_end(0)
        reference.set_margin_top(0)
        layout.insert_child_after(self.scripture_context, header)
        self.status = Gtk.Label(
            label=explanation,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            selectable=True,
            xalign=0,
            margin_start=12,
            margin_end=12,
        )
        layout.append(self.status)
        self.status.connect(
            "notify::label", lambda label, *_: label.set_visible(bool(label.get_text()))
        )
        self.status.set_visible(bool(explanation))
        note_heading = Gtk.Label(
            label=tr("My note"), xalign=0, margin_start=16, margin_end=16, margin_top=8
        )
        note_heading.add_css_class("heading")
        layout.append(note_heading)
        commands = Gtk.Box(spacing=4, margin_start=12, margin_end=12)
        self.format_buttons = {}
        for label, kind, glyph, icon in [
            ("Bold", "bold", "B", None),
            ("Italic", "italic", "I", None),
            ("Bulleted list", "bullet", None, "view-list-symbolic"),
            ("Numbered list", "number", "1.", None),
        ]:
            button = Gtk.Button(tooltip_text=tr(label))
            button.add_css_class("flat")
            if icon:
                button.set_icon_name(icon)
            else:
                title = Gtk.Label()
                title.set_markup(
                    "<b>B</b>" if glyph == "B" else "<i>I</i>" if glyph == "I" else glyph
                )
                button.set_child(title)
            button.update_property([Gtk.AccessibleProperty.LABEL], [tr(label)])
            button.connect("clicked", lambda _, value=kind: self.body.format(value))
            commands.append(button)
            self.format_buttons[kind] = button
        layout.append(commands)
        from .note_editing import NoteTextView

        self.body = NoteTextView(owner, self.context["versification"], self.guard_navigation)
        self.body.set_left_margin(10)
        self.body.set_right_margin(10)
        self.body.set_top_margin(14)
        self.body.set_bottom_margin(14)
        self.body.add_css_class("study-content")
        self.body.update_property([Gtk.AccessibleProperty.LABEL], [tr("Note text")])
        self.body.set_source(note.body if note else "")
        scroll = Gtk.ScrolledWindow(
            vexpand=False,
            min_content_height=96,
            max_content_height=240 if compact else 300,
            propagate_natural_height=True,
        )
        self.body_scroll = scroll
        scroll.set_child(self.body)
        layout.append(scroll)
        self.labels = Labels(owner.notes_store.labels(), lambda: None)
        self.labels.set_margin_start(12)
        self.labels.set_margin_end(12)
        self.labels.set_values(note.labels if note else [])
        self.writing = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=12, margin_end=12
        )
        for widget in (note_heading, commands, scroll):
            layout.remove(widget)
            widget.set_margin_start(0)
            widget.set_margin_end(0)
            widget.set_margin_top(0)
        if embedded:
            self.writing.append(note_heading)
        field = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        field.append(commands)
        field.append(scroll)
        self.writing_frame = Gtk.Frame(child=field, vexpand=True)
        self.writing.append(self.writing_frame)
        commands.add_css_class("toolbar")
        layout.append(self.writing)
        layout.append(self.labels)
        from .note_links import PassageLinks

        self.links = PassageLinks(
            owner,
            self.context,
            note.links if note else (),
            lambda: self.queue_autosave() if self.autosave else None,
        )
        self.links.set_margin_start(12)
        self.links.set_margin_end(12)
        layout.append(self.links)
        self.metadata_height = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)
        for widget in (self.labels.row, self.links.row):
            self.metadata_height.add_widget(widget)
        self.actions_menu = None
        self.delete_button = Gtk.Button(visible=bool(note))
        delete_content = Gtk.Box(spacing=8)
        delete_content.append(Gtk.Image(icon_name="user-trash-symbolic"))
        delete_content.append(Gtk.Label(label=tr("Delete note…")))
        self.delete_button.set_child(delete_content)
        self.delete_button.update_property([Gtk.AccessibleProperty.LABEL], [tr("Delete note…")])
        self.delete_button.add_css_class("flat")

        def delete(*_: object) -> None:
            if self.actions_menu:
                self.actions_menu.popdown()
            self.ask_delete()

        self.delete_button.connect("clicked", delete)
        self.delete_button.set_halign(Gtk.Align.START)
        self.delete_button.set_margin_start(12)
        self.delete_button.set_margin_top(8)
        layout.append(self.delete_button)
        self.embedded_content = layout
        if not embedded:
            self.use_window_layout()
        self._initial = (buffer_text(self.body), tuple(self.labels.values), self.links.values)
        if not embedded:
            self.enable_autosave()
            self.set_focus(self.body)

    def source_excerpt(self):
        """Read a bounded excerpt from the saved origin; keep the note usable if that source is unavailable."""
        from .reference_targets import local_excerpt

        try:
            resource = self.context["origin_translation"]
            owner = self.owner
            if resource not in owner.library.installed("bible"):
                raise ValueError("Missing original source")
            from .sword_provider import Reader

            tab = owner.active_tab
            reader = (
                tab.reader
                if tab and tab.state.resource == resource and tab.reader
                else Reader(owner.library.root / resource, resource)
            )
            return local_excerpt(
                reader,
                self.context["start"],
                self.context["end"],
                source_system=self.context["versification"],
                limit=1,
            ).text
        except (ValueError, OSError, RuntimeError):
            return tr("Original translation unavailable. Your note is kept.")

    def use_window_layout(self, *, expanded: bool = False) -> None:
        """Keep native window actions visible while short windows scroll the editor."""
        # Inline hosts hide title buttons. Restore the platform's native
        # controls when the same editor becomes a standalone window.
        self.header.set_decoration_layout(":close")
        self.header.set_show_start_title_buttons(False)
        self.header.set_show_end_title_buttons(True)
        layout = self.embedded_content
        layout.set_margin_top(0)
        layout.set_margin_bottom(0)
        if self.header.get_parent() is layout:
            layout.remove(self.header)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(self.header)
        # A standalone editor has one natural-height content scroller. Extra
        # window height must not stretch a short draft and displace metadata.
        for widget in (
            self.writing,
            self.writing_frame,
            self.writing_frame.get_child(),
            self.body_scroll,
            layout,
        ):
            widget.set_vexpand(False)
        layout.set_valign(Gtk.Align.START)
        self.body_scroll.set_max_content_height(-1)
        self.body_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        # Place insets *outside* the scrollable layout. Child margins were
        # consumed by the viewport and could disappear at both window edges.
        scroll.set_margin_top(4)
        self.scripture_context.set_margin_top(0)
        scroll.set_margin_bottom(16 if expanded else 12)
        scroll.set_child(layout)
        # The viewport must allocate natural content height; using its minimum
        # compresses the inner text view and creates a second competing scroll.
        scroll.get_child().set_vscroll_policy(Gtk.ScrollablePolicy.NATURAL)
        root.append(scroll)
        self.set_content(root)

    def guard_navigation(self, action) -> None:
        self.after_close = action
        self.close()

    def format(self, prefix, suffix: object) -> None:
        self.body.format("bold" if prefix == "**" else "italic" if prefix == "*" else "bullet")

    @property
    def dirty(self):
        return (
            buffer_text(self.body),
            tuple(self.labels.values),
            self.links.values,
        ) != self._initial or bool(
            self.labels.entry.get_text().strip() or self.links.entry.get_text().strip()
        )

    def enable_autosave(self) -> None:
        """Coalesce writes on GTK's owner thread; optimistic revisions still apply."""
        if self.autosave:
            return
        self.autosave = True
        self.body.get_buffer().connect("changed", lambda *_: self.queue_autosave())
        self.labels.changed = self.queue_autosave
        self.labels.entry.connect("changed", lambda *_: self.queue_autosave())
        self.links.entry.connect("changed", lambda *_: self.queue_autosave())

    def cancel_autosave(self) -> None:
        if self._autosave_id:
            GLib.source_remove(self._autosave_id)
            self._autosave_id = 0
        if self._saved_status_id:
            GLib.source_remove(self._saved_status_id)
            self._saved_status_id = 0

    def queue_autosave(self) -> None:
        """Queue one bounded600ms write window; continuous typing does not postpone it forever."""
        if self.closed or self._discard or self._saving:
            return
        # A continuous typing burst must not postpone every write forever.
        # Keep one bounded write window; schedule again only after later edits.
        if self._autosave_id:
            return
        if self._saved_status_id:
            GLib.source_remove(self._saved_status_id)
            self._saved_status_id = 0
        self.status.set_text(tr("Saving…"))
        self._autosave_id = GLib.timeout_add(600, self.autosave_pending)

    def autosave_pending(self):
        """Save a dirty draft unless an uncommitted label/passage still requires explicit Add."""
        self._autosave_id = 0
        if self.closed or self._discard:
            return False
        if not self.dirty:
            self.status.set_text(tr("Note saved.") if self.note else "")
            return False
        # Typing a label is not an implicit Add-label action. Keep the whole
        # draft and normal leave/save guards until the label is committed.
        if self.labels.entry.get_text().strip():
            self.status.set_text(tr("Press Enter to add the label before saving."))
            return False
        if self.links.entry.get_text().strip():
            self.status.set_text(tr("Press Enter to add the passage before saving."))
            return False
        self.save(close=False)
        return False

    def save(self, close: bool = True):
        """Validate and save the draft, retaining it on revision conflicts or storage failure.

        Returns:
            True after persistence succeeds; False while the draft still needs
            correction/retry. Successful saves update the editor's revision token.
        """
        if self.closed or self._discard:
            return False
        self.cancel_autosave()
        self._saving = True
        if self.links.entry.get_text().strip() and not self.links.add():
            self.status.set_text(self.links.error.get_text())
            self._saving = False
            return False
        if self.labels.entry.get_text().strip():
            self.labels.add()
            if self.labels.error.get_text():
                self._saving = False
                return False
        try:
            buffer = self.body.get_buffer()
            if not buffer.get_text(*buffer.get_bounds(), False).strip():
                raise ValueError(tr("Write some text before saving the note."))
            self.note = self.owner.notes_store.save(
                buffer_text(self.body),
                self.labels.values,
                links=self.links.values,
                existing=self.note,
                **self.context,
            )
            if self.actions_menu:
                self.actions_menu.set_visible(True)
            self.delete_button.set_visible(True)
            self._initial = (self.note.body, tuple(self.labels.values), self.note.links)
            host = self.embedded_host
            if host and hasattr(host, "note_saved"):
                host.note_saved(self)
            self.owner.notes_changed()
            self.status.set_text(tr("Note saved."))
            if self.autosave:

                def clear_saved():
                    self._saved_status_id = 0
                    if not self.closed and self.status.get_text() == tr("Note saved."):
                        self.status.set_text("")
                    return False

                self._saved_status_id = GLib.timeout_add(2000, clear_saved)
            if close:
                self.close()
            return True
        except Exception as error:
            self.status.set_text(
                (
                    tr("Unable to save this note. Your draft is kept.") + "\n"
                    if self.autosave
                    else ""
                )
                + tr(str(error))
            )
            return False
        finally:
            self._saving = False

    def ask_delete(self, *_: object) -> None:
        if self.note:
            self._confirmation = message(
                self.dialog_parent,
                "Delete this note permanently?",
                "This removes the note, its labels and all linked passages.",
                self.delete_confirmed,
            )

    def delete_confirmed(self) -> None:
        """Cancel pending autosave before revision-checked deletion so a callback cannot recreate the note."""
        self.cancel_autosave()
        try:
            self.owner.notes_store.delete(self.note)
            self._discard = True
            self.owner.notes_changed()
            self.close()
        except Exception as error:
            self.status.set_text(tr(str(error)))

    def present(self) -> None:
        if self.embedded:
            self.owner.present()
        else:
            super().present()

    def close(self):
        if not self.embedded:
            return super().close()
        if not self.on_close():
            host = self.embedded_host or getattr(self.owner, "notes_space", None)
            if host:
                host.editor_closed(self)
            self.destroy()

    def on_close(self, *_: object):
        """Flush autosave and keep the editor open if unsaved changes need an explicit decision."""
        if self.autosave and self.dirty and not self._discard:
            self.save(close=False)
        if self.dirty and not self._discard:
            if self._confirmation is None or not self._confirmation.get_visible():
                dialog = Adw.MessageDialog.new(
                    self.dialog_parent, tr("Unsaved changes"), tr("Save this note before leaving?")
                )
                dialog.add_response("cancel", tr("Keep editing"))
                dialog.add_response("discard", tr("Discard"))
                dialog.add_response("save", tr("Retry") if self.autosave else tr("Save"))
                dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
                dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
                dialog.set_default_response("save")
                dialog.set_close_response("cancel")

                def response(_: object, choice) -> None:
                    if choice in ("discard", "confirm"):
                        self._discard = True
                        self.close()
                    elif choice == "save":
                        if self.save(close=False):
                            self.close()
                    else:
                        self.after_close = None

                dialog.connect("response", response)
                dialog.present()
                self._confirmation = dialog
            return True
        self.cancel_autosave()
        self.closed = True
        if self.embedded_host and not self.embedded:
            self.embedded_host.editor_closed(self)
        if self.after_close:
            callback, self.after_close = self.after_close, None
            callback()
        return False


class NotesWindow(Adw.Window):
    """Legacy notes-only window retaining shared note-backup actions for existing callers."""

    def __init__(self, owner) -> None:
        super().__init__(
            transient_for=owner, title=tr("My notes"), default_width=720, default_height=700
        )
        self.add_css_class(owner.reading_style.scope + "-window")
        self.set_size_request(360, 360)
        self.owner = owner
        self.closed = False
        self.passage_filter = None
        self._related_filter_keys = None
        self.rows = []
        self._choosers = []
        self.connect("close-request", self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header = Adw.HeaderBar()
        header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        header.set_title_widget(Adw.WindowTitle(title=tr("My notes")))
        back = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text=tr("Back to reading"))
        back.connect("clicked", lambda *_: self.close())
        header.pack_start(back)
        menu = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text=tr("Backup and restore"))
        popover = Gtk.Popover()
        actions = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=12,
        )
        for label, save in [("Back up notes", True), ("Restore notes", False)]:
            button = Gtk.Button(label=tr(label))
            button.connect("clicked", lambda _, saving=save: self.choose_backup(saving))
            actions.append(button)
        popover.set_child(actions)
        menu.set_popover(popover)
        header.pack_end(menu)
        layout.append(header)
        self.search = Gtk.SearchEntry(
            placeholder_text=tr("Search notes or references"), margin_start=12, margin_end=12
        )
        self.search.update_property(
            [Gtk.AccessibleProperty.LABEL], [tr("Search notes or references")]
        )
        self.search.connect("search-changed", lambda *_: self.refresh())
        layout.append(self.search)
        self.sort = Gtk.DropDown(
            model=Gtk.StringList.new([tr("Most recent"), tr("Oldest first"), tr("Bible order")]),
            margin_start=12,
            margin_end=12,
        )
        self.sort.update_property([Gtk.AccessibleProperty.LABEL], [tr("Sort notes")])
        self.sort.connect("notify::selected", lambda *_: self.refresh())
        layout.append(self.sort)
        self.labels = Labels(owner.notes_store.labels(), self.refresh)
        self.labels.set_margin_start(12)
        self.labels.set_margin_end(12)
        layout.append(self.labels)
        self.all_passages = Gtk.Button(
            label=tr("All passages"), visible=False, margin_start=12, margin_end=12
        )
        self.all_passages.connect("clicked", lambda *_: self.show_all())
        layout.append(self.all_passages)
        self.status = Gtk.Label(
            xalign=0, wrap=True, selectable=True, margin_start=12, margin_end=12
        )
        layout.append(self.status)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.connect("row-activated", self.activate)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.list)
        layout.append(scroll)
        self.set_content(layout)
        self.refresh()

    def show_all(self) -> None:
        self.passage_filter = None
        self.refresh()

    def refresh(self) -> None:
        """Rebuild the legacy notes-only list from saved notes and explicit filters, reporting read failures."""
        if self.closed:
            return
        try:
            notes = self.owner.notes_store.search(
                self.search.get_text(),
                self.labels.values,
                ["recent", "oldest", "bible"][min(self.sort.get_selected(), 2)],
            )
            if self._related_filter_keys is not None:
                notes = [n for n in notes if ("note", n.id) in self._related_filter_keys]
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
                box = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL,
                    spacing=4,
                    margin_start=12,
                    margin_end=12,
                    margin_top=8,
                    margin_bottom=8,
                )
                title = (
                    passage_label(note.start, note.end, note.versification)
                    + f" [{note.versification}]"
                )
                for text in [
                    title,
                    render(note.body)[0][:160].replace("\n", " "),
                    " · ".join(note.labels),
                    f"{tr('Created')}: {note.created[:19]} · {tr('Modified')}: {note.modified[:19]}",
                ]:
                    box.append(
                        Gtk.Label(
                            label=text, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR
                        )
                    )
                self.list.append(box)
            self.all_passages.set_visible(self.passage_filter is not None)
            self.status.set_text(
                tr("No matching note.")
                if not notes
                else f"{len(notes)} {tr('note') if len(notes) == 1 else tr('notes')}"
            )
        except Exception as error:
            self.status.set_text(tr(str(error)))

    def activate(self, _: object, row) -> None:
        if 0 <= row.get_index() < len(self.rows):
            self.owner.open_saved_note(self.rows[row.get_index()])

    def choose_backup(self, save) -> None:
        """Use the native local-file chooser for notes-only export/restore and retain chooser lifetime."""
        chooser = Gtk.FileChooserNative.new(
            tr("Back up notes") if save else tr("Restore notes"),
            self.owner,
            Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN,
            tr("Save") if save else tr("Open"),
            tr("Cancel"),
        )
        filter = Gtk.FileFilter()
        filter.set_name(tr("Notes backup (JSON)"))
        filter.add_pattern("*.json")
        chooser.add_filter(filter)
        if save:
            chooser.set_current_name("bible-notes.json")

        def response(dialog, result) -> None:
            if result == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                path = file.get_path() if file else None
                if path:
                    self.backup_to(path) if save else self.restore_from(path)
                else:
                    self.status.set_text(tr("Choose a local file."))
            dialog.destroy()
            self._choosers.remove(dialog)

        chooser.connect("response", response)
        self._choosers.append(chooser)
        chooser.show()

    def backup_to(self, path):
        try:
            self.owner.notes_store.export(path)
            self.status.set_text(tr("Notes backup saved."))
            return True
        except Exception as error:
            self.status.set_text(tr(str(error)))
            return False

    def restore_from(self, path):
        """Merge a validated notes-only backup and report added/skipped/conflict-copy counts."""
        try:
            added, skipped, conflicts = self.owner.notes_store.restore(path)
            self.owner.notes_changed()
            self.status.set_text(
                f"{tr('Restore complete. Added / already present / copies kept')}: {added} / {skipped} / {conflicts}"
            )
            return True
        except Exception as error:
            self.status.set_text(tr(str(error)))
            return False

    def on_close(self, *_: object):
        self.closed = True
        for chooser in self._choosers[:]:
            chooser.destroy()
        return False


class LabelFilter(Gtk.Box):
    """Existing labels only: consultation never creates or mutates a label."""

    def __init__(self, existing, changed) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.values = []
        self.existing = list(existing)
        self.changed = changed
        self._updating = False
        self.button = Gtk.MenuButton(label=tr("Filter by label"))
        popover = Gtk.Popover()
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=12,
        )
        self.entry = Gtk.SearchEntry(placeholder_text=tr("Search labels"))
        self.entry.connect("search-changed", lambda *_: self.rebuild())
        self.entry.connect("activate", lambda *_: self.add())
        box.append(self.entry)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        scroll = Gtk.ScrolledWindow(
            min_content_height=160, max_content_height=300, propagate_natural_height=True
        )
        scroll.set_child(self.list)
        box.append(scroll)
        popover.set_child(box)
        self.button.set_popover(popover)
        self.append(self.button)
        self.chips = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=6)
        self.append(self.chips)
        self.rebuild()

    def set_suggestions(self, existing) -> None:
        self.existing = list(existing)
        self.rebuild()

    def set_values(self, values) -> None:
        from .notes import label_key

        known = {label_key(v): v for v in self.existing}
        self.values = [known[label_key(v)] for v in values if label_key(v) in known]
        self.rebuild()

    def add(self) -> None:
        self.set_values(self.values + [self.entry.get_text()])
        self.changed()

    def remove(self, label) -> None:
        self.set_values([v for v in self.values if v != label])
        self.changed()

    def rebuild(self) -> None:
        """Rebuild filter controls while suppressing synthetic toggle callbacks."""
        from .book_names import normalized

        self._updating = True
        for container in [self.list, self.chips]:
            child = container.get_first_child()
            while child:
                after = child.get_next_sibling()
                container.remove(child)
                child = after
        for label in self.existing:
            if normalized(self.entry.get_text()) not in normalized(label):
                continue
            button = Gtk.CheckButton(label=label, active=label in self.values)
            caption = button.get_child()
            if isinstance(caption, Gtk.Label):
                caption.set_wrap(True)
                caption.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
                caption.set_width_chars(1)
                caption.set_max_width_chars(24)

            def toggle(widget, value=label) -> None:
                if self._updating:
                    return
                self.values = (
                    list(dict.fromkeys(self.values + [value]))
                    if widget.get_active()
                    else [v for v in self.values if v != value]
                )
                GLib.idle_add(self.rebuild)
                self.changed()

            button.connect("toggled", toggle)
            self.list.append(button)
        for label in self.values:
            button = Gtk.Button(label=label + " ×", tooltip_text=tr("Remove filter"))
            button.connect("clicked", lambda _, value=label: self.remove(value))
            self.chips.append(button)
        self._updating = False


class NoteItem(GObject.Object):
    """A GObject list-model wrapper for an immutable saved note."""

    def __init__(self, note) -> None:
        super().__init__()
        self.note = note


def readable_date(value):
    """Format a stored timestamp for display, retaining unparseable input as text."""
    from datetime import datetime, timedelta
    from babel.dates import format_date, format_datetime

    local = datetime.fromisoformat(value).astimezone()
    today = datetime.now().astimezone().date()
    label = (
        tr("Today")
        if local.date() == today
        else tr("Yesterday")
        if local.date() == today - timedelta(days=1)
        else format_date(
            local.date(), format="long", locale="fr" if LANGUAGE.startswith("fr") else "en"
        )
    )
    exact = format_datetime(
        local, format="long", locale="fr" if LANGUAGE.startswith("fr") else "en"
    )
    return label, exact


class AnnotationItem(GObject.Object):
    """A GObject list-model wrapper for an independent annotation projection."""

    def __init__(self, annotation) -> None:
        super().__init__()
        self.annotation = annotation


class NotesSpace(Gtk.Box):
    """Adaptive projection over the existing note database and highlight file."""

    def __init__(self, owner) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.owner = owner
        self.closed = False
        self.rows = []
        self._choosers = []
        self.passage_filter = None
        self._related_filter_keys = None
        self.editor = None
        self.selected_key = None
        self.selected_annotation = None
        self.category = "all"
        self._detail_requested = False
        self._syncing = False
        self._wide = None
        self._reader_cache = {}
        self._excerpt_cache = {}
        self._version = None
        header = Adw.HeaderBar()
        header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        from .workspace_selector import WorkspaceSelector

        self.space_selector = WorkspaceSelector(owner, notes=True)
        header.pack_start(self.space_selector)
        self.workspace_title = Gtk.Label(
            label=tr("Notes and highlights"),
            ellipsize=Pango.EllipsizeMode.END,
            width_chars=1,
            max_width_chars=24,
            visible=owner.get_width() >= 760,
        )
        self.workspace_title.add_css_class("heading")
        header.set_title_widget(self.workspace_title)
        self.sidebar_button = Gtk.ToggleButton(
            icon_name="sidebar-show-symbolic", tooltip_text=tr("Show filters"), visible=False
        )
        self.sidebar_button.update_property([Gtk.AccessibleProperty.LABEL], [tr("Show filters")])
        self.sidebar_button.add_css_class("flat")
        header.pack_start(self.sidebar_button)
        from .application_surfaces import application_menu

        self.main_menu = application_menu()
        header.pack_end(self.main_menu)
        self.append(header)
        self.filters = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        self.categories = {}
        for key, title in [("all", "All"), ("notes", "Notes"), ("highlights", "Highlights")]:
            button = Gtk.ToggleButton()
            if self.categories:
                button.set_group(next(iter(self.categories.values())))
            button.connect(
                "clicked",
                lambda widget, value=key: self.set_category(value) if widget.get_active() else None,
            )
            self.categories[key] = button
            self.filters.append(button)
        self.categories["all"].set_active(True)
        self.books = [""]
        self.book = Gtk.DropDown(model=Gtk.StringList.new([tr("All books")]))
        self.book.update_property([Gtk.AccessibleProperty.LABEL], [tr("Book")])
        self.book.connect(
            "notify::selected", lambda *_: self.refresh() if not self._syncing else None
        )
        self.filters.append(self.book)
        self.labels = LabelFilter(owner.notes_store.labels(), self.refresh)
        self.filters.append(self.labels)
        self.color = Gtk.DropDown(
            model=Gtk.StringList.new(
                [tr("All colors"), *[tr(label) for _, label in COLORS.values()]]
            )
        )
        self.color.update_property([Gtk.AccessibleProperty.LABEL], [tr("Highlight color")])
        self.color.connect(
            "notify::selected", lambda *_: self.refresh() if not self._syncing else None
        )
        self.filters.append(self.color)
        filters_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        filters_scroll.set_child(self.filters)
        filters_scroll.add_css_class("annotation-navigation")
        self.side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tools = Gtk.Box(spacing=6, margin_start=12, margin_end=12, margin_top=12)
        self.search = Gtk.SearchEntry(placeholder_text=tr("Search annotations"), hexpand=True)
        self.search.connect("search-changed", lambda *_: self.refresh())
        tools.append(self.search)
        self.sort = Gtk.DropDown(
            model=Gtk.StringList.new([tr("Most recent"), tr("Oldest first"), tr("Bible order")])
        )
        from .version_chooser import bounded_choices

        for control in (self.book, self.color, self.sort):
            bounded_choices(control)
        self.sort.update_property([Gtk.AccessibleProperty.LABEL], [tr("Sort annotations")])
        self.sort.connect("notify::selected", lambda *_: self.refresh())
        tools.append(self.sort)
        self.side.append(tools)
        self.sort.set_tooltip_text(
            tr(
                "Date sorting uses annotation modification dates. Highlights without dates follow in Bible order."
            )
        )
        self.status = Gtk.Label(xalign=0, wrap=True, margin_start=12, margin_end=12)
        self.side.append(self.status)
        self.model = Gio.ListStore.new(AnnotationItem)
        self.selection = Gtk.SingleSelection(model=self.model, autoselect=False)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.row_setup)
        factory.connect("bind", self.row_bind)
        factory.connect("unbind", self.row_unbind)
        self.list = Gtk.ListView(model=self.selection, factory=factory, single_click_activate=True)
        self.list.connect("activate", self.activate)
        self.list.add_css_class("annotation-list")
        self.list.add_css_class("study-card-list")
        self.side.add_css_class("annotation-sidebar")
        keys = Gtk.EventControllerKey()

        def activate_space(_: object, key, code: object, state):
            if key != Gdk.KEY_space or state:
                return False
            index = self.selection.get_selected()
            if index == Gtk.INVALID_LIST_POSITION:
                return False
            self.activate(self.list, index)
            return True

        keys.connect("key-pressed", activate_space)
        self.list.add_controller(keys)
        self.scroll = Gtk.ScrolledWindow(vexpand=True)
        self.scroll.set_child(self.list)
        self.side.append(self.scroll)
        self.editor_panel = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, vexpand=True, margin_top=12, margin_bottom=16
        )  # The complete pane, including expanded links, scrolls inside these insets.
        detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        detail.add_css_class("annotation-detail")
        self.detail_back = Gtk.Button(
            label=tr("Back to annotations"),
            visible=False,
            halign=Gtk.Align.START,
            margin_start=12,
            margin_top=8,
        )
        self.detail_back.connect("clicked", lambda *_: self.back_to_list())
        detail.append(self.detail_back)
        self.detail_scroll = Gtk.ScrolledWindow(
            vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER
        )
        self.detail_scroll.set_overflow(Gtk.Overflow.HIDDEN)
        self.editor_panel.set_vexpand(True)
        self.detail_scroll.set_child(self.editor_panel)
        viewport = self.detail_scroll.get_child()
        if isinstance(viewport, Gtk.Viewport):
            viewport.set_scroll_to_focus(True)
        detail.append(self.detail_scroll)
        self.context_panel = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_start=20,
            margin_end=20,
            margin_top=12,
            visible=False,
        )
        self.highlight_heading = Gtk.Label(xalign=0, wrap=True, hexpand=True, width_chars=1)
        self.highlight_heading.add_css_class("title-2")
        self.highlight_menu = Gtk.MenuButton(tooltip_text=tr("Highlight actions"))
        self.highlight_menu.add_css_class("flat")
        self.open_button = Gtk.Button(label=tr("Open in Bible"), halign=Gtk.Align.START)
        self.open_button.add_css_class("flat")
        self.open_button.connect("clicked", lambda *_: self.open_passage())
        heading = Gtk.Box(spacing=8)
        heading.append(self.highlight_heading)
        heading.append(self.highlight_menu)
        heading.append(self.open_button)
        self.context_panel.append(heading)
        self.excerpt = Gtk.Label(
            wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0, selectable=True, width_chars=1
        )
        self.excerpt.add_css_class("study-content")
        self.excerpt_caption = Gtk.Label(
            wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0, width_chars=1
        )
        self.excerpt_caption.add_css_class("caption")
        self.excerpt_caption.add_css_class("dim-label")
        self.context_panel.append(self.excerpt_caption)
        self.context_panel.append(self.excerpt)
        self.highlight_detail = Adw.Clamp(
            child=self.context_panel, maximum_size=720, tightening_threshold=540, visible=False
        )
        self.editor_panel.append(self.highlight_detail)
        self.related = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=8, visible=False
        )
        self.related_section = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=12,
            margin_end=12,
            margin_top=8,
            margin_bottom=12,
            visible=False,
        )
        self.related_row, related_header = metadata_row(
            "Other annotations on this passage", "view-list-symbolic"
        )
        self.related_count = Gtk.Label()
        self.related_count.add_css_class("dim-label")
        self.related_row.add_suffix(self.related_count)
        self.related_toggle = Gtk.ToggleButton(
            icon_name="go-next-symbolic",
            valign=Gtk.Align.CENTER,
            tooltip_text=tr("Other annotations on this passage"),
        )
        self.related_toggle.add_css_class("flat")
        self.related_row.add_suffix(self.related_toggle)
        self.related_row.set_activatable_widget(self.related_toggle)
        self.related_toggle.connect(
            "toggled",
            lambda button: (
                self.related.set_visible(button.get_active()),
                button.set_icon_name(
                    "pan-down-symbolic" if button.get_active() else "go-next-symbolic"
                ),
            ),
        )
        self.related_section.append(related_header)
        self.related_section.append(self.related)
        self.editor_panel.append(self.related_section)
        self.placeholder = Adw.StatusPage(
            title=tr("Choose an annotation"),
            description=tr("Your annotations remain available offline."),
            icon_name="notebook-symbolic",
        )
        self.editor_panel.append(self.placeholder)
        list_pane = Gtk.Box()
        self.side.set_hexpand(True)
        list_pane.append(self.side)
        list_pane.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.split = Adw.OverlaySplitView(
            sidebar=list_pane,
            content=detail,
            min_sidebar_width=280,
            max_sidebar_width=380,
            sidebar_width_unit=Adw.LengthUnit.PX,
            sidebar_position=Gtk.PackType.START,
            show_sidebar=True,
            collapsed=True,
        )
        self.outer = Adw.OverlaySplitView(
            sidebar=filters_scroll,
            content=self.split,
            min_sidebar_width=210,
            max_sidebar_width=240,
            sidebar_width_unit=Adw.LengthUnit.PX,
            sidebar_position=Gtk.PackType.START,
            collapsed=True,
            show_sidebar=False,
        )
        self.sidebar_button.connect(
            "toggled", lambda widget: self.outer.set_show_sidebar(widget.get_active())
        )
        self.outer.connect(
            "notify::show-sidebar",
            lambda *_: self.sidebar_button.set_active(self.outer.get_show_sidebar()),
        )
        self.append(self.outer)
        self.add_tick_callback(self.adapt)
        self.refresh()

    def adapt(self, *_: object):
        """Switch collection/navigation/detail presentation at native width breakpoints without replacing the editor."""
        if self.closed:
            return False
        wide = self.get_width() >= 1120
        if wide != self._wide:
            self._wide = wide
            self.outer.set_collapsed(not wide)
            self.outer.set_show_sidebar(wide)
            self.sidebar_button.set_visible(not wide)
        collapsed = self.split.get_width() < 760
        self.workspace_title.set_visible(self.get_width() >= 760)
        if self.split.get_collapsed() != collapsed:
            self.split.set_collapsed(collapsed)
            self.split.set_show_sidebar(not self._detail_requested if collapsed else True)
        self.detail_back.set_visible(
            collapsed and (self.editor is not None or self._detail_requested)
        )
        return True

    def row_setup(self, _: object, item) -> None:
        """Create the reusable native row container for annotation cards."""
        item.set_child(
            Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                margin_start=8,
                margin_end=8,
                margin_top=4,
                margin_bottom=4,
            )
        )

    def card(self, a):
        """Build a shared source-aware annotation card with snapshot-checked highlight actions."""
        from .annotation_card import annotation_card, highlight_actions

        return annotation_card(
            self.owner,
            a,
            lambda: self.open_annotation(a),
            excerpt=self.excerpt_for(a, limit=1)[0] if a.mark else "",
            colors=lambda menu, mark: highlight_actions(
                menu,
                self.owner,
                mark,
                lambda _, color: self.change_highlight(a, color),
                self.status.set_text,
                confirm_remove=True,
            ),
        )

    def row_bind(self, _: object, item) -> None:
        self.row_unbind(None, item)
        item.get_child().append(self.card(item.get_item().annotation))

    def row_unbind(self, _: object, item) -> None:
        from .annotation_card import release_card

        box = item.get_child()
        card = box.get_first_child()
        if card:
            release_card(card)
            box.remove(card)

    def set_category(self, key) -> None:
        if self._syncing or key not in self.categories:
            return
        self.category = key
        self._syncing = True
        self.categories[key].set_active(True)
        self._syncing = False
        self.refresh()

    def show_all(self) -> None:
        self.passage_filter = None
        self._related_filter_keys = None
        self.set_category("all")

    def reveal(self, key) -> None:
        """An explicit passage-to-collection route reveals its actual record."""
        self._syncing = True
        self.passage_filter = None
        self._related_filter_keys = None
        self.category = "all"
        self.search.set_text("")
        self.labels.set_values([])
        self.book.set_selected(0)
        self.color.set_selected(0)
        self.categories["all"].set_active(True)
        self._syncing = False
        self.refresh()
        current = next((a for a in self.all_records if a.key == key), None)
        if current:
            self.open_annotation(current)

        def scroll():
            if not self.closed and self.selected_key == key:
                index = next((i for i, a in enumerate(self.rows) if a.key == key), None)
                if index is not None:
                    self.list.scroll_to(index, 0, None)
            return False

        GLib.idle_add(scroll)

    def refresh(self) -> None:
        """Refresh independent annotation rows/counts/filters while retaining the selected detail and list scroll.

        Missing/unreadable sources do not remove stored annotations. A live editor
        is not remounted by collection filtering or a saved-store notification.
        """
        if self.closed:
            return
        from .annotation_collection import records, filter_records
        from .highlights import COLORS
        from .notes import BOOK_ORDER

        try:
            items = records(self.owner.notes_store.all(), self.owner.highlights.entries.values())
            self.all_records = items
            if (
                self.selected_key
                and not any(a.key == self.selected_key for a in items)
                and (not self.editor or self.editor._discard)
            ):
                self.selected_key = None
                self.selected_annotation = None
                self._detail_requested = False
                self.context_panel.set_visible(False)
                self.highlight_detail.set_visible(False)
                self.placeholder.set_visible(True)
            current_book = self.books[min(self.book.get_selected(), len(self.books) - 1)]
            books = [""] + sorted(
                {parts(a.start)[0] for a in items},
                key=lambda code: (BOOK_ORDER.get(code, 10000), code),
            )
            names = {
                parts(a.start)[0]: passage_label(a.start, versification=a.system).rsplit(" ", 1)[0]
                for a in items
            }
            self._syncing = True
            if books != self.books:
                self.books = books
                self.book.set_model(
                    Gtk.StringList.new([tr("All books")] + [names[code] for code in books[1:]])
                )
                self.book.set_selected(books.index(current_book) if current_book in books else 0)
            note_count = sum(a.note is not None for a in items)
            for key, title, count in [
                (
                    "all",
                    "All",
                    str(note_count) + " + ?" if self.owner.highlights.error else len(items),
                ),
                ("notes", "Notes", note_count),
                (
                    "highlights",
                    "Highlights",
                    "?" if self.owner.highlights.error else sum(a.mark is not None for a in items),
                ),
            ]:
                self.categories[key].set_child(
                    Gtk.Label(
                        label=f"{tr(title)} ({count})",
                        wrap=True,
                        wrap_mode=Pango.WrapMode.WORD_CHAR,
                        width_chars=1,
                    )
                )
            self._syncing = False
            if self._related_filter_keys is not None:
                items = [a for a in items if a.key in self._related_filter_keys]
            if self.passage_filter:
                system, first, last = self.passage_filter
                items = [
                    a
                    for a in items
                    if a.system == system
                    and passage_order(a.start) <= passage_order(last)
                    and passage_order(a.end) >= passage_order(first)
                ]
            rows = filter_records(
                items,
                self.search.get_text(),
                self.labels.values,
                self.category,
                self.books[min(self.book.get_selected(), len(self.books) - 1)],
                ([""] + list(COLORS))[min(self.color.get_selected(), len(COLORS))],
                ["recent", "oldest", "bible"][min(self.sort.get_selected(), 2)],
                names,
            )
            self.refresh_versions()
            position = self.scroll.get_vadjustment().get_value()
            self.rows = rows
            self.model.splice(0, self.model.get_n_items(), [AnnotationItem(a) for a in rows])
            selected = next(
                (i for i, a in enumerate(rows) if a.key == self.selected_key),
                Gtk.INVALID_LIST_POSITION,
            )
            self.selection.set_selected(selected)

            def restore():
                if not self.closed:
                    self.scroll.get_vadjustment().set_value(position)
                return False

            GLib.idle_add(restore)
            self.status.set_text(
                tr("No matching annotations.")
                if not rows and self.all_records
                else tr("No annotations yet.")
                if not rows
                else ""
            )
            if self.owner.highlights.error:
                self.status.set_text(
                    tr("Highlights unavailable. The original file is preserved.")
                    + " "
                    + self.owner.highlights.error
                )
            self.refresh_versions()
        except Exception as error:
            self._syncing = False
            self.status.set_text(str(error))

    def refresh_versions(self) -> None:
        # The approved editor uses the recorded original translation. Never
        # substitute another Bible when that resource is unavailable.
        self._available_names = self.owner.library.installed("bible")
        if self.selected_annotation:
            self._version = self.selected_annotation.origin

    def reader(self, resource=None):
        """Reuse at most four installed source readers; return None for an unavailable module."""
        name = resource or self._version
        if not name or name not in self.owner.library.installed("bible"):
            return None
        if name not in self._reader_cache:
            from .sword_provider import Reader

            self._reader_cache[name] = Reader(self.owner.library.root / name, name)
            if len(self._reader_cache) > 4:
                self._reader_cache.pop(next(iter(self._reader_cache)))
        return self._reader_cache[name]

    def mapped_references(self, a, reader):
        """Validate and enumerate actual saved-range correspondences without guessing endpoint equivalence."""
        from .reference_resolution import resolve, _span

        # Imported annotations can contain structurally valid but unavailable
        # references. Validate in the established resolver before enumerating.
        resolve(a.start, a.system, reader)
        if a.end != a.start:
            resolve(a.end, a.system, reader)
        refs = []
        for source in dict.fromkeys(_span(a.start, a.end, a.system, reader)):
            if source.rsplit(".", 1)[-1] == "0":
                continue
            mapped = resolve(source, a.system, reader)
            for reference in _span(mapped.start, mapped.end, reader.versification, reader):
                if reference not in refs:
                    refs.append(reference)
        return refs

    def excerpt_for(self, a, limit=6):
        """Cache a bounded exact origin excerpt and label, or an explicit unavailable result."""
        key = (a.origin, a.system, a.start, a.end, limit)
        if key in self._excerpt_cache:
            return self._excerpt_cache[key]
        try:
            reader = self.reader(a.origin)
            if not reader:
                raise ValueError(
                    tr("Install a Bible to display this passage. Your annotation is kept.")
                )
            refs = self.mapped_references(a, reader)
            from .sword_provider import passage_verses

            text = [value for _, value in passage_verses(reader, refs[:limit])]
            from .reference_resolution import _span

            mapped_label = (
                passage_label(refs[0], refs[-1], reader.versification)
                if _span(refs[0], refs[-1], reader.versification, reader) == refs
                else "; ".join(
                    passage_label(ref, versification=reader.versification) for ref in refs
                )
            )
            description = (
                tr("Displayed in")
                + " "
                + self.owner.library.resource(a.origin).description
                + " · "
                + mapped_label
            )
            if len(refs) > limit:
                description += " · " + tr("Excerpt")
            result = ("\n".join(text), description, True)
        except (ValueError, OSError, IndexError) as error:
            result = (
                tr("Passage unavailable or no verified alignment.") + " " + str(error),
                tr("Original source") + ": " + a.origin + " · " + a.system,
                False,
            )
        self._excerpt_cache[key] = result
        if len(self._excerpt_cache) > 512:
            self._excerpt_cache.pop(next(iter(self._excerpt_cache)))
        return result

    def update_context(self, a) -> None:
        """Display original context and derive related overlaps without persisting note/highlight relationships."""
        from .annotation_card import original_caption, color_dot, highlight_actions, release_card

        if self.selected_key != a.key:
            self.related_toggle.set_active(False)
        self.selected_key = a.key
        self.selected_annotation = a
        self.context_panel.set_visible(not bool(a.note))
        self.placeholder.set_visible(False)
        selected = next(
            (i for i, row in enumerate(self.rows) if row.key == a.key), Gtk.INVALID_LIST_POSITION
        )
        self.selection.set_selected(selected)
        self._version = a.origin
        text, description, available = self.excerpt_for(a)
        self.excerpt.set_text(text)
        self.excerpt_caption.set_text(original_caption(self.owner, a))
        self.excerpt_caption.set_tooltip_text(description + " · " + a.origin + " · " + a.system)
        self.open_button.set_sensitive(available)
        if self.editor and self.editor.open_button:
            self.editor.open_button.set_sensitive(available)
        if a.mark:
            self.highlight_heading.set_text(passage_label(a.start, a.end, a.system))
            color_dot(self.highlight_menu, a.color)
            highlight_actions(
                self.highlight_menu,
                self.owner,
                a.mark,
                lambda _, color: self.change_highlight(a, color),
                self.status.set_text,
                confirm_remove=True,
            )
        while self.related.get_first_child():
            child = self.related.get_first_child()
            release_card(child)
            self.related.remove(child)
        try:
            reader = self.reader()
        except (ValueError, OSError):
            reader = None
        self.related_section.set_visible(False)
        if not reader:
            return
        from .passage_annotations import PassageAnnotations

        matching = PassageAnnotations(self.owner.library)
        try:
            spans = matching.positions(reader, a.system, a.start, a.end, a.origin)
            related = []
            for other in sorted(self.all_records, key=lambda item: item.origin):
                if other.key == a.key:
                    continue
                links = other.note.passages if other.note else (other,)
                if any(
                    matching.matches(
                        reader,
                        start,
                        end,
                        link.versification if other.note else link.system,
                        link.start,
                        link.end,
                        other.origin
                        if not other.note or link.versification == other.system
                        else None,
                    )
                    for _, _, start, end in spans
                    for link in links
                ):
                    related.append(other)
        except ValueError:
            related = []
        if related:
            self.related_count.set_text(str(len(related)))
            self.related_section.set_visible(True)
            for other in related[:20]:
                self.related.append(self.card(other))
            if len(related) > 20:
                button = Gtk.Button(label=tr("See all"))
                button.add_css_class("flat")

                def see_all(*_: object) -> None:
                    self._related_filter_keys = {other.key for other in related}
                    self.passage_filter = None
                    self.search.set_text("")
                    self.labels.set_values([])
                    self.book.set_selected(0)
                    self.color.set_selected(0)
                    self.set_category("all")
                    self.split.set_show_sidebar(True)

                button.connect("clicked", see_all)
                self.related.append(button)

    def guard(self, action) -> None:
        editor = self.owner.note_editor
        if editor and not editor.closed:
            editor.after_close = action
            editor.close()
        else:
            action()

    def activate(self, _: object, index) -> None:
        if 0 <= index < len(self.rows):
            self.open_annotation(self.rows[index])

    def open_annotation(self, a):
        """Open a note or highlight detail through the unsaved-draft navigation guard."""
        if a.note:
            return self.open_note(a.note)

        def show() -> None:
            self._detail_requested = True
            self.update_context(a)
            self.highlight_detail.set_visible(True)
            if self.split.get_collapsed():
                self.split.set_show_sidebar(False)

        self.guard(show)

    def change_highlight(self, a, color) -> None:
        """Reject a stale card snapshot before recolor/removal and retain independent notes."""
        try:
            key = (a.system, a.start)
            if self.owner.highlights.entries.get(key) != a.mark:
                raise ValueError(tr("This highlight changed elsewhere. Reopen it before editing."))
            selected = self.selected_key == a.key
            self.owner.highlights.set(a.system, [a.start], color, a.origin)
            self.owner.refresh_highlights()
            if not selected:
                return
            if color:
                current = next(item for item in self.all_records if item.key == a.key)
                self.open_annotation(current)
            else:
                self.selected_key = None
                self.selected_annotation = None
                self._detail_requested = False
                self.context_panel.set_visible(False)
                self.highlight_detail.set_visible(False)
                self.placeholder.set_visible(True)
                self.split.set_show_sidebar(True)
        except (ValueError, OSError) as error:
            self.status.set_text(str(error))

    def open_note(self, note):
        """Reuse the current note editor or guard navigation before loading the latest saved revision."""
        if (
            self.editor
            and not self.editor.closed
            and self.editor.note
            and self.editor.note.id == note.id
        ):
            return self.editor
        self.guard(lambda: self.mount(note=self.owner.notes_store.get(note.id)))
        return self.editor

    def mount(self, note):
        """Embed the shared editor and attach source/related context without replacing its undo/autosave model."""
        if note is None:
            return
        editor = NoteEditor(self.owner, note=note, embedded=True, open_passage=self.open_passage)
        editor.embedded_host = self
        editor.embedded_content.set_vexpand(True)
        editor.writing.set_vexpand(True)
        editor.body_scroll.set_vexpand(True)
        self.editor = editor
        self.owner.note_editor = editor
        self._detail_requested = True
        editor.enable_autosave()
        self.highlight_detail.set_visible(False)
        self.placeholder.set_visible(False)
        self.editor_panel.insert_child_after(editor.embedded_content, self.highlight_detail)
        from .annotation_collection import records

        self.related_section.get_parent().remove(self.related_section)
        editor.embedded_content.insert_child_after(self.related_section, editor.links)
        self.update_context(records([note], [])[0])
        if self.split.get_collapsed():
            self.split.set_show_sidebar(False)
        self.detail_back.set_visible(self.split.get_collapsed())

        def focus():
            if self.editor is editor and not editor.closed and editor.body.get_mapped():
                # Start at the detail's context, keeping its first controls
                # visible instead of scrolling a short window to the editor.
                (
                    self.detail_back if self.split.get_collapsed() else editor.open_button
                ).grab_focus()
                self.detail_scroll.get_vadjustment().set_value(0)
            return False

        GLib.idle_add(focus)
        return editor

    def editor_closed(self, editor) -> None:
        """Detach the closed editor's widgets while returning shared context controls to the workspace."""
        self.related_section.get_parent().remove(self.related_section)
        self.editor_panel.insert_child_after(self.related_section, self.highlight_detail)
        parent = editor.embedded_content.get_parent()
        if parent:
            parent.remove(editor.embedded_content)
        if self.editor is editor:
            self.editor = None
            if not editor.note:
                self._detail_requested = False
                self.placeholder.set_visible(True)

    def note_saved(self, editor) -> None:
        if self.editor is editor and editor.note:
            from .annotation_collection import records

            self.update_context(records([editor.note], [])[0])

    def leave(self) -> None:
        self.guard(self.owner.return_to_reading)

    def back_to_list(self) -> None:
        def show() -> None:
            self._detail_requested = False
            self.split.set_show_sidebar(True)

        self.guard(show)

    def open_passage(self) -> None:
        """Navigate to a verified origin target only after pending note edits can safely be left."""
        if not self.selected_annotation:
            return
        a = self.selected_annotation

        def go() -> None:
            try:
                reader = self.reader()
                refs = self.mapped_references(a, reader)
                tab = self.owner.active_tab
                same = (
                    tab and tab.state.resource == self._version and tab.state.reference == refs[0]
                )
                if same or self.owner.navigate_selection(self._version, refs[0], new_tab=True):
                    self.owner.main_pages.set_visible_child_name("reading")
            except (ValueError, OSError, AttributeError) as error:
                self.status.set_text(str(error))

        self.guard(go)

    def present(self) -> None:
        self.owner.main_pages.set_visible_child_name("notes")
        self.owner.present()
        if self._detail_requested and self.selected_key and not self.editor:
            current = next((a for a in self.all_records if a.key == self.selected_key), None)
            if current:
                self.open_annotation(current)

    def close(self) -> None:
        self.leave()

    def set_default_size(self, width, height) -> None:
        self.owner.set_default_size(width, height)

    def flush_for_backup(self):
        """Persist a pending editor draft before backup, returning False to block an unsafe export."""
        if (
            self.editor
            and not self.editor.closed
            and self.editor.dirty
            and not self.editor.save(close=False)
        ):
            self.status.set_text(self.editor.status.get_text())
            return False
        return True

    def choose_backup(self, save):
        if self.flush_for_backup():
            return NotesWindow.choose_backup(self, save)

    def backup_to(self, path):
        return bool(self.flush_for_backup() and NotesWindow.backup_to(self, path))

    def restore_from(self, path):
        return bool(self.flush_for_backup() and NotesWindow.restore_from(self, path))

    def choose_highlight_backup(self, restore) -> None:
        """Choose a local standalone highlight backup and confirm a merge before restoring."""
        chooser = Gtk.FileChooserNative.new(
            tr("Restore highlights") if restore else tr("Back up highlights"),
            self.owner,
            Gtk.FileChooserAction.OPEN if restore else Gtk.FileChooserAction.SAVE,
            tr("Open") if restore else tr("Save"),
            tr("Cancel"),
        )
        if not restore:
            chooser.set_current_name("Bible-highlights.json")
        self._choosers.append(chooser)

        def response(dialog, result) -> None:
            if result == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                path = file.get_path() if file else None

                def apply() -> None:
                    try:
                        if not path:
                            raise ValueError(tr("Choose a local file."))
                        if restore:
                            self.owner.highlights.restore(path)
                            self.owner.refresh_highlights()
                            self.refresh()
                        else:
                            self.owner.highlights.backup(path)
                        self.status.set_text(tr("Done"))
                    except (ValueError, OSError) as error:
                        self.status.set_text(str(error))

                if restore:
                    message(
                        self.owner,
                        "Restore highlights?",
                        "Merge the backup with existing highlights. Notes and translations are unchanged.",
                        apply,
                    )
                else:
                    apply()
            dialog.destroy()
            self._choosers.remove(dialog)

        chooser.connect("response", response)
        chooser.show()
