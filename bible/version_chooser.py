"""Pane-local installed Bible choices over the existing tab/session state."""
from gi.repository import Gtk, Pango, GObject
from .i18n import tr
from .providers import module_name


def fit_wrapped_button(button,text):
    """MenuButton is constant-size: request its native wrapped content height."""
    if not button.get_mapped():return
    content=button.get_child()
    if not content or content.get_width()<=0:return
    stamp=(button.get_width(),content.get_width(),text,content.get_pango_context().get_serial())
    if stamp==getattr(button,'_wrapped_height_stamp',None):return
    button._wrapped_height_stamp=stamp
    button.props.height_request=-1
    base=button.measure(Gtk.Orientation.VERTICAL,-1)[1]
    natural=content.measure(Gtk.Orientation.VERTICAL,-1)[1]
    wrapped=content.measure(Gtk.Orientation.VERTICAL,content.get_width())[1]
    button.props.height_request=base+max(0,wrapped-natural)


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


def fit_translation_choices(popover,choices,owner):
    if not popover.get_visible():return
    width=max(120,min(520,owner.get_width()-48))
    choices.set_propagate_natural_width(True)
    if choices.get_min_content_width()!=width or choices.get_max_content_width()!=width:
        choices.set_min_content_width(-1)
        choices.set_max_content_width(width)
        choices.set_min_content_width(width)
    # Ask GTK for the wrapped rows' height rather than the unconstrained one.
    # Long lists still scroll, and short windows retain room for the action.
    height=min(360,max(80,owner.get_height()-160),choices.list.measure(Gtk.Orientation.VERTICAL,width)[1])
    choices.set_min_content_height(height)
    from .popover_dismissal import fit_reader_popover
    fit_reader_popover(popover,owner)


def choice_details(resource):
    return resource.description,resource.source,resource.public_code


def download_translations_action():
    button=Gtk.Button(tooltip_text=tr('Download other translations…'))
    button.add_css_class('flat')
    row=Gtk.Box(spacing=6,halign=Gtk.Align.CENTER)
    row.append(Gtk.Image(icon_name='folder-download-symbolic',pixel_size=14))
    label=Gtk.Label(label=tr('Download other translations…'),wrap=True,
        wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,hexpand=True)
    label.add_css_class('caption');row.append(label);button.set_child(row)
    button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Download other translations…')])
    return button


class DirectChoices(Gtk.ScrolledWindow):
    """One native list, with the same selection contract in every pane."""
    __gsignals__={'reselected':(GObject.SignalFlags.RUN_LAST,None,())}
    selected=GObject.Property(type=GObject.TYPE_UINT,default=Gtk.INVALID_LIST_POSITION)
    def __init__(self):
        super().__init__(hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,max_content_height=360,propagate_natural_height=True)
        self.list=Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.add_css_class('boxed-list');self.set_child(self.list);self.rows=[]
        self.list.connect('row-activated',self.activate)
        self.connect('map',self.focus_selection)
    def focus_selection(self,*_):
        row=self.list.get_selected_row()
        if row:row.grab_focus()
    def activate(self,_,row):
        if row.get_index()==self.get_selected():self.emit('reselected')
        else:self.set_selected(row.get_index())

    def set_model(self,model,details=None):
        while self.list.get_first_child():self.list.remove(self.list.get_first_child())
        self.rows=[]
        for i in range(model.get_n_items()):
            box=Gtk.Box(spacing=12,margin_top=10,margin_bottom=10,margin_start=12,margin_end=12)
            title,source,code=details[i] if details else (model.get_string(i),'','')
            labels=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3,hexpand=True)
            text=Gtk.Label(label=title,xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,max_width_chars=48,hexpand=True)
            text.add_css_class('heading');labels.append(text);box.append(labels)
            if source:
                provider=Gtk.Label(label=source,xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
                provider.add_css_class('caption');provider.add_css_class('dim-label');labels.append(provider)
            if code:
                badge=Gtk.Label(label=code,valign=Gtk.Align.CENTER,width_chars=1,max_width_chars=12,
                    ellipsize=Pango.EllipsizeMode.NONE if len(code)<=4 else Pango.EllipsizeMode.END,tooltip_text=code)
                badge.add_css_class('caption');badge.add_css_class('translation-code');box.append(badge)
            check=Gtk.Image(icon_name='object-select-symbolic',opacity=0);box.append(check)
            row=Gtk.ListBoxRow(child=box)
            row.update_property([Gtk.AccessibleProperty.LABEL],[', '.join(x for x in (title,code,source) if x)])
            self.list.append(row);self.rows.append(check)
    def get_selected(self):return self.selected
    def set_selected(self,index):
        for i,check in enumerate(self.rows):check.set_opacity(1 if i==index else 0)
        self.list.select_row(self.list.get_row_at_index(index) if index<len(self.rows) else None)
        if self.selected!=index:self.selected=index


class VersionChooser(Gtk.MenuButton):
    def __init__(self, owner, comparison=False):
        super().__init__(tooltip_text=tr('Version'))
        self.set_can_shrink(True)
        self.owner=owner;self.comparison=comparison;self._syncing=False;self.names=[]
        self.add_css_class('flat')
        self.caption=Gtk.Label(wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,max_width_chars=24,width_chars=1)
        self.caption.set_hexpand(True)
        row=Gtk.Overlay();self.caption.set_margin_end(16);row.set_child(self.caption)
        self.chevron=Gtk.Image(icon_name='pan-down-symbolic',pixel_size=12,halign=Gtk.Align.END)
        row.add_overlay(self.chevron);self.set_child(row)
        self.popover=Gtk.Popover(autohide=False)
        self.choices=DirectChoices()
        self.choices.connect('notify::selected',self.selected)
        self.choices.connect('reselected',lambda *_:self.popover.popdown())
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_top=8,margin_bottom=8,margin_start=8,margin_end=8)
        box.append(self.choices)
        self.download_more=download_translations_action()
        self.download_more.connect('clicked',lambda *_:owner.contextual_library('bible','comparison' if comparison else 'bible'))
        box.append(Gtk.Separator());box.append(self.download_more)
        self.status=Gtk.Label(wrap=True,max_width_chars=28,xalign=0,visible=False);box.append(self.status)
        self.popover.set_child(box);self.set_popover(self.popover)
        self.popover.connect_after('show',lambda *_:self.fit_popup())
        owner._reading_popovers.append(self.popover)
        self.connect('notify::active',lambda *_:self.sync())

    def fit_popup(self):
        fit_translation_choices(self.popover,self.choices,self.owner)

    def sync(self):
        if self.owner.closed:return False
        tab=self.owner.active_tab
        if not tab:return
        current=tab.state.comparison if self.comparison else tab.state.resource
        installed=self.owner.library.installed('bible')
        names=list(installed)
        if current and current not in names:names.insert(0,current)
        labels=[];captions=[];details=[]
        for name in names:
            if name in installed:
                try:
                    resource=self.owner.library.resource(name)
                    labels.append(resource.description+' — '+resource.source)
                    captions.append(resource.description)
                    details.append(choice_details(resource))
                except (ValueError,OSError):
                    labels.append(module_name(name)+' ('+tr('Missing translation')+')');captions.append(tr('Missing translation'))
                    details.append((labels[-1],'',''))
            else:
                labels.append(module_name(name)+' ('+tr('Missing translation')+')');captions.append(tr('Missing translation'))
                details.append((labels[-1],'',''))
        self._syncing=True
        if names!=self.names or details!=getattr(self,'_details',None):
            self.names=names;self._labels=labels;self._details=details;self.choices.set_model(Gtk.StringList.new(labels),details)
        self.choices.set_selected(names.index(current) if current in names else Gtk.INVALID_LIST_POSITION)
        self._syncing=False
        caption=captions[names.index(current)] if current in names else tr('Choose a translation')
        # The header uses the provider's public abbreviation. Pane selectors
        # keep their full name; the picker and accessible label always do too.
        reader=tab.reader
        in_header=not self.comparison and not tab.state.comparison
        if in_header and reader and current==tab.state.resource:
            short=reader.module.getConfigEntry('Abbreviation')
            # Older converted modules wrote their internal ID when the source
            # supplied no abbreviation. That fallback is not a public code.
            if current.startswith('youversion~') and short==module_name(current):short=None
            if isinstance(short,str) and short.strip() and len(short)<=40 and not any(ord(c)<32 for c in short):
                caption=short
        self.set_hexpand(not in_header)
        self.caption.set_margin_start(0 if in_header else 16)
        self.caption.set_wrap(not in_header)
        self.caption.set_ellipsize(Pango.EllipsizeMode.END if in_header and len(caption)>4 else Pango.EllipsizeMode.NONE)
        if in_header:self.caption.add_css_class('dim-label')
        else:self.caption.remove_css_class('dim-label')
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
                if not self.owner.switch_translation(name):
                    raise ValueError(tab.status.get_text())
            self.status.set_visible(False)
            # Finish native row activation before rebuilding any models.
            from gi.repository import GLib
            GLib.idle_add(self.finish)
        except Exception as error:
            self.status.set_text(str(error));self.status.set_visible(True)
            from gi.repository import GLib
            GLib.idle_add(self.sync)

    def finish(self):
        if self.owner.closed:return False
        self.sync();self.popover.popdown();return False
