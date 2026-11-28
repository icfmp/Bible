"""Safe native Markdown preview; generated citations never rewrite note data."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from ..ui import Window
    from ..citations import Citation

from gi.repository import Gtk, Pango, Gdk
from ..markdown import render
from ..i18n import tr


type FocusDirection = (
    Gtk.DirectionType
    | Literal[
        "GTK_DIR_DOWN",
        "GTK_DIR_LEFT",
        "GTK_DIR_RIGHT",
        "GTK_DIR_TAB_BACKWARD",
        "GTK_DIR_TAB_FORWARD",
        "GTK_DIR_UP",
        "down",
        "left",
        "right",
        "tab-backward",
        "tab-forward",
        "up",
    ]
)


class NotePreview(Gtk.TextView):
    """Render inert note Markdown and bounded local-reference previews without rewriting saved notes."""

    def __init__(
        self,
        *,
        owner: Window | None = None,
        system: str | None = None,
        navigation_guard: Callable[[Callable[[], None]], None] | None = None,
        **kwargs: object,
    ) -> None:
        # GObject validates this public bag of native construction properties.
        # Keep that boundary dynamic without weakening the note/citation model.
        initialize = cast("Callable[..., None]", super().__init__)
        initialize(
            editable=False,
            cursor_visible=False,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            left_margin=12,
            right_margin=12,
            top_margin=12,
            bottom_margin=12,
            **kwargs,
        )
        self.add_css_class("study-content")
        self.owner = owner
        self.system = system
        self.navigation_guard = navigation_guard
        self.citations: list[Citation] = []
        self._citation_focus = -1
        self._pressed: tuple[int, float, float] | None = None
        self.set_accepts_tab(False)
        self.update_property([Gtk.AccessibleProperty.LABEL], [tr("Safe preview")])
        buffer = self.get_buffer()
        self.tags = {
            "bold": buffer.create_tag(None, weight=700),
            "italic": buffer.create_tag(None, style=Pango.Style.ITALIC),
            "link": buffer.create_tag(None, underline=Pango.Underline.SINGLE),
        }
        self.citation_tag = buffer.create_tag(None, underline=Pango.Underline.SINGLE)
        click = Gtk.GestureClick(button=1)
        click.connect("pressed", self.pressed)
        click.connect("released", self.released)
        self.add_controller(click)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.motion)
        self.add_controller(motion)
        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.key_pressed)
        self.add_controller(keys)

    def set_source(self, source: str) -> None:
        """Replace preview tags/citations and dismiss any anchored preview of the previous text."""
        if self.owner:
            preview = self.owner.reference_preview.popover
            if preview and getattr(preview, "_note_preview", None) is self:
                self.owner.reference_preview.dismiss()
        text, spans = render(source)
        buffer = self.get_buffer()
        buffer.set_text(text)
        for kind, start, end in spans:
            buffer.apply_tag(
                self.tags[kind], buffer.get_iter_at_offset(start), buffer.get_iter_at_offset(end)
            )
        from ..citations import citations

        self.citations = citations(text, self.system, spans) if self.owner and self.system else []
        self._citation_focus = -1
        for citation in self.citations:
            buffer.apply_tag(
                self.citation_tag,
                buffer.get_iter_at_offset(citation.begin),
                buffer.get_iter_at_offset(citation.finish),
            )
        self.set_tooltip_text(
            tr("Bible references: Tab to choose, Enter to preview.") if self.citations else None
        )

    def at_offset(self, offset: int) -> int | None:
        """Find the citation containing a half-open display-buffer offset."""
        return next((i for i, c in enumerate(self.citations) if c.begin <= offset < c.finish), None)

    def at_point(self, x: float, y: float) -> int | None:
        """Resolve widget coordinates through GTK without guessing a passage."""
        bx, by = self.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(x), int(y))
        found, iterator = self.get_iter_at_location(bx, by)
        return self.at_offset(iterator.get_offset()) if found else None

    def pressed(self, _: Gtk.GestureClick, count: int, x: float, y: float) -> None:
        self._pressed = (count, x, y)

    def released(self, _: object, count: int, x: float, y: float) -> None:
        if not self._pressed:
            return
        previous, px, py = self._pressed
        self._pressed = None
        if previous != 1 or count != 1 or abs(px - x) > 4 or abs(py - y) > 4:
            return
        if self.get_buffer().get_has_selection():
            return
        index = self.at_point(x, y)
        if index is not None:
            self.activate_citation(index)

    def motion(self, _: Gtk.EventControllerMotion, x: float, y: float) -> None:
        self.set_cursor_from_name("pointer" if self.at_point(x, y) is not None else "text")

    def do_focus(self, direction: FocusDirection) -> bool:
        """Traverse recognized citations with Tab before yielding native focus to surrounding controls."""
        if self.citations and direction in (
            Gtk.DirectionType.TAB_FORWARD,
            Gtk.DirectionType.TAB_BACKWARD,
        ):
            backward = direction == Gtk.DirectionType.TAB_BACKWARD
            index = (
                (self._citation_focus + (-1 if backward else 1))
                if self.has_focus()
                else (len(self.citations) - 1 if backward else 0)
            )
            if 0 <= index < len(self.citations):
                self.grab_focus()
                self._citation_focus = index
                citation = self.citations[index]
                buffer = self.get_buffer()
                buffer.select_range(
                    buffer.get_iter_at_offset(citation.begin),
                    buffer.get_iter_at_offset(citation.finish),
                )
                self.scroll_to_iter(buffer.get_iter_at_offset(citation.begin), 0.1, False, 0, 0)
                return True
            self._citation_focus = -1
            return False
        return Gtk.TextView.do_focus(self, direction)

    def key_pressed(self, _: object, key: int, code: object, state: Gdk.ModifierType) -> bool:
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space) and not state & (
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK
        ):
            offset = self.get_buffer().get_iter_at_mark(self.get_buffer().get_insert()).get_offset()
            index = self.at_offset(offset)
            if index is not None:
                self.activate_citation(index)
                return True
        return False

    def activate_citation(self, index: int) -> None:
        """Preview a recognized citation in the active reader through the existing draft/navigation guard."""
        if not self.owner or self.owner.closed or not 0 <= index < len(self.citations):
            return
        self._citation_focus = index
        citation = self.citations[index]
        tab = self.owner.active_tab
        reader = tab.reader if tab else None
        resource = tab.state.resource if tab and reader else None
        position = self.get_iter_location(self.get_buffer().get_iter_at_offset(citation.begin))
        x, y = self.buffer_to_window_coords(Gtk.TextWindowType.WIDGET, position.x, position.y)
        rectangle = Gdk.Rectangle()
        rectangle.x = x
        rectangle.y = y
        rectangle.width = max(1, position.width)
        rectangle.height = max(1, position.height)
        anchor = self.get_ancestor(Gtk.ScrolledWindow) or self
        if anchor is not self:
            found, bounds = self.compute_bounds(anchor)
            if found:
                rectangle.x += int(bounds.origin.x)
                rectangle.y += int(bounds.origin.y)
        popover = self.owner.reference_preview.show(
            anchor,
            resource,
            reader,
            citation.start,
            citation.end,
            source_system=citation.system,
            navigation_guard=self.navigation_guard,
            pointing_to=rectangle,
        )
        if popover:
            popover._note_preview = self
