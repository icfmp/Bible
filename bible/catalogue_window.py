"""Catalogue/download UI kept separate from the reading surface."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from threading import Event
import json
import time
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, GLib, Gtk, Pango, Gio, GObject

from .i18n import tr
from .library import catalogues as catalogue
from .providers import PROVIDERS
from .book_names import normalized
from .resource_details import details, language_name, plain
from .language_picker import LanguagePicker
from .catalogue_session import CatalogueSession
from .languages import canonical_language


class ResourceItem(GObject.Object):
    def __init__(self,resource):
        super().__init__();self.resource=resource


class MetadataLabel(Gtk.Label):
    """Keep native selection/copy, without GtkLabel's focus-time Select All."""
    def do_grab_focus(self):
        result = Gtk.Label.do_grab_focus(self)
        self.select_region(0, 0)
        return result


class CatalogueWindow(Adw.Window):
    def __init__(self, parent, library, on_installed):
        super().__init__(transient_for=parent, modal=True, title=tr('Library'),
                         default_width=560, default_height=640)
        self.set_size_request(320,320)
        self.library, self.on_installed = library, on_installed
        self.owner = parent
        self.add_css_class(parent.reading_style.scope+'-window')
        self._covered=frozenset();self._catalogue_errors={};self._loading_tick=0
        from .study_resources import StudyResources
        self.study_resources=StudyResources(library.root.parent/'study-data')
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='bible-download')
        existing=getattr(parent,'catalogue_session',None)
        if not existing:parent.catalogue_session=CatalogueSession(library)
        self.session=parent.catalogue_session;self.cache=self.session.cache
        self.resources=[];self.preparing=True
        self._installed_metadata={};self._study_installed=frozenset();self._study_current=frozenset()
        self._language_records={};self._search_terms={};self._rows_generation=0;self._building_rows=False;self._refresh_generation=0
        self._pending_resource=None
        self._bound_rows={};self._task_resource=None;self._cancel=Event()
        self._install_started=False
        self.open_context=None
        self.settings=parent.application_settings
        self.language_choice=self.settings.language
        self.timings={}
        self._completed_resource=None
        self._failed_resource=None
        self.filtered_resources = []
        self.languages = []
        self.source_ids = [None] + [p.id for p in PROVIDERS]
        self._filtering = False
        self._transfer_busy = False
        self.refreshing = False
        self.closed = False
        self._task_id = 0
        self._pulse_id = 0
        self._phase = "idle"
        self._indeterminate = False
        self._pending_progress = None
        self._progress_lock = Lock()
        self.connect('close-request', self.on_close)
        layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header=Adw.HeaderBar()
        self.back_button=Gtk.Button(icon_name='go-previous-symbolic',tooltip_text=tr('Back'),visible=False)
        self.back_button.connect('clicked',self.back_to_list);header.pack_start(self.back_button)
        header.set_title_widget(Adw.WindowTitle(title=tr('Library')))
        self.catalogue_button=Gtk.Button(icon_name='view-refresh-symbolic',tooltip_text=tr('Refresh catalogue'))
        self.catalogue_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Refresh catalogue')])
        self.catalogue_button.connect('clicked',self.load_catalogue);header.pack_end(self.catalogue_button)
        layout.append(header)
        self.pages=Gtk.Stack(vexpand=True)
        explorer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10,margin_top=16)
        views=Gtk.Box(spacing=0,halign=Gtk.Align.CENTER);views.add_css_class('linked')
        self.bibles_button=Gtk.ToggleButton(label=tr('Bibles'),active=True)
        self.commentaries_button=Gtk.ToggleButton(label=tr('Commentaries'),group=self.bibles_button)
        self.bibles_button.connect('toggled',lambda button:self.kind.set_selected(0) if button.get_active() else None)
        self.commentaries_button.connect('toggled',lambda button:self.kind.set_selected(1) if button.get_active() else None)
        views.append(self.bibles_button);views.append(self.commentaries_button);explorer.append(views)
        self.type_tabs=views
        self.search=Gtk.SearchEntry(placeholder_text=tr('Search resources'),margin_start=12,margin_end=12)
        self.search.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search resources')])
        self.search.connect('search-changed',self.filter_resources);explorer.append(self.search)
        filters=Gtk.Box(spacing=8,margin_start=12,margin_end=12)
        self.kind=Gtk.DropDown(model=Gtk.StringList.new([tr('Bibles'),tr('Commentaries'),tr('Study resources')]))
        self.kind.update_property([Gtk.AccessibleProperty.LABEL],[tr('Resource type')])
        self.kind.connect('notify::selected',self.update_languages)
        self.language=LanguagePicker(self.language_changed);self.language.set_hexpand(True)
        self.language.prepare_languages=self.session.load_languages
        self.language.update_property([Gtk.AccessibleProperty.LABEL],[tr('Language')]);filters.append(self.language)
        explorer.append(filters)
        self.source_filter=Gtk.DropDown(model=Gtk.StringList.new([tr('All sources')]+[p.name for p in PROVIDERS]))
        from .version_chooser import bounded_choices
        bounded_choices(self.source_filter)
        self.source_filter.update_property([Gtk.AccessibleProperty.LABEL],[tr('Source')])
        self.source_filter.connect('notify::selected',self.update_languages);filters.append(self.source_filter)
        narrow=Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 440px'))
        narrow.add_setter(filters,'orientation',Gtk.Orientation.VERTICAL)
        self.add_breakpoint(narrow)
        self.choice_model=Gio.ListStore.new(ResourceItem)
        self.choices=Gtk.SingleSelection(model=self.choice_model)
        self.choices.connect('notify::selected',self.selection_changed)
        factory=Gtk.SignalListItemFactory()
        factory.connect('setup',self.setup_resource_row);factory.connect('bind',self.bind_resource_row)
        factory.connect('unbind',lambda _,item:self._bound_rows.pop(item,None))
        self.resource_list=Gtk.ListView(model=self.choices,factory=factory,single_click_activate=True)
        self.resource_list.set_show_separators(True)
        self.resource_list.connect('activate',self.open_details)
        self.list_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.list_scroll.set_child(self.resource_list)
        self.result_pages=Gtk.Stack(vexpand=True)
        self.result_pages.add_named(self.list_scroll,'rows')
        self.skeleton=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14,margin_start=20,margin_end=20,margin_top=20)
        self.loading_phase=Gtk.Label(wrap=True,xalign=0,max_width_chars=40)
        self.skeleton.append(self.loading_phase)
        for i in range(5):
            row=Gtk.Box(spacing=12)
            icon=Gtk.DrawingArea(width_request=34,height_request=38)
            def draw(area,cr,w,h):
                cr.set_source_rgba(.5,.5,.5,.25);cr.rectangle(0,0,w,h);cr.fill()
            icon.set_draw_func(draw);row.append(icon)
            lines=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,hexpand=True)
            for width in (150,220):
                line=Gtk.DrawingArea(height_request=12,width_request=width,halign=Gtk.Align.START)
                line.set_draw_func(draw);lines.append(line)
            row.append(lines);self.skeleton.append(row)
        self.skeleton.set_can_target(False)
        self.result_pages.add_named(self.skeleton,'loading')
        self.empty_page=Adw.StatusPage(icon_name='edit-find-symbolic')
        empty_actions=Gtk.Box(spacing=8,halign=Gtk.Align.CENTER)
        clear=Gtk.Button(label=tr('Clear filters'));clear.connect('clicked',self.clear_filters);empty_actions.append(clear)
        retry=self.result_retry=Gtk.Button(label=tr('Refresh catalogue'));retry.connect('clicked',self.load_catalogue);empty_actions.append(retry)
        self.empty_page.set_child(empty_actions);self.result_pages.add_named(self.empty_page,'empty')
        self.result_pages.set_visible_child_name('loading');explorer.append(self.result_pages)
        self.catalogue_progress=Gtk.ProgressBar(visible=True,margin_start=12,margin_end=12)
        explorer.append(self.catalogue_progress)
        self.empty=Gtk.Label(label=tr('No matching resource.'),wrap=True,visible=False,margin_top=20,margin_bottom=20)
        # Retain the explanatory label as a queryable compatibility surface;
        # the centered native status page owns its visible presentation.
        self.pages.add_named(explorer,'list')
        detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_start=20,margin_end=20,margin_top=12,margin_bottom=12)
        self.metadata=MetadataLabel(xalign=0,yalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,selectable=True,max_width_chars=55)
        metadata_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        metadata_scroll.set_child(self.metadata);detail.append(metadata_scroll)
        self.download_button=Gtk.Button(label=tr('Download'),sensitive=False,halign=Gtk.Align.CENTER)
        self.download_button.add_css_class('suggested-action')
        self.download_button.connect('clicked',self.install);detail.append(self.download_button)
        self.installed_state=Gtk.Box(spacing=6,halign=Gtk.Align.CENTER,visible=False)
        self.installed_state.append(Gtk.Image(icon_name='emblem-ok-symbolic'))
        self.installed_state.append(Gtk.Label(label=tr('Installed — available offline'),wrap=True))
        detail.append(self.installed_state)
        self.read_button=Gtk.Button(label=tr('Read'),halign=Gtk.Align.CENTER,visible=False)
        self.read_button.connect('clicked',lambda *_:self.read_resource(self.selected_resource()))
        detail.append(self.read_button)
        self.pages.add_named(detail,'detail');layout.append(self.pages)
        self.progress=Gtk.ProgressBar(margin_start=12,margin_end=12,visible=False)
        layout.append(self.progress)
        self.cancel_button=Gtk.Button(child=Gtk.Label(label=tr('Cancel download'),wrap=True),halign=Gtk.Align.CENTER,visible=False)
        self.cancel_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Cancel download')])
        self.cancel_button.connect('clicked',self.cancel_download);layout.append(self.cancel_button)
        self.status=Gtk.Label(xalign=0,wrap=True,selectable=True,margin_start=12,margin_end=12,margin_bottom=12,visible=False)
        layout.append(self.status)
        self.refresh_status=Gtk.Label(xalign=0,wrap=True,margin_start=12,margin_end=12,margin_bottom=8)
        self.refresh_status.add_css_class('dim-label');layout.append(self.refresh_status)
        if self.resources:self.refresh_status.set_text(tr('Saved catalogue — available offline.'))
        self.set_content(layout)
        self._catalogue_requested=False
        self.update_languages()
        self.refresh_status.set_text(tr('Loading saved resources…'))
        self.session.subscribe(self.snapshot_ready)
        if existing and self.session.bootstrap_future.done():self.session.reload_installed()
        self.connect('map',lambda *_:GLib.timeout_add(100,self.auto_load))

    @property
    def busy(self):return self._transfer_busy or self.refreshing or self.preparing or self._building_rows

    def snapshot_ready(self,snapshot):
        # The service publishes plain immutable snapshots from metadata workers.
        GLib.idle_add(self.apply_snapshot,snapshot)

    def apply_snapshot(self,snapshot):
        if self.closed or snapshot.generation<self._refresh_generation:return False
        changed=(self.resources!=list(snapshot.resources) or self._installed_metadata!=snapshot.installed
                 or self._study_installed!=snapshot.study_installed or self._study_current!=snapshot.study_current
                 or self._language_records!=snapshot.languages)
        self._covered=snapshot.covered_providers;self._catalogue_errors=snapshot.errors
        self.preparing=False;self.resources=list(snapshot.resources)
        self._installed_metadata=snapshot.installed;self._study_installed=snapshot.study_installed
        self._study_current=snapshot.study_current;self._language_records=snapshot.languages
        self._search_terms=snapshot.search;self.timings.update(snapshot.timings)
        if snapshot.generation>=self._refresh_generation:self.refreshing=snapshot.refreshing
        if changed:self.update_languages()
        self.update_result_state()
        self.refresh_controls()
        if not self._catalogue_requested and self.get_mapped():GLib.idle_add(self.auto_load)
        return False

    def clear_filters(self,*_):
        self.search.set_text('');self.source_filter.set_selected(0)
        self.language.set_selected(0);self.filter_resources()

    def update_result_state(self,rows=None):
        if not hasattr(self,'refresh_status'):return
        rows=self.filtered_resources if rows is None else rows
        study=self.kind.get_selected()==2
        index=self.source_filter.get_selected()
        providers=(PROVIDERS[index-1],) if 0<index<=len(PROVIDERS) else PROVIDERS
        complete=study or all(p.id in self._covered for p in providers)
        names={p.name for p in providers}
        all_names={p.name for p in PROVIDERS}
        errors={name:error for name,error in self._catalogue_errors.items() if not index or name in names or name not in all_names}
        self.result_retry.set_label(tr('Retry') if errors else tr('Refresh catalogue'))
        pending=self.preparing or self.refreshing or (not self._catalogue_requested and not complete and not errors and self.settings.value['automatic_catalogue_refresh'] and not study)
        if rows:
            state='rows'
            message=(tr('Refreshing sources…') if pending else tr('Partial catalogue. Retry to reload unavailable sources.') if errors else '')
        elif pending:
            state='loading';message=tr('Loading catalogue…')
        else:
            state='empty'
            title=tr('Catalogue unavailable') if errors else tr('No Bible found') if complete and self.kind.get_selected()==0 else tr('No matching resource.') if complete else tr('Catalogue not loaded')
            language=self.language.codes[self.language.get_selected()] if self.language.get_selected()<len(self.language.codes) else ''
            description=(tr('Retry or open installed resources. No files were removed.') if errors else
                tr('No resources match the current filters. Clear filters, choose another language or refresh.') if complete else
                tr('Refresh the catalogue to discover resources.'))
            if language:description+=' '+tr('Language')+': '+self.language_label(language)
            if self.search.get_text():description+=' '+tr('Search')+': '+self.search.get_text()
            if index:description+=' '+tr('Source')+': '+providers[0].name
            if errors:description+='\n'+'\n'.join(f'{name}: {error}' for name,error in errors.items())
            self.empty_page.set_title(title);self.empty_page.set_description(GLib.markup_escape_text(description))
            self.empty.set_text(description);message=title
        self.loading_phase.set_text(tr('Preparing saved resource metadata…') if self.preparing else tr('Looking for available resources from the selected sources…') if self.refreshing else tr('Preparing Library…'))
        self.result_pages.set_visible_child_name(state)
        if errors:message+='\n'+'\n'.join(f'{name}: {error}' for name,error in errors.items())
        self.refresh_status.set_text(message);self.refresh_status.set_visible(bool(message))
        if not self._transfer_busy and self._phase!='error' and self._completed_resource is None:
            self.status.set_text(message);self.status.set_visible(False)
        self.catalogue_progress.set_visible(pending)
        if not pending and self._loading_tick:
            self.catalogue_progress.remove_tick_callback(self._loading_tick);self._loading_tick=0;self.skeleton.set_opacity(1)
        if pending and not self._loading_tick:
            def pulse(widget,clock):
                if self.closed or not self.catalogue_progress.get_visible():
                    self.skeleton.set_opacity(1);self._loading_tick=0;return False
                animated=Gtk.Settings.get_default().get_property('gtk-enable-animations')
                if animated:
                    import math
                    self.skeleton.set_opacity(.7+.25*math.sin(clock.get_frame_time()/1000000*3))
                    self.catalogue_progress.pulse()
                else:self.skeleton.set_opacity(1)
                return True
            self._loading_tick=self.catalogue_progress.add_tick_callback(pulse)

    def auto_load(self,*_):
        if self.kind.get_selected()==2:return False
        if not self.closed and not self._catalogue_requested and not self.busy and self.settings.value['automatic_catalogue_refresh']:self.load_catalogue(force=False)
        return False

    def setup_resource_row(self,_,item):
        box=Gtk.Box(spacing=10,margin_start=12,margin_end=12,margin_top=10,margin_bottom=10)
        labels=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,hexpand=True)
        title=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,lines=2,ellipsize=Pango.EllipsizeMode.END,max_width_chars=40,width_chars=1)
        title.add_css_class('heading');labels.append(title)
        subtitle=Gtk.Label(xalign=0,wrap=True,max_width_chars=40)
        subtitle.add_css_class('dim-label');labels.append(subtitle);box.append(labels)
        item.title=title;item.subtitle=subtitle
        item.action=Gtk.Button(icon_name='folder-download-symbolic',valign=Gtk.Align.CENTER)
        item.action.add_css_class('flat')
        item.action.connect('clicked',lambda *_:self.row_action(item.get_item().resource) if item.get_item() else None)
        box.append(item.action)
        item.state=Gtk.Label(wrap=True,max_width_chars=12,valign=Gtk.Align.CENTER)
        item.state.add_css_class('caption');box.append(item.state)
        item.set_child(box)

    def bind_resource_row(self,_,item):
        resource=item.get_item().resource
        self._bound_rows[item]=resource
        installed=resource.id in getattr(self,'_installed_ids',set()) and (resource.kind!='study' or resource.id in self._study_current)
        busy=self._transfer_busy and self._task_resource==resource.id
        stamp=(resource,installed,self._transfer_busy,self._phase if busy else None,
               self.progress.get_text() if busy else None,self._failed_resource==resource.id)
        if getattr(item,'_render_stamp',None)==stamp:return
        item._render_stamp=stamp
        item.title.set_text(plain(resource.description))
        item.subtitle.set_text(self.language_label(resource.language)+' — '+resource.source)
        item.state.set_text(tr('Installing and checking…') if busy and self._phase=='installing' else
                            self.progress.get_text() or tr('Downloading…') if busy else tr('Installed') if installed else '')
        item.state.set_visible(busy or installed)
        item.action.set_icon_name('media-playback-start-symbolic' if installed else 'folder-download-symbolic')
        label=tr('Read') if installed and resource.kind=='bible' else tr('Open') if installed else tr('Retry') if self._failed_resource==resource.id else tr('Download')
        item.action.set_tooltip_text(label+' — '+plain(resource.description))
        item.action.update_property([Gtk.AccessibleProperty.LABEL],[label+' — '+plain(resource.description)])
        item.action.set_sensitive(installed or (resource.installable and not self._transfer_busy))
        item.action.set_visible(not (installed and resource.kind=='study'))
        item.get_child().set_tooltip_text(resource.name+' · '+resource.language)

    def refresh_rows(self):
        for item in list(self._bound_rows):
            if item.get_item():self.bind_resource_row(None,item)

    def row_action(self,resource):
        if resource.id in self.installed_ids() and (resource.kind!='study' or resource.id in self._study_current):self.read_resource(resource)
        else:self.install(resource=resource)

    def read_resource(self,resource):
        if not resource or resource.id not in self.installed_ids():return
        try:
            if self.owner.open_installed_resource(resource.id,self.open_context):self.close();return
            message=tr('This reading tab is no longer available. Open Library again from the intended tab.')
        except (OSError,ValueError) as error:message=str(error)
        self.status.set_text(message);self.status.set_visible(True)

    def open_details(self,_,index):
        self._list_position=self.list_scroll.get_vadjustment().get_value()
        self.choices.set_selected(index);self.selection_changed()
        self.pages.set_visible_child_name('detail');self.back_button.set_visible(True)
        self.metadata.select_region(0, 0)
        self.back_button.grab_focus()

    def reveal_study_resource(self,identifier):
        self.back_to_list()
        self.kind.set_selected(2);self.search.set_text('');self.filter_resources()
        attempts=[0]
        def reveal():
            if self.closed or self.kind.get_selected()!=2 or self.search.get_text() or self.pages.get_visible_child_name()!='list':return False
            attempts[0]+=1
            if self.preparing or self._building_rows:
                return attempts[0]<200
            index=next((i for i,r in enumerate(self.filtered_resources) if r.id==identifier),None)
            if index is not None:self.open_details(None,index)
            return False
        GLib.timeout_add(16,reveal)

    def back_to_list(self,*_):
        self.pages.set_visible_child_name('list');self.back_button.set_visible(False)
        self.list_scroll.get_vadjustment().set_value(getattr(self,'_list_position',0))

    def current_resources(self):
        if self.kind.get_selected()==2:
            return self.study_resources.available()
        resources={r.id:r for r in self.resources};resources.update(self._installed_metadata)
        kind = 'commentary' if self.kind.get_selected() == 1 else 'bible'
        index = self.source_filter.get_selected()
        provider_id = self.source_ids[index] if index < len(self.source_ids) else None
        return [resource for resource in resources.values() if resource.kind == kind
                and (provider_id is None or resource.provider_id == provider_id)]

    def update_languages(self, *_):
        study=self.kind.get_selected()==2
        self.type_tabs.set_visible(not study)
        if not study:
            (self.commentaries_button if self.kind.get_selected()==1 else self.bibles_button).set_active(True)
        wording=tr('Search resources') if study else tr('Search commentaries') if self.kind.get_selected()==1 else tr('Search Bibles')
        self.search.set_placeholder_text(wording);self.search.update_property([Gtk.AccessibleProperty.LABEL],[wording])
        self.language.set_visible(not study);self.source_filter.set_visible(not study)
        self.catalogue_button.set_visible(not study)
        self._filtering=True
        self.languages=['']+sorted(({canonical_language(code) for code in self._language_records}|{canonical_language(self.language_choice)}|{'en','fr'})-{''},key=lambda code:self.language_label(code).casefold())
        self.language.set_codes(self.languages,self._language_records)
        self.language.set_selected(self.languages.index(canonical_language(self.language_choice)) if canonical_language(self.language_choice) in self.languages else 0)
        self._filtering=False
        self.filter_resources()
        if not self.busy and not self.resources and self.get_mapped():
            GLib.idle_add(self.auto_load)

    def language_changed(self):
        if self._filtering:return
        self.language_choice=self.language.codes[self.language.get_selected()]
        try:self.settings.set('library_language',self.language_choice)
        except (OSError,ValueError) as error:self.status.set_text(str(error));self.status.set_visible(True)
        self.filter_resources()

    def filter_resources(self, *_):
        if self.closed:return False
        if self._filtering:
            return
        selected=self.selected_resource()
        selected_id=selected.id if selected else None
        position=self.list_scroll.get_vadjustment().get_value()
        index = self.language.get_selected()
        language = self.language.codes[index] if index < len(self.language.codes) else ''
        query = normalized(self.search.get_text())
        study=self.kind.get_selected()==2
        selected_language=canonical_language(language)
        rows = [r for r in self.current_resources()
                                   if (study or not language or canonical_language(r.language) == selected_language)
                                   and (not query or query in (self._search_terms.get(r.id) or normalized(' '.join((r.name,r.description,r.language,self.language_label(r.language))))))]
        self._installed_ids=set(self.installed_ids())
        self.update_result_state(rows)
        if rows==self.filtered_resources:
            self.refresh_rows();self.selection_changed()
            return
        self.filtered_resources=rows
        self._rows_generation+=1;generation=self._rows_generation
        rows=self.filtered_resources;target=next((i for i,r in enumerate(rows) if r.id==selected_id),0)
        self._building_rows=True;self._pending_resource=rows[target] if rows else None
        self.choices.set_autoselect(False);self.choice_model.remove_all()
        offset=0
        def append_rows():
            nonlocal offset
            if self.closed or generation!=self._rows_generation:return False
            last=min(offset+16,len(rows))
            self.choice_model.splice(self.choice_model.get_n_items(),0,[ResourceItem(r) for r in rows[offset:last]])
            offset=last
            if self.choices.get_selected()==Gtk.INVALID_LIST_POSITION and target<offset:self.choices.set_selected(target)
            if offset<len(rows):return True
            self._building_rows=False;self._pending_resource=None;self.choices.set_autoselect(True)
            self.list_scroll.get_vadjustment().set_value(position);self.selection_changed()
            if not self._catalogue_requested and self.get_mapped():GLib.idle_add(self.auto_load)
            return False
        # Give GTK a frame between batches instead of filling its entire native
        # row cache before the first layout of a large multi-script catalogue.
        if append_rows():GLib.timeout_add(4,append_rows)
        self.selection_changed()

    def selected_resource(self):
        index = self.choices.get_selected()
        return self.filtered_resources[index] if index < len(self.filtered_resources) else self._pending_resource if self._building_rows else None

    def language_label(self,code):return self._language_records[code][0] if code in self._language_records else language_name(code)

    def installed_ids(self):return [*self._installed_metadata,*self._study_installed]

    def installed_resource(self,name):
        return self.study_resources.resource(name) if name in self.study_resources.stores else self._installed_metadata[name]

    def selection_changed(self, *_):
        resource = self.selected_resource()
        if resource and resource.id in self.installed_ids():
            resource=self.installed_resource(resource.id)
        self.metadata.set_text(details(resource) if resource else tr('No matching resource.'))
        self.refresh_controls()

    def refresh_controls(self):
        resource = self.selected_resource()
        installed=bool(resource and resource.id in self.installed_ids())
        current=installed and (resource.kind!='study' or resource.id in self._study_current)
        self.installed_state.set_visible(current)
        self.read_button.set_visible(current and resource.kind!='study')
        self.read_button.set_label(tr('Read') if resource and resource.kind=='bible' else tr('Open'))
        self.download_button.set_visible(not current)
        self.download_button.set_label(tr('Update') if installed and not current else
                                       tr('Retry') if resource and resource.id==self._failed_resource else tr('Download'))
        self.catalogue_button.set_sensitive(not self.busy)
        self.download_button.set_sensitive(bool(resource and resource.installable
                                               and not current)
                                           and not self._transfer_busy)
        # Browsing/back navigation stays available during a transfer. The
        # captured resource, not the current selection, owns that task.
        self.progress.set_visible(self._transfer_busy or self._phase=='error')
        self.cancel_button.set_visible(self._transfer_busy)
        self.cancel_button.set_sensitive(self._phase in ('downloading','preparing','converting','compiling','verifying'))
        self.refresh_rows()


    def on_close(self, *_):
        if self._transfer_busy and not self.owner.closed:
            self.set_visible(False)
            return True
        self.closed = True
        from .study_resources import STEP_RESOURCE_ID
        if self._task_resource==STEP_RESOURCE_ID or str(self._task_resource).startswith('youversion~'):self._cancel.set()
        if self._loading_tick:self.catalogue_progress.remove_tick_callback(self._loading_tick);self._loading_tick=0
        self._rows_generation+=1;self.language.cancel_pending();self.session.unsubscribe(self.snapshot_ready)
        self.stop_animation()
        self.executor.shutdown(wait=False, cancel_futures=True)
        return False

    def task(self, message, action, finished, success_text=None, resource=None):
        if self._transfer_busy:
            return
        self._transfer_busy = True
        self._cancel.clear();self._install_started=False;self._task_resource=resource.id if resource else None
        self._task_caption=plain(resource.description) if resource else ''
        self._task_id += 1
        self._phase = "downloading"
        self._indeterminate = True
        self.status.set_visible(True)
        self.progress.set_visible(True)
        self.status.set_text(tr(message))
        self.progress.set_fraction(0)
        self.progress.set_show_text(True)
        self.progress.set_text(tr(message))
        self._pulse_id = GLib.timeout_add(80, self.animate_progress)
        self.refresh_controls()
        future = self.executor.submit(action)

        def complete():
            if self.closed:
                return False
            self._transfer_busy = False
            self.stop_animation()
            try:
                value = future.result()
                finished(value)
                self._failed_resource=None
                self._phase = "complete"
                self.progress.set_fraction(1 if success_text else 0)
                self.progress.set_text(success_text or "")
            except Exception as error:
                self._phase = "error"
                self.progress.set_fraction(0)
                self.progress.set_text(tr("Failed"))
                self._failed_resource=resource.id if resource else None
                context=(resource.id+': ') if resource else ''
                self.status.set_text(f'{context}{error}\n{tr("Retry using the same button.")}')
                self.status.set_visible(True)
            finally:
                self.refresh_controls()
            return False

        future.add_done_callback(lambda _: GLib.idle_add(complete))

    def load_catalogue(self, *_, force=True):
        if self.closed or self.refreshing:return
        self._catalogue_requested=True
        self.refreshing=True
        self.refresh_status.set_visible(True)
        self.update_result_state()
        self.refresh_controls()
        index=self.source_filter.get_selected()
        providers=(PROVIDERS[index-1],) if 0<index<=len(PROVIDERS) else PROVIDERS
        self.session.refresh(catalogue,force,providers);self._refresh_generation=self.session.generation

    def stop_animation(self):
        if self._pulse_id:
            GLib.source_remove(self._pulse_id)
            self._pulse_id = 0
        with self._progress_lock:
            self._pending_progress = None

    def queue_progress(self, phase, done=0, total=0):
        # Worker threads only publish data. The GTK timeout coalesces updates
        # and animates while a network read or validation is waiting.
        with self._progress_lock:
            self._pending_progress = (self._task_id, phase, done, total)

    def animate_progress(self):
        if self.closed or not self._transfer_busy:
            self._pulse_id = 0
            return False
        with self._progress_lock:
            pending, self._pending_progress = self._pending_progress, None
        if pending and pending[0] == self._task_id:
            _, self._phase, done, total = pending
            self._indeterminate = self._phase in ('installing','preparing','compiling') or not total
            if self._phase == 'preparing':
                self.status.set_text(tr('Preparing study data…'));self.progress.set_text(tr('Preparing study data…'))
            elif self._phase in ('converting','compiling','verifying'):
                label=tr({'converting':'Converting the translation…','compiling':'Preparing the offline translation…',
                          'verifying':'Checking all chapters, introductions and translation notes…'}[self._phase])
                self.status.set_text(label)
                self.progress.set_fraction(min(done/total,1) if total else 0)
                self.progress.set_text(label+(f' {done}/{total}' if total else ''))
            elif self._phase == 'installing':
                self.status.set_text(tr('Installing {name} and checking…').format(name=self._task_caption) if self._task_caption else tr('Installing and checking…'))
                self.progress.set_fraction(0)
                self.progress.set_text(tr('Installing and checking…'))
            else:
                self.progress.set_fraction(min(done / total, 1) if total else 0)
                self.progress.set_text(f'{done / 1024:.1f} KiB' +
                                       (f' / {total / 1024:.1f} KiB ({min(done * 100 // total, 100)}%)'
                                        if total else ' — ' + tr('Size unknown')))
        if self._indeterminate:
            self.progress.pulse()
        self.cancel_button.set_sensitive(self._phase in ('downloading','preparing','converting','compiling','verifying'));self.refresh_rows()
        return True

    def report_progress(self, done, total):
        if self._cancel.is_set():raise OSError(tr('Download cancelled.'))
        self.queue_progress('downloading', done, total)

    def cancel_download(self,*_):
        from .study_resources import STEP_RESOURCE_ID
        with self._progress_lock:
            if not self._install_started or self._task_resource==STEP_RESOURCE_ID:self._cancel.set()
        self.cancel_button.set_sensitive(False)

    def begin_installation(self):
        from .study_resources import STEP_RESOURCE_ID
        with self._progress_lock:
            if self._cancel.is_set():raise OSError(tr('Download cancelled.'))
            self._install_started=True
            self._pending_progress=(self._task_id,'preparing' if self._task_resource==STEP_RESOURCE_ID else 'installing',0,0)

    def install(self, *_, resource=None, permission=None):
        resource = resource or self.selected_resource()
        if not resource or not resource.installable or self._transfer_busy or (resource.id in self.installed_ids() and (resource.kind!='study' or resource.id in self._study_current)):
            return

        if resource.provider_id=='youversion':
            from .youversion_install import acknowledgement
            if permission!=acknowledgement(resource):
                dialog=Adw.MessageDialog.new(self,tr('Download from Bible.com?'),
                    tr('You are responsible for checking that you have permission to download, convert and use this edition offline. The source requires an email agreement (version {version}). Satisfy this requirement with the provider before continuing. Bible does not submit an agreement or claim provider approval.').format(
                        version=json.loads(resource.acquisition).get('offline',{}).get('agreement_version','?')))
                dialog.add_response('cancel',tr('Cancel'));dialog.add_response('download',tr('I have the required permission'))
                dialog.set_close_response('cancel');dialog.set_default_response('cancel')
                dialog.connect('response',lambda _,response:self.install(resource=resource,permission=acknowledgement(resource)) if response=='download' else None)
                dialog.present();return
        caption=plain(resource.description) if resource.provider_id=='youversion' else resource.name

        def installed(_):
            self._completed_resource=resource.id
            self.preparing=True;self.session.reload_installed()
            self.on_installed(resource.id)
            self.filter_resources()
            self.status.set_text(tr('Installed: {name}').format(name=caption))
            self.selection_changed()
        installer=self.study_resources if resource.kind=='study' else self.library
        def perform():
            options={'cancelled':self._cancel.is_set} if resource.kind=='study' else {}
            if resource.provider_id=='youversion':
                options.update(cancelled=self._cancel.is_set,phase=self.queue_progress,permission=permission)
            return installer.install(resource,self.report_progress,installing=self.begin_installation,**options)
        self.task(tr('Downloading {name}…').format(name=caption),
                  perform,
                  installed, success_text=tr('Installed: {name}').format(name=caption),resource=resource)

