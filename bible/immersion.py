"""Native paginated full-screen Bible/commentary reading with reversible UI state."""
import time
import gi

gi.require_version('Gtk','4.0')
gi.require_version('Adw','1')
from gi.repository import Adw,Gdk,Gio,GLib,Gtk,Pango
from .i18n import tr
from .pagination import Anchor
from .paged_sources import PagedStream,PageAddress
from .reading_style import SPACING,WIDTHS
from .notes_window import passage_label


class Immersion(Gtk.Overlay):
    def __init__(self,owner,source,key,anchor):
        super().__init__()
        self.add_css_class(owner.reading_style.scope+'-surface')
        self.owner=owner;self.tab=owner.active_tab;self.source=source;self.kind=source.kind
        self.initial_key=key;self.initial_anchor=anchor;self.was_fullscreen=owner.is_fullscreen()
        self._geometry=None;self._hide_id=0;self._last_turn=0;self._wheel=0
        self._geometry_candidate=None;self._geometry_since=0
        self._gesture_turned=False;self._pointer_top=False;self._pointer_edge=False;self._updating=False;self.selection=None;self.addresses=[]
        self.views=[];self.frames=[];self.count=2;self._closed=False
        self.clicked_reference=None
        self.layout_ready=False;self._stable_frames=0;self._selection_restore_pending=False;self._allocation_signature=None
        body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.pages=Gtk.Box(spacing=32,homogeneous=True,hexpand=True,vexpand=True,halign=Gtk.Align.CENTER,
                           margin_top=48,margin_bottom=48,margin_start=56,margin_end=56)
        self.pages.set_direction(Gtk.TextDirection.LTR if self.kind=='bible' else
                                 Gtk.TextDirection.RTL if source.rtl else Gtk.TextDirection.LTR)
        for number in range(2):
            from .context_indicator import ContextTextView
            view=ContextTextView(editable=False,cursor_visible=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,
                              left_margin=8,right_margin=8,top_margin=12,bottom_margin=12,hexpand=True,vexpand=True)
            view.set_direction(Gtk.TextDirection.RTL if source.rtl else Gtk.TextDirection.LTR)
            if source.rtl:view.set_justification(Gtk.Justification.RIGHT)
            view.update_property([Gtk.AccessibleProperty.LABEL],[tr('Reading page')+' '+str(number+1)])
            view.add_css_class(owner.reading_style.scope)
            owner.reading_style.views.add(view)
            view._reading_palette=owner.reading_style.palette
            if self.kind=='bible':
                owner.passage_actions.bind(view,lambda v=view:owner.passage_actions.immersive(self,v))
            gesture=Gtk.GestureClick(button=1)
            gesture.connect('released',lambda g,n,x,y,v=view:self.clicked(v,x,y));view.add_controller(gesture)
            view.get_buffer().connect('mark-set',lambda *_,v=view:self.selection_changed(v))
            view.connect('copy-clipboard',self.copy_selection)
            if self.kind=='bible':
                menu=Gio.Menu();menu.append(tr('Add a passage note'),'win.note')
                menu.append(tr('Copy verses without numbers'),'win.copy-passage')
                menu.append(tr('Copy verses with reference'),'win.copy-with-reference')
                menu.append(tr('Copy reference'),'win.copy-reference');view.set_extra_menu(menu)
                for color,label in [('yellow','Yellow'),('green','Green'),('blue','Blue')]:
                    menu.append(tr('Highlight')+': '+tr(label),'win.highlight-'+color)
                menu.append(tr('Remove highlight'),'win.highlight-remove')
            frame=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.EXTERNAL,vscrollbar_policy=Gtk.PolicyType.EXTERNAL,
                                     min_content_height=0,propagate_natural_height=False,hexpand=True,vexpand=True)
            frame.set_child(view);self.pages.append(frame);self.frames.append(frame);self.views.append(view)
        self.pages.set_halign(Gtk.Align.FILL)
        self.page_clamp=Adw.Clamp(child=self.pages,maximum_size=1200,tightening_threshold=1200,vexpand=True)
        self.page_stack=Gtk.Stack(transition_duration=200,hhomogeneous=False,vhomogeneous=False,vexpand=True)
        self.previous_page=Gtk.Picture(can_shrink=True)
        self.page_stack.add_named(self.page_clamp,'live');self.page_stack.add_named(self.previous_page,'previous')
        self.page_stack.set_visible_child_name('live');self._slide_serial=0
        body.append(self.page_stack)
        self.footer=Gtk.Label(ellipsize=Pango.EllipsizeMode.END,margin_start=24,margin_end=24,margin_bottom=12)
        self.footer.add_css_class('dim-label');body.append(self.footer);self.set_child(body)
        if getattr(source,'book_pages',False):
            from .book_stream import BookStream
            self.stream=BookStream(self.views[0],source,owner.preferences.value)
        else:self.stream=PagedStream(self.views[0],source,owner.preferences.value)
        self.top=Gtk.Revealer(reveal_child=True,transition_type=Gtk.RevealerTransitionType.CROSSFADE,transition_duration=200,
                              valign=Gtk.Align.START,halign=Gtk.Align.FILL)
        controls=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header=Adw.HeaderBar(show_start_title_buttons=False,show_end_title_buttons=False)
        header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        self.leave_button=Gtk.ToggleButton(icon_name='view-restore-symbolic',active=True,
                                           tooltip_text=tr('Leave immersive mode'))
        self.leave_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Leave immersive mode')])
        self.leave_button.connect('clicked',lambda *_:owner.leave_immersion())
        self.caption=Gtk.Label(label=source.resource.name,ellipsize=Pango.EllipsizeMode.END,max_width_chars=18,width_chars=1)
        self.passage_button=(Gtk.MenuButton(child=self.caption) if self.kind=='bible' else Gtk.Button(child=self.caption))
        if self.kind=='commentary':self.passage_button.connect('clicked',lambda *_:self.info.popup())
        self.passage_button.set_tooltip_text(tr('Choose a passage') if self.kind=='bible' else source.resource.description)
        if self.kind=='bible':
            owner.passage_button.popdown();owner.passage_button.set_popover(None)
            self.passage_button.set_popover(owner.navigation)
        header.set_title_widget(self.passage_button)
        self.aa=Gtk.MenuButton(child=Gtk.Label(label='Aa'),tooltip_text=tr('Reading appearance'))
        owner.appearance_button.popdown();owner.appearance_button.set_popover(None)
        self.aa.set_popover(owner.appearance)
        commands=Gio.Menu()
        if self.kind=='commentary':
            commands.append(tr('Previous available entry'),'win.previous-commentary-entry')
            commands.append(tr('Next available entry'),'win.next-commentary-entry')
            commands.append(tr('Open this passage in the Bible'),'win.immersive-open-bible')
        from .application_surfaces import application_menu
        self.menu=application_menu()
        if self.kind=='commentary':
            contextual=Gtk.MenuButton(icon_name='view-more-symbolic',menu_model=commands,tooltip_text=tr('Commentary actions'))
            header.pack_start(contextual)
        header.pack_start(self.menu);header.pack_end(self.aa);header.pack_end(self.leave_button)
        self.header=header
        if self.kind=='bible':
            owner.reader_controls.remove(owner.primary_version)
            header.pack_end(owner.primary_version)
        for button in (self.aa,self.leave_button):
            button.add_css_class('circular');button.add_css_class('reader-action')
        if self.kind=='commentary':
            self.entry_previous=Gtk.Button(icon_name='go-previous-symbolic')
            self.entry_next=Gtk.Button(icon_name='go-next-symbolic')
            self.entry_previous.connect('clicked',lambda *_:self.change_entry(-1))
            self.entry_next.connect('clicked',lambda *_:self.change_entry(1))
            header.pack_start(self.entry_previous);header.pack_start(self.entry_next)
            self.open_bible=Gtk.Button(label=tr('Open this passage in the Bible'))
            self.open_bible.connect('clicked',lambda *_:self.open_in_bible());header.pack_end(self.open_bible)
            self.info=Gtk.MenuButton(icon_name='dialog-information-symbolic',tooltip_text=tr('Source and conditions'))
            from .resource_details import details
            pop=Gtk.Popover();label=Gtk.Label(label=details(source.resource),selectable=True,wrap=True,max_width_chars=36,
                                           margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
            scroll=Gtk.ScrolledWindow(max_content_height=350,propagate_natural_height=True);scroll.set_child(label)
            pop.set_child(scroll);self.info.set_popover(pop);header.pack_end(self.info)
        controls.append(header)
        self.notification_help=Adw.Banner(title=tr('In GNOME, turn on Do Not Disturb in the clock menu. Bible does not change notifications.'),
                                          button_label=tr('Do not show again'))
        self.notification_help.connect('button-clicked',lambda *_:self.hide_help())
        self.notification_help.set_revealed(not owner.immersion_hints.disabled and not owner._immersion_help_seen)
        owner._immersion_help_seen=True
        controls.append(self.notification_help);self.top.set_child(controls);self.add_overlay(self.top)
        self.nav_revealers=[]
        self.back=self.page_button(-1);self.forward=self.page_button(1)
        self.buttons=[self.back,self.forward]
        motion=Gtk.EventControllerMotion();motion.connect('motion',self.pointer_moved);motion.connect('leave',lambda *_:self.pointer_left());self.add_controller(motion)
        keys=Gtk.EventControllerKey();keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect('key-pressed',self.key_pressed);self.add_controller(keys)
        pointer=Gtk.GestureClick(button=0);pointer.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        pointer.connect('pressed',lambda *_:owner.set_focus_visible(False));self.add_controller(pointer)
        wheel=Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES|Gtk.EventControllerScrollFlags.KINETIC)
        wheel.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        wheel.connect('scroll-begin',lambda *_:self.begin_scroll())
        wheel.connect('scroll-end',lambda *_:self.end_scroll())
        wheel.connect('scroll',self.wheel_scroll);self.add_controller(wheel)
        self._tick=self.add_tick_callback(self.adapt)
        self.reveal_controls()

    def page_button(self,direction):
        icon='go-previous-symbolic' if (direction<0)!=self.source.rtl else 'go-next-symbolic'
        button=Gtk.Button(icon_name=icon,tooltip_text=tr('Previous pages') if direction<0 else tr('Next pages'),
                          valign=Gtk.Align.CENTER,halign=(Gtk.Align.END if self.source.rtl else Gtk.Align.START) if direction<0 else
                          (Gtk.Align.START if self.source.rtl else Gtk.Align.END),margin_start=8,margin_end=8)
        button.add_css_class('circular');button.add_css_class('osd');button.add_css_class('chapter-navigation')
        button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Previous pages') if direction<0 else tr('Next pages')])
        button.connect('clicked',lambda *_:self.turn(direction))
        reveal=Gtk.Revealer(child=button,reveal_child=True,transition_type=Gtk.RevealerTransitionType.CROSSFADE,transition_duration=200,halign=button.get_halign(),valign=Gtk.Align.CENTER)
        self.nav_revealers.append(reveal);self.add_overlay(reveal);return button

    def adapt(self,*_):
        if self._closed:return False
        if hasattr(self.stream,'poll'):
            changed=self.stream.poll()
            if changed=='current':self.render()
            elif changed=='controls' and self.stream.cursor:self.update_page_buttons()
        width,height=self.get_width(),self.get_height()
        if width<100 or height<100:return True
        from .navigation_overlay import position
        ok,first=self.frames[0].compute_bounds(self)
        last_frame=self.frames[1] if self.count==2 else self.frames[0]
        last_ok,last=last_frame.compute_bounds(self)
        if ok and last_ok:
            for button in self.nav_revealers:
                position(button,first.origin.x+self.views[0].get_left_margin(),
                         last.origin.x+last.size.width-self.views[-1].get_right_margin(),
                         first.origin.y,first.size.height,width)
        minimum=max(280,self.owner.preferences.value.size*15)
        count=2 if (width-112-32)/2>=minimum else 1
        usable=min(WIDTHS[self.owner.preferences.value.column_width],int((width-112-(32 if count==2 else 0))/count))
        usable=max(40,usable-16)
        page_height=max(40,self.pages.get_height()-24)
        geometry=(usable,page_height,count)
        if self.kind=='commentary':
            self.entry_previous.set_visible(width>=700);self.entry_next.set_visible(width>=700)
            self.open_bible.set_visible(width>=700);self.info.set_visible(width>=500)
        if geometry!=self._geometry:
            self.cancel_slide()
            anchor=self.stream.anchor() if self.stream.cursor else self.initial_anchor
            key=self.stream.cursor.key if self.stream.cursor else self.initial_key
            self.count=count;self.frames[1].set_visible(count==2);self.views[1].set_visible(count==2)
            maximum=(usable+16)*count+(32 if count==2 else 0)+112
            self.page_clamp.set_maximum_size(maximum);self.page_clamp.set_tightening_threshold(maximum)
            # Settle allocations before scheduling expensive work. Rapid resize
            # and consecutive Aa changes should prepare only the last geometry.
            if geometry!=self._geometry_candidate:
                self._geometry_candidate=geometry;self._geometry_since=time.monotonic()
                return True
            if time.monotonic()-self._geometry_since<.08:return True
            self._geometry=geometry;self.stream.spread_count=count
            self.stream.configure(usable,page_height,anchor,key);self.render()
        else:
            if self.stream.cursor is None:return True
            allocation=tuple((view.get_width(),view.get_height()) for view in self.views[:self.count])
            if allocation!=self._allocation_signature:
                self._allocation_signature=allocation;self._stable_frames=0;self.layout_ready=False
            else:self._stable_frames+=1
            if self._stable_frames==2:
                # GTK may complete font layout/selection ownership after render.
                # Reapply canonical bounds only once the allocations are stable.
                self._updating=True
                try:self.restore_selection()
                finally:self._updating=False
                self._selection_restore_pending=False;self.layout_ready=True
        return True

    def reflow(self):
        self.cancel_slide()
        if self._closed:return
        self.clicked_reference=None
        self.capture_selection();self._restored_selection=bool(self.selection)
        self.layout_ready=False;self._stable_frames=0;self._selection_restore_pending=bool(self.selection);self._allocation_signature=None
        anchor=self.stream.anchor() if self.stream.cursor else self.initial_anchor
        key=self.stream.cursor.key if self.stream.cursor else self.initial_key
        self._geometry=None;self.initial_anchor=anchor;self.initial_key=key
        self._geometry_candidate=None
        # Keep the stream anchor until adapt recalculates both geometry and pages.
        if hasattr(self.stream,'cancel_pending'):self.stream.cancel_pending()
        self.stream.cursor=None

    def capture_selection(self):
        if self._updating:return
        for view,address in zip(self.views,self.addresses):
            bounds=view.get_buffer().get_selection_bounds()
            if bounds:
                plan=self.stream.plan(address.key);page=plan.pages[address.index]
                self.selection=(address.key,*(plan.document.anchor(page.start+i.get_offset()) for i in bounds))
                return

    def selection_changed(self,view):
        if self._updating or self._selection_restore_pending:return
        self._restored_selection=False
        if view.get_buffer().get_has_selection():self.capture_selection()
        elif not any(v.get_buffer().get_has_selection() for v in self.views):self.selection=None

    def update_study_indicator(self):
        for view in self.views:
            context=getattr(view,'_study_page',None)
            if self.kind!='bible' or not context:
                view.set_study_ranges([]);continue
            document,first,last=context
            ranges=[]
            for span in document.spans:
                number=len(span.reference.rsplit('.',1)[-1])+1 if self.owner.preferences.value.verse_numbers else 0
                begin=max(first,span.body-number);end=min(last,span.end)
                if end>begin:ranges.append((span.reference,begin-first,end-first))
            view.set_study_ranges([])  # Clean immersive presentation; ordinary coverage is untouched.

    def render(self):
        if not self.stream.cursor:
            self.clicked_reference=None
            self._updating=True;self.addresses=[];self.layout_ready=False
            for view in self.views:
                view._study_page=None
                view.set_study_ranges([])
                view.get_buffer().set_text('')
            self._updating=False
            self.back.set_sensitive(False);self.forward.set_sensitive(False)
            self.footer.set_text((tr('Unable to read this passage.')+' '+self.stream.error)
                                 if getattr(self.stream,'error',None) else tr('Preparing reading pages…'))
            return
        self.clicked_reference=None
        self.layout_ready=False;self._stable_frames=0;self._selection_restore_pending=bool(self.selection);self._allocation_signature=None
        self._updating=True;self.addresses=self.stream.spread(self.count)
        p=self.owner.preferences.value
        for index,view in enumerate(self.views):
            self.frames[index].set_visible(index<self.count);view.set_visible(index<self.count)
            if index>=len(self.addresses):
                view._study_page=None;view.get_buffer().set_text('');continue
            address=self.addresses[index];plan=self.stream.plan(address.key);page=plan.pages[address.index]
            buffer=view.get_buffer();buffer.set_text(plan.document.text[page.start:page.end])
            view._study_page=(plan.document,page.start,page.end)
            from .bible_render import bind_copy
            bind_copy(view,plan.document,page.start)
            table=buffer.get_tag_table();body=table.lookup('page-body')
            if body is None:body=buffer.create_tag('page-body')
            body.props.family=p.font;body.props.size_points=p.size
            buffer.apply_tag(body,buffer.get_start_iter(),buffer.get_end_iter())
            view.set_pixels_inside_wrap(SPACING[p.line_spacing]);view.set_pixels_below_lines(SPACING[p.line_spacing])
            for kind in ('chapter','heading','number','verse-start'):
                tag=table.lookup('page-'+kind)
                if tag is None:tag=buffer.create_tag('page-'+kind)
                if kind=='number':
                    from .verse_typography import configure
                    configure(tag,view,p,self.owner.reading_style.palette)
                elif kind=='verse-start':tag.props.allow_breaks=False
                else:tag.props.weight=700;tag.props.scale=1.35 if kind=='chapter' else 1.12
                for style in plan.document.styles:
                    first,last=max(page.start,style.start),min(page.end,style.end)
                    if style.kind==kind and last>first:
                        buffer.apply_tag(tag,buffer.get_iter_at_offset(first-page.start),buffer.get_iter_at_offset(last-page.start))
            from .commentary_format import apply
            inline=[(s.kind,max(s.start,page.start)-page.start,min(s.end,page.end)-page.start)
                    for s in plan.document.styles if s.kind in {'hidden','italic','bold','small-caps'}
                    and s.end>page.start and s.start<page.end]
            apply(view,inline,p,self.owner.reading_style.palette)
        if self.kind=='bible' and hasattr(self.owner,'highlights'):
            from .highlight_ui import paint
            for view,address in zip(self.views,self.addresses):
                plan=self.stream.plan(address.key);page=plan.pages[address.index]
                ranges=[(span.reference,max(page.start,span.body)-page.start,min(page.end,span.end)-page.start)
                        for span in plan.document.spans if span.end>page.start and span.body<page.end]
                paint(view,self.owner.highlights,self.source.reader.versification,ranges,False,
                      self.owner.reading_style.manager.get_high_contrast(),self.owner.reading_style.palette)
        self.update_study_indicator()
        self.restore_selection()
        self._updating=False
        anchor=self.stream.anchor();caption=self.source.resource.name
        if self.kind=='bible':
            caption+=' — '+passage_label(anchor.reference,versification=self.source.reader.versification)
            self.owner.active_tab.state.reference=anchor.reference
        else:
            caption+=' — '+self.source.reader.index.label(self.stream.cursor.key)
            section=self.source.reader.index.sections[self.stream.cursor.key]
            self.open_bible.set_sensitive(not section.introduction)
            for direction,button in [(-1,self.entry_previous),(1,self.entry_next)]:
                position=self.source.entry_neighbour(self.stream.cursor.key,direction)
                button.set_sensitive(position is not None)
                button.set_tooltip_text((tr('Previous available entry') if direction<0 else tr('Next available entry'))+
                                       (': '+self.source.reader.index.label(position) if position is not None else ''))
        self.footer.set_text(caption);self.caption.set_text(caption)
        self.update_page_buttons()

    def update_page_buttons(self):
        self.back.set_sensitive(self.stream.step(self.stream.cursor,-1) is not None)
        self.forward.set_sensitive(self.stream.step(self.addresses[-1],1) is not None)

    def restore_selection(self):
        if not self.selection:return
        for view,address in zip(self.views,self.addresses):
            if self.selection[0]!=address.key:continue
            plan=self.stream.plan(address.key);page=plan.pages[address.index]
            first,last=(plan.document.locate(a) for a in self.selection[1:])
            first,last=max(first,page.start),min(last,page.end)
            if last>first:
                buffer=view.get_buffer()
                buffer.select_range(buffer.get_iter_at_offset(first-page.start),buffer.get_iter_at_offset(last-page.start))

    def cancel_slide(self):
        self._slide_serial+=1
        self.page_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.page_stack.set_visible_child_name('live');self.previous_page.set_paintable(None)

    def turn(self,direction):
        self.cancel_slide()
        animated=Gtk.Settings.get_default().get_property('gtk-enable-animations')
        previous=Gtk.WidgetPaintable.new(self.page_clamp).get_current_image() if animated and self.layout_ready else None
        self.owner.passage_actions.dismiss()
        if self.stream.cursor and self.stream.turn(direction,self.count):
            self.selection=None;self.render()
            if previous:
                self.previous_page.set_paintable(previous);self.page_stack.set_visible_child_name('previous')
                serial=self._slide_serial
                def reveal():
                    if self._closed or serial!=self._slide_serial:return False
                    forward=(direction>0)!=self.source.rtl
                    self.page_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT if forward else Gtk.StackTransitionType.SLIDE_RIGHT)
                    self.page_stack.set_visible_child_name('live');return False
                GLib.idle_add(reveal)
            return True
        return False

    def go_to_reference(self,reference):
        if self.kind!='bible':return
        self.cancel_slide()
        self.clicked_reference=None
        key=self.source.key(reference);self.initial_anchor=Anchor(reference);self.initial_key=key
        self.stream.configure(self.stream.width,self.stream.height,self.initial_anchor,key);self.render()

    def change_entry(self,direction):
        self.cancel_slide()
        key=self.source.entry_neighbour(self.stream.cursor.key,direction)
        if key is None:return
        doc=self.source.document(key,self.owner.preferences.value)
        anchor=doc.anchor(0);self.stream.configure(self.stream.width,self.stream.height,anchor,key)
        self.selection=None;self.render();self.reveal_controls()

    def clicked(self,view,x,y):
        if view.get_buffer().get_has_selection() or view not in self.views:return
        index=self.views.index(view)
        if index>=len(self.addresses):return
        bx,by=view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET,int(x),int(y))
        found,iterator=view.get_iter_at_location(bx,by)
        if found:
            address=self.addresses[index];plan=self.stream.plan(address.key);page=plan.pages[address.index]
            anchor=plan.document.anchor(page.start+iterator.get_offset())
            if self.kind=='bible':self.clicked_reference=anchor.reference
            self.footer.set_text(self.source.resource.name+' — '+(passage_label(anchor.reference,versification=self.source.reader.versification) if self.kind=='bible' else self.source.reader.index.label(address.key)))

    def selected_passage(self):
        for view,address in zip(self.views,self.addresses):
            bounds=view.get_buffer().get_selection_bounds()
            if bounds:
                plan=self.stream.plan(address.key);page=plan.pages[address.index]
                result=plan.document.selected_passage(*(page.start+i.get_offset() for i in bounds))
                if result:return result
        anchor=self.stream.anchor() if self.stream.cursor else self.initial_anchor
        reference=self.clicked_reference or anchor.reference
        return reference,reference

    def copy_selection(self,view):
        if not self.selection or not getattr(self,'_restored_selection',False):return
        key,start,end=self.selection;doc=self.stream.plan(key).document
        value=doc.copy(doc.locate(start),doc.locate(end))
        view.get_clipboard().set(value)
        from gi.repository import GObject
        GObject.signal_stop_emission_by_name(view,'copy-clipboard')

    def any_selection(self):return any(view.get_buffer().get_has_selection() for view in self.views)

    def key_pressed(self,controller,key,code,state):
        self.owner.set_focus_visible(True)
        if state&Gdk.ModifierType.SHIFT_MASK and key in (Gdk.KEY_Left,Gdk.KEY_Right,Gdk.KEY_Up,Gdk.KEY_Down,Gdk.KEY_Home,Gdk.KEY_End,Gdk.KEY_Page_Up,Gdk.KEY_Page_Down):
            return False
        if key==Gdk.KEY_Escape:
            for popover in self.open_popovers():
                if popover and popover.get_visible():popover.popdown();return True
            self.owner.leave_immersion();return True
        if key==Gdk.KEY_F10:
            self.reveal_controls();self.leave_button.grab_focus();return True
        if self.controls_focused() or self.any_selection() or state&Gdk.ModifierType.CONTROL_MASK:return False
        if key in (Gdk.KEY_Page_Down,Gdk.KEY_Page_Up,Gdk.KEY_space,Gdk.KEY_Left,Gdk.KEY_Right):
            direction=-1 if key==Gdk.KEY_Page_Up or (key==Gdk.KEY_space and state&Gdk.ModifierType.SHIFT_MASK) else 1
            if key in (Gdk.KEY_Left,Gdk.KEY_Right):direction=(1 if key==Gdk.KEY_Right else -1)*(-1 if self.source.rtl else 1)
            self.turn(direction);return True
        return False

    def begin_scroll(self):self._wheel=0;self._gesture_turned=False
    def end_scroll(self):self._wheel=0;self._gesture_turned=False

    def wheel_scroll(self,controller,dx,dy):
        if self.controls_focused() or self.any_selection() or self.open_popovers() or self._pointer_top:return False
        delta=dy if abs(dy)>=abs(dx) else dx*(-1 if self.source.rtl else 1)
        now=time.monotonic();smooth=controller.get_unit()==Gdk.ScrollUnit.SURFACE
        self._wheel+=delta
        if smooth and (self._gesture_turned or abs(self._wheel)<60):return True
        if now-self._last_turn<.25:return True
        self._last_turn=now;self._gesture_turned=True
        self.turn(1 if self._wheel>0 else -1);self._wheel=0;return True

    def pointer_moved(self,controller,x,y):
        # Hidden chrome reveals at the edge; visible chrome retains its actual
        # hover area. Neither sensor depends on the revealer's animated size.
        controls=self.top.get_child()
        self._pointer_top=y<24 or (controls.get_mapped() and y<max(90,controls.get_height()))
        self._pointer_edge=x<75 or x>self.get_width()-75
        for reveal in self.nav_revealers:
            found,bounds=reveal.compute_bounds(self)
            if found and bounds.origin.x-16<=x<=bounds.origin.x+bounds.size.width+16 and bounds.origin.y-16<=y<=bounds.origin.y+bounds.size.height+16:
                self._pointer_edge=True
        if self._pointer_top or self._pointer_edge:self.reveal_controls()
        elif not self._hide_id:self.schedule_hide()

    def pointer_left(self):
        self._pointer_top=False;self._pointer_edge=False;self.schedule_hide()

    def open_popovers(self):
        result=[]
        def visit(widget):
            if isinstance(widget,Gtk.Popover) and widget.get_visible():result.append(widget)
            child=widget.get_first_child()
            while child:
                visit(child);child=child.get_next_sibling()
        visit(self)
        return result

    def controls_focused(self):
        focus=self.owner.get_focus()
        if not focus or not self.owner.get_focus_visible():return False
        if self.owner.passage_actions.contains(focus):return True
        return (focus.is_ancestor(self.top) or any(focus is button or focus.is_ancestor(button) for button in self.buttons))

    def reveal_controls(self):
        self.top.set_can_target(True);self.top.set_reveal_child(True)
        for button,reveal in zip(self.buttons,self.nav_revealers):
            button.set_can_target(True);reveal.set_can_target(True);reveal.set_reveal_child(True)
        self.schedule_hide()

    def schedule_hide(self):
        if self._hide_id:GLib.source_remove(self._hide_id)
        self._hide_id=GLib.timeout_add(1600,self.hide_controls)

    def hide_controls(self):
        self._hide_id=0
        if self.controls_focused() or self.open_popovers() or self._pointer_top:self.schedule_hide();return False
        focus=self.owner.get_focus()
        if focus and not self.owner.get_focus_visible() and (focus.is_ancestor(self.top) or any(focus is button or focus.is_ancestor(button) for button in self.buttons)):
            next((view for view in self.views if view.get_mapped() and view.get_buffer().get_has_selection()),self.views[0]).grab_focus()
        self.top.set_can_target(False);self.top.set_reveal_child(False)
        if not self._pointer_edge:
            for button,reveal in zip(self.buttons,self.nav_revealers):
                button.set_can_target(False);reveal.set_can_target(False);reveal.set_reveal_child(False)
        return False

    def hide_help(self):
        self.owner.immersion_hints.disable();self.notification_help.set_revealed(False)

    def open_in_bible(self):
        section=self.source.reader.index.sections[self.stream.cursor.key]
        if section.introduction:return
        reference=section.start;reader=self.owner.active_tab.reader
        if reader and reader.versification==self.source.reader.versification and reader.has_reference(reference):
            self.owner.leave_immersion();self.owner.navigate_selection(self.owner.active_tab.state.resource,reference)

    def finish(self):
        self.cancel_slide()
        self._closed=True
        if self._hide_id:GLib.source_remove(self._hide_id);self._hide_id=0
        if self._tick:self.remove_tick_callback(self._tick);self._tick=0
        self.owner.appearance.popdown();self.aa.set_popover(None);self.owner.appearance_button.set_popover(self.owner.appearance)
        if self.kind=='bible':
            self.owner.primary_version.popdown()
            self.header.remove(self.owner.primary_version)
            self.owner.reader_controls.prepend(self.owner.primary_version)
            self.owner.navigation.popdown();self.passage_button.set_popover(None);self.owner.passage_button.set_popover(self.owner.navigation)
        anchor=self.stream.anchor() if self.stream.cursor else self.initial_anchor
        if hasattr(self.stream,'close'):self.stream.close()
        return anchor,self.stream.cursor.key if self.stream.cursor else self.initial_key
