"""Small native highlight list and paint-only tags; never change scripture words."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .ui import Window
    from .highlights import Highlight, HighlightStore
    from .sword_provider import Reader
    from .passage_annotations import PassageAnnotations

from gi.repository import Adw, Gio, GObject, Gtk, Pango
from .highlights import COLORS
from .i18n import tr, LANGUAGE
from .book_names import display_name, normalized
from .notes import parts
from .reference_labels import passage_label
from .shared_ui import message
from .reading_style import PALETTES


def text_changed(buffer: Gtk.TextBuffer) -> None:
    """Invalidate paint-only caches when the native buffer text changes."""
    revision = cast("int", getattr(buffer, "_highlight_revision"))
    setattr(buffer, "_highlight_revision", revision + 1)


def paint(
    view: Gtk.TextView,
    store: HighlightStore,
    system: str,
    ranges: Iterable[tuple[str, int, int]],
    visible: bool,
    high: bool,
    palette: str,
    *,
    reader: Reader | None = None,
    annotations: PassageAnnotations | None = None,
) -> None:
    """Apply cached paint-only highlight tags using deterministic projected mark priority.

    Skip unchanged buffer/range/color/palette state. Shared source ranges
    choose one display color without changing stored annotation identities
    or rewriting Scripture text.
    """
    buffer = view.get_buffer()
    table = buffer.get_tag_table()
    if not hasattr(buffer, "_highlight_revision"):
        setattr(buffer, "_highlight_revision", 0)
        buffer.connect("changed", text_changed)
    ranges = tuple(ranges)
    marks: dict[str, Highlight]
    if not visible:
        marks = {}
    elif reader and annotations:
        marks = annotations.colors(reader, (ref for ref, _, _ in ranges), store)
    else:
        marks = {
            ref: store.entries[(system, ref)]
            for ref, _, _ in ranges
            if (system, ref) in store.entries
        }
    groups: dict[tuple[int, int], tuple[tuple[int | str, ...], Highlight]] = {}
    for reference, start, end in ranges:
        mark = marks.get(reference)
        if not mark:
            continue
        priority = (
            annotations.mark_priority(reader, mark)
            if reader and annotations
            else (mark["resource"], mark["system"], mark["reference"], mark["color"])
        )
        previous = groups.get((start, end))
        if previous is None or priority < previous[0]:
            groups[(start, end)] = (priority, mark)
    state = (
        buffer,
        getattr(buffer, "_highlight_revision"),
        system,
        ranges,
        visible,
        high,
        palette,
        tuple(
            (reference, marks[reference].get("color") if reference in marks else None)
            for reference, _, _ in ranges
        ),
    )
    # Comparison can rebuild from an adjustment notification during GTK layout.
    # Do not invalidate the unchanged primary view while GTK validates it.
    if getattr(view, "_highlight_paint_state", None) == state:
        return
    for color, (background, label) in COLORS.items():
        tag = table.lookup("highlight-" + color)
        if tag is None:
            tag = buffer.create_tag("highlight-" + color)
        style = (
            PALETTES[palette][0] if high else background,
            PALETTES[palette][1] if high else "#202020",
            Pango.Underline.DOUBLE if high else Pango.Underline.NONE,
        )
        if getattr(tag, "_highlight_style", None) != style:
            tag.props.background, tag.props.foreground, tag.props.underline = style
            setattr(tag, "_highlight_style", style)
        buffer.remove_tag(tag, buffer.get_start_iter(), buffer.get_end_iter())
    if visible:
        for (start, end), (_, mark) in groups.items():
            if end > start:
                buffer.apply_tag(
                    cast("Gtk.TextTag", table.lookup("highlight-" + mark["color"])),
                    buffer.get_iter_at_offset(start),
                    buffer.get_iter_at_offset(end),
                )
    setattr(view, "_highlight_paint_state", state)


class MarkItem(GObject.Object):
    """Native list-model wrapper for one retained highlight record."""

    def __init__(self, mark: Highlight) -> None:
        super().__init__()
        self.mark = mark


class HighlightsWindow(Adw.Window):
    """Browse retained highlights and open them only in an available compatible translation."""

    def __init__(self, owner: Window) -> None:
        super().__init__(
            transient_for=owner, title=tr("Highlights"), default_width=500, default_height=560
        )
        self.owner = owner
        self.closed = False
        self.rows: list[Highlight] = []
        self.choosers: list[Gtk.FileChooserNative] = []
        self.set_destroy_with_parent(True)
        self.connect("close-request", self.closed_request)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=tr("Highlights")))
        menu = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text=tr("Highlight actions"))
        popover = Gtk.Popover()
        actions = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=12,
        )
        for label, restore in [("Back up highlights", False), ("Restore highlights", True)]:
            button = Gtk.Button(label=tr(label))
            button.connect("clicked", lambda _, r=restore: self.choose_file(r))
            actions.append(button)
        popover.set_child(actions)
        menu.set_popover(popover)
        header.pack_end(menu)
        box.append(header)
        self.search = Gtk.SearchEntry(
            placeholder_text=tr("Search highlighted passages"), margin_start=12, margin_end=12
        )
        self.search.update_property(
            [Gtk.AccessibleProperty.LABEL], [tr("Search highlighted passages")]
        )
        self.search.connect("search-changed", lambda *_: self.refresh())
        box.append(self.search)
        self.status = Gtk.Label(wrap=True, xalign=0, margin_start=12, margin_end=12)
        box.append(self.status)
        self.model = Gio.ListStore.new(MarkItem)
        selection = Gtk.NoSelection(model=self.model)
        factory = Gtk.SignalListItemFactory()
        factory.connect(
            "setup",
            lambda _, item: item.set_child(
                Gtk.Label(
                    xalign=0,
                    wrap=True,
                    margin_start=12,
                    margin_end=12,
                    margin_top=10,
                    margin_bottom=10,
                )
            ),
        )

        def bind(_: object, item: Gtk.ListItem) -> None:
            mark = cast("MarkItem", item.get_item()).mark
            label = cast("Gtk.Label", item.get_child())
            label.set_text(
                passage_label(mark["reference"], versification=mark["system"])
                + " — "
                + tr(COLORS[mark["color"]][1])
            )
            label.set_tooltip_text(mark["resource"] + " · " + mark["system"])

        factory.connect("bind", bind)
        self.list = Gtk.ListView(model=selection, factory=factory, single_click_activate=True)
        self.list.connect("activate", self.row_activated)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.list)
        box.append(scroll)
        self.set_content(box)
        self.refresh()

    def closed_request(self, *_: object) -> bool:
        self.closed = True
        return False

    def refresh(self) -> None:
        """Filter stored marks without requiring their original resource to remain installed."""
        query = normalized(self.search.get_text())
        self.rows = []
        for mark in reversed(list(self.owner.highlights.entries.values())):
            code, chapter, verse = parts(mark["reference"])
            name = display_name(code, code, LANGUAGE)
            if query in normalized(
                f"{name} {chapter}:{verse} {mark['reference']} {tr(COLORS[mark['color']][1])}"
            ):
                self.rows.append(mark)
        self.model.splice(0, self.model.get_n_items(), [MarkItem(mark) for mark in self.rows])
        self.status.set_text(
            (
                tr("Highlights unavailable. The original file is preserved.")
                + "\n"
                + self.owner.highlights.error
            )
            if self.owner.highlights.error
            else tr("No highlights yet.")
            if not self.rows
            else ""
        )

    def row_activated(self, _: object, index: int) -> None:
        """Try compatible installed translations and retain the highlight when none can open its passage."""
        if index >= len(self.rows):
            return
        mark = self.rows[index]
        tab = self.owner.active_tab
        candidates = list(
            dict.fromkeys(
                ([tab.state.resource] if tab else [])
                + [mark["resource"]]
                + self.owner.library.installed("bible")
            )
        )
        for name in candidates:
            if not name or name not in self.owner.library.installed("bible"):
                continue
            resource = self.owner.library.resource(name)
            if resource.versification == mark["system"] and self.owner.navigate_selection(
                name, mark["reference"]
            ):
                self.owner.present()
                self.close()
                return
        self.status.set_text(
            tr("No installed translation can open this highlight. The highlight is retained.")
        )

    def choose_file(self, restore: bool) -> None:
        """Run explicit standalone backup/confirmed merge restore through the highlight store contract."""
        title = tr("Restore highlights") if restore else tr("Back up highlights")
        chooser = Gtk.FileChooserNative.new(
            title,
            self,
            Gtk.FileChooserAction.OPEN if restore else Gtk.FileChooserAction.SAVE,
            tr("Open") if restore else tr("Save"),
            tr("Cancel"),
        )
        if not restore:
            chooser.set_current_name("Bible-highlights.json")
        self.choosers.append(chooser)

        def response(dialog: Gtk.FileChooserNative, result: int) -> None:
            if result == Gtk.ResponseType.ACCEPT:
                selected_file = dialog.get_file()
                path = selected_file.get_path() if selected_file else None

                def apply() -> None:
                    try:
                        if path is None:
                            raise ValueError(tr("Choose a local file."))
                        if restore:
                            self.owner.highlights.restore(path)
                            self.owner.refresh_highlights()
                            self.refresh()
                        else:
                            self.owner.highlights.backup(path)
                        self.status.set_text(tr("Done"))
                    except (OSError, ValueError, TypeError) as error:
                        self.status.set_text(str(error))

                if restore:
                    message(
                        self,
                        "Restore highlights?",
                        "Merge the backup with existing highlights. Notes and translations are unchanged.",
                        apply,
                    )
                else:
                    apply()
            dialog.destroy()
            self.choosers.remove(dialog)

        chooser.connect("response", response)
        chooser.show()
