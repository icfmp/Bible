"""Intent-driven passage actions with frozen source/range/copy targets."""
from dataclasses import dataclass
from gi.repository import Gdk, Gio, GLib, Gtk, Pango, Graphene, Gsk
from .i18n import tr
from .notes_window import passage_label
from .providers import module_name

BACKDROP_BLUR=16


@dataclass(frozen=True)
class Source:
    tab: object
    resource: str
    reader: object
    document: object
    base: int
    parent: object
    side: str


@dataclass(frozen=True)
class Target:
    source: Source
    view: object
    factory: object
    references: tuple
    text: str
    verses: tuple
    native_selection: bool
    anchor: int


def references(source,first,last):
    numbers=source.tab.preferences.verse_numbers
    inline=getattr(source.document,'inline',{})
    return tuple(s.reference for s in source.document.spans
                 if s.end>first and s.body-(len(s.reference.rsplit('.',1)[-1])+1 if numbers else 0)
                 -sum(reference==s.reference for reference,_,_ in inline.values())<last)


def target(view,source,factory,clicked=None):
    selection=view.get_buffer().get_selection_bounds()
    if selection:first,last=(source.base+i.get_offset() for i in selection)
    elif clicked is not None:first=source.base+clicked;last=first+1
    else:return None
    refs=references(source,first,last)
    if not refs:return None
    chapters={};verses=[]
    for reference in refs:
        key=reference.rsplit('.',1)[0]
        if key not in chapters:chapters[key]=dict(source.reader.chapter(reference).verses)
        verses.append(chapters[key][reference])
    text=source.document.copy(first,last) if selection else '\n'.join(verses)
    anchor=view.get_buffer().get_iter_at_mark(view.get_buffer().get_insert()).get_offset() if selection else clicked
    return Target(source,view,factory,refs,text,tuple(verses),bool(selection),anchor)


class Backdrop(Gtk.Widget):
    """Blur only the underlying reader at this small, clipped action surface."""
    def do_snapshot(self,snapshot):
        bounds=Graphene.Rect().init(0,0,self.get_width(),self.get_height())
        radius=Graphene.Size().init(16,16)
        # init() returns a borrowed pointer for this non-boxed GSK struct.
        # Keep its owning Python instance alive until GTK copies the clip.
        rounded=Gsk.RoundedRect()
        rounded.init(bounds,radius,radius,radius,radius)
        snapshot.push_rounded_clip(rounded)
        surface=self.get_parent()
        actions=getattr(surface,'actions_owner',None)
        target=actions.target if actions else None
        high=bool(actions and actions.owner.reading_style.manager.get_high_contrast())
        if target and not high:
            view=target.view
            found,point=view.compute_point(self,Graphene.Point().init(0,0))
            if found:
                snapshot.push_blur(BACKDROP_BLUR)
                # Bound the blur input as well as its rounded output: never
                # allocate an offscreen texture the height of an entire book.
                padding=3*BACKDROP_BLUR
                sample=Graphene.Rect().init(-padding,-padding,bounds.size.width+2*padding,bounds.size.height+2*padding)
                snapshot.push_clip(sample);snapshot.save();snapshot.translate(point)
                surface.backdrop.get_current_image().snapshot(snapshot,view.get_width(),view.get_height())
                snapshot.restore();snapshot.pop();snapshot.pop()
        snapshot.pop()


class ActionSurface(Gtk.Overlay):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.backdrop=None;self._backdrop_signals=()
        self.background=Backdrop(hexpand=True,vexpand=True)
        self.set_child(self.background)
        self.connect('notify::visible',lambda *_:self.clear_backdrop() if not self.get_visible() else None)

    def clear_backdrop(self):
        if self.backdrop:
            for handler in self._backdrop_signals:self.backdrop.disconnect(handler)
            self.backdrop.set_widget(None)
        self.backdrop=None;self._backdrop_signals=()

    def set_backdrop(self,view):
        import weakref
        if self.backdrop and self.backdrop.get_widget() is view:return
        self.clear_backdrop()
        self.backdrop=Gtk.WidgetPaintable.new(view)
        background=weakref.ref(self.background)
        def changed(*_):
            widget=background()
            if widget and widget.get_mapped():
                actions=widget.get_parent().actions_owner
                if not actions.valid():actions.dismiss();return
                widget.queue_draw();actions.schedule_adapt()
        self._backdrop_signals=tuple(self.backdrop.connect(signal,changed) for signal in ('invalidate-contents','invalidate-size'))
        self.background.queue_draw()


class PassageActions:
    def __init__(self,owner):
        self.owner=owner;self.target=None;self.dragging=False;self.keyboard=False;self.adapt_tick=0;self._adapt_passes=0
        self.clearance=None;self.intent=0
        self.bar=ActionSurface(halign=Gtk.Align.CENTER,valign=Gtk.Align.END,
                         margin_start=12,margin_end=12,margin_bottom=12,visible=False)
        self.bar.actions_owner=self
        self.bar.add_css_class('passage-actions')
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        content.add_css_class('passage-actions-content')
        self.bar.add_overlay(content);self.bar.set_measure_overlay(content,True)
        self.bar.update_property([Gtk.AccessibleProperty.LABEL],[tr('Passage actions')])
        identity=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        self.label=Gtk.Label(wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,xalign=0)
        self.label.add_css_class('heading')
        self.version_label=Gtk.Label(ellipsize=Pango.EllipsizeMode.END,xalign=0)
        self.version_label.add_css_class('dim-label')
        identity.append(self.label);identity.append(self.version_label);content.append(identity)
        self.actions=Gtk.Box(spacing=4,halign=Gtk.Align.CENTER)
        self.actions.add_css_class('toolbar');content.append(self.actions)
        self.copy_button=Gtk.MenuButton(icon_name='edit-copy-symbolic',tooltip_text=tr('Copy'))
        self.copy_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Copy')])
        self.actions.append(self.copy_button)
        self.copy_options=self.copy_button  # One widget; retained internal compatibility name.
        self.copy_popover=self.menu(self.copy_button,[(label,lambda *_,mode=mode:self.copy(mode))
            for label,mode in [('Copy selected text','selected'),('Copy verses without numbers','verses'),
                               ('Copy verses with reference','reference'),('Copy reference','label')]])
        self.highlight_button=None
        if hasattr(owner,'highlights'):
            from .highlights import COLORS
            self.highlight_button=Gtk.MenuButton(icon_name='color-select-symbolic',tooltip_text=tr('Highlight'))
            self.highlight_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Highlight')])
            self.actions.append(self.highlight_button)
            self.highlight_popover=self.menu(self.highlight_button,[(label,lambda *_,c=color:self.highlight(c))
                for color,(_,label) in COLORS.items()]+[('Remove highlight',lambda *_:self.highlight(None)),
                    ('All highlights',lambda *_:owner.open_highlights())])
        self.note_button=self.button('bible-notes-symbolic','Add a passage note',lambda *_:self.note())
        self.compare_button=self.button('view-dual-symbolic','Compare translations',lambda *_:self.compare())
        self.word_button=self.button('accessories-dictionary-symbolic','Study word',lambda *_:self.study_word())
        self.close_button=self.button('window-close-symbolic','Dismiss passage actions',lambda *_:self.dismiss())
        for button in (self.copy_options,self.highlight_button):
            if button:button.set_child(Gtk.Image(icon_name=button.get_icon_name(),pixel_size=20))
        self.bar.connect('notify::visible',lambda *_:self.dismiss() if not self.bar.get_visible() and self.target else None)
        owner.view.connect('notify::selected-page',lambda *_:self.dismiss())
        gesture=Gtk.GestureClick(button=1);gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def outside(controller,_,x,y):
            event=controller.get_current_event()
            if self.target and event and event.get_surface()==owner.get_surface():
                widget=owner.pick(x,y,Gtk.PickFlags.DEFAULT)
                if not self.contains(widget):self.dismiss()
        gesture.connect('pressed',outside);owner.add_controller(gesture)
        keys=Gtk.EventControllerKey();keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect('key-pressed',self.key);owner.add_controller(keys)
        wheel=Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        wheel.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        wheel.connect('scroll',lambda *_:self.dismiss() or False);owner.add_controller(wheel)

    def contains(self,widget):return bool(widget and (widget is self.bar or widget.is_ancestor(self.bar)))

    def study_word(self):
        value=self.target
        if value is None:
            tab=self.owner.active_tab
            if not tab or not tab.reader:return
            view=self.owner.get_focus()
            comparison=view is tab.comparison_text
            view=tab.comparison_text if comparison else tab.text
            factory=lambda:self.ordinary(tab,comparison)
            source=factory()
            value=target(view,source,factory) if source else None
            if value is None:
                offset=tab._verse_offsets.get(tab.state.reference)
                source=self.ordinary(tab)
                if offset is not None:value=target(tab.text,source,lambda:self.ordinary(tab),offset)
        if value:self.owner.study.words.offer(value,self.word_button if self.word_button.get_mapped() else self.owner.study_button)

    def button(self,icon,label,callback):
        button=Gtk.Button(icon_name=icon,tooltip_text=tr(label))
        button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
        button.set_child(Gtk.Image(icon_name=icon,pixel_size=20))
        button.connect('clicked',callback);self.actions.append(button);return button

    def menu(self,button,choices):
        popover=Gtk.Popover(autohide=False);box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,
            margin_start=8,margin_end=8,margin_top=8,margin_bottom=8)
        for label,callback in choices:
            item=Gtk.Button(label=tr(label));item.add_css_class('flat')
            item.connect('clicked',callback);item.connect('clicked',lambda *_:popover.popdown());box.append(item)
        popover.set_child(box);button.set_popover(popover)
        popover.parent_dismissed=lambda widget:self.dismiss() if not self.contains(widget) else None
        self.owner._reading_popovers.append(popover);return popover

    def context_menu(self,view,factory):
        """Native text menu with deliberate, source-specific passage commands."""
        context=[None]
        def capture(x=None,y=None):
            source=factory()
            if not source:return
            if x is None:offset=view.get_buffer().get_iter_at_mark(view.get_buffer().get_insert()).get_offset()
            else:
                bx,by=view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET,int(x),int(y))
                found,iterator=view.get_iter_at_location(bx,by)
                offset=iterator.get_offset() if found else None
            context[0]=target(view,source,factory,offset)
        pointer=Gtk.GestureClick(button=3);pointer.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        pointer.connect('pressed',lambda _,n,x,y:capture(x,y));view.add_controller(pointer)
        keys=Gtk.EventControllerKey();keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def key(_,value,code,state):
            if value==Gdk.KEY_Menu or value==Gdk.KEY_F10 and state&Gdk.ModifierType.SHIFT_MASK:capture()
            return False
        keys.connect('key-pressed',key);view.add_controller(keys)
        group=Gio.SimpleActionGroup();menu=Gio.Menu()
        def execute(command):
            value=context[0]
            if value is None:capture();value=context[0]
            source=factory()
            if (not value or not source or source.tab is not self.owner.active_tab
                    or source.reader is not value.source.reader or source.resource!=value.source.resource
                    or source.document.key!=value.source.document.key):return
            if command=='note':
                self.owner.open_passage_notes((value.references[0],value.references[-1]),resource=source.resource,reader=source.reader)
            elif command=='word':self.owner.study.words.offer(value,view)
            elif command.startswith('highlight:'):
                self.owner.highlights.set(source.reader.versification,value.references,(None if command=='highlight:remove' else command.split(':')[1]),source.resource)
                self.owner.refresh_highlights()
            else:
                label=passage_label(value.references[0],value.references[-1],source.reader.versification)+' — '+module_name(source.resource)
                text=label if command=='label' else (label+'\n' if command=='reference' else '')+'\n'.join(value.verses)
                self.owner.get_clipboard().set(text)
        choices=[('Add a passage note','note'),('Copy verses without numbers','verses'),
                 ('Copy verses with reference','reference'),('Copy reference','label'),('Study word','word')]
        choices += [(tr('Highlight')+': '+tr(label),'highlight:'+color) for color,label in [('yellow','Yellow'),('green','Green'),('blue','Blue')]]
        choices.append(('Remove highlight','highlight:remove'))
        for index,(label,command) in enumerate(choices):
            name='action'+str(index);action=Gio.SimpleAction.new(name,None)
            action.connect('activate',lambda _,parameter,c=command:execute(c));group.add_action(action)
            menu.append(tr(label),'passage.'+name)
        view.insert_action_group('passage',group);view.set_extra_menu(menu)
        view._passage_context=group

    def ordinary(self,tab,comparison=False):
        reader=tab._comparison_reader if comparison else tab.reader
        doc=getattr(tab,'_comparison_document' if comparison else '_document',None)
        resource=tab.state.comparison if comparison else tab.state.resource
        if not reader or not doc or not resource:return None
        return Source(tab,resource,reader,doc,0,tab.comparison_overlay if comparison else tab.reading_overlay,
                      'comparison' if comparison else 'primary')

    def immersive(self,reading,view):
        page=getattr(view,'_study_page',None)
        if not page or not view.get_buffer().get_char_count():return None
        return Source(reading.tab,reading.source.resource.id,reading.source.reader,page[0],page[1],reading,'immersion')

    def bind(self,view,factory):
        self.context_menu(view,factory)
        def selection_changed(*_):
            if self.target and self.target.view is view and not view.get_buffer().get_has_selection():self.dismiss()
        view.get_buffer().connect('notify::has-selection',selection_changed)
        click=Gtk.GestureClick(button=1);click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        pending=[None]
        def pressed(controller,count,x,y):
            widget=view.pick(x,y,Gtk.PickFlags.DEFAULT)
            while widget and widget is not view:
                if widget.has_css_class('inline-marker'):return
                widget=widget.get_parent()
            event=controller.get_current_event()
            if event and getattr(self.owner,'_popup_dismissed_event_time',None)==event.get_time():return
            source=factory()
            if not source:return
            view.set_cursor_visible(False)
            self.dismiss();self.dragging=True;self.intent+=1;generation=self.intent
            bx,by=view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET,int(x),int(y))
            found,iterator=view.get_iter_at_location(bx,by)
            pending[0]=(source,iterator.get_offset() if found else None,generation)
        def released(*_):
            value=pending[0];pending[0]=None
            if not value:return
            source,offset,generation=value;self.dragging=False
            current=factory()
            if (generation==self.intent and current and current.reader is source.reader
                    and current.document.key==source.document.key):
                GLib.idle_add(self.capture,view,factory,offset,generation)
        click.connect('pressed',pressed);click.connect('released',released)
        click.connect('unpaired-release',released);view.add_controller(click)
        keys=Gtk.EventControllerKey();keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def pressed(_,value,code,state):
            selection_key=value in (Gdk.KEY_Left,Gdk.KEY_Right,Gdk.KEY_Up,Gdk.KEY_Down,Gdk.KEY_Home,Gdk.KEY_End,Gdk.KEY_Page_Up,Gdk.KEY_Page_Down)
            if (state&Gdk.ModifierType.SHIFT_MASK and selection_key) or (state&Gdk.ModifierType.CONTROL_MASK and value in (Gdk.KEY_a,Gdk.KEY_A)):
                view.set_cursor_visible(True)
                self.dismiss();self.keyboard=True
            elif value in (Gdk.KEY_Up,Gdk.KEY_Down,Gdk.KEY_Page_Up,Gdk.KEY_Page_Down,Gdk.KEY_Home,Gdk.KEY_End):self.dismiss()
            return False
        def released(controller,value,*args):
            if self.keyboard and value in (Gdk.KEY_Shift_L,Gdk.KEY_Shift_R,Gdk.KEY_a,Gdk.KEY_A):
                self.keyboard=False;GLib.idle_add(self.capture,view,factory,None)
        keys.connect('key-pressed',pressed);keys.connect('key-released',released);view.add_controller(keys)

    def capture(self,view,factory,clicked,generation=None):
        if generation is not None and generation!=self.intent:return False
        if self.owner.closed or not view.get_mapped():return False
        source=factory()
        if not source:return False
        value=target(view,source,factory,clicked)
        if not value or not value.native_selection or not value.text.strip():self.dismiss();return False
        self.target=value;self.bar.set_backdrop(view)
        parent=self.bar.get_parent()
        if parent is not source.parent:
            if parent:parent.remove_overlay(self.bar)
            source.parent.add_overlay(self.bar)
        label=passage_label(value.references[0],value.references[-1],source.reader.versification)
        resource=self.owner.library.resource(source.resource)
        version=resource.description+' — '+resource.source
        self.label.set_text(label);self.label.set_tooltip_text(label)
        self.version_label.set_text(version);self.version_label.set_tooltip_text(version)
        self.bar.update_property([Gtk.AccessibleProperty.LABEL],[label+' — '+version])
        self.copy_button.set_tooltip_text(tr('Copy'))
        self.note_button.set_sensitive(self.owner.notes_store is not None)
        self.bar.set_visible(True)
        self.schedule_adapt()
        self.bar.set_margin_bottom(0 if source.side=='immersion' else 12)
        self.compare_button.set_sensitive(source.tab.reader is not None)
        return False

    def schedule_adapt(self):
        if not self.target or not self.bar.get_visible():return
        # Settle a changed native allocation, then stop. No idle frame polling.
        self._adapt_passes=2
        if not self.adapt_tick:self.adapt_tick=self.bar.add_tick_callback(self._adapt_layout)

    def _adapt_layout(self,*_):
        self.adapt();self._adapt_passes-=1
        pending=bool(self.target and self._adapt_passes>0)
        if not pending:self.adapt_tick=0
        return pending

    def adapt(self,*_):
        value=self.target
        if not value:return True
        parent=value.source.parent
        available=max(1,parent.get_width()-48)
        # Pango wrapping gives the reference priority; secondary metadata ellipsizes.
        em=max(1,self.version_label.create_pango_layout('M').get_pixel_size()[0])
        chars=max(8,min(38,available//em))
        self.label.set_max_width_chars(chars);self.version_label.set_max_width_chars(chars)
        margin_bottom=12
        from gi.repository import Graphene
        buffer=value.view.get_buffer()
        bounds=buffer.get_selection_bounds() if value.native_selection else ()
        positions=bounds or (buffer.get_iter_at_offset(value.anchor),)
        lines=[]
        for iterator in positions:
            location=value.view.get_iter_location(iterator)
            x,y=value.view.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,location.x,location.y)
            ok,point=value.view.compute_point(parent,Graphene.Point().init(float(x),float(y)))
            if ok:lines.append((point.y,point.y+location.height))
        if lines:
            start=min(y for y,_ in lines);end=max(y for _,y in lines)
            bottom=parent.get_height()-12
            bar_top=bottom-self.bar.get_height()
            if end>bar_top and start<bottom:
                # Move the bar above a lower selection without moving the reader.
                margin=int(parent.get_height()-start+12)
                if parent.get_height()-margin-self.bar.get_height()>=8:
                    margin_bottom=margin
        if self.bar.get_margin_bottom()!=margin_bottom:
            self.bar.set_margin_bottom(margin_bottom);self.bar.background.queue_draw()
        return True

    def valid(self):
        value=self.target
        if not value or self.owner.closed or self.owner.active_tab is not value.source.tab:return False
        current=value.factory()
        if not (current and current.resource==value.source.resource and current.reader is value.source.reader
                and current.document.key==value.source.document.key):return False
        reflow=current.tab._restoring_scroll or getattr(current.tab,'_comparison_positioning',False)
        reflow=reflow or (self.owner.immersion and not self.owner.immersion.layout_ready)
        if value.native_selection and not reflow:
            bounds=value.view.get_buffer().get_selection_bounds()
            if not bounds:return False
            first,last=(current.base+i.get_offset() for i in bounds)
            if references(current,first,last)!=value.references or current.document.copy(first,last)!=value.text:return False
        return True

    def key(self,controller,value,*_):
        if value==Gdk.KEY_Escape and self.target:
            if any(p.get_visible() for p in self.owner._reading_popovers):return False
            self.dismiss();return True
        return False

    def dismiss(self):
        self.intent+=1
        self.keyboard=False
        if self.adapt_tick:self.bar.remove_tick_callback(self.adapt_tick);self.adapt_tick=0
        value=self.target;restore=bool(value and self.contains(self.owner.get_focus()))
        self.target=None;self.bar.clear_backdrop();self.bar.set_visible(False)
        if self.clearance:
            view,original,margin=self.clearance
            if view.get_bottom_margin()==margin:view.set_bottom_margin(original)
            self.clearance=None
        self.copy_popover.popdown()
        if self.highlight_button:self.highlight_popover.popdown()
        if restore and value.view.get_mapped():value.view.grab_focus()

    def copy(self,mode='selected'):
        if not self.valid():self.dismiss();return
        value=self.target
        label=passage_label(value.references[0],value.references[-1],value.source.reader.versification)+' — '+module_name(value.source.resource)
        text=value.text if mode=='selected' else '\n'.join(value.verses)
        if mode=='reference':text=label+'\n'+text
        if mode=='label':text=label
        self.owner.get_clipboard().set(text)

    def note(self):
        if self.valid():
            value=self.target
            self.owner.open_passage_notes((value.references[0],value.references[-1]),
                resource=value.source.resource,reader=value.source.reader)

    def highlight(self,color):
        if not self.valid():self.dismiss();return
        value=self.target
        try:
            if len(value.references)>1000:raise ValueError('Select at most 1000 verses')
            self.owner.highlights.set(value.source.reader.versification,value.references,color,value.source.resource)
            self.owner.refresh_highlights()
        except (ValueError,OSError) as error:
            value.source.tab.status.set_text(str(error));value.source.tab.status.set_visible(True)

    def compare(self):
        if not self.valid():self.dismiss();return
        value=self.target;tab=value.source.tab
        from .reference_resolution import resolve
        try:
            reference=resolve(value.references[0],value.source.reader.versification,tab.reader).start
            if self.owner.immersion:self.owner.leave_immersion()
            tab.reveal_reference(reference);self.owner.show_comparison()
        except ValueError as error:
            tab.comparison_status.set_text(str(error))
