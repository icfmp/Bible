"""User-driven passage synchronization; programmatic/layout scrolling never leads."""
import time
import gi

gi.require_version('Gtk','4.0')
from gi.repository import Gdk, GLib, GObject, Gtk


class ReadingSync:
    def __init__(self, owner):
        self.owner=owner;self.driver=None;self.pending=False;self.running=False
        self.armed_until=0;self.dragging=None;self.forced_position=None;self.needs_sync=False
        self.bind(owner.study.scroll,owner.study.text,'commentary')

    def bind(self,scroll,view,side,tab=None):
        if tab:tab.sync_coordinator=self
        wheel=Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        wheel.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        wheel.connect('scroll',lambda *_:self.intent(side,tab) or False)
        scroll.add_controller(wheel)
        keys=Gtk.EventControllerKey();keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def key(_,value,code,state):
            if (value in (Gdk.KEY_Up,Gdk.KEY_Down,Gdk.KEY_Page_Up,Gdk.KEY_Page_Down,
                          Gdk.KEY_Home,Gdk.KEY_End,Gdk.KEY_space)
                    and not state & Gdk.ModifierType.SHIFT_MASK):self.intent(side,tab)
            return False
        keys.connect('key-pressed',key);scroll.add_controller(keys)
        bar=scroll.get_vscrollbar()
        drag=Gtk.GestureClick(button=1);drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drag.connect('pressed',lambda *_:self.begin_drag(side,tab))
        drag.connect('released',lambda *_:self.end_drag())
        drag.connect('stopped',lambda *_:self.end_drag())
        bar.add_controller(drag)
        # GestureClick stops recognizing when a press turns into a drag.
        # Continue observing actual held-button motion on the native track;
        # otherwise the user-intent deadline expires during a long drag.
        motion=Gtk.EventControllerMotion()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def dragged(controller,*_):
            if controller.get_current_event_state() & Gdk.ModifierType.BUTTON1_MASK:
                self.intent(side,tab)
        motion.connect('motion',dragged);bar.add_controller(motion)
        if GObject.signal_lookup('move-viewport',view.__gtype__):
            view.connect('move-viewport',lambda *_:self.intent(side,tab))
        scroll.get_vadjustment().connect('value-changed',lambda *_:self.moved(side,view,bar,tab))

    def intent(self,side,tab=None):
        if tab is not None and tab is not self.owner.active_tab:return False
        self.driver=side;self.armed_until=time.monotonic()+.4;self.forced_position=None;self.needs_sync=True
        if side=='bible' and tab:
            # Actual user input overrides an outstanding automatic restore.
            if tab._tick_id:tab.remove_tick_callback(tab._tick_id);tab._tick_id=0
            tab._appearance_anchor=None;tab._jump_reference=None;tab._restoring_scroll=False
        if side=='commentary':self.owner.study.cancel_reveal()
        self.schedule();return False

    def begin_drag(self,side,tab):
        self.intent(side,tab);self.dragging=side

    def end_drag(self):
        self.dragging=None;self.armed_until=time.monotonic()+.15

    def explicit_bible(self):
        self.driver='bible';self.armed_until=0;self.forced_position=None;self.needs_sync=False

    def explicit_commentary(self,position):
        self.driver='commentary';self.forced_position=position;self.schedule()

    def moved(self,side,view,bar,tab):
        if self.running or (tab is not None and tab is not self.owner.active_tab):return
        if getattr(view,'_reader_reflow_tick',0) or (tab and tab._restoring_scroll) or (side=='commentary' and self.owner.study._positioning):return
        geometry=(view.get_width(),view.get_height())
        previous=getattr(view,'_sync_geometry',geometry);view._sync_geometry=geometry
        if previous!=geometry:return
        if bar.has_focus() and not self.owner.study._positioning:self.intent(side,tab)
        if self.dragging!=side and time.monotonic()>self.armed_until:return
        if self.driver==side and not view.get_buffer().get_has_selection():self.needs_sync=True;self.schedule()

    def schedule(self):
        if not self.pending:
            self.pending=True;GLib.timeout_add(35,self.synchronize)

    def synchronize(self):
        self.pending=False
        owner=self.owner;tab=owner.active_tab;study=owner.study
        if (owner.closed or getattr(owner,'immersion',None) or self.running or not tab
                or not tab.reader or not owner.split.get_show_sidebar() or not study.reader
                or not tab.text.get_mapped() or not study.text.get_mapped()):return False
        if (tab._restoring_scroll or study._positioning
                or getattr(study.text,'_reader_reflow_tick',0)):
            self.schedule();return False
        if self.forced_position is None and not self.needs_sync and self.dragging!=self.driver:return False
        self.needs_sync=False;self.running=True
        try:
            if self.driver=='bible' and not tab.text.get_buffer().get_has_selection():
                reference=tab.visible_reference()
                if reference and reference!=tab.state.reference:tab.select_verse(reference)
                elif reference:study.follow(reference)
            elif self.driver=='commentary' and not study.text.get_buffer().get_has_selection():
                position=self.forced_position if self.forced_position is not None else study.visible_section()
                self.forced_position=None
                if position is None:return False
                section=study.reader.index.sections[position]
                if section.introduction:
                    study.status.set_text(study.translate('Introduction has no verified verse alignment.'));return False
                if study.reader.versification!=tab.reader.versification:return False
                if not tab.reader.has_reference(section.start) or not tab.reader.has_reference(section.end):
                    study.status.set_text(study.translate('This passage is not available in this translation.'));return False
                current=tab.reader.key(tab.state.reference).getIndex()
                if not section.contains_index(current):tab.reveal_reference(section.start)
                tab.mark_commentary_range(section.start,section.end)
                study.current_position=position;study.remember_position()
        finally:self.running=False
        return False
