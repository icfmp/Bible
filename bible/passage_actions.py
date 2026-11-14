"""Intent-driven passage actions with frozen source/range/copy targets."""
from dataclasses import dataclass
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango, Graphene, Gsk
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
    selection: tuple | None = None


def references(source,first,last):
    numbers=source.tab.preferences.verse_numbers
    refs=tuple(dict.fromkeys(ref for s in source.document.spans
                 if s.end>first and s.body-(len(s.number)+1 if numbers and s.number else 0)<last for ref in s.members))
    if getattr(source.reader,'addresses',None):refs=tuple(sorted(refs,key=source.reader.reference_sort_key))
    return refs


def target(view,source,factory,clicked=None):
    selection=view.get_buffer().get_selection_bounds()
    if selection:first,last=(source.base+i.get_offset() for i in selection)
    elif clicked is not None:first=source.base+clicked;last=first+1
    else:return None
    refs=references(source,first,last)
    if not refs:return None
    from .sword_provider import passage_verses
    verses=[text for _,text in passage_verses(source.reader,refs)]
    text=source.document.copy(first,last) if selection else '\n'.join(verses)
    anchor=view.get_buffer().get_iter_at_mark(view.get_buffer().get_insert()).get_offset() if selection else clicked
    return Target(source,view,factory,refs,text,tuple(verses),bool(selection),anchor,
                  (first,last) if selection else None)


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
    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.backdrop=None;self._backdrop_signals=()
        self.background=Backdrop(hexpand=True,vexpand=True)
        self.background.set_can_target(False);self.add_overlay(self.background)
        self.connect('notify::visible',lambda *_:self.clear_backdrop() if not self.get_visible() else None)

    def do_snapshot(self,snapshot):
        # Keep GTK measuring/allocating the actual content as the main child.
        # Paint its cached backdrop first, then its controls and translucent tint.
        self.snapshot_child(self.background,snapshot)
        if self.get_child():self.snapshot_child(self.get_child(),snapshot)

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
        self.capture_idle=0
        self._pointer_release=None;self._native_drags={}
        self.bar=ActionSurface(halign=Gtk.Align.CENTER,valign=Gtk.Align.END,
                         margin_start=12,margin_end=12,margin_bottom=12,visible=False)
        self.bar.actions_owner=self
        self.bar.add_css_class('passage-actions')
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        content.add_css_class('passage-actions-content')
        self.bar.set_child(content)
        self.bar.update_property([Gtk.AccessibleProperty.LABEL],[tr('Passage actions')])
        identity=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        self.label=Gtk.Label(wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,xalign=0)
        self.label.add_css_class('heading')
        self.version_label=Gtk.Label(ellipsize=Pango.EllipsizeMode.END,xalign=0)
        self.version_label.add_css_class('dim-label')
        identity.append(self.label);identity.append(self.version_label);content.append(identity)
        self.actions=(Adw.WrapBox(child_spacing=4,line_spacing=4,natural_line_length=340)
            if hasattr(Adw,'WrapBox') else Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,column_spacing=4,row_spacing=4,
                min_children_per_line=1,max_children_per_line=20,halign=Gtk.Align.FILL))
        self.actions.add_css_class('toolbar')
        self.actions_clamp=Adw.Clamp(child=self.actions,maximum_size=340,tightening_threshold=340,unit=Adw.LengthUnit.PX)
        content.append(self.actions_clamp)
        self.copy_button=Gtk.MenuButton(icon_name='edit-copy-symbolic',tooltip_text=tr('Copy'))
        self.copy_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Copy')])
        self.actions.append(self.copy_button)
        self.copy_options=self.copy_button  # One widget; retained internal compatibility name.
        self.copy_popover=self.menu(self.copy_button,[(label,lambda *_,mode=mode:self.copy(mode))
            for label,mode in [('Copy selected text','selected'),('Copy verses without numbers','verses'),
                               ('Copy verses with reference','reference'),('Copy reference','label')]])
        self.highlight_button=None;self.highlight_buttons={}
        if hasattr(owner,'highlights'):
            from .highlights import COLORS
            for color,(_,label) in COLORS.items():
                button=Gtk.ToggleButton(tooltip_text=tr('Highlight')+': '+tr(label))
                button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Highlight')+': '+tr(label)])
                circle=Gtk.Box(width_request=20,height_request=20,halign=Gtk.Align.CENTER,valign=Gtk.Align.CENTER)
                circle.add_css_class('highlight-'+color)
                check=Gtk.Image(icon_name='object-select-symbolic',pixel_size=14,opacity=0);circle.append(check)
                button.set_child(circle);button.connect('clicked',lambda *_,c=color:self.highlight(c))
                self.actions.append(button);self.highlight_buttons[color]=(button,check)
        self.note_button=self.button('notebook-symbolic','Add a passage note',lambda *_:self.note())
        self.word_button=self.button('accessories-dictionary-symbolic','Original text',lambda *_:self.study_word())
        word=Gtk.Box(spacing=6)
        word.append(Gtk.Image(icon_name='accessories-dictionary-symbolic',pixel_size=20))
        word.append(Gtk.Label(label=tr('Original text')));self.word_button.set_child(word)
        self.word_button.set_tooltip_text(tr('Study original text'))
        self.word_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Study original text')])
        if isinstance(self.actions,Gtk.FlowBox):
            # Older Adwaita uses FlowBox wrappers; only the actual controls
            # belong in the toolbar's keyboard traversal order.
            child=self.actions.get_first_child()
            while child:
                child.set_focusable(False);child=child.get_next_sibling()
        for button in (self.copy_options,self.highlight_button):
            if button:button.set_child(Gtk.Image(icon_name=button.get_icon_name(),pixel_size=20))
        self.bar.connect('notify::visible',lambda *_:self.dismiss() if not self.bar.get_visible() and self.target else None)
        owner.view.connect('notify::selected-page',lambda *_:self.dismiss())
        gesture=Gtk.GestureClick(button=1);gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def outside(controller,_,x,y):
            event=controller.get_current_event()
            if (self.target or self.dragging) and event and event.get_surface()==owner.get_surface():
                widget=owner.pick(x,y,Gtk.PickFlags.DEFAULT)
                if not self.contains(widget):self.dismiss()
        gesture.connect('pressed',outside);owner.add_controller(gesture)
        keys=Gtk.EventControllerKey();keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect('key-pressed',self.key);owner.add_controller(keys)
        wheel=Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        wheel.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        wheel.connect('scroll',lambda *_:self.dismiss() or False);owner.add_controller(wheel)
        # GestureClick can stop before a child TextView releases its selection.
        # Observe the physical release without claiming GTK's native gesture.
        release=Gtk.EventControllerLegacy();release.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def pointer_event(controller,_event):
            if not self._pointer_release:return False
            event=controller.get_current_event()
            if (event and event.get_event_type()==Gdk.EventType.BUTTON_RELEASE
                    and event.get_button()==1 and event.get_surface()==owner.get_surface()):
                self._pointer_release[0]()
            return False
        release.connect('event',pointer_event);owner.add_controller(release)
        # TextView starts its own Gdk.Drag when pressing inside a selection.
        # That native grab replaces GestureClick's release. Observe the local
        # drop passively and finish through the same selection callback.
        drop=Gtk.DropControllerMotion();drop.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drop.connect('enter',self.native_drag_motion);drop.connect('motion',self.native_drag_motion)
        owner.add_controller(drop)

    def native_drag_motion(self,controller,*_):
        pending=self._pointer_release
        if not pending:return
        _,generation,view=pending
        if generation!=self.intent or not view.get_mapped():return
        drop=controller.get_drop();drag=drop.get_drag() if drop else None
        if drag is None or drag in self._native_drags:return
        # A pending press on this reading view owns the current gesture.
        # get_drag() excludes external applications; GTK text drags expose
        # TextBuffer content. Backend drag surfaces are not source toplevels.
        if not (view.get_buffer().get_has_selection()
                and drag.get_content().ref_formats().contain_gtype(Gtk.TextBuffer)):return
        import weakref
        owner=weakref.ref(self)
        def finished(drag,reason=None):
            actions=owner()
            if actions:actions.native_drag_finished(drag,reason,generation)
        self._native_drags[drag]=(drag.connect('cancel',finished),drag.connect('dnd-finished',finished))

    def native_drag_finished(self,drag,reason,generation):
        for handler in self._native_drags.pop(drag,()):
            if drag.handler_is_connected(handler):drag.disconnect(handler)
        pending=self._pointer_release
        if not pending or generation!=self.intent or pending[1]!=generation:return
        if reason not in (None,Gdk.DragCancelReason.NO_TARGET) or not self.owner.is_active():
            self.dismiss();return
        self._pointer_release=None
        pending[0]()

    def contains(self,widget):return bool(widget and (widget is self.bar or widget.is_ancestor(self.bar)))

    def study_word(self):
        value=self.target
        if value is not None and not self.valid():self.dismiss();return
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
                 ('Copy verses with reference','reference'),('Copy reference','label'),('Original text','word')]
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
        pointer=Gtk.EventControllerLegacy();pointer.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        pending=[None]
        def pointer_pressed(controller,count,x,y):
            widget=view.pick(x,y,Gtk.PickFlags.DEFAULT)
            while widget and widget is not view:
                if widget.has_css_class('inline-marker'):
                    pending[0]=None;self.dismiss();return
                widget=widget.get_parent()
            event=controller.get_current_event()
            if event and getattr(self.owner,'_popup_dismissed_event_time',None)==event.get_time():return
            source=factory()
            if not source:return
            view.set_cursor_visible(False)
            self.dismiss();self.dragging=True;self.intent+=1;generation=self.intent
            view.grab_focus()
            bx,by=view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET,int(x),int(y))
            found,iterator=view.get_iter_at_location(bx,by)
            pending[0]=(source,iterator.get_offset() if found else None,generation)
            self._pointer_release=(pointer_released,generation,view)
        def pointer_released(*_):
            value=pending[0];pending[0]=None
            if not value:return
            source,offset,generation=value
            if generation!=self.intent:return
            if self._pointer_release and self._pointer_release[:2]==(pointer_released,generation):self._pointer_release=None
            self.dragging=False
            current=factory()
            if (generation==self.intent and current and current.reader is source.reader
                    and current.document.key==source.document.key):
                self.schedule_capture(view,factory,offset,generation)
        def pointer_event(controller,event):
            event=event or controller.get_current_event()
            if event and event.get_event_type()==Gdk.EventType.BUTTON_PRESS and event.get_button()==1:
                native=view.get_native();found,bounds=view.compute_bounds(native)
                if found:
                    _,x,y=event.get_position();dx,dy=native.get_surface_transform()
                    pointer_pressed(controller,1,x-dx-bounds.origin.x,y-dy-bounds.origin.y)
            return False
        pointer.connect('event',pointer_event);view.add_controller(pointer)
        touch=Gtk.GestureClick(button=1,touch_only=True)
        touch.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        touch.connect('pressed',pointer_pressed);touch.connect('released',pointer_released)
        touch.connect('unpaired-release',pointer_released);view.add_controller(touch)
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
                self.keyboard=False;self.schedule_capture(view,factory,None,self.intent)
        keys.connect('key-pressed',pressed);keys.connect('key-released',released);view.add_controller(keys)

    def cancel_capture(self):
        if self.capture_idle:GLib.source_remove(self.capture_idle);self.capture_idle=0

    def schedule_capture(self,view,factory,clicked,generation):
        # A newer gesture/dismissal owns the selection. An old keyboard idle
        # must never inspect a new mouse drag and cancel its completion.
        self.cancel_capture()
        self.capture_idle=GLib.idle_add(self.capture_pending,view,factory,clicked,generation)

    def capture_pending(self,view,factory,clicked,generation):
        self.capture_idle=0
        return self.capture(view,factory,clicked,generation)

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
        self.version_label.set_text(resource.public_code or resource.description);self.version_label.set_tooltip_text(version)
        self.bar.update_property([Gtk.AccessibleProperty.LABEL],[label+' — '+version])
        self.copy_button.set_tooltip_text(tr('Copy'))
        self.note_button.set_sensitive(self.owner.notes_store is not None)
        self.bar.set_visible(True)
        self.schedule_adapt()
        self.bar.set_margin_bottom(0 if source.side=='immersion' else 12)
        self.sync_highlights()
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
        # Measure the controls, including native padding, instead of reserving
        # a fixed desktop line. Adwaita1.7's unlimited (-1) line request can
        # propagate INT_MAX through an overlay, so retain a finite native size.
        widths=[];child=self.actions.get_first_child()
        while child:
            if child.get_visible():widths.append(child.measure(Gtk.Orientation.HORIZONTAL,-1)[1])
            child=child.get_next_sibling()
        padding=self.actions.get_style_context().get_padding()
        natural=sum(widths)+4*max(0,len(widths)-1)+padding.left+padding.right
        width=max(1,min(available,natural))
        if hasattr(self.actions,'set_natural_line_length'):self.actions.set_natural_line_length(width)
        self.actions_clamp.set_maximum_size(width);self.actions_clamp.set_tightening_threshold(width)
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
            if value.selection is not None and (first,last)!=value.selection:return False
            if references(current,first,last)!=value.references or current.document.copy(first,last)!=value.text:return False
        return True

    def key(self,controller,value,*_):
        if value==Gdk.KEY_Escape and (self.target or self.capture_idle or self.keyboard or self.dragging):
            if any(p.get_visible() for p in self.owner._reading_popovers):return False
            native=bool(self._native_drags)
            self.dismiss();return not native
        return False

    def dismiss(self):
        self.intent+=1
        self.keyboard=False;self.dragging=False
        self._pointer_release=None
        for drag,handlers in tuple(self._native_drags.items()):
            for handler in handlers:
                if drag.handler_is_connected(handler):drag.disconnect(handler)
        self._native_drags.clear()
        self.cancel_capture()
        # Still invalidate a pending selection capture, but do no native popup
        # or backdrop work for each wheel event when everything is already hidden.
        if self.target is None and not self.adapt_tick and self.clearance is None and not self.bar.get_visible():return
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
            self.owner.refresh_highlights();self.sync_highlights()
        except (ValueError,OSError) as error:
            value.source.tab.status.set_text(str(error));value.source.tab.status.set_visible(True)

    def sync_highlights(self):
        value=self.target
        if not value:return
        colors={self.owner.highlights.entries.get((value.source.reader.versification,ref),{}).get('color') for ref in value.references}
        for color,(button,check) in self.highlight_buttons.items():
            active=colors=={color};button.set_active(active);check.set_opacity(1 if active else 0)

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
