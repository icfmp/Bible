"""Catalogue/download UI kept separate from the reading surface."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from threading import Event
import json
import logging
import time
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, GLib, Gtk, Pango, Gio, GObject

from .i18n import tr, collation_key
from .library import catalogues as catalogue
from .providers import PROVIDERS,DEFAULT_PROVIDERS
from .book_names import normalized
from .resource_details import details, language_name, plain
from .language_picker import LanguagePicker
from .catalogue_session import CatalogueSession
from .languages import canonical_language, language_order


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
        from .application_surfaces import secondary_dialog
        secondary_dialog(self,parent)
        self._covered=frozenset();self._catalogued_ids=frozenset();self._removed_ids=frozenset();self._archived_ids=frozenset();self._catalogue_errors={};self._loading_tick=0
        from .study_resources import StudyResources
        self.study_resources=StudyResources(library.root.parent/'study-data')
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='bible-download')
        existing=getattr(parent,'catalogue_session',None)
        if not existing:parent.catalogue_session=CatalogueSession(library)
        self.session=parent.catalogue_session;self.cache=self.session.cache
        self.resources=[];self.preparing=True
        self._category=0;self._category_queries={}
        self._installed_metadata={};self._study_installed=frozenset();self._study_current=frozenset()
        self._language_records={};self._available_languages=frozenset();self._search_terms={};self._rows_generation=0;self._building_rows=False;self._refresh_generation=0
        self._pending_resource=None
        self._edition_details={}
        self._edition_requests={};self._study_requests={};self._review_downloads={};self._permission_dialog=None
        self._bound_rows={};self._task_resource=None;self._cancel=Event()
        self._install_started=False
        self.open_context=None
        self.settings=parent.application_settings
        self.language_choice=self.settings.language
        self.timings={}
        self._completed_resource=None
        self._failed_resource=None
        self._task_errors={};self._success_toast=None
        from .download_queue import DownloadQueue
        self.downloads=DownloadQueue(library.root.parent/'download-queue.json')
        self._queue_active=None;self._queue_tick=0;self._queue_revision=0;self._queue_problem=self.downloads.error
        for request in self.downloads.requests:
            if request.state=='failed':self._task_errors[request.resource.id]=(request.error,None)
        self.filtered_resources = []
        self.languages = []
        self.source_ids = [None] + [p.id for p in PROVIDERS]
        self._optional_requested=False
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
        actions=Gtk.MenuButton(icon_name='view-more-symbolic',tooltip_text=tr('Library actions'))
        actions.update_property([Gtk.AccessibleProperty.LABEL],[tr('Library actions')])
        menu=Gio.Menu();menu.append(tr('Check for module updates'),'catalogue.check-updates')
        group=Gio.SimpleActionGroup();check=Gio.SimpleAction.new('check-updates',None)
        check.connect('activate',lambda *_:self.modules.check());group.add_action(check)
        self._check_updates_action=check
        menu.append(tr('Update all verified modules'),'catalogue.update-all')
        update_all=Gio.SimpleAction.new('update-all',None)
        update_all.connect('activate',lambda *_:self.modules.update_all());group.add_action(update_all)
        self._update_all_action=update_all
        menu.append(tr('Installed module information'),'catalogue.module-info')
        information=Gio.SimpleAction.new('module-info',None)
        def module_info(*_):
            from .module_updates_window import ModuleUpdatesWindow
            ModuleUpdatesWindow(self,self.library).present()
        information.connect('activate',module_info);group.add_action(information);self.insert_action_group('catalogue',group)
        actions.set_menu_model(menu);header.pack_end(actions)
        layout.append(header)
        self.pages=Gtk.Stack(vexpand=True)
        explorer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10,margin_top=16)
        views=Gtk.Box(spacing=0,homogeneous=True,margin_start=12,margin_end=12);views.add_css_class('linked')
        self.bibles_button=Gtk.ToggleButton(label=tr('Bibles'),active=True)
        self.commentaries_button=Gtk.ToggleButton(label=tr('Commentaries'),group=self.bibles_button)
        self.study_tools_button=Gtk.ToggleButton(label=tr('Study tools'),group=self.bibles_button)
        self.category_buttons=(self.bibles_button,self.commentaries_button,self.study_tools_button)
        self.bibles_button.connect('toggled',lambda button:self.kind.set_selected(0) if button.get_active() else None)
        self.commentaries_button.connect('toggled',lambda button:self.kind.set_selected(1) if button.get_active() else None)
        self.study_tools_button.connect('toggled',lambda button:self.kind.set_selected(2) if button.get_active() else None)
        for button in self.category_buttons:
            text=button.get_label()
            button.set_child(Gtk.Label(label=text,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1))
            button.update_property([Gtk.AccessibleProperty.LABEL],[text])
            views.append(button)
        explorer.append(views)
        self.type_tabs=views
        self.search=Gtk.SearchEntry(placeholder_text=tr('Search resources'),margin_start=12,margin_end=12)
        self.search.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search resources')])
        self.search.connect('search-changed',self.filter_resources);explorer.append(self.search)
        filters=Gtk.Box(spacing=8,margin_start=12,margin_end=12)
        self.kind=Gtk.DropDown(model=Gtk.StringList.new([tr('Bibles'),tr('Commentaries'),tr('Study tools')]))
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
        self.result_pages=Gtk.Stack(vexpand=True,hhomogeneous=False,vhomogeneous=False)
        self.result_pages.add_named(self.list_scroll,'rows')
        self.skeleton=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14,margin_start=20,margin_end=20,margin_top=20)
        self.loading_phase=Gtk.Label(wrap=True,xalign=0,max_width_chars=40)
        self.skeleton.append(self.loading_phase)
        from .loading_cards import placeholder
        for i in range(5):
            row=Gtk.Box(spacing=12)
            icon=Gtk.DrawingArea(width_request=34,height_request=38)
            icon.set_draw_func(placeholder);row.append(icon)
            lines=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,hexpand=True)
            for width in (150,220):
                line=Gtk.DrawingArea(height_request=12,width_request=width,halign=Gtk.Align.START)
                line.set_draw_func(placeholder);lines.append(line)
            row.append(lines);self.skeleton.append(row)
        self.skeleton.set_can_target(False)
        self.result_pages.add_named(self.skeleton,'loading')
        self.empty_page=Adw.StatusPage(icon_name='edit-find-symbolic')
        empty_actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,halign=Gtk.Align.CENTER)
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
        # One scrollable native detail hierarchy for every module kind.
        detail_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14,
                       margin_start=16,margin_end=16,margin_top=16,margin_bottom=18)
        detail_scroll.set_child(detail)
        identity=Gtk.Box(spacing=12)
        identity.append(Gtk.Image(icon_name='text-x-generic-symbolic',pixel_size=32,
                                  valign=Gtk.Align.START))
        identity_text=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,hexpand=True)
        self.detail_title=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
        self.detail_title.add_css_class('title-2');identity_text.append(self.detail_title)
        self.detail_subtitle=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
        self.detail_subtitle.add_css_class('dim-label');identity_text.append(self.detail_subtitle)
        identity.append(identity_text);detail.append(identity)
        self.installed_state=Gtk.Box(spacing=6,halign=Gtk.Align.START,visible=False)
        self.installed_state.append(Gtk.Image(icon_name='object-select-symbolic'))
        self.installed_label=Gtk.Label(label=tr('Installed — available offline'),wrap=True)
        self.installed_state.append(self.installed_label)
        detail.append(self.installed_state)
        self.primary_actions=Gtk.Box(spacing=8,orientation=Gtk.Orientation.HORIZONTAL)
        self.read_button=Gtk.Button(label=tr('Read'),visible=False)
        self.read_button.add_css_class('suggested-action')
        self.read_button.connect('clicked',lambda *_:self.read_resource(self.selected_resource()))
        self.primary_actions.append(self.read_button)
        self.download_button=Gtk.Button(label=tr('Download'),sensitive=False)
        self.download_button.add_css_class('suggested-action')
        self.download_button.connect('clicked',self.download_action)
        self.primary_actions.append(self.download_button);detail.append(self.primary_actions)

        self.description_group=Adw.PreferencesGroup(title=tr('Description'),
            description=tr('Description and notices supplied by the source.'))
        self.about_text=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,
                                  selectable=True,width_chars=1)
        self.description_group.add(self.about_text);detail.append(self.description_group)
        self.information=Adw.PreferencesGroup(title=tr('Resource information'))
        self.detail_rows={}
        for key,label in (('type','Resource type'),('language','Language'),
                          ('author','Author'),('version','Version'),
                          ('numbering','Verse numbering')):
            row=Adw.ActionRow(title=tr(label),use_markup=False)
            self.information.add(row);self.detail_rows[key]=row
        detail.append(self.information)
        self.source_group=Adw.PreferencesGroup(title=tr('Source and attribution'))
        self.source_row=Adw.ActionRow(title=tr('Source'),use_markup=False)
        self.source_group.add(self.source_row)
        self.text_source_row=Adw.ActionRow(title=tr('Text source'),use_markup=False)
        self.source_group.add(self.text_source_row);detail.append(self.source_group)
        self._source_link=None;self._license_link=None;self._text_source_link=None
        self.license_group=Adw.PreferencesGroup(title=tr('License and conditions of use'))
        license_row=Adw.ActionRow(title=tr('License'),use_markup=False)
        self.detail_rows['license']=license_row;self.license_group.add(license_row)
        self.conditions_text=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,
                                       selectable=True,width_chars=1,margin_top=8)
        self.license_group.add(self.conditions_text);detail.append(self.license_group)
        self.technical=Adw.ExpanderRow(title=tr('Technical details'))
        self.metadata=MetadataLabel(xalign=0,yalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,
                                    selectable=True,width_chars=1)
        self.metadata.set_margin_top(8);self.metadata.set_margin_bottom(8)
        self.metadata.set_margin_start(12);self.metadata.set_margin_end(12)
        self.technical.add_row(self.metadata)
        technical_group=Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE);technical_group.add_css_class('boxed-list')
        technical_group.append(self.technical);detail.append(technical_group)
        self.module_actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        from .module_management import ModuleManagement
        self.modules=ModuleManagement(self,self.module_actions,primary=self.primary_actions)
        self.remove_hint=Gtk.Label(label=tr('Personal notes and highlights are retained when removing a resource.'),
                                   xalign=0,wrap=True,visible=False)
        self.remove_hint.add_css_class('caption');self.remove_hint.add_css_class('dim-label')
        self.module_actions.append(self.remove_hint);detail.append(self.module_actions)
        narrow_detail=Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 440px'))
        narrow_detail.add_setter(self.primary_actions,'orientation',Gtk.Orientation.VERTICAL)
        self.add_breakpoint(narrow_detail)
        self.pages.add_named(detail_scroll,'detail');layout.append(self.pages)
        self.transfer_footer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,visible=False)
        self.transfer_footer.append(Gtk.Separator())
        transfer=Gtk.Box(spacing=12,margin_start=16,margin_end=16,margin_top=12,margin_bottom=16)
        information=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6,hexpand=True)
        self.transfer_phase=Gtk.Label(label=tr('Downloading'),xalign=0,wrap=True,width_chars=1)
        self.transfer_phase.add_css_class('caption');information.append(self.transfer_phase)
        self.transfer_name=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
        self.transfer_name.add_css_class('heading');information.append(self.transfer_name)
        self.queue_count=Gtk.Label(xalign=0,wrap=True,visible=False);self.queue_count.add_css_class('caption');information.append(self.queue_count)
        meter=Gtk.Box(spacing=8)
        self.progress=Gtk.ProgressBar(hexpand=True,valign=Gtk.Align.CENTER,visible=False)
        self.transfer_percent=Gtk.Label();self.transfer_percent.add_css_class('caption')
        meter.append(self.progress);meter.append(self.transfer_percent);information.append(meter);transfer.append(information)
        self.cancel_button=Gtk.Button(child=Gtk.Label(label=tr('Cancel'),wrap=True),valign=Gtk.Align.CENTER,visible=False)
        self.cancel_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Cancel download')])
        self.cancel_button.connect('clicked',self.cancel_download);transfer.append(self.cancel_button)
        self.resume_downloads=Gtk.Button(label=tr('Resume'),valign=Gtk.Align.CENTER,visible=False)
        self.resume_downloads.set_tooltip_text(tr('Resume queued downloads'))
        self.resume_downloads.connect('clicked',self.resume_queue);transfer.append(self.resume_downloads)
        self.transfer_footer.append(transfer);layout.append(self.transfer_footer)
        self.status=Gtk.Label(xalign=0,wrap=True,selectable=True,margin_start=12,margin_end=12,margin_bottom=12,visible=False)
        layout.append(self.status)
        self.refresh_status=Gtk.Label(xalign=0,wrap=True,margin_start=12,margin_end=12,margin_bottom=8)
        self.refresh_status.add_css_class('dim-label');layout.append(self.refresh_status)
        if self.resources:self.refresh_status.set_text(tr('Saved catalogue — available offline.'))
        self.toast_overlay=Adw.ToastOverlay();self.toast_overlay.set_child(layout)
        self.set_content(self.toast_overlay)
        self._catalogue_requested=False
        self.update_languages()
        self.refresh_status.set_text(tr('Loading saved resources…'))
        self.session.subscribe(self.snapshot_ready)
        if existing and self.session.bootstrap_future.done():self.session.reload_installed()
        self.connect('map',lambda *_:GLib.timeout_add(100,self.auto_load))
        if self._queue_problem:self.queue_error(self._queue_problem)

    @property
    def busy(self):return self._transfer_busy or self.refreshing or self.preparing or self._building_rows

    def adopt_owner(self,parent):
        previous=self.owner
        if previous is parent:return
        if previous.catalogue_window is self:previous.catalogue_window=None
        if getattr(previous,'catalogue_session',None) is self.session:previous.catalogue_session=None
        other=getattr(parent,'catalogue_session',None)
        if other and other is not self.session:other.close()
        self.remove_css_class(previous.reading_style.scope+'-window')
        self.add_css_class(parent.reading_style.scope+'-window')
        self.owner=parent;self.on_installed=parent.resource_installed
        parent.catalogue_window=self;parent.catalogue_session=self.session
        self.set_transient_for(parent)

    def snapshot_ready(self,snapshot):
        # The service publishes plain immutable snapshots from metadata workers.
        GLib.idle_add(self.apply_snapshot,snapshot)

    def apply_snapshot(self,snapshot):
        if self.closed or snapshot.generation<self._refresh_generation:return False
        changed=(self.resources!=list(snapshot.resources) or self._installed_metadata!=snapshot.installed
                 or self._study_installed!=snapshot.study_installed or self._study_current!=snapshot.study_current
                 or self._language_records!=snapshot.languages or self._archived_ids!=snapshot.archived_resources
                 or self._available_languages!=snapshot.available_languages
                 or getattr(self,'_candidate_languages',())!=snapshot.candidate_languages)
        self._covered=snapshot.covered_providers;self._catalogue_errors=snapshot.errors
        self.preparing=False;self.resources=list(snapshot.resources)
        self._catalogued_ids=frozenset(r.id for r in snapshot.resources)
        self._removed_ids=snapshot.removed_resources
        self._archived_ids=snapshot.archived_resources
        self._installed_metadata=snapshot.installed;self._study_installed=snapshot.study_installed
        self._study_current=snapshot.study_current;self._language_records=snapshot.languages
        self._available_languages=snapshot.available_languages
        self._candidate_languages=snapshot.candidate_languages
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
        providers=self.selected_providers()
        complete=study or all(p.id in self._covered for p in providers)
        selected_language=self.language.codes[self.language.get_selected()]
        candidate=canonical_language(selected_language) in {canonical_language(code) for code in getattr(self,'_candidate_languages',())}
        if candidate and not study:complete=False
        names={p.name for p in providers}
        all_names={p.name for p in PROVIDERS}
        errors=({name:error for name,error in self._catalogue_errors.items() if name=='Study tools'} if study else
                {name:error for name,error in self._catalogue_errors.items() if name!='Study tools' and (not index or name in names or name not in all_names)})
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
            if language and not study:description+=' '+tr('Language')+': '+self.language_label(language)
            if self.search.get_text():description+=' '+tr('Search')+': '+self.search.get_text()
            if index and not study:description+=' '+tr('Source')+': '+providers[0].name
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
        installed=resource.id in getattr(self,'_installed_ids',set())
        current=installed and (resource.kind!='study' or resource.id in self._study_current)
        archived=self.queued_unavailable(resource) and not installed
        busy=self._transfer_busy and self._task_resource==resource.id
        request=self.downloads.find(resource.id)
        queued=request is not None and request.state in ('queued','paused')
        checking=self.checking_download(resource.id)
        stamp=(resource,installed,current,archived,checking,self._queue_revision,self.modules.revision,self._transfer_busy,self._phase if busy else None,
               self.progress.get_text() if busy else None,resource.id in self._task_errors)
        if getattr(item,'_render_stamp',None)==stamp:return
        item._render_stamp=stamp
        item.title.set_text(plain(resource.description))
        item.subtitle.set_text(self.language_label(resource.language)+' — '+resource.source)
        active_label=tr({'preparing':'Preparing','converting':'Converting','compiling':'Converting',
                         'verifying':'Checking','installing':'Installing'}.get(self._phase,'Downloading'))
        item.state.set_text(active_label if busy else tr('Checking resource information…') if checking else tr('Paused') if queued and request.state=='paused' else tr('Queued') if queued else tr('Failed') if resource.id in self._task_errors else tr('Archived') if archived else tr('Update available') if self.modules.available(resource.id) else tr('Installed') if current else tr('Update available') if installed else '')
        item.state.set_visible(busy or installed or archived or queued or checking or resource.id in self._task_errors)
        dismiss=bool(request and request.state=='failed' and archived)
        item.action.set_icon_name('process-stop-symbolic' if queued or checking or dismiss else 'media-playback-start-symbolic' if installed and resource.kind!='study' else 'folder-download-symbolic')
        label=tr('Dismiss failed download') if dismiss else tr('Cancel queued download') if queued or checking else tr('Read') if installed and resource.kind=='bible' else tr('Update') if installed and not current else tr('Open') if installed else tr('Retry') if resource.id in self._task_errors else tr('Download')
        item.action.set_tooltip_text(label+' — '+plain(resource.description))
        item.action.update_property([Gtk.AccessibleProperty.LABEL],[label+' — '+plain(resource.description)])
        item.action.set_sensitive(current or queued or dismiss or (resource.installable and not archived))
        item.action.set_visible(not busy and (queued or checking or not (current and resource.kind not in ('bible','commentary'))))
        item.get_child().set_tooltip_text(resource.name+' · '+(getattr(resource,'version','') or '—')+' · '+resource.language)

    def refresh_rows(self):
        for item in list(self._bound_rows):
            if item.get_item():self.bind_resource_row(None,item)

    def row_action(self,resource):
        if self.cancel_queued(resource.id):return
        if resource.id in self.installed_ids() and (resource.kind!='study' or resource.id in self._study_current):self.read_resource(resource)
        else:self.install(resource=resource)

    def download_action(self,*_):
        resource=self.selected_resource()
        if resource and not self.cancel_queued(resource.id):self.install(resource=resource)

    def cancel_queued(self,identifier):
        if identifier in self._study_requests:
            self._study_requests.pop(identifier).cancel();self.queue_changed();return True
        metadata=self._edition_requests.get(identifier)
        if metadata and metadata[1]:metadata[1]=None;self.queue_changed();return True
        if identifier in self._review_downloads:
            self._review_downloads.pop(identifier);self.queue_changed();return True
        request=self.downloads.find(identifier)
        if request is None or (request.state not in ('queued','paused') and not (request.state=='failed' and self.queued_unavailable(request.resource))):return False
        dismissed=request.state=='failed'
        try:self.downloads.cancel(identifier)
        except (OSError,ValueError) as error:self.queue_error(error);return True
        if dismissed:self._task_errors.pop(identifier,None)
        self.queue_changed();return True

    def checking_download(self,identifier):
        metadata=self._edition_requests.get(identifier)
        return identifier in self._study_requests or bool(metadata and metadata[1]) or identifier in self._review_downloads

    def queued_unavailable(self,resource):
        return resource.id in self._archived_ids or (resource.provider_id!='youversion' and resource.provider_id in self._covered
            and resource.id not in self._catalogued_ids and resource.id not in self._installed_metadata)

    def queue_error(self,error):
        self._queue_problem=str(error)
        self.status.set_text(tr('The download queue is unavailable. Existing resources were preserved.')+' '+str(error))
        self.status.set_visible(True)

    def queue_changed(self):
        self._queue_revision+=1
        self.filter_resources();self.refresh_controls()

    def queue_request(self,resource,permission=None,operation='install'):
        from .download_queue import QueueConflict
        try:self.downloads.enqueue(resource,permission,operation)
        except QueueConflict as error:
            self.status.set_text(tr(str(error)));self.status.set_visible(True);return
        except (OSError,ValueError) as error:self.queue_error(error);return
        self._queue_problem=None;self.queue_changed()

    def resume_queue(self,*_):
        try:self.downloads.resume()
        except (OSError,ValueError) as error:self.queue_error(error);return
        self._queue_problem=None;self.queue_changed()

    def start_queued(self):
        self._queue_tick=0
        if self.closed or self.owner.closed or self._transfer_busy or self._queue_active or self._queue_problem:return False
        try:request=self.downloads.start()
        except (OSError,ValueError) as error:self.queue_error(error);return False
        if request is None:return False
        self._queue_active=request
        try:
            if self.queued_unavailable(request.resource):raise ValueError(tr('This queued resource is no longer available from its source.'))
            if request.operation=='update':
                actual=self.library.resource(request.resource.id)
                if actual.version!=request.resource.version or actual.acquisition!=request.resource.acquisition:
                    self.modules.run('update',resource=request.resource,queued=True)
            else:self.install(resource=request.resource,permission=request.permission,queued=True)
            if not self._transfer_busy:
                # A source already installed after an interrupted commit is
                # discovered normally; never start a duplicate installation.
                actual=self.installed_resource(request.resource.id)
                expected=request.resource
                matches=(actual.revision==expected.revision if expected.kind=='study'
                         else actual.version==expected.version and actual.acquisition==expected.acquisition)
                if not matches:raise ValueError(tr('The queued operation could not start. Review this resource.'))
                self.downloads.finish(request);self._queue_active=None;self.queue_changed()
        except Exception as error:
            self._queue_active=None
            try:self.downloads.fail(request,error)
            except (OSError,ValueError) as failure:self.queue_error(failure)
            self._task_errors[request.resource.id]=(str(error),None);self.queue_changed()
        return False

    def read_resource(self,resource):
        if not resource or resource.id not in self.installed_ids():return
        try:
            if self.owner.open_installed_resource(resource.id,self.open_context):self.close();return
            message=tr('This reading tab is no longer available. Open Library again from the intended tab.')
        except (OSError,ValueError) as error:message=str(error)
        self.status.set_text(message);self.status.set_visible(True)

    def open_details(self,_,index):
        self.dismiss_success_toast()
        self._list_position=self.list_scroll.get_vadjustment().get_value()
        self.choices.set_selected(index);self.selection_changed()
        self.pages.set_visible_child_name('detail');self.back_button.set_visible(True)
        self.metadata.select_region(0, 0)
        self.back_button.grab_focus()
        resource=self.selected_resource()
        if resource and resource.provider_id=='youversion' and json.loads(resource.acquisition).get('_catalogue_summary'):
            self.load_edition_details(resource)

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
        self.dismiss_success_toast()
        self.pages.set_visible_child_name('list');self.back_button.set_visible(False)
        self.list_scroll.get_vadjustment().set_value(getattr(self,'_list_position',0))

    def current_resources(self):
        queued={r.resource.id:r.resource for r in self.downloads.requests if r.resource.kind!='study'}
        if self.kind.get_selected()==2:
            # Installed native dictionaries/lexicons share lifecycle controls.
            # Discovering new dictionary catalogues remains the separate #236.
            native={r.id:r for r in self.resources if r.id in self._removed_ids};native.update(queued);native.update(self._installed_metadata)
            return (*self.study_resources.available(),*(r for r in native.values()
                       if r.kind not in ('bible','commentary')))
        resources=dict(queued);resources.update((r.id,r) for r in self.resources);resources.update(self._installed_metadata)
        kind = 'commentary' if self.kind.get_selected() == 1 else 'bible'
        index = self.source_filter.get_selected()
        provider_id = self.source_ids[index] if index < len(self.source_ids) else None
        return [resource for resource in resources.values() if resource.kind == kind
                and (provider_id is None or resource.provider_id == provider_id)]

    def update_languages(self, *_):
        study=self.kind.get_selected()==2
        category=self.kind.get_selected()
        if category!=self._category:
            self.dismiss_success_toast()
            self._category_queries[self._category]=self.search.get_text()
            self._category=category
            self._filtering=True
            self.search.set_text(self._category_queries.get(category,''))
            self._filtering=False
        self.category_buttons[category].set_active(True)
        wording=tr('Search resources') if study else tr('Search commentaries') if self.kind.get_selected()==1 else tr('Search Bibles')
        self.search.set_placeholder_text(wording);self.search.update_property([Gtk.AccessibleProperty.LABEL],[wording])
        self.language.set_visible(not study);self.source_filter.set_visible(not study)
        self._filtering=True
        known={canonical_language(r.language) for r in self.current_resources() if not self.queued_unavailable(r)}
        source=self.source_filter.get_selected()
        candidates=(getattr(self,'_candidate_languages',()) if not category and
                    (not source or self.source_ids[source]=='youversion') else ())
        codes=known|{canonical_language(code) for code in candidates}
        self.languages,priority=language_order(codes,known,self.language_label)
        self.language.set_codes(self.languages,self._language_records,priority=priority)
        self.language.set_selected(self.languages.index(canonical_language(self.language_choice)) if canonical_language(self.language_choice) in self.languages else 0)
        self._filtering=False
        self.filter_resources()
        self.request_youversion_language()
        if not self.busy and not self.resources and self.get_mapped():
            GLib.idle_add(self.auto_load)
        # Choosing the optional source is an explicit catalogue request. The
        # existing global network preference still wins; Refresh stays manual
        # when automatic catalogue metadata refresh is disabled.
        chosen=self.source_filter.get_selected()
        if (self.get_mapped() and chosen<len(self.source_ids) and self.source_ids[chosen]=='bible-resources'
                and 'bible-resources' not in self._covered and not self.refreshing and not self._optional_requested
                and self.settings.value['automatic_catalogue_refresh']):
            self._optional_requested=True;self.load_catalogue(force=False)

    def language_changed(self):
        if self._filtering:return
        self.language_choice=self.language.codes[self.language.get_selected()]
        try:self.settings.set('library_language',self.language_choice)
        except (OSError,ValueError) as error:self.status.set_text(str(error));self.status.set_visible(True)
        self.filter_resources()
        self.request_youversion_language()

    def request_youversion_language(self,force=False):
        if self.closed or not self.get_mapped() or self.kind.get_selected()!=0:return
        if not self._catalogue_requested and not force:return
        if not force and not self.settings.value['automatic_catalogue_refresh']:return
        index=self.source_filter.get_selected()
        if index and self.source_ids[index]!='youversion':return
        choice=self.language.codes[self.language.get_selected()]
        self.session.load_youversion_language(choice,force)

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
        rows.sort(key=lambda r:(r.id not in self._installed_ids,
                               collation_key(plain(r.description)),r.provider_id,r.id))
        self.update_result_state(rows)
        # Installed attribution can replace catalogue summaries without changing
        # row identity/order. Keep GtkListView's native visible-item anchor and
        # selection; clearing the model collapses its adjustment before layout.
        if [r.id for r in rows]==[r.id for r in self.filtered_resources]:
            self.filtered_resources[:]=rows
            for index in range(self.choice_model.get_n_items()):
                self.choice_model.get_item(index).resource=rows[index]
            self.refresh_rows();self.selection_changed()
            return
        if (not self._building_rows and len(rows)==len(self.filtered_resources)
                and {r.id for r in rows}=={r.id for r in self.filtered_resources}):
            # Native sorting retains the existing GObjects and their list-row
            # anchors. Installation changes the group, not resource identity.
            order={resource.id:index for index,resource in enumerate(rows)}
            resources={resource.id:resource for resource in rows}
            self.filtered_resources=rows
            for index in range(self.choice_model.get_n_items()):
                item=self.choice_model.get_item(index);item.resource=resources[item.resource.id]
            self.choice_model.sort(lambda a,b:order[a.resource.id]-order[b.resource.id])
            if selected_id in order:self.choices.set_selected(order[selected_id])
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
        resource=self.filtered_resources[index] if index < len(self.filtered_resources) else self._pending_resource if self._building_rows else None
        return self.known_edition_details(resource)

    def known_edition_details(self,resource):
        if resource:
            cached=self._edition_details.get(resource.id)
            if cached and cached[0]==resource.acquisition and time.monotonic()-cached[2]<900:return cached[1]
        return resource

    def load_edition_details(self,resource,finished=None):
        from .youversion_install import fetch_resource
        from .youversion_editions import edition_id
        if resource.id in self._edition_requests:
            if finished:self._edition_requests[resource.id][1]=finished;self.refresh_rows();self.refresh_controls()
            return
        future=self.session.network.submit(fetch_resource,edition_id(resource.name))
        request=[future,finished];self._edition_requests[resource.id]=request
        self.refresh_rows();self.refresh_controls()
        def complete():
            self._edition_requests.pop(resource.id,None)
            if self.closed:return False
            try:
                actual=future.result()
                if actual.language!=resource.language:raise ValueError('Source edition language changed')
                self._edition_details[resource.id]=(resource.acquisition,actual,time.monotonic())
                selected=self.selected_resource()
                if selected and selected.id==resource.id:self.selection_changed()
                if request[1]:
                    self._review_downloads[resource.id]=(actual,request[1]);self.review_downloads()
            except Exception as error:
                self._failed_resource=resource.id
                if not self._transfer_busy:self._phase='error'
                self._task_errors[resource.id]=(str(error),None);self.status.set_text(plain(resource.description)+': '+str(error));self.status.set_visible(True)
            self.refresh_rows();return False
        future.add_done_callback(lambda _:GLib.idle_add(complete))

    def review_downloads(self):
        if self.closed or not self.get_visible() or self._permission_dialog or not self._review_downloads:return
        identifier=next(iter(self._review_downloads));resource,callback=self._review_downloads.pop(identifier)
        callback(resource)
        return False

    def prepare_study_download(self,resource):
        # Pin the existing provider's current checked metadata before queuing.
        # The installer checks that same revision again before fetching bytes.
        if resource.id in self._study_requests:return
        def check():
            try:self.study_resources.catalogue.refresh()
            except OSError:self.study_resources.catalogue.load()
            return self.study_resources.resource(resource.id)
        future=self.session.network.submit(check);self._study_requests[resource.id]=future
        self.refresh_rows();self.refresh_controls()
        def complete():
            if self._study_requests.get(resource.id) is not future:return False
            self._study_requests.pop(resource.id,None)
            if self.closed:return False
            try:self.queue_request(future.result())
            except Exception as error:
                self._task_errors[resource.id]=(str(error),None);self.status.set_text(str(error));self.status.set_visible(True)
            self.refresh_rows();return False
        future.add_done_callback(lambda _:GLib.idle_add(complete))

    def language_label(self,code):return self._language_records[code][0] if code in self._language_records else language_name(code)

    def installed_ids(self):return [*self._installed_metadata,*self._study_installed]

    def installed_resource(self,name):
        return self.study_resources.installed_resource(name) if name in self.study_resources.stores else self._installed_metadata[name]

    def selection_changed(self, *_):
        resource = self.selected_resource()
        if resource and resource.id in self.installed_ids():
            resource=self.installed_resource(resource.id)
        text=details(resource) if resource else tr('No matching resource.')
        notes=self.modules.version_notes(resource)
        self.metadata.set_text(text+('\n\n'+notes if notes else ''))
        failure=self._task_errors.get(resource.id) if resource else None
        if failure:self.status.set_text(failure[0]);self.status.set_tooltip_text(failure[1]);self.status.set_visible(True)
        elif not self._transfer_busy and not self._queue_problem:self.status.set_visible(False)
        self.detail_title.set_text(plain(resource.description) if resource else tr('No matching resource.'))
        self.detail_subtitle.set_text((resource.source+' · '+self.language_label(resource.language)) if resource else '')
        values=({
            'type':tr({'commentary':'Commentaries','study':'Study resources',
                       'dictionary':'Dictionary or lexicon','general':'General book'}.get(resource.kind,'Bibles')),
            'language':language_name(resource.language),
            'author':plain(resource.author),
            'version':getattr(resource,'version',''),
            'license':plain(resource.license),
            'numbering':resource.versification if resource.kind in ('bible','commentary','study') else '',
        } if resource else {})
        for key,row in self.detail_rows.items():
            value=values.get(key,'')
            row.set_visible(bool(value));row.set_subtitle(value)
        self.source_group.set_visible(bool(resource))
        self.source_row.set_subtitle(resource.source if resource else '')
        from .resource_details import linkable_url, first_link, visible_conditions
        self._detail_link(self.source_row,'_source_link',
                          linkable_url(resource.source_url) if resource else '',tr('Open source'))
        text_source=linkable_url(getattr(resource,'text_source','')) if resource else ''
        self.text_source_row.set_visible(bool(text_source))
        self._detail_link(self.text_source_row,'_text_source_link',text_source,tr('Open source'))
        self._detail_link(self.detail_rows['license'],'_license_link',
                          first_link(resource.license) if resource else '',tr('License details'))
        # Do not present pending catalogue summaries as confirmed source terms.
        pending=False
        if resource and resource.provider_id=='youversion':
            try:pending=bool(json.loads(resource.acquisition).get('_catalogue_summary'))
            except (ValueError,TypeError,AttributeError):pass
        conditions=(tr('Loading edition details…') if pending else visible_conditions(resource)) if resource else ''
        self.conditions_text.set_text(conditions);self.conditions_text.set_visible(bool(conditions))
        self.license_group.set_visible(bool(resource and (resource.license or conditions)))
        # About is a source-owned mixed field, not reliably separable prose and
        # legal metadata. Present every word, including editorial limitations,
        # as first-class description/notices rather than guessing boundaries.
        # Study About carries index/checksum metadata and stays in disclosure.
        about=plain(resource.about) if resource and resource.kind!='study' and not pending else ''
        self.about_text.set_text(about);self.about_text.set_visible(bool(about))
        self.description_group.set_visible(bool(about))
        self.refresh_controls()

    def _detail_link(self,row,attribute,url,label):
        previous=getattr(self,attribute)
        if previous:
            row.remove(previous);setattr(self,attribute,None)
        if url:
            link=Gtk.LinkButton(uri=url,label=label)
            row.add_suffix(link);setattr(self,attribute,link)

    def refresh_controls(self):
        resource = self.selected_resource()
        request=self.downloads.find(resource.id) if resource else None
        queued=request is not None and request.state in ('queued','paused')
        checking=bool(resource and self.checking_download(resource.id))
        dismiss=bool(resource and request and request.state=='failed' and self.queued_unavailable(resource))
        installed=bool(resource and resource.id in self.installed_ids())
        version=getattr(resource,'version','')
        self.installed_label.set_text(tr('Installed — available offline')+(' · '+version if installed and version else ''))
        if resource:self.detail_rows['version'].set_visible(bool(version) and not installed)
        current=installed and (resource.kind!='study' or resource.id in self._study_current)
        self.installed_state.set_visible(installed)
        self.read_button.set_visible(current and resource.kind in ('bible','commentary'))
        self.read_button.set_label(tr('Read') if resource and resource.kind=='bible' else tr('Open'))
        self.download_button.set_visible(not current or queued or checking)
        self.download_button.set_label(tr('Dismiss failed download') if dismiss else tr('Cancel queued download') if queued or checking else tr('Update') if installed and not current else
                                       tr('Archived') if resource and resource.id in self._archived_ids else
                                       tr('Retry') if resource and resource.id in self._task_errors else tr('Download'))
        self.download_button.set_tooltip_text(tr('Refresh this source to verify whether this removed version is still available.')
                                             if resource and resource.id in self._archived_ids else None)
        self.catalogue_button.set_sensitive(not self.busy)
        self.download_button.set_sensitive(queued or checking or dismiss or bool(resource and resource.installable
                                               and not current and resource.id not in self._archived_ids
                                               and not (request and request.state=='active')))
        # Browsing/back navigation stays available during a transfer. The
        # captured resource, not the current selection, owns that task.
        pending=sum(r.state in ('queued','paused') for r in self.downloads.requests)
        paused=sum(r.state=='paused' for r in self.downloads.requests)
        self.queue_count.set_text(tr('{count} paused').format(count=paused) if paused else tr('{count} queued').format(count=pending))
        self.queue_count.set_visible(bool(pending))
        self.resume_downloads.set_visible(bool(paused) and not self._transfer_busy)
        if not self._transfer_busy and pending:
            self.transfer_name.set_text('');self.transfer_phase.set_text(tr('Downloads paused after restart') if paused else tr('Queued'))
        self.transfer_footer.set_visible(self._transfer_busy or bool(pending))
        self.progress.set_visible(self._transfer_busy)
        self.cancel_button.set_visible(self._transfer_busy)
        self.cancel_button.set_sensitive(self._phase in ('downloading','preparing','converting','compiling','verifying'))
        self.modules.refresh(resource)
        self.remove_hint.set_visible(False)
        if (not self.closed and not self.owner.closed and not self._transfer_busy and not self._queue_active
                and not self._queue_tick and not self._queue_problem and any(r.state=='queued' for r in self.downloads.requests)):
            self._queue_tick=GLib.idle_add(self.start_queued)
        self._check_updates_action.set_enabled(not self.busy)
        self._update_all_action.set_enabled(not self.busy and any(self.modules.available(i) for i in self._installed_metadata))
        self.refresh_rows()


    def on_close(self, *_):
        self.dismiss_success_toast()
        if (self._transfer_busy or self._review_downloads or self._study_requests or any(r[1] for r in self._edition_requests.values())) and not self.owner.closed:
            self.set_visible(False)
            return True
        self.closed = True
        if self._permission_dialog:self._permission_dialog.destroy();self._permission_dialog=None
        if self._queue_tick:GLib.source_remove(self._queue_tick);self._queue_tick=0
        try:self.downloads.pause()
        except (OSError,ValueError) as error:logging.getLogger(__name__).warning('Could not persist download queue: %s',error)
        self._cancel.set()
        from .study_resources import STEP_RESOURCE_ID
        if self._task_resource==STEP_RESOURCE_ID or str(self._task_resource).startswith('youversion~'):self._cancel.set()
        if self._loading_tick:self.catalogue_progress.remove_tick_callback(self._loading_tick);self._loading_tick=0
        self._rows_generation+=1;self.language.cancel_pending();self.session.unsubscribe(self.snapshot_ready)
        self.stop_animation()
        self.executor.shutdown(wait=False, cancel_futures=True)
        return False

    def dismiss_success_toast(self):
        if self._success_toast:self._success_toast.dismiss();self._success_toast=None

    def task(self, message, action, finished, success_text=None, resource=None,executor=None,settled=None,failed=None):
        if self._transfer_busy:
            return
        self.dismiss_success_toast()
        self._transfer_busy = True
        self._cancel.clear();self._install_started=False;self._task_resource=resource.id if resource else None
        self._task_caption=plain(resource.description) if resource else ''
        self._task_id += 1;task_id=self._task_id
        queued_request=self._queue_active if self._queue_active and resource and self._queue_active.resource.id==resource.id else None
        self._phase = "downloading"
        self._indeterminate = True
        self.status.set_visible(False)
        self.progress.set_visible(True)
        self.status.set_text(tr(message));self.status.set_tooltip_text(None)
        self.progress.set_fraction(0)
        self.progress.set_show_text(False)
        self.transfer_name.set_text(self._task_caption)
        self.transfer_phase.set_text(tr(message) if not resource else tr('Downloading'))
        self.transfer_percent.set_text('');self.transfer_percent.set_visible(False)
        self.progress.set_text(tr(message))
        self._pulse_id = GLib.timeout_add(80, self.animate_progress)
        self.refresh_controls()
        future = (executor or self.executor).submit(action)

        def complete():
            if self.closed or task_id!=self._task_id:
                if settled:settled()
                return False
            self._transfer_busy = False
            self.stop_animation()
            try:
                failure=None
                try:value=future.result()
                except Exception as error:failure=error
                if settled:
                    try:settled()
                    except Exception as error:
                        if failure:raise RuntimeError(str(failure)+'; '+str(error)) from failure
                        raise
                if failure:raise failure
                finished(value)
                # A completion callback may start the next captured job.
                if task_id!=self._task_id:return False
                self._task_errors.pop(resource.id if resource else None,None)
                self._failed_resource=next(reversed(self._task_errors),None)
                self._phase = "error" if self._task_errors else "complete"
                self.progress.set_fraction(0)
                self.progress.set_text(tr('Failed') if self._task_errors else '')
                remaining=self._task_errors.get(self._failed_resource)
                self.status.set_text(remaining[0] if remaining else '')
                self.status.set_tooltip_text(remaining[1] if remaining else None)
                self.status.set_visible(bool(remaining))
                selected=self.selected_resource()
                context_current=(self.pages.get_visible_child_name()!='detail' or resource is None
                                 or selected is not None and selected.id==resource.id)
                if success_text and self.get_mapped() and context_current:
                    if self._success_toast:self._success_toast.dismiss()
                    toast=Adw.Toast.new(success_text);toast.set_timeout(4)
                    self._success_toast=toast;self.toast_overlay.add_toast(toast)
            except Exception as error:
                if failed:failed()
                self._phase = "error"
                self.progress.set_fraction(0)
                self.progress.set_text(tr("Failed"))
                self._failed_resource=resource.id if resource else None
                context=((plain(resource.description)+' ('+resource.name+'): ') if resource.provider_id=='youversion' else resource.id+': ') if resource else ''
                message=str(error)
                if resource and resource.kind=='study':
                    from .reference_data import ReferenceDataError
                    context=plain(resource.description)+': '
                    message=tr('Download cancelled.') if isinstance(error,InterruptedError) or str(error)==tr('Download cancelled.') else tr(
                        'The study data could not be verified. Previously installed data was preserved.' if isinstance(error,ReferenceDataError) else
                        'The study tool could not be downloaded or installed. Previously installed data was preserved.')
                    logging.getLogger(__name__).warning('Study resource %s: %s',resource.id,error)
                    self.status.set_tooltip_text(str(error))
                self.status.set_text(f'{context}{message}\n{tr("Retry using the same button.")}')
                self.status.set_visible(True)
                self._task_errors[self._failed_resource]=(self.status.get_text(),self.status.get_tooltip_text())
            finally:
                if queued_request:
                    self._queue_active=None
                    try:
                        if resource.id in self._task_errors:self.downloads.fail(queued_request,self._task_errors[resource.id][0])
                        else:self.downloads.finish(queued_request)
                    except (OSError,ValueError) as error:self.queue_error(error)
                    self._queue_revision+=1
                self.refresh_controls()
            return False

        future.add_done_callback(lambda _: GLib.idle_add(complete))

    def selected_providers(self):
        index=self.source_filter.get_selected()
        if 0<index<=len(PROVIDERS):return (PROVIDERS[index-1],)
        return tuple(p for p in PROVIDERS if p in DEFAULT_PROVIDERS or p.id in self._covered)

    def load_catalogue(self, *_, force=True):
        if self.closed or self.refreshing:return
        self._catalogue_requested=True
        self.refreshing=True
        self.refresh_status.set_visible(True)
        self.update_result_state()
        self.refresh_controls()
        if self.kind.get_selected()==2:
            self.session.refresh_study();self._refresh_generation=self.session.generation;return
        index=self.source_filter.get_selected()
        providers=self.selected_providers()
        self.session.refresh(catalogue,force,providers);self._refresh_generation=self.session.generation
        self.request_youversion_language(force)

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
                label=tr('Preparing the translation…') if self._task_resource and self._task_resource.startswith('youversion~') else tr('Preparing study data…')
                self.transfer_phase.set_text(label);self.progress.set_text(label)
            elif self._phase in ('converting','compiling','verifying'):
                label=tr({'converting':'Converting the translation…','compiling':'Converting to SWORD…',
                          'verifying':'Checking all chapters, introductions and translation notes…'}[self._phase])
                self.transfer_phase.set_text(label)
                self.progress.set_fraction(min(done/total,1) if total else 0)
                self.progress.set_text(label+(f' {done}/{total}' if total else ''))
            elif self._phase == 'installing':
                self.transfer_phase.set_text(tr('Installing and checking…'))
                self.progress.set_fraction(0)
                self.progress.set_text(tr('Installing and checking…'))
            else:
                self.transfer_phase.set_text(tr('Downloading') if total else tr('Downloading…')+' — '+tr('Size unknown'))
                self.progress.set_fraction(min(done / total, 1) if total else 0)
                self.progress.set_text(f'{done / 1024:.1f} KiB' +
                                       (f' / {total / 1024:.1f} KiB ({min(done * 100 // total, 100)}%)'
                                        if total else ' — ' + tr('Size unknown')))
            self.transfer_percent.set_text(f'{min(done * 100 // total,100)}%' if total and not self._indeterminate else '')
            self.transfer_percent.set_visible(bool(total) and not self._indeterminate)
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

    def install(self, *_, resource=None, permission=None, queued=False):
        resource = self.known_edition_details(resource) if resource else self.selected_resource()
        if resource and resource.kind=='study' and not queued:resource=self.study_resources.resource(resource.id)
        if not resource or not resource.installable or resource.id in self._archived_ids or (queued and self._transfer_busy):
            return
        existing=self.downloads.find(resource.id)
        if not queued and existing and existing.state!='failed':return
        if queued and resource.kind=='study':
            if resource.id in self._study_installed and self.study_resources.installed_resource(resource.id).revision==resource.revision:return
            if self.study_resources.resource(resource.id).revision!=resource.revision:
                raise ValueError(tr('The study resource changed. Review this download again.'))
        if resource.id in self.installed_ids() and (resource.kind!='study' or resource.id in self._study_current):
            if queued and resource.kind!='study':
                actual=self.installed_resource(resource.id)
                if actual.version!=resource.version or actual.acquisition!=resource.acquisition:
                    raise ValueError(tr('A different version is already installed. Check for updates before retrying.'))
            return

        if resource.provider_id=='youversion':
            if json.loads(resource.acquisition).get('_catalogue_summary'):
                def ready(actual):
                    if not actual.installable:raise ValueError(tr('No offline package supplied by the source.'))
                    self.install(resource=actual)
                self.load_edition_details(resource,ready)
                return
            from .youversion_install import acknowledgement
            if permission!=acknowledgement(resource):
                if queued:raise ValueError(tr('Source conditions changed. Review this download again.'))
                if self._permission_dialog:
                    self._review_downloads[resource.id]=(resource,lambda actual:self.install(resource=actual));return
                policy=json.loads(resource.acquisition).get('offline') or {}
                message=tr('You are responsible for checking that you have permission to download, convert and use this edition offline.')
                if policy.get('require_email_agreement'):
                    message+=' '+tr('The source requires an email agreement (version {version}). Satisfy this requirement with the provider before continuing.').format(version=policy.get('agreement_version') if policy.get('agreement_version') is not None else '?')
                message+=' '+tr('Bible does not submit an agreement or claim provider approval.')
                dialog=Adw.MessageDialog.new(self,tr('Download from Bible.com?'),
                    message)
                data=json.loads(resource.acquisition);notices=[]
                for key in ('copyright_short','copyright_long','reader_footer'):
                    value=data.get(key)
                    if isinstance(value,dict) and isinstance(value.get('text'),str):
                        notice=plain(value['text'])
                        if notice and notice not in notices:notices.append(notice)
                if notices:
                    label=Gtk.Label(label='\n\n'.join(notices),wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,selectable=True,xalign=0)
                    scroll=Gtk.ScrolledWindow(min_content_height=80,max_content_height=180,
                        propagate_natural_height=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
                    scroll.set_child(label);dialog.set_extra_child(scroll)
                dialog.add_response('cancel',tr('Cancel'));dialog.add_response('download',tr('I have the required permission'))
                dialog.set_close_response('cancel');dialog.set_default_response('cancel')
                self._permission_dialog=dialog
                def response(_,choice):
                    self._permission_dialog=None
                    if choice=='download' and not self.closed:self.install(resource=resource,permission=acknowledgement(resource))
                    GLib.idle_add(self.review_downloads)
                dialog.connect('response',response)
                dialog.present();return
        if not queued:
            from .study_resources import REFERENCE_RESOURCE_ID,TOPIC_RESOURCE_ID
            if resource.id in (REFERENCE_RESOURCE_ID,TOPIC_RESOURCE_ID):self.prepare_study_download(resource)
            else:self.queue_request(resource,permission)
            return
        caption=plain(resource.description)

        def installed(_):
            self._completed_resource=resource.id
            self.preparing=True;self.session.reload_installed()
            self.on_installed(resource.id)
            self.filter_resources()
            self.selection_changed()
        installer=self.study_resources if resource.kind=='study' else self.library
        def perform():
            options={'cancelled':self._cancel.is_set}
            if resource.provider_id=='youversion':
                options.update(cancelled=self._cancel.is_set,phase=self.queue_progress,permission=permission)
            return installer.install(resource,self.report_progress,installing=self.begin_installation,**options)
        self.task(tr('Downloading {name}…').format(name=caption),
                  perform,
                  installed, success_text=tr('Installed: {name}').format(name=caption),resource=resource)

