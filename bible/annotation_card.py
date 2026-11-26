"""Bounded native annotation previews using the existing inert Markdown renderer."""

from __future__ import annotations

from gi.repository import Gtk, Pango, GLib
from .markdown import render
from .citations import citations
from .i18n import tr


def original_caption(owner, annotation):
    """Human original-edition metadata only; never a substitute Bible name."""
    try:
        return owner.library.resource(annotation.origin).description
    except (OSError, ValueError):
        snapshot = getattr(getattr(owner, "catalogue_session", None), "snapshot", None)
        resource = (
            next((r for r in snapshot.resources if r.id == annotation.origin), None)
            if snapshot
            else None
        )
        return resource.description if resource else tr("Original translation unavailable.")


def highlight_actions(menu, owner, mark, changed, failed, *, confirm_remove: bool = False) -> None:
    """One compact menu; context callbacks retain their navigation policy."""
    from .highlights import COLORS

    old = menu.get_popover()
    if old:
        old.popdown()
        menu.set_popover(None)
    snapshot = dict(mark)
    popover = Gtk.Popover()
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=4,
        margin_start=8,
        margin_end=8,
        margin_top=8,
        margin_bottom=8,
    )

    def apply(color) -> None:
        try:
            if (
                owner.highlights.entries.get((snapshot["system"], snapshot["reference"]))
                != snapshot
            ):
                raise ValueError(tr("This highlight changed elsewhere. Reopen it before editing."))
            changed(snapshot, color)
        except (OSError, ValueError) as error:
            failed(str(error))

    for color in [*COLORS, None]:
        button = Gtk.Button(label=tr(COLORS[color][1] if color else "Remove highlight"))

        def choose(_: object, value=color) -> None:
            popover.popdown()
            if value is None and confirm_remove:
                from .notes_window import message

                message(
                    owner,
                    "Remove this highlight?",
                    "The related notes are kept.",
                    lambda: apply(None),
                )
            else:
                apply(value)

        button.connect("clicked", choose)
        box.append(button)
    popover.set_child(box)
    menu.set_popover(popover)


def color_dot(menu, color) -> None:
    dot = Gtk.Box(
        width_request=16, height_request=16, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER
    )
    dot.add_css_class("highlight-" + color)
    dot.add_css_class("highlight-swatch")
    menu.set_child(dot)


def annotation_card(owner, annotation, activate, *, excerpt="", colors=None):
    """The same card in Study, the virtualized collection and related results."""
    from .passage_card import passage_card, bind_card_actions
    from .notes_window import passage_label, readable_date
    from .highlights import COLORS

    a = annotation
    card = passage_card(compound=True)
    card.add_css_class("study-action-card")
    title, empty = card._reference_labels
    title.set_text(passage_label(a.start, a.end, a.system))
    content = card._card_content
    content.remove(empty)
    header = content.get_first_child()
    kind = tr("Open note") if a.note else tr("Highlight") + " · " + tr(COLORS[a.color][1])
    indicator = Gtk.Image(
        icon_name="notebook-symbolic" if a.note else "edit-select-all-symbolic",
        pixel_size=16,
        tooltip_text=kind,
    )
    indicator.update_property([Gtk.AccessibleProperty.LABEL], [kind])
    header.prepend(indicator)
    card.type_icon = indicator
    menu = None
    if a.mark:
        card.highlight_key = (a.system, a.start)
        card.add_css_class("highlight-" + a.color)
        menu = Gtk.MenuButton(
            tooltip_text=kind + " — " + tr("Highlight actions"), valign=Gtk.Align.CENTER
        )
        menu.add_css_class("flat")
        menu.add_css_class("highlight-color-action")
        menu.update_property(
            [Gtk.AccessibleProperty.LABEL], [kind + " — " + tr("Highlight actions")]
        )
        color_dot(menu, a.color)
        card.actions = menu
        if colors:
            colors(menu, a.mark)
    bind_card_actions(
        card,
        activate,
        secondary=menu,
        label=kind + ": " + title.get_text(),
        ignore=(AnnotationPreview,),
    )
    card.update_property([Gtk.AccessibleProperty.LABEL], [kind + ": " + title.get_text()])
    card.annotation = a
    if a.note:
        preview = AnnotationPreview(owner, a.note, activate)
        preview.set_tooltip_text(None)
        content.append(preview)
        card.preview = preview
        card.note_id = a.note.id
        date, _ = readable_date(a.modified)
        linked = tr("+{count} passages").format(count=len(a.note.links)) if a.note.links else ""
        metadata = " · ".join(value for value in (date, " · ".join(a.labels), linked) if value)
        label = Gtk.Label(label=metadata, xalign=0, wrap=True)
    else:
        preview = Gtk.Label(
            label=" ".join(excerpt.split()),
            xalign=0,
            yalign=0,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            lines=2,
            ellipsize=Pango.EllipsizeMode.END,
            width_chars=1,
        )
        preview.add_css_class("study-content")
        content.append(preview)
        content.excerpt = preview
        label = Gtk.Label(
            label=original_caption(owner, a),
            xalign=0,
            ellipsize=Pango.EllipsizeMode.END,
            width_chars=1,
        )
        label.set_tooltip_text(a.origin + " · " + a.system)
        content.source_caption = label
    label.add_css_class("caption")
    label.add_css_class("dim-label")
    content.append(label)
    return card


def release_card(card) -> None:
    menu = getattr(card, "actions", None)
    if menu and menu.get_popover():
        menu.get_popover().popdown()
        menu.set_popover(None)


class AnnotationPreview(Gtk.Label):
    """Present a bounded inert note excerpt and its original-offset citations without altering the saved body."""

    def __init__(self, owner, note, open_note) -> None:
        super().__init__(
            xalign=0,
            yalign=0,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            lines=3,
            ellipsize=Pango.EllipsizeMode.END,
            width_chars=1,
            max_width_chars=40,
        )
        self.add_css_class("study-content")
        self.owner = owner
        self.note = note
        self.open_note = open_note
        text, spans = render(note.body)
        self.citations = citations(text, note.versification, spans)
        # Bound native markup/layout work even for very long saved notes.
        # Resolve citations before truncating so a cut reference never acquires
        # a different target. The complete saved note is untouched.
        if len(text) > 2048:
            text = text[:2048] + "…"
            spans = [(kind, a, min(b, 2048)) for kind, a, b in spans if a < 2048]
            self.citations = [c for c in self.citations if c.finish <= 2048]
        # A bounded preview is one paragraph: Pango's negative line limit is
        # otherwise applied separately to every Markdown paragraph. Offsets stay exact.
        text = text.replace("\n", " ").replace("\r", " ")
        cuts = sorted(
            {
                0,
                len(text),
                *(n for _, a, b in spans for n in (a, b)),
                *(n for c in self.citations for n in (c.begin, c.finish)),
            }
        )
        chunks = []
        for first, last in zip(cuts, cuts[1:]):
            value = GLib.markup_escape_text(text[first:last])
            for kind, start, end in spans:
                if start <= first and last <= end:
                    tag = {"bold": "b", "italic": "i", "link": "u"}[kind]
                    value = f"<{tag}>{value}</{tag}>"
            for index, c in enumerate(self.citations):
                if c.begin <= first and last <= c.finish:
                    value = f'<a href="bible-preview:{index}">{value}</a>'
            chunks.append(value)
        self.set_markup("".join(chunks) if text else GLib.markup_escape_text(tr("Empty note")))
        self._link_activated = False
        self.connect("activate-link", self.preview_citation)
        click = Gtk.GestureClick(button=1)
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def pressed(gesture, count, x, y) -> None:
            self._link_activated = False
            if count == 1 and not self.over_citation(x, y):
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        click.connect("pressed", pressed)
        click.connect(
            "released",
            lambda _, count, x, y: open_note()
            if count == 1 and not self._link_activated and not self.over_citation(x, y)
            else None,
        )
        self.add_controller(click)
        self.set_tooltip_text(tr("Open note"))

    def over_citation(self, x, y):
        # get_current_uri() can retain the keyboard-focused link after the
        # pointer leaves it. Hit-test the actual click instead.
        """Hit-test the actual pointer position instead of a possibly retained keyboard-focused link URI."""
        left, top = self.get_layout_offsets()
        inside, index, _ = self.get_layout().xy_to_index(
            int((x - left) * Pango.SCALE), int((y - top) * Pango.SCALE)
        )
        if not inside:
            return False
        offset = len(self.get_text().encode()[:index].decode())
        return any(c.begin <= offset < c.finish for c in self.citations)

    def preview_citation(self, _: object, uri):
        if not uri.startswith("bible-preview:"):
            return True
        try:
            index = int(uri.split(":", 1)[1])
            _citation = self.citations[index]
        except (ValueError, IndexError):
            return True
        self._link_activated = True
        return self.activate(index)

    def activate(self, index):
        """Open a recognized citation through the shared source-aware preview without navigating immediately."""
        if not 0 <= index < len(self.citations):
            return True
        citation = self.citations[index]
        tab = self.owner.active_tab
        reader = tab.reader if tab else None
        resource = tab.state.resource if reader else None
        self.owner.reference_preview.show(
            self, resource, reader, citation.start, citation.end, source_system=citation.system
        )
        return True
