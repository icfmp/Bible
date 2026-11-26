"""Searchable language picker: CLDR/ISO names, native names and exact source codes."""

from __future__ import annotations

from gi.repository import Gtk, GLib, Pango
from .book_names import normalized
from .languages import language_name, language_info, search_terms
from .i18n import tr


class LanguagePicker(Gtk.MenuButton):
    """Present exact provider language codes with searchable localized/native labels."""

    def __init__(self, changed) -> None:
        super().__init__(label=tr("All languages"))
        self.changed = changed
        self.prepare_languages = None
        self.codes = [""]
        self.selected = 0
        self.visible_codes = [""]
        self.prepared = {}
        self.priority = []
        self._first_other = None
        self._bound_rows = set()
        self._model_generation = 0
        self._desired_labels = []
        self._label_codes = {}
        popover = Gtk.Popover()
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        self.search = Gtk.SearchEntry(placeholder_text=tr("Search languages"))
        self.search.update_property([Gtk.AccessibleProperty.LABEL], [tr("Search languages")])
        self.search.connect("search-changed", self.filter)
        self.search.connect("stop-search", lambda *_: self.popdown())
        box.append(self.search)
        self.strings = Gtk.StringList.new([])
        self.selection = Gtk.SingleSelection(model=self.strings, autoselect=False)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.setup_row)
        factory.connect("bind", self.bind_row)
        factory.connect("unbind", lambda _, item: self._bound_rows.discard(item))
        self.list = Gtk.ListView(model=self.selection, factory=factory, single_click_activate=True)
        self.list.connect("activate", self.activate)
        scroll = Gtk.ScrolledWindow(
            min_content_width=260,
            min_content_height=250,
            max_content_height=380,
            propagate_natural_height=True,
        )
        scroll.set_child(self.list)
        box.append(scroll)
        popover.set_child(box)
        self.set_popover(popover)
        popover.connect(
            "show",
            lambda *_: (
                self.prepare_languages() if self.prepare_languages else None,
                self.filter(force=True),
                self.search.grab_focus(),
            ),
        )
        self.filter()

    def setup_row(self, _: object, item) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        item.divider = Gtk.Separator(margin_top=4, margin_bottom=4, visible=False)
        item.label = Gtk.Label(xalign=0, wrap=True, margin_top=8, margin_bottom=8)
        box.append(item.divider)
        box.append(item.label)
        item.set_child(box)

    def bind_row(self, _: object, item) -> None:
        self._bound_rows.add(item)
        text = item.get_item().get_string()
        item.label.set_text(text)
        code = self._label_codes.get(text)
        grouped = not self.search.get_text() and bool(self.priority)
        first_other = self._first_other
        item.divider.set_visible(grouped and code == first_other)
        group = (
            tr("Common languages")
            if grouped and code == self.priority[0]
            else tr("Other languages")
            if grouped and code == first_other
            else ""
        )
        item.label.update_property([Gtk.AccessibleProperty.DESCRIPTION], [group])

    def set_codes(self, codes, prepared=None, *, priority=()) -> None:
        """Replace available codes/prepared labels while retaining the selected code when possible."""
        if (
            codes == self.codes
            and (prepared or {}) == self.prepared
            and list(priority) == self.priority
        ):
            return
        selected = self.codes[self.selected] if self.selected < len(self.codes) else ""
        self.codes = codes
        self.prepared = prepared or {}
        self.priority = list(priority)
        self._first_other = next(
            (code for code in codes if code and code not in self.priority), None
        )
        self.selected = codes.index(selected) if selected in codes else 0
        self.set_label(self.name(self.codes[self.selected]))
        self.filter()

    def cancel_pending(self) -> None:
        self._model_generation += 1

    def set_label(self, value) -> None:
        """Update the visible/accessibility caption while constraining nested native labels."""
        Gtk.MenuButton.set_label(self, value)
        self.set_tooltip_text(value)
        self.update_property([Gtk.AccessibleProperty.LABEL], [tr("Language") + ": " + value])

        def bound(widget) -> None:
            if isinstance(widget, Gtk.Label):
                widget.set_ellipsize(Pango.EllipsizeMode.END)
                widget.set_max_width_chars(18)
                widget.set_width_chars(1)
            child = widget.get_first_child()
            while child:
                bound(child)
                child = child.get_next_sibling()

        child = self.get_child()
        if child:
            bound(child)

    def get_selected(self):
        return self.selected

    def set_selected(self, index) -> None:
        self.selected = index if 0 <= index < len(self.codes) else 0
        code = self.codes[self.selected]
        self.set_label(self.name(code))
        self.changed()

    def filter(self, *_: object, force: bool = False) -> None:
        """Patch the filtered model in bounded GTK idle batches, invalidating superseded updates.

        Delay unqueried hidden-list population; preserve exact source codes even
        when displayed language names coincide.
        """
        query = normalized(self.search.get_text())
        if query and self.prepare_languages:
            self.prepare_languages()
        self.visible_codes = [
            code
            for code in self.codes
            if not code
            or query
            in (self.prepared[code][2] if code in self.prepared else normalized(search_terms(code)))
        ]
        # Prepare source-backed choices without building hidden GTK rows during
        # Library's first paint. Open/search binds the native model lazily.
        if not force and not query and not self.get_popover().get_visible():
            return
        labels = [
            self.prepared[code][1]
            if code in self.prepared
            else self.display_language(code)
            if code
            else tr("All languages")
            for code in self.visible_codes
        ]
        self._label_codes = dict(zip(labels, self.visible_codes))
        for item in tuple(self._bound_rows):
            if item.get_item():
                self.bind_row(None, item)
        if labels == self._desired_labels:
            return
        self._desired_labels = labels
        self._model_generation += 1
        generation = self._model_generation
        previous = [self.strings.get_string(i) for i in range(self.strings.get_n_items())]
        prefix = 0
        while prefix < min(len(previous), len(labels)) and previous[prefix] == labels[prefix]:
            prefix += 1
        suffix = 0
        while (
            suffix < min(len(previous), len(labels)) - prefix
            and previous[-1 - suffix] == labels[-1 - suffix]
        ):
            suffix += 1
        remove = len(previous) - prefix - suffix
        add = labels[prefix : len(labels) - suffix if suffix else len(labels)]
        offset = 0

        def update():
            nonlocal remove, offset
            if generation != self._model_generation:
                return False
            # Bound native row rebinding as catalogues progressively add languages.
            if remove:
                count = min(remove, 16)
                self.strings.splice(prefix + remove - count, count, [])
                remove -= count
            elif offset < len(add):
                batch = add[offset : offset + 16]
                self.strings.splice(prefix + offset, 0, batch)
                offset += len(batch)
            return bool(remove or offset < len(add))

        if update():
            GLib.idle_add(update)

    def name(self, code):
        value = (
            self.prepared[code][0]
            if code in self.prepared
            else language_name(code)
            if code
            else tr("All languages")
        )
        return value[:1].upper() + value[1:]

    @staticmethod
    def display_language(code):
        """Combine localized/native names and the exact source code for an explicit language choice."""
        name, native = language_info(code)
        name = name[:1].upper() + name[1:]
        native = native[:1].upper() + native[1:]
        return (
            name
            + ((" — " + native) if native and native.casefold() != name.casefold() else "")
            + f" ({code})"
        )

    def activate(self, _: object, index) -> None:
        # During a bounded update, retained suffix rows may have old indexes.
        # Resolve the actual displayed row, never a future model position.
        code = self._label_codes.get(self.strings.get_string(index))
        if code is not None and code in self.codes:
            self.set_selected(self.codes.index(code))
            self.popdown()
