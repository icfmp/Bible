"""Intent-driven passage actions with frozen source/range/copy targets."""
from dataclasses import dataclass
from gi.repository import Gdk, GLib, Gtk, Pango
from .i18n import tr
from .notes_window import passage_label
from .providers import module_name


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
    return tuple(s.reference for s in source.document.spans
                 if s.end>first and s.body-(len(s.reference.rsplit('.',1)[-1])+1 if numbers else 0)<last)


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


class PassageActions:
    def __init__(self,owner):
        self.owner=owner;self.target=None;self.dragging=False;self.keyboard=False;self.timer=0
        self.clearance=None;self.intent=0
        self.bar=Gtk.Box(spacing=4,halign=Gtk.Align.CENTER,valign=Gtk.Align.END,
                         margin_start=12,margin_end=12,margin_bottom=12,visible=False)
        self.bar.add_css_class('toolbar');self.bar.add_css_class('osd')
        self.bar.add_css_class('passage-actions')
        self.bar.update_property([Gtk.AccessibleProperty.LABEL],[tr('Passage actions')])
        self.label=Gtk.Label(ellipsize=Pango.EllipsizeMode.END,width_chars=1,max_width_chars=18)
        self.bar.append(self.label)
        self.copy_button=self.button('edit-copy-symbolic','Copy selected text',lambda *_:self.copy())
        self.copy_options=Gtk.MenuButton(icon_name='pan-down-symbolic',tooltip_text=tr('Copy options'))
        self.bar.append(self.copy_options)
        self.copy_popover=self.menu(self.copy_options,[(label,lambda *_,mode=mode:self.copy(mode))
            for label,mode in [('Copy selected text','selected'),('Copy verses without numbers','verses'),
                               ('Copy verses with reference','reference'),('Copy reference','label')]])
        self.note_button=self.button('bible-notes-symbolic','Add a passage note',lambda *_:self.note())
        self.highlight_button=None
        if hasattr(owner,'highlights'):
            from .highlights import COLORS
            self.highlight_button=Gtk.MenuButton(icon_name='color-select-symbolic',tooltip_text=tr('Highlight'))
            self.highlight_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Highlight')])
            self.bar.append(self.highlight_button)
            self.highlight_popover=self.menu(self.highlight_button,[(label,lambda *_,c=color:self.highlight(c))
                for color,(_,label) in COLORS.items()]+[('Remove highlight',lambda *_:self.highlight(None))])
        self.compare_button=self.button('view-dual-symbolic','Compare translations',lambda *_:self.compare())
        self.close_button=self.button('window-close-symbolic','Dismiss passage actions',lambda *_:self.dismiss())
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

    def button(self,icon,label,callback):
        button=Gtk.Button(icon_name=icon,tooltip_text=tr(label))
        button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
        button.connect('clicked',callback);self.bar.append(button);return button

    def menu(self,button,choices):
        popover=Gtk.Popover(autohide=False);box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,
            margin_start=8,margin_end=8,margin_top=8,margin_bottom=8)
        for label,callback in choices:
            item=Gtk.Button(label=tr(label));item.add_css_class('flat')
            item.connect('clicked',callback);item.connect('clicked',lambda *_:popover.popdown());box.append(item)
        popover.set_child(box);button.set_popover(popover)
        popover.parent_dismissed=lambda widget:self.dismiss() if not self.contains(widget) else None
        self.owner._reading_popovers.append(popover);return popover

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
        click=Gtk.GestureClick(button=1);click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        pending=[None]
        def pressed(controller,count,x,y):
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
        if not value:self.dismiss();return False
        self.target=value
        parent=self.bar.get_parent()
        if parent is not source.parent:
            if parent:parent.remove_overlay(self.bar)
            source.parent.add_overlay(self.bar)
        label=passage_label(value.references[0],value.references[-1],source.reader.versification)+' · '+module_name(source.resource)
        self.label.set_text(label);self.label.set_tooltip_text(label)
        self.copy_button.set_tooltip_text(tr('Copy selected text') if value.native_selection else tr('Copy verses without numbers'))
        self.note_button.set_sensitive(self.owner.notes_store is not None)
        self.bar.set_visible(True)
        self.bar.set_margin_bottom(0 if source.side=='immersion' else 12)
        self.compare_button.set_sensitive(source.tab.reader is not None)
        frames=[0]
        def keep_clear(*_):
            frames[0]+=1
            if self.target is not value or not view.get_mapped():return False
            if frames[0]<2:return True
            if source.side=='immersion':return False
            location=view.get_iter_location(view.get_buffer().get_iter_at_offset(value.anchor))
            visible=view.get_visible_rect()
            safe=visible.y+visible.height-self.bar.get_height()-20
            if visible.y<=location.y<visible.y+visible.height and location.y+location.height>safe:
                original=view.get_bottom_margin();margin=max(original,self.bar.get_height()+32)
                if margin!=original:self.clearance=(view,original,margin);view.set_bottom_margin(margin)
                adjustment=view.get_vadjustment()
                adjustment.set_value(adjustment.get_value()+min(self.bar.get_height()+20,location.y+location.height-safe))
            return False
        self.bar.add_tick_callback(keep_clear)
        if not self.timer:self.timer=GLib.timeout_add(100,self.watch)
        return False

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

    def watch(self):
        if not self.target:self.timer=0;return False
        if not self.valid():self.dismiss();self.timer=0;return False
        value=self.target
        reflow=value.source.tab._restoring_scroll or (self.owner.immersion and not self.owner.immersion.layout_ready)
        if not reflow and (not self.bar.get_mapped() or
                (value.native_selection and not value.view.get_buffer().get_has_selection())):
            self.dismiss();self.timer=0;return False
        return True

    def key(self,controller,value,*_):
        if value==Gdk.KEY_Escape and self.target:
            if any(p.get_visible() for p in self.owner._reading_popovers):return False
            self.dismiss();return True
        return False

    def dismiss(self):
        self.intent+=1
        self.keyboard=False
        value=self.target;restore=bool(value and self.contains(self.owner.get_focus()))
        self.target=None;self.bar.set_visible(False)
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
