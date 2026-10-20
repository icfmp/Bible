"""Searchable language picker: CLDR/ISO names, native names and exact source codes."""
from gi.repository import Gtk
from .book_names import normalized
from .languages import language_name, language_info, search_terms
from .i18n import tr


class LanguagePicker(Gtk.MenuButton):
    def __init__(self,changed):
        super().__init__(label=tr('All languages'))
        self.changed=changed
        self.codes=[''];self.selected=0;self.visible_codes=['']
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

    def set_codes(self,codes):
        selected=self.codes[self.selected] if self.selected<len(self.codes) else ''
        self.codes=codes
        self.selected=codes.index(selected) if selected in codes else 0
        self.set_label(language_name(self.codes[self.selected]) if self.codes[self.selected] else tr('All languages'))
        self.filter()

    def get_selected(self):return self.selected

    def set_selected(self,index):
        self.selected=index if 0<=index<len(self.codes) else 0
        code=self.codes[self.selected]
        self.set_label(language_name(code) if code else tr('All languages'))
        self.changed()

    def filter(self,*_):
        query=normalized(self.search.get_text())
        self.visible_codes=[code for code in self.codes if not code or query in normalized(search_terms(code))]
        self.strings.splice(0,self.strings.get_n_items(),[
            self.display_language(code) if code else tr('All languages') for code in self.visible_codes])

    @staticmethod
    def display_language(code):
        name,native=language_info(code)
        return name+((' — '+native) if native and native.casefold()!=name.casefold() else '')+f' ({code})'

    def activate(self,_,index):
        self.set_selected(self.codes.index(self.visible_codes[index]));self.popdown()
