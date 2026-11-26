"""One native contextual host for the existing word and place components."""

from __future__ import annotations

from dataclasses import replace
from gi.repository import Adw, Gdk, Gtk, Pango as Pango
from .i18n import tr
from .reference_preview import passage_title


class PassageStudy(Adw.Window):
    """Host the existing source-qualified word/place views in one contextual native window."""

    def __init__(
        self, owner, *, target=None, context=None, mode="original", place=None, metadata=None
    ) -> None:
        super().__init__(
            title=tr("Study passage"),
            transient_for=owner,
            modal=True,
            destroy_with_parent=True,
            default_width=min(700, max(320, owner.get_width() - 48)),
            default_height=min(680, max(360, owner.get_height() - 96)),
        )
        self.owner = owner
        self.closed = False
        self.words = None
        from .application_surfaces import secondary_dialog

        secondary_dialog(self, owner)
        # v1 exposes only implemented contextual views. Legacy callers cannot
        # send the dialog to an empty Dictionary/People placeholder page.
        mode = mode if mode in ("original", "map") else "original"
        if target is None:
            target = self.context_target(context)
        self.target = target
        if context is None and target:
            context = (
                target.source.resource,
                target.source.reader,
                target.references[0],
                target.references[-1],
            )
        self.context = context
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar(show_end_title_buttons=False)
        self.header = header
        self.close_button = Gtk.Button(icon_name="window-close-symbolic", tooltip_text=tr("Close"))
        self.close_button.update_property([Gtk.AccessibleProperty.LABEL], [tr("Close")])
        self.close_button.add_css_class("flat")
        self.close_button.connect("clicked", lambda *_: self.close())
        header.pack_end(self.close_button)
        root.append(header)
        caption = (
            passage_title(context[2], context[3], context[1].versification)
            if context
            else tr("Choose a passage")
        )
        self.passage = Gtk.Label(
            label=caption, wrap=True, margin_start=16, margin_end=16, margin_top=8, margin_bottom=4
        )
        self.passage.add_css_class("heading")
        root.append(self.passage)
        modern = hasattr(Adw, "InlineViewSwitcher")
        self.tabs = (Adw.ViewStack if modern else Gtk.Stack)(
            vexpand=True, hhomogeneous=False, vhomogeneous=False
        )
        switcher = (
            Adw.InlineViewSwitcher(
                stack=self.tabs,
                can_shrink=False,
                homogeneous=False,
                display_mode=Adw.InlineViewSwitcherDisplayMode.LABELS,
            )
            if modern
            else Gtk.StackSwitcher(stack=self.tabs)
        )
        self.switcher = switcher
        header.set_title_widget(switcher)
        root.append(self.tabs)
        if not modern:
            layout = switcher.get_layout_manager()
            if isinstance(layout, Gtk.BoxLayout):
                layout.set_homogeneous(False)
        if target:
            self.words = owner.study.words
            self.words.attach(target, metadata, host=self, start=mode == "original")
            self.tabs.add_titled(self.words, "original", tr("Original text"))
        else:
            self.tabs.add_titled(
                self.empty(tr("Choose a Bible passage to study.")), "original", tr("Original text")
            )
        from .place_cards import PlaceView

        self.places = PlaceView(owner, context=context, host=self)
        self.tabs.add_titled(self.places, "map", tr("Map"))
        compact = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 520sp"))
        for name, icon in (
            ("original", "text-x-generic-symbolic"),
            ("map", "mark-location-symbolic"),
        ):
            page = self.tabs.get_page(self.tabs.get_child_by_name(name))
            if modern:
                page.set_icon_name(icon)
            else:
                compact.add_setter(page, "icon-name", icon)
        if modern:
            compact.add_setter(switcher, "display-mode", Adw.InlineViewSwitcherDisplayMode.ICONS)
        self.add_breakpoint(compact)
        self.tabs.set_visible_child_name(mode)
        self._words_started = mode == "original"

        def selected(*_: object) -> None:
            if (
                self.words
                and self.tabs.get_visible_child_name() == "original"
                and not self._words_started
            ):
                self._words_started = True
                self.words.begin()

        self.tabs.connect("notify::visible-child-name", selected)
        self.set_content(root)
        self.set_size_request(320, 320)
        self.connect("close-request", self.on_close)
        keys = Gtk.EventControllerKey()
        keys.connect(
            "key-pressed",
            lambda _, key, *args: (self.close() or True) if key == Gdk.KEY_Escape else False,
        )
        self.add_controller(keys)
        if place:
            self.places.open_place(place)

    @staticmethod
    def empty(message):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=20,
            margin_end=20,
            margin_top=20,
            margin_bottom=20,
        )
        label = Gtk.Label(label=message, wrap=True, xalign=0)
        label.add_css_class("dim-label")
        box.append(label)
        return box

    def context_target(self, context):
        """Resolve the requested pane and verified local excerpt, returning None without matching source evidence."""
        tab = self.owner.active_tab
        if not tab or not tab.reader:
            return None
        comparison = bool(
            context and context[0] == tab.state.comparison and context[0] != tab.state.resource
        )
        factory = lambda: self.owner.passage_actions.ordinary(tab, comparison=comparison)
        source = factory()
        if not source or context and source.resource != context[0]:
            return None
        from .passage_actions import target

        view = tab.comparison_text if comparison else tab.text
        reference = context[2] if context else tab.state.reference
        span = next((s for s in source.document.spans if reference in s.members), None)
        if context and span is None:
            return None
        value = target(view, source, factory, span.body - source.base if span else 0)
        if value and context:
            from .reference_targets import local_excerpt

            try:
                excerpt = local_excerpt(
                    source.reader,
                    context[2],
                    context[3],
                    source_system=context[1].versification,
                    limit=40,
                )
            except (ValueError, OSError):
                return None
            value = replace(
                value,
                references=tuple(ref for ref, _ in excerpt.verses),
                text=excerpt.text,
                verses=tuple(text for _, text in excerpt.verses),
                native_selection=False,
                selection=None,
            )
        return value

    def refresh(self) -> None:
        if self.words:
            self.words.refresh()
        if not self.closed:
            self.places.refresh()

    def on_close(self, *_: object):
        """Invalidate child views and remove owner references before native window disposal."""
        if self.closed:
            return False
        self.closed = True
        self.close_button.grab_focus()
        if self.words:
            self.words.dialog_closed()
            self.tabs.remove(self.words)
        self.places.on_closed()
        for name in ("passage_study_dialog", "place_dialog"):
            if getattr(self.owner, name, None) is self:
                setattr(self.owner, name, None)
        return False
