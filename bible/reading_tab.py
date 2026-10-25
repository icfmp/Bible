"""One independent local reader, including its scroll position and translation."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Adw, Pango, Gio, GLib

from .providers import module_name
from .i18n import tr
from .sword_provider import Reader
from .book_names import display_name
from .i18n import LANGUAGE
from . import history
from .preferences import ReadingPreferences
from .reading_style import WIDTHS, SPACING, apply_direction
from .context_indicator import ContextTextView


class ReadingTab(Gtk.Box):
    def __init__(self, library, state, changed, jump_to_reference=False, notes_store=None, notes_requested=None, preferences=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6, vexpand=True)
        self.library, self.state, self.changed = library, state, changed
        self.preferences = preferences or ReadingPreferences()
        self._travelling = False
        self._verse_ranges = {}
        self._marker_ends = {}
        self.notes_store, self.notes_requested = notes_store, notes_requested
        from .inline_markers import InlineMarkers
        self.inline_markers=InlineMarkers(self)
        self._notes_stamp = None
        self._note_refs = {}
        self._study_coverage = None
        self.reader = None
        self.current = None
        self._restoring_scroll = True
        self._tick_id = 0
        self._scroll_frames = 0
        self._verse_offsets = {}
        self._jump_reference = None
        self._appearance_anchor = None
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True,
                                margin_start=12, margin_end=12)
        self.append(self.status)
        self.scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        from .scroll_motion import ScrollMotion
        self.scroll_motion=ScrollMotion(self.scroll)
        self.scroll.set_margin_top(56)  # Fixed clearance for the reading overlay controls.
        self.text = ContextTextView(editable=False, cursor_visible=False,
                                 wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                 left_margin=56, right_margin=56,
                                 top_margin=16, bottom_margin=24)
        self.text.add_css_class('reading')
        self.text._marker_context=self.inline_markers
        self.text.set_pixels_inside_wrap(5)
        self.text.set_pixels_below_lines(9)
        self._body_tag = self.text.get_buffer().create_tag(None)
        self._number_tag = self.text.get_buffer().create_tag('verse-number')
        self._verse_start_tag = self.text.get_buffer().create_tag('verse-start', allow_breaks=False)
        self._heading_tag = self.text.get_buffer().create_tag(None, weight=700, pixels_above_lines=16, pixels_below_lines=12)
        self._chapter_tag = self.text.get_buffer().create_tag(None, weight=700, justification=Gtk.Justification.CENTER, pixels_above_lines=20, pixels_below_lines=20)
        self._selected_tag = self.text.get_buffer().create_tag(None, weight=700)
        self._annotated_tag = self.text.get_buffer().create_tag(None, underline=1)
        self.verse_click = Gtk.GestureClick(button=1)
        self.verse_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.verse_click.connect('released', self.verse_clicked)
        self.text.add_controller(self.verse_click)
        self._target_mark = self.text.get_buffer().create_mark(
            None, self.text.get_buffer().get_start_iter(), True)
        self.clamp = None  # Keep GtkTextView directly scrollable; centre using dynamic margins.
        self.scroll.set_child(self.text)
        self.reading_overlay = Gtk.Overlay(vexpand=True, hexpand=True)
        self.reading_overlay.set_child(self.scroll)
        self.previous = self.chapter_button('go-previous-symbolic', 'Previous chapter',
                                            'win.previous-chapter', Gtk.Align.START)
        self.following = self.chapter_button('go-next-symbolic', 'Next chapter',
                                             'win.next-chapter', Gtk.Align.END)
        self.reading_layout=Gtk.Box(spacing=16,vexpand=True,homogeneous=True)
        self.primary_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,vexpand=True,hexpand=True)
        self.primary_heading=Gtk.Label(wrap=True,yalign=0,margin_top=12,margin_start=12,margin_end=12,visible=False)
        self.primary_heading.add_css_class('heading')
        self.primary_box.append(self.primary_heading);self.primary_box.append(self.reading_overlay)
        self.reading_layout.append(self.primary_box)
        self.comparison_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,visible=False,vexpand=True,hexpand=True)
        self.comparison_heading=Gtk.Label(wrap=True,yalign=0,margin_top=12,margin_start=12,margin_end=12)
        self.comparison_heading.add_css_class('heading')
        self.comparison_box.append(self.comparison_heading)
        self.comparison_status=Gtk.Label(wrap=True,margin_start=12,margin_end=12,visible=False)
        self.comparison_box.append(self.comparison_status)
        self.comparison_text=ContextTextView(editable=False,cursor_visible=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                          left_margin=24,right_margin=24,top_margin=16,bottom_margin=24,pixels_inside_wrap=5,pixels_below_lines=9)
        self.comparison_scroll=Gtk.ScrolledWindow(vexpand=True,hexpand=True,min_content_height=140)
        self.comparison_text._marker_context=self.inline_markers
        self.comparison_scroll.set_child(self.comparison_text)
        self.comparison_overlay=Gtk.Overlay(vexpand=True,hexpand=True)
        self.comparison_scroll.set_margin_top(56)
        self.comparison_overlay.set_child(self.comparison_scroll)
        self.comparison_controls=Gtk.Box(spacing=6,halign=Gtk.Align.END,valign=Gtk.Align.START,margin_top=12,margin_end=12)
        self.comparison_overlay.add_overlay(self.comparison_controls)
        headings=Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)
        headings.add_widget(self.primary_heading);headings.add_widget(self.comparison_heading)
        self.heading_size_group=headings
        self.comparison_box.append(self.comparison_overlay)
        self.reading_layout.append(self.comparison_box)
        self.comparison_horizontal=Gtk.ScrolledWindow(vexpand=True,hexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,vscrollbar_policy=Gtk.PolicyType.NEVER)
        self.comparison_horizontal.set_child(self.reading_layout)
        self.append(self.comparison_horizontal)
        from .comparison_rows import ComparisonRows
        self.comparison_rows=ComparisonRows(self)
        self._comparison_reader=None
        self._comparison_name=None
        self.add_tick_callback(self.adapt_comparison)
        context=Gio.Menu()
        context.append(tr('Add a passage note'),'win.note')
        context.append(tr('Study word'),'win.study-word')
        context.append(tr('Copy verses without numbers'),'win.copy-passage')
        context.append(tr('Copy verses with reference'),'win.copy-with-reference')
        context.append(tr('Copy reference'),'win.copy-reference')
        for color,label in [('yellow','Yellow'),('green','Green'),('blue','Blue')]:
            context.append(tr('Highlight')+': '+tr(label),'win.highlight-'+color)
        context.append(tr('Remove highlight'),'win.highlight-remove')
        self.text.set_extra_menu(context)
        self.comparison_text.set_extra_menu(context)
        self.scroll.get_vadjustment().connect('value-changed', self.scroll_changed)
        self.connect('map', self.on_map)
        self.load_resource(jump_to_reference)
        history.seed(self.state)

    def chapter_button(self, icon, label, action, align):
        button = Gtk.Button(icon_name=icon, tooltip_text=tr(label), action_name=action,
                            halign=align, valign=Gtk.Align.CENTER,
                            margin_start=6, margin_end=6)
        button.add_css_class('circular')
        button.add_css_class('osd')
        button.add_css_class('chapter-navigation')
        button.update_property([Gtk.AccessibleProperty.LABEL], [tr(label)])
        self.reading_overlay.add_overlay(button)
        return button

    def passage_title(self):
        if self.reader:
            try:
                key = self.reader.key(self.state.reference)
                name = display_name(key.getOSISBookName(), key.getBookName(), LANGUAGE)
                return f'{name} {key.getChapter()}:{key.getVerse()}'
            except ValueError:
                pass
        return self.state.reference if self.state.resource else tr('Choose a passage')

    def title(self):
        return f'{self.passage_title()} — {module_name(self.state.resource)}' if self.state.resource else tr('New tab')

    def navigate(self, resource, reference):
        try:
            reader = self.reader if resource == self.state.resource and self.reader else Reader(
                self.library.root / resource, resource)
            if not reader.has_reference(reference):
                raise ValueError(tr('This passage is not available in this translation.'))
            previous_reader, previous_resource = self.reader, self.state.resource
            self.reader = reader
            self.state.resource = resource
            if self.show(reference):
                return True
            self.reader, self.state.resource = previous_reader, previous_resource
            self.changed(self)
            return False
        except Exception as error:
            self.status.set_text(f'{tr("Unable to read this passage.")} {error}')
            self.status.set_visible(True)
            return False

    def load_resource(self, jump_to_reference=False):
        self._verse_offsets = {}
        self._jump_reference = None
        self.reader = None
        self.current = None
        self.text.get_buffer().set_text('')
        if not self.state.resource:
            self.status.set_text(tr('Choose or download a Bible. Downloaded texts are available offline.')
                                 if not self.library.installed('bible') else tr('Choose a translation'))
        elif self.state.resource not in self.library.installed('bible'):
            self.status.set_text(tr('This translation is no longer installed. Download it again or choose another translation.'))
        else:
            try:
                self.reader = Reader(self.library.root / self.state.resource, self.state.resource)
                available = self.reader.has_reference(self.state.reference)
                reference = self.state.reference if available else self.reader.first_reference()
                if not available:
                    self.state.scroll = 0.0
                self.show(reference, restore=not jump_to_reference)
                if not available:
                    self.status.set_text(tr('This passage is unavailable. Opened the first available passage.'))
                    self.status.set_visible(True)
            except Exception as error:
                self.status.set_text(f'{tr("Unable to read this passage.")} {error}')
                self.status.set_visible(True)
        if self.reader is None:
            self.status.set_visible(True)

    def show(self, reference, restore=False):
        self.scroll_motion.cancel()
        if not restore and not self._travelling and hasattr(self,'sync_coordinator'):self.sync_coordinator.explicit_bible()
        self._appearance_anchor = None
        if not self.reader or not reference:
            return
        try:
            if not self.reader.has_reference(reference):
                raise ValueError(tr('This passage is not available in this translation.'))
            chapter = self.reader.chapter(reference)
            canonical = self.reader.key(reference).getOSISRef()
            self._restoring_scroll = True
            self.current = chapter
            if not restore and not self._travelling:
                history.visit(self.state, self.state.resource, canonical)
            self.state.reference = canonical
            self._jump_reference = canonical if not restore else None
            if not restore:
                self.state.scroll = 0.0
            self.render_chapter(chapter)
            self._notes_stamp = None
            self.highlight_selection()
            self.status.set_text(tr('Ready'))
            self.status.set_visible(False)
            self.schedule_scroll_restore()
            self.changed(self)
            return True
        except Exception as error:
            self.status.set_text(f'{tr("Unable to read this passage.")} {error}')
            self.status.set_visible(True)
            return False

    def adapt_comparison(self,*_):
        geometry=(self.scroll.get_width(),self.scroll.get_height(),self.preferences.column_width)
        changed=geometry!=getattr(self,'_reading_geometry',geometry)
        if changed and not self._restoring_scroll and getattr(self,'_layout_anchor',None):
            self._appearance_anchor=self._layout_anchor;self._jump_reference=None
            self.schedule_scroll_restore()
        self._reading_geometry=geometry
        orientation=Gtk.Orientation.HORIZONTAL if self.state.comparison or self.get_width()>=760 else Gtk.Orientation.VERTICAL
        if self.reading_layout.get_orientation()!=orientation:self.reading_layout.set_orientation(orientation)
        for view,scroll,minimum in [(self.text,self.scroll,66),(self.comparison_text,self.comparison_scroll,66)]:
            margin=max(minimum,(scroll.get_width()-WIDTHS[self.preferences.column_width])//2)
            if view.get_left_margin()!=margin:view.set_left_margin(margin);view.set_right_margin(margin)
        if self.scroll.get_height()>0:
            from .navigation_overlay import position
            for button in (self.previous,self.following):
                position(button,self.text.get_left_margin(),self.scroll.get_width()-self.text.get_right_margin(),
                         self.scroll.get_margin_top(),self.scroll.get_height(),self.reading_overlay.get_width())
        self.comparison_rows.layout()
        comparison_geometry=(self.comparison_scroll.get_width(),self.comparison_scroll.get_height(),self.preferences.column_width)
        if (not getattr(self,'_shared_comparison',False) and comparison_geometry!=getattr(self,'_comparison_geometry',comparison_geometry)
                and getattr(self,'_comparison_layout_anchor',None)):
            anchor=self._comparison_layout_anchor
            self.reveal_comparison(anchor.reference,anchor=anchor,settle=True)
        self._comparison_geometry=comparison_geometry
        if (self.comparison_text.get_mapped() and not getattr(self,'_comparison_positioning',False)
                and getattr(self,'_comparison_document',None)):
            rect=self.comparison_text.get_visible_rect()
            _,iterator=self.comparison_text.get_iter_at_location(rect.x,rect.y)
            self._comparison_layout_anchor=self._comparison_document.anchor(iterator.get_offset())
        if self.text.get_mapped() and not self._restoring_scroll:
            rect=self.text.get_visible_rect();_,iterator=self.text.get_iter_at_location(rect.x,rect.y)
            self._layout_anchor=self.position_anchor(iterator.get_offset())
        return True

    def refresh_comparison(self):
        name = self.state.comparison
        stamp = (name, self.state.resource, self.reader.versification if self.reader else None,
                 self.state.reference, tuple(vars(self.preferences).items()))
        if stamp == getattr(self, '_comparison_stamp', None):return
        self._comparison_stamp = stamp
        if bool(name) != self.comparison_box.get_visible() and self.text.get_mapped() and not self._restoring_scroll:
            rect = self.text.get_visible_rect(); _, iterator = self.text.get_iter_at_location(rect.x, rect.y)
            self._appearance_anchor = self.position_anchor(iterator.get_offset())
            self._jump_reference = None; self.schedule_scroll_restore()
        self.comparison_box.set_visible(bool(name))
        self.primary_heading.set_visible(bool(name))
        self.comparison_horizontal.set_policy(Gtk.PolicyType.AUTOMATIC if name else Gtk.PolicyType.NEVER,Gtk.PolicyType.NEVER)
        self.reading_layout.set_size_request(760 if name else -1,-1)
        if not name:
            self.comparison_rows.leave()
            return
        try:
            primary=self.library.resource(self.state.resource)
            self.primary_heading.set_text(primary.description+' — '+primary.source+' · '+self.state.reference if self.reader else '')
        except ValueError:self.primary_heading.set_text('')
        self.comparison_status.set_text('');self.comparison_status.set_visible(False)
        self._comparison_layout_error=None
        try:
            if name not in self.library.installed('bible'):raise ValueError(tr('Comparison translation unavailable.'))
            resource = self.library.resource(name)
            if self._comparison_name != name:
                self._comparison_reader = Reader(self.library.root/name, name); self._comparison_name = name
            reader = self._comparison_reader
            if not self.reader:raise ValueError(tr('Open a Bible passage to read its commentary.'))
            from .reference_resolution import resolve
            alignment_error = None
            try:
                resolved = resolve(self.state.reference, self.reader.versification, reader,require_entry=False)
                reference, end = resolved.start, resolved.end
            except ValueError as error:
                # Keep this readable resource accessible in its own canon.
                # Never pass an unmapped printed source reference to it.
                alignment_error = error
                same_resource = (getattr(self, '_comparison_signature', None) or (None,))[0] == name
                reference = self.comparison_visible_reference() if same_resource else None
                reference = reference or reader.first_reference()
                end = reference
            chapter = reader.chapter(reference)
            self._comparison_heading_base = resource.description+' — '+resource.source+' · '+reference+(
                '–'+end if end != reference else '')
            self.set_comparison_alignment(alignment_error)
            signature = (name, chapter.reference, tuple(vars(self.preferences).items()))
            rebuild = signature != getattr(self, '_comparison_signature', None)
            anchor = None
            if rebuild:
                from .bible_render import render
                buffer = self.comparison_text.get_buffer()
                old = getattr(self, '_comparison_document', None)
                selected = [old.anchor(i.get_offset()) for i in buffer.get_selection_bounds()] if old else []
                if old and (getattr(self, '_comparison_signature', None) or (None,))[0] == name:
                    rect = self.comparison_text.get_visible_rect()
                    _, iterator = self.comparison_text.get_iter_at_location(rect.x, rect.y)
                    if old.key == chapter.reference:anchor = old.anchor(iterator.get_offset())
                self._comparison_document, self._comparison_offsets, self._comparison_ranges, self._comparison_markers = render(
                    self.comparison_text, reader, chapter, self.preferences)
                self._comparison_signature = signature
                self.update_highlights()
                self.refresh_study_indicator()
                if selected and old.key == chapter.reference:
                    buffer.select_range(*(buffer.get_iter_at_offset(self._comparison_document.locate(a)) for a in selected))
            if alignment_error is None:
                try:self.comparison_rows.build(chapter)
                except ValueError as error:
                    self.comparison_rows.leave()
                    self._comparison_layout_error=error
                    self.set_comparison_alignment(error)
            else:self.comparison_rows.leave()
            sync = getattr(self, 'comparison_sync', None)
            if not (sync and sync.running and sync.driver == 'comparison'):
                self.reveal_comparison(reference, anchor=anchor, settle=rebuild)
        except Exception as error:
            self.comparison_rows.leave()
            self.comparison_text.get_buffer().set_text('')
            self._comparison_reader = None; self._comparison_name = None
            self._comparison_signature = None; self._comparison_offsets = {}
            self._comparison_document = None; self._comparison_ranges = {}; self._comparison_markers = {}
            self.comparison_heading.set_text('')
            self.comparison_status.set_text(str(error));self.comparison_status.set_visible(True)

    def set_comparison_alignment(self, error):
        error=error or getattr(self,'_comparison_layout_error',None)
        self._comparison_aligned = error is None
        self.comparison_status.set_visible(error is not None)
        self.comparison_status.set_text((tr('Automatic following unavailable. Reading independently.')+' '+str(error))
                                        if error is not None else '')
        heading = getattr(self, '_comparison_heading_base', '')
        self.comparison_heading.set_text(heading+(' · '+tr('Independent reading') if error is not None else ''))

    def comparison_visible_reference(self):
        offsets = getattr(self, '_comparison_offsets', {})
        if not offsets:return None
        rect = self.comparison_text.get_visible_rect(); buffer = self.comparison_text.get_buffer()
        starts = [(ref, self.comparison_text.get_iter_location(buffer.get_iter_at_offset(offset)).y)
                  for ref, offset in offsets.items()]
        visible = [ref for ref, y in starts if rect.y <= y < rect.y+rect.height]
        if visible:return visible[0]
        preceding = [ref for ref, y in starts if y <= rect.y]
        return preceding[-1] if preceding else starts[0][0]

    def reveal_comparison(self, reference, anchor=None, settle=False):
        if getattr(self,'_shared_comparison',False):return
        offsets = getattr(self, '_comparison_offsets', {})
        if reference not in offsets:return
        if getattr(self, '_comparison_tick', 0):self.comparison_text.remove_tick_callback(self._comparison_tick)
        frames = [0]; self._comparison_positioning = True
        def reveal(*_):
            frames[0] += 1
            if not self.get_mapped():
                self._comparison_tick = 0; self._comparison_positioning = False; return False
            if settle and frames[0] < 3:return True
            view = self.comparison_text; buffer = view.get_buffer()
            offset = self._comparison_document.locate(anchor) if anchor else offsets[reference]
            target = view.get_iter_location(buffer.get_iter_at_offset(offset))
            rect = view.get_visible_rect(); adjustment = self.comparison_scroll.get_vadjustment()
            view.set_bottom_margin(max(24, self.comparison_scroll.get_height()))
            adjustment.set_value(adjustment.get_value()+target.y-rect.y)
            if settle and frames[0] < 6:return True
            self._comparison_tick = 0; self._comparison_positioning = False; return False
        self._comparison_tick = self.comparison_text.add_tick_callback(reveal)

    def render_chapter(self, chapter):
        if hasattr(self,'comparison_rows'):
            self.comparison_rows.signature=None
            self._comparison_stamp=None
        from .bible_render import render
        self._document, self._verse_offsets, self._verse_ranges, self._marker_ends = render(
            self.text, self.reader, chapter, self.preferences)
        self.update_highlights()

    def update_highlights(self,high=None,palette=None):
        store=getattr(self,'_highlight_store',None)
        if store is None or not self.reader:return
        if high is not None:self._highlight_high=high
        if palette is not None:self._highlight_palette=palette
        from .highlight_ui import paint
        options=(self.preferences.show_highlights,getattr(self,'_highlight_high',False),getattr(self,'_highlight_palette','white'))
        paint(self.text,store,self.reader.versification,[(ref,*bounds) for ref,bounds in self._verse_ranges.items()],*options)
        if self._comparison_reader and self.state.comparison:
            paint(self.comparison_text,store,self._comparison_reader.versification,
                  [(ref,*bounds) for ref,bounds in getattr(self,'_comparison_ranges',{}).items()],*options)
        self.refresh_study_indicator()

    def position_anchor(self, offset):
        candidates = [(ref,start,end) for ref,(start,end) in self._verse_ranges.items()
                      if start <= offset]
        if not candidates:return None
        ref,start,end = candidates[-1]
        return ref, max(0,offset-self._marker_ends[ref])

    def anchor_offset(self, anchor):
        ref,relative = anchor
        return min(self._verse_ranges[ref][1],self._marker_ends[ref]+relative)

    def apply_appearance(self):
        if self.current:
            buffer = self.text.get_buffer()
            selection = buffer.get_selection_bounds()
            selected = [self.position_anchor(i.get_offset()) for i in selection]
            visible = self.text.get_visible_rect()
            _,iterator = self.text.get_iter_at_location(visible.x,visible.y)
            anchor = self._appearance_anchor or (self.position_anchor(iterator.get_offset()) if self.get_mapped() and not self._restoring_scroll else None)
            pending_jump = self._jump_reference
            self.render_chapter(self.current)
            if selected and all(selected):
                buffer.select_range(*(buffer.get_iter_at_offset(self.anchor_offset(a)) for a in selected))
            self._notes_stamp = None
            self.highlight_selection()
            self.update_notes(force=True)
            self._appearance_anchor = anchor
            self._jump_reference = None if anchor else pending_jump
            self.schedule_scroll_restore()

    def travel(self, index):
        if not 0 <= index < len(self.state.history):return False
        entry = self.state.history[index]
        if entry['resource'] not in self.library.installed('bible'):
            self.status.set_text(tr('History resource unavailable. The passage has been kept.'))
            self.status.set_visible(True);return False
        history.capture(self.state)
        self._travelling = True
        try:
            if not self.navigate(entry['resource'],entry['reference']):return False
            self.state.history_index = index
            self.state.scroll = entry.get('scroll',0.0)
            self._jump_reference = None
            self.schedule_scroll_restore()
            self.changed(self)
            return True
        finally:self._travelling = False

    def highlight_selection(self):
        buffer = self.text.get_buffer()
        buffer.remove_tag(self._selected_tag, buffer.get_start_iter(), buffer.get_end_iter())
        if self.state.reference in self._verse_offsets:
            start = self._verse_offsets[self.state.reference]
            buffer.apply_tag(self._selected_tag, buffer.get_iter_at_offset(start),
                             buffer.get_iter_at_offset(start + len(self.state.reference.rsplit('.', 1)[-1])))
        self.text.update_property([Gtk.AccessibleProperty.LABEL], [self.passage_title()])

    def select_verse(self, reference):
        if hasattr(self,'sync_coordinator') and not self.sync_coordinator.running:self.sync_coordinator.explicit_bible()
        if reference not in self._verse_offsets:
            return False
        self.state.reference = reference
        self.highlight_selection()
        self.changed(self)
        return True

    def verse_clicked(self, gesture, count, x, y):
        widget=self.text.pick(x,y,Gtk.PickFlags.DEFAULT)
        while widget and widget is not self.text:
            if widget.has_css_class('inline-marker'):return
            widget=widget.get_parent()
        if self.text.get_buffer().get_has_selection():
            return
        bx, by = self.text.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(x), int(y))
        found, iterator = self.text.get_iter_at_location(bx, by)
        if found:
            candidates = [ref for ref,(start,end) in self._verse_ranges.items()
                          if start <= iterator.get_offset() < end]
            if candidates:
                reference = candidates[-1]
                self.select_verse(reference)
                if (reference in self._note_refs and self.notes_requested
                        and iterator.get_offset() < self._verse_offsets[reference] + len(reference.rsplit('.', 1)[-1])):
                    self.notes_requested()

    def selected_passage(self):
        selection = self.text.get_buffer().get_selection_bounds()
        if selection:
            start, end = (iterator.get_offset() for iterator in selection)
            selected = [reference for reference,(first,last) in self._verse_ranges.items()
                        if first < end and last > start]
            if selected:
                return selected[0], selected[-1]
        return self.state.reference, self.state.reference

    def update_notes(self, force=False):
        generation=self.notes_store.generation if self.notes_store else -1
        if generation!=getattr(self,'_inline_note_generation',generation):
            self._inline_note_generation=generation
            self.apply_appearance();self.refresh_comparison()
        self._inline_note_generation=generation
        stamp = (id(self.reader), self.state.reference,
                 self.notes_store.generation if self.notes_store else -1)
        if not force and stamp == self._notes_stamp:
            return
        self._notes_stamp = stamp
        buffer = self.text.get_buffer()
        buffer.remove_tag(self._annotated_tag, buffer.get_start_iter(), buffer.get_end_iter())
        self._note_refs = {}
        if self.reader and self._verse_offsets and self.notes_store:
            references = list(self._verse_offsets)
            notes = self.notes_store.passage(self.reader.versification, references[0], references[-1])
            for reference, offset in self._verse_offsets.items():
                matching = [note for note in notes if note.covers(reference)]
                if matching:
                    self._note_refs[reference] = matching

    def visible_reference(self):
        if not self._verse_offsets:return None
        rect=self.text.get_visible_rect()
        starts=[(reference,self.text.get_iter_location(self.text.get_buffer().get_iter_at_offset(offset)).y)
                for reference,offset in self._verse_offsets.items()]
        visible=[ref for ref,y in starts if rect.y <= y < rect.y+rect.height]
        if visible:return visible[0]
        preceding=[ref for ref,y in starts if y<=rect.y]
        return preceding[-1] if preceding else starts[0][0]

    def reveal_reference(self, reference):
        same_document=reference in self._verse_offsets
        if reference not in self._verse_offsets:
            self._travelling=True
            try:self.show(reference)
            finally:self._travelling=False
        else:self.select_verse(reference)
        offset=self._verse_offsets.get(reference)
        if offset is not None:
            iterator=self.text.get_buffer().get_iter_at_offset(offset)
            target=self.text.get_iter_location(iterator);visible=self.text.get_visible_rect()
            if not visible.y<=target.y<visible.y+visible.height:
                if same_document:
                    document=self.current
                    adjustment=self.scroll.get_vadjustment()
                    self.scroll_motion.move(adjustment.get_value()+target.y-visible.y-visible.height*.1,
                        valid=lambda:self.get_mapped() and self.current is document and self.state.reference==reference)
                else:self.text.scroll_to_iter(iterator,.05,True,0,.1)

    def mark_commentary_range(self,start,end):
        self._study_coverage=(self.reader.versification,start,end) if start and end and self.reader else None
        self.refresh_study_indicator()

    def study_ranges(self,reader,ranges):
        if not self._study_coverage or not self.state.study_visible or not reader:return []
        system,start,end=self._study_coverage
        from .reference_resolution import resolve
        try:
            first=reader.key(resolve(start,system,reader,require_entry=False).start).getIndex()
            last=reader.key(resolve(end,system,reader,require_entry=False).end).getIndex()
            return [(begin,finish) for reference,begin,finish in ranges
                    if first<=reader.key(reference).getIndex()<=last]
        except ValueError:return []

    def refresh_study_indicator(self):
        if not hasattr(self,'text'):return
        ranges=[(ref,start,end) for ref,(start,end) in self._verse_ranges.items()]
        self.text.set_study_ranges(self.study_ranges(self.reader,ranges))
        if hasattr(self,'comparison_text'):
            ranges=[(ref,start,end) for ref,(start,end) in getattr(self,'_comparison_ranges',{}).items()]
            self.comparison_text.set_study_ranges(self.study_ranges(getattr(self,'_comparison_reader',None),ranges))
        owner=getattr(getattr(self,'sync_coordinator',None),'owner',None)
        if owner and owner.immersion and owner.immersion.kind=='bible':owner.immersion.update_study_indicator()

    def step_verse(self, direction):
        references = list(self._verse_offsets)
        if self.state.reference in references:
            index = references.index(self.state.reference) + direction
            if 0 <= index < len(references):
                self.select_verse(references[index])
                iterator = self.text.get_buffer().get_iter_at_offset(self._verse_offsets[references[index]])
                self.text.scroll_to_iter(iterator, 0.1, False, 0, 0)

    def on_map(self, *_):
        self.schedule_scroll_restore()

    def schedule_scroll_restore(self):
        self._restoring_scroll = True
        self._scroll_frames = 0
        if not self._tick_id:
            self._tick_id = self.add_tick_callback(self.restore_scroll)

    def restore_scroll(self, *_):
        if getattr(self,'_shared_comparison',False) and self.comparison_rows.settling:
            return True
        # GTK needs layout frames after mapping or replacing a chapter.
        self._scroll_frames += 1
        if self._scroll_frames < 3:
            return True
        adjustment = self.scroll.get_vadjustment()
        maximum = max(0, adjustment.get_upper() - adjustment.get_page_size())
        desired = self.state.scroll * maximum
        if self._appearance_anchor:
            iterator = self.text.get_buffer().get_iter_at_offset(self.anchor_offset(self._appearance_anchor))
            target = self.text.get_iter_location(iterator)
            visible = self.text.get_visible_rect()
            adjustment.set_value(adjustment.get_value()+target.y-visible.y)
            # TextView validates wrapped paragraphs lazily. Keep the semantic
            # anchor for two more frames as its adjustment bounds settle.
            if self._scroll_frames < 5:return True
            self._appearance_anchor = None
        elif (self._jump_reference in self._verse_offsets
                and self._jump_reference.rsplit('.', 1)[-1] != '1'):
            iterator = self.text.get_buffer().get_iter_at_offset(self._verse_offsets[self._jump_reference])
            self.text.get_buffer().move_mark(self._target_mark, iterator)
            # Mapping can invalidate GTK's first pending scroll. Keep the request
            # until a subsequent layout frame confirms the verse is visible.
            target = self.text.get_iter_location(iterator)
            visible = self.text.get_visible_rect()
            if not (visible.y <= target.y < visible.y + visible.height):
                adjustment.set_value(adjustment.get_value()+target.y-visible.y)
                return True
            if self._scroll_frames < 6:return True
        else:
            adjustment.set_value(min(desired, maximum))
        self._tick_id = 0
        self._jump_reference = None
        self._restoring_scroll = False
        self.scroll_changed()
        return False

    def scroll_changed(self, *_):
        if self._restoring_scroll or not self.get_mapped():
            return
        adjustment = self.scroll.get_vadjustment()
        maximum = adjustment.get_upper() - adjustment.get_page_size()
        if maximum > 0:
            self.state.scroll = max(0.0, min(1.0, adjustment.get_value() / maximum))
            self.changed(self)
