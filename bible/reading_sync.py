"""User-driven passage synchronization; programmatic/layout scrolling never leads."""

from __future__ import annotations

import time
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, GObject, Gtk
from .scroll_motion import stop_native_scroll


class ReadingSync:
    """Coordinate user-led Bible/study following on the GTK owner thread.

    One pending callback coalesces input. Layout/programmatic movements do not
    become drivers, and hidden study content does not trigger synchronization.
    """

    def __init__(self, owner) -> None:
        self.owner = owner
        self.driver = None
        self.pending = False
        self.running = False
        self.armed_until = 0
        self.dragging = None
        self.forced_position = None
        self.needs_sync = False
        self._after_selection = False
        self.bind(owner.study.scroll, owner.study.text, "commentary")

    def bind(self, scroll, view, side, tab=None) -> None:
        """Observe native wheel/key/scrollbar intent without consuming the default scrolling gesture."""
        if tab:
            tab.sync_coordinator = self
        wheel = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        wheel.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        wheel.connect("scroll", lambda *_: self.intent(side, tab) or False)
        scroll.add_controller(wheel)
        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def key(_: object, value, code: object, state) -> bool:
            if (
                value
                in (
                    Gdk.KEY_Up,
                    Gdk.KEY_Down,
                    Gdk.KEY_Page_Up,
                    Gdk.KEY_Page_Down,
                    Gdk.KEY_Home,
                    Gdk.KEY_End,
                    Gdk.KEY_space,
                )
                and not state & Gdk.ModifierType.SHIFT_MASK
            ):
                self.intent(side, tab)
            return False

        keys.connect("key-pressed", key)
        scroll.add_controller(keys)
        bar = scroll.get_vscrollbar()
        drag = Gtk.GestureClick(button=1)
        drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drag.connect("pressed", lambda *_: self.begin_drag(side, tab))
        drag.connect("released", lambda *_: self.end_drag())
        drag.connect("stopped", lambda *_: self.end_drag())
        bar.add_controller(drag)
        # GestureClick stops recognizing when a press turns into a drag.
        # Continue observing actual held-button motion on the native track;
        # otherwise the user-intent deadline expires during a long drag.
        motion = Gtk.EventControllerMotion()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def dragged(controller, *_: object) -> None:
            if controller.get_current_event_state() & Gdk.ModifierType.BUTTON1_MASK:
                self.intent(side, tab)

        motion.connect("motion", dragged)
        bar.add_controller(motion)
        if GObject.signal_lookup("move-viewport", view.__gtype__):
            view.connect("move-viewport", lambda *_: self.intent(side, tab))
        scroll.get_vadjustment().connect(
            "value-changed", lambda *_: self.moved(side, view, bar, tab)
        )

    def intent(self, side, tab=None) -> bool:
        """Arm a user-selected driver and cancel obsolete automatic viewport restoration."""
        if tab is not None and tab is not self.owner.active_tab:
            return False
        if self.driver != side and self.owner.active_tab:
            target = self.owner.study.scroll if side == "bible" else self.owner.active_tab.scroll
            stop_native_scroll(target)
        self.driver = side
        self.armed_until = time.monotonic() + 0.4
        self.forced_position = None
        self.needs_sync = True
        self._after_selection = False
        if side == "bible" and tab:
            # Actual user input overrides an outstanding automatic restore.
            if tab._tick_id:
                tab.remove_tick_callback(tab._tick_id)
                tab._tick_id = 0
            tab._appearance_anchor = None
            tab._jump_reference = None
            tab._restoring_scroll = False
        if side == "bible" and self.owner.study.tool == "notes":
            self.owner.study.notes.resume_following()
        if side == "commentary":
            self.owner.study.cancel_reveal()
            self.owner.study.scrolled()
        self.schedule()
        return False

    def begin_drag(self, side, tab) -> None:
        self.intent(side, tab)
        self.dragging = side

    def end_drag(self) -> None:
        self.dragging = None
        self.armed_until = time.monotonic() + 0.15

    def explicit_bible(self) -> None:
        if self.owner.study.tool == "notes":
            self.owner.study.notes.resume_following()
        self.driver = "bible"
        self.armed_until = 0
        self.forced_position = None
        self.needs_sync = False
        self._after_selection = False

    def explicit_commentary(self, position) -> None:
        self.driver = "commentary"
        self.forced_position = position
        self.schedule()

    def moved(self, side, view, bar, tab) -> None:
        """Schedule following only for armed user motion, ignoring reflow, restoration and programmatic scrolling."""
        if self.running or (tab is not None and tab is not self.owner.active_tab):
            return
        if side == "commentary" and self.owner.study.motion.running:
            return
        if tab and tab.scroll_motion.running:
            return
        if (
            getattr(view, "_reader_reflow_tick", 0)
            or (tab and tab._restoring_scroll)
            or (side == "commentary" and self.owner.study._positioning)
        ):
            return
        geometry = (view.get_width(), view.get_height())
        previous = getattr(view, "_sync_geometry", geometry)
        view._sync_geometry = geometry
        if previous != geometry:
            return
        if bar.has_focus() and not self.owner.study._positioning:
            self.intent(side, tab)
        if self.dragging != side and time.monotonic() > self.armed_until:
            return
        if self.driver == side and not view.get_buffer().get_has_selection():
            self.needs_sync = True
            self.schedule()

    def schedule(self) -> None:
        """Queue at most one short main-loop callback for pending user intent."""
        if not self.pending:
            self.pending = True
            GLib.timeout_add(35, self.synchronize)

    def synchronize(self) -> bool:
        """Apply eligible user intent once, using verified passage correspondence.

        The callback exits for hidden/closed/immersive or unstable layouts. A
        bounded follow-up handles selection-induced reflow; it never starts
        permanent polling or invents cross-versification alignments.
        """
        self.pending = False
        owner = self.owner
        tab = owner.active_tab
        study = owner.study
        if (
            owner.closed
            or getattr(owner, "immersion", None)
            or self.running
            or not tab
            or getattr(owner, "_study_resizing", False)
            or study.tool not in ("commentaries", "notes", "references")
            or not tab.reader
            or not owner.split.get_show_sidebar()
            or not tab.text.get_mapped()
            or (study.tool == "commentaries" and (not study.reader or not study.text.get_mapped()))
        ):
            return False
        if (
            tab._restoring_scroll
            or getattr(tab, "_adapt_frames", 0) > 1
            or getattr(tab.text, "_reader_reflow_tick", 0)
            or (
                study.tool == "commentaries"
                and (study._positioning or getattr(study.text, "_reader_reflow_tick", 0))
            )
        ):
            # Reopening/resizing the drawer changes wrapping before the reader's
            # bounded layout frames restore its anchor. Do not consume the
            # pending intent using that intermediate viewport. Ordinary input
            # queues only one adaptation frame, so continuous following stays live.
            self.schedule()
            return False
        if self.forced_position is None and not self.needs_sync and self.dragging != self.driver:
            return False
        checking_layout = self._after_selection
        self._after_selection = False
        self.needs_sync = False
        self.running = True
        try:
            if self.driver == "bible" and not tab.text.get_buffer().get_has_selection():
                reference = tab.visible_reference()
                if reference and reference != tab.state.reference:
                    tab.select_verse(reference)
                    # Styling the selected number invalidates GtkTextView's
                    # lazy line layout. GTK 4.14 can settle on another visible
                    # verse after that selection, with no further input event.
                    # Recheck once through the existing bounded layout gate;
                    # never add a permanent tick or restart native scrolling.
                    if not checking_layout:
                        self._after_selection = True
                        self.needs_sync = True
                        self.schedule()
                elif reference:
                    if study.tool == "notes":
                        study.notes.queue_follow(reference)
                    elif study.tool == "references":
                        study.references.refresh()
                    else:
                        study.follow(reference)
            elif (
                study.tool == "commentaries"
                and self.driver == "commentary"
                and not study.text.get_buffer().get_has_selection()
            ):
                position = (
                    self.forced_position
                    if self.forced_position is not None
                    else study.visible_section()
                )
                self.forced_position = None
                if position is None:
                    return False
                section = study.reader.index.sections[position]
                if section.introduction:
                    study.current_position = position
                    study.passage.set_text(study.reader.index.label(position))
                    study.entry_controls()
                    tab.mark_commentary_range(None, None)
                    study.status.set_text(
                        study.translate("Introduction has no verified verse alignment.")
                    )
                    return False
                from .reference_resolution import resolve

                try:
                    passages = [
                        (
                            resolve(first, study.reader.versification, tab.reader).start,
                            resolve(last, study.reader.versification, tab.reader).end,
                        )
                        for first, last in section.passages
                    ]
                except ValueError as error:
                    tab.mark_commentary_range(None, None)
                    study.status.set_text(
                        study.translate("No verified alignment for this passage.") + f" {error}"
                    )
                    return False
                current = tab.reader.key(tab.state.reference).getIndex()
                if not any(
                    tab.reader.key(first).getIndex() <= current <= tab.reader.key(last).getIndex()
                    for first, last in passages
                ):
                    tab.reveal_reference(passages[0][0])
                tab.mark_commentary_segments(passages)
                study.current_position = position
                study.remember_position()
                study.passage.set_text(study.reader.index.label(position))
                study.entry_controls()
        finally:
            self.running = False
        return False
