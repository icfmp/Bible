"""Local, source-aware note and place affordances in ordinary Bible prose."""
from gi.repository import Gtk, GLib, Pango
from .i18n import tr
from .reference_resolution import resolve
from .metadata_workers import MetadataExecutor


class InlineMarkers:
    def __init__(self,tab):
        self.tab=tab;self.geo={};self.pending=set();self.executor=MetadataExecutor()

    @property
    def owner(self):
        return getattr(getattr(self.tab,'sync_coordinator',None),'owner',None)

    def markers(self,reader,document):
        tab=self.tab;result={};primary={ref:s.reference for s in document.spans for ref in s.members};refs=set(primary)
        if tab.preferences.note_indicators and tab.notes_store:
            for note in tab.notes_store.all():
                if not note.body.strip():continue
                try:
                    from .reference_resolution import _span
                    mapped=resolve(note.start,note.versification,reader,require_entry=False)
                    reference=next((r for r in _span(mapped.start,mapped.end,reader.versification) if reader.has_reference(r)),None)
                except ValueError:continue
                if reference in refs:
                    entry=result.setdefault(primary[reference],{})
                    entry.setdefault('note',[]).append(note.id)
        if tab.preferences.place_markers:
            owner=self.owner
            if owner:
                from .place_data import PlaceData
                data=PlaceData(owner.library.root.parent/'study-data')
                key=(reader.name,reader.versification,document.key,data.revision)
                if data.revision and key not in self.geo and key not in self.pending:
                    self.load_places(key,data,reader,refs)
                for ref,places in self.geo.get(key,{}).items():
                    if ref in refs:
                        values=result.setdefault(primary[ref],{}).setdefault('place',[])
                        seen={p['id'] for p in values}
                        values.extend(p for p in places if p['id'] not in seen)
        return {ref:tuple((kind,payload) for kind,payload in sorted(values.items())) for ref,values in result.items()}

    def load_places(self,key,data,reader,refs):
        from .reference_targets import source_references
        owner=self.owner
        if not hasattr(owner,'_inline_marker_executor'):
            owner._inline_marker_executor=MetadataExecutor(thread_name_prefix='bible-inline-places')
        self.executor=owner._inline_marker_executor
        # SWORD handles stay on their owner thread; the worker uses SQLite only.
        origins={}
        for ref in refs:
            try:origins[ref]=set(source_references(reader,ref,ref))
            except ValueError:continue
        self.pending.add(key)
        future=self.executor.submit(data.query,set().union(*origins.values()) if origins else ())
        def complete():
            self.pending.discard(key)
            owner=self.owner;tab=self.tab
            if not owner or owner.closed or tab not in owner.tabs():return False
            try:
                places=future.result()
                self.geo[key]={ref:[p for p in places if supplied.intersection(p['references'])] for ref,supplied in origins.items()}
                self.geo[key]={ref:p for ref,p in self.geo[key].items() if p}
            except Exception as error:
                self.geo[key]={};self.error=str(error)
            if len(self.geo)>64:self.geo.pop(next(iter(self.geo)))
            if tab.current and ((tab.reader and tab.reader.name==key[0] and tab.current.reference==key[2])
                    or (tab._comparison_reader and tab._comparison_reader.name==key[0]
                        and getattr(tab,'_comparison_document',None) and tab._comparison_document.key==key[2])):
                tab.apply_appearance();tab.refresh_comparison()
            return False
        future.add_done_callback(lambda _:GLib.idle_add(complete))

    def button(self,view,reader,ref,kind,payload):
        title=tr('Notes on this verse' if kind=='note' else 'Places in this verse')
        button=Gtk.Button(icon_name='bible-notes-symbolic' if kind=='note' else 'bible-place-symbolic',
                          tooltip_text=title,halign=Gtk.Align.CENTER,valign=Gtk.Align.CENTER)
        button.add_css_class('flat');button.add_css_class('inline-marker')
        from .reference_preview import passage_title
        button.update_property([Gtk.AccessibleProperty.LABEL],[title+' · '+passage_title(ref,system=reader.versification)])
        button._marker_reference=ref;button._marker_kind=kind
        def activate(*_):
            owner=self.owner;tab=self.tab
            if not owner or owner.closed or owner.active_tab is not tab:return
            if kind=='note':
                try:reference=resolve(ref,reader.versification,tab.reader).start
                except ValueError:return
                tab.select_verse(reference);owner.reveal_passage_annotations()
            elif len(payload)==1:self.place(reader,ref,payload[0])
            else:
                pop=Gtk.Popover(autohide=False);pop.set_parent(button)
                owner._reading_popovers.append(pop)
                box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,margin_top=8,margin_bottom=8,margin_start=8,margin_end=8)
                from .place_names import place_name
                from .place_cards import STATUS
                names=[place_name(p['name']) for p in payload]
                for place in {p['id']:p for p in payload}.values():
                    name=place_name(place['name'])
                    modern='; '.join(dict.fromkeys(place_name(c['name']) for c in place['candidates'] if c['longitude'] is not None))
                    caption=name+'\n'+(modern+' · ' if modern else '')+tr(STATUS[place['status']])
                    if names.count(name)>1:caption+='\n'+tr('Source identity')+': '+place['id']
                    choice=Gtk.Button(child=Gtk.Label(label=caption,xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,max_width_chars=32));choice.add_css_class('flat')
                    choice._place_id=place['id']
                    choice.connect('clicked',lambda _,p=place:(pop.popdown(),self.place(reader,ref,p)))
                    box.append(choice)
                scroll=Gtk.ScrolledWindow(max_content_height=300,propagate_natural_height=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
                scroll.set_child(box);pop.set_child(scroll)
                unmap=button.connect('unmap',lambda *_:pop.popdown())
                def closed(*_):
                    if pop in owner._reading_popovers:owner._reading_popovers.remove(pop)
                    if button.handler_is_connected(unmap):button.disconnect(unmap)
                    GLib.idle_add(lambda:pop.unparent() or False)
                pop.connect('closed',closed)
                from .popover_dismissal import fit_reader_popover
                pop.connect('show',lambda *_:fit_reader_popover(pop,owner));pop.popup()
        button.connect('clicked',activate)
        return button

    def place(self,reader,ref,place):
        from .place_cards import PlaceCards
        owner=self.owner
        if not owner or owner.closed:return
        dialog=PlaceCards(owner,context=(reader.name,reader,ref,ref))
        from .reference_targets import source_references
        dialog.origins=set(source_references(reader,ref,ref))
        dialog.open_place(dict(place));dialog.back.set_visible(False)
        owner.place_dialog=dialog;dialog.present(owner)
