"""Searchable language picker: CLDR/ISO names, native names and exact source codes."""
from gi.repository import Gtk,GLib
from .book_names import normalized
from .languages import language_name, language_info, search_terms
from .i18n import tr


class LanguagePicker(Gtk.MenuButton):
    def __init__(self,changed):
        super().__init__(label=tr('All languages'))
        self.changed=changed
        self.codes=[''];self.selected=0;self.visible_codes=[''];self.prepared={}
        self._model_generation=0;self._desired_labels=[];self._label_codes={}
        popover=Gtk.Popover()
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_top=12,margin_bottom=12,margin_start=12,margin_end=12)
        self.search=Gtk.SearchEntry(placeholder_text=tr('Search languages'))
        self.search.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search languages')])
        self.search.connect('search-changed',self.filter)
        box.append(self.search)
        self.strings=Gtk.StringList.new([])
        self.selection=Gtk.SingleSelection(model=self.strings,autoselect=False)
        factory=Gtk.SignalListItemFactory()
        factory.connect('setup',lambda _,item:item.set_child(Gtk.Label(xalign=0,wrap=True,margin_top=8,margin_bottom=8)))
        factory.connect('bind',lambda _,item:item.get_child().set_text(item.get_item().get_string()))
        self.list=Gtk.ListView(model=self.selection,factory=factory,single_click_activate=True)
        self.list.connect('activate',self.activate)
        scroll=Gtk.ScrolledWindow(min_content_width=260,min_content_height=250,max_content_height=380,propagate_natural_height=True)
        scroll.set_child(self.list);box.append(scroll)
        popover.set_child(box);self.set_popover(popover)
        popover.connect('show',lambda *_:self.search.grab_focus())
        self.filter()

    def set_codes(self,codes,prepared=None):
        if codes==self.codes and (prepared or {})==self.prepared:return
        selected=self.codes[self.selected] if self.selected<len(self.codes) else ''
        self.codes=codes
        self.prepared=prepared or {}
        self.selected=codes.index(selected) if selected in codes else 0
        self.set_label(self.name(self.codes[self.selected]))
        self.filter()

    def cancel_pending(self):self._model_generation+=1

    def get_selected(self):return self.selected

    def set_selected(self,index):
        self.selected=index if 0<=index<len(self.codes) else 0
        code=self.codes[self.selected]
        self.set_label(self.name(code))
        self.changed()

    def filter(self,*_):
        query=normalized(self.search.get_text())
        self.visible_codes=[code for code in self.codes if not code or query in (
            self.prepared[code][2] if code in self.prepared else normalized(search_terms(code)))]
        labels=[self.prepared[code][1] if code in self.prepared else
                self.display_language(code) if code else tr('All languages') for code in self.visible_codes]
        self._label_codes=dict(zip(labels,self.visible_codes))
        if labels==self._desired_labels:return
        self._desired_labels=labels;self._model_generation+=1;generation=self._model_generation
        previous=[self.strings.get_string(i) for i in range(self.strings.get_n_items())]
        prefix=0
        while prefix<min(len(previous),len(labels)) and previous[prefix]==labels[prefix]:prefix+=1
        suffix=0
        while suffix<min(len(previous),len(labels))-prefix and previous[-1-suffix]==labels[-1-suffix]:suffix+=1
        remove=len(previous)-prefix-suffix;add=labels[prefix:len(labels)-suffix if suffix else len(labels)];offset=0
        def update():
            nonlocal remove,offset
            if generation!=self._model_generation:return False
            # Bound native row rebinding as catalogues progressively add languages.
            if remove:
                count=min(remove,16);self.strings.splice(prefix+remove-count,count,[]);remove-=count
            elif offset<len(add):
                batch=add[offset:offset+16];self.strings.splice(prefix+offset,0,batch);offset+=len(batch)
            return bool(remove or offset<len(add))
        if update():GLib.idle_add(update)

    def name(self,code):
        return self.prepared[code][0] if code in self.prepared else language_name(code) if code else tr('All languages')

    @staticmethod
    def display_language(code):
        name,native=language_info(code)
        return name+((' — '+native) if native and native.casefold()!=name.casefold() else '')+f' ({code})'

    def activate(self,_,index):
        # During a bounded update, retained suffix rows may have old indexes.
        # Resolve the actual displayed row, never a future model position.
        code=self._label_codes.get(self.strings.get_string(index))
        if code is not None and code in self.codes:self.set_selected(self.codes.index(code));self.popdown()
