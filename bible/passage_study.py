"""One native contextual host for the existing word and place components."""
from dataclasses import replace
from gi.repository import Adw,Gdk,Gtk,Pango
from .i18n import tr
from .reference_preview import passage_title


class PassageStudy(Adw.Window):
    def __init__(self,owner,*,target=None,context=None,mode='original',place=None,metadata=None):
        super().__init__(title=tr('Study passage'),transient_for=owner,modal=True,destroy_with_parent=True,
                         default_width=min(700,max(320,owner.get_width()-48)),
                         default_height=min(680,max(360,owner.get_height()-96)))
        self.owner=owner;self.closed=False;self.words=None
        self.add_css_class(owner.reading_style.scope+'-window')
        if target is None:target=self.context_target(context)
        self.target=target
        if context is None and target:
            context=(target.source.resource,target.source.reader,target.references[0],target.references[-1])
        self.context=context
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header=Adw.HeaderBar(show_end_title_buttons=False)
        header.set_title_widget(Gtk.Label(label=tr('Study passage')))
        self.close_button=Gtk.Button(icon_name='window-close-symbolic',tooltip_text=tr('Close'))
        self.close_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Close')])
        self.close_button.add_css_class('flat');self.close_button.connect('clicked',lambda *_:self.close())
        header.pack_end(self.close_button);root.append(header)
        caption=passage_title(context[2],context[3],context[1].versification) if context else tr('Choose a passage')
        self.passage=Gtk.Label(label=caption,wrap=True,margin_start=16,margin_end=16,margin_bottom=8)
        self.passage.add_css_class('heading');root.append(self.passage)
        self.tabs=Gtk.Stack(vexpand=True,hhomogeneous=False,vhomogeneous=False)
        switcher=Gtk.StackSwitcher(stack=self.tabs,halign=Gtk.Align.FILL,margin_start=12,margin_end=12,margin_bottom=8)
        self.switcher=switcher;root.append(switcher);root.append(self.tabs)
        if target:
            self.words=owner.study.words;self.words.attach(target,metadata,host=self,start=mode=='original')
            self.tabs.add_titled(self.words,'original',tr('Original text'))
        else:
            self.tabs.add_titled(self.empty(tr('Choose a Bible passage to study.')),'original',tr('Original text'))
        self.tabs.add_titled(self.empty(tr('No linked dictionary data is available.')),'dictionary',tr('Dictionary'))
        from .place_cards import PlaceView
        self.places=PlaceView(owner,context=context,host=self)
        self.tabs.add_titled(self.places,'map',tr('Map'))
        self.tabs.add_titled(self.empty(tr('No source-backed people data is available.')),'people',tr('People'))
        self.tabs.set_visible_child_name(mode)
        self._words_started=mode=='original'
        def selected(*_):
            if self.words and self.tabs.get_visible_child_name()=='original' and not self._words_started:
                self._words_started=True;self.words.begin()
        self.tabs.connect('notify::visible-child-name',selected)
        def wrap_labels(widget):
            if isinstance(widget,Gtk.Label):
                widget.set_wrap(True);widget.set_wrap_mode(Pango.WrapMode.WORD_CHAR);widget.set_width_chars(1)
            child=widget.get_first_child()
            while child:wrap_labels(child);child=child.get_next_sibling()
        wrap_labels(switcher)
        self.set_content(root);self.set_size_request(320,320)
        self.connect('close-request',self.on_close)
        keys=Gtk.EventControllerKey()
        keys.connect('key-pressed',lambda _,key,*args:(self.close() or True) if key==Gdk.KEY_Escape else False)
        self.add_controller(keys)
        if place:self.places.open_place(place)

    @staticmethod
    def empty(message):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,margin_start=20,margin_end=20,margin_top=20,margin_bottom=20)
        label=Gtk.Label(label=message,wrap=True,xalign=0);label.add_css_class('dim-label');box.append(label)
        return box

    def context_target(self,context):
        tab=self.owner.active_tab
        if not tab or not tab.reader:return None
        comparison=bool(context and context[0]==tab.state.comparison and context[0]!=tab.state.resource)
        factory=lambda:self.owner.passage_actions.ordinary(tab,comparison=comparison)
        source=factory()
        if not source or context and source.resource!=context[0]:return None
        from .passage_actions import target
        view=tab.comparison_text if comparison else tab.text
        reference=context[2] if context else tab.state.reference
        span=next((s for s in source.document.spans if reference in s.members),None)
        if context and span is None:return None
        value=target(view,source,factory,span.body-source.base if span else 0)
        if value and context:
            from .reference_targets import local_excerpt
            try:excerpt=local_excerpt(source.reader,context[2],context[3],source_system=context[1].versification,limit=40)
            except (ValueError,OSError):return None
            value=replace(value,references=tuple(ref for ref,_ in excerpt.verses),text=excerpt.text,
                          verses=tuple(text for _,text in excerpt.verses),native_selection=False,selection=None)
        return value

    def refresh(self):
        if self.words:self.words.refresh()
        if not self.closed:self.places.refresh()

    def on_close(self,*_):
        if self.closed:return False
        self.closed=True;self.close_button.grab_focus()
        if self.words:
            self.words.dialog_closed()
            self.tabs.remove(self.words)
        self.places.on_closed()
        for name in ('passage_study_dialog','place_dialog'):
            if getattr(self.owner,name,None) is self:setattr(self.owner,name,None)
        return False
