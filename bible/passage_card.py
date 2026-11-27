"""Shared native passage card for reference and theme results."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, cast, overload
from gi.repository import Gtk, Pango

if TYPE_CHECKING:
    # These contracts describe attributes attached by the factory below. They
    # introduce no runtime subclasses or additional GTK GTypes.
    class ButtonCard(Gtk.Button):
        _card_content: Gtk.Box
        _reference_labels: tuple[Gtk.Label, Gtk.Label]
        primary_action: Gtk.Button

    class CompoundCard(Gtk.Box):
        _card_content: Gtk.Box
        _reference_labels: tuple[Gtk.Label, Gtk.Label]
        primary_action: Gtk.Button


type PassageCard = ButtonCard | CompoundCard


@overload
def passage_card(*, compound: Literal[False] = False) -> ButtonCard: ...


@overload
def passage_card(*, compound: Literal[True]) -> CompoundCard: ...


@overload
def passage_card(*, compound: bool) -> PassageCard: ...


def passage_card(*, compound: bool = False) -> PassageCard:
    # Cards with embedded links need a native composite instead of nesting
    # competing interactive descendants inside a GtkButton.
    """Build the shared native reference/excerpt card, optionally leaving actions to a compound container."""
    button = (
        cast("CompoundCard", Gtk.Box(orientation=Gtk.Orientation.VERTICAL))
        if compound
        else cast("ButtonCard", Gtk.Button())
    )
    for name in ("card", "annotation-card", "reference-card", "action-card"):
        button.add_css_class(name)
    button.set_cursor_from_name("pointer")
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    title = Gtk.Label(xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, width_chars=1)
    title.add_css_class("passage-card-title")
    text = Gtk.Label(
        xalign=0,
        wrap=True,
        wrap_mode=Pango.WrapMode.WORD_CHAR,
        ellipsize=Pango.EllipsizeMode.END,
        lines=3,
        width_chars=1,
    )
    text.add_css_class("reference-excerpt")
    text.add_css_class("study-content")
    header = Gtk.Box(spacing=8)
    title.set_hexpand(True)
    header.append(title)
    arrow = Gtk.Image(icon_name="go-next-symbolic", pixel_size=12, valign=Gtk.Align.START)
    arrow.add_css_class("dim-label")
    header.append(arrow)
    content.append(header)
    content.append(text)
    if isinstance(button, Gtk.Box):
        button.append(content)
    else:
        button.set_child(content)
    button._card_content = content
    button._reference_labels = (title, text)
    return button


def bind_card_actions(
    card: PassageCard,
    activate: Callable[[], object],
    *,
    secondary: Gtk.Widget | None = None,
    label: str = "",
    ignore: tuple[type[Gtk.Widget], ...] = (),
) -> None:
    """Independent native controls on one shared, full-width card surface."""
    content = card._card_content
    # The factory always places this header first and its arrow last.
    header = cast("Gtk.Box", content.get_first_child())
    content.remove(header)
    title, _ = card._reference_labels
    action = Gtk.Button(child=header, hexpand=secondary is None)
    action.add_css_class("flat")
    action.add_css_class("card-primary")
    action.connect("clicked", lambda *_: activate())
    action.update_property([Gtk.AccessibleProperty.LABEL], [label or title.get_text()])
    row = Gtk.Box(spacing=6)
    row.append(action)
    content.prepend(row)
    if secondary is not None:
        arrow = cast("Gtk.Widget", header.get_last_child())
        header.remove(arrow)
        title.set_hexpand(False)
        title.set_width_chars(-1)
        title.set_max_width_chars(24)
        title.set_wrap(False)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        row.append(secondary)
        row.append(Gtk.Box(hexpand=True))
        row.append(arrow)
    click = Gtk.GestureClick(button=1)

    def clicked(_: object, count: int, x: float, y: float) -> None:
        if count != 1:
            return
        target = card.pick(x, y, Gtk.PickFlags.DEFAULT)
        while target and target is not card:
            if isinstance(target, (Gtk.Button, Gtk.MenuButton, *ignore)):
                return
            target = target.get_parent()
        activate()

    click.connect("released", clicked)
    card.add_controller(click)
    card.primary_action = action
