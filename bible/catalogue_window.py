"""Catalogue/download UI kept separate from the reading surface."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
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
        self.library, self.on_installed = library, on_installed
        self.owner = parent
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
        self.explore_button=Gtk.ToggleButton(label=tr('Explore'),active=True)
        self.installed_only=Gtk.ToggleButton(label=tr('Installed resources'),group=self.explore_button)
        self.installed_only.connect('toggled',self.update_languages)
        views.append(self.explore_button);views.append(self.installed_only);explorer.append(views)
        self.search=Gtk.SearchEntry(placeholder_text=tr('Search resources'),margin_start=12,margin_end=12)
        self.search.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search resources')])
        self.search.connect('search-changed',self.filter_resources);explorer.append(self.search)
        filters=Gtk.Box(spacing=8,margin_start=12,margin_end=12)
        self.kind=Gtk.DropDown(model=Gtk.StringList.new([tr('Bibles'),tr('Commentaries'),tr('Study resources')]))
        self.kind.update_property([Gtk.AccessibleProperty.LABEL],[tr('Resource type')])
        self.kind.connect('notify::selected',self.update_languages)
        filters.append(self.kind)
        self.language=LanguagePicker(self.filter_resources);self.language.set_hexpand(True)
        self.language.update_property([Gtk.AccessibleProperty.LABEL],[tr('Language')]);filters.append(self.language)
        explorer.append(filters)
        self.source_filter=Gtk.DropDown(model=Gtk.StringList.new([tr('All sources')]+[p.name for p in PROVIDERS]),margin_start=12,margin_end=12)
        self.source_filter.update_property([Gtk.AccessibleProperty.LABEL],[tr('Source')])
        self.source_filter.connect('notify::selected',self.update_languages);explorer.append(self.source_filter)
        self.choice_model=Gio.ListStore.new(ResourceItem)
        self.choices=Gtk.SingleSelection(model=self.choice_model)
        self.choices.connect('notify::selected',self.selection_changed)
        factory=Gtk.SignalListItemFactory()
        factory.connect('setup',self.setup_resource_row);factory.connect('bind',self.bind_resource_row)
        self.resource_list=Gtk.ListView(model=self.choices,factory=factory,single_click_activate=True)
        self.resource_list.add_css_class('navigation-sidebar')
        self.resource_list.connect('activate',self.open_details)
        self.list_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.list_scroll.set_child(self.resource_list);explorer.append(self.list_scroll)
        self.empty=Gtk.Label(label=tr('No matching resource.'),wrap=True,visible=False,margin_top=20,margin_bottom=20)
        explorer.append(self.empty)
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
        self.pages.add_named(detail,'detail');layout.append(self.pages)
        self.progress=Gtk.ProgressBar(margin_start=12,margin_end=12,visible=False)
        layout.append(self.progress)
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
        if self.closed:return False
        changed=(self.resources!=list(snapshot.resources) or self._installed_metadata!=snapshot.installed
                 or self._study_installed!=snapshot.study_installed or self._study_current!=snapshot.study_current
                 or self._language_records!=snapshot.languages)
        self.preparing=False;self.resources=list(snapshot.resources)
        self._installed_metadata=snapshot.installed;self._study_installed=snapshot.study_installed
        self._study_current=snapshot.study_current;self._language_records=snapshot.languages
        self._search_terms=snapshot.search;self.timings.update(snapshot.timings)
        if snapshot.generation>=self._refresh_generation:self.refreshing=snapshot.refreshing
        if changed:self.update_languages()
        errors=snapshot.errors
        message=(tr('Refreshing sources… Cached resources remain available.') if self.refreshing else
            tr('Partial catalogue. Retry to reload unavailable sources.')+' '+tr('Saved results retained.')+'\n'+
            '\n'.join(f'{name}: {error}' for name,error in errors.items()) if errors else
            tr('Saved catalogue — available offline.') if self.resources and not self._catalogue_requested else
            tr('Ready') if self.resources else tr('No supported resource found.'))
        self.refresh_status.set_text(message);self.refresh_status.set_visible(bool(errors) or self.refreshing or not self.resources)
        if not self._transfer_busy and self._phase!='error' and self._completed_resource is None:
            self.status.set_text(message);self.status.set_visible(False)
        self.refresh_controls()
        if not self._catalogue_requested and self.get_mapped():GLib.idle_add(self.auto_load)
        return False

    def auto_load(self,*_):
        if self.kind.get_selected()==2:return False
        if not self.closed and not self._catalogue_requested and not self.busy and not self.installed_only.get_active():self.load_catalogue(force=False)
        return False

    def setup_resource_row(self,_,item):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,margin_start=12,margin_end=12,margin_top=10,margin_bottom=10)
        title=Gtk.Label(xalign=0,ellipsize=Pango.EllipsizeMode.END,max_width_chars=40,width_chars=1)
        title.add_css_class('heading');box.append(title)
        subtitle=Gtk.Label(xalign=0,wrap=True,max_width_chars=40)
        subtitle.add_css_class('dim-label');box.append(subtitle)
        item.set_child(box)

    def bind_resource_row(self,_,item):
        resource=item.get_item().resource
        box=item.get_child();title=box.get_first_child();subtitle=title.get_next_sibling()
        title.set_text(plain(resource.description))
        installed=resource.id in getattr(self,'_installed_ids',set())
        subtitle.set_text(self.language_label(resource.language)+' — '+resource.source+(' · '+tr('Installed') if installed else ''))
        box.set_tooltip_text(resource.name+' · '+resource.language)

    def open_details(self,_,index):
        self._list_position=self.list_scroll.get_vadjustment().get_value()
        self.choices.set_selected(index);self.selection_changed()
        self.pages.set_visible_child_name('detail');self.back_button.set_visible(True)
        self.metadata.select_region(0, 0)
        self.back_button.grab_focus()

    def back_to_list(self,*_):
        self.pages.set_visible_child_name('list');self.back_button.set_visible(False)
        self.list_scroll.get_vadjustment().set_value(getattr(self,'_list_position',0))

    def current_resources(self):
        if self.kind.get_selected()==2:
            installed=self._study_installed
            return [r for r in self.study_resources.available()
                    if not self.installed_only.get_active() or r.id in installed]
        resources = (list(self._installed_metadata.values())
                     if self.installed_only.get_active() else self.resources)
        kind = 'commentary' if self.kind.get_selected() == 1 else 'bible'
        index = self.source_filter.get_selected()
        provider_id = self.source_ids[index] if index < len(self.source_ids) else None
        return [resource for resource in resources if resource.kind == kind
                and (provider_id is None or resource.provider_id == provider_id)]

    def update_languages(self, *_):
        study=self.kind.get_selected()==2
        self.language.set_visible(not study);self.source_filter.set_visible(not study)
        self.catalogue_button.set_visible(not study)
        self._filtering=True
        self.languages=['']+sorted({r.language for r in self.current_resources()},key=lambda code:self.language_label(code).casefold())
        self.language.set_codes(self.languages,self._language_records)
        self._filtering=False
        self.filter_resources()
        if not self.installed_only.get_active() and not self.busy and not self.resources and self.get_mapped():
            GLib.idle_add(self.auto_load)

    def filter_resources(self, *_):
        if self.closed:return False
        if self._filtering:
            return
        selected=self.selected_resource()
        selected_id=selected.id if selected else None
        position=self.list_scroll.get_vadjustment().get_value()
        index = self.language.get_selected()
        language = self.languages[index] if index < len(self.languages) else ''
        query = normalized(self.search.get_text())
        self.filtered_resources = [r for r in self.current_resources()
                                   if (not language or r.language == language)
                                   and query in (self._search_terms.get(r.id) or normalized(' '.join((r.name,r.description,r.language,self.language_label(r.language)))))]
        self._installed_ids=set(self.installed_ids())
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
        if append_rows():GLib.idle_add(append_rows)
        self.empty.set_visible(not self.filtered_resources)
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


    def on_close(self, *_):
        if self._transfer_busy and not self.owner.closed:
            self.set_visible(False)
            return True
        self.closed = True
        self._rows_generation+=1;self.language.cancel_pending();self.session.unsubscribe(self.snapshot_ready)
        self.stop_animation()
        self.executor.shutdown(wait=False, cancel_futures=True)
        return False

    def task(self, message, action, finished, success_text=None, resource=None):
        if self._transfer_busy:
            return
        self._transfer_busy = True
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
        self.refresh_status.set_text(tr('Refreshing sources… Cached resources remain available.'))
        self.refresh_controls()
        self.session.refresh(catalogue,force);self._refresh_generation=self.session.generation

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
            self._indeterminate = self._phase == 'installing' or not total
            if self._phase == 'installing':
                self.status.set_text(tr('Installing and checking…'))
                self.progress.set_fraction(0)
                self.progress.set_text(tr('Installing and checking…'))
            else:
                self.progress.set_fraction(min(done / total, 1) if total else 0)
                self.progress.set_text(f'{done / 1024:.1f} KiB' +
                                       (f' / {total / 1024:.1f} KiB ({min(done * 100 // total, 100)}%)'
                                        if total else ' — ' + tr('Size unknown')))
        if self._indeterminate:
            self.progress.pulse()
        return True

    def report_progress(self, done, total):
        self.queue_progress('downloading', done, total)

    def install(self, *_):
        resource = self.selected_resource()
        if not resource or not resource.installable or self._transfer_busy:
            return

        def installed(_):
            self._completed_resource=resource.id
            self.preparing=True;self.session.reload_installed()
            self.on_installed(resource.id)
            self.filter_resources()
            self.status.set_text(tr('Installed: {name}').format(name=resource.name))
            self.selection_changed()
        installer=self.study_resources if resource.kind=='study' else self.library
        self.task(tr('Downloading {name}…').format(name=resource.name),
                  lambda: installer.install(resource, self.report_progress,
                                                installing=lambda: self.queue_progress('installing')),
                  installed, success_text=tr('Installed: {name}').format(name=resource.name),resource=resource)

