"""Pane-local installed Bible choices over the existing tab/session state."""
from gi.repository import Gtk, Pango, GObject
from .i18n import tr
from .providers import module_name


def bounded_choices(dropdown):
    """Keep long installed resource names usable inside constrained native popups."""
    def factory(popup):
        value=Gtk.SignalListItemFactory()
        def setup(_,item):
            label=Gtk.Label(xalign=0,max_width_chars=28,width_chars=1)
            if popup:label.set_wrap(True);label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            else:label.set_ellipsize(Pango.EllipsizeMode.END)
            item.set_child(label)
        def bind(_,item):item.get_child().set_text(item.get_item().get_string())
        value.connect('setup',setup);value.connect('bind',bind);return value
    dropdown.set_factory(factory(False));dropdown.set_list_factory(factory(True))
    dropdown.set_enable_search(False)


class DirectChoices(Gtk.ScrolledWindow):
    """One native list, with the same selection contract in every pane."""
    __gsignals__={'reselected':(GObject.SignalFlags.RUN_LAST,None,())}
    selected=GObject.Property(type=GObject.TYPE_UINT,default=Gtk.INVALID_LIST_POSITION)
    def __init__(self):
        super().__init__(hscrollbar_policy=Gtk.PolicyType.NEVER,max_content_height=360,propagate_natural_height=True)
        self.list=Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.add_css_class('boxed-list');self.set_child(self.list);self.rows=[]
        self.list.connect('row-activated',self.activate)
    def activate(self,_,row):
        if row.get_index()==self.get_selected():self.emit('reselected')
        else:self.set_selected(row.get_index())

    def set_model(self,model):
        while self.list.get_first_child():self.list.remove(self.list.get_first_child())
        self.rows=[]
        for i in range(model.get_n_items()):
            box=Gtk.Box(spacing=12,margin_top=10,margin_bottom=10,margin_start=12,margin_end=12)
            text=Gtk.Label(label=model.get_string(i),xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,max_width_chars=36,hexpand=True)
            check=Gtk.Image(icon_name='object-select-symbolic',opacity=0);box.append(text);box.append(check);self.list.append(box);self.rows.append(check)
    def get_selected(self):return self.selected
    def set_selected(self,index):
        for i,check in enumerate(self.rows):check.set_opacity(1 if i==index else 0)
        self.list.select_row(self.list.get_row_at_index(index) if index<len(self.rows) else None)
        if self.selected!=index:self.selected=index


class VersionChooser(Gtk.MenuButton):
    def __init__(self, owner, comparison=False):
        super().__init__(tooltip_text=tr('Version'))
        self.owner=owner;self.comparison=comparison;self._syncing=False;self.names=[]
        self.add_css_class('version-pill')
        self.caption=Gtk.Label(ellipsize=Pango.EllipsizeMode.END,max_width_chars=16,width_chars=1)
        row=Gtk.Box(spacing=4);row.append(self.caption);row.append(Gtk.Image(icon_name='pan-down-symbolic',pixel_size=12))
        self.set_child(row)
        self.popover=Gtk.Popover(autohide=False)
        self.choices=DirectChoices()
        self.choices.connect('notify::selected',self.selected)
        self.choices.connect('reselected',lambda *_:self.popover.popdown())
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_top=8,margin_bottom=8,margin_start=8,margin_end=8)
        box.append(self.choices)
        self.download_more=Gtk.Button(label=tr('Download more…'))
        self.download_more.connect('clicked',lambda *_:owner.contextual_library('bible','comparison' if comparison else 'bible'))
        box.append(self.download_more)
        self.status=Gtk.Label(wrap=True,max_width_chars=28,xalign=0,visible=False);box.append(self.status)
        self.popover.set_child(box);self.set_popover(self.popover)
        from .popover_dismissal import fit_reader_popover
        self.popover.connect('show',lambda *_:fit_reader_popover(self.popover,owner))
        owner._reading_popovers.append(self.popover)
        self.connect('notify::active',lambda *_:self.sync())

    def sync(self):
        if self.owner.closed:return False
        tab=self.owner.active_tab
        if not tab:return
        current=tab.state.comparison if self.comparison else tab.state.resource
        installed=self.owner.library.installed('bible')
        names=list(installed)
        if current and current not in names:names.insert(0,current)
        labels=[];captions=[]
        for name in names:
            if name in installed:
                try:
                    resource=self.owner.library.resource(name)
                    labels.append(resource.description+' — '+resource.source)
                    captions.append(resource.description.split(' with ')[0])
                except (ValueError,OSError):
                    labels.append(module_name(name)+' ('+tr('Missing translation')+')');captions.append(module_name(name))
            else:
                labels.append(module_name(name)+' ('+tr('Missing translation')+')');captions.append(module_name(name))
        self._syncing=True
        if names!=self.names or labels!=getattr(self,'_labels',None):
            self.names=names;self._labels=labels;self.choices.set_model(Gtk.StringList.new(labels))
        self.choices.set_selected(names.index(current) if current in names else Gtk.INVALID_LIST_POSITION)
        self._syncing=False
        caption=captions[names.index(current)] if current in names else tr('Choose a translation')
        self.caption.set_text(caption)
        full=labels[names.index(current)] if current in names else tr('Choose a translation')
        self.set_tooltip_text(tr('Version')+': '+full)
        self.update_property([Gtk.AccessibleProperty.LABEL],[tr('Version')+': '+full])
        self.choices.update_property([Gtk.AccessibleProperty.LABEL],[tr('Version')])

    def selected(self, widget, *_):
        if self._syncing or widget.get_selected()>=len(self.names):return
        tab=self.owner.active_tab
        if not tab:return
        name=self.names[widget.get_selected()]
        current=tab.state.comparison if self.comparison else tab.state.resource
        if name==current:self.popover.popdown();return
        self.owner.passage_actions.dismiss()
        try:
            if self.comparison:
                # The existing comparison resolver owns alignment and error states.
                tab.state.comparison=name;self.owner.sync_comparison();self.owner.schedule_save()
            else:
                from .sword_provider import Reader
                from .reference_resolution import resolve
                reader=Reader(self.owner.library.root/name,name)
                reference=resolve(tab.state.reference,tab.reader.versification,reader).start if tab.reader else reader.first_reference()
                if not self.owner.navigate_selection(name,reference):
                    raise ValueError(tab.status.get_text())
            self.status.set_visible(False)
            # Finish GtkDropDown's activation before rebuilding any models.
            from gi.repository import GLib
            GLib.idle_add(self.finish)
        except Exception as error:
            self.status.set_text(str(error));self.status.set_visible(True)
            from gi.repository import GLib
            GLib.idle_add(self.sync)

    def finish(self):
        if self.owner.closed:return False
        self.sync();self.popover.popdown();return False
