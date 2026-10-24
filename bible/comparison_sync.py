"""Reference-driven Bible comparison, independent of the study coordinator."""
import time
from .reading_sync import ReadingSync
from .reference_resolution import resolve


class ComparisonSync(ReadingSync):
    def __init__(self, owner, tab):
        self.owner=owner;self.tab=tab;self.driver=None;self.pending=False;self.running=False
        self.armed_until=0;self.dragging=None;self.last_target=None
        # Reuse input observation only. Never replace tab.sync_coordinator,
        # which belongs to the client-validated Bible/commentary following.
        self.bind(tab.scroll,tab.text,'primary')
        self.bind(tab.comparison_scroll,tab.comparison_text,'comparison')

    def intent(self, side, tab=None):
        if self.tab is not self.owner.active_tab or self.running:return False
        if self.driver != side:self.last_target=None
        self.driver=side;self.armed_until=time.monotonic()+.4
        if self.owner.study.tool=='notes':
            self.owner.study.notes.resume_following()
            if side=='comparison':
                self.owner.reading_sync.driver=None;self.owner.reading_sync.needs_sync=False
        if side=='comparison' and getattr(self.tab,'_comparison_tick',0):
            self.tab.comparison_text.remove_tick_callback(self.tab._comparison_tick)
            self.tab._comparison_tick=0;self.tab._comparison_positioning=False
        self.schedule();return False

    def moved(self,side,view,bar,tab=None):
        if self.running or self.tab is not self.owner.active_tab:return
        if self.tab._restoring_scroll or getattr(self.tab,'_comparison_positioning',False):return
        geometry=(view.get_width(),view.get_height())
        previous=getattr(view,'_comparison_geometry',geometry);view._comparison_geometry=geometry
        if previous != geometry:return
        if bar.has_focus():self.intent(side)
        if self.driver==side and (self.dragging==side or time.monotonic()<self.armed_until):self.schedule()

    def synchronize(self):
        self.pending=False;tab=self.tab
        if (self.owner.closed or self.owner.active_tab is not tab or self.owner.immersion
                or getattr(self.owner,'_study_resizing',False)
                or self.running or not tab.state.comparison or not tab._comparison_reader
                or not tab.text.get_mapped() or not tab.comparison_text.get_mapped()):return False
        # Queued layout callbacks must not outlive the actual input gesture.
        if self.driver is None or (self.dragging!=self.driver and time.monotonic()>=self.armed_until):return False
        if tab._restoring_scroll or getattr(tab,'_comparison_positioning',False):
            self.schedule();return False
        view=tab.text if self.driver=='primary' else tab.comparison_text
        if view.get_buffer().get_has_selection():return False
        self.running=True
        try:
            if self.driver=='primary':
                reference=tab.visible_reference()
                if not reference:return False
                resolved=resolve(reference,tab.reader.versification,tab._comparison_reader)
                target=('comparison',resolved.start,id(tab._comparison_document))
                if target!=self.last_target:
                    if reference!=tab.state.reference:tab.select_verse(reference)
                    if resolved.start not in tab._comparison_offsets:
                        tab._comparison_stamp=None;tab.refresh_comparison()
                    tab.reveal_comparison(resolved.start)
                    self.last_target=target
            elif self.driver=='comparison':
                reference=tab.comparison_visible_reference()
                if not reference:return False
                resolved=resolve(reference,tab._comparison_reader.versification,tab.reader)
                target=('primary',resolved.start,id(tab.current))
                if target!=self.last_target:
                    if resolved.start!=tab.state.reference:tab.reveal_reference(resolved.start)
                    if resolved.start in tab._verse_offsets:
                        buffer=tab.text.get_buffer();iterator=buffer.get_iter_at_offset(tab._verse_offsets[resolved.start])
                        rect=tab.text.get_visible_rect();location=tab.text.get_iter_location(iterator)
                        adjustment=tab.scroll.get_vadjustment()
                        adjustment.set_value(adjustment.get_value()+location.y-rect.y)
                    self.last_target=target
            tab.set_comparison_alignment(None)
        except ValueError as error:
            tab.set_comparison_alignment(error)
            self.last_target=None
        finally:self.running=False
        return False
