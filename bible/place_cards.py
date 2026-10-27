"""On-demand native place window, shared previews and contextual map."""
from concurrent.futures import ThreadPoolExecutor
from gi.repository import Adw,Gtk,GLib,Gio,GObject,Pango
from .i18n import tr
from .place_data import PlaceData,SOURCE_URL,LICENSE_URL,ODBL_URL
from .place_names import place_name
from .reference_targets import source_references,local_excerpt
from .reference_preview import passage_title
from .reference_resolution import VersificationMismatch

STATUS={'known':'Known identification','probable':'Probable identification',
        'disputed':'Disputed identification','unknown':'Unknown location'}


class PlaceItem(GObject.Object):
    def __init__(self,payload):super().__init__();self.payload=payload


class PlaceCards(Adw.Window):
    def __init__(self,owner,context=None):
        super().__init__(title=tr('Places in this passage'),default_width=640,default_height=720,
                         transient_for=owner,modal=True,destroy_with_parent=True)
        self.add_css_class(owner.reading_style.scope+'-window')
        self.owner=owner;self.closed=False;self.generation=0;self.rows=[];self.pending=False
        self.data=PlaceData(owner.library.root.parent/'study-data')
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='bible-places')
        tab=owner.active_tab
        self.context=context or ((tab.state.resource,tab.reader,*tab.selected_passage()) if tab and tab.reader else None)
        self.map_widget=None
        self.connect('close-request',self.on_closed)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header=Adw.HeaderBar(show_end_title_buttons=False)
        self.title=Gtk.Label(label=tr('Places in this passage'),ellipsize=Pango.EllipsizeMode.END,width_chars=1)
        self.title.add_css_class('heading');header.set_title_widget(self.title)
        self.back=Gtk.Button(icon_name='go-previous-symbolic',tooltip_text=tr('Back'),visible=False)
        self.back.connect('clicked',lambda *_:self.show_list());header.pack_start(self.back)
        close=Gtk.Button(icon_name='window-close-symbolic',tooltip_text=tr('Close'))
        close.add_css_class('flat');close.connect('clicked',lambda *_:self.close());header.pack_end(close)
        box.append(header)
        context=Gtk.Label(xalign=0,wrap=True,margin_start=16,margin_end=16,margin_bottom=8)
        if self.context:
            resource,reader,start,end=self.context
            context.set_text(tr('Studied passage: {passage}').format(passage=passage_title(start,end,reader.versification)))
        context.add_css_class('dim-label');self.passage_context=context
        box.append(context)
        self.pages=Gtk.Stack(vexpand=True,hhomogeneous=False,vhomogeneous=False);box.append(self.pages)
        listing=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10,margin_start=12,margin_end=12)
        self.status=Gtk.Label(xalign=0,wrap=True);listing.append(self.status)
        self.download=Gtk.Button(label=tr('Download place data'));self.download.connect('clicked',self.open_library);listing.append(self.download)
        self.model=Gio.ListStore.new(PlaceItem)
        factory=Gtk.SignalListItemFactory();factory.connect('setup',self.row_setup);factory.connect('bind',self.row_bind)
        self.list=Gtk.ListView(model=Gtk.NoSelection(model=self.model),factory=factory,vexpand=True)
        self.list.add_css_class('navigation-sidebar')
        scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER);scroll.set_child(self.list);listing.append(scroll)
        self.pages.add_named(listing,'list')
        self.card_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.pages.add_named(self.card_scroll,'card')
        credit=Gtk.Label(xalign=0,wrap=True,margin_start=16,margin_end=16,margin_top=8,margin_bottom=12)
        credit.set_markup(f'<a href="{SOURCE_URL}">OpenBible.info</a> · <a href="{LICENSE_URL}">CC BY 4.0</a>'
                          f' · <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>'
                          f' · <a href="{ODBL_URL}">ODbL</a>')
        credit.add_css_class('caption');box.append(credit)
        self.set_content(box);self.refresh()

    def present(self,parent=None):
        if parent:self.set_transient_for(parent)
        super().present()

    def stop_map(self):
        if self.map_widget:self.map_widget.stop();self.map_widget=None

    def on_closed(self,*_):
        if self.closed:return False
        self.stop_map()
        self.closed=True;self.generation+=1;self.executor.shutdown(wait=False,cancel_futures=True)
        if getattr(self.owner,'place_dialog',None) is self:self.owner.place_dialog=None
        return False

    def show_list(self):
        self.stop_map()
        self.generation+=1;self.pages.set_visible_child_name('list')
        self.back.set_visible(False);self.title.set_text(tr('Places in this passage'));self.set_title(tr('Places in this passage'))

    def message(self,value,download=False):
        self.status.set_text(value);self.status.set_tooltip_text(None);self.download.set_visible(download)

    def refresh(self):
        self.show_list();self.model.remove_all();self.rows=[];self.pending=False
        if not self.context:self.message(tr('Open a Bible passage to see its places.'));return
        if self.data.revision is None:
            self.message(tr('Download place data once to use it offline.'),True);return
        resource,reader,start,end=self.context
        try:origins=source_references(reader,start,end)
        except ValueError as error:
            self.message(tr('No verified alignment for this passage.'));self.status.set_tooltip_text(str(error));return
        self.origins=set(origins)
        self.message(tr('Loading places…'));self.pending=True;generation=self.generation
        future=self.executor.submit(self.data.query,origins)
        def complete():
            if self.closed or self.owner.closed or generation!=self.generation:return False
            self.pending=False
            try:self.rows=future.result()
            except Exception as error:
                self.message(tr('Place data is unavailable. Download it again from Library.'),True)
                self.status.set_tooltip_text(str(error));return False
            self.message(tr('{count} recorded places.').format(count=len(self.rows)) if self.rows else tr('No places recorded for this passage.'))
            self.model.splice(0,self.model.get_n_items(),[PlaceItem(p) for p in self.rows]);return False
        future.add_done_callback(lambda _:GLib.idle_add(complete))

    def row_setup(self,_,item):
        button=Gtk.Button();button.add_css_class('flat')
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,margin_top=6,margin_bottom=6)
        title=Gtk.Label(xalign=0,wrap=True,width_chars=1);title.add_css_class('heading');content.append(title)
        subtitle=Gtk.Label(xalign=0,wrap=True,width_chars=1);subtitle.add_css_class('dim-label');content.append(subtitle)
        button.set_child(content);button.connect('clicked',lambda b:self.open_place(b._place));item.set_child(button)

    def row_bind(self,_,item):
        button=item.get_child();place=item.get_item().payload;button._place=place
        title=button.get_child().get_first_child();title.set_text(place_name(place['name']))
        title.get_next_sibling().set_text(tr(STATUS[place['status']]))
        button.set_tooltip_text(tr('Related to {count} selected verses.').format(count=place['source_verse_count']))

    def open_library(self,*_):
        from .study_resources import PLACE_RESOURCE_ID
        library=self.owner.open_library('study')
        index=next(i for i,r in enumerate(library.filtered_resources) if r.id==PLACE_RESOURCE_ID)
        library.open_details(None,index)

    def label(self,text,*,caption=False):
        label=Gtk.Label(label=text,xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,selectable=True)
        if caption:label.add_css_class('caption');label.add_css_class('dim-label')
        return label

    def open_place(self,place):
        self.stop_map()
        self.generation+=1;self.current_place=place
        self.pages.set_visible_child_name('card');self.back.set_visible(True);self.title.set_text(place_name(place['name']))
        self.set_title(place_name(place['name']))
        card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_start=16,margin_end=16,margin_top=12,margin_bottom=16)
        card.append(self.label(tr(STATUS[place['status']])))
        map_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);card.append(map_box)
        located=[c for c in place['candidates'] if c['longitude'] is not None]
        if located:
            modern=self.label(tr('Proposed modern locations')+': '+ '; '.join(dict.fromkeys(place_name(c['name']) for c in located)))
            card.insert_child_after(modern,card.get_first_child())
        if located:
            try:
                from .place_map import PlaceMap
                self.map_widget=PlaceMap(located);map_box.append(self.map_widget)
            except (ImportError,ValueError):
                map_box.append(self.label(tr('Map unavailable; place information and references remain available.'),caption=True))
        else:
            map_box.append(self.label(tr('No identified location; no map pin is shown.'),caption=True))
        if len(located)>1:
            for index,candidate in enumerate(located):
                card.append(self.label(str(index+1)+'. '+place_name(candidate['name']),caption=True))
        self.reference_model=Gio.ListStore.new(PlaceItem)
        factory=Gtk.SignalListItemFactory();factory.connect('setup',self.reference_setup);factory.connect('bind',self.reference_bind)
        self.references=Gtk.ListView(model=Gtk.NoSelection(model=self.reference_model),factory=factory)
        self.reference_cache={};self.chapter_cache={}
        reference_title=self.label(tr('Related Bible references'));reference_title.add_css_class('heading');card.append(reference_title)
        references_scroll=Gtk.ScrolledWindow(min_content_height=160,max_content_height=280,propagate_natural_height=True,
                                            hscrollbar_policy=Gtk.PolicyType.NEVER)
        references_scroll.set_child(self.references);card.append(references_scroll)
        ordered=[ref for ref in place['references'] if ref in self.origins]+[ref for ref in place['references'] if ref not in self.origins]
        self.reference_model.splice(0,0,[PlaceItem(ref) for ref in ordered[:2]])
        all_refs=Gtk.Button(label=tr('View all'),visible=len(place['references'])>2)
        def show_all(*_):
            self.reference_model.splice(0,self.reference_model.get_n_items(),[PlaceItem(ref) for ref in ordered]);all_refs.set_visible(False)
        all_refs.connect('clicked',show_all);card.append(all_refs)
        clamp=Adw.Clamp(maximum_size=700,child=card);self.card_scroll.set_child(clamp)
        self.card_scroll.get_vadjustment().set_value(0)

    def reference_setup(self,_,item):
        button=Gtk.Button();button.add_css_class('flat');button.add_css_class('place-reference')
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        title=self.label('');title.set_selectable(False);title.add_css_class('accent');title.add_css_class('heading');content.append(title)
        body=self.label('');body.set_selectable(False)
        attrs=Pango.AttrList();attrs.insert(Pango.attr_weight_new(Pango.Weight.NORMAL));body.set_attributes(attrs);body.set_lines(3);body.set_ellipsize(Pango.EllipsizeMode.END);content.append(body)
        button.set_child(content);button.connect('clicked',self.preview_reference);item.set_child(button)

    def reference_bind(self,_,item):
        ref=item.get_item().payload;button=item.get_child();button._reference=ref
        resource,reader,_,_=self.context
        if ref not in self.reference_cache:
            try:
                excerpt=local_excerpt(reader,ref,limit=1,chapter_cache=self.chapter_cache)
                value=(passage_title(excerpt.start,excerpt.end,reader.versification),excerpt.text)
            except (ValueError,OSError) as error:value=(passage_title(ref),tr('No verified alignment for this passage.') if isinstance(error,VersificationMismatch) else tr('This passage is unavailable in the selected translation.'))
            self.reference_cache[ref]=value
        title,body=self.reference_cache[ref];label=button.get_child().get_first_child();label.set_text(title);label.get_next_sibling().set_text(body)

    def preview_reference(self,button):
        resource,reader,_,_=self.context
        self.owner.reference_preview.show(button,resource,reader,button._reference,
            provenance='OpenBible.info · CC BY 4.0\n'+SOURCE_URL,navigation_guard=self.navigate)

    def navigate(self,action):
        def run():self.close();action()
        editor=self.owner.note_editor
        if editor and not editor.closed:editor.after_close=run;editor.close()
        else:run()
