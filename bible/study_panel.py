"""One safe, local commentary view following the active reading tab."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gtk, Pango

from .i18n import tr
from .reading_style import apply_direction
from .resource_details import details, plain
from .sword_provider import CommentaryReader, VersificationMismatch


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
        self.translate=tr
        self.append(Gtk.Label(label=tr('Commentaries'), xalign=0,
                              margin_start=12, margin_top=12))
        self.choices = Gtk.DropDown(enable_search=True, margin_start=12, margin_end=12)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', lambda _, item: item.set_child(Gtk.Label(
            xalign=0, ellipsize=Pango.EllipsizeMode.END, width_chars=1, max_width_chars=32)))
        factory.connect('bind', lambda _, item: item.get_child().set_text(item.get_item().get_string()))
        self.choices.set_factory(factory)
        self.choices.set_list_factory(factory)
        self.choices.update_property([Gtk.AccessibleProperty.LABEL], [tr('Choose a commentary')])
        self.choices.connect('notify::selected', self.selection_changed)
        self.append(self.choices)
        self.passage = Gtk.Label(xalign=0, wrap=True, margin_start=12, margin_end=12)
        self.append(self.passage)
        entries=Gtk.Box(spacing=6,margin_start=12,margin_end=12)
        self.previous_entry=Gtk.Button(icon_name='go-previous-symbolic',tooltip_text=tr('Previous available entry'))
        self.next_entry=Gtk.Button(icon_name='go-next-symbolic',tooltip_text=tr('Next available entry'))
        self.previous_entry.connect('clicked',lambda *_:self.step_entry(-1))
        self.next_entry.connect('clicked',lambda *_:self.step_entry(1))
        entries.append(self.previous_entry);entries.append(self.next_entry)
        self.immersive_button=Gtk.Button(icon_name='view-fullscreen-symbolic',tooltip_text=tr('Read in immersive mode'))
        self.immersive_button.connect('clicked',lambda *_:owner.enter_immersion('commentary'))
        entries.append(self.immersive_button)
        self.append(entries)
        self.source = Gtk.Label(xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR,
                                 margin_start=12, margin_end=12)
        self.append(self.source)
        self.info = Gtk.MenuButton(label=tr('Source and conditions'),
                                    margin_start=12, margin_end=12)
        popover = Gtk.Popover()
        self.metadata = Gtk.Label(xalign=0, yalign=0, wrap=True,
                                   wrap_mode=Pango.WrapMode.WORD_CHAR, selectable=True,
                                   max_width_chars=32, margin_start=12, margin_end=12,
                                   margin_top=12, margin_bottom=12)
        info_scroll = Gtk.ScrolledWindow(min_content_width=260, max_content_width=300,
                                         propagate_natural_width=True,
                                         max_content_height=350, propagate_natural_height=True,
                                         hscrollbar_policy=Gtk.PolicyType.NEVER)
        info_scroll.set_child(self.metadata)
        popover.set_child(info_scroll)
        self.info.set_popover(popover)
        self.append(self.info)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True,
                                 margin_start=12, margin_end=12)
        self.append(self.status)
        self.text = Gtk.TextView(editable=False, cursor_visible=False,
                                 wrap_mode=Gtk.WrapMode.WORD_CHAR, left_margin=12,
                                 right_margin=12, top_margin=8, bottom_margin=12)
        self.text.update_property([Gtk.AccessibleProperty.LABEL], [tr('Commentary text')])
        self.scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.scroll.set_child(self.text)
        self.append(self.scroll)
        self.scroll.get_vadjustment().connect('value-changed',self.scrolled)
        hint = Gtk.Label(label=tr('Click a verse in the Bible to follow it here.'),
                          wrap=True, margin_start=12, margin_end=12)
        self.append(hint)
        download = Gtk.Button(label=tr('Download a commentary'), margin_start=12,
                              margin_end=12, margin_bottom=12)
        download.connect('clicked', lambda *_: owner.open_library('commentary'))
        self.append(download)

    def refresh(self, force=False):
        tab = self.owner.active_tab
        if tab is None:
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
                labels.append(f'{plain(resource.description)} ({name})')
            else:
                labels.append(f'{name} ({tr("Missing commentary")})')
        if labels != self._labels:
            self.choices.set_model(Gtk.StringList.new(labels))
            self._labels = labels
        self.choices.set_selected(self.names.index(tab.state.commentary))
        self._syncing = False
        self.render(tab, installed)

    def clear_content(self):
        self.cancel_reveal();self.loaded=[];self.ranges={};self.current_position=None
        self.text.get_buffer().set_text('')

    @property
    def entry_text(self):
        return self.reader.index.text(self.current_position) if self.reader and self.current_position is not None else ''

    def render(self, tab, installed):
        self.passage.set_text(tab.passage_title())
        name=tab.state.commentary
        if name is None or name not in installed:
            self.clear_content();self.reader=None;self.source.set_text('');self.metadata.set_text('');self.info.set_sensitive(False)
            self.status.set_text(tr('Choose or download a commentary.') if name is None else
                                tr('This commentary is no longer installed. Choose another or download it again.'))
            self.entry_controls();return
        try:
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
            if tab.reader.versification!=self.reader.versification:
                raise VersificationMismatch(f'{tab.reader.versification} / {self.reader.versification}')
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
                            offset=document.locate(Anchor(section.start,offset,True))
                        self.reveal(self.current_position,offset,force=True)
        except VersificationMismatch as error:
            self.clear_content();self.reader=None
            self.status.set_text(tr('Different versifications. Automatic alignment is unavailable.')+f' ({error})')
        except Exception as error:
            self.clear_content();self.reader=None;self.status.set_text(tr('Unable to read this commentary.')+f' {error}')
        self.entry_controls()

    def follow(self,reference):
        if not self.reader:return
        position=self.reader.index.locate(reference)
        if position is None or not self.reader.index.text(position).strip():
            self.clear_content();self._missing_near=self.reader.index.near(reference)
            self.status.set_text(tr('No commentary for this passage.'));self.entry_controls();return
        self.status.set_text('');self.current_position=position
        if position not in self.loaded:
            self.loaded=list(range(max(0,position-1),min(len(self.reader.index.sections),position+3)))
            self.rebuild()
        self.reveal(position);self.entry_controls()

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
        self.cancel_reveal();self._positioning=True
        pieces=[];self.ranges={};offset=0
        for position in self.loaded:
            heading=self.reader.index.label(position)+'\n'
            body=self.reader.index.text(position)
            pieces.extend([heading,body,'\n\n'])
            self.ranges[position]=(offset,offset+len(heading),offset+len(heading)+len(body))
            offset+=len(heading)+len(body)+2
        buffer=self.text.get_buffer();buffer.set_text(''.join(pieces))
        self.owner.reading_style.apply_text(self.text,preserve=False)
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
        if self._positioning or not self.loaded or not self.reader or self.owner.closed:return
        if getattr(self.text,'_reader_reflow_tick',0):return
        self.remember_position()
        adjustment=self.scroll.get_vadjustment()
        if not self._loading:
            before=adjustment.get_value()<100 and self.loaded[0]>0
            after=adjustment.get_value()+adjustment.get_page_size()>adjustment.get_upper()-180 and self.loaded[-1]+1<len(self.reader.index.sections)
            if before or after:
                self._loading=True;GLib.idle_add(self.load_more,-1 if before else 1)

    def load_more(self,direction):
        self._loading=False
        if self.owner.closed or not self.reader or not self.loaded:return False
        anchor=self.anchor()
        first=max(0,self.loaded[0]-3) if direction<0 else self.loaded[0]
        last=min(len(self.reader.index.sections),self.loaded[-1]+4) if direction>0 else self.loaded[-1]+1
        self.loaded=list(range(first,last))
        if len(self.loaded)>20:self.loaded=self.loaded[:20] if direction<0 else self.loaded[-20:]
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
        if not self.reader:return
        position=(self.current_position+direction) if self.current_position is not None else self._missing_near-(1 if direction<0 else 0)
        if not 0<=position<len(self.reader.index.sections):return
        self.current_position=position
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
        self.rebuild((position,doc.locate(anchor)))
        self.passage.set_text(self.reader.index.label(position))
        self.status.set_text(tr('Commentary resumed. The Bible passage is unchanged.'))
        self.entry_controls()

    def selection_changed(self, *_):
        if self._syncing or self.owner.active_tab is None:
            return
        index = self.choices.get_selected()
        if index < len(self.names):
            self.owner.active_tab.state.commentary = self.names[index]
            self.refresh()
            self.owner.schedule_save()
