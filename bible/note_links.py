"""Explicit offline passage relationships; body citations are never auto-linked."""

import re
from gi.repository import Gtk, Pango, GLib
from .i18n import tr
from .notes import PassageLink, validate_link, BOOK_ORDER
from .citations import grammar, fold


def parse_link(text, system):
    """Parse canonical/localized offline input into a validated explicit same-system passage range."""
    text = text.strip()
    canonical = re.fullmatch(
        r"([1-5]?[A-Za-z][A-Za-z0-9]*\.[0-9]+(?:_[0-9]+)?\.[0-9]+)(?:\s*[-–]\s*([1-5]?[A-Za-z][A-Za-z0-9]*\.[0-9]+(?:_[0-9]+)?\.[0-9]+))?",
        text,
    )
    if canonical:
        start, end = canonical[1], canonical[2] or canonical[1]
    else:
        pattern, names = grammar()
        value = fold(text)[0]
        match = pattern.fullmatch(value)
        if not match:
            raise ValueError(tr("Enter a passage such as John 3:16–18."))
        from .book_names import normalized

        book = names.get(normalized(match["name"]))
        if not book:
            raise ValueError(tr("Enter a passage such as John 3:16–18."))
        start = f"{book}.{match['chapter']}.{match['verse']}"
        end = f"{book}.{match['end_chapter'] or match['chapter']}.{match['end_verse'] or match['verse']}"
    link = validate_link(PassageLink(system, start, end))
    if start.split(".")[0] not in BOOK_ORDER:
        raise ValueError(tr("Unknown Bible book."))
    return link


class PassageLinks(Gtk.Box):
    """Edit explicit secondary note anchors independently of body citations and resource availability."""

    def __init__(self, owner, context, values, changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.owner = owner
        self.context = context
        self.values = tuple(values)
        self.changed = changed
        self._suggestion_epoch = 0
        self._suggestion_future = None
        self._excerpts = {}
        self._chapter_cache = {}
        self.primary = PassageLink(context["versification"], context["start"], context["end"])
        from .notes_window import metadata_row

        self.row, header = metadata_row("Linked passages", "insert-link-symbolic")
        self.rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.revealer = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.NONE)
        self.revealer.set_child(self.rows)
        self.disclosure = Gtk.ToggleButton(
            icon_name="pan-down-symbolic",
            tooltip_text=tr("Show linked passages"),
            valign=Gtk.Align.CENTER,
        )
        self.disclosure.add_css_class("flat")
        self.disclosure.connect(
            "toggled", lambda button: self.revealer.set_reveal_child(button.get_active())
        )
        self.row.add_suffix(self.disclosure)
        self.add_button = Gtk.MenuButton(
            label=tr("Add"),
            direction=Gtk.ArrowType.NONE,
            tooltip_text=tr("Add a linked passage"),
            valign=Gtk.Align.CENTER,
        )
        self.add_button.update_property(
            [Gtk.AccessibleProperty.LABEL], [tr("Add a linked passage")]
        )
        pop = Gtk.Popover()
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=12,
        )
        self.entry = Gtk.Entry(placeholder_text=tr("John 3:16–18"), width_chars=18)
        self.entry.update_property([Gtk.AccessibleProperty.LABEL], [tr("Linked passage")])
        self.entry.connect("activate", lambda *_: self.add())
        box.append(self.entry)
        hint = Gtk.Label(
            label=tr(
                "Numbering follows the original passage. Availability is checked when opening."
            ),
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            max_width_chars=32,
            xalign=0,
        )
        hint.add_css_class("caption")
        box.append(hint)
        add = Gtk.Button(label=tr("Add"))
        add.connect("clicked", lambda *_: self.add())
        box.append(add)
        self.suggestions = Gtk.Expander(label=tr("Suggested passages"), visible=False)
        self.suggestion_rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        suggestions_scroll = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            max_content_height=180,
            propagate_natural_height=True,
        )
        suggestions_scroll.set_child(self.suggestion_rows)
        self.suggestions.set_child(suggestions_scroll)
        box.append(self.suggestions)
        self.error = Gtk.Label(wrap=True, max_width_chars=32, xalign=0)
        box.append(self.error)
        outer = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            max_content_height=max(160, min(420, owner.get_height() - 100)),
            propagate_natural_height=True,
        )
        outer.set_child(box)
        pop.set_child(outer)
        self.add_button.set_popover(pop)
        self.row.add_suffix(self.add_button)
        self.append(header)
        self.append(self.revealer)

        def shown(*_):
            root = self.get_root() or owner
            outer.set_max_content_height(max(120, min(420, root.get_height() - 100)))
            outer.set_propagate_natural_width(True)
            outer.set_min_content_width(-1)
            outer.set_max_content_width(max(160, min(340, root.get_width() - 64)))
            outer.set_min_content_width(max(160, min(280, root.get_width() - 64)))
            self.load_suggestions(pop)

        pop.connect("show", shown)

        def hidden(*_):
            self._suggestion_epoch += 1
            if self._suggestion_future:
                self._suggestion_future.cancel()
                self._suggestion_future = None

        pop.connect("unmap", hidden)
        self.refresh()

    def load_suggestions(self, pop):
        """Optional existing reference data; manual entry never waits on it."""
        self._suggestion_epoch += 1
        epoch = self._suggestion_epoch
        if self._suggestion_future:
            self._suggestion_future.cancel()
        self.suggestions.set_visible(False)
        while self.suggestion_rows.get_first_child():
            self.suggestion_rows.remove(self.suggestion_rows.get_first_child())
        panel = self.owner.study.references
        if panel.data.revision is None:
            return
        try:
            from .reference_targets import source_references

            reader = self.suggestion_reader()
            if reader.versification != self.context["versification"]:
                return
            origins = source_references(reader, self.primary.start, self.primary.end)
        except (ValueError, OSError, RuntimeError):
            return
        future = panel.executor.submit(panel.data.query, origins)
        self._suggestion_future = future

        def complete():
            if self.owner.closed or epoch != self._suggestion_epoch or not pop.get_visible():
                return False
            self._suggestion_future = None
            try:
                rows = future.result()
            except (ValueError, OSError, RuntimeError):
                return False
            try:
                reader = self.suggestion_reader()
            except (ValueError, OSError, RuntimeError):
                return False
            from .reference_targets import local_target_ranges
            from .notes_window import passage_label as passage_label

            choices = []
            for result in rows:
                try:
                    ranges = local_target_ranges(reader, result.start, result.end)
                except ValueError:
                    continue
                for start, end in ranges:
                    link = PassageLink(reader.versification, start, end)
                    if link != self.primary and link not in self.values and link not in choices:
                        choices.append(link)
                if len(choices) >= 8:
                    break
            for link in choices[:8]:
                button = self.card(link, reader=reader if hasattr(reader, "root") else None)

                def choose(*_, value=link):
                    self.entry.set_text(
                        value.start + ("–" + value.end if value.end != value.start else "")
                    )
                    self.add()

                button.connect("clicked", choose)
                button._linked_passage = link
                self.suggestion_rows.append(button)
            if choices:
                from .reference_data import SOURCE_URL, LICENSE_URL
                from .source_credit import source_credit

                self.suggestion_rows.append(
                    source_credit("OpenBible.info · CC BY 4.0\n" + SOURCE_URL + "\n" + LICENSE_URL)
                )
                self.suggestions.set_visible(True)
            return False

        future.add_done_callback(lambda _: GLib.idle_add(complete))

    def suggestion_reader(self):
        """Use the installed origin reader or a canon-only key space that supplies no invented excerpt."""
        origin = self.context["origin_translation"]
        if origin in self.owner.library.installed("bible"):
            from .passage_annotations import PassageAnnotations

            return PassageAnnotations(self.owner.library).source_reader(None, origin)
        # Relationships may still be queried in a registered saved canonical
        # numbering system. Canon supplies no Scripture and never a preview.
        from .reference_targets import Canon

        return Canon(self.context["versification"])

    def card(self, link, reader=None, *, compound=False):
        """The saved origin is the only source of Scripture in this editor."""
        from .passage_card import passage_card
        from .notes_window import passage_label

        card = passage_card(compound=compound)
        title, text = card._reference_labels
        title.set_text(passage_label(link.start, link.end, link.versification))
        origin = self.context["origin_translation"]
        root = self.owner.library.root / origin
        try:
            if reader is None:
                from .passage_annotations import PassageAnnotations

                reader = PassageAnnotations(self.owner.library).source_reader(None, origin)
            revision = (root / ".complete").stat().st_mtime_ns
            key = (origin, revision, link)
            if key not in self._excerpts:
                from .passage_annotations import PassageAnnotations

                spans = PassageAnnotations(self.owner.library).positions(
                    reader,
                    link.versification,
                    link.start,
                    link.end,
                    origin if link.versification == self.context["versification"] else None,
                )
                if not spans:
                    raise ValueError("No verified passage correspondence")
                from .reference_resolution import _span
                from .sword_provider import passage_verses

                # A card needs only a short excerpt, even for a book-long link.
                first, last = spans[0][2:]
                references = (
                    reader.reference_range(first, last)
                    if reader.addresses
                    else _span(first, last, reader.versification, reader)
                )
                verses = list(passage_verses(reader, references[:3], self._chapter_cache))
                if not verses:
                    raise ValueError("No source excerpt")
                self._excerpts[key] = (
                    " ".join(" ".join(value.split()) for _, value in verses),
                    spans[0][2],
                    reader.rtl,
                )
                if len(self._excerpts) > 64:
                    self._excerpts.pop(next(iter(self._excerpts)))
                if len(self._chapter_cache) > 8:
                    self._chapter_cache.clear()
            excerpt, target, rtl = self._excerpts[key]
            text.set_text(excerpt)
            text.set_direction(Gtk.TextDirection.RTL if rtl else Gtk.TextDirection.LTR)
            text.set_xalign(1 if rtl else 0)
            card._target = (origin, target)
        except (ValueError, OSError, RuntimeError):
            text.set_text(tr("Bible excerpt unavailable."))
            card._target = None
        card.update_property([Gtk.AccessibleProperty.LABEL], [title.get_text()])
        return card

    def invalidate_source(self):
        self._suggestion_epoch += 1
        if self._suggestion_future:
            self._suggestion_future.cancel()
            self._suggestion_future = None
        self._excerpts.clear()
        self._chapter_cache.clear()

    def refresh(self):
        """Rebuild actual linked-passage cards and unlink actions without changing saved note identity."""
        from .notes_window import passage_label

        while self.rows.get_first_child():
            self.rows.remove(self.rows.get_first_child())
        for link in self.values:
            card = self.card(link, compound=True)
            card.set_hexpand(True)
            card.add_css_class("study-action-card")
            label = (
                tr("Unlink passage")
                + ": "
                + passage_label(link.start, link.end, link.versification)
            )
            remove = Gtk.Button(
                icon_name="edit-clear-symbolic", tooltip_text=label, valign=Gtk.Align.CENTER
            )
            remove.add_css_class("flat")
            remove.update_property([Gtk.AccessibleProperty.LABEL], [label])
            remove.connect("clicked", lambda *_, value=link: self.remove(value))
            card.unlink_button = remove
            from .passage_card import bind_card_actions

            bind_card_actions(
                card,
                lambda value=card: self.owner.navigate_selection(*value._target)
                if value._target
                else None,
                secondary=remove,
            )
            self.rows.append(card)
        self.row.set_subtitle(str(len(self.values)))
        self.disclosure.set_sensitive(bool(self.values))
        if not self.values:
            self.disclosure.set_active(False)

    def add(self):
        """Explicitly add one validated nonduplicate passage, respecting the200-link bound."""
        try:
            link = parse_link(self.entry.get_text(), self.context["versification"])
            if link == self.primary or link in self.values:
                self.error.set_text(tr("This passage is already linked."))
                return False
            if len(self.values) >= 200:
                raise ValueError(tr("Too many linked passages"))
            self.values = (*self.values, link)
            self.entry.set_text("")
            self.error.set_text("")
            self.refresh()
            self.disclosure.set_active(True)
            self.add_button.popdown()
            self.changed()
            return True
        except ValueError as error:
            self.error.set_text(tr(str(error)))
            return False

    def remove(self, link):
        self.values = tuple(value for value in self.values if value != link)
        self.refresh()
        self.changed()
