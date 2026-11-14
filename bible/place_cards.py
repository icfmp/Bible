"""On-demand native place window, shared previews and contextual map."""
from .metadata_workers import MetadataExecutor
from gi.repository import Adw,Gtk,GLib,Gio,GObject,Pango
from .i18n import tr
from .disclosure import disclosure
from .place_data import PlaceData,SOURCE_URL,LICENSE_URL,ODBL_URL
from .place_names import place_name
from .resource_details import plain
from .reference_targets import source_references,local_excerpt
from .reference_preview import passage_title
from .reference_resolution import VersificationMismatch

STATUS={'known':'Known identification','probable':'Probable identification',
        'disputed':'Disputed identification','unknown':'Unknown location'}


class PlaceItem(GObject.Object):
    def __init__(self,payload):super().__init__();self.payload=payload


class PlaceView(Adw.Bin):
    def __init__(self,owner,context=None,host=None):
        super().__init__()
        self.host=host
        self.add_css_class(owner.reading_style.scope+'-window')
        self.owner=owner;self.closed=False;self.generation=0;self.rows=[];self.pending=False
        self.data=PlaceData(owner.library.root.parent/'study-data')
        self.executor=MetadataExecutor(max_workers=1,thread_name_prefix='bible-places')
        tab=owner.active_tab
        self.context=context or ((tab.state.resource,tab.reader,*tab.selected_passage()) if tab and tab.reader else None)
        self.map_widget=None
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);self.layout=box
        header=Adw.HeaderBar(show_end_title_buttons=False)
        self.title=Gtk.Label(label=tr('Places in this passage'),ellipsize=Pango.EllipsizeMode.END,width_chars=1)
        self.title.add_css_class('heading');header.set_title_widget(self.title)
        self.back=Gtk.Button(icon_name='go-previous-symbolic',tooltip_text=tr('Back'),visible=False)
        self.back.connect('clicked',lambda *_:self.show_list());header.pack_start(self.back)
        box.append(header);self.header=header
        context=Gtk.Label(xalign=0,wrap=True,margin_start=16,margin_end=16,margin_bottom=8)
        if self.context:
            resource,reader,start,end=self.context
            context.set_text(tr('Studied passage: {passage}').format(passage=passage_title(start,end,reader.versification)))
        context.add_css_class('dim-label');self.passage_context=context
        box.append(context)
        self.pages=Gtk.Stack(vexpand=True,hhomogeneous=False,vhomogeneous=False);box.append(self.pages)
        self.pages.set_size_request(-1,min(360,max(120,owner.get_height()-300)))
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
        credit.add_css_class('caption');credit.add_css_class('source-attribution');box.append(credit)
        self.set_child(box);self.refresh()

    def close(self):
        if self.host:self.host.close()
        else:self.on_closed()

    def stop_map(self):
        if self.map_widget:self.map_widget.stop();self.map_widget=None

    def on_closed(self,*_):
        if self.closed:return False
        self.stop_map()
        self.closed=True;self.generation+=1;self.executor.shutdown(wait=False,cancel_futures=True)
        return False

    def show_list(self):
        self.stop_map()
        self.generation+=1;self.pages.set_visible_child_name('list')
        self.back.set_visible(False);self.title.set_text(tr('Places in this passage'))
        parent=self.passage_context.get_parent()
        if parent is not self.layout:
            if parent:parent.remove(self.passage_context)
            self.layout.insert_child_after(self.passage_context,self.header)
        self.passage_context.set_margin_start(16);self.passage_context.set_margin_end(16)
        if self.context:
            _,reader,start,end=self.context
            self.passage_context.set_text(tr('Studied passage: {passage}').format(passage=passage_title(start,end,reader.versification)))

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
        self.close()
        library=self.owner.open_library('study')
        library.reveal_study_resource(PLACE_RESOURCE_ID)

    def label(self,text,*,caption=False):
        label=Gtk.Label(label=text,xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,selectable=True)
        if caption:label.add_css_class('caption');label.add_css_class('dim-label')
        return label

    def open_place(self,place):
        self.stop_map()
        self.generation+=1;self.current_place=place
        self.pages.set_visible_child_name('card');self.back.set_visible(True);self.title.set_text(place_name(place['name']))
        card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_start=16,margin_end=16,margin_top=12,margin_bottom=16)
        located=[c for c in place['candidates'] if c['longitude'] is not None]
        # The supplied description can name a region while its representative
        # coordinate belongs to a modern site. Do not equate those two entities.
        descriptions=list(dict.fromkeys(plain(c.get('description') or c['name']) for c in located))
        self.location_description=self.label(descriptions[0] if len(located)==1 else
            tr('Several proposed locations') if len(located)>1 else tr('Unknown location'))
        self.location_description.add_css_class('heading')
        self.location_description.set_visible(self.location_description.get_text()!=place_name(place['name']))
        card.append(self.location_description)
        metadata=[]
        if place['status']!='known' and (located or place['status']!='unknown'):metadata.append(tr(STATUS[place['status']]))
        if len(located)==1:
            note=self.location_note(located[0])
            if note:metadata.append(note)
        parent=self.passage_context.get_parent()
        if parent:parent.remove(self.passage_context)
        self.passage_context.set_margin_start(0);self.passage_context.set_margin_end(0)
        self.passage_context.add_css_class('caption')
        resource,reader,start,end=self.context
        self.passage_context.set_text(' · '.join(metadata+[tr('Studied passage: {passage}').format(passage=passage_title(start,end,reader.versification))]))
        card.append(self.passage_context)
        aliases=list(dict.fromkeys(place_name(alias) for alias in place.get('aliases',[]) if alias!=place['name']))
        if aliases:
            caption=tr('Names recorded by the source')+' · '+', '.join(aliases[:3])
            names=disclosure()
            names.set_label_widget(Gtk.Label(label=caption,xalign=0,wrap=True,
                width_chars=1,wrap_mode=Pango.WrapMode.WORD_CHAR))
            names.update_property([Gtk.AccessibleProperty.LABEL],[caption])
            names.set_child(self.label(', '.join(aliases),caption=True));card.append(names)
        map_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);card.append(map_box)
        if located:
            try:
                from .place_map import PlaceMap
                self.map_widget=PlaceMap(located);map_box.append(self.map_widget)
            except (ImportError,ValueError):
                map_box.append(self.label(tr('Map unavailable; place information and references remain available.'),caption=True))
        else:
            map_box.append(self.label(tr('No identified location; no map pin is shown.'),caption=True))
        if len(located)>1:
            # Group presentation by the supplied modern ID, never by name or
            # nearby coordinates. Every proposal/path remains in the index/map.
            groups={}
            for candidate in located:groups.setdefault(candidate['modern_id'],[]).append(candidate)
            for proposals in groups.values():
                card.append(self.label(place_name(proposals[0]['name']),caption=True))
                if len(proposals)>1:card.append(self.label(tr('{count} source proposals for this site').format(count=len(proposals)),caption=True))
                for candidate in proposals:
                    description=plain(candidate.get('description',''))
                    if description:card.append(self.label(description,caption=True))
                    note=self.location_note(candidate)
                    if note:card.append(self.label(note,caption=True))
        if located and any(c['longitude'] is None for c in place['candidates']):
            card.append(self.label(tr('Other proposed locations have not been identified on the map.'),caption=True))
        evidence=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_top=8)
        for candidate in place['candidates']:
            source=candidate.get('coordinate_source',{})
            url=source.get('url','')
            if source.get('type')=='wikidata':
                import re
                if re.fullmatch(r'Q[1-9][0-9]*',source.get('id','')):url='https://www.wikidata.org/wiki/'+source['id']
            if url:evidence.append(self.link_label(url,place_name(candidate['name'])+' · '+tr('Coordinate source')))
        for source in place.get('sources',[]):
            evidence.append(self.label(source['name'],caption=True))
        evidence.append(self.link_label(place['source_url'],'OpenBible.info · CC BY 4.0'))
        sources=disclosure(label=tr('Sources and evidence'));sources.set_child(evidence);card.append(sources)
        self.reference_model=Gio.ListStore.new(PlaceItem)
        self.reference_cache={};self.chapter_cache={}
        reference_title=self.label(tr('Related Bible references'));reference_title.add_css_class('heading');card.append(reference_title)
        ordered=[ref for ref in place['references'] if ref in self.origins]+[ref for ref in place['references'] if ref not in self.origins]
        self.reference_model.splice(0,0,[PlaceItem(ref) for ref in ordered])
        # One virtualized body: metadata/map header and every reference use
        # the same adjustment. Large place inventories do not create hundreds
        # of native buttons/excerpts before the user reaches them.
        header_model=Gio.ListStore.new(PlaceItem);header_model.append(PlaceItem(None))
        sections=Gio.ListStore.new(Gio.ListModel);sections.append(header_model);sections.append(self.reference_model)
        model=Gtk.FlattenListModel(model=sections)
        factory=Gtk.SignalListItemFactory()
        factory.connect('setup',lambda _,item:(item.set_activatable(False),item.set_selectable(False)))
        header=Adw.Clamp(maximum_size=700,child=card)
        def bind(_,item):
            ref=item.get_item().payload
            if ref is None:item.set_child(header)
            else:
                button=self.reference_button();self.bind_reference(button,ref)
                button.set_margin_start(16);button.set_margin_end(16)
                item.set_child(Adw.Clamp(maximum_size=700,child=button))
        factory.connect('bind',bind);factory.connect('unbind',lambda _,item:item.set_child(None))
        self.references=Gtk.ListView(model=Gtk.NoSelection(model=model),factory=factory)
        self.card_scroll.set_child(self.references)
        self.card_scroll.get_vadjustment().set_value(0)

    def link_label(self,url,title,license_url='',license_name=''):
        from urllib.parse import urlsplit
        label=self.label('',caption=True)
        if urlsplit(url).scheme not in ('http','https'):label.set_text(title);return label
        value='<a href="'+GLib.markup_escape_text(url)+'">'+GLib.markup_escape_text(title)+'</a>'
        if license_url and urlsplit(license_url).scheme in ('http','https'):
            value+=' · <a href="'+GLib.markup_escape_text(license_url)+'">'+GLib.markup_escape_text(license_name)+'</a>'
        label.set_markup(value);return label

    def location_note(self,candidate):
        if candidate.get('role') in ('center','representative point') or candidate.get('radius_meters'):
            return tr('Approximate location')
        if candidate.get('role')=='settlement':return tr('Within the proposed modern settlement')
        return tr({'near':'Near this location','along':'Along this geographical feature','on':'On this geographical feature',
                   '<':'Within this area','>':'Around this location'}.get(candidate.get('modifier'),''))

    def reference_setup(self,_,item):
        item.set_child(self.reference_button())

    def reference_button(self):
        from .passage_card import passage_card
        button=passage_card();button.add_css_class('place-reference')
        button.connect('clicked',self.preview_reference);return button

    def reference_bind(self,_,item):
        self.bind_reference(item.get_child(),item.get_item().payload)

    def bind_reference(self,button,ref):
        button._reference=ref
        resource,reader,_,_=self.context
        if ref not in self.reference_cache:
            try:
                excerpt=local_excerpt(reader,ref,limit=1,chapter_cache=self.chapter_cache)
                value=(passage_title(excerpt.start,excerpt.end,reader.versification),excerpt.text)
            except (ValueError,OSError) as error:value=(passage_title(ref),tr('No verified alignment for this passage.') if isinstance(error,VersificationMismatch) else tr('This passage is unavailable in the selected translation.'))
            self.reference_cache[ref]=value
        title,body=self.reference_cache[ref];heading,excerpt=button._reference_labels
        heading.set_text(title);excerpt.set_text(body)

    def preview_reference(self,button):
        resource,reader,_,_=self.context
        self.owner.reference_preview.show(button,resource,reader,button._reference,
            provenance='OpenBible.info · CC BY 4.0\n'+SOURCE_URL,navigation_guard=self.navigate)

    def navigate(self,action):
        def run():self.close();action()
        editor=self.owner.note_editor
        if editor and not editor.closed:editor.after_close=run;editor.close()
        else:run()
