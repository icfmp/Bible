"""Native passage study tools and the existing synchronized commentary reader."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Adw, GLib, Gtk, Pango

from .i18n import tr
from .reading_style import apply_direction
from .resource_details import details, plain
from .sword_provider import CommentaryReader, VersificationMismatch
from .reference_resolution import resolve


class StudyPanel(Gtk.Box):
    def __init__(self, owner):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.owner = owner
        self.names = []
        self._syncing = False
        self._stamp = None
        self._readers = {}
        self._labels = []
        self.reader=None;self.current_position=None;self.loaded=[];self.ranges={}
        self._display_context=None;self._positioning=False;self._reveal_tick=0
        self._loading=False;self._missing_near=0
        self._scroll_idle=0;self._load_idle=0;self._processing_scroll=False
        self.translate=tr
        self.add_css_class('sidebar-pane')
        self.add_css_class('end')
        self.add_css_class('study-drawer')
        self.header = Adw.HeaderBar(show_start_title_buttons=False, show_end_title_buttons=False)
        self.header.add_css_class('flat')
        title = Gtk.Label(label=tr('Passage study'), ellipsize=Pango.EllipsizeMode.END,
                          width_chars=1, max_width_chars=22)
        title.add_css_class('heading'); self.header.set_title_widget(title)
        self.hide_button = Gtk.Button(icon_name='go-next-symbolic',tooltip_text=tr('Hide study'))
        self.hide_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Hide study')])
        self.hide_button.connect('clicked',lambda *_:owner.study_button.set_active(False))
        self.header.pack_start(self.hide_button)
        self.choices = Gtk.DropDown(enable_search=True)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', lambda _, item: item.set_child(Gtk.Label(
            xalign=0, ellipsize=Pango.EllipsizeMode.END, width_chars=1, max_width_chars=24)))
        factory.connect('bind', lambda _, item: item.get_child().set_text(item.get_item().get_string()))
        self.choices.set_factory(factory);self.choices.set_list_factory(factory)
        self.choices.update_property([Gtk.AccessibleProperty.LABEL],[tr('Choose a commentary')])
        self.choices.connect('notify::selected',self.selection_changed)
        self.immersive_button = Gtk.Button(icon_name='view-fullscreen-symbolic',tooltip_text=tr('Read in immersive mode'))
        self.immersive_button.connect('clicked',lambda *_:owner.enter_immersion('commentary'))
        self.more = Gtk.MenuButton(icon_name='view-more-symbolic',tooltip_text=tr('Commentary actions'))
        self.more.update_property([Gtk.AccessibleProperty.LABEL],[tr('Commentary actions')])
        actions = Gtk.Popover()
        action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6,
                             margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        self.previous_entry = Gtk.Button(label=tr('Previous available entry'))
        self.next_entry = Gtk.Button(label=tr('Next available entry'))
        self.previous_entry.connect('clicked',lambda *_:self.step_entry(-1))
        self.next_entry.connect('clicked',lambda *_:self.step_entry(1))
        action_box.append(self.previous_entry);action_box.append(self.next_entry)
        self.info = Gtk.MenuButton(label=tr('Source and conditions'))
        from .catalogue_window import MetadataLabel
        self.metadata = MetadataLabel(xalign=0,yalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,
                                      selectable=True,max_width_chars=32,margin_start=12,margin_end=12,
                                      margin_top=12,margin_bottom=12)
        info_scroll = Gtk.ScrolledWindow(min_content_width=260,max_content_width=320,
                                         propagate_natural_width=True,max_content_height=350,
                                         propagate_natural_height=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        info_scroll.set_child(self.metadata)
        info = Gtk.Popover();info.set_child(info_scroll);self.info.set_popover(info)
        action_box.append(self.info)
        library = Gtk.Button(label=tr('Download a commentary'))
        library.connect('clicked',lambda *_:self.open_library())
        action_box.append(library)
        actions.set_child(action_box);self.more.set_popover(actions)
        for widget in [self.more,self.immersive_button]:
            widget.add_css_class('flat');self.header.pack_end(widget)
        self.places_button=Gtk.Button(icon_name='mark-location-symbolic',tooltip_text=tr('Places in this passage'))
        self.places_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Places in this passage')])
        self.places_button.add_css_class('flat');self.places_button.connect('clicked',lambda *_:owner.open_places())
        self.header.pack_end(self.places_button)
        self.append(self.header)
        self.tools = Gtk.Stack(vexpand=True, hhomogeneous=False, vhomogeneous=False)
        switcher = Gtk.StackSwitcher(stack=self.tools, halign=Gtk.Align.FILL)
        switcher.add_css_class('study-tools')
        layout = switcher.get_layout_manager()
        if isinstance(layout, Gtk.BoxLayout):layout.set_homogeneous(False)
        switcher.set_margin_start(12); switcher.set_margin_end(12)
        self.append(switcher)
        from .passage_notes import PassageNotes
        self.notes = PassageNotes(owner)
        from .study_references import StudyReferences
        self.references=StudyReferences(owner)
        notes_scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        notes_scroll.set_child(self.notes)
        self.tools.add_titled(notes_scroll, 'notes', tr('Notes'))
        self.tools.add_titled(self.references,'references',tr('References'))
        self.commentaries = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.choices.set_margin_start(12); self.choices.set_margin_end(12)
        self.commentaries.append(self.choices)
        self.tools.add_titled(self.commentaries, 'commentaries', tr('Commentaries'))
        tool = owner.study_settings.tool
        self.tools.set_visible_child_name(tool if tool in ('notes','references','commentaries') else 'commentaries')
        def compact_labels(widget):
            if isinstance(widget,Gtk.Label):widget.set_ellipsize(Pango.EllipsizeMode.END);widget.set_width_chars(1)
            if isinstance(widget,Gtk.ToggleButton) and isinstance(widget.get_child(),Gtk.Label):widget.set_tooltip_text(widget.get_child().get_text())
            child=widget.get_first_child()
            while child:compact_labels(child);child=child.get_next_sibling()
        compact_labels(switcher)
        self.append(self.tools)
        self.tools.connect('notify::visible-child-name', self.tool_changed)
        self.popovers = [actions,info]
        for popover in self.popovers:
            popover.set_autohide(False);owner._reading_popovers.append(popover)
        # Retain semantic source/reference fields for existing synchronization
        # and accessible tooltips, without duplicating long in-content banners.
        self.source = Gtk.Label()
        self.passage = Gtk.Label()
        self.source.connect('notify::label',lambda *_:self.choices.set_tooltip_text(self.source.get_text()))
        self.passage.connect('notify::label',lambda *_:self.text.update_property(
            [Gtk.AccessibleProperty.LABEL],[tr('Commentary text')+': '+self.passage.get_text()]))
        self.status = MetadataLabel(xalign=0,wrap=True,selectable=True,
                                    margin_start=16,margin_end=16,visible=False)
        self.status.connect('notify::label',lambda *_:self.status.set_visible(bool(self.status.get_text())))
        self.commentaries.append(self.status)
        self.text = Gtk.TextView(editable=False,cursor_visible=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                 left_margin=24,right_margin=24,top_margin=20,bottom_margin=24)
        self.text.add_css_class('study-reader')
        self.text.update_property([Gtk.AccessibleProperty.LABEL],[tr('Commentary text')])
        self.scroll = Gtk.ScrolledWindow(vexpand=True,hexpand=True)
        self.scroll.set_child(self.text)
        self.pages = Gtk.Stack(vexpand=True)
        self.pages.add_named(self.scroll,'reading')
        self.empty = Adw.StatusPage(title=tr('Choose a commentary'),
                                    description=tr('Choose or download a commentary.'),icon_name='accessories-dictionary-symbolic')
        self.download = Gtk.Button(child=Gtk.Label(label=tr('Download a commentary'),wrap=True),halign=Gtk.Align.CENTER)
        self.download.connect('clicked',lambda *_:self.open_library())
        self.empty.set_child(self.download);self.pages.add_named(self.empty,'empty')
        self.pages.set_visible_child_name('empty');self.commentaries.append(self.pages)
        self.scroll.get_vadjustment().connect('value-changed',self.scrolled)
        self._layout_geometry = None;self._layout_anchor = None
        self.add_tick_callback(self.adapt)
        self.sidebar_preferences = None
        self.tool_controls()

    @property
    def tool(self):return self.tools.get_visible_child_name()

    def tool_controls(self):
        for widget in (self.more,self.immersive_button):widget.set_visible(self.tool=='commentaries')

    def tool_changed(self, *_):
        self.tool_controls()
        self.owner.study_settings.tool = self.tool
        try:self.owner.study_settings.save()
        except (OSError,ValueError) as error:self.owner.report_session_error(tr('Unable to save study preferences.'),error)
        coordinator=getattr(self.owner,'reading_sync',None)
        if coordinator:
            coordinator.driver=None; coordinator.needs_sync=False; coordinator.forced_position=None
        if self.tool=='notes':self.notes.refresh();self.references.refresh()
        else:self.refresh(force=True)
        self.update_indicator()

    def apply_typography(self):
        from .preferences import ReadingPreferences
        self.sidebar_preferences = ReadingPreferences(font='sans-serif', size=12, line_spacing='normal')
        self.text.set_pixels_inside_wrap(0); self.text.set_pixels_below_lines(0)
        buffer=self.text.get_buffer(); tag=buffer.get_tag_table().lookup('reader-typography')
        if tag is None:tag=buffer.create_tag('reader-typography')
        tag.props.family='sans-serif'; tag.props.size_points=12; tag.props.line_height=1.5
        buffer.apply_tag(tag, buffer.get_start_iter(), buffer.get_end_iter())

    def adapt(self,*_):
        geometry=(self.scroll.get_width(),self.scroll.get_height())
        if geometry != self._layout_geometry and geometry[0]>0:
            anchor=self._layout_anchor or self.anchor()
            self.text.set_left_margin(24);self.text.set_right_margin(24)
            self._layout_geometry=geometry
            if anchor:self.reveal(*anchor,force=True)
        if not self._positioning:self._layout_anchor=self.anchor()
        return not self.owner.closed

    def open_library(self):
        for popover in self.popovers:popover.popdown()
        self.owner.open_library('commentary')

    def refresh(self, force=False):
        tab = self.owner.active_tab
        if tab is None:
            return
        if self.tool!='commentaries':
            if self.tool=='notes':self.notes.refresh(force=force)
            self.references.refresh(force=force)
            return
        installed = self.owner.library.installed('commentary')
        stamp = (id(tab), tab.state.commentary, tab.state.reference,
                 tab.state.resource, id(tab.reader), tuple(installed))
        if not force and stamp == self._stamp:
            return
        self._stamp = stamp
        self._syncing = True
        self.names = [None] + installed
        if tab.state.commentary and tab.state.commentary not in installed:
            self.names.append(tab.state.commentary)
        labels = [tr('Choose a commentary')]
        for name in self.names[1:]:
            if name in installed:
                resource = self.owner.library.resource(name)
                labels.append(f'{name} — {plain(resource.description)}')
            else:
                labels.append(f'{name} ({tr("Missing commentary")})')
        if labels != self._labels:
            self.choices.set_model(Gtk.StringList.new(labels))
            self._labels = labels
        self.choices.set_selected(self.names.index(tab.state.commentary))
        self._syncing = False
        self.render(tab, installed)

    def clear_content(self):
        self.cancel_scroll()
        self.cancel_reveal();self.loaded=[];self.ranges={};self.current_position=None
        self._layout_anchor=None
        if self.owner.active_tab:self.owner.active_tab.mark_commentary_range(None,None)
        self.text.get_buffer().set_text('')

    @property
    def entry_text(self):
        return self.reader.index.text(self.current_position) if self.reader and self.current_position is not None else ''

    def render(self, tab, installed):
        self.passage.set_text(tab.passage_title())
        name=tab.state.commentary
        if name is None or name not in installed:
            self.pages.set_visible_child_name('empty')
            self.clear_content();self.reader=None;self.source.set_text('');self.metadata.set_text('');self.info.set_sensitive(False)
            self.status.set_text(tr('Choose or download a commentary.') if name is None else
                                tr('This commentary is no longer installed. Choose another or download it again.'))
            self.entry_controls();return
        try:
            self.pages.set_visible_child_name('reading')
            resource=self.owner.library.resource(name)
            self.source.set_text(f'{plain(resource.description)} — {resource.source}')
            self.metadata.set_text(details(resource));self.info.set_sensitive(True)
            context=(id(tab),name)
            if context!=self._display_context:
                self.clear_content();self._display_context=context
            if name not in self._readers:self._readers[name]=CommentaryReader(self.owner.library.root/name,name)
            self.reader=self._readers[name]
            apply_direction(self.text,self.reader)
            if tab.reader is None:
                self.clear_content();self.status.set_text(tr('Open a Bible passage to read its commentary.'));return
            self.follow(tab.state.reference)
            saved=tab.state.commentary_positions.get(name)
            if context!=getattr(self,'_last_restored_context',None):
                self._last_restored_context=context
                if saved and self.current_position is not None:
                    section=self.reader.index.sections[self.current_position]
                    if section.index==saved['index']:
                        offset=saved['offset']
                        if saved.get('canonical'):
                            from .paged_sources import CommentaryPages
                            from .pagination import Anchor
                            document=CommentaryPages(self.reader,resource).document(self.current_position,self.owner.preferences.value)
                            offset=max(0,document.locate(Anchor(section.start,offset,True))-document.spans[0].body)
                        self.reveal(self.current_position,offset,force=True)
        except VersificationMismatch as error:
            self.clear_content();self.reader=None
            self.status.set_text(tr('Different versifications. Automatic alignment is unavailable.')+f' ({error})')
        except Exception as error:
            self.clear_content();self.reader=None;self.status.set_text(tr('Unable to read this commentary.')+f' {error}')
        self.entry_controls()

    def follow(self,reference):
        if not self.reader:return
        try:
            resolved=resolve(reference,self.owner.active_tab.reader.versification,self.reader,require_entry=False)
        except (ValueError,VersificationMismatch) as error:
            self.clear_content();self.status.set_text(tr('No verified alignment for this passage.')+f' {error}')
            self.entry_controls();return
        reference=resolved.start
        position=self.reader.index.locate(reference)
        if position is None or not self.reader.index.text(position).strip():
            self.clear_content();self._missing_near=self.reader.index.near(reference)
            self.status.set_text(tr('No commentary for this passage.'));self.entry_controls();return
        self.status.set_text('');self.current_position=position
        self.passage.set_text(self.reader.index.label(position))
        if position not in self.loaded:
            self.loaded=list(range(max(0,position-1),min(len(self.reader.index.sections),position+3)))
            self.rebuild()
        self.reveal(position);self.entry_controls()
        self.update_indicator()

    def update_indicator(self):
        tab=self.owner.active_tab
        if not tab:return
        if (self.tool!='commentaries' or not tab.reader or not self.reader or self.current_position is None
                or not self.owner.split.get_show_sidebar()):
            tab.mark_commentary_range(None,None);return
        section=self.reader.index.sections[self.current_position]
        if section.introduction:tab.mark_commentary_range(None,None);return
        try:
            first=resolve(section.start,self.reader.versification,tab.reader,require_entry=False).start
            last=resolve(section.end,self.reader.versification,tab.reader,require_entry=False).end
            tab.mark_commentary_range(first,last)
        except ValueError:tab.mark_commentary_range(None,None)

    def anchor(self):
        position=self.visible_section()
        if position is None:return None
        rect=self.text.get_visible_rect();_,iterator=self.text.get_iter_at_location(rect.x,rect.y)
        body=self.ranges[position][1]
        return position,max(0,iterator.get_offset()-body)

    def visible_section(self):
        if not self.ranges:return None
        rect=self.text.get_visible_rect();buffer=self.text.get_buffer()
        for position,(start,body,end) in self.ranges.items():
            top=self.text.get_iter_location(buffer.get_iter_at_offset(start)).y
            bottom=self.text.get_iter_location(buffer.get_iter_at_offset(end)).y
            if top<=rect.y<bottom:return position
            if rect.y<=top<rect.y+rect.height:return position
        return next(reversed(self.ranges))

    def rebuild(self,anchor=None):
        self.cancel_scroll()
        self.cancel_reveal();self._positioning=True
        from .paged_sources import CommentaryPages
        from .pagination import Document,StyleSpan
        from .bible_render import bind_copy
        from .commentary_format import apply
        source=CommentaryPages(self.reader,self.owner.library.resource(self.owner.active_tab.state.commentary))
        pieces=[];styles=[];self.ranges={};offset=0
        for position in self.loaded:
            heading=self.reader.index.label(position)+'\n'
            document=source.document(position,self.owner.preferences.value)
            base=offset+len(heading)
            pieces.extend([heading,document.text,'\n\n'])
            styles.extend(StyleSpan(s.kind,s.start+base,s.end+base) for s in document.styles)
            self.ranges[position]=(offset,base+document.spans[0].body,base+len(document.text))
            offset=base+len(document.text)+2
        document=Document('study',''.join(pieces),(),tuple(styles))
        buffer=self.text.get_buffer();buffer.set_text(document.text)
        bind_copy(self.text,document)
        self.apply_typography()
        palette='contrast-night' if self.owner.reading_style.manager.get_dark() else 'contrast-day'
        apply(self.text,[(s.kind,s.start,s.end) for s in styles],self.sidebar_preferences,palette)
        # Native sidebar ink follows theme/contrast changes without a rebuild.
        # The Bible's fixed palette colors must not override it here.
        number=buffer.get_tag_table().lookup('source-number')
        if number:number.props.foreground_set=False
        tag=buffer.get_tag_table().lookup('entry-heading')
        if tag is None:tag=buffer.create_tag('entry-heading',weight=700)
        for start,body,end in self.ranges.values():buffer.apply_tag(tag,buffer.get_iter_at_offset(start),buffer.get_iter_at_offset(body))
        if anchor:self.reveal(anchor[0],anchor[1],force=True)
        else:self.reveal(self.current_position,force=True)

    def cancel_reveal(self):
        if self._reveal_tick:self.text.remove_tick_callback(self._reveal_tick);self._reveal_tick=0
        self._positioning=False

    def reveal(self,position,offset=0,force=False):
        if position not in self.ranges:return
        buffer=self.text.get_buffer();start,body,end=self.ranges[position]
        visible=self.text.get_visible_rect()
        top=self.text.get_iter_location(buffer.get_iter_at_offset(start)).y
        bottom=self.text.get_iter_location(buffer.get_iter_at_offset(end)).y
        if not force and (top<=visible.y<bottom or visible.y<=top<visible.y+visible.height):return
        self._layout_anchor=(position,offset)
        self.cancel_reveal();self._positioning=True
        frames=[0]
        def restore(*_):
            if self.owner.closed or position not in self.ranges:self._reveal_tick=0;self._positioning=False;return False
            frames[0]+=1
            self.text.set_bottom_margin(max(24,self.text.get_visible_rect().height))
            if frames[0]<3:return True
            first,begin,last=self.ranges[position]
            iterator=buffer.get_iter_at_offset(min(last,begin+offset) if offset else first)
            target=self.text.get_iter_location(iterator);rect=self.text.get_visible_rect()
            adjustment=self.scroll.get_vadjustment();adjustment.set_value(adjustment.get_value()+target.y-rect.y)
            if frames[0]<5:return True
            self._positioning=False;self._reveal_tick=0;return False
        self._reveal_tick=self.text.add_tick_callback(restore)

    def scrolled(self,*_):
        if (self._positioning or not self.loaded or not self.reader or self.owner.closed
                or not self.owner.split.get_show_sidebar()):return
        if getattr(self.text,'_reader_reflow_tick',0):return
        # Read layout/anchors after GTK finishes the adjustment notification;
        # coalesce it with any pending scroll work and cancel it on replacement.
        if not self._scroll_idle and not self._processing_scroll:
            self._scroll_idle=GLib.idle_add(self.process_scroll)

    def cancel_scroll(self):
        for name in ('_scroll_idle','_load_idle'):
            source=getattr(self,name,0)
            if source:GLib.source_remove(source);setattr(self,name,0)
        self._loading=False

    def process_scroll(self):
        self._scroll_idle=0
        if (self.owner.closed or not self.owner.split.get_show_sidebar() or
                self._positioning or not self.loaded or not self.reader or
                getattr(self.text,'_reader_reflow_tick',0)):return False
        self._processing_scroll=True
        try:
            self.remember_position()
            adjustment=self.scroll.get_vadjustment()
            if not self._loading:
                before=adjustment.get_value()<100 and self.loaded[0]>0
                after=adjustment.get_value()+adjustment.get_page_size()>adjustment.get_upper()-180 and self.loaded[-1]+1<len(self.reader.index.sections)
                if before or after:
                    self._loading=True
                    self._load_idle=GLib.idle_add(self.load_more,-1 if before else 1)
        finally:self._processing_scroll=False
        return False

    def load_more(self,direction):
        self._load_idle=0
        self._loading=False
        if self.owner.closed or not self.owner.split.get_show_sidebar() or not self.reader or not self.loaded:return False
        anchor=self.anchor()
        first=max(0,self.loaded[0]-3) if direction<0 else self.loaded[0]
        last=min(len(self.reader.index.sections),self.loaded[-1]+4) if direction>0 else self.loaded[-1]+1
        loaded=list(range(first,last))
        if len(loaded)>20:loaded=loaded[:20] if direction<0 else loaded[-20:]
        if loaded==self.loaded:return False
        self.loaded=loaded
        self.rebuild(anchor);return False

    def remember_position(self):
        if not hasattr(self.owner,'reading_sync') or self.owner.reading_sync.driver!='commentary':return
        anchor=self.anchor();tab=self.owner.active_tab
        if anchor and tab and tab.state.commentary:
            section=self.reader.index.sections[anchor[0]]
            tab.state.commentary_positions[tab.state.commentary]=dict(reference=section.start,index=section.index,offset=anchor[1])
            self.owner.schedule_save()

    def entry_controls(self):
        self.immersive_button.set_sensitive(bool(self.reader and self.current_position is not None and self.entry_text.strip()))
        self.immersive_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Read in immersive mode')+': '+self.source.get_text()])
        count=len(self.reader.index.sections) if self.reader else 0
        previous=(self.current_position-1) if self.current_position is not None else self._missing_near-1
        following=(self.current_position+1) if self.current_position is not None else self._missing_near
        self.previous_entry.set_sensitive(0<=previous<count);self.next_entry.set_sensitive(0<=following<count)
        if self.reader:
            if 0<=previous<count:self.previous_entry.set_tooltip_text(tr('Previous available entry')+': '+self.reader.index.label(previous))
            if 0<=following<count:self.next_entry.set_tooltip_text(tr('Next available entry')+': '+self.reader.index.label(following))

    def step_entry(self,direction):
        if self.tool!='commentaries':self.tools.set_visible_child_name('commentaries')
        if not self.reader:return
        position=(self.current_position+direction) if self.current_position is not None else self._missing_near-(1 if direction<0 else 0)
        if not 0<=position<len(self.reader.index.sections):return
        self.current_position=position
        self.passage.set_text(self.reader.index.label(position));self.update_indicator()
        if position not in self.loaded:
            self.loaded=list(range(max(0,position-1),min(len(self.reader.index.sections),position+3)));self.rebuild()
        self.reveal(position,force=True);self.entry_controls()
        self.owner.reading_sync.explicit_commentary(position)

    def resume(self,position,anchor):
        if not self.reader:return
        self.current_position=position
        self.loaded=list(range(max(0,position-1),min(len(self.reader.index.sections),position+3)))
        from .paged_sources import CommentaryPages
        source=CommentaryPages(self.reader,self.owner.library.resource(self.owner.active_tab.state.commentary))
        doc=source.document(position,self.owner.preferences.value)
        self.rebuild((position,max(0,doc.locate(anchor)-doc.spans[0].body)))
        self.passage.set_text(self.reader.index.label(position))
        self.status.set_text(tr('Commentary resumed. The Bible passage is unchanged.'))
        self.entry_controls()
        self.update_indicator()

    def selection_changed(self, *_):
        if self._syncing or self.owner.active_tab is None:
            return
        index = self.choices.get_selected()
        if index < len(self.names):
            self.owner.active_tab.state.commentary = self.names[index]
            self.refresh()
            self.owner.schedule_save()
